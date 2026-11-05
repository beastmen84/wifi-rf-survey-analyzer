"""Native vector icons for the plan-only boundary fill controls."""
from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from qt_ui.qt_theme import QT_THEMES


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
