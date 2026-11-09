"""Immutable clean plan paths, painted at the destination's actual resolution."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush
from copy import copy

from survey.plan_annotations import visible_wall_segments
from survey.plan_annotation_rendering import annotation_parts, annotation_pen, annotation_brush
from survey.plan_curve_rendering import curve_path
from survey.plan_label_rendering import glyph_path, label_pen
from survey.plan_labels import labels_geometry
from survey.plan_curves import curve_bounds
from survey.plan_annotation_rendering import annotation_fits
from survey.plan_symbol_rendering import SymbolNumber, paint_number, number_commands
from survey.wall_rendering import MaterialPath, paint_material, WallReferenceInk


class VectorPlanSource:
    def __init__(self, size, lines, curves, labels, annotations):
        self._width, self._height = size.width(), size.height()
        self._viewport = QRectF(0,0,self._width,self._height)
        self._background = None
        commands = []
        if any(shape.get("wall") for shape in [*lines, *curves]):
            from survey.wall_geometry import wall_commands
            commands.extend(wall_commands(lines, curves, annotations))
            bounds = QRectF(0, 0, size.width(), size.height()).adjusted(-1e-6, -1e-6, 1e-6, 1e-6)
            if any(not bounds.contains(path.boundingRect()) for path, _pen, _brush in commands):
                raise ValueError("wall_outside")
        ink = WallReferenceInk(lines, curves)
        for line in visible_wall_segments(lines, annotations):
            if line.get("wall", {}).get("side") == 0:
                continue
            path = QPainterPath()
            path.moveTo(line["x1"], line["y1"])
            path.lineTo(line["x2"], line["y2"])
            commands.append(ink.command(line, path, QPen(QColor(line["color"]), 2)))
        for curve in curves:
            if curve.get("wall", {}).get("side") == 0:
                continue
            commands.append(ink.command(curve, curve_path(curve), QPen(QColor(curve["color"]), 2)))
        for item in annotations:
            for path, dashed in annotation_parts(item, lines):
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
            if any(not annotation_fits(a, bounds, state["segments"] or []) for a in state["annotations"]):
                raise ValueError("Layer annotation is outside the sheet")
            source = cls(size, state["segments"] or [], state["curves"], state["labels"], state["annotations"])
            if layer.get("visible", True):
                commands.extend(source._commands)
        result._commands = tuple(commands)
        return result

    def width(self):
        return self._width if self._viewport.width() == self._width else self._viewport.width()

    def height(self):
        return self._height if self._viewport.height() == self._height else self._viewport.height()

    def isNull(self):
        return self._width <= 0 or self._height <= 0

    def fitted_content(self):
        """An export-only viewport: imported backgrounds and model coordinates stay."""
        if self._background is not None:
            return self
        bounds=QRectF()
        full=QRectF(0,0,self._width,self._height)
        for path,pen,_brush in self._commands:
            parts=number_commands(path.item,11,full) if isinstance(path,SymbolNumber) else [(path,pen,None)]
            for shape,stroke,_fill in parts:
                box=shape.boundingRect()
                margin=stroke.widthF()/2 if stroke is not None and stroke.style()!=Qt.PenStyle.NoPen else 0
                box=box.adjusted(-margin,-margin,margin,margin)
                # QRectF.united ignores null line boxes. A minimum ink margin
                # also makes horizontal/vertical-only drawings fit safely.
                bounds=bounds.united(box.adjusted(-.5,-.5,.5,.5))
        if bounds.isEmpty():
            return self
        padding=max(2,max(bounds.width(),bounds.height())*.015)
        result=copy(self)
        # Keep symmetric whitespace even when ink touches an original sheet edge.
        # The export can extend over white; the survey canvas never changes.
        result._viewport=bounds.adjusted(-padding,-padding,padding,padding)
        return result

    def paint_plan(self, painter, target):
        painter.save()
        try:
            painter.translate(target.topLeft())
            bounds=self._viewport
            painter.scale(target.width() / bounds.width(), target.height() / bounds.height())
            painter.translate(-bounds.left(),-bounds.top())
            painter.setClipRect(bounds,Qt.ClipOperation.IntersectClip)
            if self._background is None:
                painter.fillRect(bounds, Qt.GlobalColor.white)
            else:
                painter.drawImage(0, 0, self._background)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            for path, pen, brush in self._commands:
                if isinstance(path, SymbolNumber):
                    paint_number(painter, path.item, bounds)
                    continue
                if isinstance(path, MaterialPath):
                    paint_material(painter, path, pen)
                    continue
                painter.setPen(pen)
                painter.setBrush(brush)
                painter.drawPath(path)
        finally:
            painter.restore()
