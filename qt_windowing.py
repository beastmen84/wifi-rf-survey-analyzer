"""Shared Qt window behavior helpers."""

from PySide6.QtCore import QObject, QEvent, QTimer
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QApplication, QDialog


CENTERED_PROPERTY = "_wifi_heatmap_centered_once"


class DialogCenteringFilter(QObject):
    """Center top-level dialogs the first time they are shown."""

    def eventFilter(self, obj, event):
        if (
            event.type() == QEvent.Type.Show
            and isinstance(obj, QDialog)
            and obj.isWindow()
            and not obj.property(CENTERED_PROPERTY)
        ):
            obj.setProperty(CENTERED_PROPERTY, True)
            QTimer.singleShot(0, lambda dialog=obj: center_window(dialog))
        return False


def install_dialog_centering(app=None):
    """Install the app-wide dialog-centering event filter once."""

    app = app or QApplication.instance()
    if app is None:
        return None

    existing = getattr(app, "_wifi_heatmap_dialog_centering_filter", None)
    if existing is not None:
        return existing

    dialog_filter = DialogCenteringFilter(app)
    app.installEventFilter(dialog_filter)
    app._wifi_heatmap_dialog_centering_filter = dialog_filter
    return dialog_filter


def center_window(window):
    """Move a top-level window to the center of its parent or active screen."""

    if window is None or not window.isWindow():
        return

    frame = window.frameGeometry()
    if frame.width() <= 0 or frame.height() <= 0:
        return

    target_screen = screen_for_window(window)
    if target_screen is None:
        return

    available = target_screen.availableGeometry()
    parent = window.parentWidget()
    if parent is not None and parent.window() is not window and parent.window().isVisible():
        target = parent.window().frameGeometry()
    else:
        active = QApplication.activeWindow()
        if active is not None and active is not window and active.isVisible():
            target = active.frameGeometry()
        else:
            target = available

    frame.moveCenter(target.center())
    x = clamp(frame.x(), available.left(), available.left() + max(0, available.width() - frame.width()))
    y = clamp(frame.y(), available.top(), available.top() + max(0, available.height() - frame.height()))
    window.move(x, y)


def screen_for_window(window):
    parent = window.parentWidget()
    if parent is not None and parent.windowHandle() is not None:
        return parent.windowHandle().screen()
    if window.windowHandle() is not None:
        return window.windowHandle().screen()

    cursor_screen = QGuiApplication.screenAt(QCursor.pos())
    return cursor_screen or QGuiApplication.primaryScreen()


def clamp(value, minimum, maximum):
    return min(max(value, minimum), maximum)
