"""Clipped vector hatches shared by the editor, clean print and raster exports."""
import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPainterPathStroker, QPen
from PySide6.QtWidgets import QGraphicsPathItem
from survey.wall_materials import MATERIALS
from survey.wall_properties import wall_rank


def split_contours(path):
    """Keep original cubic contours; fill polygons may add artificial bridges."""
    result, current, index = [], QPainterPath(), 0
    while index < path.elementCount():
        e = path.elementAt(index)
        if e.isMoveTo():
            if not current.isEmpty():
                result.append(current)
            current = QPainterPath()
            current.moveTo(e.x,e.y)
        elif e.isLineTo():
            current.lineTo(e.x,e.y)
        elif e.isCurveTo():
            second, end = path.elementAt(index+1), path.elementAt(index+2)
            current.cubicTo(e.x,e.y,second.x,second.y,end.x,end.y)
            index += 2
        index += 1
    if not current.isEmpty():
        result.append(current)
    return result


class MaterialPath(QPainterPath):
    def __init__(self, path, material, pattern):
        super().__init__(path)
        fill, ink, default = MATERIALS[material]
        self.fill, self.ink = QColor(fill), QColor(ink)
        self.pattern = default if pattern == 'auto' else pattern
        self.hatch = QPainterPath()
        self.joints = QPainterPath()
        self.pitch = 12.0  # Schematic drawing units, independent of output DPI.
        b = path.boundingRect()
        # Guard imported extents too: at most ~2000 rows/columns per group.
        self.pitch = max(self.pitch, (b.width()+b.height())/1800)
        p = self.pitch
        left, right = math.floor(b.left()/p)*p, math.ceil(b.right()/p)*p
        top, bottom = math.floor(b.top()/p)*p, math.ceil(b.bottom()/p)*p
        def line(x1,y1,x2,y2):
            self.hatch.moveTo(x1,y1)
            self.hatch.lineTo(x2,y2)
        if self.pattern in ('diagonal','cross','wood'):
            for i in range(math.floor((left-bottom)/p), math.ceil((right-top)/p)+1):
                x = i*p
                line(x+top,top,x+bottom,bottom)
                if self.pattern == 'wood':
                    line(x+top+p*.28,top,x+bottom+p*.28,bottom)
            if self.pattern == 'cross':
                for i in range(math.floor((left+top)/p), math.ceil((right+bottom)/p)+1):
                    line(i*p-top,top,i*p-bottom,bottom)
        elif self.pattern in ('dots','brick','grid'):
            for row in range(round(top/p),round(bottom/p)+1):
                y = row*p
                line(left,y,right,y)
            if self.pattern == 'brick':
                for col in range(round(left/p),round(right/p)+1):
                    y = top+((col+round(top/p))%2)*p
                    self.joints.moveTo(col*p,y)
                    self.joints.lineTo(col*p,bottom+p)
            if self.pattern == 'grid':
                for col in range(round(left/p),round(right/p)+1):
                    line(col*p,top,col*p,bottom)


def paint_material(painter, path, outline):
    painter.save()
    try:
        painter.fillPath(path, path.fill)
        if not path.hatch.isEmpty():
            painter.setClipPath(path, Qt.ClipOperation.IntersectClip)
            pen = QPen(path.ink, .7)
            if path.pattern == 'dots':
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setDashPattern([.01, path.pitch/.7-.01])
                pen.setDashOffset(0)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path.hatch)
            if not path.joints.isEmpty():
                pen.setDashPattern([path.pitch/.7, path.pitch/.7])
                painter.setPen(pen)
                painter.drawPath(path.joints)
    finally:
        painter.restore()
    painter.setPen(outline)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


class WallReferenceInk:
    """Hide lower-priority reference ink beneath the winning physical material."""
    def __init__(self, lines=(), curves=()):
        from survey.wall_geometry import ranked_wall_bodies
        self.bodies = ranked_wall_bodies(lines, curves)
        self.masks = {}

    def command(self, shape, path, pen):
        if not shape.get('wall') or pen.style() == Qt.PenStyle.NoPen:
            return path, pen, QBrush(Qt.BrushStyle.NoBrush)
        from survey.wall_geometry import united
        rank = wall_rank(shape)
        if rank not in self.masks:
            self.masks[rank] = united(body for other,body in self.bodies if other > rank)
        mask = self.masks[rank]
        if mask.isEmpty() or not mask.boundingRect().intersects(path.boundingRect().adjusted(-1,-1,1,1)):
            return path, pen, QBrush(Qt.BrushStyle.NoBrush)
        stroke = QPainterPathStroker()
        stroke.setWidth(pen.widthF())
        stroke.setCapStyle(pen.capStyle())
        stroke.setJoinStyle(pen.joinStyle())
        ink = stroke.createStroke(path)
        if ink.intersected(mask).simplified().isEmpty():
            return path, pen, QBrush(Qt.BrushStyle.NoBrush)
        return ink.subtracted(mask), QPen(Qt.PenStyle.NoPen), QBrush(pen.color())


class MaterialItem(QGraphicsPathItem):
    def __init__(self, path, pen):
        super().__init__(path)
        self.material_path = path
        self.setPen(pen)
        # A device-coordinate pixmap can retain stale strips while scrolling at
        # fractional display scaling. Repaint the precomputed vectors directly.

    def paint(self, painter, option, widget=None):
        paint_material(painter, self.material_path, self.pen())


def wall_item(path, pen, brush):
    if isinstance(path, MaterialPath):
        return MaterialItem(path, pen)
    item = QGraphicsPathItem(path)
    item.setPen(pen)
    item.setBrush(brush)
    return item
