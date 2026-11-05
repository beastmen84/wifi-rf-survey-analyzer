"""Whole-fragment selection and reversible rigid move/quarter-turn previews."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QGraphicsPathItem, QGraphicsRectItem

from qt_ui.scaling import widget_px
from survey.plan_drawing import validate_segments
from survey.plan_erasing import intersecting_segments
from survey.plan_geometry import rotate_degrees, segment_bounds, translate_segments
from survey.plan_labels import labels_geometry, transform_labels
from survey.plan_snapping import PlanSnapper
from survey.plan_curves import curves_geometry, transform_curves, validate_curves
from survey.plan_curve_geometry import normalize_plan
from survey.plan_curve_rendering import curve_path
from survey.curve_erasing import intersecting_curves
from survey.plan_erasing import nearest_segment
from survey.curve_erasing import nearest_curve
from survey.planar_geometry import point_projection
from survey.plan_curves import project_curve, curve_info
from app_core.units import meters_to_display_units, distance_unit_label
from qt_ui.qt_plan_region_selection import RegionPicker


class PlanSelectionController:
    def __init__(self, drawing):
        self.drawing, self.owner, self.view = drawing, drawing.owner, drawing.view
        self.lines, self.selected, self.highlights = [], (), []
        self.selected_labels, self.area_labels = (), ()
        self.selected_curves, self.area_curves = (), ()
        self.move_curve_source, self.move_curve_preview = [], []
        self.move_label_source, self.move_label_preview = [], []
        self.origin = self.press_position = self.last_pointer = self.area = None
        self.dragged = self.moving = self.consume_release = False
        self.move_source = []
        self.move_turns = 0
        self.move_anchor = None
        self.move_preview = []
        self.move_snapper = PlanSnapper()
        self.region_picker = None
        self.selected_region_area = None

    def reset_scene(self):
        self.highlights, self.area = [], None
        self.selected = ()
        self.cancel()

    def set_segments(self, lines):
        self.cancel()
        self.lines = lines
        self.region_picker = None

    def cancel(self):
        active = self.origin is not None or self.moving or self.has_selection()
        self.origin = self.press_position = self.last_pointer = None
        self.dragged = self.moving = self.consume_release = False
        self.move_preview, self.move_source = [], []
        self.selected = ()
        self.selected_labels = ()
        self.selected_curves = ()
        self.selected_region_area = None
        self.move_label_source, self.move_label_preview = [], []
        self.move_curve_source, self.move_curve_preview = [], []
        self.clear_items()
        self.drawing.text.clear_preview()
        for item in self.drawing.text.items:
            item.setOpacity(1)
        for item in self.drawing.items:
            item.setOpacity(1)
        for item in self.drawing.curve.items:
            item.setOpacity(1)
        self.drawing.clear_snap_guides()
        self.drawing.measurement.hide()
        return active

    def clear_items(self):
        for item in self.highlights:
            self.view.scene.removeItem(item)
        self.highlights = []
        if self.area is not None:
            self.view.scene.removeItem(self.area)
            self.area = None

    def hide_preview(self):
        self.last_pointer = None
        if self.moving:
            for item in self.highlights:
                item.hide()

    def show_lines(self, lines, moving=False, labels=None, curves=None):
        for item in self.highlights:
            self.view.scene.removeItem(item)
        self.highlights = []
        labels = labels or []
        curves = curves or []
        if moving:
            self.drawing.text.show_labels(labels)
        if not lines and not labels and not curves:
            return
        path = QPainterPath()
        for line in list(lines) + labels_geometry(labels):
            path.moveTo(line["x1"], line["y1"])
            path.lineTo(line["x2"], line["y2"])
        for curve in curves:
            path.addPath(curve_path(curve))
        for color, width in ((QColor(14, 165, 233, 85), 8), (QColor("#0284c7"), 2)):
            item = QGraphicsPathItem(path)
            pen = QPen(color, widget_px(self.owner, width))
            pen.setCosmetic(True)
            if moving and width == 2:
                pen.setStyle(Qt.PenStyle.DashLine)
            item.setPen(pen)
            item.setZValue(8)
            item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.view.scene.addItem(item)
            self.highlights.append(item)

    def has_selection(self):
        return bool(self.selected or self.selected_labels or self.selected_curves)

    def can_rotate(self):
        # A single complete circle has no orientation. In a larger selection
        # its center participates in the group's rigid positional transform.
        return self.has_selection() and bool(self.selected or self.selected_labels
            or len(self.selected_curves) > 1 or self.selected_curve_shapes()[0]["kind"] != "circle")

    def selected_texts(self):
        return [self.drawing.text.labels[index] for index in self.selected_labels]

    def selected_curve_shapes(self):
        curves = self.drawing.curves()
        return [curves[index] for index in self.selected_curves]

    def geometry(self, lines=None, labels=None, curves=None):
        if lines is None:
            lines = [self.lines[index] for index in self.selected]
        if labels is None:
            labels = self.selected_texts()
        if curves is None:
            curves = self.selected_curve_shapes()
        return list(lines) + labels_geometry(labels) + curves_geometry(curves)

    def set_selected(self, indices, label_indices=(), curve_indices=(), *, region_area=None):
        self.selected = tuple(sorted(indices))
        self.selected_labels = tuple(sorted(label_indices))
        self.selected_curves = tuple(sorted(curve_indices))
        self.selected_region_area = (self.regions().matching_area(self.selected, self.selected_curves)
                                     if region_area is not None else None)
        self.show_lines([self.lines[index] for index in self.selected], labels=self.selected_texts(), curves=self.selected_curve_shapes())
        self.drawing.tools.update_tool_state()

    def point(self, position):
        point = self.view.mapToScene(position.toPoint())
        bounds = self.view.scene.sceneRect()
        return QPointF(min(max(point.x(), bounds.left()), bounds.right()),
                       min(max(point.y(), bounds.top()), bounds.bottom()))

    def show_count(self, position):
        if self.has_selection():
            count = len(self.selected) + len(self.selected_labels) + len(self.selected_curves)
            rows = []
            if self.selected_region_area is not None:
                rows.append(self.measure("selection_area", self.selected_region_area, power=2))
            elif count == 1 and self.selected:
                line = (self.move_preview[0] if self.moving and self.move_preview else self.lines[self.selected[0]])
                rows.append(self.measure("line_length", math.hypot(line["x2"] - line["x1"], line["y2"] - line["y1"])))
            elif count == 1 and self.selected_curves:
                curve = self.move_curve_preview[0] if self.moving and self.move_curve_preview else self.selected_curve_shapes()[0]
                _cx, _cy, radius, _start, sweep = curve_info(curve)
                if curve["kind"] == "arc":
                    rows.append(self.measure("selection_arc_length", radius * abs(sweep)))
                rows.append(self.measure("curve_radius", radius))
                if curve["kind"] == "arc":
                    rows.append(self.measure("curve_chord", math.hypot(curve["x2"] - curve["x1"], curve["y2"] - curve["y1"])))
                    rows.append(self.measure("curve_sagitta", curve["height"]))
            rows.append(self.owner.tr("selection_items_count").format(count=count))
            if self.moving:
                rows.append(self.owner.tr("selection_action_place"))
            if self.can_rotate():
                rows.append(self.owner.tr("selection_action_rotate"))
            if not self.moving:
                rows.append(self.owner.tr("selection_action_move"))
                if count == 1 and (self.selected_labels or self.selected_curves):
                    rows.append(self.owner.tr("selection_action_edit"))
            rows.extend(self.owner.tr(key) for key in ("selection_action_delete", "selection_action_cancel"))
            self.drawing.show_measurement("\n".join(rows), position)
        else:
            self.drawing.measurement.hide()

    def measure(self, key, pixels, power=1):
        density = self.owner.get_px_per_meter()
        value = pixels / density ** power * meters_to_display_units(1, self.owner.measurement_system) ** power
        unit = distance_unit_label(self.owner.measurement_system) + ("²" if power == 2 else "")
        return self.owner.tr(key) + ": " + self.drawing.measurement.locale().toString(value, "f", 2) + " " + unit

    def regions(self):
        if self.region_picker is None:
            self.region_picker = RegionPicker(self.lines, self.drawing.curves())
            if self.region_picker.limited:
                self.owner.status.showMessage(self.owner.tr("design_regions_limited"))
        return self.region_picker

    def pick_stroke(self, point):
        zoom = max(1e-9, math.hypot(self.view.transform().m11(), self.view.transform().m12()))
        tolerance = widget_px(self.owner, 6) / zoom + 1
        x, y = point.x(), point.y()
        curves = self.drawing.curves()
        line_index = nearest_segment(self.lines, x, y, tolerance)
        curve_index = nearest_curve(curves, x, y, tolerance)
        choices = []
        if line_index is not None:
            line = self.lines[line_index]
            projection = point_projection((x, y), (line["x1"], line["y1"]), (line["x2"], line["y2"]))
            choices.append((math.dist((x, y), projection), 1, line_index))
        if curve_index is not None:
            choices.append((math.dist((x, y), project_curve(curves[curve_index], (x, y))), 0, curve_index))
        if not choices:
            return (), ()
        _distance, kind, index = min(choices)
        return ((index,), ()) if kind else ((), (index,))

    def press(self, event):
        self.last_pointer = event.position()
        if self.moving:
            if self.view.scene.sceneRect().contains(self.view.mapToScene(event.position().toPoint())):
                self.update_move(event.position(), bool(event.modifiers() & Qt.KeyboardModifier.AltModifier))
                transformed = self.move_preview
                self.apply_transformed(transformed, self.move_label_preview, self.move_curve_preview)
            self.consume_release = True
            return True
        if self.view.scene.sceneRect().contains(self.view.mapToScene(event.position().toPoint())):
            self.origin, self.press_position = self.point(event.position()), event.position()
            self.dragged = False
        return True

    def move(self, event):
        self.last_pointer = event.position()
        if self.moving:
            if self.view.scene.sceneRect().contains(self.view.mapToScene(event.position().toPoint())):
                self.update_move(event.position(), bool(event.modifiers() & Qt.KeyboardModifier.AltModifier))
            else:
                self.drawing.hide_preview()
            return False  # Left-button hand-drag still pans, then refreshes.
        if self.origin is not None and event.buttons() & Qt.MouseButton.RightButton:
            self.dragged |= (event.position() - self.press_position).manhattanLength() >= QApplication.startDragDistance()
            if self.dragged:
                self.show_area(event.position())
            return True
        self.show_count(event.position())
        return False

    def show_area(self, position):
        rect = QRectF(self.origin, self.point(position)).normalized()
        indices = intersecting_segments(self.lines, rect.left(), rect.top(), rect.right(), rect.bottom())
        self.area_labels = self.drawing.text.intersecting(rect)
        self.area_curves = intersecting_curves(self.drawing.curves(), rect.left(), rect.top(), rect.right(), rect.bottom())
        self.show_lines([self.lines[index] for index in indices],
                        labels=[self.drawing.text.labels[index] for index in self.area_labels],
                        curves=[self.drawing.curves()[index] for index in self.area_curves])
        if self.area is None:
            self.area = QGraphicsRectItem()
            pen = QPen(QColor("#0284c7"), 1, Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            self.area.setPen(pen)
            self.area.setBrush(QColor(14, 165, 233, 25))
            self.area.setZValue(7)
            self.area.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.view.scene.addItem(self.area)
        self.area.setRect(rect)
        text = self.owner.tr("selection_items_count").format(count=len(indices) + len(self.area_labels) + len(self.area_curves))
        self.drawing.show_measurement(text, position)
        return indices

    def release(self, event):
        if self.consume_release:
            self.consume_release = False
            return True
        if self.origin is None:
            return True
        region_area = None
        if self.dragged or (event.position() - self.press_position).manhattanLength() >= QApplication.startDragDistance():
            indices = self.show_area(event.position())
            label_indices = self.area_labels
            curve_indices = self.area_curves
        else:
            hit = self.drawing.text.hit(self.origin)
            label_indices = (hit,) if hit is not None else ()
            indices, curve_indices = ((), ()) if label_indices else self.pick_stroke(self.origin)
            if not (label_indices or indices or curve_indices):
                region = self.regions().pick(self.origin)
                if region is None:
                    self.origin = self.press_position = None
                    self.dragged = False
                    self.show_count(event.position())
                    return True  # Open space does not change the current selection.
                indices, curve_indices, region_area = region.lines, region.curves, region.area
        self.origin = self.press_position = None
        self.dragged = False
        self.clear_items()
        self.set_selected(indices, label_indices, curve_indices, region_area=region_area)
        self.show_count(event.position())
        return True

    def fits(self, lines):
        if not lines:
            return False
        left, top, right, bottom = segment_bounds(lines)
        bounds = self.view.scene.sceneRect()
        return left >= bounds.left() - 1e-7 and top >= bounds.top() - 1e-7 and right <= bounds.right() + 1e-7 and bottom <= bounds.bottom() + 1e-7

    def apply_transformed(self, transformed, transformed_labels=None, transformed_curves=None):
        region_area = self.selected_region_area
        transformed_labels = self.selected_texts() if transformed_labels is None else transformed_labels
        transformed_curves = self.selected_curve_shapes() if transformed_curves is None else transformed_curves
        if not self.fits(self.geometry(transformed, transformed_labels, transformed_curves)):
            self.owner.status.showMessage(self.owner.tr("design_rotation_outside"))
            return False
        current = [self.lines[index] for index in self.selected]
        if transformed == current and transformed_labels == self.selected_texts() and transformed_curves == self.selected_curve_shapes():
            previous, previous_labels, previous_curves = self.selected, self.selected_labels, self.selected_curves
            self.cancel()
            self.set_selected(previous, previous_labels, previous_curves, region_area=region_area)
            return False
        selected_indices = set(self.selected)
        others = [line for index, line in enumerate(self.lines) if index not in selected_indices]
        other_curves = [curve for index, curve in enumerate(self.drawing.curves()) if index not in self.selected_curves]
        try:
            normalized, curves, sources, curve_sources = normalize_plan(validate_segments(others + transformed),
                validate_curves(other_curves + list(transformed_curves)), with_sources=True)
        except ValueError:
            self.owner.status.showMessage(self.owner.tr("design_edit_limit"))
            return False
        # A joined piece may include stationary geometry. Do not silently select
        # that geometry and move it with the next transform.
        selected = tuple(index for index, source in enumerate(sources) if all(origin >= len(others) for origin in source))
        selected_curves = tuple(index for index, source in enumerate(curve_sources) if all(origin >= len(other_curves) for origin in source))
        other_labels = [label for index, label in enumerate(self.drawing.text.labels) if index not in self.selected_labels]
        changed = self.drawing.apply_edit(normalized, other_labels + list(transformed_labels), curves)
        if changed:
            self.set_selected(selected, range(len(other_labels), len(other_labels) + len(transformed_labels)), selected_curves, region_area=region_area)
        elif self.moving:
            # A zero-offset placement finishes the preview without a history edit.
            previous, previous_labels, previous_curves = self.selected, self.selected_labels, self.selected_curves
            self.cancel()
            self.set_selected(previous, previous_labels, previous_curves, region_area=region_area)
        return changed

    def delete_selected(self):
        if not self.has_selection() or self.drawing.rotation.active:
            return False
        segments = [line for index, line in enumerate(self.lines) if index not in self.selected]
        labels = [label for index, label in enumerate(self.drawing.text.labels) if index not in self.selected_labels]
        curves = [curve for index, curve in enumerate(self.drawing.curves()) if index not in self.selected_curves]
        self.cancel()
        return self.drawing.apply_edit(segments, labels, curves)

    def apply_rotation(self, angle, pivot=None):
        if not self.can_rotate():
            return False
        geometry = self.geometry()
        left, top, right, bottom = segment_bounds(geometry)
        pivot = pivot or ((left + right) / 2, (top + bottom) / 2)
        return self.apply_transformed(rotate_degrees([self.lines[index] for index in self.selected], angle, pivot),
                                      transform_labels(self.selected_texts(), angle, pivot),
                                      transform_curves(self.selected_curve_shapes(), angle, pivot))

    def rotated_move(self, turns=None):
        turns = self.move_turns if turns is None else turns
        left, top, right, bottom = segment_bounds(self.geometry(self.move_source, self.move_label_source, self.move_curve_source))
        pivot = ((left + right) / 2, (top + bottom) / 2)
        return (rotate_degrees(self.move_source, turns * 90, pivot),
                transform_labels(self.move_label_source, turns * 90, pivot),
                transform_curves(self.move_curve_source, turns * 90, pivot))

    def rotate(self):
        if not self.can_rotate() or self.origin is not None:
            return False
        if self.moving:
            turns = (self.move_turns + 1) % 4
            rotated, labels, curves = self.rotated_move(turns)
            left, top, right, bottom = segment_bounds(self.geometry(rotated, labels, curves))
            bounds = self.view.scene.sceneRect()
            if right - left > bounds.width() or bottom - top > bounds.height():
                self.owner.status.showMessage(self.owner.tr("design_rotation_outside"))
                return True
            self.move_turns = turns
            self.refresh_snap()
        else:
            self.apply_rotation(90)
        return True

    def begin_move(self):
        if not self.has_selection() or self.origin is not None:
            return False
        if self.moving:
            return True
        self.moving = True
        self.move_source = [dict(self.lines[index]) for index in self.selected]
        self.move_label_source = transform_labels(self.selected_texts())
        self.move_curve_source = transform_curves(self.selected_curve_shapes())
        self.move_turns = 0
        left, top, right, bottom = segment_bounds(self.geometry(self.move_source, self.move_label_source, self.move_curve_source))
        self.move_anchor = (self.point(self.last_pointer) if self.last_pointer is not None
                            else QPointF((left + right) / 2, (top + bottom) / 2))
        if self.last_pointer is None:
            self.last_pointer = QPointF(self.view.mapFromScene(self.move_anchor))
        selected = set(self.selected)
        self.move_snapper = PlanSnapper([line for index, line in enumerate(self.lines) if index not in selected],
                                      [curve for index, curve in enumerate(self.drawing.curves()) if index not in self.selected_curves])
        self.clear_items()
        for index in self.selected:
            self.drawing.items[index].setOpacity(.25)
        for index in self.selected_labels:
            self.drawing.text.items[index].setOpacity(.25)
        for index in self.selected_curves:
            self.drawing.curve.items[index].setOpacity(.25)
        self.refresh_snap()
        return True

    def update_move(self, position, bypass=False):
        source, labels, curves = self.rotated_move()
        geometry = self.geometry(source, labels, curves)
        left, top, right, bottom = segment_bounds(geometry)
        point = self.point(position)
        x, y = left + point.x() - self.move_anchor.x(), top + point.y() - self.move_anchor.y()
        bounds = self.view.scene.sceneRect()
        x = min(max(x, bounds.left()), bounds.right() - (right - left))
        y = min(max(y, bounds.top()), bounds.bottom() - (bottom - top))
        self.drawing.snap_guides = ()
        if not bypass and not self.drawing.snap_bypass and not any(
                line["x1"] != line["x2"] and line["y1"] != line["y2"] for line in geometry):
            zoom = max(1e-9, math.hypot(self.view.transform().m11(), self.view.transform().m12()))
            result = self.move_snapper.snap(x, y, right - left, bottom - top,
                (bounds.left(), bounds.top(), bounds.right(), bounds.bottom()), widget_px(self.owner, 10) / zoom,
                self.view.grid_spacing_pixels() if self.drawing.tools.snap_button.isChecked() else None,
                source_vertices=[(line[a] + (x - left), line[b] + (y - top))
                                 for line in geometry for a, b in (("x1", "y1"), ("x2", "y2"))])
            x, y, self.drawing.snap_guides = result.x, result.y, result.guides
        self.move_preview = translate_segments(source, x - left, y - top)
        self.move_label_preview = transform_labels(labels, dx=x - left, dy=y - top)
        self.move_curve_preview = transform_curves(curves, dx=x - left, dy=y - top)
        combined = self.geometry(self.move_preview, self.move_label_preview, self.move_curve_preview)
        if any(line["x1"] != line["x2"] and line["y1"] != line["y2"] for line in combined):
            snapped = self.drawing.snap_shape(combined, bypass, self.move_snapper)
            dx, dy = snapped[0]["x1"] - combined[0]["x1"], snapped[0]["y1"] - combined[0]["y1"]
            self.move_preview = translate_segments(self.move_preview, dx, dy)
            self.move_label_preview = transform_labels(self.move_label_preview, dx=dx, dy=dy)
            self.move_curve_preview = transform_curves(self.move_curve_preview, dx=dx, dy=dy)
            left, top, right, bottom = segment_bounds(snapped)
            x, y = left, top
            self.show_lines(self.move_preview, moving=True, labels=self.move_label_preview, curves=self.move_curve_preview)
            self.drawing.show_snap_guides(QRectF(left, top, right - left, bottom - top))
            self.show_count(position)
            return
        self.show_lines(self.move_preview, moving=True, labels=self.move_label_preview, curves=self.move_curve_preview)
        self.drawing.show_snap_guides(QRectF(x, y, right - left, bottom - top))
        self.show_count(position)

    def refresh_snap(self):
        if self.moving and self.last_pointer is not None:
            self.update_move(self.last_pointer)
