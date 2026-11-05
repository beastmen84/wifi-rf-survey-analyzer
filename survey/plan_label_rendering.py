"""Shared glyph outlines for native previews, saved PNGs and map/report workers."""
from uuid import uuid4
import math

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QGraphicsPathItem

from survey.plan_labels import validate_labels


def build_label(style, identity=None):
    text = style["text"]
    size = float(style["size"])
    if (not isinstance(text, str) or not text.strip() or len(text) > 2048
            or not math.isfinite(size) or not 1 <= size <= 300):
        raise ValueError("Invalid text or font size")
    font = QFont(style["family"])
    font.setPixelSize(max(1, round(size * 96 / 72)))
    font.setBold(bool(style.get("bold")))
    font.setItalic(bool(style.get("italic")))
    metrics = QFontMetricsF(font)
    lines = text.splitlines() or [""]
    widths = [metrics.horizontalAdvance(line) for line in lines]
    width = max(widths)
    path = QPainterPath()
    for index, line in enumerate(lines):
        gap = width - widths[index]
        x = gap / 2 if style.get("alignment") == "center" else gap if style.get("alignment") == "right" else 0
        path.addText(x, index * metrics.lineSpacing(), font, line)
    if path.isEmpty():
        raise ValueError("Empty glyph outline")
    bounds = path.controlPointRect()
    path = QTransform.fromTranslate(-bounds.center().x(), -bounds.center().y()).map(path)
    commands, index = [], 0
    while index < path.elementCount():
        element = path.elementAt(index)
        if element.isMoveTo():
            commands.append(["M", element.x, element.y])
        elif element.isLineTo():
            commands.append(["L", element.x, element.y])
        else:
            second, third = path.elementAt(index + 1), path.elementAt(index + 2)
            commands.append(["C", element.x, element.y, second.x, second.y, third.x, third.y])
            index += 2
        index += 1
        if len(commands) > 25000:
            raise ValueError("Text outline is too complex")
    outline = float(style.get("outline_width", 0))
    label = dict(style, id=identity or uuid4().hex, path=commands,
                 width=bounds.width() + outline, height=bounds.height() + outline,
                 x=float(style.get("x", 0)), y=float(style.get("y", 0)), angle=float(style.get("angle", 0)))
    return validate_labels([label])[0]


def glyph_path(label):
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    for command in label["path"]:
        if command[0] == "M":
            path.moveTo(*command[1:])
        elif command[0] == "L":
            path.lineTo(*command[1:])
        else:
            path.cubicTo(*command[1:])
    transform = QTransform()
    transform.translate(label["x"], label["y"])
    transform.rotate(label["angle"])
    return transform.map(path)


def label_pen(label):
    if not label["outline_width"]:
        return QPen(Qt.PenStyle.NoPen)
    pen = QPen(QColor(label["outline_color"]), label["outline_width"])
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


class GlyphItem(QGraphicsPathItem):
    def paint(self, painter, option, widget=None):
        painter.save()
        if self.pen().style() != Qt.PenStyle.NoPen:
            painter.setPen(self.pen())
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(self.path())
        painter.fillPath(self.path(), self.brush())
        painter.restore()


def label_item(label):
    item = GlyphItem(glyph_path(label))
    item.setPen(label_pen(label))
    item.setBrush(QColor(label["color"]))
    item.setZValue(6)
    item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
    return item


def render_labels(image, labels):
    if not labels:
        return image
    source = image.convert("RGBA")
    buffer = source.tobytes()
    canvas = QImage(buffer, image.width, image.height, image.width * 4, QImage.Format.Format_RGBA8888).copy()
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for label in labels:
        path = glyph_path(label)
        if label["outline_width"]:
            painter.setPen(label_pen(label))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
        painter.fillPath(path, QColor(label["color"]))
    painter.end()
    return Image.frombytes("RGBA", image.size, bytes(canvas.constBits())).convert("RGB")
