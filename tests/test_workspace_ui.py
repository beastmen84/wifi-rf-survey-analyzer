from tests._common import *
from PySide6.QtWidgets import QPushButton
from qt_ui.qt_point_workflow import MissingRelevantNetworksDialog


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

    def test_workspace_styles_scrollbars_and_measurement_point_selection(self):
        window = WifiHeatmapQtApp()
        try:
            style = window.styleSheet()
            self.assertIn("QScrollBar::handle:vertical", style)
            self.assertIn("QScrollBar::add-line:vertical", style)
            self.assertEqual(window.points_table.objectName(), "measurementPointsTable")
            self.assertIn("QTableWidget#measurementPointsTable::item:selected", style)
            self.assertIn("color: #FFFFFF", style)
        finally:
            window.deleteLater()


class APGroupManagerDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    class FakeApp(QDialog):
        def __init__(self, session):
            super().__init__()
            self.session = session
            self.theme = "light"

        def tr(self, key, **kwargs):
            return translate("en", key, **kwargs)

        def channel_sort_key(self, channel):
            try:
                return int(str(channel))
            except ValueError:
                return 9999

    def make_bssid_dialog(self):
        class FakeChannelApp:
            def channel_sort_key(self, channel):
                try:
                    return int(str(channel))
                except ValueError:
                    return 9999

        class FakeManager(QDialog):
            def __init__(self):
                super().__init__()
                self.app = FakeChannelApp()

            def tr(self, key, **kwargs):
                return translate("en", key, **kwargs)

            def prepare_action_button(self, button):
                button.setObjectName("apDialogActionButton")

        manager = FakeManager()
        current_group = {
            "group_id": "current-ap",
            "alias": "Current AP",
            "bssids": ["70:4f:57:aa:bb:10", "70:4f:57:aa:bb:11"],
        }
        groups = [
            current_group,
            {
                "group_id": "neighbor-ap",
                "alias": "Neighbor AP",
                "bssids": ["70:4f:57:aa:bb:20"],
            },
        ]
        detected_by_bssid = {
            "70:4f:57:aa:bb:10": {"ssids": ["MAIN"], "channels": ["1"], "bands": ["2.4"]},
            "70:4f:57:aa:bb:11": {"ssids": ["MAIN-6"], "channels": ["5"], "bands": ["6"]},
            "70:4f:57:aa:bb:20": {"ssids": ["Guest"], "channels": ["36"], "bands": ["5"]},
            "90:11:22:33:44:10": {"ssids": ["New"], "channels": ["11"], "bands": ["2.4"]},
        }
        dialog = BssidSelectionDialog(
            manager,
            current_group,
            groups,
            detected_by_bssid,
            focus_bssids=["70:4f:57:aa:bb:20"],
        )
        return manager, dialog

    def make_ap_manager_dialog(self):
        session = SurveySession()
        session.rows = [
            build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 1),
            build_row("p2", "MAIN", "70:4f:57:aa:bb:11", -51, 6),
            build_row("p3", "Guest", "80:4f:57:aa:bb:20", -55, 36),
            build_row("p4", "MAIN-6", "90:4f:57:aa:cc:30", -60, 5, band="6"),
        ]
        session.set_ap_groups([
            build_manual_ap_group(
                "warning-ap",
                ["70:4f:57:aa:bb:10", "70:4f:57:aa:bb:11"],
                alias="Warning AP",
                locked=True,
            ),
            build_manual_ap_group(
                "neighbor-ap",
                ["80:4f:57:aa:bb:20"],
                alias="Neighbor AP",
                locked=True,
                role=AP_ROLE_EXTERNAL,
            ),
        ])
        app = self.FakeApp(session)
        dialog = APGroupManagerDialog(app)
        return app, dialog

    def set_combo_value(self, combo, value):
        index = combo.findData(value)
        self.assertNotEqual(index, -1)
        combo.setCurrentIndex(index)
        QApplication.processEvents()

    def test_ap_manager_table_filters_status_role_band_and_state(self):
        app, dialog = self.make_ap_manager_dialog()
        try:
            self.assertEqual(len(dialog.visible_group_ids), 3)

            self.set_combo_value(dialog.status_filter_combo, "warning")
            self.assertEqual(dialog.visible_group_ids, ["warning-ap"])

            dialog.clear_filters()
            self.set_combo_value(dialog.role_filter_combo, AP_ROLE_EXTERNAL)
            self.assertEqual(dialog.visible_group_ids, ["neighbor-ap"])

            dialog.clear_filters()
            self.set_combo_value(dialog.band_filter_combo, "6")
            self.assertEqual(len(dialog.visible_group_ids), 1)
            visible_group = dialog.get_group_by_id(dialog.visible_group_ids[0])
            self.assertEqual(visible_group.get("bands"), ["6"])

            dialog.clear_filters()
            self.set_combo_value(dialog.state_filter_combo, "auto")
            self.assertEqual(len(dialog.visible_group_ids), 1)
            visible_group = dialog.get_group_by_id(dialog.visible_group_ids[0])
            self.assertFalse(visible_group.get("locked"))

            dialog.clear_filters()
            dialog.search_edit.setText("Neighbor")
            QApplication.processEvents()
            self.assertEqual(dialog.visible_group_ids, ["neighbor-ap"])

            dialog.clear_filters()
            self.assertEqual(len(dialog.visible_group_ids), 3)
        finally:
            dialog.deleteLater()
            app.deleteLater()

    def test_ap_manager_styles_modern_scrollbars(self):
        app, dialog = self.make_ap_manager_dialog()
        try:
            style = dialog.styleSheet()
            self.assertIn("QScrollBar::handle:vertical", style)
            self.assertIn("QScrollBar::add-line:vertical", style)
            self.assertIn("QScrollBar::handle:horizontal", style)
        finally:
            dialog.deleteLater()
            app.deleteLater()

    def test_ap_manager_can_split_bssids_into_new_manual_group(self):
        app, dialog = self.make_ap_manager_dialog()
        try:
            self.assertTrue(dialog.split_bssids_to_new_group(
                "warning-ap",
                ["70:4f:57:aa:bb:11"],
            ))

            source_group = dialog.get_group_by_id("warning-ap")
            self.assertEqual(source_group["bssids"], ["70:4f:57:aa:bb:10"])
            split_groups = [
                group
                for group in dialog.groups
                if group.get("group_id") != "warning-ap" and "70:4f:57:aa:bb:11" in group.get("bssids", [])
            ]
            self.assertEqual(len(split_groups), 1)
            self.assertTrue(split_groups[0]["locked"])
            self.assertEqual(split_groups[0]["role"], AP_ROLE_INTERNAL)
        finally:
            dialog.deleteLater()
            app.deleteLater()

    def test_ap_manager_can_move_bssids_to_existing_group(self):
        app, dialog = self.make_ap_manager_dialog()
        try:
            self.assertTrue(dialog.move_bssids_to_group(
                "neighbor-ap",
                ["90:4f:57:aa:cc:30"],
            ))

            target_group = dialog.get_group_by_id("neighbor-ap")
            self.assertEqual(target_group["bssids"], [
                "80:4f:57:aa:bb:20",
                "90:4f:57:aa:cc:30",
            ])
            other_groups_with_bssid = [
                group
                for group in dialog.groups
                if group.get("group_id") != "neighbor-ap"
                and "90:4f:57:aa:cc:30" in group.get("bssids", [])
            ]
            self.assertEqual(other_groups_with_bssid, [])
        finally:
            dialog.deleteLater()
            app.deleteLater()

    def test_conflict_dialog_explains_warning_and_action(self):
        app, dialog = self.make_ap_manager_dialog()
        conflict_dialog = None
        try:
            group = dialog.get_group_by_id("warning-ap")
            conflicts = dialog.group_conflicts_by_id["warning-ap"]
            conflict_dialog = ConflictDialog(dialog, group, conflicts)

            text = conflict_dialog.format_conflicts()

            self.assertIn("AP group: Warning AP (warning-ap)", text)
            self.assertIn("What this can mean", text)
            self.assertIn("Recommended check", text)
            self.assertIn("2.4 GHz: 2 channels, 2 BSSIDs (1, 6)", text)
            self.assertIn("CH 1: 70:4f:57:aa:bb:10", text)
            self.assertIn("CH 6: 70:4f:57:aa:bb:11", text)
        finally:
            if conflict_dialog is not None:
                conflict_dialog.deleteLater()
            dialog.deleteLater()
            app.deleteLater()

    def test_bssid_dialog_filters_and_visible_selection_actions(self):
        manager, dialog = self.make_bssid_dialog()
        try:
            self.assertEqual(set(dialog.visible_bssids), {
                "70:4f:57:aa:bb:10",
                "70:4f:57:aa:bb:11",
                "70:4f:57:aa:bb:20",
                "90:11:22:33:44:10",
            })

            self.set_combo_value(dialog.scope_combo, "current")
            self.assertEqual(set(dialog.visible_bssids), {
                "70:4f:57:aa:bb:10",
                "70:4f:57:aa:bb:11",
            })

            self.set_combo_value(dialog.band_combo, "6")
            self.assertEqual(dialog.visible_bssids, ["70:4f:57:aa:bb:11"])

            dialog.clear_visible_button.click()
            self.assertEqual(dialog.selected_bssids(), ["70:4f:57:aa:bb:10"])

            dialog.select_visible_button.click()
            self.assertEqual(set(dialog.selected_bssids()), {
                "70:4f:57:aa:bb:10",
                "70:4f:57:aa:bb:11",
            })

            self.set_combo_value(dialog.band_combo, "")
            self.set_combo_value(dialog.scope_combo, "other")
            self.assertEqual(dialog.visible_bssids, ["70:4f:57:aa:bb:20"])

            self.set_combo_value(dialog.scope_combo, "unassigned")
            self.assertEqual(dialog.visible_bssids, ["90:11:22:33:44:10"])

            self.set_combo_value(dialog.scope_combo, "focus")
            self.assertEqual(dialog.visible_bssids, ["70:4f:57:aa:bb:20"])

            dialog.search_edit.setText("Guest")
            QApplication.processEvents()
            self.assertEqual(dialog.visible_bssids, ["70:4f:57:aa:bb:20"])
        finally:
            dialog.deleteLater()
            manager.deleteLater()


class PointCaptureDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    class FakeApp(QDialog):
        def tr(self, key, **kwargs):
            return translate("it", key, **kwargs)

    def test_missing_relevant_network_buttons_use_compact_layout(self):
        app = self.FakeApp()
        dialog = MissingRelevantNetworksDialog(app, ["AICS-WIFI-UFF6"])
        try:
            buttons = [
                button
                for button in dialog.findChildren(QPushButton)
                if button.text() in {
                    app.tr("keep_scan"),
                    app.tr("retry_scan"),
                    app.tr("cancel_point"),
                }
            ]

            self.assertEqual(len(buttons), 3)
            self.assertTrue(all(button.objectName() == "compactButton" for button in buttons))
            total_button_width = sum(button.minimumWidth() for button in buttons)
            self.assertLess(total_button_width, dialog.minimumWidth())
        finally:
            dialog.deleteLater()
            app.deleteLater()


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

            self.assertEqual(file_message, window.tr("file_created", path="export.pdf"))
            self.assertNotIn(window.tr("interference_summary_title"), file_message)
        finally:
            window.deleteLater()

    def test_relevant_ssid_state_loads_from_session_metadata(self):
        window = WifiHeatmapQtApp()
        try:
            session = SurveySession()
            session.metadata[qt_app_module.RELEVANT_SSIDS_METADATA_KEY] = json.dumps(["MAIN", "Guest"])
            session.metadata[qt_app_module.KNOWN_SSIDS_METADATA_KEY] = json.dumps(["MAIN", "Guest", "IoT"])
            window.session = session

            window.load_session_ssid_state()

            self.assertEqual(window.relevant_ssids, {"MAIN", "Guest"})
            self.assertEqual(window.known_ssids, {"MAIN", "Guest", "IoT"})
        finally:
            window.deleteLater()

    def test_set_relevant_ssids_persists_metadata_and_updates_existing_row_flags(self):
        window = WifiHeatmapQtApp()
        try:
            main_row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 1)
            guest_row = build_row("p1", "Guest", "70:4f:57:aa:bb:11", -55, 1)
            iot_row = build_row("p1", "IoT", "70:4f:57:aa:bb:12", -60, 1)
            session = SurveySession()
            session.rows = [main_row, guest_row, iot_row]
            session.dirty = False
            window.session = session
            window.known_ssids = {"Old"}

            window.set_relevant_ssids({" MAIN ", "guest", ""})

            self.assertEqual(window.relevant_ssids, {"MAIN", "guest"})
            self.assertEqual(window.known_ssids, {"Old", "MAIN", "guest"})
            self.assertEqual(json.loads(session.metadata[qt_app_module.RELEVANT_SSIDS_METADATA_KEY]), ["MAIN", "guest"])
            self.assertEqual([row["is_relevant"] for row in session.rows], ["1", "1", "0"])
            self.assertTrue(session.dirty)
        finally:
            window.deleteLater()

    def test_clear_relevant_ssids_removes_metadata_and_resets_row_flags(self):
        window = WifiHeatmapQtApp()
        try:
            session = SurveySession()
            session.rows = [
                build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 1),
                build_row("p1", "Guest", "70:4f:57:aa:bb:11", -55, 1),
            ]
            session.metadata[qt_app_module.RELEVANT_SSIDS_METADATA_KEY] = json.dumps(["MAIN"])
            session.metadata[qt_app_module.KNOWN_SSIDS_METADATA_KEY] = json.dumps(["MAIN", "Guest"])
            session.dirty = False
            window.session = session
            window.relevant_ssids = {"MAIN"}
            window.known_ssids = {"MAIN", "Guest"}

            window.clear_relevant_ssids()

            self.assertEqual(window.relevant_ssids, set())
            self.assertEqual(window.known_ssids, set())
            self.assertNotIn(qt_app_module.RELEVANT_SSIDS_METADATA_KEY, session.metadata)
            self.assertNotIn(qt_app_module.KNOWN_SSIDS_METADATA_KEY, session.metadata)
            self.assertEqual([row["is_relevant"] for row in session.rows], ["0", "0"])
            self.assertTrue(session.dirty)
        finally:
            window.deleteLater()

    def test_available_relevant_ssids_combines_known_current_and_session_ssids(self):
        window = WifiHeatmapQtApp()
        try:
            session = SurveySession()
            session.rows = [
                build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 1),
                build_row("p1", "Guest", "70:4f:57:aa:bb:11", -55, 1),
            ]
            window.session = session
            window.relevant_ssids = {"IoT"}
            window.known_ssids = {"Old"}

            self.assertEqual(window.available_relevant_ssids(), {"MAIN", "Guest", "IoT", "Old"})
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

    def test_live_discrete_legend_auto_fits_without_locking_splitter(self):
        window = WifiHeatmapQtApp()
        try:
            payload = {
                "kind": "swatches",
                "title": "Dominant AP",
                "items": [{
                    "label": "Corr. uff. 12 - AICS-WIFI very long readable legend label",
                    "marker_id": "p1",
                    "color": "#1976d2",
                }],
            }

            window.update_live_legend(payload)

            self.assertFalse(window.live_legend_frame.isHidden())
            self.assertEqual(window.live_legend_frame.minimumWidth(), window.spx(240))
            self.assertGreater(window.live_legend_frame.maximumWidth(), window.spx(5000))
            self.assertFalse(window.live_splitter.childrenCollapsible())
            self.assertFalse(window.live_splitter.isCollapsible(0))
            self.assertFalse(window.live_splitter.isCollapsible(1))
            self.assertFalse(window.live_legend_user_resized)

            window.on_live_splitter_moved(0, 1)

            self.assertTrue(window.live_legend_user_resized)

            dominant_index = window.live_map_type_combo.findData("dominant")
            window.live_current_map_type = "channel"
            window.live_map_type_combo.blockSignals(True)
            window.live_map_type_combo.setCurrentIndex(dominant_index)
            window.live_map_type_combo.blockSignals(False)
            window.update_live_option_state()

            self.assertFalse(window.live_legend_user_resized)
        finally:
            window.deleteLater()

    def test_live_pdf_export_asks_for_destination_path(self):
        window = WifiHeatmapQtApp()
        original_save_file_name = qt_live_export_module.get_centered_save_file_name
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

                qt_live_export_module.get_centered_save_file_name = fake_save_file_name
                window.session = FakeSession()

                output_file = window.choose_live_pdf_output_file(MapConfig(ssid="MAIN", map_type="signal"))

                self.assertEqual(output_file, f"{chosen_path}.pdf")
                self.assertEqual(captured["title"], window.tr("save_live_pdf_title"))
                self.assertEqual(captured["file_filter"], window.tr("live_pdf_file_filter"))
                self.assertIn("MAIN_coverage", captured["default_path"])
        finally:
            qt_live_export_module.get_centered_save_file_name = original_save_file_name
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
            self.assertEqual(combo_values(window.live_band_combo), ["all", "2.4", "5", "6"])
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
            self.assertEqual(combo_values(window.live_band_combo), ["2.4", "5", "6"])
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
            self.assertEqual(combo_values(window.live_band_combo), ["all", "2.4", "5", "6"])
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
            self.assertEqual(combo_values(window.live_band_combo), ["all", "2.4", "5", "6"])
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



