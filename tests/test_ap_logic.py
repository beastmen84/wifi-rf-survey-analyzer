from tests._common import *

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

    def test_default_manual_groups_prefill_consistent_scan_metadata(self):
        first_bssid = "70:4f:57:aa:bb:10"
        second_bssid = "70:4f:57:aa:bb:11"
        first_row = build_row("p1", "MAIN", first_bssid, -50, 1)
        second_row = build_row("p1", "GUEST", second_bssid, -55, 1)
        for row in (first_row, second_row):
            row["vendor"] = "Acme"
            row["model"] = "AX-1"

        groups = build_default_manual_groups([first_row, second_row])

        self.assertEqual(groups[0]["metadata"]["vendor"], "Acme")
        self.assertEqual(groups[0]["metadata"]["model"], "AX-1")

    def test_default_manual_groups_skip_ambiguous_scan_metadata(self):
        first_row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 1)
        second_row = build_row("p1", "GUEST", "70:4f:57:aa:bb:11", -55, 1)
        first_row["vendor"] = "Acme"
        second_row["vendor"] = "Other"

        groups = build_default_manual_groups([first_row, second_row])

        self.assertNotIn("metadata", groups[0])

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

    def test_ap_group_conflicts_use_explicit_6ghz_band_for_low_channels(self):
        bssid_24 = "70:4f:57:aa:bb:10"
        bssid_6a = "70:4f:57:aa:bb:11"
        bssid_6b = "70:4f:57:aa:bb:12"
        groups = [build_manual_ap_group("tri-band-ap", [bssid_24, bssid_6a, bssid_6b])]
        rows = [
            build_row("p1", "MAIN", bssid_24, -50, 1),
            build_row("p1", "MAIN", bssid_6a, -51, 1, band="6"),
            build_row("p1", "MAIN", bssid_6b, -52, 9, band="6"),
        ]

        conflicts = build_ap_group_conflicts(rows, groups)

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["band"], "6")
        self.assertEqual(conflicts[0]["channels"], ["1", "9"])

    def test_ap_group_conflicts_ignore_same_bssid_set_channel_changes(self):
        bssids = ["70:4f:57:aa:bb:10", "72:4f:57:aa:bb:10"]
        groups = [build_manual_ap_group("office-ap", bssids)]
        rows = [
            build_row("p1", "MAIN", bssids[0], -50, 36),
            build_row("p1", "GUEST", bssids[1], -51, 36),
            build_row("p2", "MAIN", bssids[0], -45, 40),
            build_row("p2", "GUEST", bssids[1], -46, 40),
        ]

        conflicts = build_ap_group_conflicts(rows, groups)

        self.assertEqual(conflicts, [])

    def test_ap_channel_changes_classify_clean_and_ambiguous_sequences(self):
        bssid = "70:4f:57:aa:bb:10"
        groups = [build_manual_ap_group("office-ap", [bssid])]

        clean_changes = build_ap_channel_changes([
            build_row("p1", "MAIN", bssid, -50, 36),
            build_row("p2", "MAIN", bssid, -50, 40),
            build_row("p3", "MAIN", bssid, -50, 40),
        ], groups)
        self.assertEqual(len(clean_changes), 1)
        self.assertEqual(clean_changes[0]["status"], AP_CHANNEL_CHANGE_CLEAN)
        self.assertEqual(clean_changes[0]["current_channel"], "40")
        self.assertEqual(clean_changes[0]["previous_channels"], ["36"])

        ambiguous_changes = build_ap_channel_changes([
            build_row("p1", "MAIN", bssid, -50, 36),
            build_row("p2", "MAIN", bssid, -50, 40),
            build_row("p3", "MAIN", bssid, -50, 36),
        ], groups)
        self.assertEqual(len(ambiguous_changes), 1)
        self.assertEqual(ambiguous_changes[0]["status"], AP_CHANNEL_CHANGE_AMBIGUOUS)


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

    def test_interference_uses_final_channel_for_clean_ap_channel_change(self):
        serving_bssid = "70:4f:57:aa:bb:10"
        neighbor_bssid = "80:11:22:33:44:10"
        rows = [
            build_row("p1", "MAIN", serving_bssid, -50, 36, band="5"),
            build_row("p1", "NEIGHBOR", neighbor_bssid, -55, 36, band="5"),
            build_row("p2", "MAIN", serving_bssid, -50, 44, band="5"),
            build_row("p2", "NEIGHBOR", neighbor_bssid, -55, 36, band="5"),
        ]
        groups = [
            build_manual_ap_group("serving-ap", [serving_bssid]),
            build_manual_ap_group("neighbor-ap", [neighbor_bssid]),
        ]
        group_map = build_bssid_to_manual_group_map(groups)

        risk_df = calculate_interference_points(
            rows_to_dataframe(rows),
            "MAIN",
            "5",
            mode="all",
            include_details=True,
            ap_group_map=tuple(sorted(group_map.items())),
        )

        p1 = risk_df[risk_df["timestamp"] == "p1"].iloc[0]
        self.assertEqual(p1["serving_channel"], 44)
        self.assertEqual(p1["serving_channel_original"], 36)
        self.assertTrue(p1["serving_channel_adjusted_for_change"])
        self.assertEqual(p1["serving_channel_change_status"], AP_CHANNEL_CHANGE_CLEAN)
        self.assertEqual(p1["serving_channel_change_previous_channels"], "36")
        self.assertEqual(p1["risk"], 0)

    def test_interference_keeps_original_channels_for_ambiguous_channel_changes(self):
        serving_bssid = "70:4f:57:aa:bb:10"
        neighbor_bssid = "80:11:22:33:44:10"
        rows = [
            build_row("p1", "MAIN", serving_bssid, -50, 36, band="5"),
            build_row("p1", "NEIGHBOR", neighbor_bssid, -55, 36, band="5"),
            build_row("p2", "MAIN", serving_bssid, -50, 44, band="5"),
            build_row("p2", "NEIGHBOR", neighbor_bssid, -55, 36, band="5"),
            build_row("p3", "MAIN", serving_bssid, -50, 36, band="5"),
            build_row("p3", "NEIGHBOR", neighbor_bssid, -55, 36, band="5"),
        ]
        groups = [
            build_manual_ap_group("serving-ap", [serving_bssid]),
            build_manual_ap_group("neighbor-ap", [neighbor_bssid]),
        ]
        group_map = build_bssid_to_manual_group_map(groups)

        risk_df = calculate_interference_points(
            rows_to_dataframe(rows),
            "MAIN",
            "5",
            mode="all",
            include_details=True,
            ap_group_map=tuple(sorted(group_map.items())),
        )

        p1 = risk_df[risk_df["timestamp"] == "p1"].iloc[0]
        self.assertEqual(p1["serving_channel"], 36)
        self.assertFalse(p1["serving_channel_adjusted_for_change"])
        self.assertEqual(p1["risk"], 100)

    def test_channel_map_uses_final_channel_for_clean_ap_channel_change(self):
        bssid = "70:4f:57:aa:bb:10"
        groups = [build_manual_ap_group("office-ap", [bssid])]
        group_map = build_bssid_to_manual_group_map(groups)
        rows = [
            build_row("p1", "MAIN", bssid, -50, 36, band="5"),
            build_row("p2", "MAIN", bssid, -49, 44, band="5"),
        ]

        channel_df = get_channel_map_points(
            rows_to_dataframe(rows),
            "MAIN",
            "5",
            ap_group_map=tuple(sorted(group_map.items())),
        )

        p1 = channel_df[channel_df["timestamp"] == "p1"].iloc[0]
        p2 = channel_df[channel_df["timestamp"] == "p2"].iloc[0]
        self.assertEqual(p1["channel"], 44)
        self.assertEqual(p1["channel_original"], 36)
        self.assertTrue(p1["channel_adjusted_for_change"])
        self.assertEqual(p1["channel_change_status"], AP_CHANNEL_CHANGE_CLEAN)
        self.assertEqual(p2["channel"], 44)
        self.assertFalse(p2["channel_adjusted_for_change"])

    def test_24ghz_interference_overlap_weights_are_ordered_by_channel_distance(self):
        self.assertEqual(channel_overlap_weight(1, 1, "2.4"), 1.0)
        self.assertEqual(channel_overlap_weight(1, 2, "2.4"), 0.8)
        self.assertEqual(channel_overlap_weight(1, 3, "2.4"), 0.6)
        self.assertEqual(channel_overlap_weight(1, 4, "2.4"), 0.35)
        self.assertEqual(channel_overlap_weight(1, 5, "2.4"), 0.15)
        self.assertEqual(channel_overlap_weight(1, 6, "2.4"), 0)

    def test_5ghz_channel_width_overlap_uses_frequency_ranges_when_width_is_known(self):
        self.assertEqual(channel_width_overlap_weight(36, 44, 80, 20), 1.0)
        self.assertEqual(channel_width_overlap_weight(36, 52, 80, 20), 0.0)
        self.assertIsNone(channel_width_overlap_weight(36, 44, "", 20))

    def test_6ghz_channel_width_overlap_uses_frequency_ranges_when_width_is_known(self):
        self.assertEqual(channel_width_overlap_weight(1, 9, 80, 20, band="6"), 1.0)
        self.assertEqual(channel_width_overlap_weight(1, 17, 80, 20, band="6"), 0.0)
        self.assertEqual(channel_overlap_weight(1, 9, "6", 80, 20), 1.0)

    def test_signal_interference_weight_thresholds(self):
        self.assertEqual(signal_interference_weight(-60), 1.0)
        self.assertEqual(signal_interference_weight(-67), 0.7)
        self.assertEqual(signal_interference_weight(-75), 0.4)
        self.assertEqual(signal_interference_weight(-85), 0.15)
        self.assertEqual(signal_interference_weight(-90), 0.05)
        self.assertEqual(signal_interference_weight(-91), 0)

    def test_interference_5ghz_uses_channel_width_overlap_and_confidence(self):
        serving_bssid = "70:4f:57:aa:bb:10"
        overlapping_bssid = "80:11:22:33:44:10"
        non_overlapping_bssid = "90:11:22:33:44:10"
        serving = build_row("p1", "MAIN", serving_bssid, -50, 36)
        serving["channel_width_mhz"] = "80"
        serving["scan_confidence"] = "0.8"
        overlapping = build_row("p1", "NEIGHBOR", overlapping_bssid, -60, 44)
        overlapping["channel_width_mhz"] = "20"
        overlapping["scan_confidence"] = "0.3"
        non_overlapping = build_row("p1", "NEIGHBOR", non_overlapping_bssid, -40, 52)
        non_overlapping["channel_width_mhz"] = "20"
        non_overlapping["scan_confidence"] = "1.0"

        risk_df = calculate_interference_points(
            rows_to_dataframe([serving, overlapping, non_overlapping]),
            "MAIN",
            "5",
            mode="all",
            include_details=True,
        )

        self.assertEqual(len(risk_df), 1)
        row = risk_df.iloc[0]
        self.assertEqual(row["risk"], 100)
        self.assertEqual(row["scan_confidence"], 0.3)
        self.assertEqual(row["interferer_count"], 1)
        self.assertEqual(row["strongest_interferer_bssid"], overlapping_bssid)
        self.assertNotIn(non_overlapping_bssid, row["interfering_bssids"])

    def test_interference_6ghz_uses_explicit_band_for_ambiguous_channels(self):
        serving_bssid = "70:4f:57:aa:bb:10"
        overlapping_bssid = "80:11:22:33:44:10"
        legacy_24_bssid = "90:11:22:33:44:10"
        serving = build_row("p1", "MAIN", serving_bssid, -50, 1, band="6")
        serving["channel_width_mhz"] = "80"
        overlapping = build_row("p1", "NEIGHBOR", overlapping_bssid, -60, 9, band="6")
        overlapping["channel_width_mhz"] = "20"
        legacy_24 = build_row("p1", "NEIGHBOR", legacy_24_bssid, -30, 1)

        risk_df = calculate_interference_points(
            rows_to_dataframe([serving, overlapping, legacy_24]),
            "MAIN",
            "6",
            mode="all",
            include_details=True,
        )

        self.assertEqual(len(risk_df), 1)
        row = risk_df.iloc[0]
        self.assertEqual(row["risk"], 100)
        self.assertEqual(row["serving_band"], "6")
        self.assertEqual(row["strongest_interferer_band"], "6")
        self.assertEqual(row["strongest_interferer_bssid"], overlapping_bssid)
        self.assertNotIn(legacy_24_bssid, row["interfering_bssids"])

    def test_filter_by_band_uses_explicit_6ghz_band_for_ambiguous_channels(self):
        row_24 = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 5)
        row_6 = build_row("p2", "MAIN", "80:11:22:33:44:10", -55, 5, band="6")

        filtered = filter_by_band(rows_to_dataframe([row_24, row_6]), "6")

        self.assertEqual(filtered["bssid"].tolist(), ["80:11:22:33:44:10"])

    def test_interference_data_quality_counts_rows_with_channel_width_details(self):
        risk_df = rows_to_dataframe([
            {"serving_channel_width_mhz": "20", "strongest_interferer_channel_width_mhz": ""},
            {"serving_channel_width_mhz": "", "strongest_interferer_channel_width_mhz": ""},
            {"serving_channel_width_mhz": "", "strongest_interferer_channel_width_mhz": "40"},
        ])

        quality = get_interference_data_quality(risk_df)

        self.assertEqual(quality, {"available": 2, "total": 3, "percent": 67})



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



class ApMetadataTests(unittest.TestCase):
    def test_expected_channel_parser_handles_ranges_reversed_ranges_and_text(self):
        self.assertEqual(
            parse_expected_channels("1-3, 11; ch36 / 40-38"),
            {"1", "2", "3", "11", "36", "38", "39", "40"},
        )

    def test_expected_band_parser_accepts_common_wifi_band_labels_including_6ghz_metadata(self):
        self.assertEqual(parse_expected_bands("2.4 GHz / 5GHz; 6g"), {"2.4", "5", "6"})
        self.assertEqual(parse_expected_bands("24, 5, 6"), {"2.4", "5", "6"})

    def test_expected_channel_helpers_include_6ghz_channels(self):
        self.assertEqual(EXPECTED_CHANNELS_BY_BAND["6"][:3], ("1", "2", "5"))
        self.assertIn("2", EXPECTED_CHANNELS_BY_BAND["6"])
        self.assertIn("233", EXPECTED_CHANNELS_BY_BAND["6"])
        self.assertEqual(infer_expected_channel_bands("5", {"6"}), ["6"])
        self.assertEqual(infer_expected_channel_bands("149", {"5", "6"}), ["5", "6"])
        self.assertEqual(infer_expected_channel_bands("233", set()), ["6"])

    def test_metadata_channel_helpers_normalize_and_sort_values(self):
        self.assertEqual(normalize_channel("CH 036 / 80 MHz"), "36")
        self.assertEqual(normalize_channel("unknown"), "")
        self.assertEqual(sort_channels({"11", "1", "6"}), ["1", "6", "11"])
        self.assertEqual(sort_channels({"11", "1", "6"}, channel_sort_key=lambda value: -int(value)), ["11", "6", "1"])
        self.assertEqual(sort_bands({"6", "2.4", "5", "unknown"}), ["2.4", "5", "6", "unknown"])

    def test_band_inference_currently_handles_24_and_5ghz_only(self):
        self.assertEqual(infer_band_from_channel("1"), "2.4")
        self.assertEqual(infer_band_from_channel("36"), "5")
        self.assertEqual(infer_band_from_channel("5"), "2.4")
        self.assertEqual(infer_band_from_channel("233"), "")

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

    def test_metadata_warning_uses_explicit_6ghz_band_for_ambiguous_channel(self):
        bssid = "70:4f:57:aa:bb:10"
        rows = [build_row("p1", "MAIN", bssid, -55, 5, band="6")]
        groups = [
            build_manual_ap_group(
                "corridor",
                [bssid],
                metadata={"expected_channels": "5", "expected_bands": "6 GHz"},
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



