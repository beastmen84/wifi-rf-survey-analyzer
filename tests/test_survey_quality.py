from tests._common import *

class QualityTests(unittest.TestCase):
    def test_quality_marks_missing_relevant_network(self):
        row = build_row("p1", "OTHER", "70:4f:57:aa:bb:10", -55, 1)
        row["is_relevant"] = "0"

        quality = evaluate_point_quality([row], relevant_ssids={"MAIN", "GUEST"})

        self.assertEqual(quality["p1"]["status"], QUALITY_MISSING_RELEVANT)
        self.assertEqual(quality["p1"]["missing_relevant"], ["guest", "main"])

    def test_quality_accepts_any_observed_relevant_network(self):
        rows = [build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -55, 1)]

        quality = evaluate_point_quality(rows, relevant_ssids={"MAIN", "GUEST"})

        self.assertEqual(quality["p1"]["status"], QUALITY_GOOD)
        self.assertEqual(
            [item["ssid"] for item in quality["p1"]["breakdown"]],
            ["main"],
        )

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

    def test_quality_checks_present_relevant_network_before_missing_peer_ssid(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -52, 1)
        row["scan_confidence"] = "0.1"

        quality = evaluate_point_quality([row], relevant_ssids={"MAIN", "GUEST"})

        self.assertEqual(quality["p1"]["status"], QUALITY_LOW_CONFIDENCE)
        self.assertEqual(quality["p1"]["breakdown"][0]["ssid"], "main")

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

    def test_effective_relevant_ssids_prefers_user_selection_and_falls_back_to_row_flags(self):
        flagged_row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -52, 1)
        unflagged_row = build_row("p1", "GUEST", "80:11:22:33:44:10", -60, 1)
        unflagged_row["is_relevant"] = "0"

        self.assertEqual(
            get_effective_relevant_ssids(FakeQualityApp([flagged_row, unflagged_row])),
            {"main"},
        )
        self.assertEqual(
            get_effective_relevant_ssids(
                FakeQualityApp([flagged_row, unflagged_row], relevant_ssids={"GUEST"})
            ),
            {"guest"},
        )

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

    def test_build_ap_position_quality_by_point_scopes_to_relevant_ssids_and_ignores_test_aps(self):
        internal_bssid = "70:4f:57:aa:bb:10"
        guest_bssid = "80:11:22:33:44:10"
        test_bssid = "90:11:22:33:44:10"
        main_row = build_row("p1", "MAIN", internal_bssid, -50, 1)
        main_row["x"] = "0"
        main_row["y"] = "0"
        guest_row = build_row("p1", "GUEST", guest_bssid, -30, 1)
        guest_row["x"] = "0"
        guest_row["y"] = "0"
        guest_row["is_relevant"] = "0"
        test_row = build_row("p1", "MAIN", test_bssid, -20, 1)
        test_row["x"] = "0"
        test_row["y"] = "0"
        groups = [
            build_manual_ap_group("main-ap", [internal_bssid], position={"x": 30, "y": 0}),
            build_manual_ap_group("guest-ap", [guest_bssid], position={"x": 1, "y": 0}),
            build_manual_ap_group("test-ap", [test_bssid], position={"x": 1, "y": 0}, role=AP_ROLE_TEST),
        ]
        app = FakeQualityApp([main_row, guest_row, test_row], groups, relevant_ssids={"MAIN"})
        app.px_per_meter = 1

        position_by_point = build_ap_position_quality_by_point(app, groups)

        self.assertEqual(set(position_by_point), {"p1"})
        self.assertEqual(position_by_point["p1"]["dominant_ap_group"], "main-ap")
        self.assertEqual(position_by_point["p1"]["warnings"], [AP_POSITION_STRONG_FAR])

    def test_dashboard_rows_merge_quality_and_ap_position_issues(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 1)
        app = FakeQualityApp([row], relevant_ssids={"MAIN"})
        point_summaries = get_survey_point_summaries_from_rows([row])
        quality_by_point_id = {
            "p1": {
                "status": QUALITY_LOW_CONFIDENCE,
                "breakdown": [
                    {"ssid": "main", "status": QUALITY_LOW_CONFIDENCE, "message": "low_confidence"}
                ],
            }
        }
        ap_position_by_point = {
            "p1": {
                "dominant_ap_group": "main-ap",
                "warnings": [AP_POSITION_STRONG_FAR],
            }
        }

        rows = build_dashboard_rows(app, point_summaries, quality_by_point_id, ap_position_by_point)

        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["needs_review"])
        self.assertEqual(rows[0]["severity"], "warning")
        self.assertEqual(rows[0]["ap_position_warning_count"], 1)
        self.assertIn("main: low_confidence", rows[0]["issue"])
        self.assertIn("main-ap", rows[0]["issue"])

    def test_quality_summary_formats_metadata_warning_labels(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -55, 1)
        app = FakeQualityApp([row], relevant_ssids={"MAIN"})
        warnings = [
            {"group_id": "ap-1", "unexpected_channels": ["36"], "expected_channels": ["1"]},
            {"group_id": "ap-2", "unexpected_bands": ["5"], "expected_bands": ["2.4"]},
            {"group_id": "ap-3", "unexpected_channels": ["11"], "expected_channels": ["6"]},
            {"group_id": "ap-4", "unexpected_channels": ["1"], "expected_channels": ["11"]},
        ]

        summary = build_summary(
            app,
            [{"status": QUALITY_GOOD, "needs_review": False, "ap_position_warning_count": 0}],
            warnings,
            [],
        )

        self.assertEqual(summary["ap_metadata_warnings"], 4)
        self.assertIn("ap-1", summary["ap_metadata_warning_labels"])
        self.assertIn("+1", summary["ap_metadata_warning_labels"])

    def test_quality_metadata_recommendation_has_direct_actions_without_duplicate_context(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -55, 36)
        app = FakeQualityApp([row], relevant_ssids={"MAIN"})
        warnings = [
            {"group_id": "ap-1", "unexpected_channels": ["36"], "expected_channels": ["1"]},
        ]

        summary = build_summary(
            app,
            [{"status": QUALITY_GOOD, "needs_review": False, "ap_position_warning_count": 0}],
            warnings,
            [],
        )

        metadata_recommendation = next(
            recommendation
            for recommendation in summary["recommendations"]
            if recommendation["title"] == "quality_dashboard_fix_ap_metadata_title"
        )
        self.assertEqual(summary["ap_metadata_warning_items"][0]["band"], "5")
        self.assertTrue(any(action["kind"] == "ap_metadata" for action in metadata_recommendation["actions"]))
        self.assertTrue(any(action.get("map_type") == "channel" for action in metadata_recommendation["actions"]))
        self.assertEqual(len(summary["context_lines"]), 1)
        self.assertNotIn("ap-1", summary["context_lines"][0])

    def test_quality_recommends_channel_change_model_review(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -55, 36)
        app = FakeQualityApp([row], relevant_ssids={"MAIN"})
        channel_changes = [
            {
                "group_id": "ap-1",
                "band": "5",
                "status": AP_CHANNEL_CHANGE_CLEAN,
                "channels": ["36", "40"],
                "current_channel": "40",
            }
        ]

        summary = build_summary(
            app,
            [{"status": QUALITY_GOOD, "needs_review": False, "ap_position_warning_count": 0}],
            [],
            [],
            channel_changes,
        )

        self.assertEqual(summary["channel_change_count"], 1)
        self.assertEqual(summary["clean_channel_changes"], 1)
        self.assertEqual(summary["ambiguous_channel_changes"], 0)
        self.assertIn("ap-1", summary["channel_change_labels"])
        self.assertTrue(any(
            recommendation["title"] == "quality_dashboard_fix_channel_change_clean_title"
            for recommendation in summary["recommendations"]
        ))

    def test_quality_summary_separates_scan_review_from_ap_setup_warnings(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -55, 1)
        app = FakeQualityApp([row], relevant_ssids={"MAIN"})

        summary = build_summary(
            app,
            [
                {"status": QUALITY_SPARSE_DATA, "needs_review": True, "ap_position_warning_count": 0},
                {"status": QUALITY_GOOD, "needs_review": True, "ap_position_warning_count": 1},
            ],
            [],
            [],
        )

        self.assertEqual(summary["review_points"], 2)
        self.assertEqual(summary["scan_review_points"], 1)
        self.assertEqual(summary["sparse_data"], 1)
        self.assertEqual(summary["ap_position_warnings"], 1)
        self.assertEqual(summary["recommendations"][0]["title"], "quality_dashboard_fix_sparse_title")
        self.assertEqual(quality_status_text_keys(summary)[0], "quality_dashboard_status_review_title")

    def test_quality_status_uses_setup_message_when_only_ap_diagnostics_are_open(self):
        summary = {
            "total_points": 12,
            "review_points": 3,
            "scan_review_points": 0,
            "ap_position_warnings": 3,
            "ap_metadata_warnings": 0,
            "ap_missing_positions": 0,
        }

        self.assertEqual(quality_status_text_keys(summary)[0], "quality_dashboard_status_setup_title")


class SurveyPointSummaryTests(unittest.TestCase):
    def test_best_signal_prefers_relevant_networks_when_available(self):
        relevant_row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -68, 1)
        external_row = build_row("p1", "EXTERNAL", "80:11:22:33:44:10", -42, 6)
        external_row["is_relevant"] = "0"

        summaries = get_survey_point_summaries_from_rows([external_row, relevant_row])

        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["best_signal_dbm"], -68)
        self.assertEqual(summaries[0]["signal_scope"], "relevant")



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
                        "frequency_mhz": "2437",
                        "security": "WPA2-Personal / CCMP",
                        "auth": "WPA2-Personal",
                        "encryption": "CCMP",
                        "pmf": "Disabled",
                        "country_code": "IT",
                        "spatial_streams": "2",
                        "stations": "4",
                        "channel_utilization": "18%",
                        "wifi_modes": "ax/n",
                        "amendments": "d/e/h/i/k/v",
                        "vendor": "Acme",
                        "model": "AX-1",
                        "ap_name": "office-ap",
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
                                "frequency_mhz": "2437",
                                "security": "WPA2-Personal / CCMP",
                                "auth": "WPA2-Personal",
                                "encryption": "CCMP",
                                "pmf": "Disabled",
                                "country_code": "IT",
                                "spatial_streams": "2",
                                "stations": "4",
                                "channel_utilization": "18%",
                                "wifi_modes": "ax/n",
                                "amendments": "d/e/h/i/k/v",
                                "vendor": "Acme",
                                "model": "AX-1",
                                "ap_name": "office-ap",
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
                                "frequency_mhz": "2437",
                                "security": "WPA2-Personal / CCMP",
                                "auth": "WPA2-Personal",
                                "encryption": "CCMP",
                                "pmf": "Disabled",
                                "country_code": "IT",
                                "spatial_streams": "2",
                                "stations": "4",
                                "channel_utilization": "18%",
                                "wifi_modes": "ax/n",
                                "amendments": "d/e/h/i/k/v",
                                "vendor": "Acme",
                                "model": "AX-1",
                                "ap_name": "office-ap",
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
            self.assertEqual(loaded.rows[0]["frequency_mhz"], "2437")
            self.assertEqual(loaded.rows[0]["pmf"], "Disabled")
            self.assertEqual(loaded.rows[0]["channel_utilization"], "18%")
            self.assertEqual(loaded.rows[0]["wifi_modes"], "ax/n")
            self.assertEqual(loaded.rows[0]["vendor"], "Acme")
            self.assertEqual(loaded.rows[0]["model"], "AX-1")
            self.assertEqual(loaded.rows[0]["ap_name"], "office-ap")
            self.assertEqual(len(loaded.raw_scan_rows), 2)
            self.assertEqual(loaded.raw_scan_rows[0]["auth"], "WPA2-Personal")
            self.assertEqual(loaded.raw_scan_rows[0]["encryption"], "CCMP")
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

    def test_opening_custom_scan_sidecar_as_survey_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_scan_file = os.path.join(temp_dir, "custom_raw.scan")
            with open(raw_scan_file, "w", newline="", encoding="utf-8") as f:
                f.write("point_id,scan_attempt,timestamp,x,y,ssid,bssid,signal_percent,signal_dbm,channel,channel_width_mhz,radio,backend\n")

            with self.assertRaises(SurveyFormatError) as error:
                SurveySession(raw_scan_file)

            self.assertEqual(str(error.exception), "raw_scan_file")

    def test_delete_point_removes_aggregate_rows_and_linked_raw_rows(self):
        session = SurveySession()
        main_row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 1)
        guest_row = build_row("p1", "GUEST", "70:4f:57:aa:bb:11", -55, 1)
        other_row = build_row("p2", "MAIN", "90:11:22:33:44:10", -60, 6)
        session.rows = [main_row, guest_row, other_row]
        session.raw_scan_rows = [
            build_raw_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 1),
            build_raw_row("p1", "GUEST", "70:4f:57:aa:bb:11", -55, 1),
            build_raw_row("p2", "MAIN", "90:11:22:33:44:10", -60, 6),
        ]

        removed_rows = session.delete_point("p1", 10, 20)

        self.assertEqual(removed_rows, 2)
        self.assertEqual([row["point_id"] for row in session.rows], ["p2"])
        self.assertEqual([row["point_id"] for row in session.raw_scan_rows], ["p2"])
        self.assertTrue(session.dirty)

    def test_delete_point_without_match_leaves_session_clean(self):
        session = SurveySession()
        session.rows = [build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 1)]
        session.raw_scan_rows = [build_raw_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 1)]
        session.dirty = False

        removed_rows = session.delete_point("missing", 10, 20)

        self.assertEqual(removed_rows, 0)
        self.assertEqual(len(session.rows), 1)
        self.assertEqual(len(session.raw_scan_rows), 1)
        self.assertFalse(session.dirty)

    def test_ap_aliases_merge_legacy_aliases_with_group_aliases(self):
        session = SurveySession()
        session.set_ap_aliases({
            "legacy-key": "Legacy AP",
            "empty-key": " ",
            "office-ap": "Old group alias",
        })
        session.set_ap_groups([
            build_manual_ap_group(
                "office-ap",
                ["70:4f:57:aa:bb:10"],
                alias="Office AP",
            )
        ])

        aliases = session.get_ap_aliases()

        self.assertEqual(aliases["legacy-key"], "Legacy AP")
        self.assertEqual(aliases["office-ap"], "Office AP")
        self.assertNotIn("empty-key", aliases)

    def test_missing_raw_sidecar_is_allowed_but_malformed_sidecar_is_rejected(self):
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
            raw_scan_file = build_raw_scan_file_path(survey_file, session.metadata)

            os.remove(raw_scan_file)
            loaded = SurveySession(survey_file)
            self.assertEqual(loaded.raw_scan_rows, [])

            with open(raw_scan_file, "w", newline="", encoding="utf-8") as f:
                f.write("point_id,ssid\n")

            with self.assertRaises(SurveyFormatError) as error:
                SurveySession(survey_file)

            self.assertEqual(str(error.exception), "invalid_raw_scan_format")

    def test_invalid_survey_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            survey_file = os.path.join(temp_dir, "office.csv")
            with open(survey_file, "w", newline="", encoding="utf-8") as f:
                f.write("# app=wifi_heatmap\n")
                f.write("# schema_version=2\n")
                f.write(",".join(field for field in SURVEY_FIELDNAMES if field != "bssid"))
                f.write("\n")

            with self.assertRaises(SurveyFormatError) as error:
                SurveySession(survey_file)

            self.assertEqual(str(error.exception), "invalid_survey_format")



class HeatmapMathTests(unittest.TestCase):
    def test_scan_confidence_values_default_clip_and_coerce(self):
        df = rows_to_dataframe([
            {"scan_confidence": "1.5"},
            {"scan_confidence": "0.01"},
            {"scan_confidence": "bad"},
        ])

        values = get_scan_confidence_values(df, default=0.75)

        self.assertEqual(values.tolist(), [1.0, 0.05, 0.75])
        self.assertEqual(get_scan_confidence_values([{}, {}], default=0.8).tolist(), [0.8, 0.8])

    def test_normalize_confidence_array_validates_length_and_finite_values(self):
        self.assertIsNone(normalize_confidence_array(None, 2))
        self.assertIsNone(normalize_confidence_array([0.5], 2))

        values = normalize_confidence_array([float("nan"), 0.01, 2.0], 3)

        self.assertEqual(values.tolist(), [1.0, 0.05, 1.0])

    def test_confidence_rbf_smoothing_increases_for_low_confidence_points(self):
        smoothing = get_confidence_rbf_smoothing([1.0, 0.5, 0.05], 3, base_smoothing=4.0)

        self.assertAlmostEqual(smoothing[0], 4.0)
        self.assertGreater(smoothing[1], smoothing[0])
        self.assertGreater(smoothing[2], smoothing[1])
        self.assertEqual(get_confidence_rbf_smoothing([1.0], 2, base_smoothing=4.0), 4.0)

    def test_smooth_heatmap_grid_preserves_nan_voids_without_zero_bleed(self):
        grid = np.full((5, 5), np.nan)
        grid[2, 2] = -50

        smoothed = smooth_heatmap_grid(grid, sigma=1.0)

        self.assertTrue(np.isfinite(smoothed[2, 2]))
        self.assertAlmostEqual(smoothed[2, 2], -50.0, places=5)
        self.assertTrue(np.isnan(smooth_heatmap_grid(np.full((2, 2), np.nan), sigma=1.0)).all())

    def test_distance_mask_and_alpha_respect_radius_fade_and_confidence(self):
        grid_x, grid_y = np.meshgrid(np.array([0.0, 5.0, 10.0, 15.0]), np.array([0.0]), indexing="ij")
        grid_z = np.arange(4, dtype=float).reshape(4, 1)

        masked = apply_distance_mask(grid_z, grid_x, grid_y, np.array([0.0]), np.array([0.0]), max_distance_px=10)
        alpha = get_distance_alpha(
            grid_x,
            grid_y,
            np.array([0.0]),
            np.array([0.0]),
            max_distance_px=10,
            fade_ratio=0.5,
            point_confidence=[0.5],
            min_confidence_alpha=0.4,
        )

        self.assertTrue(np.isfinite(masked[2, 0]))
        self.assertTrue(np.isnan(masked[3, 0]))
        self.assertAlmostEqual(alpha[0, 0], 0.7)
        self.assertAlmostEqual(alpha[1, 0], 0.7)
        self.assertAlmostEqual(alpha[2, 0], 0.0)
        self.assertAlmostEqual(alpha[3, 0], 0.0)

    def test_apply_signal_threshold_masks_only_weak_values(self):
        grid = np.array([[-72.0, -70.0], [-65.0, np.nan]])

        thresholded = apply_signal_threshold(grid, min_signal_dbm=-70)

        self.assertTrue(np.isnan(thresholded[0, 0]))
        self.assertEqual(thresholded[0, 1], -70.0)
        self.assertEqual(thresholded[1, 0], -65.0)
        self.assertTrue(np.isnan(thresholded[1, 1]))

    def test_interpolation_falls_back_to_nearest_for_sparse_points(self):
        grid_x, grid_y = np.meshgrid(np.array([0.0, 10.0]), np.array([0.0, 10.0]), indexing="ij")

        grid = interpolate_signal_grid(
            np.array([0.0, 10.0]),
            np.array([0.0, 10.0]),
            np.array([-50.0, -70.0]),
            grid_x,
            grid_y,
            method="rbf",
        )

        self.assertEqual(grid.shape, grid_x.shape)
        self.assertEqual(grid[0, 0], -50.0)
        self.assertEqual(grid[1, 1], -70.0)



