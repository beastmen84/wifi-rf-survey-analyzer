"""One annotation path definition shared by scene, hit tests and exports."""
import math

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QGraphicsPathItem


def annotation_path(item):
    path = QPainterPath()
    if item["kind"] == "marker":
        path.moveTo(*item["points"][0])
        for point in item["points"][1:]:
            path.lineTo(*point)
        return path
    length = math.hypot(item["x2"] - item["x1"], item["y2"] - item["y1"])
    side = item.get("side", 1)
    if item["kind"] == "window":
        depth = max(3, length * .04)
        path.addRect(0, -depth, length, depth * 2)
        path.moveTo(0, 0)
        path.lineTo(length, 0)
    elif item.get("variant") == "sliding":
        depth = max(3, length * .04)
        path.addRect(0, -depth, length * .6, depth)
        path.addRect(length * .4, 0, length * .6, depth)
    else:
        def leaf(origin, radius, direction):
            path.moveTo(origin, 0)
            path.lineTo(origin, side * radius)
            path.moveTo(origin + direction * radius, 0)
            k = .5522847498307936
            path.cubicTo(origin + direction * radius, side * radius * k,
                         origin + direction * radius * k, side * radius, origin, side * radius)
        if item.get("variant") == "double":
            leaf(0, length / 2, 1)
            leaf(length, length / 2, -1)
        else:
            leaf(length if item.get("hinge") else 0, length, -1 if item.get("hinge") else 1)
    transform = QTransform()
    transform.translate(item["x1"], item["y1"])
    transform.rotate(math.degrees(math.atan2(item["y2"] - item["y1"], item["x2"] - item["x1"])))
    return transform.map(path)


def annotation_pen(item, color=None):
    pen = QPen(QColor(color or item["color"]), item["stroke"])
    if item["kind"] == "marker":
        pen.setStyle(Qt.PenStyle.DashLine)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def annotation_fits(item, bounds):
    # Horizontal/vertical marker paths have a zero-height/width bounding rect.
    # QRectF.contains(rect) rejects these even when all points are on the sheet.
    rect = annotation_path(item).boundingRect()
    return (rect.left() >= bounds.left() - 1e-7 and rect.top() >= bounds.top() - 1e-7
            and rect.right() <= bounds.right() + 1e-7 and rect.bottom() <= bounds.bottom() + 1e-7)


def annotation_item(annotation, color=None):
    item = QGraphicsPathItem(annotation_path(annotation))
    item.setPen(annotation_pen(annotation, color))
    item.setZValue(6)
    item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
    return item


def render_annotations(image, annotations):
    native = QImage(image.tobytes("raw", "RGB"), image.width, image.height,
                    image.width * 3, QImage.Format.Format_RGB888).copy()
    painter = QPainter(native)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for item in annotations:
        painter.setPen(annotation_pen(item))
        painter.drawPath(annotation_path(item))
    painter.end()
    raw = native.convertToFormat(QImage.Format.Format_RGBA8888)
    return Image.frombytes("RGBA", (raw.width(), raw.height()), bytes(raw.constBits()),
                           "raw", "RGBA", raw.bytesPerLine()).convert("RGB")
