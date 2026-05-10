import unittest

from ap_groups import (
    build_bssid_to_manual_group_map,
    build_manual_ap_group,
    resolve_ap_group_key,
)
from ap_metadata_checks import build_ap_metadata_warnings
from heatmap_tools import calculate_interference_points
from quality_engine import QUALITY_MISSING_RELEVANT, evaluate_point_quality
from survey_store import get_survey_point_summaries_from_rows
from ui_scaling import normalize_ui_scale_mode, scale_font, scale_px


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


if __name__ == "__main__":
    unittest.main()
