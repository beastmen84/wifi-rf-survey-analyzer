"""Shared native vector/raster rendering for analytic circular geometry."""
import math

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem

from survey.plan_curves import curve_info, point_at


def curve_path(curve):
    cx, cy, radius, start, sweep = curve_info(curve)
    path = QPainterPath()
    path.moveTo(*point_at(curve, 0))
    count = max(1, math.ceil(abs(sweep) / (math.pi / 4)))
    for index in range(count):
        a, b = start + sweep * index / count, start + sweep * (index + 1) / count
        p, q = point_at(curve, index / count), point_at(curve, (index + 1) / count)
        factor = radius * 4 / 3 * math.tan((b - a) / 4)
        path.cubicTo(p[0] - math.sin(a) * factor, p[1] + math.cos(a) * factor,
                     q[0] + math.sin(b) * factor, q[1] - math.cos(b) * factor, *q)
    if curve["kind"] == "circle":
        path.closeSubpath()
    return path


def curve_item(curve):
    item = QGraphicsPathItem(curve_path(curve))
    item.setPen(QPen(QColor(curve["color"]), 2))
    item.setZValue(5)
    item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
    return item


def render_curves(image, curves):
    native = QImage(image.tobytes("raw", "RGB"), image.width, image.height,
                    image.width * 3, QImage.Format.Format_RGB888).copy()
    painter = QPainter(native)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for curve in curves:
        painter.setPen(QPen(QColor(curve["color"]), 2))
        painter.drawPath(curve_path(curve))
    painter.end()
    raw = native.convertToFormat(QImage.Format.Format_RGBA8888)
    return Image.frombytes("RGBA", (raw.width(), raw.height()), bytes(raw.constBits()),
                           "raw", "RGBA", raw.bytesPerLine()).convert("RGB")
