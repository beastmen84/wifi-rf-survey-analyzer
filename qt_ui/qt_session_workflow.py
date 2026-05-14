"""Survey session lifecycle and workspace state updates for the Qt app."""

import os
from pathlib import Path

try:
    from PySide6.QtWidgets import QMessageBox
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from app_core.settings import get_last_survey_directory, save_last_survey_path
from ap.memory import count_memory_applied_groups, get_ap_memory_summary
from qt_ui.qt_windowing import get_centered_open_file_name, get_centered_save_file_name
from survey.store import SurveyFormatError, SurveySession


class SurveySessionWorkflowMixin:
    def show_start_page(self):
        self.stack.setCurrentWidget(self.start_page)
        self.status.clearMessage()

    def show_workspace_page(self):
        self.stack.setCurrentWidget(self.workspace_page)
        self.refresh_session_labels()
        self.refresh_points_table()
        self.maybe_update_live_preview()

    def new_survey(self):
        if not self.confirm_switch_survey():
            return False
        self.session = SurveySession()
        self.load_session_ssid_state()
        self.reset_live_option_memory()
        self.floorplan_view.clear_floorplan()
        self.live_view.clear()
        self.show_workspace_page()
        return True

    def open_survey(self, csv_file=None):
        if not self.confirm_switch_survey():
            return False

        if csv_file is None:
            csv_file, _selected_filter = get_centered_open_file_name(
                self,
                self.tr("open_existing_survey"),
                get_last_survey_directory(),
                self.tr("qt_survey_file_filter"),
            )
        if not csv_file:
            return False

        try:
            self.session = SurveySession(csv_file)
        except SurveyFormatError as exc:
            self.show_survey_format_error(str(exc))
            return False

        self.load_session_ssid_state()
        self.reset_live_option_memory()
        save_last_survey_path(csv_file)
        self.live_view.clear()
        self.show_workspace_page()
        self.load_saved_plan()
        self.status.showMessage(self.tr("active_survey", name=self.session_display_name()))
        return True

    def save_survey(self):
        if self.session is None:
            return False

        csv_file = self.session.csv_file
        if not csv_file:
            csv_file, _selected_filter = get_centered_save_file_name(
                self,
                self.tr("save"),
                get_last_survey_directory(),
                self.tr("qt_survey_file_filter"),
            )
            if not csv_file:
                return False
            if Path(csv_file).suffix.lower() != ".csv":
                csv_file = f"{csv_file}.csv"

        self.session.save(csv_file)
        save_last_survey_path(csv_file)
        self.refresh_session_labels()
        self.status.showMessage(self.tr("survey_saved", name=self.session.display_name))
        return True

    def confirm_switch_survey(self):
        if self.session is None or not self.session.dirty:
            return True

        response = QMessageBox.question(
            self,
            self.tr("unsaved_changes_title"),
            self.tr("unsaved_changes"),
            (
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel
            ),
            QMessageBox.StandardButton.Save,
        )
        if response == QMessageBox.StandardButton.Save:
            return self.save_survey()
        if response == QMessageBox.StandardButton.Discard:
            return True
        return False

    def closeEvent(self, event):
        if self.restart_requested:
            event.accept()
            return

        if self.scan_in_progress:
            x, y = self.pending_scan_point or ("-", "-")
            self.status.showMessage(self.tr("scanning", x=x, y=y))
            event.ignore()
            return
        if self.live_rendering:
            self.status.showMessage(self.tr("live_preview_rendering"))
            event.ignore()
            return

        if self.confirm_switch_survey():
            event.accept()
        else:
            event.ignore()

    def show_survey_format_error(self, error_key):
        message_key = {
            "raw_scan_file": "raw_scan_file_selected",
            "invalid_raw_scan_format": "invalid_raw_scan_format",
            "missing_survey_file": "invalid_survey_format",
        }.get(error_key, "invalid_survey_format")
        QMessageBox.critical(
            self,
            self.tr("invalid_survey_title"),
            self.tr(message_key),
        )

    def session_display_name(self):
        if self.session is None:
            return self.tr("unsaved_survey")
        if self.session.csv_file:
            return self.session.display_name
        return self.tr("unsaved_survey")

    def refresh_session_labels(self):
        if self.session is None:
            csv_name = self.tr("unsaved_survey")
            map_name = self.tr("no_map")
            point_count = 0
            raw_count = 0
            ap_group_count = 0
            relevant_label = self.tr("relevant_networks_none")
            last_point = "-"
            dirty_suffix = ""
        else:
            csv_name = self.session_display_name()
            map_file = self.session.metadata.get("map_file", "")
            map_name = os.path.basename(map_file) if map_file else self.tr("no_map")
            point_summaries = self.session.get_point_summaries()
            point_count = len(point_summaries)
            raw_count = len(self.session.raw_scan_rows)
            ap_group_count = len(self.session.get_ap_groups())
            relevant_label = (
                ", ".join(sorted(self.relevant_ssids, key=str.casefold))
                if self.relevant_ssids
                else self.tr("relevant_networks_none")
            )
            last_point = (
                f"x={point_summaries[-1]['x']}, y={point_summaries[-1]['y']}"
                if point_summaries
                else "-"
            )
            dirty_suffix = " *" if self.session.dirty else ""

        self.csv_label.setText(f"{csv_name}{dirty_suffix}")
        self.map_label.setText(map_name)
        self.points_label.setText(str(point_count))
        self.raw_rows_label.setText(str(raw_count))
        self.ap_groups_label.setText(str(ap_group_count))
        self.relevant_label.setText(relevant_label)
        self.footer_label.setText(
            self.tr(
                "footer_survey_info",
                csv=f"{csv_name}{dirty_suffix}",
                map=map_name,
                points=point_count,
                last=last_point,
            )
        )
        if hasattr(self, "memory_status_label"):
            self.memory_status_label.setText(self.format_ap_memory_status())
            self.memory_status_label.setToolTip(get_ap_memory_summary().get("path", ""))
        self.new_workspace_button.setEnabled(not self.scan_in_progress)
        self.open_workspace_button.setEnabled(not self.scan_in_progress)
        can_use_session = self.session is not None and not self.scan_in_progress
        self.save_workspace_button.setEnabled(can_use_session)
        self.load_plan_button.setEnabled(can_use_session)
        self.ap_groups_button.setEnabled(can_use_session)
        self.quality_button.setEnabled(can_use_session)
        self.help_button.setEnabled(True)
        self.manage_relevant_button.setEnabled(can_use_session and bool(self.available_relevant_ssids()))
        self.clear_relevant_button.setEnabled(
            can_use_session and bool(self.relevant_ssids or self.known_ssids)
        )
        live_tab_active = self.tabs.currentIndex() == 1
        has_map = self.floorplan_view.has_floorplan()
        has_zoom_map = self.live_view.pixmap_item is not None if live_tab_active else has_map
        has_scale = self.has_calibrated_scale()
        self.zoom_in_button.setEnabled(has_zoom_map and not self.scan_in_progress)
        self.zoom_out_button.setEnabled(has_zoom_map and not self.scan_in_progress)
        self.fit_view_button.setEnabled(has_zoom_map and not self.scan_in_progress)
        self.calibrate_button.setEnabled(
            has_map and not live_tab_active and not self.scan_in_progress and not has_scale
        )
        self.delete_scale_button.setEnabled(can_use_session and not live_tab_active and has_scale)
        self.update_save_action_state()
        self.refresh_live_controls()
        self.update_point_action_state()

    def format_ap_memory_status(self):
        summary = get_ap_memory_summary()
        if not summary.get("exists"):
            return self.tr("ap_memory_status_missing")

        total = summary.get("group_count", 0)
        if not total:
            return self.tr("ap_memory_status_empty")

        applied = count_memory_applied_groups(self.session.get_ap_groups()) if self.session else 0
        if applied:
            return self.tr("ap_memory_status_applied", applied=applied, total=total)

        return self.tr("ap_memory_status_saved", count=total)

    def update_save_action_state(self):
        is_dirty = bool(self.session is not None and self.session.dirty)
        self.save_workspace_button.setToolTip(
            self.tr("save_dirty_tooltip") if is_dirty else self.tr("save_clean_tooltip")
        )
        if self.save_tool_button is None:
            return

        self.save_tool_button.setObjectName("dirtySaveButton" if is_dirty else "appBarButton")
        self.save_tool_button.style().unpolish(self.save_tool_button)
        self.save_tool_button.style().polish(self.save_tool_button)
        self.save_tool_button.update()
