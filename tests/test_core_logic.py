import unittest
import logging
import os
import tempfile

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QGraphicsItem, QWidget

from app_logging import MaxLogLevelFilter
from app_restart import build_restart_command
from app_settings import get_last_survey_directory, save_last_survey_path
from ap_groups import (
    build_bssid_to_manual_group_map,
    build_manual_ap_group,
    resolve_ap_group_key,
)
from ap_metadata_checks import build_ap_metadata_warnings
from heatmap_tools import calculate_interference_points
from qt_quality_dashboard import (
    build_summary,
    format_point_confidence,
    format_relevant_ssids,
    get_effective_ap_groups,
)
from qt_floorplan import AP_MARKER_BASE_SIZE, FloorplanView
from qt_live_map import LIVE_POINT_MARKER_BASE_SIZE, LiveGradientLegendWidget, LiveMapView
from qt_windowing import pop_modal_dim, push_modal_dim
from quality_engine import QUALITY_GOOD, QUALITY_MISSING_RELEVANT, evaluate_point_quality
from survey_store import get_survey_point_summaries_from_rows
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


class ApGroupTests(unittest.TestCase):
    def test_manual_group_map_overrides_automatic_collision(self):
        first_bssid = "70:4f:57:aa:bb:10"
        second_bssid = "80:4f:57:aa:bb:10"
        groups = [
            build_manual_ap_group("corridor", [first_bssid]),
            build_manual_ap_group("office", [second_bssid]),
        ]

        group_map = build_bssid_to_manual_group_map(groups)

        self.assertEqual(resolve_ap_group_key(first_bssid, group_map), "corridor")
        self.assertEqual(resolve_ap_group_key(second_bssid, group_map), "office")


class InterferenceTests(unittest.TestCase):
    def test_interference_ignores_same_physical_ap_group(self):
        serving_bssid = "70:4f:57:aa:bb:10"
        guest_bssid = "72:4f:57:aa:bb:10"
        neighbor_bssid = "80:11:22:33:44:10"
        rows = [
            build_row("p1", "MAIN", serving_bssid, -50, 1),
            build_row("p1", "GUEST", guest_bssid, -45, 1),
            build_row("p1", "NEIGHBOR", neighbor_bssid, -55, 1),
        ]
        groups = [
            build_manual_ap_group("ap_serving", [serving_bssid, guest_bssid]),
            build_manual_ap_group("ap_neighbor", [neighbor_bssid]),
        ]
        group_map = build_bssid_to_manual_group_map(groups)

        risk_df = calculate_interference_points(
            rows_to_dataframe(rows),
            "MAIN",
            "2.4",
            mode="all",
            include_details=True,
            ap_group_map=tuple(sorted(group_map.items())),
        )

        self.assertEqual(len(risk_df), 1)
        row = risk_df.iloc[0]
        self.assertEqual(row["same_physical_ap_ignored_count"], 1)
        self.assertEqual(row["strongest_interferer_bssid"], neighbor_bssid)
        self.assertGreater(row["risk"], 0)


class QualityTests(unittest.TestCase):
    def test_quality_marks_missing_relevant_network(self):
        rows = [build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -55, 1)]

        quality = evaluate_point_quality(rows, relevant_ssids={"MAIN", "GUEST"})

        self.assertEqual(quality["p1"]["status"], QUALITY_MISSING_RELEVANT)
        self.assertEqual(quality["p1"]["missing_relevant"], ["guest"])

    def test_quality_ignores_low_confidence_weak_non_dominant_bssid(self):
        strong_row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -52, 1)
        weak_row = build_row("p1", "MAIN", "80:11:22:33:44:10", -82, 1)
        weak_row["samples_seen"] = "1"
        weak_row["scan_confidence"] = "0.2"

        quality = evaluate_point_quality([strong_row, weak_row], relevant_ssids={"MAIN"})

        self.assertEqual(quality["p1"]["status"], QUALITY_GOOD)

    def test_dashboard_confidence_uses_dominant_candidates(self):
        strong_row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -52, 1)
        weak_row = build_row("p1", "MAIN", "80:11:22:33:44:10", -82, 1)
        weak_row["samples_seen"] = "1"
        weak_row["scan_confidence"] = "0.2"

        confidence = format_point_confidence([strong_row, weak_row], "p1", {"MAIN"})

        self.assertEqual(confidence, "1.00")

    def test_dashboard_relevant_ssid_column_hides_irrelevant_networks(self):
        relevant_row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -52, 1)
        irrelevant_row = build_row("p1", "GUEST", "80:11:22:33:44:10", -60, 1)
        irrelevant_row["is_relevant"] = "0"

        ssids = format_relevant_ssids([irrelevant_row, relevant_row], "p1", {"MAIN"})

        self.assertEqual(ssids, "MAIN")

    def test_dashboard_relevant_ssid_column_falls_back_to_row_flags(self):
        relevant_row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -52, 1)
        irrelevant_row = build_row("p1", "GUEST", "80:11:22:33:44:10", -60, 1)
        irrelevant_row["is_relevant"] = "0"

        ssids = format_relevant_ssids([irrelevant_row, relevant_row], "p1", set())

        self.assertEqual(ssids, "MAIN")

    def test_quality_summary_counts_auto_ap_groups_without_position(self):
        rows = [build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -55, 1)]
        app = FakeQualityApp(rows)
        groups = get_effective_ap_groups(app)

        summary = build_summary(
            app,
            [{"status": QUALITY_GOOD, "needs_review": False, "ap_position_warning_count": 0}],
            [],
            groups,
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(summary["ap_missing_positions"], 1)
        self.assertEqual(summary["ap_positions"], "0/1")

    def test_quality_summary_scopes_missing_ap_positions_to_relevant_ssids(self):
        rows = [
            build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -55, 1),
            build_row("p1", "GUEST", "80:11:22:33:44:10", -56, 6),
        ]
        app = FakeQualityApp(rows, relevant_ssids={"MAIN"})
        groups = get_effective_ap_groups(app)

        summary = build_summary(
            app,
            [{"status": QUALITY_GOOD, "needs_review": False, "ap_position_warning_count": 0}],
            [],
            groups,
        )

        self.assertEqual(len(groups), 2)
        self.assertEqual(summary["ap_missing_positions"], 1)
        self.assertEqual(summary["ap_positions"], "0/1")


class SurveyPointSummaryTests(unittest.TestCase):
    def test_best_signal_prefers_relevant_networks_when_available(self):
        relevant_row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -68, 1)
        external_row = build_row("p1", "EXTERNAL", "80:11:22:33:44:10", -42, 6)
        external_row["is_relevant"] = "0"

        summaries = get_survey_point_summaries_from_rows([external_row, relevant_row])

        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["best_signal_dbm"], -68)
        self.assertEqual(summaries[0]["signal_scope"], "relevant")


class UiScalingTests(unittest.TestCase):
    def test_ui_scale_helpers_are_predictable(self):
        self.assertEqual(normalize_ui_scale_mode("125%"), "125")
        self.assertEqual(normalize_ui_scale_mode("auto"), "auto")
        self.assertEqual(normalize_ui_scale_mode("bad"), "auto")
        self.assertEqual(scale_px(10, 1.25), 12)
        self.assertGreater(scale_font(10, 1.25), 10)

    def test_ui_auto_scale_matches_common_resolutions(self):
        self.assertEqual(scale_percent_for_resolution(1920, 1080), 100)
        self.assertEqual(scale_percent_for_resolution(2560, 1440), 125)
        self.assertEqual(scale_percent_for_resolution(2560, 1600), 125)
        self.assertEqual(scale_percent_for_resolution(3840, 2160), 150)

    def test_ui_scale_percent_is_relative_to_resolution_class(self):
        self.assertEqual(effective_scale_for_percent(125, 125), 1.0)
        self.assertEqual(effective_scale_for_percent(100, 125), 0.8)
        self.assertEqual(effective_scale_for_percent(150, 125), 1.2)

    def test_screen_resolution_uses_device_pixel_ratio(self):
        screen = FakeScreen(1280, 800, 2.0)

        self.assertEqual(detect_screen_resolution(screen), (2560, 1600))

    def test_ui_scale_diagnostics_format_is_stable(self):
        diagnostics = {
            "mode": "125",
            "auto_percent": 125,
            "effective_scale": 1.0,
            "screen": "2560x1600",
        }

        self.assertEqual(
            format_ui_scale_diagnostics(diagnostics),
            "mode=125 auto_percent=125 effective_scale=1.0 screen=2560x1600",
        )

    def test_ui_scale_diagnostics_accepts_app_like_object(self):
        app = FakeApp(FakeScreen(2560, 1600, 1.0))

        diagnostics = ui_scale_diagnostics("100", app)

        self.assertEqual(diagnostics["auto_percent"], 125)
        self.assertEqual(diagnostics["effective_scale"], 0.8)
        self.assertEqual(diagnostics["screen"], "2560x1600")


class AppRestartTests(unittest.TestCase):
    def test_restart_command_uses_python_script_in_source_mode(self):
        command = build_restart_command(
            executable="python.exe",
            argv=["main.py", "--debug"],
            frozen=False,
        )

        self.assertEqual(command, ["python.exe", "main.py", "--debug"])

    def test_restart_command_uses_executable_only_in_frozen_mode(self):
        command = build_restart_command(
            executable="wifi_heatmap.exe",
            argv=["wifi_heatmap.exe", "--debug"],
            frozen=True,
        )

        self.assertEqual(command, ["wifi_heatmap.exe", "--debug"])


class AppSettingsTests(unittest.TestCase):
    def test_last_survey_directory_uses_saved_file_parent(self):
        previous = os.environ.get("WIFI_HEATMAP_SETTINGS_FILE")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                settings_file = os.path.join(temp_dir, "settings.json")
                survey_file = os.path.join(temp_dir, "surveys", "test.csv")
                os.makedirs(os.path.dirname(survey_file), exist_ok=True)
                os.environ["WIFI_HEATMAP_SETTINGS_FILE"] = settings_file

                self.assertTrue(save_last_survey_path(survey_file))

                self.assertEqual(get_last_survey_directory(), os.path.dirname(survey_file))
        finally:
            if previous is None:
                os.environ.pop("WIFI_HEATMAP_SETTINGS_FILE", None)
            else:
                os.environ["WIFI_HEATMAP_SETTINGS_FILE"] = previous


class LoggingTests(unittest.TestCase):
    def test_info_console_filter_excludes_warnings_and_errors(self):
        log_filter = MaxLogLevelFilter(logging.INFO)

        self.assertTrue(log_filter.filter(logging.LogRecord(
            "test",
            logging.INFO,
            __file__,
            1,
            "info",
            (),
            None,
        )))
        self.assertFalse(log_filter.filter(logging.LogRecord(
            "test",
            logging.WARNING,
            __file__,
            1,
            "warning",
            (),
            None,
        )))


class QtWindowingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_dim_push_ignores_dialog_that_is_already_hidden(self):
        parent = QWidget()
        parent.show()
        dialog = QDialog(parent)
        dialog.show()
        dialog.hide()

        push_modal_dim(dialog)

        self.assertIsNone(getattr(parent.window(), "_wifi_heatmap_dim_overlay", None))
        dialog.deleteLater()
        parent.deleteLater()

    def test_dim_pop_clears_overlay_and_active_token(self):
        parent = QWidget()
        parent.resize(300, 200)
        parent.show()
        dialog = QDialog(parent)
        dialog.show()

        push_modal_dim(dialog)
        self.assertIsNotNone(getattr(parent.window(), "_wifi_heatmap_dim_overlay", None))

        pop_modal_dim(dialog)

        self.assertEqual(getattr(parent.window(), "_wifi_heatmap_dim_count", 0), 0)
        self.assertEqual(getattr(parent.window(), "_wifi_heatmap_dim_tokens", set()), set())
        self.assertIsNone(getattr(parent.window(), "_wifi_heatmap_dim_overlay", None))
        dialog.deleteLater()
        parent.deleteLater()


class FloorplanViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_ap_marker_keeps_high_resolution_source_pixmap(self):
        view = FloorplanView()

        marker = view.create_ap_marker(100, 120, {"group_id": "ap"}, "AP")
        pixmap = marker.pixmap()
        rendered_size = max(pixmap.width(), pixmap.height()) * marker.scale()

        self.assertGreater(max(pixmap.width(), pixmap.height()), AP_MARKER_BASE_SIZE)
        self.assertAlmostEqual(rendered_size, AP_MARKER_BASE_SIZE, delta=0.1)
        view.deleteLater()


class LiveMapViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_live_marker_uses_scene_sized_survey_marker(self):
        view = LiveMapView()

        marker = view.create_marker_item({})

        self.assertEqual(marker.rect().width(), LIVE_POINT_MARKER_BASE_SIZE)
        self.assertFalse(marker.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        view.deleteLater()

    def test_gradient_legend_paints_payload(self):
        widget = LiveGradientLegendWidget()
        widget.resize(220, 260)
        widget.set_scale_payload({
            "kind": "gradient",
            "cmap": "RdYlGn",
            "min": -90,
            "max": -40,
            "suffix": " dBm",
        })
        pixmap = QPixmap(widget.size())
        pixmap.fill(Qt.GlobalColor.transparent)

        widget.render(pixmap)

        self.assertFalse(pixmap.isNull())
        widget.deleteLater()

    def test_live_view_hosts_compact_gradient_overlay(self):
        view = LiveMapView()
        view.resize(500, 360)

        view.set_gradient_legend({
            "kind": "gradient",
            "cmap": "RdYlGn",
            "min": -90,
            "max": -40,
            "suffix": " dBm",
        })

        self.assertFalse(view.gradient_legend.isHidden())
        self.assertLessEqual(view.gradient_legend.width(), 160)

        view.clear_gradient_legend()

        self.assertTrue(view.gradient_legend.isHidden())
        view.deleteLater()


class ApMetadataTests(unittest.TestCase):
    def test_metadata_warning_detects_unexpected_channel(self):
        bssid = "70:4f:57:aa:bb:10"
        rows = [build_row("p1", "MAIN", bssid, -55, 6)]
        groups = [
            build_manual_ap_group(
                "corridor",
                [bssid],
                metadata={"expected_channels": "1", "expected_bands": "2.4"},
            )
        ]

        warnings = build_ap_metadata_warnings(rows, groups)

        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["group_id"], "corridor")
        self.assertEqual(warnings[0]["unexpected_channels"], ["6"])


def build_row(point_id, ssid, bssid, signal_dbm, channel):
    return {
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
        self._ap_groups = ap_groups or []

    def get_ap_groups(self):
        return self._ap_groups


class FakeQualityApp:
    def __init__(self, rows, ap_groups=None, relevant_ssids=None):
        self.session = FakeQualitySession(rows, ap_groups)
        self.relevant_ssids = set(relevant_ssids or [])

    def tr(self, key, **kwargs):
        if key == "relevant_networks_none":
            return "No relevant network defined"
        if key == "quality_dashboard_missing_positions_more":
            return f"{kwargs.get('names', '')} +{kwargs.get('count', 0)}"
        if key == "quality_dashboard_missing_positions_none":
            return "None"
        if key == "quality_dashboard_more_issues":
            return f"+{kwargs.get('count', 0)}"
        return key.format(**kwargs) if kwargs else key

    def get_ap_group_display_name(self, group_id):
        return str(group_id)


if __name__ == "__main__":
    unittest.main()
