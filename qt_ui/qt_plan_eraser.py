"""Preview and commit whole-segment erasing, sharing the drawing undo history."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QGraphicsPathItem, QGraphicsRectItem

from qt_ui.scaling import widget_px
from survey.plan_erasing import intersecting_segments, nearest_segment
from survey.curve_erasing import intersecting_curves, nearest_curve
from survey.plan_curve_rendering import curve_path


class PlanEraserController:
    def __init__(self, drawing):
        self.drawing = drawing
        self.view, self.owner = drawing.view, drawing.owner
        self.origin = self.press_position = None
        self.dragged = False
        self.targets = ()
        self.highlights = []
        self.area = None
        self.lines = []

    def set_segments(self, lines):
        self.cancel()
        self.lines = lines

    def reset_scene(self):
        # scene.clear() has already destroyed the C++ items.
        self.highlights = []
        self.area = None
        self.cancel()

    def cancel(self):
        active = self.origin is not None
        self.origin = self.press_position = None
        self.dragged = False
        self.clear_feedback()
        return active

    def clear_feedback(self):
        for item in self.highlights:
            self.view.scene.removeItem(item)
        self.highlights = []
        self.targets = ()
        if self.area is not None:
            self.view.scene.removeItem(self.area)
            self.area = None
        self.drawing.measurement.hide()

    def hide_preview(self):
        for item in self.highlights:
            item.hide()
        if self.area is not None:
            self.area.hide()
        self.drawing.measurement.hide()

    def point(self, event):
        point = self.view.mapToScene(event.position().toPoint())
        bounds = self.view.scene.sceneRect()
        return QPointF(min(max(point.x(), bounds.left()), bounds.right()),
                       min(max(point.y(), bounds.top()), bounds.bottom()))

    def pick(self, point):
        zoom = max(1e-9, math.hypot(self.view.transform().m11(), self.view.transform().m12()))
        # A constant screen-space margin plus the visible stroke's half width.
        index = nearest_segment(self.lines, point.x(), point.y(),
                                widget_px(self.owner, 6) / zoom + 1)
        return () if index is None else (index,)

    def pick_curves(self, point):
        zoom = max(1e-9, math.hypot(self.view.transform().m11(), self.view.transform().m12()))
        index = nearest_curve(self.drawing.curves(), point.x(), point.y(), widget_px(self.owner, 6) / zoom + 1)
        return () if index is None else (index,)

    def pick_all(self, point):
        lines = self.pick(point)
        return lines if lines else tuple(len(self.lines) + index for index in self.pick_curves(point))

    def show_targets(self, targets, position, rect=None):
        if targets != self.targets:
            for item in self.highlights:
                self.view.scene.removeItem(item)
            self.highlights = []
            self.targets = targets
            path = QPainterPath()
            for index in targets:
                if index >= len(self.lines):
                    path.addPath(curve_path(self.drawing.curves()[index - len(self.lines)]))
                    continue
                line = self.lines[index]
                path.moveTo(line["x1"], line["y1"])
                path.lineTo(line["x2"], line["y2"])
            # Two path items cover any selection size, without an item per side.
            if targets:
                for color, width in ((QColor(239, 68, 68, 90), 8), (QColor("#ef4444"), 2)):
                    item = QGraphicsPathItem(path)
                    pen = QPen(color, widget_px(self.owner, width))
                    pen.setCosmetic(True)
                    item.setPen(pen)
                    item.setZValue(9)
                    item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                    self.view.scene.addItem(item)
                    self.highlights.append(item)
        for item in self.highlights:
            item.show()
        if rect is not None:
            if self.area is None:
                self.area = QGraphicsRectItem()
                pen = QPen(QColor("#ef4444"), 1, Qt.PenStyle.DashLine)
                pen.setCosmetic(True)
                self.area.setPen(pen)
                self.area.setBrush(QColor(239, 68, 68, 28))
                self.area.setZValue(8)
                self.area.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                self.view.scene.addItem(self.area)
            self.area.setRect(rect)
            self.area.show()
        if targets or rect is not None:
            key = "eraser_one_segment" if len(targets) == 1 else "eraser_many_segments"
            text = self.owner.tr(key).format(count=len(targets))
            action = "eraser_release" if self.origin is not None else "eraser_click"
            self.drawing.show_measurement(text + "\n" + self.owner.tr(action), position)
        else:
            self.drawing.measurement.hide()

    def press(self, event):
        if self.view.scene.sceneRect().contains(self.view.mapToScene(event.position().toPoint())):
            self.origin = self.point(event)
            self.press_position = event.position()
            self.dragged = False
            self.show_targets(self.pick_all(self.origin), event.position())
        return True

    def move(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.hide_preview()
            return False  # QGraphicsView still handles hand-drag panning.
        point = self.point(event)
        if self.origin is not None and event.buttons() & Qt.MouseButton.RightButton:
            self.dragged |= (event.position() - self.press_position).manhattanLength() >= QApplication.startDragDistance()
            if self.dragged:
                self.show_area(point, event.position())
            return True
        if self.view.scene.sceneRect().contains(self.view.mapToScene(event.position().toPoint())):
            self.show_targets(self.pick_all(point), event.position())
        else:
            self.clear_feedback()
        return False

    def show_area(self, point, position):
        rect = QRectF(self.origin, point).normalized()
        targets = intersecting_segments(self.lines, rect.left(), rect.top(), rect.right(), rect.bottom())
        targets += tuple(len(self.lines) + index for index in intersecting_curves(self.drawing.curves(), rect.left(), rect.top(), rect.right(), rect.bottom()))
        self.show_targets(targets, position, rect)

    def release(self, event):
        if self.origin is None:
            return True
        if self.dragged or (event.position() - self.press_position).manhattanLength() >= QApplication.startDragDistance():
            self.show_area(self.point(event), event.position())
        targets = set(self.targets)
        lines = self.drawing.segments() or []
        curves = self.drawing.curves()
        self.cancel()
        if targets:
            self.drawing.apply_edit([line for index, line in enumerate(lines) if index not in targets],
                curves=[curve for index, curve in enumerate(curves) if len(lines) + index not in targets])
        return True
