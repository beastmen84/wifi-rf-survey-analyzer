"""Workspace settings actions for language, theme, and UI scale."""

import time

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QLabel, QMessageBox, QVBoxLayout

from app_logging import log_event, log_exception
from app_restart import start_replacement_process
from app_settings import save_theme, save_ui_scale
from i18n import LANGUAGE_OPTIONS, normalize_language
from qt_ui.qt_theme import QT_THEME_OPTIONS, QT_THEMES
from qt_ui.qt_windowing import SKIP_CENTERING_PROPERTY
from ui_scaling import (
    UI_SCALE_OPTIONS,
    detect_auto_ui_scale_percent,
    format_ui_scale_diagnostics,
    normalize_ui_scale_mode,
    ui_scale_diagnostics,
)


class WorkspaceSettingsMixin:
    def change_language(self, value):
        language = normalize_language(value)
        if language == self.language:
            return

        self.language = language
        self.start_language_combo.blockSignals(True)
        language_index = self.start_language_combo.findData(language.upper())
        if language_index >= 0:
            self.start_language_combo.setCurrentIndex(language_index)
        self.start_language_combo.blockSignals(False)
        self.retranslate()
        if self.session is not None:
            self.floorplan_view.set_ap_groups(self.session.get_ap_groups())
            self.refresh_live_controls()
            self.maybe_update_live_preview()

    def change_theme(self, theme):
        if theme not in QT_THEMES or theme == self.theme:
            return

        self.theme = theme
        save_theme(theme)
        log_event(f"workspace theme changed theme={theme}", logger_name="ui")
        self.apply_styles()

    def change_ui_scale(self, mode):
        mode = normalize_ui_scale_mode(mode)
        if mode == self.ui_scale_mode:
            return

        if self.scan_in_progress or self.live_rendering:
            QMessageBox.warning(self, self.tr("warning"), self.tr("restart_blocked_busy"))
            return
        if not self.confirm_ui_scale_restart(mode):
            return
        if not self.confirm_switch_survey():
            return
        if not save_ui_scale(mode):
            QMessageBox.warning(self, self.tr("warning"), self.tr("settings_save_failed"))
            return

        log_event(
            f"workspace ui scale saved for restart {format_ui_scale_diagnostics(ui_scale_diagnostics(mode))}",
            logger_name="ui",
        )
        try:
            start_replacement_process()
        except OSError as exc:
            log_exception("workspace restart failed after ui scale change", exc, logger_name="ui")
            QMessageBox.warning(self, self.tr("warning"), self.tr("restart_failed"))
            return

        self.restart_requested = True
        QApplication.instance().quit()

    def confirm_ui_scale_restart(self, mode):
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Question)
        message_box.setWindowTitle(self.tr("ui_scale_restart_title"))
        message_box.setText(
            self.tr("ui_scale_restart_message", scale=self.ui_scale_label_for_mode(mode))
        )
        save_button = message_box.addButton(
            self.tr("save_and_restart"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        message_box.addButton(self.tr("cancel"), QMessageBox.ButtonRole.RejectRole)
        message_box.setDefaultButton(save_button)
        message_box.exec()
        return message_box.clickedButton() == save_button

    def ui_scale_label_for_mode(self, mode):
        return dict(self.ui_scale_items()).get(mode, f"{mode}%")

    def open_settings_menu(self):
        if self.should_suppress_settings_menu_toggle():
            return

        active_dialog = self.settings_menu_dialog
        if active_dialog is not None and active_dialog.isVisible():
            active_dialog.close()
            return

        dialog = QDialog(self)
        self.settings_menu_dialog = dialog
        dialog.setObjectName("settingsMenuPanel")
        dialog.setProperty(SKIP_CENTERING_PROPERTY, True)
        dialog.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(self.spx(12), self.spx(10), self.spx(12), self.spx(10))
        layout.setSpacing(self.spx(8))

        theme_combo = self.create_settings_combo(
            [(theme, self.tr(f"qt_theme_{theme}")) for theme in QT_THEME_OPTIONS],
            self.theme,
        )
        theme_combo.currentIndexChanged.connect(lambda _index: self.change_theme(theme_combo.currentData()))
        self.add_settings_row(layout, self.tr("theme"), theme_combo)

        scale_combo = self.create_settings_combo(self.ui_scale_items(), self.ui_scale_mode)
        scale_combo.currentIndexChanged.connect(lambda _index: self.change_ui_scale(scale_combo.currentData()))
        self.add_settings_row(layout, self.tr("ui_scale"), scale_combo)

        language_combo = self.create_settings_combo(
            LANGUAGE_OPTIONS,
            self.language.upper(),
        )
        language_combo.currentIndexChanged.connect(lambda _index: self.change_language(language_combo.currentData()))
        self.add_settings_row(layout, self.tr("language"), language_combo)

        menu_width = self.spx(230)
        dialog.setMinimumWidth(menu_width)
        dialog.adjustSize()
        position = self.settings_menu_button.mapToGlobal(
            QPoint(self.settings_menu_button.width() - menu_width, self.settings_menu_button.height())
        )
        dialog.move(position)
        try:
            dialog.exec()
        finally:
            if self.settings_menu_dialog is dialog:
                self.settings_menu_dialog = None
            if self.is_settings_button_global_pos(QCursor.pos()):
                self.settings_menu_suppressed_until = time.monotonic() + 0.35

    def should_suppress_settings_menu_toggle(self):
        if time.monotonic() < self.settings_menu_suppressed_until:
            self.settings_menu_suppressed_until = 0.0
            return True
        return False

    def is_settings_button_global_pos(self, global_pos):
        local_pos = self.settings_menu_button.mapFromGlobal(global_pos)
        return self.settings_menu_button.rect().contains(local_pos)

    def create_settings_combo(self, items, current_value):
        combo = QComboBox()
        combo.setMinimumWidth(self.spx(150))
        for value, label in items:
            combo.addItem(label, value)
        index = combo.findData(current_value)
        combo.setCurrentIndex(max(0, index))
        return combo

    def add_settings_row(self, layout, label_text, widget):
        label = QLabel(label_text)
        label.setObjectName("settingsMenuLabel")
        layout.addWidget(label)
        layout.addWidget(widget)

    def ui_scale_items(self):
        auto_percent = detect_auto_ui_scale_percent()
        return [
            (mode, self.tr("ui_scale_auto", percent=auto_percent) if mode == "auto" else f"{mode}%")
            for mode in UI_SCALE_OPTIONS
        ]
