"""Live map preview rendering and legend handling for the Qt workspace."""

import os

try:
    from PySide6.QtCore import Qt, QThread, QTimer
    from PySide6.QtWidgets import QListWidgetItem
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from ap.groups import (
    build_ap_group_channel_override_map,
    build_ap_group_role_map,
    build_bssid_to_manual_group_map,
    serialize_ap_group_channel_overrides,
    serialize_ap_group_map,
    serialize_ap_group_roles,
)
from app_core.logging import log_event
from maps.config import MapConfig
from qt_ui.qt_live_map import LiveMapRenderWorker, create_marker_icon, qimage_to_pil_image


class LivePreviewMixin:
    def invalidate_live_preview(self):
        self.live_generation += 1
        self.live_dirty = bool(self.live_rendering)

    def is_current_live_result(self, request):
        return request is None or request == (self.session, self.live_generation)

    def on_workspace_tab_changed(self, index):
        if index != 0:
            self.set_boundaries_mode_enabled(False, show_status=False)
        self.refresh_session_labels()
        if index == 1:
            self.maybe_update_live_preview()

    def on_live_option_changed(self):
        self.invalidate_live_preview()
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
            self.invalidate_live_preview()
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
            boundary_mask_image=self.current_boundary_mask_image(),
        )
        worker.request = (self.session, self.live_generation)
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

        return bool(self.live_ssid_combo.currentText())

    def build_live_map_config(self):
        groups = self.session.get_ap_groups() if self.session is not None else []
        ap_group_map = serialize_ap_group_map(build_bssid_to_manual_group_map(groups, confirmed_only=True))
        ap_group_roles = serialize_ap_group_roles(build_ap_group_role_map(groups))
        ap_group_channel_overrides = serialize_ap_group_channel_overrides(
            build_ap_group_channel_override_map(groups)
        )
        map_type = self.current_combo_value(self.live_map_type_combo, "signal")
        ap_group_filter = (
            self.current_combo_value(self.live_ap_group_combo, "")
            if map_type in {"signal", "channel"}
            else ""
        )
        return MapConfig(
            ssid=self.live_ssid_combo.currentText(),
            band=self.current_combo_value(self.live_band_combo, "all"),
            map_type=map_type,
            interference_mode=self.current_combo_value(self.live_interference_mode_combo, "intra_ssid"),
            interpolation=self.current_combo_value(self.live_interpolation_combo, "rbf"),
            aggregation=self.current_combo_value(self.live_aggregation_combo, "max"),
            color_scale=self.current_combo_value(self.live_color_scale_combo, "fixed"),
            point_label_mode=self.current_combo_value(self.live_point_labels_combo, "auto"),
            usable_only=self.live_usable_check.isChecked(),
            survey_bounds=self.live_survey_bounds_check.isChecked() or self.has_manual_boundaries_mask(),
            smoothing_sigma=float(self.live_smoothing_spin.value()),
            max_distance_px=self.current_live_max_distance_px(),
            ap_group_filter=ap_group_filter,
            ap_group_map=ap_group_map,
            ap_group_roles=ap_group_roles,
            ap_group_channel_overrides=ap_group_channel_overrides,
        ).normalized()

    def get_current_ap_group_map(self):
        if self.session is None:
            return {}

        return build_bssid_to_manual_group_map(self.session.get_ap_groups(), confirmed_only=True)

    def get_current_ap_group_roles(self):
        if self.session is None:
            return {}

        return build_ap_group_role_map(self.session.get_ap_groups())

    def get_current_ap_group_channel_overrides(self):
        if self.session is None:
            return {}

        return build_ap_group_channel_override_map(self.session.get_ap_groups())

    def build_export_default_config(self):
        if self.session is None:
            return MapConfig()

        ssids = self.session.get_ssids()
        current_ssid = self.live_ssid_combo.currentText()
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
            survey_bounds=self.live_survey_bounds_check.isChecked() or self.has_manual_boundaries_mask(),
            smoothing_sigma=float(self.live_smoothing_spin.value()),
            max_distance_px=self.current_live_max_distance_px(),
            ap_group_filter=ap_group_filter,
            ap_group_map=serialize_ap_group_map(build_bssid_to_manual_group_map(groups, confirmed_only=True)),
            ap_group_roles=serialize_ap_group_roles(build_ap_group_role_map(groups)),
            ap_group_channel_overrides=serialize_ap_group_channel_overrides(
                build_ap_group_channel_override_map(groups)
            ),
        ).normalized()

    def current_boundary_mask_image(self):
        if not self.has_manual_boundaries_mask():
            return None

        image = self.floorplan_view.get_boundaries_mask_image_copy()
        return qimage_to_pil_image(image)

    def build_live_renderer_translations(self):
        return {
            "signal_title": self.tr("map_type_signal"),
            "interference_title": self.tr("map_type_interference"),
            "channel_title": self.tr("map_type_channel"),
            "dominant_title": self.tr("map_type_dominant"),
            "risk": self.tr("interference_top_risk"),
            "rf_unknown": self.tr("advisor_rf_unknown"),
            "serving_ap": self.tr("interference_summary_serving_ap"),
            "serving_signal": self.tr("interference_summary_serving_dbm"),
            "serving_channel": self.tr("interference_summary_serving_channel"),
            "interferer": self.tr("interference_summary_interferer"),
            "interferer_ssid": self.tr("interference_summary_interferer_ssid"),
            "interferer_signal": self.tr("interference_summary_interferer_dbm"),
            "interferer_channel": self.tr("interference_summary_interferer_channel"),
            "interference_overlap": self.tr("interference_overlap"),
            "interference_contributors": self.tr("interference_contributors"),
            "interference_ignored": self.tr("interference_ignored"),
            "interference_ignored_same_ap": self.tr("interference_ignored_same_ap"),
            "interference_ignored_test_ap": self.tr("interference_ignored_test_ap"),
            "channel_change": self.tr("interference_channel_change"),
            "channel_change_note": self.tr("interference_channel_change_note"),
            "channel_change_manual_note": self.tr("interference_channel_change_manual_note"),
            "source_rows": self.tr("rows"),
            "signal": self.tr("signal"),
            "coverage_aggregation": self.tr("coverage_aggregation"),
            "aggregation_max": self.tr("aggregation_max"),
            "aggregation_mean": self.tr("aggregation_mean"),
            "aggregation_median": self.tr("aggregation_median"),
            "samples": self.tr("samples"),
            "scan_confidence": self.tr("scan_confidence"),
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
            "second_channel": self.tr("second_channel"),
            "second_signal": self.tr("second_signal"),
            "second_samples": self.tr("second_samples"),
            "second_confidence": self.tr("second_confidence"),
            "signal_delta": self.tr("signal_delta"),
            "roaming_overlap": self.tr("roaming_overlap"),
            "dominant_map_roaming_overlap": self.tr("dominant_map_roaming_overlap"),
            "ap_position_warning_legend": self.tr("ap_position_warning_legend"),
            "ap_position_distance": self.tr("ap_position_distance"),
            "ap_position_nearest": self.tr("ap_position_nearest"),
            "ap_position_analysis": self.tr("ap_position_analysis"),
            "_measurement_system": self.measurement_system,
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
            "wifi_ap_tooltip_title": self.tr("wifi_ap_tooltip_title"),
            "ap_alias_group": self.tr("ap_alias_group"),
            "ap_alias_value": self.tr("ap_alias_value"),
            "ap_alias_bssids": self.tr("ap_alias_bssids"),
            "ap_alias_ssids": self.tr("ap_alias_ssids"),
            "ap_alias_channels": self.tr("ap_alias_channels"),
            "ap_alias_bands": self.tr("ap_alias_bands"),
            "ap_group_metadata_vendor": self.tr("ap_group_metadata_vendor"),
            "ap_group_metadata_model": self.tr("ap_group_metadata_model"),
            "ap_group_metadata_mounting": self.tr("ap_group_metadata_mounting"),
            "ap_group_metadata_expected_bands": self.tr("ap_group_metadata_expected_bands"),
            "ap_group_metadata_expected_channels": self.tr("ap_group_metadata_expected_channels"),
            "ap_group_metadata_coverage_scope": self.tr("ap_group_metadata_coverage_scope"),
            "ap_group_metadata_coverage_radius": self.tr("ap_group_metadata_coverage_radius"),
            "tooltip_section_location": self.tr("tooltip_section_location"),
            "tooltip_section_signal": self.tr("tooltip_section_signal"),
            "tooltip_section_networks": self.tr("tooltip_section_networks"),
            "tooltip_section_identity": self.tr("tooltip_section_identity"),
            "tooltip_section_radio": self.tr("tooltip_section_radio"),
            "tooltip_section_metadata": self.tr("tooltip_section_metadata"),
            "tooltip_section_position": self.tr("tooltip_section_position"),
            "tooltip_section_analysis": self.tr("tooltip_section_analysis"),
            "tooltip_section_reference": self.tr("tooltip_section_reference"),
            "tooltip_section_interference": self.tr("tooltip_section_interference"),
            "tooltip_section_serving_ap": self.tr("tooltip_section_serving_ap"),
            "tooltip_section_interferer": self.tr("tooltip_section_interferer"),
            "tooltip_section_dominant_ap": self.tr("tooltip_section_dominant_ap"),
            "tooltip_section_second_ap": self.tr("tooltip_section_second_ap"),
        }

    def finish_live_preview(self, payload, request=None):
        if not self.is_current_live_result(request):
            log_event("qt stale live render discarded", logger_name="main")
            return
        if self.live_thread is None:
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

    def fail_live_preview(self, message, request=None):
        if not self.is_current_live_result(request):
            return
        if self.live_thread is None:
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
            self.live_rendering = False
            self.refresh_session_labels()
            if self.live_dirty and self.live_auto_check.isChecked():
                self.live_dirty = False
                QTimer.singleShot(0, self.maybe_update_live_preview)
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
            self.fit_live_legend_width(scale_payload.get("items", []))
            return

        if kind == "gradient":
            self.live_legend_user_resized = False
            self.live_legend_frame.hide()
            self.live_view.set_gradient_legend(scale_payload)

    def clear_live_legend(self):
        self.live_legend_title.setText("")
        self.live_legend_list.clear()
        self.clear_live_marker_selection()
        self.live_view.clear_gradient_legend()
        self.live_legend_frame.hide()
        self.live_legend_list.show()
        self.live_legend_user_resized = False

    def clear_live_marker_selection(self):
        self.live_legend_list.clearSelection()
        self.live_legend_list.setCurrentRow(-1)
        self.live_view.clear_marker_highlight()

    def on_live_splitter_moved(self, position, index):
        if not self.live_legend_frame.isHidden() and not self.live_legend_list.isHidden():
            self.live_legend_user_resized = True

    def fit_live_legend_width(self, items):
        labels = [str(item.get("label", "")) for item in items or []]
        title = self.live_legend_title.text()
        metrics = self.live_legend_list.fontMetrics()
        title_metrics = self.live_legend_title.fontMetrics()
        label_width = max([metrics.horizontalAdvance(label) for label in labels] or [0])
        title_width = title_metrics.horizontalAdvance(title) if title else 0
        scrollbar_width = self.live_legend_list.verticalScrollBar().sizeHint().width()
        content_width = max(label_width, title_width)
        target_width = content_width + self.spx(96) + scrollbar_width
        target_width = max(self.spx(240), min(self.spx(760), target_width))
        self.live_legend_frame.setMinimumWidth(self.spx(240))
        self.live_legend_frame.setMaximumWidth(16777215)
        if not self.live_legend_user_resized:
            self.set_live_legend_width(target_width)

    def set_live_legend_width(self, target_width):
        splitter = getattr(self, "live_splitter", None)
        if splitter is None:
            return

        sizes = splitter.sizes()
        total_width = sum(sizes)
        if total_width <= 0:
            self.live_legend_frame.resize(target_width, self.live_legend_frame.height())
            return

        map_min_width = max(self.live_view_container.minimumWidth(), self.spx(260))
        available_legend_width = max(self.live_legend_frame.minimumWidth(), total_width - map_min_width)
        legend_width = min(target_width, available_legend_width)
        if legend_width <= 0:
            return

        was_blocked = splitter.blockSignals(True)
        splitter.setSizes([max(map_min_width, total_width - legend_width), legend_width])
        splitter.blockSignals(was_blocked)

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
