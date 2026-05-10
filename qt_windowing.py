"""Shared Qt window behavior helpers."""

from PySide6.QtCore import QEasingCurve, QObject, QEvent, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGraphicsOpacityEffect,
    QHeaderView,
    QListView,
    QComboBox,
    QLineEdit,
    QPushButton,
    QTreeView,
    QToolButton,
    QWidget,
)

from qt_theme import QT_THEMES


CENTERED_PROPERTY = "_wifi_heatmap_centered_once"
SKIP_CENTERING_PROPERTY = "_wifi_heatmap_skip_centering"
DIM_OVERLAY_OBJECT_NAME = "modalDimOverlay"
DIM_FADE_MS = 120
FILE_DIALOG_OBJECT_NAME = "centeredFileDialog"


class DialogCenteringFilter(QObject):
    """Center top-level dialogs and dim their parent while they are visible."""

    def eventFilter(self, obj, event):
        if isinstance(obj, QWidget) and event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
            resize_dim_overlay(obj)

        if (
            event.type() == QEvent.Type.Show
            and isinstance(obj, QDialog)
            and obj.isWindow()
            and not obj.property(SKIP_CENTERING_PROPERTY)
        ):
            if not obj.property(CENTERED_PROPERTY):
                obj.setProperty(CENTERED_PROPERTY, True)
                QTimer.singleShot(0, lambda dialog=obj: center_window(dialog))
            QTimer.singleShot(0, lambda dialog=obj: push_modal_dim(dialog))

        if (
            event.type() in (QEvent.Type.Hide, QEvent.Type.Close)
            and isinstance(obj, QDialog)
            and obj.isWindow()
        ):
            pop_modal_dim(obj)
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


def get_centered_open_file_name(parent, caption, directory, name_filter):
    """Open a centered Qt file-open dialog and return `(path, selected_filter)`."""

    return run_centered_file_dialog(
        parent,
        caption,
        directory,
        name_filter,
        QFileDialog.AcceptMode.AcceptOpen,
        QFileDialog.FileMode.ExistingFile,
    )


def get_centered_save_file_name(parent, caption, directory, name_filter):
    """Open a centered Qt file-save dialog and return `(path, selected_filter)`."""

    return run_centered_file_dialog(
        parent,
        caption,
        directory,
        name_filter,
        QFileDialog.AcceptMode.AcceptSave,
        QFileDialog.FileMode.AnyFile,
    )


def run_centered_file_dialog(parent, caption, directory, name_filter, accept_mode, file_mode):
    dialog = QFileDialog(parent, caption, directory, name_filter)
    dialog.setObjectName(FILE_DIALOG_OBJECT_NAME)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setAcceptMode(accept_mode)
    dialog.setFileMode(file_mode)
    dialog.setModal(True)
    apply_file_dialog_tuning(dialog, parent)
    QTimer.singleShot(0, lambda current_dialog=dialog: tune_file_dialog_views(current_dialog))

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return "", ""

    selected = dialog.selectedFiles()
    return (selected[0] if selected else ""), dialog.selectedNameFilter()


def apply_file_dialog_tuning(dialog, parent):
    theme = getattr(parent, "theme", "light")
    palette = QT_THEMES.get(theme, QT_THEMES["light"])
    scale = getattr(parent, "ui_scale", 1.0)
    px = lambda value: max(1, int(round(value * scale)))
    font_px = lambda value: max(9, int(round(value * scale)))

    dialog.setMinimumSize(px(980), px(620))
    dialog.resize(px(1080), px(700))
    dialog.setStyleSheet(
        f"""
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} {{
            background: {palette["bg"]};
            color: {palette["text"]};
            font-family: "Segoe UI";
            font-size: {font_px(13)}px;
        }}
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} QLabel {{
            color: {palette["text"]};
            font-size: {font_px(13)}px;
        }}
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} QLineEdit,
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} QComboBox {{
            background: {palette["panel"]};
            color: {palette["text"]};
            border: 1px solid {palette["border"]};
            border-radius: {px(4)}px;
            padding: 0 {px(8)}px;
            min-height: {px(38)}px;
            max-height: {px(38)}px;
            min-width: 0;
        }}
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} QComboBox::drop-down {{
            width: {px(24)}px;
            border-left: 1px solid {palette["border"]};
            background: {palette["metric_info"]};
        }}
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} QPushButton {{
            background: {palette["button_bg"]};
            color: {palette["text"]};
            border: 1px solid {palette["border"]};
            border-radius: {px(5)}px;
            padding: {px(6)}px {px(14)}px;
            min-width: {px(96)}px;
            min-height: {px(30)}px;
            font-size: {font_px(13)}px;
            font-weight: 500;
        }}
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} QPushButton:hover {{
            background: {palette["button_hover"]};
        }}
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} QToolButton {{
            background: {palette["button_bg"]};
            color: {palette["text"]};
            border: 1px solid transparent;
            border-radius: {px(5)}px;
            padding: 0;
            min-width: {px(38)}px;
            max-width: {px(38)}px;
            min-height: {px(38)}px;
            max-height: {px(38)}px;
        }}
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} QToolButton:hover {{
            background: {palette["button_hover"]};
            border: 1px solid {palette["border"]};
        }}
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} QTreeView,
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} QListView {{
            background: {palette["panel"]};
            color: {palette["text"]};
            border: 0;
            selection-background-color: {palette["selection"]};
            selection-color: {palette["text"]};
            font-size: {font_px(13)}px;
            outline: 0;
        }}
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} QTreeView::item,
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} QListView::item {{
            min-height: {px(26)}px;
            padding: {px(2)}px {px(5)}px;
        }}
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} QHeaderView {{
            background: {palette["header"]};
        }}
        QFileDialog#{FILE_DIALOG_OBJECT_NAME} QHeaderView::section {{
            background: {palette["header"]};
            color: {palette["text"]};
            padding: {px(6)}px {px(8)}px;
            border: 0;
            border-right: 1px solid {palette["border"]};
            font-weight: 600;
            font-size: {font_px(13)}px;
        }}
        """
    )


def tune_file_dialog_views(dialog):
    if dialog is None:
        return

    scale = getattr(dialog.parentWidget(), "ui_scale", 1.0) if dialog.parentWidget() else 1.0
    px = lambda value: max(1, int(round(value * scale)))
    control_height = px(38)

    for combo in dialog.findChildren(QComboBox):
        combo.setMinimumHeight(control_height)
        combo.setMaximumHeight(control_height)

    for line_edit in dialog.findChildren(QLineEdit):
        line_edit.setMinimumHeight(control_height)
        line_edit.setMaximumHeight(control_height)

    for tool_button in dialog.findChildren(QToolButton):
        tool_button.setFixedSize(control_height, control_height)

    for push_button in dialog.findChildren(QPushButton):
        push_button.setMinimumHeight(control_height)

    for tree in dialog.findChildren(QTreeView):
        header = tree.header()
        if header is None or header.count() <= 1:
            tree.setMinimumWidth(px(160))
            continue

        header.setStretchLastSection(True)
        for section in range(header.count()):
            header.setSectionResizeMode(section, QHeaderView.ResizeMode.Interactive)
        tree.setColumnWidth(0, px(360))
        if header.count() > 1:
            tree.setColumnWidth(1, px(110))
        if header.count() > 2:
            tree.setColumnWidth(2, px(150))
        if header.count() > 3:
            tree.setColumnWidth(3, px(190))
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

    for list_view in dialog.findChildren(QListView):
        list_view.setMinimumWidth(px(170))


def push_modal_dim(dialog):
    """Add a soft dim overlay to the dialog parent window."""

    if dialog is None or dialog.property(SKIP_CENTERING_PROPERTY):
        return

    parent = dialog.parentWidget()
    if parent is None:
        return

    target = parent.window()
    if target is None or target is dialog or not target.isVisible():
        return

    if getattr(dialog, "_wifi_heatmap_dim_parent", None) is target:
        return

    count = getattr(target, "_wifi_heatmap_dim_count", 0)
    overlay = getattr(target, "_wifi_heatmap_dim_overlay", None)
    if overlay is None:
        overlay = QWidget(target)
        overlay.setObjectName(DIM_OVERLAY_OBJECT_NAME)
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        overlay.setStyleSheet(
            f"QWidget#{DIM_OVERLAY_OBJECT_NAME} {{ background-color: rgba(6, 12, 22, 92); }}"
        )
        overlay.setGeometry(target.rect())
        overlay.raise_()
        overlay.show()
        fade_overlay(overlay, 0.0, 1.0)
        target._wifi_heatmap_dim_overlay = overlay
    else:
        resize_dim_overlay(target)
        overlay.raise_()
        overlay.show()

    target._wifi_heatmap_dim_count = count + 1
    dialog._wifi_heatmap_dim_parent = target


def pop_modal_dim(dialog):
    target = getattr(dialog, "_wifi_heatmap_dim_parent", None)
    if target is None:
        return

    dialog._wifi_heatmap_dim_parent = None
    count = max(0, getattr(target, "_wifi_heatmap_dim_count", 1) - 1)
    target._wifi_heatmap_dim_count = count
    if count > 0:
        return

    overlay = getattr(target, "_wifi_heatmap_dim_overlay", None)
    target._wifi_heatmap_dim_overlay = None
    if overlay is None:
        return

    fade_overlay(overlay, 1.0, 0.0, delete_when_finished=True)


def resize_dim_overlay(widget):
    overlay = getattr(widget, "_wifi_heatmap_dim_overlay", None)
    if overlay is not None and overlay.isVisible():
        overlay.setGeometry(widget.rect())
        overlay.raise_()


def fade_overlay(overlay, start, end, delete_when_finished=False):
    effect = overlay.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(overlay)
        overlay.setGraphicsEffect(effect)

    animation = QPropertyAnimation(effect, b"opacity", overlay)
    animation.setDuration(DIM_FADE_MS)
    animation.setStartValue(start)
    animation.setEndValue(end)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    if delete_when_finished:
        animation.finished.connect(overlay.deleteLater)
    overlay._wifi_heatmap_dim_animation = animation
    animation.start()


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
