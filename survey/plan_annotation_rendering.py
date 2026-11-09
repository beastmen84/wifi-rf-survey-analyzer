"""One annotation path definition shared by scene, hit tests and exports."""
import math

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QGraphicsPathItem
from survey.plan_objects import FREE_ANNOTATIONS, object_local_vertices, object_is_round


def annotation_parts(item, lines=()):
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
    from survey.wall_geometry import aperture_profile
    profile = aperture_profile(item, lines)
    depth = max(3, length * .04)
    low, high = profile if profile is not None else (-depth, depth)
    center = (low + high) / 2
    if profile is not None:
        path.setFillRule(Qt.FillRule.WindingFill)

    def jambs():
        jamb = min(length / 4, max(1, length * .02))
        path.addRect(0, low, jamb, high-low)
        path.addRect(length-jamb, low, jamb, high-low)

    if item["kind"] == "window":
        path.addRect(0, low, length, high-low)
        path.moveTo(0, center)
        path.lineTo(length, center)
    elif item.get("variant") == "frame":
        jambs()
    elif item.get("variant") == "sliding":
        if profile is not None:
            jambs()
        path.addRect(0, low, length * .6, center-low)
        path.addRect(length * .4, center, length * .6, high-center)
    else:
        if profile is not None:
            jambs()
        def leaf(origin, radius, direction):
            path.moveTo(origin, center)
            path.lineTo(origin, center + side * radius)
            arcs.moveTo(origin + direction * radius, center)
            k = .5522847498307936
            arcs.cubicTo(origin + direction * radius, center + side * radius * k,
                         origin + direction * radius * k, center + side * radius, origin, center + side * radius)
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


def annotation_path(item, lines=()):
    path = QPainterPath()
    parts = annotation_parts(item, lines)
    if parts:
        path.setFillRule(parts[0][0].fillRule())
    for part, _dashed in parts:
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


def annotation_fits(item, bounds, lines=()):
    # Horizontal/vertical marker paths have a zero-height/width bounding rect.
    # QRectF.contains(rect) rejects these even when all points are on the sheet.
    rect = annotation_path(item, lines).boundingRect()
    return (rect.left() >= bounds.left() - 1e-7 and rect.top() >= bounds.top() - 1e-7
            and rect.right() <= bounds.right() + 1e-7 and rect.bottom() <= bounds.bottom() + 1e-7)


def annotation_item(annotation, color=None, lines=()):
    item = QGraphicsPathItem(annotation_path(annotation, lines))
    item.setPen(QPen(Qt.PenStyle.NoPen))
    for path, dashed in annotation_parts(annotation, lines):
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


def render_annotations(image, annotations, lines=()):
    native = QImage(image.tobytes("raw", "RGB"), image.width, image.height,
                    image.width * 3, QImage.Format.Format_RGB888).copy()
    painter = QPainter(native)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for item in annotations:
        for path, dashed in annotation_parts(item, lines):
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
