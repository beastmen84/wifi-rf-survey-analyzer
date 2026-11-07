"""Upright fitted numbers, readable external badges, shared by all plan outputs."""
from copy import deepcopy
from functools import lru_cache
import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainterPath, QPen, QBrush, QTransform
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem


class SymbolNumber:
    def __init__(self, item):
        self.item = deepcopy(item)


@lru_cache(maxsize=2048)
def number_glyph(number):
    font = QFont("Segoe UI")
    font.setPixelSize(100)
    font.setBold(True)
    path = QPainterPath()
    path.addText(0, 0, font, str(number))
    rect = path.boundingRect()
    return QTransform.fromTranslate(-rect.center().x(), -rect.center().y()).map(path)


def number_layout(item):
    """Fit immutable source geometry once; zoom only changes badge placement."""
    from survey.plan_annotation_rendering import annotation_path
    text_value = str(item.get("number") or item.get("ap_label", ""))
    text_value = " ".join(text_value.split())
    if len(text_value) > 40:
        text_value = text_value[:39] + "…"
    glyph = number_glyph(text_value)
    rect = glyph.boundingRect()
    if rect.isEmpty():
        return None
    shape = annotation_path(item)
    center_x, center_y = item["cx"], item["cy"]
    if item["variant"] == "triangle":
        angle = math.radians(item["angle"])
        center_x -= item["height"] / 6 * math.sin(angle)
        center_y += item["height"] / 6 * math.cos(angle)
    factor = min(item["width"] * .72 / rect.width(), item["height"] * .62 / rect.height())
    for _ in range(32):
        transform = QTransform()
        transform.translate(center_x, center_y)
        transform.scale(factor, factor)
        path = transform.map(glyph)
        box = path.boundingRect()
        test = QPainterPath()
        test.addRect(box.adjusted(-item["width"] * .04, -item["height"] * .04,
                                  item["width"] * .04, item["height"] * .04))
        if shape.contains(test):
            break
        factor *= .85
    fill = QColor(item.get("fill") or "#ffffff")
    text = QColor("#ffffff" if fill.lightnessF() < .5 else "#111827")
    return glyph, rect, shape.boundingRect(), box, path, text


def number_commands(item, minimum_height=0, bounds=None, layout=None):
    layout = layout or number_layout(item)
    if layout is None:
        return []
    glyph, rect, frame, box, path, text = layout
    if box.height() >= minimum_height and not item.get("ap_label"):
        return [(path, QPen(Qt.PenStyle.NoPen), QBrush(text))]
    factor = max(minimum_height, 1e-6) / rect.height()
    width, height = rect.width() * factor, rect.height() * factor
    padding = minimum_height * .25
    x = frame.right() + minimum_height * .7
    y = frame.top() - minimum_height * .3 - height / 2
    if bounds is not None:
        if x + width + padding > bounds.right():
            x = frame.left() - minimum_height * .7 - width
        x = min(max(x, bounds.left() + padding), bounds.right() - width - padding)
        y = min(max(y, bounds.top() + padding + height / 2), bounds.bottom() - padding - height / 2)
    bubble = QPainterPath()
    bubble.addRoundedRect(QRectF(x - padding, y - height / 2 - padding, width + 2 * padding,
                                height + 2 * padding), padding, padding)
    transform = QTransform()
    transform.translate(x + width / 2, y)
    transform.scale(factor, factor)
    path = transform.map(glyph)
    leader = QPainterPath()
    leader.moveTo(item["cx"], item["cy"])
    leader.lineTo(x if x > item["cx"] else x + width, y)
    pen = QPen(QColor("#334155"), max(.01, minimum_height / 14))
    return [(leader, pen, QBrush(Qt.BrushStyle.NoBrush)),
            (bubble, pen, QBrush(QColor("#ffffff"))),
            (path, QPen(Qt.PenStyle.NoPen), QBrush(QColor("#111827")))]


def paint_number(painter, item, bounds):
    transform = painter.worldTransform()
    factor = max(1e-9, math.hypot(transform.m11(), transform.m12()))
    # QImage density and QPrinter resolution give the same physical 7pt minimum.
    minimum = 7 * painter.device().logicalDpiY() / 72 / factor
    for path, pen, brush in number_commands(item, minimum, bounds):
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawPath(path)


class SymbolNumberItem(QGraphicsItem):
    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.value, self.last = deepcopy(item), None
        self.layout = number_layout(self.value)
        self._bounds = QRectF()
        self.parts = [QGraphicsPathItem(self) for _ in range(3)]
        for child in self.parts:
            child.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setPos(item["cx"], item["cy"])
        self.update_scale(1)

    def boundingRect(self):
        return self._bounds

    def paint(self, painter, option, widget=None):
        pass  # Child paths paint with the same pens/brushes as raster output.

    def update_scale(self, factor, bounds=None, minimum=11):
        factor = max(factor, 1e-9)
        key = factor, bounds, minimum
        if key == self.last:
            return
        self.last = key
        self.prepareGeometryChange()
        transform = QTransform()
        transform.scale(factor, factor)
        transform.translate(-self.value["cx"], -self.value["cy"])
        commands = number_commands(self.value, minimum / factor, bounds, self.layout)
        self._bounds = QRectF()
        for index, child in enumerate(self.parts):
            child.setVisible(index < len(commands))
            if index >= len(commands):
                child.setPath(QPainterPath())
                continue
            path, pen, brush = commands[index]
            child.setPath(transform.map(path))
            pen = QPen(pen)
            pen.setWidthF(pen.widthF() * factor)
            child.setPen(pen)
            child.setBrush(brush)
            self._bounds = self._bounds.united(child.boundingRect())
