"""Shared AP Memory actions for Qt settings popups."""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QLabel, QMessageBox, QPushButton

from ap.memory import clear_ap_memory, ensure_ap_memory_file
from qt_ui.qt_theme import QT_THEMES


def add_ap_memory_settings_section(owner, layout):
    separator = QFrame()
    separator.setObjectName("settingsMenuSeparator")
    separator.setFrameShape(QFrame.Shape.HLine)
    layout.addWidget(separator)

    title = QLabel(owner.tr("ap_memory_settings_title"))
    title.setObjectName("settingsMenuSectionLabel")
    layout.addWidget(title)

    open_button = QPushButton(owner.tr("open_memory_folder"))
    clear_button = QPushButton(owner.tr("clear_ap_memory"))
    for button in (open_button, clear_button):
        button.setObjectName("settingsMenuActionButton")
        layout.addWidget(button)

    open_button.clicked.connect(lambda _checked=False: open_ap_memory_folder(owner))
    clear_button.clicked.connect(lambda _checked=False: confirm_clear_ap_memory(owner))


def open_ap_memory_folder(owner):
    memory_path = ensure_ap_memory_file()
    folder = memory_path.parent
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        show_ap_memory_warning(owner, owner.tr("open_memory_folder_failed"))
        return False

    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
        show_ap_memory_warning(owner, owner.tr("open_memory_folder_failed"))
        return False
    return True


def confirm_clear_ap_memory_dialog(owner):
    message_box = create_ap_memory_message_box(
        owner,
        QMessageBox.Icon.Warning,
        owner.tr("clear_ap_memory_title"),
        owner.tr("clear_ap_memory_confirm"),
    )
    clear_button = message_box.addButton(
        owner.tr("clear_ap_memory_confirm_button"),
        QMessageBox.ButtonRole.DestructiveRole,
    )
    clear_button.setObjectName("apMemoryDialogDestructiveButton")
    cancel_button = message_box.addButton(owner.tr("cancel"), QMessageBox.ButtonRole.RejectRole)
    message_box.setDefaultButton(cancel_button)
    message_box.setEscapeButton(cancel_button)
    message_box.exec()
    return message_box.clickedButton() == clear_button


def confirm_clear_ap_memory(owner):
    if not confirm_clear_ap_memory_dialog(owner):
        return False

    if not clear_ap_memory():
        show_ap_memory_warning(owner, owner.tr("clear_ap_memory_failed"))
        return False

    if hasattr(owner, "refresh_session_labels"):
        owner.refresh_session_labels()
    return True


def show_ap_memory_warning(owner, message):
    message_box = create_ap_memory_message_box(owner, QMessageBox.Icon.Warning, owner.tr("warning"), message)
    close_button = message_box.addButton(owner.tr("close"), QMessageBox.ButtonRole.AcceptRole)
    message_box.setDefaultButton(close_button)
    message_box.setEscapeButton(close_button)
    message_box.exec()


def create_ap_memory_message_box(owner, icon, title, message):
    message_box = QMessageBox(owner)
    message_box.setIcon(icon)
    message_box.setWindowTitle(title)
    message_box.setText(message)
    message_box.setStyleSheet(ap_memory_message_box_stylesheet(owner))
    return message_box


def ap_memory_message_box_stylesheet(owner):
    palette = QT_THEMES.get(getattr(owner, "theme", "light"), QT_THEMES["light"])
    scale_px = getattr(owner, "spx", lambda value: max(1, int(round(value))))
    scale_font = getattr(owner, "sfont", lambda value: max(9, int(round(value))))
    return f"""
        QMessageBox {{
            background: {palette["panel"]};
            color: {palette["text"]};
            font-family: "Segoe UI";
            font-size: {scale_font(13)}px;
        }}
        QMessageBox QLabel {{
            background: transparent;
            color: {palette["text"]};
            padding: {scale_px(2)}px;
        }}
        QMessageBox QPushButton {{
            background: {palette["button_bg"]};
            color: {palette["text"]};
            border: 1px solid {palette["border"]};
            border-radius: {scale_px(5)}px;
            padding: {scale_px(6)}px {scale_px(14)}px;
            min-width: {scale_px(96)}px;
            min-height: {scale_px(30)}px;
            font-weight: 700;
        }}
        QMessageBox QPushButton:hover {{
            background: {palette["button_hover"]};
        }}
        QMessageBox QPushButton#apMemoryDialogDestructiveButton {{
            background: {palette["metric_danger"]};
            color: #FFFFFF;
            border-color: {palette["metric_danger"]};
        }}
        QMessageBox QPushButton#apMemoryDialogDestructiveButton:hover {{
            background: {palette["metric_warning"]};
            border-color: {palette["metric_warning"]};
        }}
    """
