import unittest
import logging
import os
import tempfile
import time

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QGraphicsItem, QGraphicsView, QWidget
from PIL import Image

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
from live_renderer import build_signal_payload
from map_config import MapConfig
from qt_quality_dashboard import (
    build_summary,
    format_point_confidence,
    format_relevant_ssids,
    get_effective_ap_groups,
)
from qt_floorplan import AP_MARKER_BASE_SIZE, FloorplanView, format_ap_tooltip, format_point_tooltip
from qt_live_map import (
    LIVE_POINT_MARKER_BASE_SIZE,
    LiveGradientLegendWidget,
    LiveMapView,
    build_ap_position_marker_infos,
    gradient_stops,
)
from qt_app import WifiHeatmapQtApp
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

    def test_survey_point_tooltip_uses_live_style_html_layout(self):
        tooltip = format_point_tooltip(
            {
                "x": 10,
                "y": 20,
                "best_signal_dbm": -61,
                "signal_scope": "relevant",
                "row_count": 4,
                "relevant_row_count": 2,
                "timestamp": "2026-05-11T12:00:00",
                "ssids": ["MAIN", "Guest <wifi>"],
            }
        )

        self.assertIn("<table", tooltip)
        self.assertIn("border-left:4px solid", tooltip)
        self.assertIn("Survey point", tooltip)
        self.assertIn("Best signal", tooltip)
        self.assertIn("Guest &lt;wifi&gt;", tooltip)

    def test_survey_ap_tooltip_uses_live_style_html_layout(self):
        tooltip = format_ap_tooltip(
            {"group_id": "office", "bssids": ["70:4f:57:aa:bb:10"]},
            "Office AP",
            30,
            40,
        )

        self.assertIn("<table", tooltip)
        self.assertIn("AP position", tooltip)
        self.assertIn("Office AP", tooltip)
        self.assertIn("70:4f:57:aa:bb:10", tooltip)

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
        self.assertEqual(view.dragMode(), QGraphicsView.DragMode.NoDrag)
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
        image = pixmap.toImage()
        top = image.pixelColor(20, 20)
        middle = image.pixelColor(20, 130)
        bottom = image.pixelColor(20, 240)
        self.assertGreater(top.green(), 150)
        self.assertLess(top.red(), 90)
        self.assertGreater(middle.red(), 220)
        self.assertGreater(middle.green(), 190)
        self.assertLess(middle.blue(), 95)
        self.assertGreater(bottom.red(), 190)
        self.assertLess(bottom.green(), 120)
        widget.deleteLater()

    def test_gradient_scale_uses_saturated_heatmap_stops(self):
        self.assertEqual(
            gradient_stops("RdYlGn"),
            (
                (0.0, "#25a865"),
                (0.5, "#f2d33b"),
                (1.0, "#d94343"),
            ),
        )
        self.assertEqual(
            gradient_stops("RdYlGn_r"),
            (
                (0.0, "#d94343"),
                (0.5, "#f2d33b"),
                (1.0, "#25a865"),
            ),
        )

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
        self.assertLessEqual(view.gradient_legend.width(), 128)
        self.assertGreaterEqual(view.gradient_legend.width(), 112)
        self.assertGreaterEqual(
            view.gradient_legend.x(),
            view.viewport().width() - view.gradient_legend.width() - 20,
        )
        self.assertGreaterEqual(
            view.gradient_legend.y(),
            view.viewport().height() - view.gradient_legend.height() - 20,
        )

        view.clear_gradient_legend()

        self.assertTrue(view.gradient_legend.isHidden())
        view.deleteLater()

    def test_live_gradient_overlay_reanchors_after_content_scroll(self):
        view = LiveMapView()
        view.resize(500, 360)
        view.set_gradient_legend({
            "kind": "gradient",
            "cmap": "RdYlGn",
            "min": -90,
            "max": -40,
            "suffix": " dBm",
        })
        anchored_pos = view.gradient_legend.pos()

        view.gradient_legend.move(0, 0)
        view.scrollContentsBy(24, 18)

        self.assertEqual(view.gradient_legend.pos(), anchored_pos)
        view.deleteLater()

    def test_live_pan_uses_closed_hand_cursor_only_while_dragging(self):
        if QApplication.overrideCursor() is not None:
            self.skipTest("existing override cursor would make the cursor stack ambiguous")

        view = LiveMapView()
        view.begin_pan(QPoint(10, 10))
        try:
            override_cursor = QApplication.overrideCursor()
            self.assertEqual(view.viewport().cursor().shape(), Qt.CursorShape.ClosedHandCursor)
            self.assertIsNotNone(override_cursor)
            self.assertEqual(override_cursor.shape(), Qt.CursorShape.ClosedHandCursor)
        finally:
            view.end_pan()

        self.assertEqual(view.viewport().cursor().shape(), Qt.CursorShape.ArrowCursor)
        self.assertIsNone(QApplication.overrideCursor())
        view.deleteLater()

    def test_live_view_shows_positioned_ap_markers(self):
        view = LiveMapView()
        payload = {
            "image": Image.new("RGB", (120, 90), "white"),
            "point_infos": [],
            "ap_infos": [{"x": 40, "y": 30, "label": "AP", "tooltip": "AP"}],
        }

        view.set_payload(payload)

        self.assertEqual(len(view.ap_marker_items), 1)
        view.deleteLater()

    def test_live_signal_tooltip_rows_keep_selected_ssid_after_aggregation(self):
        rows = [
            build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -55, 1),
            build_row("p2", "MAIN", "70:4f:57:aa:bb:11", -65, 1),
            build_row("p3", "MAIN", "70:4f:57:aa:bb:12", -70, 1),
        ]
        for index, row in enumerate(rows):
            row["timestamp"] = f"p{index + 1}"
            row["x"] = str(20 + index * 30)
            row["y"] = str(20 + (index % 2) * 30)
        tooltip_ssids = []

        payload = build_signal_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="all", map_type="signal", interpolation="linear"),
            Image.new("RGB", (120, 90), "white"),
            {"signal_title": "Signal coverage"},
            lambda _map_type, row, _raw_rows: tooltip_ssids.append(row.get("ssid")) or "tooltip",
            lambda _grid_z, _config: (-90, -40),
        )
        payload["fig"].clf()

        self.assertEqual(tooltip_ssids, ["MAIN", "MAIN", "MAIN"])

    def test_live_ap_position_markers_skip_test_groups(self):
        markers = build_ap_position_marker_infos(
            [
                {"group_id": "visible", "position": {"x": 10, "y": 20}, "role": "internal"},
                {"group_id": "hidden", "position": {"x": 30, "y": 40}, "role": "test"},
            ],
            aliases={},
            translations={},
        )

        self.assertEqual([marker["label"] for marker in markers], ["visible"])

    def test_live_ap_position_markers_highlight_selected_group(self):
        markers = build_ap_position_marker_infos(
            [{"group_id": "visible", "position": {"x": 10, "y": 20}, "role": "internal"}],
            aliases={},
            translations={},
            selected_group="visible",
        )

        self.assertTrue(markers[0]["highlight"])


class SettingsMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_settings_menu_suppresses_immediate_reopen_after_button_close(self):
        window = WifiHeatmapQtApp()
        window.settings_menu_suppressed_until = time.monotonic() + 1.0

        self.assertTrue(window.should_suppress_settings_menu_toggle())
        self.assertFalse(window.should_suppress_settings_menu_toggle())
        window.deleteLater()

    def test_settings_button_global_hit_test_matches_button(self):
        window = WifiHeatmapQtApp()
        window.show()
        QApplication.processEvents()
        button_pos = window.settings_menu_button.mapToGlobal(window.settings_menu_button.rect().center())

        self.assertTrue(window.is_settings_button_global_pos(button_pos))
        window.deleteLater()


class WorkspaceLiveStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_live_refresh_callbacks_use_existing_session_refresh(self):
        window = WifiHeatmapQtApp()
        try:
            window.on_workspace_tab_changed(1)
            window.on_live_option_changed()
            window.finish_live_preview(None)
            window.fail_live_preview("render failed")
        finally:
            window.deleteLater()

    def test_live_status_does_not_append_map_scale_details(self):
        window = WifiHeatmapQtApp()
        try:
            self.assertEqual(
                window.format_live_status({
                    "scale_payload": {
                        "kind": "gradient",
                        "title": "AP interference",
                        "min": 0,
                        "max": 100,
                        "suffix": "%",
                    }
                }),
                window.tr("live_preview_updated"),
            )
            self.assertEqual(
                window.format_live_status({
                    "scale_payload": {
                        "kind": "swatches",
                        "title": "AP channels",
                        "items": [{"label": "CH 1"}, {"label": "CH 6"}],
                    }
                }),
                window.tr("live_preview_updated"),
            )
        finally:
            window.deleteLater()

    def test_live_toolbar_keeps_map_options_in_overlay(self):
        window = WifiHeatmapQtApp()
        try:
            self.assertIs(window.live_map_type_combo.parent(), window.live_toolbar_frame)
            self.assertIs(window.live_ssid_combo.parent(), window.live_toolbar_frame)
            self.assertIs(window.live_update_button.parent(), window.live_toolbar_frame)
            self.assertIs(window.live_band_combo.parent(), window.live_options_body)
            self.assertTrue(window.live_options_body.isHidden())
            window.live_view_container.resize(900, 600)
            window.position_live_options_overlay()
            collapsed_geometry = window.live_options_overlay.geometry()
            self.assertLessEqual(collapsed_geometry.x(), window.spx(16))
            self.assertLess(collapsed_geometry.width(), window.spx(64))
            self.assertGreater(collapsed_geometry.height(), collapsed_geometry.width())

            window.toggle_live_options_panel()
            expanded_geometry = window.live_options_overlay.geometry()

            self.assertFalse(window.live_options_body.isHidden())
            self.assertEqual(window.live_options_toggle_button.text(), window.tr("live_options_hide"))
            self.assertEqual(expanded_geometry.x(), collapsed_geometry.x())
            self.assertGreater(expanded_geometry.width(), collapsed_geometry.width() * 3)
            self.assertGreater(expanded_geometry.right(), collapsed_geometry.right())
            self.assertLess(expanded_geometry.width(), window.spx(440))

            expanded_heights = []
            for map_type in ("signal", "interference", "channel", "dominant"):
                index = window.live_map_type_combo.findData(map_type)
                window.live_map_type_combo.blockSignals(True)
                window.live_map_type_combo.setCurrentIndex(index)
                window.live_map_type_combo.blockSignals(False)
                window.update_live_option_state()
                window.position_live_options_overlay()
                expanded_heights.append(window.live_options_overlay.geometry().height())
            self.assertEqual(len(set(expanded_heights)), 1)
            self.assertGreaterEqual(expanded_heights[0], window.spx(214))
        finally:
            window.deleteLater()

    def test_live_options_overlay_is_specific_to_map_type(self):
        window = WifiHeatmapQtApp()
        try:
            window.live_ap_group_filter_items = lambda: [("ap-1", "AP 1")]
            window.refresh_live_ap_group_filter()

            def set_map_type(value):
                index = window.live_map_type_combo.findData(value)
                window.live_map_type_combo.blockSignals(True)
                window.live_map_type_combo.setCurrentIndex(index)
                window.live_map_type_combo.blockSignals(False)
                window.update_live_option_state()

            def grid_position(widget):
                item_index = window.live_options_layout.indexOf(widget)
                return window.live_options_layout.getItemPosition(item_index)

            def combo_values(combo):
                return [combo.itemData(index) for index in range(combo.count())]

            set_map_type("signal")
            self.assertEqual(combo_values(window.live_band_combo), ["all", "2.4", "5"])
            self.assertEqual(grid_position(window.live_ap_group_label)[:2], (0, 0))
            self.assertEqual(grid_position(window.live_ap_group_combo)[:2], (0, 1))
            self.assertEqual(grid_position(window.live_band_label)[:2], (1, 0))
            self.assertEqual(grid_position(window.live_band_combo)[:2], (1, 1))
            self.assertEqual(grid_position(window.live_interpolation_label)[:2], (2, 0))
            self.assertEqual(grid_position(window.live_aggregation_label)[:2], (3, 0))
            self.assertEqual(grid_position(window.live_options_separator), (4, 0, 1, 2))
            self.assertEqual(grid_position(window.live_usable_check), (5, 0, 1, 2))
            self.assertEqual(window.live_band_combo.width(), window.live_interpolation_combo.width())
            required_group_width = window.live_ap_group_combo.fontMetrics().horizontalAdvance("All AP groups")
            self.assertGreater(window.live_ap_group_combo.width(), required_group_width + window.spx(70))
            self.assertLess(window.live_band_combo.width(), window.spx(300))
            self.assertFalse(window.live_band_combo.isHidden())
            self.assertFalse(window.live_aggregation_combo.isHidden())
            self.assertFalse(window.live_interpolation_combo.isHidden())
            self.assertFalse(window.live_usable_check.isHidden())
            self.assertFalse(window.live_ap_group_combo.isHidden())
            self.assertFalse(window.live_options_separator.isHidden())
            self.assertTrue(window.live_interference_mode_combo.isHidden())

            set_map_type("interference")
            self.assertEqual(combo_values(window.live_band_combo), ["2.4", "5"])
            self.assertEqual(window.current_combo_value(window.live_band_combo), "2.4")
            self.assertEqual(window.live_band_combo.width(), window.live_interference_mode_combo.width())
            self.assertEqual(grid_position(window.live_band_label)[:2], (0, 0))
            self.assertEqual(grid_position(window.live_band_combo)[:2], (0, 1))
            self.assertEqual(grid_position(window.live_interference_mode_label)[:2], (1, 0))
            self.assertEqual(grid_position(window.live_interference_mode_combo)[:2], (1, 1))
            self.assertEqual(grid_position(window.live_interpolation_label)[:2], (2, 0))
            self.assertFalse(window.live_band_combo.isHidden())
            self.assertFalse(window.live_interference_mode_combo.isHidden())
            self.assertFalse(window.live_interpolation_combo.isHidden())
            self.assertTrue(window.live_aggregation_combo.isHidden())
            self.assertTrue(window.live_usable_check.isHidden())
            self.assertTrue(window.live_ap_group_combo.isHidden())
            self.assertTrue(window.live_options_separator.isHidden())
            self.assertEqual(window.live_options_layout.indexOf(window.live_options_separator), -1)

            set_map_type("channel")
            self.assertEqual(combo_values(window.live_band_combo), ["all", "2.4", "5"])
            self.assertEqual(grid_position(window.live_ap_group_label)[:2], (0, 0))
            self.assertEqual(grid_position(window.live_band_label)[:2], (1, 0))
            self.assertFalse(window.live_band_combo.isHidden())
            self.assertFalse(window.live_ap_group_combo.isHidden())
            self.assertTrue(window.live_interference_mode_combo.isHidden())
            self.assertTrue(window.live_interpolation_combo.isHidden())

            set_map_type("dominant")
            self.assertEqual(combo_values(window.live_band_combo), ["all", "2.4", "5"])
            self.assertEqual(grid_position(window.live_band_label)[:2], (0, 0))
            self.assertFalse(window.live_band_combo.isHidden())
            self.assertTrue(window.live_aggregation_combo.isHidden())
            self.assertTrue(window.live_interference_mode_combo.isHidden())
            self.assertTrue(window.live_interpolation_combo.isHidden())
            self.assertTrue(window.live_usable_check.isHidden())
            self.assertTrue(window.live_ap_group_combo.isHidden())
        finally:
            window.deleteLater()

    def test_live_options_remember_values_per_map_type(self):
        window = WifiHeatmapQtApp()
        try:
            window.live_ap_group_filter_items = lambda: [("ap-1", "AP 1")]
            window.refresh_live_ap_group_filter()

            def set_map_type(value):
                index = window.live_map_type_combo.findData(value)
                window.live_map_type_combo.blockSignals(True)
                window.live_map_type_combo.setCurrentIndex(index)
                window.live_map_type_combo.blockSignals(False)
                window.update_live_option_state()

            def set_combo_value(combo, value):
                index = combo.findData(value)
                combo.blockSignals(True)
                combo.setCurrentIndex(index)
                combo.blockSignals(False)

            set_map_type("signal")
            set_combo_value(window.live_band_combo, "all")
            set_combo_value(window.live_aggregation_combo, "median")
            set_combo_value(window.live_interpolation_combo, "linear")
            window.live_usable_check.blockSignals(True)
            window.live_usable_check.setChecked(True)
            window.live_usable_check.blockSignals(False)
            window.update_live_option_state()

            set_map_type("interference")
            self.assertEqual(window.current_combo_value(window.live_band_combo), "2.4")
            set_combo_value(window.live_band_combo, "5")
            set_combo_value(window.live_interference_mode_combo, "all")
            set_combo_value(window.live_interpolation_combo, "rbf")
            window.update_live_option_state()

            set_map_type("signal")
            self.assertEqual(window.current_combo_value(window.live_band_combo), "all")
            self.assertEqual(window.current_combo_value(window.live_aggregation_combo), "median")
            self.assertEqual(window.current_combo_value(window.live_interpolation_combo), "linear")
            self.assertTrue(window.live_usable_check.isChecked())

            set_map_type("interference")
            self.assertEqual(window.current_combo_value(window.live_band_combo), "5")
            self.assertEqual(window.current_combo_value(window.live_interference_mode_combo), "all")
            self.assertEqual(window.current_combo_value(window.live_interpolation_combo), "rbf")

            window.reset_live_option_memory()
            set_map_type("signal")
            self.assertEqual(window.current_combo_value(window.live_band_combo), "all")
            self.assertEqual(window.current_combo_value(window.live_aggregation_combo), "max")
            self.assertEqual(window.current_combo_value(window.live_interpolation_combo), "rbf")
            self.assertFalse(window.live_usable_check.isChecked())
        finally:
            window.deleteLater()


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
