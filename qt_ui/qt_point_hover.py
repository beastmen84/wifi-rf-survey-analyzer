"""An immediate, input-transparent Survey popup, independent of Qt hover timers."""

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class SurveyPointHover(QFrame):
    context_changed = Signal()

    def __init__(self, owner):
        flags = (Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
                 | Qt.WindowType.WindowDoesNotAcceptFocus | Qt.WindowType.WindowTransparentForInput)
        super().__init__(owner, flags)
        self.setObjectName("surveyPointHover")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet("QFrame#surveyPointHover { background: white; border: 1px solid #cbd5e1; }"
                           "QLabel { background: transparent; color: #111827; border: 0; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 8, 9, 8)
        self.label = QLabel()
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setWordWrap(True)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.label)
        self.owner_window = owner.window()
        self.owner_window.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self.owner_window and event.type() in {
            QEvent.Type.WindowDeactivate, QEvent.Type.Hide, QEvent.Type.Move, QEvent.Type.Resize,
        }:
            self.context_changed.emit()
        return super().eventFilter(watched, event)

    def present(self, html, anchor):
        screen = QGuiApplication.screenAt(anchor.center()) or self.screen()
        available = screen.availableGeometry()
        self.label.setMaximumWidth(max(100, min(400, available.width() - 36)))
        self.label.setText(html)
        self.adjustSize()
        self.move(self.position_for(anchor, self.size(), available))
        self.show()
        self.raise_()

    @staticmethod
    def position_for(anchor, size, available):
        """Prefer a gap beside the marker; clamp to its monitor's work area."""
        gap = 12
        candidates = (
            QPoint(anchor.right() + gap, anchor.bottom() + gap),
            QPoint(anchor.left() - size.width() - gap, anchor.bottom() + gap),
            QPoint(anchor.right() + gap, anchor.top() - size.height() - gap),
            QPoint(anchor.left() - size.width() - gap, anchor.top() - size.height() - gap),
        )
        fallback = None
        for candidate in candidates:
            position = QPoint(max(available.left(), min(candidate.x(), available.right() - size.width() + 1)),
                              max(available.top(), min(candidate.y(), available.bottom() - size.height() + 1)))
            rect = QRect(position, size)
            if available.contains(rect) and not rect.intersects(anchor):
                return position
            if fallback is None:
                fallback = position
        return fallback
