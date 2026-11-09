"""Free-angle line drawing, exact length placement and rotation previews."""
import math

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QDoubleSpinBox,
                              QFormLayout, QGraphicsLineItem, QLabel, QVBoxLayout)

from app_core.units import distance_unit_label, display_units_to_meters, meters_to_display_units
from qt_ui.scaling import widget_px
from survey.plan_geometry import rotate_degrees, segment_bounds


class LineSizeDialog(QDialog):
    def __init__(self, owner, bounds, density, previous=None):
        super().__init__(owner)
        self.owner, self.density = owner, density
        self.setWindowTitle(owner.tr("line_size_title"))
        self.setMinimumWidth(widget_px(owner, 400))
        layout = QVBoxLayout(self)
        hint = QLabel(owner.tr("line_size_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.length_spin = QDoubleSpinBox()
        self.length_spin.setObjectName("blankPlanDimension")
        self.length_spin.setDecimals(2)
        self.length_spin.setSingleStep(.01)
        self.length_spin.setRange(.01, math.floor(meters_to_display_units(max(bounds.width(), bounds.height()) / density,
                                                                        owner.measurement_system) * 100) / 100)
        self.length_spin.setSuffix(" " + distance_unit_label(owner.measurement_system))
        self.length_spin.setMinimumHeight(widget_px(owner, 36))
        self.length_spin.setKeyboardTracking(False)
        self.length_spin.setValue(meters_to_display_units(previous / density, owner.measurement_system) if previous else 3)
        form = QFormLayout()
        form.addRow(owner.tr("line_length"), self.length_spin)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(owner.tr("cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def length(self):
        return display_units_to_meters(self.length_spin.value(), self.owner.measurement_system) * self.density


class LineDesignController:
    def __init__(self, drawing):
        self.drawing, self.owner, self.view = drawing, drawing.owner, drawing.view
        self.origin = self.press_position = self.last_pointer = None
        self.pending_length = self.last_length = None
        self.turns = 0
        self.placement_offset = QPointF()
        self.preview = None
        self.dragged = self.consume_release = False
        self.wall_index = None
        self.raw_placement = False

    def reset_scene(self):
        self.preview = None
        self.wall_index = None
        self.cancel()
        self.last_length = None

    @property
    def turns(self):
        return self.angle / 90

    @turns.setter
    def turns(self, turns):
        self.angle = (turns * 90) % 360

    def cancel(self):
        active = self.origin is not None or self.pending_length is not None
        if self.preview is not None:
            self.view.scene.removeItem(self.preview)
            self.preview = None
        self.origin = self.press_position = self.last_pointer = self.pending_length = None
        self.placement_offset = QPointF()
        self.dragged = self.consume_release = False
        self.drawing.clear_snap_guides()
        self.drawing.measurement.hide()
        return active

    def hide_preview(self):
        self.last_pointer = None
        if self.preview is not None:
            self.preview.hide()

    def geometry(self, point, bypass=False):
        self.raw_placement = bypass or self.drawing.snap_bypass
        if self.pending_length is not None:
            point = point + self.placement_offset
            local = rotate_degrees([dict(x1=0, y1=0, x2=self.pending_length, y2=0, color="#000000")], self.angle, (0, 0))[0]
            dx, dy = local["x2"], local["y2"]
            if self.angle % 90:
                lines = self.drawing.snap_shape([dict(local, x1=point.x(), y1=point.y(),
                    x2=point.x() + dx, y2=point.y() + dy)], bypass)
                line = lines[0]
                return self.compensate(QLineF(line["x1"], line["y1"], line["x2"], line["y2"]))
            result = self.drawing.snap_position(QPointF(point.x() + min(0, dx), point.y() + min(0, dy)),
                                                 abs(dx), abs(dy), bypass)
            self.drawing.snap_guides = result.guides
            anchor = QPointF(result.x - min(0, dx), result.y - min(0, dy))
            return self.compensate(QLineF(anchor, anchor + QPointF(dx, dy)))
        result = self.drawing.snap_endpoint(point, self.origin, bypass=bypass)
        self.drawing.snap_guides = result.guides
        return QLineF(self.origin, QPointF(result.x, result.y))

    def attachments(self):
        if self.wall_index is None:
            from survey.wall_attachments import WallAttachmentIndex
            self.wall_index = WallAttachmentIndex(layer['drawing'] for layer in
                self.drawing.layer_document()['layers'] if layer['visible'])
        return self.wall_index

    def compensate(self, line):
        if self.raw_placement or line.length() == 0:
            return line
        before,after = self.attachments().clear_ends((line.x1(),line.y1()),(line.x2(),line.y2()))
        direction = (line.p2()-line.p1())/line.length()
        # Keep the snapped reference endpoint, extending only the free end.
        if before:
            return QLineF(line.p1(),line.p2()+direction*before)
        if after:
            return QLineF(line.p1()-direction*after,line.p2())
        return line

    def measured_line(self, line):
        if self.raw_placement or line.length() == 0:
            return line
        before,after = self.attachments().clear_ends((line.x1(),line.y1()),(line.x2(),line.y2()))
        direction = (line.p2()-line.p1())/line.length()
        start = min(before,line.length())
        end = max(start,line.length()-after)
        return QLineF(line.p1()+direction*start,line.p1()+direction*end)

    def show_preview(self, line, position):
        if self.preview is None:
            self.preview = QGraphicsLineItem()
            self.preview.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.preview.setZValue(8)
            self.view.scene.addItem(self.preview)
        measured = self.measured_line(line)
        self.preview.setLine(measured)
        bounds = self.view.scene.sceneRect()
        valid = (bounds.contains(line.p1()) and bounds.contains(line.p2())
                 and (self.pending_length is None or abs(measured.length()-self.pending_length)<=1e-5))
        self.preview.setPen(QPen(self.drawing.tools.stroke_color if valid else QColor('#ef4444'), 2, Qt.PenStyle.DashLine))
        self.preview.show()
        self.drawing.show_snap_guides(QRectF(line.p1(), line.p2()).normalized())
        length = meters_to_display_units(measured.length() / self.owner.get_px_per_meter(), self.owner.measurement_system)
        text = self.drawing.measurement.locale().toString(length, "f", 2) + " " + distance_unit_label(self.owner.measurement_system)
        if self.pending_length is not None:
            text += "\n" + self.owner.tr("design_rotate_hint")
            if not valid:
                text += '\n'+self.owner.tr('line_clear_length_invalid')
        self.drawing.show_measurement(text, position)

    def begin_placement(self, length, anchor=None):
        bounds = self.view.scene.sceneRect()
        if not math.isfinite(length) or not 0 < length <= max(bounds.width(), bounds.height()):
            raise ValueError("Line does not fit the sheet")
        self.cancel()
        self.pending_length = self.last_length = length
        local = rotate_degrees([dict(x1=0, y1=0, x2=length, y2=0, color="#000000")], self.angle)
        left, top, right, bottom = segment_bounds(local)
        if right - left > bounds.width() or bottom - top > bounds.height():
            self.turns = 0 if length <= bounds.width() else 1
        point = anchor if anchor is not None else bounds.center()
        self.last_pointer = QPointF(self.view.mapFromScene(point))
        self.show_preview(self.geometry(point), self.last_pointer)

    def rotate(self):
        if self.pending_length is None:
            return False
        bounds = self.view.scene.sceneRect()
        local = rotate_degrees([dict(x1=0, y1=0, x2=self.pending_length, y2=0, color="#000000")], self.angle + 90)
        left, top, right, bottom = segment_bounds(local)
        if right - left > bounds.width() or bottom - top > bounds.height():
            self.owner.status.showMessage(self.owner.tr("design_rotation_outside"))
            return True
        self.turns = (self.turns + 1) % 4
        self.refresh_snap()
        return True

    def refresh_snap(self):
        if self.last_pointer is not None and (self.pending_length is not None or self.dragged):
            self.show_preview(self.geometry(self.view.mapToScene(self.last_pointer.toPoint())), self.last_pointer)

    def press(self, event):
        point = self.view.mapToScene(event.position().toPoint())
        self.last_pointer = event.position()
        bypass = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        if self.pending_length is not None:
            if self.view.scene.sceneRect().contains(point):
                self.commit(self.geometry(point, bypass))
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
        point = self.view.mapToScene(event.position().toPoint())
        bypass = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
        if self.pending_length is not None:
            if self.view.scene.sceneRect().contains(point):
                self.show_preview(self.geometry(point, bypass), event.position())
            else:
                self.drawing.hide_preview()
        if self.origin is not None and event.buttons() & Qt.MouseButton.RightButton:
            self.dragged |= (event.position() - self.press_position).manhattanLength() >= QApplication.startDragDistance()
            if self.dragged:
                self.show_preview(self.geometry(point, bypass), event.position())
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
            self.commit(self.geometry(self.view.mapToScene(event.position().toPoint()),
                                      bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)))
            self.cancel()
        else:
            anchor = self.origin
            self.cancel()
            dialog = LineSizeDialog(self.owner, self.view.scene.sceneRect(), self.owner.get_px_per_meter(), self.last_length)
            try:
                if dialog.exec() == QDialog.DialogCode.Accepted and self.drawing.tools.open:
                    self.begin_placement(dialog.length(), anchor)
            finally:
                dialog.deleteLater()
        return True

    def commit(self, line):
        bounds = self.view.scene.sceneRect()
        if (not all(math.isfinite(value) for value in (line.x1(), line.y1(), line.x2(), line.y2()))
                or not bounds.contains(line.p1()) or not bounds.contains(line.p2())):
            if self.pending_length is not None:
                self.owner.status.showMessage(self.owner.tr('line_clear_length_invalid'))
                return False
            raise ValueError("Line is outside the sheet")
        if line.length() > 0:
            if self.pending_length is not None and abs(self.measured_line(line).length()-self.pending_length)>1e-5:
                self.owner.status.showMessage(self.owner.tr('line_clear_length_invalid'))
                return False
            segment = dict(x1=line.x1(), y1=line.y1(), x2=line.x2(), y2=line.y2(),
                           color=self.drawing.tools.stroke_color.name())
            from qt_ui.qt_wall_sides import place_structure
            return place_structure(self.drawing, lines=[segment])
