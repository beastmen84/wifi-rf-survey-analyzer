"""Live map preview rendering and legend handling for the Qt workspace."""

import os

try:
    from PySide6.QtCore import Qt, QThread, QTimer
    from PySide6.QtWidgets import QListWidgetItem
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from ap.groups import (
    build_ap_group_role_map,
    build_bssid_to_manual_group_map,
    serialize_ap_group_map,
    serialize_ap_group_roles,
)
from app_logging import log_event
from map_config import MapConfig
from qt_ui.qt_live_map import LiveMapRenderWorker, create_marker_icon


class LivePreviewMixin:
    def on_workspace_tab_changed(self, index):
        self.refresh_session_labels()
        if index == 1:
            self.maybe_update_live_preview()

    def on_live_option_changed(self):
        self.refresh_session_labels()
        self.maybe_update_live_preview()

    def maybe_update_live_preview(self):
        if self.tabs.currentIndex() != 1:
            return
        if not self.live_auto_check.isChecked():
            return
        self.update_live_preview()

    def update_live_preview(self):
        if not self.can_render_live_preview():
            self.live_view.clear()
            self.live_status_label.setText(self.tr("live_preview_empty"))
            self.clear_live_legend()
            self.refresh_live_controls()
            return

        if self.live_rendering:
            self.live_dirty = True
            return

        map_file = self.session.metadata.get("map_file", "")
        config = self.build_live_map_config()
        translations = self.build_live_renderer_translations()
        self.live_rendering = True
        self.live_dirty = False
        self.live_status_label.setText(self.tr("live_preview_rendering"))
        self.refresh_session_labels()

        thread = QThread(self)
        worker = LiveMapRenderWorker(
            self.session.rows,
            map_file,
            config,
            translations,
            aliases=self.session.get_ap_aliases(),
            ap_groups=self.session.get_ap_groups(),
            px_per_meter=self.get_px_per_meter(),
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self.finish_live_preview)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(self.fail_live_preview)
        worker.failed.connect(thread.quit)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(self.cleanup_live_render_thread)
        thread.finished.connect(thread.deleteLater)
        self.live_thread = thread
        self.live_worker = worker
        thread.start()

    def can_render_live_preview(self):
        if self.session is None:
            return False

        map_file = self.session.metadata.get("map_file", "")
        if not map_file or not os.path.exists(map_file):
            return False

        point_count = len(self.session.get_point_summaries())
        map_type = self.current_combo_value(self.live_map_type_combo, "signal")
        required_points = 1 if map_type in {"channel", "dominant"} else 3
        if point_count < required_points:
            return False

        return bool(self.live_ssid_combo.currentText().strip())

    def build_live_map_config(self):
        groups = self.session.get_ap_groups() if self.session is not None else []
        ap_group_map = serialize_ap_group_map(build_bssid_to_manual_group_map(groups))
        ap_group_roles = serialize_ap_group_roles(build_ap_group_role_map(groups))
        map_type = self.current_combo_value(self.live_map_type_combo, "signal")
        ap_group_filter = (
            self.current_combo_value(self.live_ap_group_combo, "")
            if map_type in {"signal", "channel"}
            else ""
        )
        return MapConfig(
            ssid=self.live_ssid_combo.currentText().strip(),
            band=self.current_combo_value(self.live_band_combo, "all"),
            map_type=map_type,
            interference_mode=self.current_combo_value(self.live_interference_mode_combo, "intra_ssid"),
            interpolation=self.current_combo_value(self.live_interpolation_combo, "rbf"),
            aggregation=self.current_combo_value(self.live_aggregation_combo, "max"),
            color_scale=self.current_combo_value(self.live_color_scale_combo, "fixed"),
            point_label_mode=self.current_combo_value(self.live_point_labels_combo, "auto"),
            usable_only=self.live_usable_check.isChecked(),
            smoothing_sigma=float(self.live_smoothing_spin.value()),
            max_distance_px=self.current_live_max_distance_px(),
            ap_group_filter=ap_group_filter,
            ap_group_map=ap_group_map,
            ap_group_roles=ap_group_roles,
        ).normalized()

    def get_current_ap_group_map(self):
        if self.session is None:
            return {}

        return build_bssid_to_manual_group_map(self.session.get_ap_groups())

    def get_current_ap_group_roles(self):
        if self.session is None:
            return {}

        return build_ap_group_role_map(self.session.get_ap_groups())

    def build_export_default_config(self):
        if self.session is None:
            return MapConfig()

        ssids = self.session.get_ssids()
        current_ssid = self.live_ssid_combo.currentText().strip()
        if current_ssid not in ssids:
            current_ssid = ssids[0] if ssids else ""

        groups = self.session.get_ap_groups()
        map_type = self.current_combo_value(self.live_map_type_combo, "signal")
        ap_group_filter = (
            self.current_combo_value(self.live_ap_group_combo, "")
            if map_type in {"signal", "channel"}
            else ""
        )
        return MapConfig(
            ssid=current_ssid,
            band=self.current_combo_value(self.live_band_combo, "all"),
            map_type=map_type,
            interference_mode=self.current_combo_value(self.live_interference_mode_combo, "intra_ssid"),
            interpolation=self.current_combo_value(self.live_interpolation_combo, "rbf"),
            aggregation=self.current_combo_value(self.live_aggregation_combo, "max"),
            color_scale=self.current_combo_value(self.live_color_scale_combo, "fixed"),
            point_label_mode=self.current_combo_value(self.live_point_labels_combo, "auto"),
            usable_only=self.live_usable_check.isChecked(),
            smoothing_sigma=float(self.live_smoothing_spin.value()),
            max_distance_px=self.current_live_max_distance_px(),
            ap_group_filter=ap_group_filter,
            ap_group_map=serialize_ap_group_map(build_bssid_to_manual_group_map(groups)),
            ap_group_roles=serialize_ap_group_roles(build_ap_group_role_map(groups)),
        ).normalized()

    def build_live_renderer_translations(self):
        return {
            "signal_title": self.tr("map_type_signal"),
            "interference_title": self.tr("map_type_interference"),
            "channel_title": self.tr("map_type_channel"),
            "dominant_title": self.tr("map_type_dominant"),
            "risk": self.tr("interference_top_risk"),
            "serving_ap": self.tr("interference_summary_serving_ap"),
            "serving_channel": self.tr("interference_summary_serving_channel"),
            "interferer": self.tr("interference_summary_interferer"),
            "interferer_channel": self.tr("interference_summary_interferer_channel"),
            "source_rows": self.tr("rows"),
            "reference_ap": self.tr("reference_ap"),
            "reference_channel": self.tr("reference_channel"),
            "ap_group_role": self.tr("ap_group_role"),
            "ap_group_role_internal": self.tr("ap_group_role_internal"),
            "ap_group_role_external": self.tr("ap_group_role_external"),
            "ap_group_role_interferer": self.tr("ap_group_role_interferer"),
            "ap_group_role_test": self.tr("ap_group_role_test"),
            "best": self.tr("best"),
            "confidence": self.tr("confidence"),
            "second_ap": self.tr("second_ap"),
            "second_ap_role": self.tr("second_ap_role"),
            "second_confidence": self.tr("second_confidence"),
            "roaming_overlap": self.tr("dominant_map_roaming_overlap"),
            "ap_position_warning_legend": self.tr("ap_position_warning_legend"),
            "ap_position_distance": self.tr("ap_position_distance"),
            "ap_position_nearest": self.tr("ap_position_nearest"),
            "ap_position_analysis": self.tr("ap_position_analysis"),
            "ap_position_distance_m": self.tr("ap_position_distance_m", distance="{distance}"),
            "ap_position_distance_px": self.tr("ap_position_distance_px", distance="{distance}"),
            "ap_position_ok": self.tr("ap_position_ok"),
            "ap_position_no_scale": self.tr("ap_position_no_scale"),
            "ap_position_strong_far": self.tr("ap_position_strong_far"),
            "ap_position_weak_close": self.tr("ap_position_weak_close"),
            "ap_position_unexpected_dominant": self.tr("ap_position_unexpected_dominant"),
            "ap_position_unknown_warning": self.tr("ap_position_unknown_warning"),
            "ap_position_marker_title": self.tr("ap_group_position_tooltip_title"),
            "ap_group": self.tr("ap_alias_group"),
            "ap_label": self.tr("ap_label"),
        }

    def finish_live_preview(self, payload):
        self.live_rendering = False
        log_event("qt live render finished", logger_name="main")
        if payload:
            self.live_view.set_payload(payload)
            self.update_live_legend(payload.get("scale_payload"))
            self.live_status_label.setText(self.format_live_status(payload))
        else:
            self.live_view.clear()
            self.clear_live_legend()
            self.live_status_label.setText(self.tr("live_preview_insufficient"))
        self.refresh_session_labels()

        if self.live_dirty and self.live_auto_check.isChecked():
            QTimer.singleShot(0, self.update_live_preview)

    def fail_live_preview(self, message):
        self.live_rendering = False
        log_event(f"qt live render failed message={message}", logger_name="main")
        self.live_status_label.setText(f"{self.tr('error')}: {message}")
        self.clear_live_legend()
        self.refresh_session_labels()

    def cleanup_live_render_thread(self):
        finished_thread = self.sender()
        if finished_thread is self.live_thread:
            self.live_thread = None
            self.live_worker = None
        log_event("qt live render thread cleaned up", logger_name="main")

    def format_live_status(self, payload):
        return self.tr("live_preview_updated")

    def update_live_legend(self, scale_payload):
        self.live_legend_list.clear()
        self.live_view.clear_gradient_legend()
        if not scale_payload:
            self.clear_live_legend()
            return

        self.live_legend_title.setText(str(scale_payload.get("title") or ""))
        kind = scale_payload.get("kind")
        if kind == "swatches":
            self.live_legend_frame.show()
            self.live_legend_list.show()
            for item in scale_payload.get("items", []):
                list_item = QListWidgetItem(str(item.get("label", "")))
                list_item.setIcon(create_marker_icon(
                    item.get("color", "#7f8c8d"),
                    shape=item.get("shape", "circle"),
                    outline_only=bool(item.get("outline_only")),
                ))
                list_item.setData(Qt.ItemDataRole.UserRole, dict(item))
                self.live_legend_list.addItem(list_item)
            return

        if kind == "gradient":
            self.live_legend_frame.hide()
            self.live_view.set_gradient_legend(scale_payload)

    def clear_live_legend(self):
        self.live_legend_title.setText("")
        self.live_legend_list.clear()
        self.clear_live_marker_selection()
        self.live_view.clear_gradient_legend()
        self.live_legend_frame.hide()
        self.live_legend_list.show()

    def clear_live_marker_selection(self):
        self.live_legend_list.clearSelection()
        self.live_legend_list.setCurrentRow(-1)
        self.live_view.clear_marker_highlight()

    def on_live_legend_item_clicked(self, item):
        payload = item.data(Qt.ItemDataRole.UserRole) if item else None
        marker_id = payload.get("marker_id") if isinstance(payload, dict) else ""
        if not marker_id or not self.live_view.highlight_marker(marker_id):
            self.clear_live_marker_selection()

    def on_live_legend_item_double_clicked(self, item):
        payload = item.data(Qt.ItemDataRole.UserRole) if item else None
        marker_id = payload.get("marker_id") if isinstance(payload, dict) else ""
        if marker_id and self.live_view.focus_marker(marker_id):
            return
        self.clear_live_marker_selection()
