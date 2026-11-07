"""Immutable clean plan paths, painted at the destination's actual resolution."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush

from survey.plan_annotations import visible_wall_segments
from survey.plan_annotation_rendering import annotation_parts, annotation_pen, annotation_brush
from survey.plan_curve_rendering import curve_path
from survey.plan_label_rendering import glyph_path, label_pen


class VectorPlanSource:
    def __init__(self, size, lines, curves, labels, annotations):
        self._width, self._height = size.width(), size.height()
        commands = []
        for line in visible_wall_segments(lines, annotations):
            path = QPainterPath()
            path.moveTo(line["x1"], line["y1"])
            path.lineTo(line["x2"], line["y2"])
            commands.append((path, QPen(QColor(line["color"]), 2), QBrush(Qt.BrushStyle.NoBrush)))
        for curve in curves:
            commands.append((curve_path(curve), QPen(QColor(curve["color"]), 2), QBrush(Qt.BrushStyle.NoBrush)))
        for item in annotations:
            for path, dashed in annotation_parts(item):
                commands.append((path, annotation_pen(item, dashed=dashed), annotation_brush(item)))
        for label in labels:
            path = glyph_path(label)
            if label["outline_width"]:
                commands.append((path, label_pen(label), QBrush(Qt.BrushStyle.NoBrush)))
            commands.append((path, QPen(Qt.PenStyle.NoPen), QBrush(QColor(label["color"]))))
        self._commands = tuple(commands)

    def width(self):
        return self._width

    def height(self):
        return self._height

    def isNull(self):
        return self._width <= 0 or self._height <= 0

    def paint_plan(self, painter, target):
        painter.save()
        try:
            painter.translate(target.topLeft())
            painter.scale(target.width() / self._width, target.height() / self._height)
            bounds = QRectF(0, 0, self._width, self._height)
            painter.setClipRect(bounds)
            painter.fillRect(bounds, Qt.GlobalColor.white)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            for path, pen, brush in self._commands:
                painter.setPen(pen)
                painter.setBrush(brush)
                painter.drawPath(path)
        finally:
            painter.restore()
