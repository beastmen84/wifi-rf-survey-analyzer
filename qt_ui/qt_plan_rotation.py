"""Tap R for a quarter turn; hold R and orbit the fixed pivot in 5° steps."""
import math
from copy import deepcopy

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QCursor, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsPathItem

from qt_ui.scaling import widget_px
from survey.plan_geometry import rotate_degrees, segment_bounds
from survey.plan_labels import label_geometry, labels_geometry, transform_labels
from survey.plan_label_rendering import label_item
from survey.plan_curves import curves_geometry, transform_curves
from survey.plan_curve_rendering import curve_item


def angle_readout(angle):
    positive = int(angle) % 360
    negative = positive - 360 if positive else 0
    return f"(+{positive}° / {negative}°)"


class PlanRotationController:
    def __init__(self, drawing):
        self.drawing, self.owner, self.view = drawing, drawing.owner, drawing.view
        self.active = self.dragged = False
        self.items, self.hidden, self.dimmed = [], [], []
        self.base = self.rotated = []
        self.angle = 0
        self.valid = True

    def reset_scene(self):
        self.items, self.hidden, self.dimmed = [], [], []
        self.active = False

    def begin(self):
        if self.active:
            return True
        d, tool = self.drawing, self.drawing.tools.active_tool
        self.hidden, self.dimmed = [], []
        self.label_base, self.line_base = [], []
        self.curve_base = []
        if tool == "rectangle" and d.pending_size and d.preview is not None:
            self.target, self.base = "rectangle", d.rectangle_geometry(d.preview.rect())
            position, hide = d.last_pointer, [d.preview]
        elif tool == "line" and d.line.pending_length is not None and d.line.preview is not None:
            self.target = "line"
            line = d.line.preview.line()
            self.base = [dict(x1=line.x1(), y1=line.y1(), x2=line.x2(), y2=line.y2(), color=d.tools.stroke_color.name())]
            position, hide = d.line.last_pointer, [d.line.preview]
        elif tool == "text" and d.text.pending is not None and d.text.preview is not None:
            self.target = "text"
            self.label_base = [deepcopy(d.text.pending)]
            self.base = label_geometry(d.text.pending)
            position, hide = d.text.last_pointer, list(d.text.preview_items)
        elif tool == "arc" and d.curve.pending is not None and d.curve.preview is not None:
            self.target = "curve"
            self.curve_base = transform_curves([d.curve.pending])
            self.base = curves_geometry(self.curve_base)
            position, hide = d.curve.last_pointer, [d.curve.preview]
        elif tool == "select" and d.selection.can_rotate() and d.selection.origin is None:
            s = d.selection
            self.target = "move" if s.moving else "selection"
            self.line_base = [dict(line) for line in (s.move_preview if s.moving else [s.lines[index] for index in s.selected])]
            self.label_base = deepcopy(s.move_label_preview if s.moving else s.selected_texts())
            self.curve_base = transform_curves(s.move_curve_preview if s.moving else s.selected_curve_shapes())
            self.base = self.line_base + labels_geometry(self.label_base) + curves_geometry(self.curve_base)
            position, hide = s.last_pointer, list(s.highlights) + list(d.text.preview_items)
            for index in s.selected:
                item = d.items[index]
                self.dimmed.append((item, item.opacity()))
                item.setOpacity(.25)
            for index in s.selected_labels:
                item = d.text.items[index]
                self.dimmed.append((item, item.opacity()))
                item.setOpacity(.25)
            for index in s.selected_curves:
                item = d.curve.items[index]
                self.dimmed.append((item, item.opacity()))
                item.setOpacity(.25)
        else:
            return False
        left, top, right, bottom = segment_bounds(self.base)
        self.pivot = ((left + right) / 2, (top + bottom) / 2)
        if position is None:
            current = self.view.viewport().mapFromGlobal(QCursor.pos())
            position = (QPointF(current) if self.view.viewport().rect().contains(current)
                        else QPointF(self.view.mapFromScene(QPointF(right + 20, (top + bottom) / 2))))
        self.position = self.initial_position = QPointF(position)
        self.reference = self.pointer_angle(position)
        self.angle, self.dragged, self.active = 0, False, True
        for item in hide:
            self.hidden.append((item, item.isVisible()))
            item.hide()
        d.clear_snap_guides()
        self.render()
        return True

    def pointer_angle(self, position):
        point = self.view.mapToScene(position.toPoint())
        dx, dy = point.x() - self.pivot[0], point.y() - self.pivot[1]
        zoom = max(1e-9, math.hypot(self.view.transform().m11(), self.view.transform().m12()))
        if math.hypot(dx, dy) * zoom < widget_px(self.owner, 12):
            return None
        return math.degrees(math.atan2(dy, dx))

    def move(self, position):
        self.position = QPointF(position)
        angle = self.pointer_angle(position)
        if angle is None:
            return
        if (position - self.initial_position).manhattanLength() < QApplication.startDragDistance() and not self.dragged:
            return
        self.dragged = True
        if self.reference is None:
            self.reference = angle
        difference = (angle - self.reference + 180) % 360 - 180
        self.angle = (math.floor(difference / 5 + .5) * 5) % 360
        self.render()

    def clear_items(self):
        for item in self.items:
            self.view.scene.removeItem(item)
        self.items = []

    def render(self):
        self.rotated = rotate_degrees(self.base, self.angle, self.pivot)
        rotated_curves = transform_curves(self.curve_base, self.angle, self.pivot)
        geometry = (rotate_degrees(self.line_base, self.angle, self.pivot)
                    + labels_geometry(transform_labels(self.label_base, self.angle, self.pivot))
                    + curves_geometry(rotated_curves)) if self.curve_base else self.rotated
        self.valid = self.drawing.selection.fits(geometry)
        self.clear_items()
        path = QPainterPath()
        visible_lines = rotate_degrees(self.line_base, self.angle, self.pivot) if self.curve_base else self.rotated
        for line in visible_lines:
            path.moveTo(line["x1"], line["y1"])
            path.lineTo(line["x2"], line["y2"])
        item = QGraphicsPathItem(path)
        pen = QPen(QColor("#0284c7" if self.valid else "#ef4444"), 2)
        pen.setCosmetic(True)
        pen.setStyle(Qt.PenStyle.DashLine)
        item.setPen(pen)
        self.items.append(item)
        for label in transform_labels(self.label_base, self.angle, self.pivot):
            self.items.append(label_item(label))
        for curve in rotated_curves:
            curved_item = curve_item(curve)
            curved_item.setPen(pen)
            self.items.append(curved_item)
        zoom = max(1e-9, math.hypot(self.view.transform().m11(), self.view.transform().m12()))
        radius = widget_px(self.owner, 5) / zoom
        cx, cy = self.pivot
        marker = QGraphicsEllipseItem(cx - radius, cy - radius, radius * 2, radius * 2)
        orange = QPen(QColor("#d97706"), 1.5)
        orange.setCosmetic(True)
        marker.setPen(orange)
        self.items.append(marker)
        pointer = self.view.mapToScene(self.position.toPoint())
        guide = QGraphicsLineItem(cx, cy, pointer.x(), pointer.y())
        orange.setStyle(Qt.PenStyle.DotLine)
        guide.setPen(orange)
        self.items.append(guide)
        for item in self.items:
            item.setZValue(12)
            item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.view.scene.addItem(item)
        text = self.owner.tr("rotation_angle") + "\n" + angle_readout(self.angle)
        if not self.valid:
            text += "\n" + self.owner.tr("rotation_outside_hint")
        self.drawing.show_measurement(text, self.position)

    def cancel(self):
        existed = self.active
        self.active = False
        self.clear_items()
        for item, visible in self.hidden:
            item.setVisible(visible)
        for item, opacity in self.dimmed:
            item.setOpacity(opacity)
        self.hidden, self.dimmed = [], []
        if existed:
            self.drawing.measurement.hide()
        return existed

    def finish(self):
        target, angle, dragged, valid = self.target, self.angle, self.dragged, self.valid
        result, position = self.rotated, self.position
        self.cancel()
        d = self.drawing
        if not dragged:
            if target == "rectangle":
                d.rotate_preview()
            elif target == "line":
                d.line.rotate()
            elif target == "text":
                d.text.rotate()
            elif target == "curve":
                d.curve.rotate()
            else:
                d.selection.rotate()
            return
        if not valid:
            self.owner.status.showMessage(self.owner.tr("design_rotation_outside"))
            return
        pointer = self.view.mapToScene(position.toPoint())
        if target == "rectangle":
            d.pending_angle = (d.pending_angle + angle) % 360
            left, top, right, bottom = segment_bounds(result)
            d.placement_offset = QPointF(left, top) - pointer
            d.last_pointer = position
            d.show_preview(QRectF(left, top, right - left, bottom - top), position)
        elif target == "line":
            d.line.angle = (d.line.angle + angle) % 360
            line = result[0]
            d.line.placement_offset = QPointF(line["x1"], line["y1"]) - pointer
            d.line.last_pointer = position
            d.line.show_preview(QLineF(line["x1"], line["y1"], line["x2"], line["y2"]), position)
        elif target == "move":
            s = d.selection
            lines = rotate_degrees(self.line_base, angle, self.pivot)
            labels = transform_labels(self.label_base, angle, self.pivot)
            curves = transform_curves(self.curve_base, angle, self.pivot)
            s.move_source, s.move_preview, s.move_turns = lines, lines, 0
            s.move_label_source, s.move_label_preview = labels, labels
            s.move_curve_source, s.move_curve_preview = curves, curves
            s.move_anchor, s.last_pointer = pointer, position
            s.show_lines(lines, moving=True, labels=labels, curves=curves)
            s.show_count(position)
        elif target == "text":
            label = transform_labels(self.label_base, angle, self.pivot)[0]
            d.text.pending = label
            d.text.offset = QPointF(label["x"], label["y"]) - pointer
            d.text.last_pointer = position
            d.text.show_labels([label])
        elif target == "curve":
            d.curve.pending = transform_curves(self.curve_base, angle, self.pivot)[0]
            d.curve.anchor = pointer
            d.curve.last_pointer = position
            d.curve.show_preview(d.curve.pending, position)
        elif angle:
            d.selection.apply_rotation(angle, self.pivot)
