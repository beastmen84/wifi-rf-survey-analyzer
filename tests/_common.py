import unittest
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QGraphicsItem, QGraphicsView, QListWidgetItem, QMessageBox, QWidget
from PIL import Image

from app_core.logging import MaxLogLevelFilter
from app_core.restart import build_restart_command
from app_core.settings import (
    get_last_survey_directory,
    get_saved_measurement_system,
    save_last_survey_path,
    save_measurement_system,
)
from app_core.units import (
    MEASUREMENT_SYSTEM_IMPERIAL,
    MEASUREMENT_SYSTEM_METRIC,
    display_units_to_meters,
    format_distance_meters,
    meters_to_display_units,
    normalize_measurement_system,
)
from app_core.constants import RAW_DATA_FILE_METADATA_KEY, SURVEY_FIELDNAMES
from translations.i18n import translate
from ap.groups import (
    AP_MEMORY_APPLIED_KEY,
    AP_ROLE_EXTERNAL,
    AP_ROLE_INTERNAL,
    AP_ROLE_INTERFERER,
    AP_ROLE_TEST,
    AP_COVERAGE_SCOPE_LOCAL,
    build_ap_group_channel_override_map,
    build_ap_group_role_map,
    build_bssid_to_manual_group_map,
    build_default_manual_groups,
    build_manual_ap_group,
    is_local_coverage_metadata,
    merge_new_bssids_into_manual_groups,
    normalize_ap_metadata,
    serialize_ap_group_channel_overrides,
    resolve_ap_group_key,
    serialize_ap_group_map,
    serialize_ap_group_roles,
)
from ap.memory import (
    apply_group_memory_update,
    apply_ap_memory_to_groups,
    clear_ap_memory,
    clear_group_memory_flag,
    count_memory_applied_groups,
    ensure_ap_memory_file,
    get_group_memory_update_fields,
    get_ap_memory_summary,
    load_ap_memory,
    update_ap_memory_from_groups,
)
from ap.checks import (
    AP_CHANNEL_CHANGE_AMBIGUOUS,
    AP_CHANNEL_CHANGE_CLEAN,
    build_ap_channel_changes,
    build_ap_group_conflicts,
)
from ap.metadata import (
    build_ap_metadata_warnings,
    infer_band_from_channel,
    normalize_channel,
    parse_expected_bands,
    parse_expected_channels,
    sort_bands,
    sort_channels,
)
from ap.positioning import (
    AP_POSITION_MISSING,
    AP_POSITION_NO_SCALE,
    AP_POSITION_OK,
    AP_POSITION_STRONG_FAR,
    AP_POSITION_UNEXPECTED_DOMINANT,
    AP_POSITION_WEAK_CLOSE,
    analyze_dominant_ap_position,
)
from maps.heatmap import (
    apply_distance_mask,
    apply_signal_threshold,
    calculate_interference_points,
    channel_overlap_weight,
    channel_width_overlap_weight,
    filter_by_band,
    get_confidence_rbf_smoothing,
    get_channel_map_points,
    get_distance_alpha,
    get_dominant_ap_points,
    get_interference_data_quality,
    get_scan_confidence_values,
    interpolate_signal_grid,
    normalize_confidence_array,
    signal_interference_weight,
    smooth_heatmap_grid,
)
import maps.live_renderer as live_renderer_module
from maps.live_renderer import (
    build_signal_payload,
    clone_cached_result,
    render_live_continuous_map,
    stable_dataframe_fingerprint,
)
from exporting.live_pdf import (
    MapExportResult,
    annotate_dominant_problem_numbers,
    annotate_interference_problem_numbers,
    build_channel_point_legend_items,
    build_dominant_marker_legend_items,
    build_dominant_point_legend_items,
    build_interference_problem_report_pages,
    build_live_pdf_channel_figure,
    build_live_pdf_dominant_figure,
    build_problem_report_pages,
    generate_live_pdf_export,
    get_dominant_problem_df,
    get_interference_problem_df,
)
import matplotlib.pyplot as plt
from maps.config import MapConfig
from qt_ui.qt_quality_dashboard import (
    build_ap_position_quality_by_point,
    build_dashboard_rows,
    build_summary,
    format_point_confidence,
    format_relevant_ssids,
    get_effective_relevant_ssids,
    get_effective_ap_groups,
    format_metric_point_issue,
    is_point_metric_filter,
    point_table_visible_row_count,
    point_rows_for_metric,
    PointRowsDialog,
    RecommendationDetailsDialog,
    detail_row_heights_for_width,
    label_text_height_for_width,
    recommendation_detail_max_height,
    recommendation_detail_scroll_height,
    recommendation_detail_visible_item_count,
    rescan_kpi_labels_for_row,
    quality_status_text_keys,
    resolve_metric_severity,
    split_recommendation_actions,
)
from qt_ui.qt_floorplan import AP_MARKER_BASE_SIZE, FloorplanView, format_ap_tooltip, format_point_tooltip
from qt_ui.qt_ap_groups import (
    APGroupManagerDialog,
    BssidSelectionDialog,
    ConflictDialog,
    EXPECTED_CHANNELS_BY_BAND,
    MetadataDialog,
    infer_expected_channel_bands,
)
from qt_ui.qt_live_map import (
    LIVE_POINT_MARKER_BASE_SIZE,
    LiveGradientLegendWidget,
    LiveMapView,
    build_ap_position_marker_infos,
    build_channel_payload,
    build_dominant_payload,
    build_live_tooltip,
    gradient_stops,
)
import qt_ui.qt_app as qt_app_module
import qt_ui.qt_live_export as qt_live_export_module
from qt_ui.qt_app import WifiHeatmapQtApp
from qt_ui.qt_windowing import pop_modal_dim, push_modal_dim
from maps.quality import (
    QUALITY_GOOD,
    QUALITY_LOW_CONFIDENCE,
    QUALITY_MISSING_RELEVANT,
    QUALITY_SPARSE_DATA,
    QUALITY_UNSTABLE_SIGNAL,
    SCANNER_DETAIL_FALLBACK_BACKEND,
    SCANNER_DETAIL_MISSING_6GHZ_FREQUENCY,
    SCANNER_DETAIL_MISSING_CHANNEL_WIDTH,
    evaluate_point_quality,
    evaluate_scanner_details,
)
from survey.store import (
    SurveyFormatError,
    SurveySession,
    build_raw_scan_file_path,
    get_survey_point_summaries_from_rows,
)
from qt_ui.scaling import (
    detect_screen_resolution,
    effective_scale_for_percent,
    format_ui_scale_diagnostics,
    normalize_ui_scale_mode,
    scale_font,
    scale_percent_for_resolution,
    scale_px,
    ui_scale_diagnostics,
)

TEST_AP_MEMORY_FILE = os.path.join(tempfile.gettempdir(), "wifi_heatmap_test_ap_memory.memory")
os.environ.setdefault("WIFI_HEATMAP_AP_MEMORY_FILE", TEST_AP_MEMORY_FILE)
try:
    os.remove(TEST_AP_MEMORY_FILE)
except OSError:
    pass
from wifi.scanner import (
    annotate_raw_scan_samples,
    merge_wifi_scans,
    normalize_channel_width_mhz,
    parse_lswifi_bss_list,
    parse_netsh_output,
)
from wifi.band import infer_band_from_frequency_mhz, normalize_frequency_mhz



# Shared fixtures and helpers for the split test modules.
class FakeLswifiPhy:
    def __init__(self, amendment="", name=""):
        self.amendment = amendment
        self.name = name


class FakeLswifiValue:
    def __init__(self, value):
        self.value = value


class FakeLswifiList:
    def __init__(self, elements):
        self.elements = elements


class FakeLswifiInformationElement:
    def __init__(self, decoded):
        self.decoded = decoded


class FakeLswifiBss:
    def __init__(
        self,
        ssid,
        bssid,
        rssi,
        channel_number,
        channel_width="",
        phy_type=None,
        band="",
        frequency_mhz="",
        channel_frequency="",
        security="",
        auth="",
        encryption="",
        pmf="",
        country_code="",
        spatial_streams="",
        stations="",
        utilization="",
        modes=None,
        amendments=None,
        vendor="",
        model="",
        ap_name="",
        information_elements=None,
    ):
        self.ssid = ssid
        self.bssid = bssid
        self.rssi = rssi
        self.channel_number = channel_number
        self.channel_width = channel_width
        self.phy_type = phy_type
        self.band = band
        self.frequency_mhz = frequency_mhz
        self.channel_frequency = channel_frequency
        self.security = security
        self.auth = auth
        self.encryption = encryption
        self.pmf = pmf
        self.country_code = country_code
        self.spatial_streams = spatial_streams
        self.stations = stations
        self.utilization = utilization
        self.modes = modes
        self.amendments = amendments
        self.vendor = vendor
        self.model = model
        self.apname = ap_name
        self.information_elements = information_elements or []


def build_row(point_id, ssid, bssid, signal_dbm, channel, band=None):
    row = {
        "point_id": point_id,
        "timestamp": point_id,
        "x": "10",
        "y": "20",
        "ssid": ssid,
        "bssid": bssid,
        "signal_percent": "",
        "signal_dbm": signal_dbm,
        "signal_median_dbm": signal_dbm,
        "signal_max_dbm": signal_dbm,
        "signal_min_dbm": signal_dbm,
        "signal_samples_dbm": "",
        "samples_seen": "5",
        "samples_total": "5",
        "scan_confidence": "1.0",
        "channel": channel,
        "channel_width_mhz": "20",
        "radio": "802.11ax",
        "is_relevant": "1",
    }
    if band is not None:
        row["band"] = band
    return row


def build_raw_row(point_id, ssid, bssid, signal_dbm, channel, band=None):
    row = {
        "point_id": point_id,
        "scan_attempt": "1",
        "timestamp": point_id,
        "x": "10",
        "y": "20",
        "ssid": ssid,
        "bssid": bssid,
        "signal_percent": "",
        "signal_dbm": signal_dbm,
        "channel": channel,
        "channel_width_mhz": "20",
        "radio": "802.11ax",
        "backend": "test",
    }
    if band is not None:
        row["band"] = band
    return row


def rows_to_dataframe(rows):
    import pandas as pd

    return pd.DataFrame(rows)


class FakeGeometry:
    def __init__(self, width, height):
        self._width = width
        self._height = height

    def width(self):
        return self._width

    def height(self):
        return self._height


class FakeScreen:
    def __init__(self, width, height, ratio):
        self._geometry = FakeGeometry(width, height)
        self._ratio = ratio

    def geometry(self):
        return self._geometry

    def devicePixelRatio(self):
        return self._ratio


class FakeApp:
    def __init__(self, screen):
        self._screen = screen

    def primaryScreen(self):
        return self._screen


class FakeQualitySession:
    def __init__(self, rows, ap_groups=None):
        self.rows = rows
        self.raw_scan_rows = []
        self._ap_groups = ap_groups or []

    def get_ap_groups(self):
        return self._ap_groups


class FakeQualityApp:
    def __init__(self, rows, ap_groups=None, relevant_ssids=None):
        self.session = FakeQualitySession(rows, ap_groups)
        self.relevant_ssids = set(relevant_ssids or [])
        self.px_per_meter = None

    def tr(self, key, **kwargs):
        if key == "relevant_networks_none":
            return "No relevant network defined"
        if key == "quality_dashboard_no_issue":
            return "No Issues Detected"
        if key == "quality_dashboard_metric_missing":
            return "Missing Relevant Networks"
        if key == "quality_dashboard_metric_sparse":
            return "Sparse Data"
        if key == "quality_dashboard_metric_low_confidence":
            return "Low Scan Confidence"
        if key == "quality_dashboard_metric_unstable":
            return "Unstable Signal"
        if key == "quality_dashboard_metric_scanner_details":
            return "Scanner Details Missing"
        if key == "quality_dashboard_metric_ap_diagnostic_points":
            return "Dominant AP Findings"
        if key == "quality_dashboard_metric_ap_memory_applied":
            return "AP Memory Review"
        if key == "quality_dashboard_metric_ap_missing_positions":
            return "APs Without Position"
        if key == "quality_dashboard_metric_ap_metadata_warnings":
            return "AP Config Warnings"
        if key == "quality_dashboard_metric_channel_changes":
            return "Channel Changes"
        if key == "quality_dashboard_metric_rescan":
            return "Points To Review"
        if key == "quality_dashboard_metric_extra_details":
            return "Extra Details"
        if key == "quality_dashboard_metric_click_details":
            return "Click To Open Details"
        if key == "quality_dashboard_check_kpi_issue":
            return f"Check KPI: {kwargs.get('kpis', '')}"
        if key == "ap_group_alias_menu":
            return "Alias"
        if key == "ap_group_role":
            return "Role"
        if key == "ap_group_metadata":
            return "Metadata"
        if key == "ap_group_position":
            return "Position"
        if key == "quality_dashboard_scanner_details_fallback":
            return f"Scanner Used: <b>{kwargs.get('backends')}</b> (Limited Channel Details)"
        if key == "quality_dashboard_scanner_details_missing_width":
            return f"Channel Width Missing On <b>{kwargs.get('count')}</b> Scan Rows"
        if key == "quality_dashboard_scanner_details_finding":
            return "Limited Scanner Details"
        if key == "quality_dashboard_scanner_details_scanner":
            return (
                f"Scanner: <b>{kwargs.get('backends')}</b>{kwargs.get('fallback', '')} | "
                f"Raw Scan Rows: <b>{kwargs.get('count')}</b>"
            )
        if key == "quality_dashboard_scanner_details_fallback_suffix":
            return " (fallback)"
        if key == "quality_dashboard_scanner_details_missing_width_detail":
            return f"Missing Channel Width: <b>{kwargs.get('count')}</b> channel-sensitive scan rows"
        if key == "quality_dashboard_scanner_details_missing_frequency_detail":
            return f"Missing 6 GHz Frequency: <b>{kwargs.get('count')}</b> 6 GHz scan rows"
        if key == "quality_dashboard_scanner_details_impact":
            return "Impact: channel-sensitive maps may be less reliable at this point."
        if key == "quality_dashboard_issue_missing_relevant":
            return f"<b>{kwargs.get('ssid')}</b>: Relevant Network Not Detected At This Point"
        if key == "quality_dashboard_issue_low_confidence":
            return f"<b>{kwargs.get('ssid')}</b>: {kwargs.get('confidence')} Confidence Level"
        if key == "quality_dashboard_issue_unstable_signal":
            return f"<b>{kwargs.get('ssid')}</b>: Signal Varies By {kwargs.get('range')} dB"
        if key == "quality_dashboard_issue_sparse_data":
            return "Not Enough Scan Samples At This Point"
        if key == "quality_missing_relevant":
            return "Missing Relevant Networks"
        if key == "quality_low_confidence":
            return "Low Scan Confidence"
        if key == "quality_unstable_signal":
            return "Unstable Signal"
        if key == "quality_dashboard_missing_positions_more":
            return f"{kwargs.get('names', '')} +{kwargs.get('count', 0)}"
        if key == "quality_dashboard_missing_positions_none":
            return "None"
        if key == "quality_dashboard_more_issues":
            return f"+{kwargs.get('count', 0)}"
        if key == "quality_dashboard_ap_position_issue":
            return (
                f"Dominant AP: <b>{kwargs.get('dominant')}</b> "
                f"({kwargs.get('signal')}, {kwargs.get('dominant_distance')}) | "
                f"Closest AP: <b>{kwargs.get('closest')}</b> ({kwargs.get('closest_distance')}) | "
                f"<b>{kwargs.get('warning')}</b>"
            )
        if key == "quality_dashboard_ap_metadata_channels":
            return (
                f"<b>Observed Channels:</b> {kwargs.get('channels')}<br>"
                f"<b>Expected Channels:</b> {kwargs.get('expected')}"
            )
        if key == "quality_dashboard_ap_metadata_bands":
            return (
                f"<b>Observed Bands:</b> {kwargs.get('bands')}<br>"
                f"<b>Expected Bands:</b> {kwargs.get('expected')}"
            )
        if key == "quality_dashboard_ap_memory_item_detail":
            return (
                f"<b>Memory Status:</b> M - applied from AP Memory<br>"
                f"<b>Matched BSSIDs:</b> {kwargs.get('matched_bssids')}<br>"
                "<b>Next Step:</b> confirm or edit remembered AP data"
            )
        if key == "quality_dashboard_ap_memory_update_item_detail":
            return (
                "<b>Memory Status:</b> <s>M</s> - current AP data differs from AP Memory<br>"
                f"<b>Different Fields:</b> {kwargs.get('fields')}<br>"
                "<b>Next Step:</b> update from memory, or keep current data and save it"
            )
        if key == "quality_dashboard_missing_position_item_detail":
            return (
                f"<b>AP Group:</b> {kwargs.get('group')}<br>"
                "<b>Required Action:</b> place this AP on the floor plan"
            )
        if key == "quality_dashboard_channel_change_status_clean":
            return "clean"
        if key == "quality_dashboard_channel_change_status_ambiguous":
            return "ambiguous"
        if key == "quality_dashboard_channel_change_label":
            return (
                f"{kwargs.get('ap')} {kwargs.get('band')}: {kwargs.get('status')}, "
                f"channels {kwargs.get('channels')}, current {kwargs.get('current')}"
            )
        if key == "quality_dashboard_channel_change_item_detail":
            return (
                f"<b>Band:</b> {kwargs.get('band')}<br>"
                f"<b>Observed Channels:</b> {kwargs.get('channels')}<br>"
                f"<b>Maps Use:</b> {kwargs.get('current')}<br>"
                f"<b>Status:</b> {kwargs.get('status')}"
            )
        if key == "quality_dashboard_ap_position_detail":
            return (
                f"Dominant {kwargs.get('dominant')} {kwargs.get('signal')} "
                f"{kwargs.get('dominant_distance')} closest {kwargs.get('closest')} "
                f"{kwargs.get('closest_distance')}"
            )
        if key == "quality_dashboard_ap_position_finding":
            return f"Finding {kwargs.get('finding')}"
        if key == "ap_position_distance_m":
            return f"{kwargs.get('distance')} m"
        if key == "ap_position_distance_px":
            return f"{kwargs.get('distance')} px"
        if key == "ap_position_unexpected_dominant":
            return "unexpected dominant"
        if key == "ap_position_unknown_warning":
            return "unknown warning"
        return key.format(**kwargs) if kwargs else key

    def get_ap_group_display_name(self, group_id):
        return str(group_id)

    def get_px_per_meter(self):
        return self.px_per_meter

    def format_point_quality(self, status):
        return str(status)

    def format_quality_breakdown_item(self, item):
        return str(item.get("message", ""))


if __name__ == "__main__":
    unittest.main()
