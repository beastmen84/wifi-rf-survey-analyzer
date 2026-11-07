"""One annotation path definition shared by scene, hit tests and exports."""
import math

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QGraphicsPathItem
from survey.plan_objects import FREE_ANNOTATIONS, object_local_vertices, object_is_round


def annotation_parts(item):
    path = QPainterPath()
    arcs = QPainterPath()
    if item["kind"] in FREE_ANNOTATIONS:
        if object_is_round(item):
            path.addEllipse(-item["width"] / 2, -item["height"] / 2, item["width"], item["height"])
        else:
            points = object_local_vertices(item)
            path.moveTo(*points[0])
            for point in points[1:]:
                path.lineTo(*point)
            path.closeSubpath()
        if item.get("variant") == "rack":
            for y in (-.3, 0, .3):
                path.addRect(-item["width"] * .34, item["height"] * (y - .08),
                             item["width"] * .68, item["height"] * .16)
        elif item.get("variant") == "wifi_ap":
            for factor in (.18, .34):
                radius = item["width"] * factor
                box = (-radius, item["height"] * .22 - radius, 2 * radius, 2 * radius)
                path.arcMoveTo(*box, 45)
                path.arcTo(*box, 45, 90)
            radius = item["width"] * .035
            path.addEllipse(-radius, item["height"] * .22 - radius, 2 * radius, 2 * radius)
        transform = QTransform()
        transform.translate(item["cx"], item["cy"])
        transform.rotate(0 if object_is_round(item) else item["angle"])
        return [(transform.map(path), False)]
    if item["kind"] == "marker":
        path.moveTo(*item["points"][0])
        for point in item["points"][1:]:
            path.lineTo(*point)
        return [(path, True)]
    length = math.hypot(item["x2"] - item["x1"], item["y2"] - item["y1"])
    side = item.get("side", 1)
    if item["kind"] == "window":
        depth = max(3, length * .04)
        path.addRect(0, -depth, length, depth * 2)
        path.moveTo(0, 0)
        path.lineTo(length, 0)
    elif item.get("variant") == "frame":
        depth = max(3, length * .04)
        jamb = min(length / 4, max(1, length * .02))
        path.addRect(0, -depth, jamb, depth * 2)
        path.addRect(length - jamb, -depth, jamb, depth * 2)
    elif item.get("variant") == "sliding":
        depth = max(3, length * .04)
        path.addRect(0, -depth, length * .6, depth)
        path.addRect(length * .4, 0, length * .6, depth)
    else:
        def leaf(origin, radius, direction):
            path.moveTo(origin, 0)
            path.lineTo(origin, side * radius)
            arcs.moveTo(origin + direction * radius, 0)
            k = .5522847498307936
            arcs.cubicTo(origin + direction * radius, side * radius * k,
                         origin + direction * radius * k, side * radius, origin, side * radius)
        if item.get("variant") == "double":
            leaf(0, length / 2, 1)
            leaf(length, length / 2, -1)
        else:
            leaf(length if item.get("hinge") else 0, length, -1 if item.get("hinge") else 1)
    transform = QTransform()
    transform.translate(item["x1"], item["y1"])
    transform.rotate(math.degrees(math.atan2(item["y2"] - item["y1"], item["x2"] - item["x1"])))
    parts = [(transform.map(path), False)]
    if not arcs.isEmpty():
        parts.append((transform.map(arcs), True))
    return parts


def annotation_path(item):
    path = QPainterPath()
    for part, _dashed in annotation_parts(item):
        path.addPath(part)
    return path


def annotation_pen(item, color=None, dashed=None):
    pen = QPen(QColor(color or item["color"]), item["stroke"])
    is_dashed = item["kind"] == "marker" if dashed is None else dashed
    if is_dashed:
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
    item.setPen(QPen(Qt.PenStyle.NoPen))
    for path, dashed in annotation_parts(annotation):
        child = QGraphicsPathItem(path, item)
        child.setPen(annotation_pen(annotation, color, dashed))
        child.setBrush(annotation_brush(annotation))
        child.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
    item.setZValue(6)
    if annotation.get("number") or annotation.get("ap_label"):
        from survey.plan_symbol_rendering import SymbolNumberItem
        SymbolNumberItem(annotation, item)
    item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
    return item


def annotation_brush(item):
    if item.get("variant") == "wifi_ap" and item.get("ap_group"):
        return QBrush(QColor("#bfdbfe"))
    return QBrush(QColor(item["fill"])) if item["kind"] in FREE_ANNOTATIONS and item.get("fill") else QBrush(Qt.BrushStyle.NoBrush)


def render_annotations(image, annotations):
    native = QImage(image.tobytes("raw", "RGB"), image.width, image.height,
                    image.width * 3, QImage.Format.Format_RGB888).copy()
    painter = QPainter(native)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for item in annotations:
        for path, dashed in annotation_parts(item):
            painter.setPen(annotation_pen(item, dashed=dashed))
            painter.setBrush(annotation_brush(item))
            painter.drawPath(path)
        if item.get("number") or item.get("ap_label"):
            from survey.plan_symbol_rendering import paint_number
            from PySide6.QtCore import QRectF
            paint_number(painter, item, QRectF(0, 0, image.width, image.height))
    painter.end()
    raw = native.convertToFormat(QImage.Format.Format_RGBA8888)
    return Image.frombytes("RGBA", (raw.width(), raw.height()), bytes(raw.constBits()),
                           "raw", "RGBA", raw.bytesPerLine()).convert("RGB")
