"""Theme-aware vector icons for drawing and plan-only boundary controls."""
from functools import lru_cache
from math import ceil

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from qt_ui.qt_theme import QT_THEMES


@lru_cache(maxsize=512)
def plan_tool_icon(tool, theme, size, device_pixel_ratio=1.0, swatch=None):
    """Render explicit normal/selected/disabled states at the display's real DPI."""
    palette = QT_THEMES[theme]
    icon = QIcon()
    for mode, state in ((QIcon.Mode.Normal, QIcon.State.Off),
                        (QIcon.Mode.Normal, QIcon.State.On),
                        (QIcon.Mode.Disabled, QIcon.State.Off),
                        (QIcon.Mode.Disabled, QIcon.State.On)):
        selected = state == QIcon.State.On and mode != QIcon.Mode.Disabled
        ink = QColor("#ffffff" if selected else palette["text"])
        accent = QColor("#ffffff" if selected else palette["metric_info"])
        fill = QColor(accent)
        fill.setAlpha(35 if selected else 25)
        pixels = ceil(size * device_pixel_ratio)
        pixmap = QPixmap(pixels, pixels)
        pixmap.setDevicePixelRatio(device_pixel_ratio)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.scale(size / 24, size / 24)
            if mode == QIcon.Mode.Disabled:
                painter.setOpacity(0.35)
            pen = QPen(ink, 1.7, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            _paint_tool(painter, tool, ink, accent, fill, swatch)
        finally:
            painter.end()
        icon.addPixmap(pixmap, mode, state)
    return icon


def _paint_tool(p, tool, ink, accent, fill, swatch):
    def path(points, close=False):
        outline = QPainterPath(QPointF(*points[0]))
        for point in points[1:]:
            outline.lineTo(*point)
        if close:
            outline.closeSubpath()
        p.drawPath(outline)

    def node(x, y):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(accent)
        p.drawEllipse(QPointF(x, y), 1.6, 1.6)

    if tool == "rectangle":
        p.setBrush(fill)
        p.drawRoundedRect(QRectF(4, 5, 16, 14), 1.5, 1.5)
        node(4, 5)
        node(20, 19)
    elif tool == "line":
        p.drawLine(QPointF(5, 18), QPointF(19, 6))
        node(5, 18)
        node(19, 6)
    elif tool == "circle":
        p.setBrush(fill)
        p.drawEllipse(QRectF(4, 4, 16, 16))
        p.setPen(QPen(accent, 1.4))
        p.drawLine(QPointF(12, 12), QPointF(17.5, 6.5))
        node(12, 12)
    elif tool == "arc":
        arc = QPainterPath(QPointF(4, 18))
        arc.cubicTo(4, 2, 20, 2, 20, 18)
        p.drawPath(arc)
        node(4, 18)
        node(20, 18)
    elif tool in ("eraser", "annotation_eraser"):
        p.setBrush(fill)
        path(((4, 13), (13, 4), (20, 11), (11, 20), (8, 20)), True)
        p.drawLine(QPointF(9, 8), QPointF(16, 15))
        p.setPen(QPen(accent, 1.7))
        p.drawLine(14, 20, 21, 20)
        if tool == "annotation_eraser":
            p.drawLine(18, 3, 18, 6)
            p.drawLine(16, 4, 20, 4)
    elif tool in ("select", "annotation_select"):
        p.setBrush(fill)
        path(((6, 3), (6, 19), (10, 15), (13, 21), (16, 19), (13, 13), (20, 13)), True)
        if tool == "annotation_select":
            p.setPen(QPen(accent, 1.5))
            p.drawLine(17, 3, 21, 3)
            p.drawLine(19, 3, 19, 7)
    elif tool == "wall":
        p.setBrush(fill)
        p.drawRoundedRect(QRectF(3, 5, 18, 14), 1, 1)
        p.drawLine(3, 12, 21, 12)
        p.drawLine(9, 5, 9, 12)
        p.drawLine(15, 12, 15, 19)
    elif tool == "marker":
        p.setPen(QPen(accent, 1.8, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap))
        trail = QPainterPath(QPointF(3, 18))
        trail.cubicTo(5, 3, 15, 22, 21, 6)
        p.drawPath(trail)
    elif tool == "window":
        p.setBrush(fill)
        p.drawRoundedRect(QRectF(3, 7, 18, 10), 1, 1)
        p.setPen(QPen(accent, 1.4))
        p.drawLine(4, 12, 20, 12)
        p.drawLine(12, 8, 12, 16)
    elif tool == "door":
        p.drawLine(4, 20, 4, 4)
        p.drawLine(4, 20, 20, 20)
        p.setPen(QPen(accent, 1.4, Qt.PenStyle.DashLine))
        p.drawArc(QRectF(4, 4, 32, 32), 90 * 16, 90 * 16)
    elif tool == "desk":
        p.setBrush(fill)
        p.drawRoundedRect(QRectF(3, 4, 18, 11), 1.5, 1.5)
        p.drawLine(6, 15, 6, 20)
        p.drawLine(18, 15, 18, 20)
        p.setPen(QPen(accent, 1.4))
        p.drawLine(10, 10, 14, 10)
    elif tool == "symbol":
        p.setBrush(fill)
        p.drawRoundedRect(QRectF(3, 3, 7, 7), 1.5, 1.5)
        p.drawEllipse(QRectF(14, 3, 7, 7))
        path(((6.5, 14), (10, 21), (3, 21)), True)
        p.setPen(QPen(accent, 1.5))
        path(((17.5, 14), (21, 17.5), (17.5, 21), (14, 17.5)), True)
    elif tool == "text":
        p.drawLine(5, 5, 19, 5)
        p.drawLine(5, 5, 5, 8)
        p.drawLine(19, 5, 19, 8)
        p.drawLine(12, 5, 12, 20)
        p.setPen(QPen(accent, 1.7))
        p.drawLine(8, 20, 16, 20)
    elif tool == "edit":
        p.setBrush(fill)
        path(((5, 15), (16, 4), (20, 8), (9, 19), (4, 20)), True)
        p.drawLine(13, 7, 17, 11)
    elif tool in ("undo", "redo"):
        if tool == "redo":
            p.translate(24, 0)
            p.scale(-1, 1)
        arrow = QPainterPath(QPointF(20, 19))
        arrow.cubicTo(22, 10, 13, 6, 5, 11)
        p.drawPath(arrow)
        path(((5, 5), (5, 11), (11, 11)))
    elif tool == "snap":
        p.setPen(QPen(accent, 1.1))
        for value in (5, 12, 19):
            p.drawLine(value, 3, value, 21)
            p.drawLine(3, value, 21, value)
        node(12, 12)
    elif tool == "color":
        p.setBrush(QColor(swatch or ink))
        p.drawRoundedRect(QRectF(4, 4, 16, 16), 4, 4)
    elif tool == "close":
        p.drawLine(7, 7, 17, 17)
        p.drawLine(17, 7, 7, 17)
    else:
        raise ValueError(f"Unknown drawing icon: {tool}")


def update_fill_icons(owner):
    size = owner.spx(20)
    for button, automatic in ((owner.boundaries_fill_button, False), (owner.boundaries_auto_fill_button, True)):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(size / 24, size / 24)
        color = QColor("#ffffff" if button.isChecked() else QT_THEMES[owner.theme]["text"])
        painter.setPen(QPen(color, 1.7))
        bucket = QPainterPath(QPointF(5, 6))
        for point in ((13, 6), (19, 12), (11, 20), (3, 12), (9, 6), (6, 3)):
            bucket.lineTo(*point)
        painter.drawPath(bucket)
        painter.drawLine(3, 12, 19, 12)
        painter.setBrush(color)
        painter.drawEllipse(19, 16, 3, 5)
        if automatic:
            painter.drawLine(17, 1, 17, 7)
            painter.drawLine(14, 4, 20, 4)
        painter.end()
        button.setIcon(QIcon(pixmap))
        button.setIconSize(QSize(size, size))
