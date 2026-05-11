import unittest
import logging
import os
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QGraphicsItem, QGraphicsView, QListWidgetItem, QWidget
from PIL import Image

from app_logging import MaxLogLevelFilter
from app_restart import build_restart_command
from app_settings import get_last_survey_directory, save_last_survey_path
from constants import RAW_DATA_FILE_METADATA_KEY
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
from ap_metadata_checks import build_ap_metadata_warnings
from ap_positioning import (
    AP_POSITION_MISSING,
    AP_POSITION_NO_SCALE,
    AP_POSITION_OK,
    AP_POSITION_STRONG_FAR,
    AP_POSITION_UNEXPECTED_DOMINANT,
    AP_POSITION_WEAK_CLOSE,
    analyze_dominant_ap_position,
)
from heatmap_tools import calculate_interference_points, get_channel_map_points, get_dominant_ap_points
from live_renderer import build_signal_payload
from map_exporter import (
    MapExportResult,
    annotate_interference_problem_numbers,
    build_interference_problem_report_pages,
    build_problem_report_pages,
    generate_live_pdf_export,
    get_interference_problem_df,
)
import matplotlib.pyplot as plt
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

    def test_default_manual_groups_are_unlocked_auto_suggestions(self):
        first_bssid = "70:4f:57:aa:bb:10"
        second_bssid = "70:4f:57:aa:bb:11"
        groups = build_default_manual_groups([
            build_row("p1", "MAIN", first_bssid, -50, 1),
            build_row("p1", "GUEST", second_bssid, -55, 1),
        ])

        self.assertEqual(len(groups), 1)
        self.assertFalse(groups[0]["locked"])
        self.assertEqual(groups[0]["role"], AP_ROLE_INTERNAL)
        self.assertEqual(groups[0]["bssids"], [first_bssid, second_bssid])

    def test_merge_new_bssids_preserves_manual_group_details(self):
        known_bssid = "70:4f:57:aa:bb:10"
        new_bssid = "90:11:22:33:44:10"
        manual_group = build_manual_ap_group(
            "office-ap",
            [known_bssid],
            alias="Office AP",
            locked=True,
            position={"x": 10, "y": 20},
            role=AP_ROLE_INTERFERER,
            metadata={"vendor": "Acme", "expected_channels": "1"},
        )

        merged = merge_new_bssids_into_manual_groups(
            [manual_group],
            [
                build_row("p1", "MAIN", known_bssid, -50, 1),
                build_row("p2", "MAIN", new_bssid, -60, 6),
            ],
        )

        preserved = next(group for group in merged if group["group_id"] == "office-ap")
        added = next(group for group in merged if group["group_id"] != "office-ap")

        self.assertEqual(preserved["alias"], "Office AP")
        self.assertTrue(preserved["locked"])
        self.assertEqual(preserved["position"], {"x": 10, "y": 20})
        self.assertEqual(preserved["role"], AP_ROLE_INTERFERER)
        self.assertEqual(preserved["metadata"]["vendor"], "Acme")
        self.assertFalse(added["locked"])
        self.assertEqual(added["role"], AP_ROLE_INTERNAL)
        self.assertEqual(added["bssids"], [new_bssid])

    def test_merge_new_bssids_uses_unique_group_id_when_auto_key_collides(self):
        existing_group_id = "11:22:33:44:1*"
        new_bssid = "90:11:22:33:44:10"
        manual_group = build_manual_ap_group(existing_group_id, ["70:aa:bb:cc:dd:10"])

        merged = merge_new_bssids_into_manual_groups(
            [manual_group],
            [build_row("p1", "MAIN", new_bssid, -60, 6)],
        )

        self.assertEqual(
            sorted(group["group_id"] for group in merged),
            [existing_group_id, f"{existing_group_id}#2"],
        )

    def test_ap_group_conflicts_detect_same_band_multi_channel_and_ignore_test_groups(self):
        internal_bssids = ["70:4f:57:aa:bb:10", "70:4f:57:aa:bb:11", "70:4f:57:aa:bb:50"]
        test_bssids = ["80:11:22:33:44:10", "80:11:22:33:44:11"]
        groups = [
            build_manual_ap_group("office-ap", internal_bssids, role=AP_ROLE_INTERNAL),
            build_manual_ap_group("test-ap", test_bssids, role=AP_ROLE_TEST),
        ]
        rows = [
            build_row("p1", "MAIN", internal_bssids[0], -50, 1),
            build_row("p1", "MAIN", internal_bssids[1], -51, 6),
            build_row("p1", "MAIN", internal_bssids[2], -52, 36),
            build_row("p1", "MAIN", test_bssids[0], -30, 1),
            build_row("p1", "MAIN", test_bssids[1], -31, 11),
        ]

        conflicts = build_ap_group_conflicts(rows, groups)

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["group_id"], "office-ap")
        self.assertEqual(conflicts[0]["band"], "2.4")
        self.assertEqual(conflicts[0]["channels"], ["1", "6"])
        self.assertEqual(conflicts[0]["bssids_by_channel"]["1"], [internal_bssids[0]])
        self.assertEqual(conflicts[0]["bssids_by_channel"]["6"], [internal_bssids[1]])


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

    def test_quality_marks_low_confidence_dominant_relevant_candidate(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -52, 1)
        row["scan_confidence"] = "0.2"

        quality = evaluate_point_quality([row], relevant_ssids={"MAIN"})

        self.assertEqual(quality["p1"]["status"], QUALITY_LOW_CONFIDENCE)
        self.assertEqual(quality["p1"]["breakdown"][0]["message"], "low_confidence")

    def test_quality_marks_unstable_signal_from_raw_samples(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -52, 1)
        raw_rows = [
            build_raw_row("p1", "MAIN", "70:4f:57:aa:bb:10", -45, 1),
            build_raw_row("p1", "MAIN", "70:4f:57:aa:bb:10", -59, 1),
            build_raw_row("p1", "MAIN", "70:4f:57:aa:bb:10", -52, 1),
        ]

        quality = evaluate_point_quality([row], raw_rows, relevant_ssids={"MAIN"})

        self.assertEqual(quality["p1"]["status"], QUALITY_UNSTABLE_SIGNAL)
        self.assertEqual(quality["p1"]["breakdown"][0]["range_db"], 14.0)

    def test_quality_marks_sparse_data_when_samples_are_too_few(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -52, 1)
        row["samples_seen"] = "1"

        quality = evaluate_point_quality([row], relevant_ssids={"MAIN"})

        self.assertEqual(quality["p1"]["status"], QUALITY_SPARSE_DATA)

    def test_quality_missing_relevant_takes_priority_over_low_confidence(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -52, 1)
        row["scan_confidence"] = "0.1"

        quality = evaluate_point_quality([row], relevant_ssids={"MAIN", "GUEST"})

        self.assertEqual(quality["p1"]["status"], QUALITY_MISSING_RELEVANT)
        self.assertEqual(quality["p1"]["missing_relevant"], ["guest"])

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


class ApPositioningTests(unittest.TestCase):
    def test_dominant_ap_position_reports_missing_position(self):
        result = analyze_dominant_ap_position(
            {"x": 10, "y": 20, "dominant_ap_group": "ap-1", "dominant_signal_dbm": -60},
            [],
            px_per_meter=10,
        )

        self.assertEqual(result["status"], AP_POSITION_MISSING)
        self.assertFalse(result["has_position"])

    def test_dominant_ap_position_reports_no_scale_when_position_exists(self):
        result = analyze_dominant_ap_position(
            {"x": 10, "y": 20, "dominant_ap_group": "ap-1", "dominant_signal_dbm": -60},
            [{"group_id": "ap-1", "position": {"x": 10, "y": 40}}],
            px_per_meter=None,
        )

        self.assertEqual(result["status"], AP_POSITION_NO_SCALE)
        self.assertTrue(result["has_position"])
        self.assertEqual(result["dominant_distance_px"], 20.0)

    def test_dominant_ap_position_flags_strong_far_and_weak_close(self):
        strong_far = analyze_dominant_ap_position(
            {"x": 0, "y": 0, "dominant_ap_group": "ap-1", "dominant_signal_dbm": -50},
            [{"group_id": "ap-1", "position": {"x": 30, "y": 0}}],
            px_per_meter=1,
        )
        weak_close = analyze_dominant_ap_position(
            {"x": 0, "y": 0, "dominant_ap_group": "ap-1", "dominant_signal_dbm": -80},
            [{"group_id": "ap-1", "position": {"x": 4, "y": 0}}],
            px_per_meter=1,
        )

        self.assertEqual(strong_far["status"], AP_POSITION_STRONG_FAR)
        self.assertEqual(weak_close["status"], AP_POSITION_WEAK_CLOSE)

    def test_dominant_ap_position_flags_unexpected_dominant_against_nearest_internal_ap(self):
        result = analyze_dominant_ap_position(
            {"x": 0, "y": 0, "dominant_ap_group": "far-ap", "dominant_signal_dbm": -62},
            [
                {"group_id": "far-ap", "position": {"x": 30, "y": 0}, "role": AP_ROLE_INTERNAL},
                {"group_id": "near-ap", "position": {"x": 5, "y": 0}, "role": AP_ROLE_INTERNAL},
            ],
            px_per_meter=1,
        )

        self.assertEqual(result["status"], AP_POSITION_UNEXPECTED_DOMINANT)
        self.assertEqual(result["nearest_ap_group"], "near-ap")

    def test_dominant_ap_position_ignores_test_hidden_ap_positions_as_nearest(self):
        result = analyze_dominant_ap_position(
            {"x": 0, "y": 0, "dominant_ap_group": "far-ap", "dominant_signal_dbm": -62},
            [
                {"group_id": "far-ap", "position": {"x": 30, "y": 0}, "role": AP_ROLE_INTERNAL},
                {"group_id": "hidden-ap", "position": {"x": 5, "y": 0}, "role": AP_ROLE_TEST},
            ],
            px_per_meter=1,
        )

        self.assertEqual(result["status"], AP_POSITION_OK)
        self.assertEqual(result["nearest_ap_group"], "far-ap")


class SurveyStoreTests(unittest.TestCase):
    def test_session_roundtrips_v2_metadata_and_raw_scan_sidecar(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            survey_file = os.path.join(temp_dir, "office.csv")
            session = SurveySession()
            session.add_points(
                100,
                120,
                [
                    {
                        "ssid": "MAIN",
                        "bssid": "70:4f:57:aa:bb:10",
                        "signal_percent": "80",
                        "signal_dbm": -50,
                        "signal_median_dbm": -51,
                        "signal_max_dbm": -48,
                        "signal_min_dbm": -54,
                        "signal_samples_dbm": "-50;-52;-48",
                        "samples_seen": "3",
                        "samples_total": "5",
                        "scan_confidence": "0.6",
                        "channel": "6",
                        "channel_width_mhz": "20",
                        "radio": "802.11ax",
                        "raw_samples": [
                            {
                                "scan_attempt": "1",
                                "ssid": "MAIN",
                                "bssid": "70:4f:57:aa:bb:10",
                                "signal_percent": "78",
                                "signal_dbm": "-52",
                                "channel": "6",
                                "channel_width_mhz": "20",
                                "radio": "802.11ax",
                                "backend": "netsh",
                            },
                            {
                                "scan_attempt": "2",
                                "ssid": "MAIN",
                                "bssid": "70:4f:57:aa:bb:10",
                                "signal_percent": "82",
                                "signal_dbm": "-48",
                                "channel": "6",
                                "channel_width_mhz": "20",
                                "radio": "802.11ax",
                                "backend": "lswifi",
                            },
                        ],
                    }
                ],
                relevant_ssids={"MAIN"},
            )
            session.set_ap_groups([
                build_manual_ap_group(
                    "office-ap",
                    ["70:4F:57:AA:BB:10"],
                    alias="Office AP",
                    position={"x": 21.4, "y": 44.6},
                    role=AP_ROLE_EXTERNAL,
                    metadata={
                        "vendor": "Acme",
                        "model": "AX-1",
                        "expected_bands": "2.4,5",
                        "expected_channels": "6,36",
                        "notes": "Mounted in office",
                    },
                )
            ])

            session.save(survey_file)

            raw_scan_file = build_raw_scan_file_path(survey_file, session.metadata)
            self.assertTrue(os.path.exists(raw_scan_file))
            self.assertEqual(
                session.metadata[RAW_DATA_FILE_METADATA_KEY],
                os.path.basename(raw_scan_file),
            )

            loaded = SurveySession(survey_file)

            self.assertFalse(loaded.dirty)
            self.assertEqual(len(loaded.rows), 1)
            self.assertEqual(loaded.rows[0]["is_relevant"], "1")
            self.assertEqual(loaded.rows[0]["signal_median_dbm"], "-51")
            self.assertEqual(len(loaded.raw_scan_rows), 2)
            self.assertEqual(
                {row["backend"] for row in loaded.raw_scan_rows},
                {"netsh", "lswifi"},
            )
            self.assertEqual(loaded.metadata[RAW_DATA_FILE_METADATA_KEY], os.path.basename(raw_scan_file))

            groups = loaded.get_ap_groups()
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0]["group_id"], "office-ap")
            self.assertEqual(groups[0]["alias"], "Office AP")
            self.assertEqual(groups[0]["bssids"], ["70:4f:57:aa:bb:10"])
            self.assertEqual(groups[0]["position"], {"x": 21, "y": 45})
            self.assertEqual(groups[0]["role"], AP_ROLE_EXTERNAL)
            self.assertEqual(groups[0]["metadata"]["expected_channels"], "6,36")

    def test_opening_raw_scan_sidecar_as_survey_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            survey_file = os.path.join(temp_dir, "office.csv")
            session = SurveySession()
            session.add_points(
                10,
                20,
                [{
                    "ssid": "MAIN",
                    "bssid": "70:4f:57:aa:bb:10",
                    "signal_percent": "80",
                    "signal_dbm": -50,
                    "channel": "6",
                    "radio": "802.11ax",
                }],
                relevant_ssids={"MAIN"},
            )
            session.save(survey_file)

            with self.assertRaises(SurveyFormatError) as error:
                SurveySession(build_raw_scan_file_path(survey_file, session.metadata))

            self.assertEqual(str(error.exception), "raw_scan_file")


class ApRoleFilteringTests(unittest.TestCase):
    def build_role_filter_inputs(self):
        internal_bssid = "70:4f:57:aa:bb:10"
        test_bssid = "80:11:22:33:44:10"
        neighbor_bssid = "90:11:22:33:44:10"
        groups = [
            build_manual_ap_group("internal-ap", [internal_bssid], role=AP_ROLE_INTERNAL),
            build_manual_ap_group("test-ap", [test_bssid], role=AP_ROLE_TEST),
            build_manual_ap_group("neighbor-ap", [neighbor_bssid], role=AP_ROLE_EXTERNAL),
        ]
        group_map = serialize_ap_group_map(build_bssid_to_manual_group_map(groups))
        role_map = serialize_ap_group_roles(build_ap_group_role_map(groups))
        return internal_bssid, test_bssid, neighbor_bssid, group_map, role_map

    def test_channel_and_dominant_maps_ignore_test_hidden_ap_groups(self):
        internal_bssid, test_bssid, _neighbor_bssid, group_map, role_map = self.build_role_filter_inputs()
        rows = [
            build_row("p1", "MAIN", internal_bssid, -70, 1),
            build_row("p1", "MAIN", test_bssid, -30, 6),
        ]
        df = rows_to_dataframe(rows)

        channel_df = get_channel_map_points(df, "MAIN", "2.4", group_map, role_map)
        dominant_df = get_dominant_ap_points(df, "MAIN", "2.4", group_map, role_map)

        self.assertEqual(channel_df.iloc[0]["bssid"], internal_bssid)
        self.assertEqual(channel_df.iloc[0]["channel"], 1)
        self.assertEqual(dominant_df.iloc[0]["dominant_bssid"], internal_bssid)
        self.assertEqual(dominant_df.iloc[0]["dominant_ap_group"], "internal-ap")

    def test_signal_coverage_ignores_test_hidden_ap_groups_before_aggregation(self):
        internal_bssid, test_bssid, _neighbor_bssid, group_map, role_map = self.build_role_filter_inputs()
        rows = []
        for point_id, x, y, signal in (
            ("p1", "10", "10", -70),
            ("p2", "50", "20", -71),
            ("p3", "30", "60", -72),
        ):
            internal_row = build_row(point_id, "MAIN", internal_bssid, signal, 1)
            internal_row["x"] = x
            internal_row["y"] = y
            test_row = build_row(point_id, "MAIN", test_bssid, -30, 6)
            test_row["x"] = x
            test_row["y"] = y
            rows.extend([internal_row, test_row])

        payload = build_signal_payload(
            rows_to_dataframe(rows),
            MapConfig(
                ssid="MAIN",
                band="2.4",
                map_type="signal",
                ap_group_map=group_map,
                ap_group_roles=role_map,
                smoothing_sigma=0,
                max_distance_px=200,
            ),
            Image.new("RGB", (100, 80), "white"),
            {"signal_title": "Signal", "source_rows": "Rows"},
            lambda _map_type, row, _raw_rows: str(row["signal_dbm"]),
            lambda _grid_z, _config: (-90, -30),
        )

        try:
            self.assertIsNotNone(payload)
            self.assertEqual(len(payload["point_infos"]), 3)
            self.assertNotIn("-30", {point["tooltip"] for point in payload["point_infos"]})
        finally:
            if payload and "fig" in payload:
                plt.close(payload["fig"])

    def test_interference_uses_internal_serving_ap_and_counts_ignored_test_ap(self):
        internal_bssid, test_bssid, neighbor_bssid, group_map, role_map = self.build_role_filter_inputs()
        rows = [
            build_row("p1", "MAIN", internal_bssid, -50, 1),
            build_row("p1", "MAIN", test_bssid, -20, 1),
            build_row("p1", "NEIGHBOR", neighbor_bssid, -55, 1),
        ]

        risk_df = calculate_interference_points(
            rows_to_dataframe(rows),
            "MAIN",
            "2.4",
            mode="all",
            include_details=True,
            ap_group_map=group_map,
            ap_group_roles=role_map,
        )

        self.assertEqual(len(risk_df), 1)
        row = risk_df.iloc[0]
        self.assertEqual(row["serving_bssid"], internal_bssid)
        self.assertEqual(row["test_ap_ignored_count"], 1)
        self.assertEqual(row["strongest_interferer_bssid"], neighbor_bssid)
        self.assertNotIn(test_bssid, row["interfering_bssids"])


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

    def test_live_interference_tooltip_hides_empty_interferer_rows(self):
        translations = {
            "interference_title": "AP interference",
            "risk": "Risk",
            "serving_ap": "Serving AP",
            "serving_channel": "Serving channel",
            "interferer": "Main interferer",
            "interferer_channel": "Interferer channel",
        }
        tooltip = build_live_tooltip(
            "interference",
            {
                "x": 10,
                "y": 20,
                "risk": 0,
                "serving_bssid": "70:4f:57:aa:bb:10",
                "serving_channel": 1,
                "strongest_interferer_bssid": "",
                "strongest_interferer_channel": "",
            },
            None,
            translations,
        )

        self.assertIn("Serving AP", tooltip)
        self.assertNotIn("Main interferer", tooltip)
        self.assertNotIn("Interferer channel", tooltip)

    def test_live_interference_tooltip_shows_interferer_rows_when_present(self):
        translations = {
            "interference_title": "AP interference",
            "risk": "Risk",
            "serving_ap": "Serving AP",
            "serving_channel": "Serving channel",
            "interferer": "Main interferer",
            "interferer_channel": "Interferer channel",
        }
        tooltip = build_live_tooltip(
            "interference",
            {
                "x": 10,
                "y": 20,
                "risk": 45,
                "serving_bssid": "70:4f:57:aa:bb:10",
                "serving_channel": 1,
                "strongest_interferer_bssid": "80:11:22:33:44:10",
                "strongest_interferer_channel": 6,
            },
            None,
            translations,
        )

        self.assertIn("Main interferer", tooltip)
        self.assertIn("Interferer channel", tooltip)
        self.assertIn("33:44:10", tooltip)

    def test_live_channel_point_labels_follow_auto_and_none_modes(self):
        rows = [
            build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 1),
            build_row("p2", "MAIN", "70:4f:57:aa:bb:10", -52, 1),
            build_row("p3", "MAIN", "70:4f:57:aa:bb:20", -54, 6),
        ]
        payload = build_channel_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="2.4", map_type="channel", point_label_mode="auto"),
            Image.new("RGB", (100, 100), "white"),
            {"channel_title": "AP channels"},
            {},
        )

        self.assertFalse(any(point.get("label") for point in payload["point_infos"]))
        self.assertEqual(len(payload["scale_payload"]["items"]), 2)
        self.assertEqual([item["marker_id"] for item in payload["scale_payload"]["items"]], ["channel-0", "channel-2"])

        payload = build_channel_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="2.4", map_type="channel", point_label_mode="all"),
            Image.new("RGB", (100, 100), "white"),
            {"channel_title": "AP channels"},
            {},
        )

        self.assertFalse(any(point.get("label") for point in payload["point_infos"]))
        self.assertEqual(len(payload["scale_payload"]["items"]), 3)
        self.assertEqual([item["marker_id"] for item in payload["scale_payload"]["items"]], [
            "channel-0",
            "channel-1",
            "channel-2",
        ])

        payload = build_channel_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="2.4", map_type="channel", point_label_mode="none"),
            Image.new("RGB", (100, 100), "white"),
            {"channel_title": "AP channels"},
            {},
        )

        self.assertFalse(any(point.get("label") for point in payload["point_infos"]))
        self.assertIsNone(payload["scale_payload"])

    def test_live_dominant_point_labels_follow_auto_and_none_modes(self):
        rows = [
            build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 1),
            build_row("p2", "MAIN", "70:4f:57:aa:bb:10", -52, 1),
            build_row("p3", "MAIN", "80:11:22:33:44:10", -54, 6),
        ]
        payload = build_dominant_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="2.4", map_type="dominant", point_label_mode="auto"),
            Image.new("RGB", (100, 100), "white"),
            {"dominant_title": "Dominant AP"},
            {},
            [],
            None,
        )

        self.assertFalse(any(point.get("label") for point in payload["point_infos"]))
        self.assertEqual(len(payload["scale_payload"]["items"]), 2)
        self.assertEqual([item["marker_id"] for item in payload["scale_payload"]["items"]], [
            "dominant-0",
            "dominant-2",
        ])

        payload = build_dominant_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="2.4", map_type="dominant", point_label_mode="all"),
            Image.new("RGB", (100, 100), "white"),
            {"dominant_title": "Dominant AP"},
            {},
            [],
            None,
        )

        self.assertFalse(any(point.get("label") for point in payload["point_infos"]))
        self.assertEqual(len(payload["scale_payload"]["items"]), 3)
        self.assertEqual([item["marker_id"] for item in payload["scale_payload"]["items"]], [
            "dominant-0",
            "dominant-1",
            "dominant-2",
        ])

        payload = build_dominant_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="2.4", map_type="dominant", point_label_mode="none"),
            Image.new("RGB", (100, 100), "white"),
            {"dominant_title": "Dominant AP"},
            {},
            [],
            None,
        )

        self.assertFalse(any(point.get("label") for point in payload["point_infos"]))
        self.assertIsNone(payload["scale_payload"])

    def test_live_legend_marker_actions_highlight_and_focus_points(self):
        view = LiveMapView()
        try:
            view.resize(320, 240)
            view.set_payload({
                "image": Image.new("RGB", (200, 160), "white"),
                "point_infos": [
                    {"marker_id": "p1", "x": 40, "y": 50, "color": "#111111"},
                    {"marker_id": "p2", "x": 90, "y": 80, "color": "#d62728"},
                ],
                "scale_payload": None,
            })

            self.assertTrue(view.highlight_marker("p2"))
            self.assertIsNotNone(view.marker_highlight_item)
            self.assertEqual(view.marker_highlight_item.pos(), view.marker_items_by_id["p2"].scenePos())
            self.assertTrue(view.focus_marker("p1"))
            self.assertEqual(view.marker_highlight_item.pos(), view.marker_items_by_id["p1"].scenePos())
            self.assertFalse(view.highlight_marker("missing"))
        finally:
            view.deleteLater()

    def test_live_background_click_emits_only_outside_point_markers(self):
        view = LiveMapView()
        try:
            view.resize(320, 240)
            view.show()
            view.set_payload({
                "image": Image.new("RGB", (200, 160), "white"),
                "point_infos": [
                    {"marker_id": "p1", "x": 90, "y": 70, "color": "#111111"},
                ],
                "scale_payload": None,
            })
            QApplication.processEvents()

            background_clicks = []
            view.backgroundClicked.connect(lambda: background_clicks.append(True))

            marker_pos = view.mapFromScene(view.marker_items_by_id["p1"].scenePos())
            QTest.mouseClick(
                view.viewport(),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                marker_pos,
            )
            QApplication.processEvents()
            self.assertEqual(background_clicks, [])

            QTest.mouseClick(
                view.viewport(),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(5, 5),
            )
            QApplication.processEvents()
            self.assertEqual(len(background_clicks), 1)
        finally:
            view.deleteLater()

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


class LivePdfExportTests(unittest.TestCase):
    def build_live_pdf_rows(self):
        rows = []
        for point_id, x, y, signal in (
            ("p1", "10", "10", -45),
            ("p2", "90", "20", -62),
            ("p3", "40", "80", -74),
        ):
            row = build_row(point_id, "MAIN", f"70:4f:57:aa:bb:{point_id[-1]}", signal, 6)
            row["x"] = x
            row["y"] = y
            rows.append(row)
        return rows

    def test_live_pdf_export_uses_current_config_and_writes_pdf(self):
        rows = self.build_live_pdf_rows()

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = os.path.join(temp_dir, "survey.csv")
            output_file = os.path.join(temp_dir, "chosen_live_export.pdf")
            result = generate_live_pdf_export(
                rows_to_dataframe(rows),
                Image.new("RGB", (120, 100), "white"),
                csv_file,
                MapConfig(
                    ssid="MAIN",
                    band="2.4",
                    map_type="signal",
                    interpolation="linear",
                    color_scale="auto",
                    smoothing_sigma=0,
                    max_distance_px=300,
                ),
                lambda key, **kwargs: translate("en", key, **kwargs),
                language="en",
                ap_groups=[
                    {"group_id": "ap-main", "position": {"x": 20, "y": 30}, "role": "internal"},
                ],
                output_file=output_file,
            )

            self.assertEqual(result.map_type, "signal")
            self.assertEqual(result.output_file, output_file)
            self.assertTrue(os.path.exists(result.output_file))
            with open(result.output_file, "rb") as pdf_file:
                self.assertEqual(pdf_file.read(4), b"%PDF")
            import fitz

            with fitz.open(result.output_file) as doc:
                self.assertEqual(doc[0].get_images(full=True), [])
                self.assertGreater(doc[0].get_pixmap(alpha=False).width, 0)

    def test_problem_report_pages_use_wrapped_card_layout(self):
        rows = [
            [
                f"{10 + index}, {20 + index}",
                "100.0%",
                "6",
                "6",
                (
                    "The main issue is a strong interferer on the same channel "
                    "and the diagnosis needs enough room to stay readable."
                ),
            ]
            for index in range(6)
        ]

        figures = build_problem_report_pages(
            "Problem report",
            "Wi-Fi AP interference - MAIN - 2.4 GHz",
            ["Point", "Risk", "Serving channel", "Interfering channel", "Diagnosis"],
            rows,
            "No issues",
        )
        try:
            self.assertEqual(len(figures), 2)
            first_page_text = "\n".join(text.get_text() for text in figures[0].axes[0].texts)
            self.assertIn("1/2", first_page_text)
            self.assertIn("1. Point: 10, 20", first_page_text)
            self.assertIn("Diagnosis", first_page_text)
        finally:
            for fig in figures:
                plt.close(fig)

    def test_interference_problem_report_uses_tooltip_fields(self):
        risk_df = rows_to_dataframe([
            {
                "x": 10,
                "y": 20,
                "risk": 100,
                "serving_bssid": "70:4f:57:aa:bb:10",
                "serving_ap_group": "serving-group",
                "serving_channel": 6,
                "serving_channel_width_mhz": 20,
                "strongest_interferer_bssid": "80:11:22:33:44:10",
                "strongest_interferer_ap_group": "interferer-group",
                "strongest_interferer_channel": 6,
                "strongest_interferer_channel_width_mhz": 20,
            },
            {
                "x": 30,
                "y": 40,
                "risk": 40,
                "serving_bssid": "70:4f:57:aa:bb:20",
                "serving_ap_group": "serving-group-2",
                "serving_channel": 11,
                "serving_channel_width_mhz": "",
                "strongest_interferer_bssid": "80:11:22:33:44:20",
                "strongest_interferer_ap_group": "interferer-group-2",
                "strongest_interferer_channel": 10,
                "strongest_interferer_channel_width_mhz": "",
            },
        ])

        figures = build_interference_problem_report_pages(
            risk_df,
            MapConfig(ssid="MAIN", band="2.4", map_type="interference"),
            lambda key, **kwargs: translate("en", key, **kwargs),
            "en",
            {
                "serving-group": "Serving AP",
                "interferer-group": "Neighbor AP",
            },
        )
        try:
            first_page_text = "\n".join(text.get_text() for text in figures[0].axes[0].texts)
            self.assertIn("(10, 20)", first_page_text)
            self.assertIn("Risk: 100.0%", first_page_text)
            self.assertIn("Serving AP (70:4f:57:aa:bb:10)", first_page_text)
            self.assertIn("CH 6 / 20 MHz", first_page_text)
            self.assertIn("Neighbor AP (80:11:22:33:44:10)", first_page_text)
            self.assertNotIn("Point 1", first_page_text)
            self.assertNotIn("Serving channel:", first_page_text)
            self.assertNotIn("Interfering channel:", first_page_text)
            self.assertNotIn("Diagnosis", first_page_text)
        finally:
            for fig in figures:
                plt.close(fig)

    def test_interference_problem_numbers_follow_report_order(self):
        risk_df = rows_to_dataframe([
            {"x": 10, "y": 20, "risk": 40},
            {"x": 30, "y": 40, "risk": 100},
            {"x": 50, "y": 60, "risk": 20},
        ])
        problem_df = get_interference_problem_df(risk_df)
        fig, ax = plt.subplots()
        try:
            annotate_interference_problem_numbers(ax, problem_df)
            labels = [text.get_text() for text in ax.texts]
            positions = [text.xy for text in ax.texts]

            self.assertEqual(labels, ["1", "2"])
            self.assertEqual(positions, [(30.0, 40.0), (10.0, 20.0)])
        finally:
            plt.close(fig)


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

    def test_live_pdf_file_message_omits_interference_summary(self):
        window = WifiHeatmapQtApp()
        try:
            result = MapExportResult(
                output_file="export.pdf",
                map_type="interference",
                summary={
                    "band": "2.4 GHz",
                    "max_risk": "100.0%",
                    "quality": {"available": 1, "total": 1, "percent": 100},
                },
            )

            file_message = window.format_map_export_files_message(result)
            full_message = window.format_map_export_result_message(result)

            self.assertEqual(file_message, window.tr("file_created", path="export.pdf"))
            self.assertNotIn(window.tr("interference_summary_title"), file_message)
            self.assertIn(window.tr("interference_summary_title"), full_message)
        finally:
            window.deleteLater()

    def test_live_background_click_clears_legend_selection_and_marker_highlight(self):
        window = WifiHeatmapQtApp()
        try:
            window.live_view.set_payload({
                "image": Image.new("RGB", (200, 160), "white"),
                "point_infos": [
                    {"marker_id": "p1", "x": 70, "y": 60, "color": "#111111"},
                ],
                "scale_payload": None,
            })
            list_item = QListWidgetItem("Point 1")
            list_item.setData(Qt.ItemDataRole.UserRole, {"marker_id": "p1"})
            window.live_legend_list.addItem(list_item)
            window.live_legend_list.setCurrentRow(0)
            self.assertTrue(window.live_view.highlight_marker("p1"))

            window.live_view.backgroundClicked.emit()

            self.assertEqual(window.live_legend_list.currentRow(), -1)
            self.assertEqual(window.live_legend_list.selectedItems(), [])
            self.assertIsNone(window.live_view.marker_highlight_item)
        finally:
            window.deleteLater()

    def test_live_toolbar_keeps_map_options_in_overlay(self):
        window = WifiHeatmapQtApp()
        try:
            self.assertIs(window.live_map_type_combo.parent(), window.live_toolbar_frame)
            self.assertIs(window.live_ssid_combo.parent(), window.live_toolbar_frame)
            self.assertIs(window.live_update_button.parent(), window.live_toolbar_frame)
            app_bar_layout = window.app_bar.layout()
            self.assertEqual(app_bar_layout.stretch(0), 1)
            self.assertEqual(app_bar_layout.stretch(1), 0)
            self.assertEqual(app_bar_layout.stretch(2), 1)
            toolbar_layout = window.live_toolbar_frame.layout()
            self.assertIsNone(window.live_pdf_export_button.menu())
            self.assertLess(
                toolbar_layout.indexOf(window.live_pdf_export_button),
                toolbar_layout.indexOf(window.live_export_separator),
            )
            self.assertLess(
                toolbar_layout.indexOf(window.live_export_separator),
                toolbar_layout.indexOf(window.live_update_button),
            )
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

    def test_live_pdf_export_asks_for_destination_path(self):
        window = WifiHeatmapQtApp()
        original_save_file_name = qt_app_module.get_centered_save_file_name
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                class FakeSession:
                    csv_file = os.path.join(temp_dir, "survey.csv")

                captured = {}
                chosen_path = os.path.join(temp_dir, "custom_live_export")

                def fake_save_file_name(parent, title, default_path, file_filter):
                    captured["title"] = title
                    captured["default_path"] = default_path
                    captured["file_filter"] = file_filter
                    return chosen_path, ""

                qt_app_module.get_centered_save_file_name = fake_save_file_name
                window.session = FakeSession()

                output_file = window.choose_live_pdf_output_file(MapConfig(ssid="MAIN", map_type="signal"))

                self.assertEqual(output_file, f"{chosen_path}.pdf")
                self.assertEqual(captured["title"], window.tr("save_live_pdf_title"))
                self.assertEqual(captured["file_filter"], window.tr("live_pdf_file_filter"))
                self.assertIn("MAIN_coverage", captured["default_path"])
        finally:
            qt_app_module.get_centered_save_file_name = original_save_file_name
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
            self.assertEqual(grid_position(window.live_band_label)[:2], (1, 0))
            self.assertEqual(grid_position(window.live_color_scale_label)[:2], (2, 0))
            self.assertEqual(grid_position(window.live_interpolation_label)[:2], (3, 0))
            self.assertEqual(grid_position(window.live_aggregation_label)[:2], (4, 0))
            self.assertEqual(grid_position(window.live_options_separator), (5, 0, 1, 2))
            self.assertEqual(grid_position(window.live_max_distance_label)[:2], (6, 0))
            self.assertEqual(grid_position(window.live_smoothing_label)[:2], (7, 0))
            self.assertEqual(grid_position(window.live_checkbox_separator), (8, 0, 1, 2))
            self.assertEqual(grid_position(window.live_usable_check), (9, 0, 1, 2))
            self.assertEqual(window.live_band_combo.width(), window.live_interpolation_combo.width())
            self.assertEqual(window.live_band_combo.width(), window.live_max_distance_spin.width())
            required_group_width = window.live_ap_group_combo.fontMetrics().horizontalAdvance("All AP groups")
            self.assertGreater(window.live_ap_group_combo.width(), required_group_width + window.spx(70))
            self.assertLess(window.live_band_combo.width(), window.spx(300))
            self.assertFalse(window.live_band_combo.isHidden())
            self.assertFalse(window.live_aggregation_combo.isHidden())
            self.assertFalse(window.live_color_scale_combo.isHidden())
            self.assertFalse(window.live_interpolation_combo.isHidden())
            self.assertFalse(window.live_max_distance_spin.isHidden())
            self.assertFalse(window.live_smoothing_spin.isHidden())
            self.assertFalse(window.live_usable_check.isHidden())
            self.assertFalse(window.live_ap_group_combo.isHidden())
            self.assertFalse(window.live_options_separator.isHidden())
            self.assertFalse(window.live_checkbox_separator.isHidden())
            self.assertTrue(window.live_interference_mode_combo.isHidden())
            self.assertTrue(window.live_point_labels_combo.isHidden())

            set_map_type("interference")
            self.assertEqual(combo_values(window.live_band_combo), ["2.4", "5"])
            self.assertEqual(window.current_combo_value(window.live_band_combo), "2.4")
            self.assertEqual(window.live_band_combo.width(), window.live_interference_mode_combo.width())
            self.assertEqual(grid_position(window.live_band_label)[:2], (0, 0))
            self.assertEqual(grid_position(window.live_band_combo)[:2], (0, 1))
            self.assertEqual(grid_position(window.live_color_scale_label)[:2], (1, 0))
            self.assertEqual(grid_position(window.live_interference_mode_label)[:2], (2, 0))
            self.assertEqual(grid_position(window.live_interference_mode_combo)[:2], (2, 1))
            self.assertEqual(grid_position(window.live_interpolation_label)[:2], (3, 0))
            self.assertEqual(grid_position(window.live_options_separator), (4, 0, 1, 2))
            self.assertEqual(grid_position(window.live_max_distance_label)[:2], (5, 0))
            self.assertEqual(grid_position(window.live_smoothing_label)[:2], (6, 0))
            self.assertFalse(window.live_band_combo.isHidden())
            self.assertFalse(window.live_color_scale_combo.isHidden())
            self.assertFalse(window.live_interference_mode_combo.isHidden())
            self.assertFalse(window.live_interpolation_combo.isHidden())
            self.assertFalse(window.live_max_distance_spin.isHidden())
            self.assertFalse(window.live_smoothing_spin.isHidden())
            self.assertTrue(window.live_aggregation_combo.isHidden())
            self.assertTrue(window.live_usable_check.isHidden())
            self.assertTrue(window.live_ap_group_combo.isHidden())
            self.assertTrue(window.live_point_labels_combo.isHidden())
            self.assertFalse(window.live_options_separator.isHidden())
            self.assertTrue(window.live_checkbox_separator.isHidden())
            self.assertEqual(window.live_options_layout.indexOf(window.live_checkbox_separator), -1)

            set_map_type("channel")
            self.assertEqual(combo_values(window.live_band_combo), ["all", "2.4", "5"])
            self.assertEqual(combo_values(window.live_point_labels_combo), ["auto", "all", "none"])
            self.assertEqual(grid_position(window.live_ap_group_label)[:2], (0, 0))
            self.assertEqual(grid_position(window.live_band_label)[:2], (1, 0))
            self.assertEqual(grid_position(window.live_point_labels_label)[:2], (2, 0))
            self.assertFalse(window.live_band_combo.isHidden())
            self.assertFalse(window.live_ap_group_combo.isHidden())
            self.assertFalse(window.live_point_labels_combo.isHidden())
            self.assertTrue(window.live_interference_mode_combo.isHidden())
            self.assertTrue(window.live_interpolation_combo.isHidden())
            self.assertTrue(window.live_color_scale_combo.isHidden())
            self.assertTrue(window.live_max_distance_spin.isHidden())
            self.assertTrue(window.live_smoothing_spin.isHidden())
            self.assertTrue(window.live_options_separator.isHidden())
            self.assertTrue(window.live_checkbox_separator.isHidden())

            set_map_type("dominant")
            self.assertEqual(combo_values(window.live_band_combo), ["all", "2.4", "5"])
            self.assertEqual(grid_position(window.live_band_label)[:2], (0, 0))
            self.assertEqual(grid_position(window.live_point_labels_label)[:2], (1, 0))
            self.assertFalse(window.live_band_combo.isHidden())
            self.assertFalse(window.live_point_labels_combo.isHidden())
            self.assertTrue(window.live_aggregation_combo.isHidden())
            self.assertTrue(window.live_interference_mode_combo.isHidden())
            self.assertTrue(window.live_interpolation_combo.isHidden())
            self.assertTrue(window.live_color_scale_combo.isHidden())
            self.assertTrue(window.live_max_distance_spin.isHidden())
            self.assertTrue(window.live_smoothing_spin.isHidden())
            self.assertTrue(window.live_usable_check.isHidden())
            self.assertTrue(window.live_ap_group_combo.isHidden())
            self.assertTrue(window.live_options_separator.isHidden())
            self.assertTrue(window.live_checkbox_separator.isHidden())
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
            set_combo_value(window.live_color_scale_combo, "auto")
            set_combo_value(window.live_interpolation_combo, "linear")
            window.live_smoothing_spin.blockSignals(True)
            window.live_smoothing_spin.setValue(4.5)
            window.live_smoothing_spin.blockSignals(False)
            window.live_max_distance_spin.blockSignals(True)
            window.live_max_distance_spin.setValue(260)
            window.live_max_distance_spin.blockSignals(False)
            window.live_usable_check.blockSignals(True)
            window.live_usable_check.setChecked(True)
            window.live_usable_check.blockSignals(False)
            window.update_live_option_state()

            set_map_type("interference")
            self.assertEqual(window.current_combo_value(window.live_band_combo), "2.4")
            set_combo_value(window.live_band_combo, "5")
            set_combo_value(window.live_color_scale_combo, "fixed")
            set_combo_value(window.live_interference_mode_combo, "all")
            set_combo_value(window.live_interpolation_combo, "rbf")
            window.live_smoothing_spin.blockSignals(True)
            window.live_smoothing_spin.setValue(2.0)
            window.live_smoothing_spin.blockSignals(False)
            window.update_live_option_state()

            set_map_type("signal")
            self.assertEqual(window.current_combo_value(window.live_band_combo), "all")
            self.assertEqual(window.current_combo_value(window.live_aggregation_combo), "median")
            self.assertEqual(window.current_combo_value(window.live_color_scale_combo), "auto")
            self.assertEqual(window.current_combo_value(window.live_interpolation_combo), "linear")
            self.assertEqual(window.live_smoothing_spin.value(), 4.5)
            self.assertEqual(window.current_live_max_distance_px(), 260)
            self.assertTrue(window.live_usable_check.isChecked())

            set_map_type("interference")
            self.assertEqual(window.current_combo_value(window.live_band_combo), "5")
            self.assertEqual(window.current_combo_value(window.live_color_scale_combo), "fixed")
            self.assertEqual(window.current_combo_value(window.live_interference_mode_combo), "all")
            self.assertEqual(window.current_combo_value(window.live_interpolation_combo), "rbf")
            self.assertEqual(window.live_smoothing_spin.value(), 2.0)

            set_map_type("channel")
            self.assertEqual(window.current_combo_value(window.live_point_labels_combo), "auto")
            set_combo_value(window.live_point_labels_combo, "all")
            window.update_live_option_state()

            set_map_type("dominant")
            self.assertEqual(window.current_combo_value(window.live_point_labels_combo), "auto")
            set_combo_value(window.live_point_labels_combo, "none")
            window.update_live_option_state()

            set_map_type("channel")
            self.assertEqual(window.current_combo_value(window.live_point_labels_combo), "all")
            set_map_type("dominant")
            self.assertEqual(window.current_combo_value(window.live_point_labels_combo), "none")

            window.reset_live_option_memory()
            set_map_type("signal")
            self.assertEqual(window.current_combo_value(window.live_band_combo), "all")
            self.assertEqual(window.current_combo_value(window.live_aggregation_combo), "max")
            self.assertEqual(window.current_combo_value(window.live_interpolation_combo), "rbf")
            self.assertEqual(window.current_combo_value(window.live_color_scale_combo), "fixed")
            self.assertEqual(window.live_smoothing_spin.value(), 3.0)
            self.assertEqual(window.current_live_max_distance_px(), 180)
            self.assertFalse(window.live_usable_check.isChecked())
            set_map_type("channel")
            self.assertEqual(window.current_combo_value(window.live_point_labels_combo), "auto")
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

    def test_metadata_warning_accepts_expected_channel_ranges_and_bands(self):
        bssid = "70:4f:57:aa:bb:10"
        rows = [
            build_row("p1", "MAIN", bssid, -55, 1),
            build_row("p2", "MAIN", bssid, -57, 6),
            build_row("p3", "MAIN", bssid, -59, 36),
        ]
        groups = [
            build_manual_ap_group(
                "corridor",
                [bssid],
                metadata={"expected_channels": "1-6, 36", "expected_bands": "2.4 GHz / 5 GHz"},
            )
        ]

        warnings = build_ap_metadata_warnings(rows, groups)

        self.assertEqual(warnings, [])

    def test_metadata_warning_detects_unexpected_band_and_ignores_test_groups(self):
        bssid = "70:4f:57:aa:bb:10"
        test_bssid = "80:11:22:33:44:10"
        rows = [
            build_row("p1", "MAIN", bssid, -55, 36),
            build_row("p1", "MAIN", test_bssid, -30, 36),
        ]
        groups = [
            build_manual_ap_group(
                "corridor",
                [bssid],
                metadata={"expected_bands": "2.4"},
            ),
            build_manual_ap_group(
                "test-ap",
                [test_bssid],
                role=AP_ROLE_TEST,
                metadata={"expected_bands": "2.4"},
            ),
        ]

        warnings = build_ap_metadata_warnings(rows, groups)

        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["group_id"], "corridor")
        self.assertEqual(warnings[0]["unexpected_bands"], ["5"])


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


def build_raw_row(point_id, ssid, bssid, signal_dbm, channel):
    return {
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
