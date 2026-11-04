"""Live map option controls for the Qt workspace."""

import math

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import QComboBox, QDoubleSpinBox
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from ap.groups import (
    AP_ROLE_TEST,
    build_ap_group_role_map,
    build_bssid_to_manual_group_map,
    format_ap_label,
    normalize_ap_role,
    resolve_ap_group_key,
)
from app_core.constants import (
    HEATMAP_ADAPTIVE_MAX_DISTANCE_MAX_METERS,
    HEATMAP_ADAPTIVE_MAX_DISTANCE_MIN_METERS,
    HEATMAP_ADAPTIVE_MAX_DISTANCE_MULTIPLIER,
    HEATMAP_MAX_DISTANCE_PX,
    HEATMAP_SMOOTHING_SIGMA,
)
from app_core.units import (
    distance_unit_label,
    display_units_to_meters,
    meters_to_display_units,
)
from wifi.band import row_matches_band


class LiveOptionsMixin:
    def refresh_live_static_options(self):
        self.set_combo_items(
            self.live_map_type_combo,
            [
                ("signal", self.tr("map_type_signal")),
                ("interference", self.tr("map_type_interference")),
                ("channel", self.tr("map_type_channel")),
                ("dominant", self.tr("map_type_dominant")),
            ],
        )
        self.refresh_live_band_options(self.current_combo_value(self.live_map_type_combo, "signal"))
        self.set_combo_items(
            self.live_aggregation_combo,
            [
                ("max", self.tr("aggregation_max")),
                ("median", self.tr("aggregation_median")),
                ("mean", self.tr("aggregation_mean")),
            ],
        )
        self.set_combo_items(
            self.live_color_scale_combo,
            [
                ("fixed", self.tr("color_scale_fixed")),
                ("auto", self.tr("color_scale_auto")),
            ],
        )
        self.set_combo_items(
            self.live_interpolation_combo,
            [
                ("rbf", self.tr("interpolation_rbf")),
                ("linear", self.tr("interpolation_linear")),
            ],
        )
        self.set_combo_items(
            self.live_interference_mode_combo,
            [
                ("intra_ssid", self.tr("interference_mode_intra_ssid")),
                ("all", self.tr("interference_mode_all")),
            ],
        )
        self.set_combo_items(
            self.live_point_labels_combo,
            [
                ("auto", self.tr("point_labels_auto")),
                ("all", self.tr("point_labels_all")),
                ("none", self.tr("point_labels_none")),
            ],
        )

    def live_band_items_for_map_type(self, map_type):
        items = [
            ("all", self.tr("all_bands_option")),
            ("2.4", "2.4 GHz"),
            ("5", "5 GHz"),
            ("6", "6 GHz"),
        ]
        if map_type == "interference":
            return items[1:]
        return items

    def refresh_live_band_options(self, map_type=None, preferred_band=None):
        map_type = map_type or self.current_combo_value(self.live_map_type_combo, "signal")
        current_band = (
            preferred_band
            if preferred_band is not None
            else self.current_combo_value(self.live_band_combo, "all")
        )
        items = self.live_band_items_for_map_type(map_type)
        available = {str(value) for value, _label in items}
        if current_band not in available:
            current_band = "2.4" if "2.4" in available else (str(items[0][0]) if items else "")
        self.set_combo_items(self.live_band_combo, items, current_value=current_band)

    def update_live_max_distance_label(self):
        if not hasattr(self, "live_max_distance_label"):
            return

        if self.get_px_per_meter():
            self.live_max_distance_label.setText(
                self.tr("max_distance_unit", unit=distance_unit_label(self.measurement_system))
            )
        else:
            self.live_max_distance_label.setText(self.tr("max_distance_px"))

    def current_live_max_distance_px(self):
        px_per_meter = self.get_px_per_meter() or self.live_distance_last_px_per_meter
        if getattr(self, "live_distance_spin_uses_meters", False) and px_per_meter:
            meters = display_units_to_meters(self.live_max_distance_spin.value(), self.measurement_system)
            return max(1, int(round(meters * px_per_meter)))

        return max(1, int(round(self.live_max_distance_spin.value())))

    def set_live_max_distance_px_silent(self, max_distance_px):
        px_per_meter = self.get_px_per_meter()
        self.live_max_distance_spin.blockSignals(True)
        try:
            if px_per_meter:
                self.live_distance_spin_uses_meters = True
                self.live_distance_last_px_per_meter = px_per_meter
                self.live_max_distance_spin.setRange(
                    meters_to_display_units(1.0, self.measurement_system),
                    meters_to_display_units(50.0, self.measurement_system),
                )
                self.live_max_distance_spin.setSingleStep(
                    1.0 if distance_unit_label(self.measurement_system) == "ft" else 0.5
                )
                self.live_max_distance_spin.setDecimals(1)
                self.live_max_distance_spin.setSuffix(f" {distance_unit_label(self.measurement_system)}")
                meters = max(1.0, float(max_distance_px) / px_per_meter)
                self.live_max_distance_spin.setValue(meters_to_display_units(meters, self.measurement_system))
            else:
                self.live_distance_spin_uses_meters = False
                self.live_max_distance_spin.setRange(40.0, 1000.0)
                self.live_max_distance_spin.setSingleStep(20.0)
                self.live_max_distance_spin.setDecimals(0)
                self.live_max_distance_spin.setSuffix(" px")
                self.live_max_distance_spin.setValue(float(max_distance_px or HEATMAP_MAX_DISTANCE_PX))
        finally:
            self.live_max_distance_spin.blockSignals(False)
        self.update_live_max_distance_label()

    def set_combo_value_silent(self, combo, value):
        index = combo.findData(value)
        if index < 0 and combo.count():
            index = 0
        if index < 0:
            return

        combo.blockSignals(True)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def default_live_max_distance_px(self):
        px_per_meter = self.get_px_per_meter()
        if px_per_meter:
            adaptive_max_distance_px = estimate_adaptive_live_max_distance_px(
                getattr(self.session, "rows", []),
                px_per_meter,
            )
            if adaptive_max_distance_px:
                return adaptive_max_distance_px

        return HEATMAP_MAX_DISTANCE_PX

    def default_live_option_state(self, map_type):
        return {
            "band": "2.4" if map_type == "interference" else "all",
            "aggregation": "max",
            "color_scale": "fixed",
            "interpolation": "rbf",
            "interference_mode": "intra_ssid",
            "point_label_mode": "auto",
            "ap_group_filter": "",
            "usable_only": False,
            "survey_bounds": False,
            "smoothing_sigma": HEATMAP_SMOOTHING_SIGMA,
            "max_distance_px": self.default_live_max_distance_px(),
        }

    def current_live_option_state(self):
        return {
            "band": self.current_combo_value(self.live_band_combo, "all"),
            "aggregation": self.current_combo_value(self.live_aggregation_combo, "max"),
            "color_scale": self.current_combo_value(self.live_color_scale_combo, "fixed"),
            "interpolation": self.current_combo_value(self.live_interpolation_combo, "rbf"),
            "interference_mode": self.current_combo_value(
                self.live_interference_mode_combo,
                "intra_ssid",
            ),
            "point_label_mode": self.current_combo_value(self.live_point_labels_combo, "auto"),
            "ap_group_filter": self.current_combo_value(self.live_ap_group_combo, ""),
            "usable_only": self.live_usable_check.isChecked(),
            "survey_bounds": (
                False
                if self.has_manual_boundaries_mask()
                else self.live_survey_bounds_check.isChecked()
            ),
            "smoothing_sigma": float(self.live_smoothing_spin.value()),
            "max_distance_px": self.current_live_max_distance_px(),
        }

    def remember_live_option_state(self, map_type=None):
        if self.live_option_state_syncing:
            return

        map_type = map_type or self.current_combo_value(self.live_map_type_combo, "signal")
        self.live_map_option_memory[map_type] = self.current_live_option_state()

    def restore_live_option_state(self, map_type):
        state = dict(self.default_live_option_state(map_type))
        state.update(self.live_map_option_memory.get(map_type, {}))

        self.live_option_state_syncing = True
        try:
            self.refresh_live_band_options(map_type, preferred_band=state.get("band"))
            self.set_combo_value_silent(self.live_aggregation_combo, state.get("aggregation", "max"))
            self.set_combo_value_silent(self.live_color_scale_combo, state.get("color_scale", "fixed"))
            self.set_combo_value_silent(self.live_interpolation_combo, state.get("interpolation", "rbf"))
            self.set_combo_value_silent(
                self.live_interference_mode_combo,
                state.get("interference_mode", "intra_ssid"),
            )
            self.set_combo_value_silent(self.live_point_labels_combo, state.get("point_label_mode", "auto"))
            self.live_smoothing_spin.blockSignals(True)
            self.live_smoothing_spin.setValue(float(state.get("smoothing_sigma", HEATMAP_SMOOTHING_SIGMA)))
            self.live_smoothing_spin.blockSignals(False)
            self.set_live_max_distance_px_silent(state.get("max_distance_px", HEATMAP_MAX_DISTANCE_PX))
            self.live_usable_check.blockSignals(True)
            self.live_usable_check.setChecked(bool(state.get("usable_only", False)))
            self.live_usable_check.blockSignals(False)
            self.live_survey_bounds_check.blockSignals(True)
            self.live_survey_bounds_check.setChecked(
                self.has_manual_boundaries_mask() or bool(state.get("survey_bounds", False))
            )
            self.live_survey_bounds_check.blockSignals(False)
            self.refresh_live_ap_group_filter()
            self.set_combo_value_silent(self.live_ap_group_combo, state.get("ap_group_filter", ""))
        finally:
            self.live_option_state_syncing = False

    def reset_live_option_memory(self):
        self.live_map_option_memory = {}
        self.live_current_map_type = self.current_combo_value(self.live_map_type_combo, "signal")
        self.restore_live_option_state(self.live_current_map_type)

    def set_combo_items(self, combo, items, current_value=None):
        current = combo.currentData() if current_value is None else current_value
        combo.blockSignals(True)
        combo.clear()
        for value, label in items:
            combo.addItem(label, value)
        index = combo.findData(current)
        if index < 0 and combo.count():
            index = 0
        if index >= 0:
            combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def current_combo_value(self, combo, default=""):
        value = combo.currentData()
        return default if value is None else str(value)

    def refresh_live_ap_group_filter(self):
        current_group = self.current_combo_value(self.live_ap_group_combo, "")
        items = [("", self.tr("all_ap_groups_option"))]
        items.extend(self.live_ap_group_filter_items())
        self.set_combo_items(self.live_ap_group_combo, items, current_value=current_group)

    def live_ap_group_filter_items(self):
        if self.session is None:
            return []

        ssid = self.live_ssid_combo.currentText()
        band = self.current_combo_value(self.live_band_combo, "all")
        groups = self.session.get_ap_groups()
        group_map = build_bssid_to_manual_group_map(groups, confirmed_only=True)
        role_map = build_ap_group_role_map(groups)
        aliases = self.session.get_ap_aliases()
        seen_groups = {}

        for row in self.session.rows:
            row_ssid = str(row.get("ssid", ""))
            if ssid and row_ssid != ssid:
                continue
            if not self.row_matches_live_band(row, band):
                continue

            bssid = str(row.get("bssid", "")).strip()
            if not bssid:
                continue
            group_id = resolve_ap_group_key(bssid, group_map)
            if normalize_ap_role(role_map.get(str(group_id))) == AP_ROLE_TEST:
                continue

            group_entry = seen_groups.setdefault(str(group_id), {"bssids": []})
            if bssid not in group_entry["bssids"]:
                group_entry["bssids"].append(bssid)

        return [
            (group_id, self.format_live_ap_group_filter_label(group_id, entry["bssids"], aliases))
            for group_id, entry in sorted(
                seen_groups.items(),
                key=lambda item: self.format_live_ap_group_filter_label(
                    item[0],
                    item[1]["bssids"],
                    aliases,
                ).casefold(),
            )
        ]

    def row_matches_live_band(self, row, band):
        return row_matches_band(row, band)

    def format_live_ap_group_filter_label(self, group_id, bssids, aliases):
        display_name = self.get_ap_group_display_name(group_id)
        if display_name and display_name != str(group_id):
            return display_name

        if bssids:
            label = format_ap_label(bssids[0], aliases, group_id)
            extra_count = len(bssids) - 1
            return f"{label} +{extra_count}" if extra_count > 0 else label

        return str(group_id or "-")

    def refresh_live_controls(self):
        ssids = []
        if self.session is not None:
            ssids = self.session.get_ssids()

        current_ssid = self.live_ssid_combo.currentText()
        preferred_ssid = self.preferred_live_ssid(ssids, current_ssid=current_ssid)
        self.live_ssid_combo.blockSignals(True)
        self.live_ssid_combo.clear()
        self.live_ssid_combo.addItems(ssids)
        if preferred_ssid and preferred_ssid in ssids:
            self.live_ssid_combo.setCurrentText(preferred_ssid)
        elif ssids:
            self.live_ssid_combo.setCurrentIndex(0)
        self.live_ssid_combo.blockSignals(False)
        self.refresh_live_ap_group_filter()

        can_render = self.can_use_live_controls(ssids)
        for widget in (
            self.live_ssid_combo,
            self.live_band_combo,
            self.live_map_type_combo,
            self.live_aggregation_combo,
            self.live_color_scale_combo,
            self.live_interpolation_combo,
            self.live_interference_mode_combo,
            self.live_smoothing_spin,
            self.live_max_distance_spin,
            self.live_point_labels_combo,
            self.live_ap_group_combo,
            self.live_usable_check,
            self.live_survey_bounds_check,
            self.live_auto_check,
            self.live_options_toggle_button,
        ):
            widget.setEnabled(can_render)
        self.live_update_button.setEnabled(can_render and not self.live_rendering)
        self.live_report_export_button.setEnabled(can_render and not self.live_rendering)
        self.update_live_option_state()

        if not can_render and not self.live_rendering:
            self.live_status_label.setText(self.tr("live_preview_empty"))
            self.clear_live_legend()

    def preferred_live_ssid(self, ssids, current_ssid=""):
        if not ssids:
            return ""

        ssids_by_key = {
            str(ssid): str(ssid)
            for ssid in ssids
            if str(ssid)
        }
        current_key = str(current_ssid or "")
        if current_key in ssids_by_key:
            return ssids_by_key[current_key]

        connected_ssid = self.preferred_connected_live_ssid(ssids)
        if connected_ssid:
            return connected_ssid

        relevant = {
            str(ssid)
            for ssid in getattr(self, "relevant_ssids", set()) or []
            if str(ssid)
        }
        for ssid in ssids:
            if str(ssid) in relevant:
                return ssid

        return ssids[0]

    def preferred_connected_live_ssid(self, ssids):
        if self.session is None:
            return ""

        ssid_order = {
            str(ssid): index
            for index, ssid in enumerate(ssids)
            if str(ssid)
        }
        connected_counts = {}
        for row in self.session.rows:
            if not is_truthy_flag(row.get("is_connected")):
                continue

            key = str(row.get("ssid", ""))
            if key in ssid_order:
                connected_counts[key] = connected_counts.get(key, 0) + 1

        if not connected_counts:
            return ""

        best_key = max(
            connected_counts,
            key=lambda key: (connected_counts[key], -ssid_order.get(key, len(ssids))),
        )
        return str(ssids[ssid_order[best_key]])

    def can_use_live_controls(self, ssids=None):
        has_session = self.session is not None
        has_map = bool(has_session and self.session.metadata.get("map_file"))
        has_rows = bool(has_session and self.session.get_point_summaries())
        if ssids is None:
            ssids = self.session.get_ssids() if has_session else []
        return has_session and has_map and has_rows and bool(ssids) and not self.scan_in_progress

    def update_live_option_state(self):
        map_type = self.current_combo_value(self.live_map_type_combo, "signal")
        previous_map_type = self.live_current_map_type
        map_type_changed = map_type != previous_map_type
        if map_type_changed:
            self.remember_live_option_state(previous_map_type)
            self.live_current_map_type = map_type
            self.live_legend_user_resized = False
            self.restore_live_option_state(map_type)
        else:
            self.refresh_live_band_options(map_type)
            self.refresh_live_ap_group_filter()

        is_signal = map_type == "signal"
        is_interference = map_type == "interference"
        is_channel = map_type == "channel"
        is_dominant = map_type == "dominant"
        is_continuous = is_signal or is_interference
        has_manual_boundaries = self.has_manual_boundaries_mask()
        self.set_live_max_distance_px_silent(self.current_live_max_distance_px())
        self.reflow_live_option_controls(map_type)
        can_use_controls = self.can_use_live_controls()
        self.set_labeled_live_control_state(
            self.live_band_label,
            self.live_band_combo,
            visible=is_signal or is_interference or is_channel or is_dominant,
            enabled=can_use_controls,
        )
        self.set_labeled_live_control_state(
            self.live_aggregation_label,
            self.live_aggregation_combo,
            visible=is_signal,
            enabled=can_use_controls and is_signal,
        )
        self.set_labeled_live_control_state(
            self.live_interference_mode_label,
            self.live_interference_mode_combo,
            visible=is_interference,
            enabled=can_use_controls and is_interference,
        )
        self.set_labeled_live_control_state(
            self.live_interpolation_label,
            self.live_interpolation_combo,
            visible=is_continuous,
            enabled=can_use_controls and is_continuous,
        )
        self.set_labeled_live_control_state(
            self.live_color_scale_label,
            self.live_color_scale_combo,
            visible=is_continuous,
            enabled=can_use_controls and is_continuous,
        )
        self.set_labeled_live_control_state(
            self.live_smoothing_label,
            self.live_smoothing_spin,
            visible=is_continuous,
            enabled=can_use_controls and is_continuous,
        )
        self.set_labeled_live_control_state(
            self.live_max_distance_label,
            self.live_max_distance_spin,
            visible=is_continuous,
            enabled=can_use_controls and is_continuous,
        )
        self.set_labeled_live_control_state(
            self.live_point_labels_label,
            self.live_point_labels_combo,
            visible=is_channel or is_dominant,
            enabled=can_use_controls and (is_channel or is_dominant),
        )
        self.live_usable_check.setVisible(is_signal)
        self.live_usable_check.setEnabled(can_use_controls and is_signal)
        if has_manual_boundaries:
            self.live_survey_bounds_check.blockSignals(True)
            self.live_survey_bounds_check.setChecked(True)
            self.live_survey_bounds_check.blockSignals(False)
        self.live_survey_bounds_check.setVisible(is_continuous)
        self.live_survey_bounds_check.setEnabled(
            can_use_controls and is_continuous and not has_manual_boundaries
        )
        can_filter_ap_group = (
            can_use_controls
            and (is_signal or is_channel)
            and self.live_ap_group_combo.count() > 1
        )
        self.set_labeled_live_control_state(
            self.live_ap_group_label,
            self.live_ap_group_combo,
            visible=(is_signal or is_channel) and self.live_ap_group_combo.count() > 1,
            enabled=can_filter_ap_group,
        )
        self.remember_live_option_state(map_type)

    def set_labeled_live_control_state(self, label, widget, visible, enabled):
        label.setVisible(visible)
        widget.setVisible(visible)
        label.setEnabled(enabled)
        widget.setEnabled(enabled)

    def update_live_option_dropdown_widths(self, combos):
        text_width = 0
        for combo in combos:
            metrics = combo.fontMetrics()
            text_width = max(text_width, metrics.horizontalAdvance(combo.currentText()))
            for index in range(combo.count()):
                text_width = max(text_width, metrics.horizontalAdvance(combo.itemText(index)))

        width = max(self.spx(132), min(self.spx(280), text_width + self.spx(86)))
        for combo in combos:
            combo.setFixedWidth(width)
        return width

    def reflow_live_option_controls(self, map_type):
        for widget in self.live_option_widgets:
            self.live_options_layout.removeWidget(widget)
        for separator in (self.live_options_separator, self.live_checkbox_separator):
            self.live_options_layout.removeWidget(separator)
            separator.hide()

        row = 0
        dropdowns = []
        value_widgets = []

        def add_labeled(label, widget):
            nonlocal row
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.live_options_layout.addWidget(label, row, 0)
            self.live_options_layout.addWidget(widget, row, 1)
            if isinstance(widget, QComboBox):
                dropdowns.append(widget)
            elif isinstance(widget, QDoubleSpinBox):
                value_widgets.append(widget)
            row += 1

        def add_checkbox(widget):
            nonlocal row
            self.live_options_layout.addWidget(widget, row, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)
            row += 1

        def add_separator(separator):
            nonlocal row
            self.live_options_layout.addWidget(separator, row, 0, 1, 2)
            separator.show()
            row += 1

        dropdown_controls = [(self.live_band_label, self.live_band_combo)]
        numeric_controls = []

        if map_type == "signal":
            dropdown_controls.extend(
                [
                    (self.live_aggregation_label, self.live_aggregation_combo),
                    (self.live_color_scale_label, self.live_color_scale_combo),
                    (self.live_interpolation_label, self.live_interpolation_combo),
                ]
            )
            numeric_controls.extend(
                [
                    (self.live_max_distance_label, self.live_max_distance_spin),
                    (self.live_smoothing_label, self.live_smoothing_spin),
                ]
            )
            if self.live_ap_group_combo.count() > 1:
                dropdown_controls.append((self.live_ap_group_label, self.live_ap_group_combo))
        elif map_type == "interference":
            dropdown_controls.extend(
                [
                    (self.live_color_scale_label, self.live_color_scale_combo),
                    (self.live_interference_mode_label, self.live_interference_mode_combo),
                    (self.live_interpolation_label, self.live_interpolation_combo),
                ]
            )
            numeric_controls.extend(
                [
                    (self.live_max_distance_label, self.live_max_distance_spin),
                    (self.live_smoothing_label, self.live_smoothing_spin),
                ]
            )
        elif map_type == "channel":
            dropdown_controls.append((self.live_point_labels_label, self.live_point_labels_combo))
            if self.live_ap_group_combo.count() > 1:
                dropdown_controls.append((self.live_ap_group_label, self.live_ap_group_combo))
        elif map_type == "dominant":
            dropdown_controls.append((self.live_point_labels_label, self.live_point_labels_combo))

        for label, widget in sorted(dropdown_controls, key=lambda pair: pair[0].text().casefold()):
            add_labeled(label, widget)

        if numeric_controls:
            add_separator(self.live_options_separator)
            for label, widget in sorted(numeric_controls, key=lambda pair: pair[0].text().casefold()):
                add_labeled(label, widget)

        if map_type == "signal":
            add_separator(self.live_checkbox_separator)
            add_checkbox(self.live_usable_check)
            add_checkbox(self.live_survey_bounds_check)
        elif map_type == "interference":
            add_separator(self.live_checkbox_separator)
            add_checkbox(self.live_survey_bounds_check)

        control_width = self.update_live_option_dropdown_widths(dropdowns)
        for widget in value_widgets:
            widget.setFixedWidth(control_width)

        if hasattr(self, "live_options_overlay"):
            QTimer.singleShot(0, self.position_live_options_overlay)

def is_truthy_flag(value):
    return str(value or "").strip().casefold() in {"1", "true", "yes", "y", "connected"}


def estimate_adaptive_live_max_distance_px(rows, px_per_meter):
    if not px_per_meter:
        return None

    spacing = survey_point_spacing_percentiles_px(rows)
    if not spacing:
        return None

    median_m = spacing["median"] / px_per_meter
    p75_m = spacing["p75"] / px_per_meter
    p90_m = spacing["p90"] / px_per_meter
    reference_spacing_m = max(p75_m, (median_m + p90_m) / 2.0)
    distance_m = reference_spacing_m * HEATMAP_ADAPTIVE_MAX_DISTANCE_MULTIPLIER
    distance_m = min(
        HEATMAP_ADAPTIVE_MAX_DISTANCE_MAX_METERS,
        max(HEATMAP_ADAPTIVE_MAX_DISTANCE_MIN_METERS, distance_m),
    )
    distance_m = round(distance_m * 2.0) / 2.0
    return max(1, int(round(distance_m * px_per_meter)))


def survey_point_spacing_percentiles_px(rows):
    points = unique_survey_points(rows)
    if len(points) < 4:
        return None

    distances = nearest_neighbor_distances(points)
    if len(distances) < 3:
        return None

    sorted_distances = sorted(distances)
    return {
        "median": percentile(sorted_distances, 50),
        "p75": percentile(sorted_distances, 75),
        "p90": percentile(sorted_distances, 90),
    }


def unique_survey_points(rows):
    points = []
    seen = set()

    for row in rows or []:
        try:
            x = float(row.get("x", ""))
            y = float(row.get("y", ""))
        except (TypeError, ValueError):
            continue

        if not math.isfinite(x) or not math.isfinite(y):
            continue

        key = (x, y)
        if key in seen:
            continue

        seen.add(key)
        points.append(key)

    return points


def nearest_neighbor_distances(points):
    distances = []

    for index, (x, y) in enumerate(points):
        nearest_sq = None
        for other_index, (other_x, other_y) in enumerate(points):
            if index == other_index:
                continue

            distance_sq = ((x - other_x) ** 2) + ((y - other_y) ** 2)
            if nearest_sq is None or distance_sq < nearest_sq:
                nearest_sq = distance_sq

        if nearest_sq is not None:
            distances.append(math.sqrt(nearest_sq))

    return distances


def percentile(sorted_values, percentile_value):
    if not sorted_values:
        return 0.0

    rank = (len(sorted_values) - 1) * (percentile_value / 100.0)
    lower_index = int(math.floor(rank))
    upper_index = int(math.ceil(rank))
    if lower_index == upper_index:
        return sorted_values[lower_index]

    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    return lower_value + ((upper_value - lower_value) * (rank - lower_index))
