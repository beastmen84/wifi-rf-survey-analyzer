"""Shared rounded settings popup panel widgets."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect


class SettingsPopupPanel(QFrame):
    def __init__(self, palette, radius, parent=None):
        super().__init__(parent)
        self.panel_color = QColor(palette["panel"])
        self.border_color = QColor(palette["border"])
        self.radius = radius
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.shadow_effect = QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(14)
        self.shadow_effect.setOffset(0, 3)
        shadow_color = QColor(15, 23, 42)
        shadow_color.setAlpha(42)
        self.shadow_effect.setColor(shadow_color)
        self.setGraphicsEffect(self.shadow_effect)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)
        painter.fillPath(path, self.panel_color)
        painter.setPen(QPen(self.border_color, 1.0))
        painter.drawPath(path)
