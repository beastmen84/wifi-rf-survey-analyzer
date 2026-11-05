"""Whole-fragment selection and reversible rigid move/quarter-turn previews."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QGraphicsPathItem, QGraphicsRectItem

from qt_ui.scaling import widget_px
from survey.plan_drawing import validate_segments
from survey.plan_erasing import intersecting_segments
from survey.plan_geometry import normalize_segments, rotate_degrees, segment_bounds, translate_segments
from survey.plan_labels import labels_geometry, transform_labels
from survey.plan_snapping import PlanSnapper


class PlanSelectionController:
    def __init__(self, drawing):
        self.drawing, self.owner, self.view = drawing, drawing.owner, drawing.view
        self.lines, self.selected, self.highlights = [], (), []
        self.selected_labels, self.area_labels = (), ()
        self.move_label_source, self.move_label_preview = [], []
        self.origin = self.press_position = self.last_pointer = self.area = None
        self.dragged = self.moving = self.consume_release = False
        self.move_source = []
        self.move_turns = 0
        self.move_anchor = None
        self.move_preview = []
        self.move_snapper = PlanSnapper()

    def reset_scene(self):
        self.highlights, self.area = [], None
        self.selected = ()
        self.cancel()

    def set_segments(self, lines):
        self.cancel()
        self.lines = lines

    def cancel(self):
        active = self.origin is not None or self.moving or self.has_selection()
        self.origin = self.press_position = self.last_pointer = None
        self.dragged = self.moving = self.consume_release = False
        self.move_preview, self.move_source = [], []
        self.selected = ()
        self.selected_labels = ()
        self.move_label_source, self.move_label_preview = [], []
        self.clear_items()
        self.drawing.text.clear_preview()
        for item in self.drawing.text.items:
            item.setOpacity(1)
        for item in self.drawing.items:
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

    def show_lines(self, lines, moving=False, labels=None):
        for item in self.highlights:
            self.view.scene.removeItem(item)
        self.highlights = []
        labels = labels or []
        if moving:
            self.drawing.text.show_labels(labels)
        if not lines and not labels:
            return
        path = QPainterPath()
        for line in list(lines) + labels_geometry(labels):
            path.moveTo(line["x1"], line["y1"])
            path.lineTo(line["x2"], line["y2"])
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
        return bool(self.selected or self.selected_labels)

    def selected_texts(self):
        return [self.drawing.text.labels[index] for index in self.selected_labels]

    def geometry(self, lines=None, labels=None):
        if lines is None:
            lines = [self.lines[index] for index in self.selected]
        if labels is None:
            labels = self.selected_texts()
        return list(lines) + labels_geometry(labels)

    def set_selected(self, indices, label_indices=()):
        self.selected = tuple(sorted(indices))
        self.selected_labels = tuple(sorted(label_indices))
        self.show_lines([self.lines[index] for index in self.selected], labels=self.selected_texts())
        self.drawing.tools.update_tool_state()

    def point(self, position):
        point = self.view.mapToScene(position.toPoint())
        bounds = self.view.scene.sceneRect()
        return QPointF(min(max(point.x(), bounds.left()), bounds.right()),
                       min(max(point.y(), bounds.top()), bounds.bottom()))

    def show_count(self, position):
        if self.has_selection():
            text = self.owner.tr("selection_items_count").format(count=len(self.selected) + len(self.selected_labels))
            text += "\n" + self.owner.tr("selection_move_hint" if self.moving else "selection_keys_hint")
            self.drawing.show_measurement(text, position)
        else:
            self.drawing.measurement.hide()

    def press(self, event):
        self.last_pointer = event.position()
        if self.moving:
            if self.view.scene.sceneRect().contains(self.view.mapToScene(event.position().toPoint())):
                self.update_move(event.position(), bool(event.modifiers() & Qt.KeyboardModifier.AltModifier))
                transformed = self.move_preview
                self.apply_transformed(transformed, self.move_label_preview)
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
        self.show_lines([self.lines[index] for index in indices],
                        labels=[self.drawing.text.labels[index] for index in self.area_labels])
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
        text = self.owner.tr("selection_items_count").format(count=len(indices) + len(self.area_labels))
        self.drawing.show_measurement(text, position)
        return indices

    def release(self, event):
        if self.consume_release:
            self.consume_release = False
            return True
        if self.origin is None:
            return True
        if self.dragged or (event.position() - self.press_position).manhattanLength() >= QApplication.startDragDistance():
            indices = self.show_area(event.position())
            label_indices = self.area_labels
        else:
            hit = self.drawing.text.hit(self.origin)
            label_indices = (hit,) if hit is not None else ()
            indices = () if label_indices else self.drawing.eraser.pick(self.origin)
        self.origin = self.press_position = None
        self.dragged = False
        self.clear_items()
        self.set_selected(indices, label_indices)
        self.show_count(event.position())
        return True

    def fits(self, lines):
        if not lines:
            return False
        left, top, right, bottom = segment_bounds(lines)
        bounds = self.view.scene.sceneRect()
        return left >= bounds.left() - 1e-7 and top >= bounds.top() - 1e-7 and right <= bounds.right() + 1e-7 and bottom <= bounds.bottom() + 1e-7

    def apply_transformed(self, transformed, transformed_labels=None):
        transformed_labels = self.selected_texts() if transformed_labels is None else transformed_labels
        if not self.fits(self.geometry(transformed, transformed_labels)):
            self.owner.status.showMessage(self.owner.tr("design_rotation_outside"))
            return False
        current = [self.lines[index] for index in self.selected]
        if transformed == current and transformed_labels == self.selected_texts():
            previous, previous_labels = self.selected, self.selected_labels
            self.cancel()
            self.set_selected(previous, previous_labels)
            return False
        selected_indices = set(self.selected)
        others = [line for index, line in enumerate(self.lines) if index not in selected_indices]
        try:
            normalized, sources = normalize_segments(validate_segments(others + transformed), with_sources=True)
        except ValueError:
            self.owner.status.showMessage(self.owner.tr("design_edit_limit"))
            return False
        # A joined piece may include stationary geometry. Do not silently select
        # that geometry and move it with the next transform.
        selected = tuple(index for index, source in enumerate(sources) if all(origin >= len(others) for origin in source))
        other_labels = [label for index, label in enumerate(self.drawing.text.labels) if index not in self.selected_labels]
        changed = self.drawing.apply_edit(normalized, other_labels + list(transformed_labels))
        if changed:
            self.set_selected(selected, range(len(other_labels), len(other_labels) + len(transformed_labels)))
        elif self.moving:
            # A zero-offset placement finishes the preview without a history edit.
            previous, previous_labels = self.selected, self.selected_labels
            self.cancel()
            self.set_selected(previous, previous_labels)
        return changed

    def delete_selected(self):
        if not self.has_selection() or self.drawing.rotation.active:
            return False
        segments = [line for index, line in enumerate(self.lines) if index not in self.selected]
        labels = [label for index, label in enumerate(self.drawing.text.labels) if index not in self.selected_labels]
        self.cancel()
        return self.drawing.apply_edit(segments, labels)

    def apply_rotation(self, angle, pivot=None):
        geometry = self.geometry()
        left, top, right, bottom = segment_bounds(geometry)
        pivot = pivot or ((left + right) / 2, (top + bottom) / 2)
        return self.apply_transformed(rotate_degrees([self.lines[index] for index in self.selected], angle, pivot),
                                      transform_labels(self.selected_texts(), angle, pivot))

    def rotated_move(self, turns=None):
        turns = self.move_turns if turns is None else turns
        left, top, right, bottom = segment_bounds(self.geometry(self.move_source, self.move_label_source))
        pivot = ((left + right) / 2, (top + bottom) / 2)
        return (rotate_degrees(self.move_source, turns * 90, pivot),
                transform_labels(self.move_label_source, turns * 90, pivot))

    def rotate(self):
        if not self.has_selection() or self.origin is not None:
            return False
        if self.moving:
            turns = (self.move_turns + 1) % 4
            rotated, labels = self.rotated_move(turns)
            left, top, right, bottom = segment_bounds(self.geometry(rotated, labels))
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
        self.move_turns = 0
        left, top, right, bottom = segment_bounds(self.geometry(self.move_source, self.move_label_source))
        self.move_anchor = (self.point(self.last_pointer) if self.last_pointer is not None
                            else QPointF((left + right) / 2, (top + bottom) / 2))
        if self.last_pointer is None:
            self.last_pointer = QPointF(self.view.mapFromScene(self.move_anchor))
        selected = set(self.selected)
        self.move_snapper = PlanSnapper([line for index, line in enumerate(self.lines) if index not in selected])
        self.clear_items()
        for index in self.selected:
            self.drawing.items[index].setOpacity(.25)
        for index in self.selected_labels:
            self.drawing.text.items[index].setOpacity(.25)
        self.refresh_snap()
        return True

    def update_move(self, position, bypass=False):
        source, labels = self.rotated_move()
        geometry = self.geometry(source, labels)
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
                self.view.grid_spacing_pixels() if self.drawing.tools.snap_button.isChecked() else None)
            x, y, self.drawing.snap_guides = result.x, result.y, result.guides
        self.move_preview = translate_segments(source, x - left, y - top)
        self.move_label_preview = transform_labels(labels, dx=x - left, dy=y - top)
        combined = self.geometry(self.move_preview, self.move_label_preview)
        if any(line["x1"] != line["x2"] and line["y1"] != line["y2"] for line in combined):
            snapped = self.drawing.snap_shape(combined, bypass, self.move_snapper)
            dx, dy = snapped[0]["x1"] - combined[0]["x1"], snapped[0]["y1"] - combined[0]["y1"]
            self.move_preview = translate_segments(self.move_preview, dx, dy)
            self.move_label_preview = transform_labels(self.move_label_preview, dx=dx, dy=dy)
            left, top, right, bottom = segment_bounds(snapped)
            x, y = left, top
            self.show_lines(self.move_preview, moving=True, labels=self.move_label_preview)
            self.drawing.show_snap_guides(QRectF(left, top, right - left, bottom - top))
            self.show_count(position)
            return
        self.show_lines(self.move_preview, moving=True, labels=self.move_label_preview)
        self.drawing.show_snap_guides(QRectF(x, y, right - left, bottom - top))
        self.show_count(position)

    def refresh_snap(self):
        if self.moving and self.last_pointer is not None:
            self.update_move(self.last_pointer)
