import unittest
import json
import logging
import os
import tempfile
import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QGraphicsItem, QGraphicsView, QListWidgetItem, QWidget
from PIL import Image

from app_logging import MaxLogLevelFilter
from app_restart import build_restart_command
from app_settings import get_last_survey_directory, save_last_survey_path
from constants import RAW_DATA_FILE_METADATA_KEY, SURVEY_FIELDNAMES
from i18n import translate
from ap_groups import (
    AP_ROLE_EXTERNAL,
    AP_ROLE_INTERNAL,
    AP_ROLE_INTERFERER,
    AP_ROLE_TEST,
    build_ap_group_role_map,
    build_bssid_to_manual_group_map,
    build_default_manual_groups,
    build_manual_ap_group,
    merge_new_bssids_into_manual_groups,
    resolve_ap_group_key,
    serialize_ap_group_map,
    serialize_ap_group_roles,
)
from ap_group_checks import build_ap_group_conflicts
from ap_metadata_checks import (
    build_ap_metadata_warnings,
    infer_band_from_channel,
    normalize_channel,
    parse_expected_bands,
    parse_expected_channels,
    sort_bands,
    sort_channels,
)
from ap_positioning import (
    AP_POSITION_MISSING,
    AP_POSITION_NO_SCALE,
    AP_POSITION_OK,
    AP_POSITION_STRONG_FAR,
    AP_POSITION_UNEXPECTED_DOMINANT,
    AP_POSITION_WEAK_CLOSE,
    analyze_dominant_ap_position,
)
from heatmap_tools import (
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
import live_renderer as live_renderer_module
from live_renderer import (
    build_signal_payload,
    clone_cached_result,
    render_live_continuous_map,
    stable_dataframe_fingerprint,
)
from map_exporter import (
    MapExportResult,
    annotate_interference_problem_numbers,
    build_channel_point_legend_items,
    build_dominant_marker_legend_items,
    build_dominant_point_legend_items,
    build_interference_problem_report_pages,
    build_live_pdf_channel_figure,
    build_live_pdf_dominant_figure,
    build_problem_report_pages,
    generate_live_pdf_export,
    get_interference_problem_df,
)
import matplotlib.pyplot as plt
from map_config import MapConfig
from qt_quality_dashboard import (
    build_ap_position_quality_by_point,
    build_dashboard_rows,
    build_summary,
    format_point_confidence,
    format_relevant_ssids,
    get_effective_relevant_ssids,
    get_effective_ap_groups,
)
from qt_floorplan import AP_MARKER_BASE_SIZE, FloorplanView, format_ap_tooltip, format_point_tooltip
from qt_ap_groups import EXPECTED_CHANNELS_BY_BAND, infer_expected_channel_bands
from qt_live_map import (
    LIVE_POINT_MARKER_BASE_SIZE,
    LiveGradientLegendWidget,
    LiveMapView,
    build_ap_position_marker_infos,
    build_channel_payload,
    build_dominant_payload,
    build_live_tooltip,
    gradient_stops,
)
import qt_app as qt_app_module
from qt_app import WifiHeatmapQtApp
from qt_windowing import pop_modal_dim, push_modal_dim
from quality_engine import (
    QUALITY_GOOD,
    QUALITY_LOW_CONFIDENCE,
    QUALITY_MISSING_RELEVANT,
    QUALITY_SPARSE_DATA,
    QUALITY_UNSTABLE_SIGNAL,
    evaluate_point_quality,
)
from survey_store import (
    SurveyFormatError,
    SurveySession,
    build_raw_scan_file_path,
    get_survey_point_summaries_from_rows,
)
from ui_scaling import (
    detect_screen_resolution,
    effective_scale_for_percent,
    format_ui_scale_diagnostics,
    normalize_ui_scale_mode,
    scale_font,
    scale_percent_for_resolution,
    scale_px,
    ui_scale_diagnostics,
)
from wifi_scanner import (
    annotate_raw_scan_samples,
    merge_wifi_scans,
    normalize_channel_width_mhz,
    parse_lswifi_bss_list,
    parse_netsh_output,
)
from wifi_band import infer_band_from_frequency_mhz, normalize_frequency_mhz



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
        if key == "quality_dashboard_missing_positions_more":
            return f"{kwargs.get('names', '')} +{kwargs.get('count', 0)}"
        if key == "quality_dashboard_missing_positions_none":
            return "None"
        if key == "quality_dashboard_more_issues":
            return f"+{kwargs.get('count', 0)}"
        if key == "quality_dashboard_ap_position_issue":
            return f"{kwargs.get('ap')}: {kwargs.get('warning')}"
        if key == "quality_dashboard_ap_metadata_channels":
            return f"channels {kwargs.get('channels')} expected {kwargs.get('expected')}"
        if key == "quality_dashboard_ap_metadata_bands":
            return f"bands {kwargs.get('bands')} expected {kwargs.get('expected')}"
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
