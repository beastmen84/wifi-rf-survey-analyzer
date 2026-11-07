"""Immutable clean plan paths, painted at the destination's actual resolution."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush

from survey.plan_annotations import visible_wall_segments
from survey.plan_annotation_rendering import annotation_parts, annotation_pen, annotation_brush
from survey.plan_curve_rendering import curve_path
from survey.plan_label_rendering import glyph_path, label_pen
from survey.plan_labels import labels_geometry
from survey.plan_curves import curve_bounds
from survey.plan_annotation_rendering import annotation_fits
from survey.plan_symbol_rendering import SymbolNumber, paint_number


class VectorPlanSource:
    def __init__(self, size, lines, curves, labels, annotations):
        self._width, self._height = size.width(), size.height()
        self._background = None
        commands = []
        if any(shape.get("wall") for shape in [*lines, *curves]):
            from survey.wall_geometry import wall_commands
            commands.extend(wall_commands(lines, curves, annotations))
            bounds = QRectF(0, 0, size.width(), size.height()).adjusted(-1e-6, -1e-6, 1e-6, 1e-6)
            if any(not bounds.contains(path.boundingRect()) for path, _pen, _brush in commands):
                raise ValueError("wall_outside")
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
            if item.get("number") or item.get("ap_label"):
                commands.append((SymbolNumber(item), None, None))
        for label in labels:
            path = glyph_path(label)
            if label["outline_width"]:
                commands.append((path, label_pen(label), QBrush(Qt.BrushStyle.NoBrush)))
            commands.append((path, QPen(Qt.PenStyle.NoPen), QBrush(QColor(label["color"]))))
        self._commands = tuple(commands)

    @classmethod
    def from_layers(cls, size, layers, background=None):
        from survey.plan_layers import validate_state
        result = cls(size, [], [], [], [])
        result._background = background
        commands = []
        bounds = QRectF(0, 0, size.width(), size.height())
        for layer in layers:
            state = validate_state(layer["drawing"])
            for line in (state["segments"] or []) + labels_geometry(state["labels"]):
                if any(line[key] < -1e-6 or line[key] > extent + 1e-6 for keys, extent in
                       ((('x1', 'x2'), size.width()), (('y1', 'y2'), size.height())) for key in keys):
                    raise ValueError("Layer geometry is outside the sheet")
            for curve in state["curves"]:
                left, top, right, bottom = curve_bounds(curve)
                if min(left, top) < -1e-7 or right > size.width() + 1e-7 or bottom > size.height() + 1e-7:
                    raise ValueError("Layer curve is outside the sheet")
            if any(not annotation_fits(a, bounds) for a in state["annotations"]):
                raise ValueError("Layer annotation is outside the sheet")
            source = cls(size, state["segments"] or [], state["curves"], state["labels"], state["annotations"])
            if layer.get("visible", True):
                commands.extend(source._commands)
        result._commands = tuple(commands)
        return result

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
            if self._background is None:
                painter.fillRect(bounds, Qt.GlobalColor.white)
            else:
                painter.drawImage(0, 0, self._background)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            for path, pen, brush in self._commands:
                if isinstance(path, SymbolNumber):
                    paint_number(painter, path.item, bounds)
                    continue
                painter.setPen(pen)
                painter.setBrush(brush)
                painter.drawPath(path)
        finally:
            painter.restore()
