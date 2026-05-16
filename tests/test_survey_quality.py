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

    def test_quality_treats_explicit_empty_point_scope_as_no_relevant_expected(self):
        row = build_row("p1", "LOCAL", "70:4f:57:aa:bb:10", -82, 1)
        row["scan_confidence"] = "0.1"

        quality = evaluate_point_quality(
            [row],
            relevant_ssids={"LOCAL"},
            relevant_ssids_by_point={"p1": set()},
        )

        self.assertEqual(quality["p1"]["status"], QUALITY_GOOD)
        self.assertEqual(quality["p1"]["breakdown"], [])
        self.assertFalse(quality["p1"]["scanner_details"]["has_issue"])

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

    def test_scanner_details_flag_netsh_and_missing_width_without_changing_signal_status(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -52, 36, band="5")
        row["channel_width_mhz"] = ""
        raw_rows = []
        for attempt in range(5):
            raw = build_raw_row("p1", "MAIN", "70:4f:57:aa:bb:10", -52, 36, band="5")
            raw["scan_attempt"] = str(attempt + 1)
            raw["channel_width_mhz"] = ""
            raw["backend"] = "netsh"
            raw_rows.append(raw)

        quality = evaluate_point_quality([row], raw_rows, relevant_ssids={"MAIN"})

        self.assertEqual(quality["p1"]["status"], QUALITY_GOOD)
        scanner_details = quality["p1"]["scanner_details"]
        self.assertTrue(scanner_details["has_issue"])
        self.assertEqual(scanner_details["fallback_rows"], 5)
        self.assertEqual(scanner_details["missing_channel_width_rows"], 5)
        self.assertIn(SCANNER_DETAIL_FALLBACK_BACKEND, scanner_details["issue_types"])
        self.assertIn(SCANNER_DETAIL_MISSING_CHANNEL_WIDTH, scanner_details["issue_types"])

    def test_scanner_details_flag_missing_6ghz_frequency(self):
        row = build_row("p1", "MAIN-6", "70:4f:57:aa:bb:10", -52, 5, band="6")
        row["frequency_mhz"] = ""

        scanner_details = evaluate_scanner_details([row], [], relevant_ssids={"MAIN-6"})

        self.assertTrue(scanner_details["has_issue"])
        self.assertEqual(scanner_details["missing_6ghz_frequency_rows"], 1)
        self.assertIn(SCANNER_DETAIL_MISSING_6GHZ_FREQUENCY, scanner_details["issue_types"])

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

    def test_quality_relevant_ssids_by_point_limits_auto_local_scope_to_usable_evidence(self):
        main_bssid = "70:4f:57:aa:bb:10"
        local_bssid = "80:11:22:33:44:10"
        p1_main = build_row("p1", "MAIN", main_bssid, -55, 1)
        p1_local = build_row("p1", "LOCAL", local_bssid, -48, 1)
        p2_main = build_row("p2", "MAIN", main_bssid, -54, 1)
        p2_local = build_row("p2", "LOCAL", local_bssid, -82, 1)
        p2_local["scan_confidence"] = "0.1"
        groups = [
            build_manual_ap_group("main-ap", [main_bssid]),
            build_manual_ap_group(
                "local-ap",
                [local_bssid],
                metadata={"coverage_scope": "local"},
            ),
        ]
        app = FakeQualityApp([p1_main, p1_local, p2_main, p2_local], groups, relevant_ssids={"MAIN", "LOCAL"})

        relevant_by_point = build_quality_relevant_ssids_by_point(app, groups, get_effective_relevant_ssids(app))
        quality = evaluate_point_quality(
            app.session.rows,
            relevant_ssids=get_effective_relevant_ssids(app),
            relevant_ssids_by_point=relevant_by_point,
        )

        self.assertEqual(relevant_by_point["p1"], {"main", "local"})
        self.assertEqual(relevant_by_point["p2"], {"main"})
        self.assertEqual(quality["p2"]["status"], QUALITY_GOOD)
        self.assertEqual(
            format_relevant_ssids(
                app.session.rows,
                "p2",
                relevant_by_point["p2"],
                infer_when_empty=False,
                allow_row_flags=False,
            ),
            "MAIN",
        )
        self.assertEqual(
            format_point_confidence(
                app.session.rows,
                "p2",
                relevant_by_point["p2"],
                infer_when_empty=False,
                allow_row_flags=False,
            ),
            "1.00",
        )

    def test_quality_relevant_ssids_by_point_uses_manual_local_radius(self):
        local_bssid = "80:11:22:33:44:10"
        inside = build_row("p1", "LOCAL", local_bssid, -48, 1)
        inside["x"] = "10"
        inside["y"] = "20"
        outside = build_row("p2", "LOCAL", local_bssid, -45, 1)
        outside["x"] = "200"
        outside["y"] = "20"
        groups = [
            build_manual_ap_group(
                "local-ap",
                [local_bssid],
                position={"x": 10, "y": 20},
                metadata={"coverage_scope": "local", "coverage_radius_m": "5"},
            ),
        ]
        app = FakeQualityApp([inside, outside], groups, relevant_ssids={"LOCAL"})
        app.px_per_meter = 10

        relevant_by_point = build_quality_relevant_ssids_by_point(app, groups, get_effective_relevant_ssids(app))

        self.assertEqual(relevant_by_point["p1"], {"local"})
        self.assertEqual(relevant_by_point["p2"], set())

    def test_ap_position_quality_uses_point_scoped_relevant_ssids(self):
        main_bssid = "70:4f:57:aa:bb:10"
        local_bssid = "80:11:22:33:44:10"
        inside_local = build_row("p1", "LOCAL", local_bssid, -48, 1)
        inside_local["x"] = "10"
        inside_local["y"] = "20"
        outside_main = build_row("p2", "MAIN", main_bssid, -55, 1)
        outside_main["x"] = "200"
        outside_main["y"] = "20"
        outside_local = build_row("p2", "LOCAL", local_bssid, -20, 1)
        outside_local["x"] = "200"
        outside_local["y"] = "20"
        groups = [
            build_manual_ap_group(
                "main-ap",
                [main_bssid],
                position={"x": 200, "y": 20},
            ),
            build_manual_ap_group(
                "local-ap",
                [local_bssid],
                position={"x": 10, "y": 20},
                metadata={"coverage_scope": "local", "coverage_radius_m": "5"},
            ),
        ]
        app = FakeQualityApp(
            [inside_local, outside_main, outside_local],
            groups,
            relevant_ssids={"MAIN", "LOCAL"},
        )
        app.px_per_meter = 10

        relevant_by_point = build_quality_relevant_ssids_by_point(app, groups, get_effective_relevant_ssids(app))
        position_warnings = build_ap_position_quality_by_point(
            app,
            groups,
            relevant_ssids_by_point=relevant_by_point,
        )

        self.assertEqual(relevant_by_point["p2"], {"main"})
        self.assertNotIn("p2", position_warnings)

    def test_ap_position_quality_excludes_local_ap_positions_outside_point_scope(self):
        main_bssid = "70:4f:57:aa:bb:10"
        local_bssid = "80:11:22:33:44:10"
        main_row = build_row("p1", "MAIN", main_bssid, -56, 1)
        main_row["x"] = "80"
        main_row["y"] = "0"
        local_row = build_row("p1", "LOCAL", local_bssid, -42, 1)
        local_row["x"] = "80"
        local_row["y"] = "0"
        groups = [
            build_manual_ap_group(
                "main-ap",
                [main_bssid],
                position={"x": 300, "y": 0},
            ),
            build_manual_ap_group(
                "local-ap",
                [local_bssid],
                position={"x": 0, "y": 0},
                metadata={"coverage_scope": "local", "coverage_radius_m": "5"},
            ),
        ]
        app = FakeQualityApp([main_row, local_row], groups, relevant_ssids={"MAIN", "LOCAL"})
        app.px_per_meter = 10

        relevant_by_point = build_quality_relevant_ssids_by_point(app, groups, get_effective_relevant_ssids(app))
        position_warnings = build_ap_position_quality_by_point(
            app,
            groups,
            relevant_ssids_by_point=relevant_by_point,
        )

        self.assertEqual(relevant_by_point["p1"], {"main"})
        self.assertNotIn("p1", position_warnings)

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
        missing_position_recommendation = next(
            recommendation
            for recommendation in summary["recommendations"]
            if recommendation["title"] == "quality_dashboard_fix_ap_missing_title"
        )
        self.assertEqual(
            missing_position_recommendation["metric_key"],
            "quality_dashboard_metric_ap_missing_positions",
        )
        self.assertEqual(missing_position_recommendation["actions"], [])
        self.assertEqual(
            missing_position_recommendation["dialog_detail"],
            "quality_dashboard_fix_ap_missing_dialog_detail",
        )
        self.assertIn(
            "<b>AP Group:</b>",
            missing_position_recommendation["detail_items"][0]["detail"],
        )
        self.assertNotIn(
            "<b>Label:</b>",
            missing_position_recommendation["detail_items"][0]["detail"],
        )
        self.assertIn(
            "<b>Required Action:</b>",
            missing_position_recommendation["detail_items"][0]["detail"],
        )

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
                    {
                        "ssid": "main",
                        "status": QUALITY_LOW_CONFIDENCE,
                        "message": "low_confidence",
                        "min_confidence": 0.4,
                    }
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
        self.assertIn("<b>MAIN</b>: 40% Confidence Level", rows[0]["issue"])
        self.assertIn("main-ap", rows[0]["issue"])

    def test_dashboard_counts_scanner_detail_findings_as_scan_review(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 36, band="5")
        app = FakeQualityApp([row], relevant_ssids={"MAIN"})
        point_summaries = get_survey_point_summaries_from_rows([row])
        quality_by_point_id = {
            "p1": {
                "status": QUALITY_GOOD,
                "breakdown": [{"ssid": "main", "status": QUALITY_GOOD, "message": "good"}],
                "scanner_details": {
                    "has_issue": True,
                    "issue_types": [SCANNER_DETAIL_FALLBACK_BACKEND, SCANNER_DETAIL_MISSING_CHANNEL_WIDTH],
                    "backend_counts": {"netsh": 5},
                    "fallback_rows": 5,
                    "missing_channel_width_rows": 5,
                    "missing_6ghz_frequency_rows": 0,
                    "inspected_rows": 5,
                },
            }
        }

        rows = build_dashboard_rows(app, point_summaries, quality_by_point_id, {})
        summary = build_summary(app, rows, [], [])

        self.assertTrue(rows[0]["needs_review"])
        self.assertEqual(rows[0]["severity"], "warning")
        self.assertEqual(summary["scanner_detail_points"], 1)
        self.assertEqual(summary["scan_review_points"], 1)
        self.assertEqual(summary["scan_ok_points"], 0)
        self.assertEqual(summary["recommendations"][0]["title"], "quality_dashboard_fix_scanner_details_title")
        self.assertEqual(summary["recommendations"][0]["metric_key"], "quality_dashboard_metric_scanner_details")
        self.assertEqual(len(summary["recommendations"][0]["detail_items"]), 1)
        self.assertEqual(
            summary["recommendations"][0]["detail_items"][0]["finding"],
            "Limited Scanner Details",
        )
        self.assertIn(
            "Scanner: <b>NETSH</b> (fallback) | Raw Scan Rows: <b>5</b>",
            summary["recommendations"][0]["detail_items"][0]["detail"],
        )
        self.assertIn(
            "Missing Channel Width: <b>5</b> channel-sensitive scan rows",
            summary["recommendations"][0]["detail_items"][0]["detail"],
        )
        self.assertNotIn(
            "Fallback Scanner Rows",
            summary["recommendations"][0]["detail_items"][0]["detail"],
        )

    def test_detail_dialog_visible_card_limits_are_metric_specific(self):
        scanner_recommendation = {"metric_key": "quality_dashboard_metric_scanner_details"}
        dominant_recommendation = {"metric_key": "quality_dashboard_metric_ap_diagnostic_points"}
        metadata_recommendation = {"metric_key": "quality_dashboard_metric_ap_metadata_warnings"}
        channel_recommendation = {"metric_key": "quality_dashboard_metric_channel_changes"}
        missing_position_recommendation = {"metric_key": "quality_dashboard_metric_ap_missing_positions"}
        memory_recommendation = {"metric_key": "quality_dashboard_metric_ap_memory_applied"}
        items = [{"label": str(index)} for index in range(9)]

        self.assertEqual(recommendation_detail_visible_item_count(scanner_recommendation, items), 4)
        self.assertEqual(recommendation_detail_visible_item_count(scanner_recommendation, items[:2]), 2)
        self.assertEqual(recommendation_detail_visible_item_count(dominant_recommendation, items), 5)
        self.assertEqual(recommendation_detail_visible_item_count(metadata_recommendation, items), 5)
        self.assertEqual(recommendation_detail_visible_item_count(channel_recommendation, items), 4)
        self.assertEqual(recommendation_detail_visible_item_count(missing_position_recommendation, items), 6)
        self.assertEqual(recommendation_detail_visible_item_count(memory_recommendation, items), 5)
        self.assertGreater(
            recommendation_detail_max_height(scanner_recommendation),
            recommendation_detail_max_height(dominant_recommendation),
        )
        self.assertEqual(
            recommendation_detail_scroll_height([120, 122, 124, 126, 128], 6, 4),
            120 + 122 + 124 + 126 + (3 * 6),
        )

    def test_recommendation_details_dialog_fits_visible_cards_exactly(self):
        QApplication.instance() or QApplication([])
        owner = QWidget()
        owner.app = FakeQualityApp([])
        recommendation = {
            "title": "Scanner Details Missing",
            "dialog_detail": "Review these points before reading channel-sensitive maps.",
            "metric_key": "quality_dashboard_metric_scanner_details",
            "detail_items": [
                {
                    "label": f"Point {index + 1}",
                    "finding": "Limited Scanner Details",
                    "detail": (
                        "<b>Scanner:</b> NETSH<br>"
                        "<b>Checked Scan Rows:</b> 40<br>"
                        "<b>Missing Channel Width:</b> 40 channel-sensitive scan rows<br>"
                        "<b>Impact:</b> interference and 6 GHz interpretation may be incomplete"
                    ),
                }
                for index in range(6)
            ],
        }
        dialog = RecommendationDetailsDialog(owner, recommendation)

        try:
            dialog.show()
            QApplication.processEvents()

            content_layout = dialog.detail_scroll.widget().layout()
            row_heights = detail_row_heights_for_width(
                dialog.detail_rows,
                dialog.detail_scroll.viewport().width(),
            )
            expected_visible_height = recommendation_detail_scroll_height(
                row_heights,
                content_layout.spacing(),
                dialog.visible_detail_items,
                content_layout.contentsMargins(),
                dialog.detail_scroll.frameWidth(),
            )

            self.assertEqual(dialog.visible_detail_items, 4)
            self.assertEqual(dialog.detail_scroll.minimumHeight(), expected_visible_height)
            self.assertEqual(dialog.detail_scroll.height(), expected_visible_height)
            self.assertGreater(dialog.detail_scroll.maximumHeight(), expected_visible_height)
            self.assertGreater(dialog.maximumHeight(), dialog.minimumHeight())
            self.assertEqual(
                dialog.detail_scroll.widget().height(),
                dialog.detail_rows[-1].geometry().bottom() + 1,
            )

            first_card_layout = dialog.detail_rows[0].layout().itemAt(0).layout()
            title_label = first_card_layout.itemAt(0).widget()
            finding_label = first_card_layout.itemAt(1).widget()
            detail_label = first_card_layout.itemAt(2).widget()
            self.assertEqual(title_label.height(), title_label.sizeHint().height())
            self.assertLessEqual(finding_label.height(), finding_label.sizeHint().height())
            self.assertLessEqual(detail_label.height(), detail_label.sizeHint().height())
            self.assertEqual(
                dialog.detail_rows[0].height(),
                dialog.detail_rows[0].heightForWidth(dialog.detail_scroll.viewport().width()),
            )

            initial_scroll_height = dialog.detail_scroll.height()
            dialog.resize(dialog.width(), min(dialog.maximumHeight(), dialog.height() + 120))
            QApplication.processEvents()
            self.assertGreater(dialog.detail_scroll.height(), initial_scroll_height)
            self.assertEqual(
                dialog.detail_scroll.widget().height(),
                dialog.detail_rows[-1].geometry().bottom() + 1,
            )
        finally:
            dialog.close()
            owner.deleteLater()

    def test_recommendation_details_dialog_locks_height_when_all_cards_are_visible(self):
        QApplication.instance() or QApplication([])
        owner = QWidget()
        owner.app = FakeQualityApp([])
        recommendation = {
            "title": "APs Without Position",
            "dialog_detail": "Only relevant non-test AP groups without a physical map position are listed.",
            "metric_key": "quality_dashboard_metric_ap_missing_positions",
            "detail_items": [
                {
                    "label": f"AP {index + 1}",
                    "detail": "<b>AP Group:</b> ap-demo<br><b>Required Action:</b> place this AP on the floor plan",
                }
                for index in range(3)
            ],
        }
        dialog = RecommendationDetailsDialog(owner, recommendation)

        try:
            dialog.show()
            QApplication.processEvents()
            self.assertEqual(dialog.detail_scroll.minimumHeight(), dialog.detail_scroll.maximumHeight())
            self.assertEqual(dialog.minimumHeight(), dialog.maximumHeight())
        finally:
            dialog.close()
            owner.deleteLater()

    def test_recommendation_details_dialog_does_not_show_next_card_after_header_reflow(self):
        from translations.it import TRANSLATIONS

        class LocalizedQualityApp(FakeQualityApp):
            theme = "light"

            def tr(self, key, **kwargs):
                text = TRANSLATIONS.get(key, key)
                return text.format(**kwargs) if kwargs else text

        QApplication.instance() or QApplication([])
        owner = QWidget()
        owner.app = LocalizedQualityApp([])
        detail = "<br>".join([
            owner.app.tr(
                "quality_dashboard_scanner_details_scanner",
                backends="NETSH",
                fallback=owner.app.tr("quality_dashboard_scanner_details_fallback_suffix"),
                count=40,
            ),
            owner.app.tr("quality_dashboard_scanner_details_missing_width_detail", count=40),
            owner.app.tr("quality_dashboard_scanner_details_missing_frequency_detail", count=40),
            owner.app.tr("quality_dashboard_scanner_details_impact"),
        ])
        recommendation = {
            "title": owner.app.tr("quality_dashboard_fix_scanner_details_title"),
            "dialog_detail": owner.app.tr("quality_dashboard_fix_scanner_details_dialog_detail"),
            "metric_key": "quality_dashboard_metric_scanner_details",
            "detail_items": [
                {
                    "label": f"Punto {index + 1} (100, 100)",
                    "finding": owner.app.tr("quality_dashboard_scanner_details_finding"),
                    "detail": detail,
                }
                for index in range(8)
            ],
        }
        dialog = RecommendationDetailsDialog(owner, recommendation)

        try:
            dialog.show()
            QApplication.processEvents()

            self.assertEqual(dialog.visible_detail_items, 4)
            self.assertEqual(
                dialog.detail_rows[3].geometry().bottom(),
                dialog.detail_scroll.viewport().height() - 1,
            )
            self.assertGreater(
                dialog.detail_rows[4].geometry().top(),
                dialog.detail_scroll.viewport().height() - 1,
            )
        finally:
            dialog.close()
            owner.deleteLater()

    def test_recommendation_details_dialog_card_fit_for_all_extra_detail_metrics(self):
        QApplication.instance() or QApplication([])
        metrics = [
            ("quality_dashboard_metric_scanner_details", 4, "scanner"),
            ("quality_dashboard_metric_ap_diagnostic_points", 5, "dominant"),
            ("quality_dashboard_metric_ap_metadata_warnings", 5, "metadata"),
            ("quality_dashboard_metric_channel_changes", 4, "channel"),
            ("quality_dashboard_metric_ap_memory_applied", 5, "memory"),
            ("quality_dashboard_metric_ap_missing_positions", 6, "missing_position"),
        ]

        for metric_key, visible_limit, item_kind in metrics:
            for item_count in (max(1, visible_limit - 1), visible_limit, visible_limit + 3):
                with self.subTest(metric_key=metric_key, item_count=item_count):
                    owner = QWidget()
                    owner.app = FakeQualityApp([])
                    recommendation = {
                        "title": metric_key,
                        "dialog_detail": f"Detail header for {metric_key}.",
                        "metric_key": metric_key,
                        "detail_items": [
                            self.build_fake_detail_item(item_kind, index)
                            for index in range(item_count)
                        ],
                    }
                    dialog = RecommendationDetailsDialog(owner, recommendation)

                    try:
                        dialog.show()
                        for _ in range(3):
                            QApplication.processEvents()

                        expected_visible = min(item_count, visible_limit)
                        viewport_bottom = dialog.detail_scroll.viewport().height() - 1
                        last_visible = dialog.detail_rows[expected_visible - 1]

                        self.assertEqual(dialog.visible_detail_items, expected_visible)
                        self.assertEqual(last_visible.geometry().bottom(), viewport_bottom)
                        self.assertEqual(
                            dialog.detail_scroll.widget().height(),
                            dialog.detail_rows[-1].geometry().bottom() + 1,
                        )

                        if item_count > visible_limit:
                            first_hidden = dialog.detail_rows[expected_visible]
                            self.assertGreater(first_hidden.geometry().top(), viewport_bottom)
                            self.assertGreater(dialog.maximumHeight(), dialog.minimumHeight())
                        else:
                            self.assertEqual(dialog.detail_scroll.minimumHeight(), dialog.detail_scroll.maximumHeight())
                            self.assertEqual(dialog.minimumHeight(), dialog.maximumHeight())
                    finally:
                        dialog.close()
                        owner.deleteLater()

    def test_recommendation_details_dialog_header_fits_actual_width(self):
        QApplication.instance() or QApplication([])
        owner = QWidget()
        owner.app = FakeQualityApp([])
        recommendation = {
            "title": "Review AP Memory",
            "dialog_detail": (
                "Use Open AP Group to inspect AP groups with memory state. "
                "Confirm memory-applied groups, or update/keep groups whose "
                "current data differs from AP Memory."
            ),
            "metric_key": "quality_dashboard_metric_ap_memory_applied",
            "detail_items": [self.build_fake_detail_item("memory", 0)],
        }
        dialog = RecommendationDetailsDialog(owner, recommendation)

        try:
            dialog.show()
            for _ in range(3):
                QApplication.processEvents()

            detail = dialog.header_detail_label
            self.assertIsNotNone(detail)
            fitted_height = label_text_height_for_width(detail, detail.width())
            self.assertLess(fitted_height, detail.sizeHint().height())
            self.assertEqual(detail.height(), fitted_height)
        finally:
            dialog.close()
            owner.deleteLater()

    @staticmethod
    def build_fake_detail_item(kind, index):
        label = f"{kind.title()} {index + 1}"
        if kind == "scanner":
            return {
                "label": f"Point {index + 1} ({100 + index}, {200 + index})",
                "finding": "Limited Scanner Details",
                "detail": (
                    "<b>Scanner:</b> NETSH (fallback)<br>"
                    "<b>Checked Scan Rows:</b> 40<br>"
                    "<b>Missing Channel Width:</b> 40 channel-sensitive scan rows<br>"
                    "<b>Impact:</b> channel-sensitive maps may be less reliable at this point."
                ),
            }
        if kind == "dominant":
            return {
                "label": f"Point {index + 1} ({100 + index}, {200 + index})",
                "finding": "Finding: unexpected dominant AP",
                "detail": (
                    "<b>Dominant AP:</b> AP-WEST (-48.0 dBm, 21.4 m)<br>"
                    "<b>Closest AP:</b> AP-EAST (2.6 m)"
                ),
            }
        if kind == "metadata":
            return {
                "label": label,
                "detail": (
                    "<b>Observed Channels:</b> 40, 44<br>"
                    "<b>Expected Channels:</b> 36<br>"
                    "<b>Observed Bands:</b> 5 GHz<br>"
                    "<b>Expected Bands:</b> 2.4 GHz"
                ),
            }
        if kind == "channel":
            return {
                "label": label,
                "detail": (
                    "<b>Band:</b> 5 GHz<br>"
                    "<b>Observed Channels:</b> 36, 40<br>"
                    "<b>Maps Use:</b> 40<br>"
                    "<b>Status:</b> clean"
                ),
            }
        if kind == "memory":
            return {
                "label": label,
                "detail": (
                    "<b>Memory Status:</b> <s>M</s> - current AP data differs from AP Memory<br>"
                    "<b>Different Fields:</b> Alias, Metadata<br>"
                    "<b>Next Step:</b> update from memory, or keep current data and save it"
                ),
            }
        return {
            "label": label,
            "detail": (
                f"<b>AP Group:</b> ap-{index + 1}<br>"
                "<b>Required Action:</b> place this AP on the floor plan"
            ),
        }

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
        self.assertIn(
            "quality_dashboard_action_open_ap_channels",
            [action["label"] for action in metadata_recommendation["actions"]],
        )
        self.assertIn(
            "quality_dashboard_action_open_interference",
            [action["label"] for action in metadata_recommendation["actions"]],
        )
        self.assertEqual(
            metadata_recommendation["dialog_detail"],
            "quality_dashboard_fix_ap_metadata_dialog_detail",
        )
        self.assertEqual(metadata_recommendation["metric_key"], "quality_dashboard_metric_ap_metadata_warnings")
        self.assertEqual(len(metadata_recommendation["detail_items"]), 1)
        self.assertEqual(metadata_recommendation["detail_items"][0]["label"], "ap-1")
        self.assertTrue(any(
            action["kind"] == "ap_metadata"
            for action in metadata_recommendation["detail_items"][0]["actions"]
        ))
        self.assertFalse(any(
            action["kind"] == "live_map"
            for action in metadata_recommendation["detail_items"][0]["actions"]
        ))
        self.assertEqual(len(summary["context_lines"]), 1)
        self.assertNotIn("ap-1", summary["context_lines"][0])

    def test_quality_metadata_recommendation_keeps_all_problem_aps_in_details(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -55, 36)
        app = FakeQualityApp([row], relevant_ssids={"MAIN"})
        warnings = [
            {"group_id": f"ap-{index}", "unexpected_channels": [str(36 + index)], "expected_channels": ["1"]}
            for index in range(6)
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

        self.assertEqual(summary["ap_metadata_warnings"], 6)
        self.assertEqual(len(metadata_recommendation["detail_items"]), 6)
        self.assertEqual(metadata_recommendation["detail_items"][-1]["label"], "ap-5")
        self.assertIn("+3", summary["ap_metadata_warning_labels"])

    def test_quality_recommendation_actions_put_details_before_map_buttons(self):
        inline_actions, map_actions = split_recommendation_actions(
            [
                {"kind": "live_map", "map_type": "channel"},
                {"kind": "live_map", "map_type": "interference"},
                {"kind": "ap_metadata"},
            ],
            has_details=True,
        )

        self.assertEqual(inline_actions, [])
        self.assertEqual([action["map_type"] for action in map_actions], ["channel", "interference"])

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
        channel_recommendation = next(
            recommendation
            for recommendation in summary["recommendations"]
            if recommendation["title"] == "quality_dashboard_fix_channel_change_clean_title"
        )
        self.assertEqual(len(channel_recommendation["detail_items"]), 1)
        self.assertEqual(channel_recommendation["detail_items"][0]["label"], "ap-1")
        self.assertTrue(any(action.get("map_type") == "channel" for action in channel_recommendation["actions"]))
        self.assertTrue(any(action.get("map_type") == "interference" for action in channel_recommendation["actions"]))
        self.assertEqual(
            channel_recommendation["dialog_detail"],
            "quality_dashboard_fix_channel_change_dialog_detail",
        )
        self.assertEqual(channel_recommendation["metric_key"], "quality_dashboard_metric_channel_changes")
        self.assertFalse(any(
            action["kind"] == "live_map"
            for action in channel_recommendation["detail_items"][0]["actions"]
        ))

    def test_quality_recommends_ap_memory_review_from_kpi(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -55, 36)
        groups = [
            build_manual_ap_group(
                "ap-1",
                ["70:4f:57:aa:bb:10"],
                memory_applied=True,
                memory_applied_at="2026-05-15T10:00:00Z",
                memory_match_bssids=["70:4f:57:aa:bb:10"],
            )
        ]
        app = FakeQualityApp([row], groups, relevant_ssids={"MAIN"})

        summary = build_summary(
            app,
            [{"status": QUALITY_GOOD, "needs_review": False, "ap_position_warning_count": 0}],
            [],
            groups,
        )

        memory_recommendation = next(
            recommendation
            for recommendation in summary["recommendations"]
            if recommendation["title"] == "quality_dashboard_fix_ap_memory_title"
        )

        self.assertEqual(summary["ap_memory_applied"], 1)
        self.assertEqual(summary["ap_memory_review"], 1)
        self.assertEqual(summary["ap_memory_update"], 0)
        self.assertEqual(memory_recommendation["metric_key"], "quality_dashboard_metric_ap_memory_applied")
        self.assertEqual(memory_recommendation["dialog_detail"], "quality_dashboard_fix_ap_memory_dialog_detail")
        self.assertEqual(memory_recommendation["actions"], [])
        self.assertEqual(memory_recommendation["detail_items"][0]["label"], "ap-1")
        self.assertIn("70:4f:57:aa:bb:10", memory_recommendation["detail_items"][0]["detail"])
        self.assertNotIn("Applied At", memory_recommendation["detail_items"][0]["detail"])
        self.assertTrue(any(
            action["kind"] == "ap_group"
            for action in memory_recommendation["detail_items"][0]["actions"]
        ))

    def test_quality_recommends_manual_ap_memory_update_review(self):
        temp_dir = tempfile.TemporaryDirectory()
        previous = os.environ.get("WIFI_HEATMAP_AP_MEMORY_FILE")
        os.environ["WIFI_HEATMAP_AP_MEMORY_FILE"] = os.path.join(temp_dir.name, "ap_memory.memory")
        ensure_ap_memory_file()
        try:
            bssid = "70:4f:57:aa:bb:10"
            rows = [build_row("p1", "MAIN", bssid, -55, 60, band="5")]
            update_ap_memory_from_groups(
                [
                    build_manual_ap_group(
                        "office-ap",
                        [bssid],
                        alias="Office AP",
                        metadata={"expected_channels": "60"},
                    )
                ],
                rows,
            )
            groups = [
                build_manual_ap_group(
                    "office-ap",
                    [bssid],
                    alias="Old AP",
                    metadata={"expected_channels": "40"},
                )
            ]
            app = FakeQualityApp(rows, groups, relevant_ssids={"MAIN"})

            summary = build_summary(
                app,
                [{"status": QUALITY_GOOD, "needs_review": False, "ap_position_warning_count": 0}],
                [],
                groups,
            )

            memory_recommendation = next(
                recommendation
                for recommendation in summary["recommendations"]
                if recommendation["title"] == "quality_dashboard_fix_ap_memory_title"
            )

            self.assertEqual(summary["ap_memory_review"], 1)
            self.assertEqual(summary["ap_memory_applied"], 0)
            self.assertEqual(summary["ap_memory_update"], 1)
            self.assertIn(
                "<s>M</s>",
                memory_recommendation["detail_items"][0]["detail"],
            )
            self.assertIn("Alias", memory_recommendation["detail_items"][0]["detail"])
            self.assertIn("Metadata", memory_recommendation["detail_items"][0]["detail"])
        finally:
            if previous is None:
                os.environ.pop("WIFI_HEATMAP_AP_MEMORY_FILE", None)
            else:
                os.environ["WIFI_HEATMAP_AP_MEMORY_FILE"] = previous
            temp_dir.cleanup()

    def test_quality_summary_counts_ap_position_warnings_in_point_review(self):
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
        self.assertEqual(summary["scan_review_points"], 2)
        self.assertEqual(summary["scan_ok_points"], 0)
        self.assertEqual(summary["ap_diagnostic_points"], 1)
        self.assertEqual(summary["sparse_data"], 1)
        self.assertEqual(summary["ap_position_warnings"], 1)
        self.assertEqual(summary["recommendations"][0]["title"], "quality_dashboard_fix_sparse_title")
        self.assertEqual(quality_status_text_keys(summary)[0], "quality_dashboard_status_review_title")

    def test_quality_metric_card_severity_rules(self):
        self.assertEqual(
            resolve_metric_severity("quality_dashboard_metric_points", 0, "info"),
            "info",
        )
        self.assertEqual(
            resolve_metric_severity("quality_dashboard_metric_missing", 0, "danger"),
            "good",
        )
        self.assertEqual(
            resolve_metric_severity("quality_dashboard_metric_missing", 2, "danger"),
            "danger",
        )
        self.assertEqual(
            resolve_metric_severity("quality_dashboard_metric_channel_changes", 2, "info"),
            "info",
        )
        self.assertEqual(
            resolve_metric_severity("quality_dashboard_metric_channel_changes", 2, "warning"),
            "warning",
        )

    def test_quality_point_metric_filters_match_point_table_scope(self):
        rows = [
            {
                "status": QUALITY_GOOD,
                "scanner_detail_issue": False,
                "ap_position_warning_count": 0,
            },
            {
                "status": QUALITY_GOOD,
                "scanner_detail_issue": True,
                "ap_position_warning_count": 0,
            },
            {
                "status": QUALITY_LOW_CONFIDENCE,
                "quality_breakdown": [
                    {"ssid": "main", "status": QUALITY_LOW_CONFIDENCE},
                    {"ssid": "guest", "status": QUALITY_UNSTABLE_SIGNAL},
                ],
                "scanner_detail_issue": False,
                "ap_position_warning_count": 0,
            },
            {
                "status": QUALITY_MISSING_RELEVANT,
                "scanner_detail_issue": False,
                "ap_position_warning_count": 1,
            },
            {
                "status": QUALITY_GOOD,
                "scanner_detail_issue": False,
                "ap_position_warning_count": 1,
            },
        ]

        self.assertEqual(point_rows_for_metric(rows, "quality_dashboard_metric_points"), [])
        self.assertEqual(point_rows_for_metric(rows, "quality_dashboard_metric_scan_ok"), [])
        self.assertEqual(len(point_rows_for_metric(rows, "quality_dashboard_metric_rescan")), 4)
        self.assertEqual(point_rows_for_metric(rows, "quality_dashboard_metric_scanner_details"), [])
        self.assertEqual(len(point_rows_for_metric(rows, "quality_dashboard_metric_low_confidence")), 1)
        self.assertEqual(len(point_rows_for_metric(rows, "quality_dashboard_metric_unstable")), 1)
        self.assertEqual(len(point_rows_for_metric(rows, "quality_dashboard_metric_missing")), 1)
        self.assertEqual(point_rows_for_metric(rows, "quality_dashboard_metric_ap_diagnostic_points"), [])
        self.assertEqual(point_rows_for_metric(rows, "quality_dashboard_metric_ap_metadata_warnings"), [])

    def test_quality_metric_clickability_is_limited_to_point_filters_with_rows(self):
        self.assertFalse(is_point_metric_filter("quality_dashboard_metric_points", 25))
        self.assertFalse(is_point_metric_filter("quality_dashboard_metric_scan_ok", 10))
        self.assertFalse(is_point_metric_filter("quality_dashboard_metric_scanner_details", 2))
        self.assertFalse(is_point_metric_filter("quality_dashboard_metric_ap_diagnostic_points", 2))
        self.assertTrue(is_point_metric_filter("quality_dashboard_metric_rescan", 2))
        self.assertFalse(is_point_metric_filter("quality_dashboard_metric_rescan", 0))
        self.assertFalse(is_point_metric_filter("quality_dashboard_metric_ap_metadata_warnings", 2))

    def test_quality_point_table_overlay_visible_rows_are_capped_and_autofit(self):
        self.assertEqual(point_table_visible_row_count(0), 1)
        self.assertEqual(point_table_visible_row_count(4), 4)
        self.assertEqual(point_table_visible_row_count(14), 14)
        self.assertEqual(point_table_visible_row_count(25), 14)

    def test_quality_point_table_dialog_fits_single_height_rows(self):
        QApplication.instance() or QApplication([])
        owner = QWidget()
        owner.app = FakeQualityApp([])
        rows = [
            {
                "number": index + 1,
                "x": 10,
                "y": 20,
                "severity": "warning",
                "status": QUALITY_LOW_CONFIDENCE,
                "quality_breakdown": [],
                "quality_issue": "issue",
                "scanner_detail_issue": False,
                "ap_position_warning_count": 0,
                "issue": "issue",
                "needs_review": True,
            }
            for index in range(25)
        ]
        dialog = PointRowsDialog(owner, "Low Scan Confidence", rows, len(rows), "quality_dashboard_metric_points")

        try:
            dialog.show()
            QApplication.processEvents()

            expected_rows = point_table_visible_row_count(len(rows))
            row_height = dialog.table.rowHeight(0)
            viewport_height = dialog.table.viewport().height()
            extra_height = viewport_height - (expected_rows * row_height)

            self.assertEqual(dialog.table.columnCount(), 4)
            self.assertEqual(dialog.table.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.assertGreaterEqual(extra_height, 0)
            self.assertLessEqual(extra_height, max(2, row_height // 10))

            initial_table_height = dialog.table.height()
            dialog.resize(dialog.width(), dialog.height() + 120)
            QApplication.processEvents()
            self.assertGreater(dialog.table.height(), initial_table_height)
        finally:
            dialog.close()
            owner.deleteLater()

    def test_quality_point_table_dialog_locks_height_when_all_rows_are_visible(self):
        QApplication.instance() or QApplication([])
        owner = QWidget()
        owner.app = FakeQualityApp([])
        rows = [
            {
                "number": index + 1,
                "x": 10,
                "y": 20,
                "severity": "warning",
                "status": QUALITY_LOW_CONFIDENCE,
                "quality_breakdown": [],
                "quality_issue": "issue",
                "scanner_detail_issue": False,
                "ap_position_warning_count": 0,
                "issue": "issue",
                "needs_review": True,
            }
            for index in range(4)
        ]
        dialog = PointRowsDialog(owner, "Low Scan Confidence", rows, len(rows), "quality_dashboard_metric_points")

        try:
            dialog.show()
            QApplication.processEvents()
            self.assertEqual(dialog.minimumHeight(), dialog.maximumHeight())
        finally:
            dialog.close()
            owner.deleteLater()

    def test_quality_point_table_issue_matches_selected_kpi(self):
        app = FakeQualityApp([])
        row = {
            "status": QUALITY_LOW_CONFIDENCE,
            "quality_issue": "quality issue",
            "quality_breakdown": [
                {
                    "ssid": "main",
                    "status": QUALITY_LOW_CONFIDENCE,
                    "message": "low_confidence",
                    "min_confidence": 0.4,
                },
                {
                    "ssid": "main",
                    "status": QUALITY_UNSTABLE_SIGNAL,
                    "message": "unstable_signal",
                    "range_db": 14.0,
                },
            ],
            "scanner_detail_issue": True,
            "scanner_detail_issue_text": "scanner issue",
            "scanner_details": {
                "has_issue": True,
                "issue_types": [SCANNER_DETAIL_FALLBACK_BACKEND, SCANNER_DETAIL_MISSING_CHANNEL_WIDTH],
                "backend_counts": {"netsh": 5},
                "missing_channel_width_rows": 5,
            },
            "ap_position_issue": "ap issue",
            "ap_position_warning_count": 1,
            "issue": "quality issue; scanner issue; ap issue",
        }

        self.assertEqual(
            format_metric_point_issue(app, row, "quality_dashboard_metric_points"),
            "quality issue; scanner issue; ap issue",
        )
        self.assertEqual(
            format_metric_point_issue(app, row, "quality_dashboard_metric_rescan"),
            "Check KPI: Low Scan Confidence; Unstable Signal; Scanner Details Missing; Dominant AP Findings",
        )
        self.assertEqual(
            format_metric_point_issue(app, row, "quality_dashboard_metric_scanner_details"),
            "Scanner Used: <b>NETSH</b> (Limited Channel Details) | "
            "Channel Width Missing On <b>5</b> Scan Rows",
        )
        self.assertEqual(
            format_metric_point_issue(app, row, "quality_dashboard_metric_low_confidence"),
            "<b>MAIN</b>: 40% Confidence Level",
        )
        self.assertEqual(
            format_metric_point_issue(app, row, "quality_dashboard_metric_unstable"),
            "<b>MAIN</b>: Signal Varies By 14.0 dB",
        )
        self.assertEqual(
            format_metric_point_issue(app, row, "quality_dashboard_metric_ap_diagnostic_points"),
            "ap issue",
        )
        self.assertEqual(
            format_metric_point_issue(app, row, "quality_dashboard_metric_scan_ok"),
            "No Issues Detected",
        )

    def test_quality_point_table_issue_formats_missing_and_sparse_clearly(self):
        app = FakeQualityApp([])
        missing_row = {
            "status": QUALITY_MISSING_RELEVANT,
            "quality_breakdown": [
                {"ssid": "guest", "status": QUALITY_MISSING_RELEVANT, "message": "missing"},
            ],
        }
        sparse_row = {
            "status": QUALITY_SPARSE_DATA,
            "quality_breakdown": [],
            "quality_issue": "",
        }

        self.assertEqual(
            format_metric_point_issue(app, missing_row, "quality_dashboard_metric_missing"),
            "<b>GUEST</b>: Relevant Network Not Detected At This Point",
        )
        self.assertEqual(
            format_metric_point_issue(app, sparse_row, "quality_dashboard_metric_sparse"),
            "Not Enough Scan Samples At This Point",
        )

    def test_quality_rescan_issue_lists_touched_kpis(self):
        app = FakeQualityApp([])
        row = {
            "status": QUALITY_UNSTABLE_SIGNAL,
            "scanner_detail_issue": True,
        }

        self.assertEqual(
            rescan_kpi_labels_for_row(app, row),
            [
                "Unstable Signal",
                "Scanner Details Missing",
            ],
        )

    def test_quality_ap_position_details_use_global_dominant_action(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -55, 1)
        app = FakeQualityApp([row], relevant_ssids={"MAIN"})

        summary = build_summary(
            app,
            [
                {
                    "number": 1,
                    "x": "100",
                    "y": "200",
                    "status": QUALITY_GOOD,
                    "needs_review": True,
                    "ap_position_warning_count": 1,
                    "issue": "AP Position: ap-1",
                    "ap_position": {
                        "dominant_ap_group": "far-ap",
                        "dominant_signal_dbm": -51,
                        "warnings": [AP_POSITION_UNEXPECTED_DOMINANT],
                        "analysis": {
                            "dominant_distance_m": 24.5,
                            "nearest_ap_group": "near-ap",
                            "nearest_distance_m": 3.2,
                        },
                    },
                },
            ],
            [],
            [],
        )

        position_recommendation = next(
            recommendation
            for recommendation in summary["recommendations"]
            if recommendation["title"] == "quality_dashboard_fix_ap_position_title"
        )

        self.assertEqual(position_recommendation["metric_key"], "quality_dashboard_metric_ap_diagnostic_points")
        self.assertTrue(any(action.get("map_type") == "dominant" for action in position_recommendation["actions"]))
        self.assertEqual(position_recommendation.get("detail_actions"), [])
        self.assertEqual(
            [action["kind"] for action in position_recommendation["detail_items"][0]["actions"]],
            ["point"],
        )
        self.assertIn("far-ap", position_recommendation["detail_items"][0]["detail"])
        self.assertIn("near-ap", position_recommendation["detail_items"][0]["detail"])
        self.assertIn("24.5 m", position_recommendation["detail_items"][0]["detail"])
        self.assertIn("unexpected dominant", position_recommendation["detail_items"][0]["finding"])
        ap_issue_row = {
            "ap_position_warning_count": 1,
            "ap_position": {
                "dominant_ap_group": "far-ap",
                "dominant_signal_dbm": -51,
                "warnings": [AP_POSITION_UNEXPECTED_DOMINANT],
                "analysis": {
                    "dominant_distance_m": 24.5,
                    "nearest_ap_group": "near-ap",
                    "nearest_distance_m": 3.2,
                },
            },
        }
        self.assertEqual(
            format_metric_point_issue(
                app,
                ap_issue_row,
                "quality_dashboard_metric_ap_diagnostic_points",
            ),
            "Dominant AP: <b>far-ap</b> (-51.0 dBm, 24.5 m) | "
            "Closest AP: <b>near-ap</b> (3.2 m) | <b>unexpected dominant</b>",
        )

    def test_quality_status_uses_setup_message_for_model_only_diagnostics(self):
        summary = {
            "total_points": 12,
            "review_points": 3,
            "scan_review_points": 0,
            "ap_position_warnings": 0,
            "ap_metadata_warnings": 3,
            "ap_missing_positions": 0,
        }

        self.assertEqual(quality_status_text_keys(summary)[0], "quality_dashboard_status_setup_title")

    def test_quality_status_uses_setup_message_for_channel_change_model_only(self):
        summary = {
            "total_points": 12,
            "review_points": 0,
            "scan_review_points": 0,
            "ap_position_warnings": 0,
            "ap_metadata_warnings": 0,
            "ap_missing_positions": 0,
            "channel_change_count": 1,
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
                        "coverage_scope": "local",
                        "coverage_radius_m": "22.5",
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
            self.assertEqual(groups[0]["metadata"]["coverage_scope"], AP_COVERAGE_SCOPE_LOCAL)
            self.assertEqual(groups[0]["metadata"]["coverage_radius_m"], "22.5")

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



