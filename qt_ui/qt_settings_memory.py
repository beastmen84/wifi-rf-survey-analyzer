"""Shared AP Memory actions for Qt settings popups."""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QLabel, QMessageBox, QPushButton

from ap.memory import clear_ap_memory, ensure_ap_memory_file


def add_ap_memory_settings_section(owner, layout):
    separator = QFrame()
    separator.setObjectName("settingsMenuSeparator")
    separator.setFrameShape(QFrame.Shape.HLine)
    layout.addWidget(separator)

    title = QLabel(owner.tr("ap_memory_settings_title"))
    title.setObjectName("settingsMenuLabel")
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
        QMessageBox.warning(owner, owner.tr("warning"), owner.tr("open_memory_folder_failed"))
        return False

    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
        QMessageBox.warning(owner, owner.tr("warning"), owner.tr("open_memory_folder_failed"))
        return False
    return True


def confirm_clear_ap_memory(owner):
    response = QMessageBox.warning(
        owner,
        owner.tr("clear_ap_memory_title"),
        owner.tr("clear_ap_memory_confirm"),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Cancel,
    )
    if response != QMessageBox.StandardButton.Yes:
        return False

    if not clear_ap_memory():
        QMessageBox.warning(owner, owner.tr("warning"), owner.tr("clear_ap_memory_failed"))
        return False

    if hasattr(owner, "refresh_session_labels"):
        owner.refresh_session_labels()
    return True
