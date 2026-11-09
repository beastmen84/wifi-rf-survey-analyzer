"""Workspace settings actions for language, theme, and UI scale."""

import time

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QLabel, QMessageBox, QVBoxLayout

from app_core.logging import log_event, log_exception
from app_core.restart import start_replacement_process
from app_core.settings import (
    FOCUS_POINT_ZOOM_PERCENT_OPTIONS,
    normalize_focus_point_zoom_percent,
    save_focus_point_zoom_percent,
    save_measurement_system,
    save_theme,
    save_ui_scale,
)
from app_core.units import MEASUREMENT_SYSTEM_OPTIONS, normalize_measurement_system
from translations.i18n import LANGUAGE_OPTIONS, normalize_language
from qt_ui.qt_settings_memory import add_ap_memory_settings_section
from qt_ui.qt_settings_popup import SettingsPopupPanel
from qt_ui.qt_theme import QT_THEME_OPTIONS, QT_THEMES
from qt_ui.scaling import (
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
        selected_point = self.current_selected_point()
        self.retranslate()
        if self.session is not None:
            self.refresh_points_table()
            if selected_point:
                self.select_point_in_table(selected_point)
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
        self.plan_tools.sync()
        self.layers_panel.retranslate()
        if hasattr(self, "analysis_view"):
            self.analysis_view.retranslate()
        if getattr(self.floorplan_view, "grid_visible", False):
            self.set_floorplan_grid_enabled(True, show_status=False)

    def change_ui_scale(self, mode):
        mode = normalize_ui_scale_mode(mode)
        if mode == self.ui_scale_mode:
            return

        if self.scan_in_progress or self.live_rendering or (hasattr(self, "analysis_view") and self.analysis_view.busy) or any(
            thread is not None and thread.isRunning()
            for thread in (self.scan_thread, self.live_thread)
        ):
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

    def change_measurement_system(self, mode):
        mode = normalize_measurement_system(mode)
        if mode == self.measurement_system:
            return True

        current_max_distance_px = self.current_live_max_distance_px()
        scale_was_cleared = False
        if self.session is not None and self.has_calibrated_scale():
            if not self.confirm_measurement_system_scale_reset():
                return False
            self.session.metadata.pop("px_per_meter", None)
            self.session.dirty = True
            self.floorplan_view.clear_scale_calibration_overlay()
            self.set_floorplan_grid_enabled(False, show_status=False)
            scale_was_cleared = True

        if not save_measurement_system(mode):
            QMessageBox.warning(self, self.tr("warning"), self.tr("settings_save_failed"))
            return False

        self.measurement_system = mode
        if self.session is not None and hasattr(self, "set_session_measurement_system_metadata"):
            self.set_session_measurement_system_metadata(mode, mark_dirty=True)
        log_event(f"workspace measurement system changed mode={mode}", logger_name="ui")
        self.set_live_max_distance_px_silent(current_max_distance_px)
        self.remember_live_option_state()
        if scale_was_cleared:
            self.refresh_session_labels()
            self.status.showMessage(self.tr("measurement_system_scale_reset_done"))
        self.maybe_update_live_preview()
        return True

    def change_focus_point_zoom_percent(self, percent):
        percent = normalize_focus_point_zoom_percent(percent)
        if percent == self.focus_point_zoom_percent:
            return True

        if not save_focus_point_zoom_percent(percent):
            QMessageBox.warning(self, self.tr("warning"), self.tr("settings_save_failed"))
            return False

        self.focus_point_zoom_percent = percent
        self.floorplan_view.set_focus_point_zoom_percent(percent)
        if hasattr(self, "live_view"):
            self.live_view.set_focus_marker_zoom_percent(percent)
        log_event(f"workspace focus point zoom changed percent={percent}", logger_name="ui")
        return True

    def confirm_measurement_system_scale_reset(self):
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Warning)
        message_box.setWindowTitle(self.tr("measurement_system_scale_reset_title"))
        message_box.setText(self.tr("measurement_system_scale_reset_message"))
        change_button = message_box.addButton(
            self.tr("measurement_system_scale_reset_button"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        message_box.addButton(self.tr("cancel"), QMessageBox.ButtonRole.RejectRole)
        message_box.setDefaultButton(change_button)
        message_box.exec()
        return message_box.clickedButton() == change_button

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

        active_panel = self.settings_menu_panel
        if active_panel is not None and active_panel.isVisible():
            self.close_settings_menu(suppress_if_on_button=True)
            return

        parent = self.workspace_page
        panel = SettingsPopupPanel(QT_THEMES.get(self.theme, QT_THEMES["light"]), self.spx(8), parent)
        self.settings_menu_panel = panel
        panel.setObjectName("settingsMenuPanel")
        layout = QVBoxLayout(panel)
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

        self.add_settings_section(layout, self.tr("workspace_settings_section"))

        units_combo = self.create_settings_combo(self.measurement_system_items(), self.measurement_system)
        units_combo.currentIndexChanged.connect(lambda _index: self.apply_measurement_system_combo(units_combo))
        self.add_settings_row(layout, self.tr("measurement_system"), units_combo)

        focus_zoom_combo = self.create_settings_combo(
            self.focus_point_zoom_items(),
            self.focus_point_zoom_percent,
        )
        focus_zoom_combo.currentIndexChanged.connect(
            lambda _index: self.change_focus_point_zoom_percent(focus_zoom_combo.currentData())
        )
        self.add_settings_row(layout, self.tr("go_to_point_zoom"), focus_zoom_combo)

        add_ap_memory_settings_section(self, layout)

        menu_width = self.spx(250)
        menu_gap = self.spx(8)
        panel.setMinimumWidth(menu_width)
        panel.adjustSize()
        position = self.settings_menu_button.mapTo(
            parent,
            QPoint(self.settings_menu_button.width() - menu_width, self.settings_menu_button.height() + menu_gap)
        )
        panel.move(position)
        panel.raise_()
        panel.show()
        self.install_settings_menu_event_filter()

    def close_settings_menu(self, suppress_if_on_button=False):
        panel = self.settings_menu_panel
        if panel is not None:
            panel.hide()
            panel.deleteLater()
            self.settings_menu_panel = None
        self.remove_settings_menu_event_filter()
        if suppress_if_on_button and self.is_settings_button_global_pos(QCursor.pos()):
            self.settings_menu_suppressed_until = time.monotonic() + 0.35

    def install_settings_menu_event_filter(self):
        if self.settings_menu_event_filter_installed:
            return
        QApplication.instance().installEventFilter(self)
        self.settings_menu_event_filter_installed = True

    def remove_settings_menu_event_filter(self):
        if not self.settings_menu_event_filter_installed:
            return
        QApplication.instance().removeEventFilter(self)
        self.settings_menu_event_filter_installed = False

    def handle_settings_menu_event_filter(self, event):
        if (
            self.settings_menu_panel is None
            or event.type() != QEvent.Type.MouseButtonPress
            or QApplication.activePopupWidget() is not None
        ):
            return False

        global_pos = event.globalPosition().toPoint()
        if self.is_settings_button_global_pos(global_pos):
            self.close_settings_menu(suppress_if_on_button=True)
            return False

        panel_pos = self.settings_menu_panel.mapFromGlobal(global_pos)
        if not self.settings_menu_panel.rect().contains(panel_pos):
            self.close_settings_menu()
        return False

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

    def add_settings_section(self, layout, title_text):
        separator = QFrame()
        separator.setObjectName("settingsMenuSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)

        title = QLabel(title_text)
        title.setObjectName("settingsMenuSectionLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

    def ui_scale_items(self):
        auto_percent = detect_auto_ui_scale_percent()
        return [
            (mode, self.tr("ui_scale_auto", percent=auto_percent) if mode == "auto" else f"{mode}%")
            for mode in UI_SCALE_OPTIONS
        ]

    def measurement_system_items(self):
        return [
            (mode, self.tr(f"measurement_system_{mode}"))
            for mode in MEASUREMENT_SYSTEM_OPTIONS
        ]

    def focus_point_zoom_items(self):
        return [
            (percent, f"{percent}%")
            for percent in FOCUS_POINT_ZOOM_PERCENT_OPTIONS
        ]

    def apply_measurement_system_combo(self, combo):
        if self.change_measurement_system(combo.currentData()):
            return

        combo.blockSignals(True)
        combo.setCurrentIndex(max(0, combo.findData(self.measurement_system)))
        combo.blockSignals(False)
