"""Radius circles and repeatable chord/sagitta arcs, with staged right gestures."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox,
                              QDoubleSpinBox, QFormLayout, QLabel, QVBoxLayout)

from app_core.units import distance_unit_label, display_units_to_meters, meters_to_display_units
from qt_ui.scaling import widget_px
from survey.plan_curves import curve_bounds, curves_geometry, transform_curves, validate_curves
from survey.plan_curve_rendering import curve_item, curve_path


class CurveSizeDialog(QDialog):
    def __init__(self, owner, kind, bounds, density, previous=None):
        super().__init__(owner)
        self.owner, self.kind, self.density = owner, kind, density
        self.setWindowTitle(owner.tr("curve_" + kind + "_title"))
        self.setMinimumWidth(widget_px(owner, 440))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(widget_px(owner, 20) for _ in range(4)))
        layout.setSpacing(widget_px(owner, 12))
        hint = QLabel(owner.tr("curve_" + kind + "_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        form = QFormLayout()
        self.spins = []
        for index, key in enumerate(("curve_radius",) if kind == "circle" else ("curve_chord", "curve_sagitta")):
            spin = QDoubleSpinBox()
            spin.setObjectName("blankPlanDimension")
            spin.setDecimals(2)
            spin.setSingleStep(.01)
            maximum = min(bounds.width(), bounds.height()) / 2 if kind == "circle" else math.hypot(bounds.width(), bounds.height())
            maximum = meters_to_display_units(maximum / density, owner.measurement_system)
            spin.setRange(.01, max(.01, math.floor(maximum * 100) / 100))
            spin.setSuffix(" " + distance_unit_label(owner.measurement_system))
            spin.setMinimumHeight(widget_px(owner, 36))
            spin.setKeyboardTracking(False)
            spin.setValue(meters_to_display_units(abs(previous[index]) / density, owner.measurement_system)
                          if previous else (2 if kind == "circle" else (4, 1)[index]))
            self.spins.append(spin)
            form.addRow(owner.tr(key), spin)
        self.side = QComboBox()
        if kind == "arc":
            self.side.addItems([owner.tr("curve_side_positive"), owner.tr("curve_side_negative")])
            self.side.setCurrentIndex(1 if previous and previous[1] < 0 else 0)
            form.addRow(owner.tr("curve_side"), self.side)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(owner.tr("cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def dimensions(self):
        values = [display_units_to_meters(spin.value(), self.owner.measurement_system) * self.density for spin in self.spins]
        if self.kind == "arc" and self.side.currentIndex():
            values[1] *= -1
        return tuple(values)


class CurveDesignController:
    def __init__(self, drawing):
        self.drawing, self.owner, self.view = drawing, drawing.owner, drawing.view
        self.items, self.preview = [], None
        self.pending = self.current = None
        self.placement_source = None
        self.origin = self.press_position = self.last_pointer = self.anchor = None
        self.chord = None
        self.dragged = self.consume_release = self.dialog_open = False
        self.last_dimensions = {}

    def reset_scene(self):
        self.items, self.preview = [], None
        self.cancel()
        self.last_dimensions.clear()

    def cancel(self):
        existed = self.pending is not None or self.origin is not None or self.chord is not None
        self.clear_preview()
        self.pending = self.current = self.origin = self.press_position = self.last_pointer = self.anchor = self.chord = None
        self.placement_source = None
        self.dragged = self.consume_release = False
        self.drawing.clear_snap_guides()
        self.drawing.measurement.hide()
        return existed

    def clear_preview(self):
        if self.preview is not None:
            self.view.scene.removeItem(self.preview)
            self.preview = None

    def hide_preview(self):
        if self.preview is not None:
            self.preview.hide()

    def redraw(self, curves):
        for item in self.items:
            self.view.scene.removeItem(item)
        self.items = []
        for curve in curves:
            item = curve_item(curve)
            self.view.scene.addItem(item)
            self.items.append(item)

    def point(self, position):
        point = self.view.mapToScene(position.toPoint())
        bounds = self.view.scene.sceneRect()
        return QPointF(min(max(point.x(), bounds.left()), bounds.right()), min(max(point.y(), bounds.top()), bounds.bottom()))

    def fits(self, curve):
        return self.drawing.selection.fits(curves_geometry([curve]))

    def show_preview(self, curve, position):
        self.current = curve
        if self.preview is None:
            self.preview = curve_item(curve)
            self.preview.setZValue(8)
            self.view.scene.addItem(self.preview)
        path = curve_path(curve)
        if self.chord is not None:
            path.moveTo(curve["x1"], curve["y1"])
            path.lineTo(curve["x2"], curve["y2"])
            path.moveTo((curve["x1"] + curve["x2"]) / 2, (curve["y1"] + curve["y2"]) / 2)
            from survey.plan_curves import point_at
            path.lineTo(*point_at(curve, .5))
        self.preview.setPath(path)
        self.preview.setPen(QPen(self.drawing.tools.stroke_color if self.fits(curve) else QColor("#ef4444"), 2, Qt.PenStyle.DashLine))
        self.preview.show()
        self.show_measurements(curve, position)
        left, top, right, bottom = curve_bounds(curve)
        self.drawing.show_snap_guides(QRectF(left, top, right - left, bottom - top))

    def show_measurements(self, curve, position):
        values = (("curve_radius", curve["radius"]),) if curve["kind"] == "circle" else (
            ("curve_chord", math.hypot(curve["x2"] - curve["x1"], curve["y2"] - curve["y1"])), ("curve_sagitta", curve["height"]))
        unit = distance_unit_label(self.owner.measurement_system)
        text = "\n".join(self.owner.tr(key) + ": " + self.drawing.measurement.locale().toString(
            meters_to_display_units(value / self.owner.get_px_per_meter(), self.owner.measurement_system), "f", 2) + " " + unit
            for key, value in values)
        if self.chord is not None:
            text += "\n" + self.owner.tr("curve_pull_hint")
            if any(guide.kind == "corner" for guide in self.drawing.snap_guides):
                text += "\n" + self.owner.tr("design_snap_corner")
            elif any(guide.kind == "grid" for guide in self.drawing.snap_guides):
                text += "\n" + self.owner.tr("design_snap_grid")
        elif self.pending is not None and curve["kind"] == "arc":
            text += "\n" + self.owner.tr("design_rotate_hint")
        if (curve["kind"] == "circle" or curve["height"]) and not self.fits(curve):
            text += "\n" + self.owner.tr("rotation_outside_hint")
        self.drawing.show_measurement(text, position)

    def begin_placement(self, kind, dimensions, anchor=None):
        self.cancel()
        if (kind not in ("circle", "arc") or len(dimensions) != (1 if kind == "circle" else 2)
                or not all(math.isfinite(value) for value in dimensions) or dimensions[0] <= 0
                or (kind == "arc" and dimensions[1] == 0)):
            raise ValueError("Invalid curve dimensions")
        color = self.drawing.tools.stroke_color.name()
        if kind == "circle":
            curve = dict(kind=kind, cx=0, cy=0, radius=dimensions[0], phase=0, color=color)
        else:
            curve = dict(kind=kind, x1=0, y1=0, x2=dimensions[0], y2=0, height=dimensions[1], color=color)
        point = anchor if anchor is not None else self.view.scene.sceneRect().center()
        curve = transform_curves([curve], dx=point.x(), dy=point.y())[0]
        left, top, right, bottom = curve_bounds(curve)
        bounds = self.view.scene.sceneRect()
        if right - left > bounds.width() or bottom - top > bounds.height():
            self.owner.status.showMessage(self.owner.tr("design_rotation_outside"))
            return False
        self.last_dimensions[kind] = tuple(dimensions)
        self.rebase_pending(curve, QPointF(self.view.mapFromScene(point)))
        self.update_pending(self.last_pointer)
        return True

    def rebase_pending(self, curve, position):
        self.pending = dict(curve)
        self.placement_source = dict(curve)
        self.last_pointer = QPointF(position)
        self.anchor = self.point(position)

    def update_pending(self, position, bypass=False):
        point = self.point(position)
        # Always translate an immutable placement source. Feeding each snapped
        # result into the next event traps slow cursor motion on the same grid.
        curve = transform_curves([self.placement_source], dx=point.x() - self.anchor.x(), dy=point.y() - self.anchor.y())[0]
        proxy = curves_geometry([curve])
        snapped = self.drawing.snap_shape(proxy, bypass)
        dx, dy = snapped[0]["x1"] - proxy[0]["x1"], snapped[0]["y1"] - proxy[0]["y1"]
        self.pending = transform_curves([curve], dx=dx, dy=dy)[0]
        self.show_preview(self.pending, position)

    def rotate(self):
        if self.pending is None or self.pending["kind"] == "circle":
            return False
        left, top, right, bottom = curve_bounds(self.pending)
        curve = transform_curves([self.pending], 90, ((left + right) / 2, (top + bottom) / 2))[0]
        if self.fits(curve):
            self.rebase_pending(curve, self.last_pointer)
            self.drawing.clear_snap_guides()
            self.show_preview(curve, self.last_pointer)
        else:
            self.owner.status.showMessage(self.owner.tr("design_rotation_outside"))
        return True

    def refresh_snap(self):
        if self.pending is not None and self.last_pointer is not None:
            self.update_pending(self.last_pointer)
        elif self.chord is not None and self.last_pointer is not None:
            self.pull(self.last_pointer)
        elif self.origin is not None and self.dragged and self.last_pointer is not None:
            curve = self.drag_geometry(self.last_pointer)
            if curve is not None:
                if curve["kind"] == "circle":
                    self.show_preview(curve, self.last_pointer)
                else:
                    self.show_chord(curve, self.last_pointer)

    def drag_geometry(self, position, bypass=False):
        point = self.point(position)
        result = (self.drawing.snap_endpoint(point, self.origin, bypass=bypass)
                  if self.drawing.tools.active_tool == "arc" else self.drawing.snap_position(point, bypass=bypass))
        self.drawing.snap_guides = result.guides
        point = QPointF(result.x, result.y)
        color = self.drawing.tools.stroke_color.name()
        if self.drawing.tools.active_tool == "circle":
            bounds = self.view.scene.sceneRect()
            radius = min(math.hypot(point.x() - self.origin.x(), point.y() - self.origin.y()),
                         self.origin.x() - bounds.left(), bounds.right() - self.origin.x(),
                         self.origin.y() - bounds.top(), bounds.bottom() - self.origin.y())
            return dict(kind="circle", cx=self.origin.x(), cy=self.origin.y(), radius=radius, phase=0, color=color) if radius > 1e-7 else None
        return dict(kind="arc", x1=self.origin.x(), y1=self.origin.y(), x2=point.x(), y2=point.y(),
                    height=0, color=color) if math.hypot(point.x() - self.origin.x(), point.y() - self.origin.y()) > 1e-7 else None

    def pull(self, position, bypass=False):
        curve = dict(self.chord)
        dx, dy = curve["x2"] - curve["x1"], curve["y2"] - curve["y1"]
        length = math.hypot(dx, dy)
        point = self.view.mapToScene(position.toPoint())
        h = ((point.y() - (curve["y1"] + curve["y2"]) / 2) * dx
             - (point.x() - (curve["x1"] + curve["x2"]) / 2) * dy) / length
        self.drawing.clear_snap_guides()
        if not bypass and not self.drawing.snap_bypass:
            bounds = self.view.scene.sceneRect()
            zoom = max(1e-9, math.hypot(self.view.transform().m11(), self.view.transform().m12()))
            snapped = self.drawing.snapper.snap_arc_height(curve, point.x(), point.y(),
                (bounds.left(), bounds.top(), bounds.right(), bounds.bottom()), widget_px(self.owner, 10) / zoom,
                self.view.grid_spacing_pixels() if self.drawing.tools.snap_button.isChecked() else None)
            if snapped is not None:
                h, guide = snapped
                self.drawing.snap_guides = (guide,)
        if abs(h) < 1e-7:
            self.current = None
            self.show_chord(curve, position)
            return
        curve["height"] = h
        self.show_preview(curve, position)

    def show_chord(self, curve, position):
        if self.preview is None:
            from PySide6.QtWidgets import QGraphicsPathItem
            self.preview = QGraphicsPathItem()
            self.preview.setZValue(8)
            self.preview.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.view.scene.addItem(self.preview)
        path = QPainterPath()
        path.moveTo(curve["x1"], curve["y1"])
        path.lineTo(curve["x2"], curve["y2"])
        self.preview.setPath(path)
        self.preview.setPen(QPen(self.drawing.tools.stroke_color, 2, Qt.PenStyle.DashLine))
        self.preview.show()
        self.drawing.show_snap_guides(QRectF(QPointF(curve["x1"], curve["y1"]), QPointF(curve["x2"], curve["y2"])).normalized())
        self.show_measurements(curve, position)

    def press(self, event):
        self.last_pointer = event.position()
        point = self.view.mapToScene(event.position().toPoint())
        bypass = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        if self.chord is not None:
            self.pull(event.position(), bypass)
            if self.current is not None and self.commit(self.current):
                self.cancel()
            self.consume_release = True
        elif self.pending is not None:
            if self.view.scene.sceneRect().contains(point):
                self.update_pending(event.position(), bypass)
                if self.commit(self.pending):
                    self.cancel()
            self.consume_release = True
        elif self.view.scene.sceneRect().contains(point):
            result = self.drawing.snap_position(point, bypass=bypass)
            self.origin = QPointF(result.x, result.y)
            self.press_position, self.dragged = event.position(), False
        return True

    def move(self, event):
        self.drawing.axis_lock = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        self.last_pointer = event.position()
        bypass = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        if self.pending is not None:
            if self.view.scene.sceneRect().contains(self.view.mapToScene(event.position().toPoint())):
                self.update_pending(event.position(), bypass)
            else:
                self.drawing.hide_preview()
        elif self.chord is not None:
            self.pull(event.position(), bypass)
        elif self.origin is not None and event.buttons() & Qt.MouseButton.RightButton:
            self.dragged |= (event.position() - self.press_position).manhattanLength() >= QApplication.startDragDistance()
            if self.dragged:
                curve = self.drag_geometry(event.position(), bypass)
                if curve is not None:
                    if curve["kind"] == "circle":
                        self.show_preview(curve, event.position())
                    else:
                        self.show_chord(curve, event.position())
            return True
        return False

    def release(self, event):
        self.drawing.axis_lock = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if self.consume_release:
            self.consume_release = False
            return True
        if self.origin is None:
            return True
        if self.dragged or (event.position() - self.press_position).manhattanLength() >= QApplication.startDragDistance():
            curve = self.drag_geometry(event.position(), bool(event.modifiers() & Qt.KeyboardModifier.AltModifier))
            if curve is not None and curve["kind"] == "arc":
                self.origin = self.press_position = None
                self.chord = curve
                self.pull(event.position(), bool(event.modifiers() & Qt.KeyboardModifier.AltModifier))
            else:
                if curve is not None:
                    self.commit(curve)
                self.cancel()
        else:
            kind, anchor, session, pixmap = self.drawing.tools.active_tool, self.origin, self.owner.session, self.view.pixmap_item
            self.cancel()
            dialog = CurveSizeDialog(self.owner, kind, self.view.scene.sceneRect(), self.owner.get_px_per_meter(), self.last_dimensions.get(kind))
            self.dialog_open = True
            try:
                if (dialog.exec() == QDialog.DialogCode.Accepted and self.drawing.tools.open
                        and self.owner.session is session and self.view.pixmap_item is pixmap
                        and self.drawing.tools.active_tool == kind):
                    self.begin_placement(kind, dialog.dimensions(), anchor)
            finally:
                self.dialog_open = False
                dialog.deleteLater()
        return True

    def commit(self, curve):
        curve = dict(curve, color=self.drawing.tools.stroke_color.name())
        if not self.fits(curve):
            self.owner.status.showMessage(self.owner.tr("design_rotation_outside"))
            return False
        try:
            curve = validate_curves([curve])[0]
        except ValueError:
            return False
        from qt_ui.qt_wall_sides import place_structure
        changed = place_structure(self.drawing, curves=[curve])
        if changed:
            self.last_dimensions[curve["kind"]] = (curve["radius"],) if curve["kind"] == "circle" else (
                math.hypot(curve["x2"] - curve["x1"], curve["y2"] - curve["y1"]), curve["height"])
        return changed

    def edit(self, index):
        if self.dialog_open or self.drawing.rotation.active or self.drawing.selection.moving:
            return False
        curve = dict(self.drawing.curves()[index])
        kind = curve["kind"]
        dimensions = (curve["radius"],) if kind == "circle" else (
            math.hypot(curve["x2"] - curve["x1"], curve["y2"] - curve["y1"]), curve["height"])
        dialog = CurveSizeDialog(self.owner, kind, self.view.scene.sceneRect(), self.owner.get_px_per_meter(), dimensions)
        dialog.findChild(QLabel).setText(self.owner.tr("curve_edit_hint"))
        session, pixmap = self.owner.session, self.view.pixmap_item
        state = self.drawing.snapshot()
        self.dialog_open = True
        try:
            if (dialog.exec() != QDialog.DialogCode.Accepted or self.owner.session is not session
                    or self.view.pixmap_item is not pixmap or not self.drawing.tools.open
                    or self.drawing.snapshot() != state):
                return False
            values = dialog.dimensions()
            if kind == "circle":
                curve["radius"] = values[0]
            else:
                length, height = values
                old_length = dimensions[0]
                ux, uy = (curve["x2"] - curve["x1"]) / old_length, (curve["y2"] - curve["y1"]) / old_length
                mx, my = (curve["x1"] + curve["x2"]) / 2, (curve["y1"] + curve["y2"]) / 2
                curve.update(x1=mx - ux * length / 2, y1=my - uy * length / 2,
                             x2=mx + ux * length / 2, y2=my + uy * length / 2, height=height)
            self.drawing.selection.set_selected((), (), (index,))
            changed = self.drawing.selection.apply_transformed([], [], [curve])
            if changed:
                self.last_dimensions[kind] = tuple(values)
            return changed
        finally:
            self.dialog_open = False
            dialog.deleteLater()
