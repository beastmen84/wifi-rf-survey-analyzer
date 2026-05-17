"""Survey session lifecycle and workspace state updates for the Qt app."""

import os
from pathlib import Path

try:
    from PySide6.QtWidgets import QMessageBox
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from app_core.constants import (
    DEFAULT_FLOORPLAN_METADATA_KEY,
    GENERATED_FLOORPLAN_METADATA_KEY,
    MEASUREMENT_SYSTEM_METADATA_KEY,
)
from app_core.logging import log_event, log_exception
from app_core.settings import get_last_survey_directory, save_last_survey_path, save_measurement_system
from app_core.units import (
    MEASUREMENT_SYSTEM_IMPERIAL,
    MEASUREMENT_SYSTEM_METRIC,
    normalize_measurement_system,
)
from ap.memory import count_memory_applied_groups, get_ap_memory_summary
from qt_ui.qt_windowing import get_centered_open_file_name, get_centered_save_file_name
from survey.store import SurveyFormatError, SurveySession, normalize_survey_measurement_system


class SurveySessionWorkflowMixin:
    def show_start_page(self):
        self.stack.setCurrentWidget(self.start_page)
        self.status.clearMessage()

    def show_workspace_page(self):
        self.stack.setCurrentWidget(self.workspace_page)
        self.refresh_session_labels()
        self.refresh_points_table()
        self.maybe_update_live_preview()

    def new_survey(self, from_start_page=False):
        log_event(f"qt new survey start from_start_page={from_start_page}", logger_name="main")
        if not from_start_page and not self.confirm_new_survey_replaces_current():
            log_event("qt new survey cancelled by current-survey prompt", logger_name="main")
            return False

        measurement_system = self.choose_new_survey_measurement_system()
        if not self.set_new_survey_measurement_system(measurement_system):
            log_event("qt new survey cancelled by measurement-system selection", logger_name="main")
            return False

        self.session = SurveySession()
        self.set_session_measurement_system_metadata(self.measurement_system, mark_dirty=False)
        self.generated_floorplans_pending_delete = set()
        self.load_session_ssid_state()
        self.reset_live_option_memory()
        if not self.load_default_floorplan():
            self.floorplan_view.clear_floorplan()
        self.live_view.clear()
        self.show_workspace_page()
        log_event(f"qt new survey done measurement_system={self.measurement_system}", logger_name="main")
        return True

    def confirm_new_survey_replaces_current(self):
        if self.session is None:
            return True
        if self.is_empty_generated_survey():
            return True

        action = self.choose_current_survey_close_action()
        if action == "save":
            return self.save_survey()
        if action == "discard":
            return True
        return False

    def choose_current_survey_close_action(self):
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Question)
        message_box.setWindowTitle(self.tr("new_survey_close_current_title"))
        message_box.setText(self.tr("new_survey_close_current_message"))
        discard_button = message_box.addButton(
            self.tr("discard_changes"),
            QMessageBox.ButtonRole.DestructiveRole,
        )
        save_button = message_box.addButton(
            self.tr("save"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        cancel_button = message_box.addButton(
            self.tr("cancel"),
            QMessageBox.ButtonRole.RejectRole,
        )
        message_box.setDefaultButton(save_button)
        message_box.setEscapeButton(cancel_button)
        message_box.exec()

        clicked_button = message_box.clickedButton()
        if clicked_button == save_button:
            return "save"
        if clicked_button == discard_button:
            return "discard"
        return "cancel"

    def is_empty_generated_survey(self):
        if self.session is None:
            return True

        has_rows = bool(self.session.rows or self.session.raw_scan_rows)
        has_csv = bool(self.session.csv_file)
        has_default_floorplan = self.session.metadata.get(DEFAULT_FLOORPLAN_METADATA_KEY) == "1"
        has_generated_floorplan = self.session.metadata.get(GENERATED_FLOORPLAN_METADATA_KEY) == "1"
        return not has_rows and not has_csv and (has_default_floorplan or has_generated_floorplan)

    def choose_new_survey_measurement_system(self):
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Question)
        message_box.setWindowTitle(self.tr("new_survey_measurement_system_title"))
        message_box.setText(self.tr("new_survey_measurement_system_message"))
        metric_button = message_box.addButton(
            self.tr("measurement_system_metric"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        imperial_button = message_box.addButton(
            self.tr("measurement_system_imperial"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        default_button = (
            imperial_button
            if self.measurement_system == MEASUREMENT_SYSTEM_IMPERIAL
            else metric_button
        )
        message_box.setDefaultButton(default_button)
        message_box.exec()

        clicked_button = message_box.clickedButton()
        if clicked_button == metric_button:
            return MEASUREMENT_SYSTEM_METRIC
        if clicked_button == imperial_button:
            return MEASUREMENT_SYSTEM_IMPERIAL
        return self.measurement_system

    def set_new_survey_measurement_system(self, measurement_system):
        measurement_system = normalize_measurement_system(measurement_system)
        if measurement_system == self.measurement_system:
            return True

        if not save_measurement_system(measurement_system):
            QMessageBox.warning(self, self.tr("warning"), self.tr("settings_save_failed"))
            return False

        self.measurement_system = measurement_system
        return True

    def apply_session_measurement_system(self, mark_dirty=False):
        if self.session is None:
            return self.measurement_system

        measurement_system = normalize_survey_measurement_system(
            self.session.metadata,
            default=self.measurement_system,
        )
        previous_system = self.measurement_system
        self.measurement_system = measurement_system
        self.set_session_measurement_system_metadata(measurement_system, mark_dirty=mark_dirty)
        if measurement_system != previous_system:
            log_event(
                f"qt survey measurement system applied mode={measurement_system}",
                logger_name="main",
            )
        return measurement_system

    def set_session_measurement_system_metadata(self, measurement_system=None, mark_dirty=True):
        if self.session is None:
            return

        measurement_system = normalize_measurement_system(measurement_system or self.measurement_system)
        if hasattr(self.session, "set_measurement_system"):
            self.session.set_measurement_system(measurement_system, mark_dirty=mark_dirty)
            return

        changed = self.session.metadata.get(MEASUREMENT_SYSTEM_METADATA_KEY) != measurement_system
        self.session.metadata[MEASUREMENT_SYSTEM_METADATA_KEY] = measurement_system
        if changed and mark_dirty and hasattr(self.session, "dirty"):
            self.session.dirty = True

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
            log_event(f"qt open survey load start path={csv_file}", logger_name="main")
            self.session = SurveySession(csv_file)
        except SurveyFormatError as exc:
            log_exception("qt open survey invalid format", exc, logger_name="main")
            self.show_survey_format_error(str(exc))
            return False
        except Exception as exc:
            log_exception("qt open survey load failed", exc, logger_name="main")
            raise

        self.generated_floorplans_pending_delete = set()
        self.apply_session_measurement_system(mark_dirty=False)
        self.load_session_ssid_state()
        self.reset_live_option_memory()
        save_last_survey_path(csv_file)
        self.live_view.clear()
        self.show_workspace_page()
        self.load_saved_plan()
        self.status.showMessage(self.tr("active_survey", name=self.session_display_name()))
        log_event(
            (
                f"qt open survey done path={csv_file} rows={len(self.session.rows)} "
                f"raw_rows={len(self.session.raw_scan_rows)} measurement_system={self.measurement_system}"
            ),
            logger_name="main",
        )
        return True

    def save_survey(self):
        if self.session is None:
            return False

        csv_file = self.session.csv_file
        log_event(f"qt save survey start path={csv_file or '<prompt>'}", logger_name="main")
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

        try:
            if not self.materialize_default_floorplan(csv_file):
                return False
        except Exception as exc:
            QMessageBox.warning(self, self.tr("warning"), str(exc))
            log_exception("qt save survey default floorplan materialization failed", exc, logger_name="main")
            return False

        self.set_session_measurement_system_metadata(self.measurement_system, mark_dirty=False)
        self.session.save(csv_file)
        self.cleanup_replaced_generated_floorplans()
        save_last_survey_path(csv_file)
        self.refresh_session_labels()
        self.status.showMessage(self.tr("survey_saved", name=self.session.display_name))
        log_event(
            (
                f"qt save survey done path={csv_file} rows={len(self.session.rows)} "
                f"raw_rows={len(self.session.raw_scan_rows)} measurement_system={self.measurement_system}"
            ),
            logger_name="main",
        )
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
            map_name = (
                self.tr("default_floorplan_name")
                if (
                    self.session.metadata.get(DEFAULT_FLOORPLAN_METADATA_KEY) == "1"
                    or self.session.metadata.get(GENERATED_FLOORPLAN_METADATA_KEY) == "1"
                )
                else os.path.basename(map_file) if map_file else self.tr("no_map")
            )
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
        self.update_floorplan_grid_button_state()
        self.update_boundaries_button_state()
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
