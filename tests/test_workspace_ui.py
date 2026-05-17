from tests._common import *
from app_core.constants import (
    DEFAULT_FLOORPLAN_HEIGHT_PX,
    DEFAULT_FLOORPLAN_METADATA_KEY,
    DEFAULT_FLOORPLAN_WIDTH_PX,
    HEATMAP_MAX_DISTANCE_PX,
)
from app_core.version import (
    APP_VERSION,
    APP_VERSION_LABEL,
    configure_qt_application_metadata,
    format_versioned_title,
    get_app_icon_path,
)
from PySide6.QtWidgets import QPushButton
from qt_ui.qt_help_dialog import build_help_html, build_help_sections, help_palette
from qt_ui.qt_point_workflow import MissingRelevantNetworksDialog, PointCaptureMixin
from qt_ui.qt_settings_memory import confirm_clear_ap_memory
from translations.i18n import SUPPORTED_LANGUAGES


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

    def test_product_version_metadata_is_exposed_to_qt_and_ui(self):
        app = QApplication.instance()
        configure_qt_application_metadata(app)
        self.assertEqual(app.applicationVersion(), APP_VERSION)
        self.assertTrue(get_app_icon_path().exists())
        self.assertFalse(app.windowIcon().isNull())

        window = WifiHeatmapQtApp()
        try:
            self.assertEqual(window.windowTitle(), format_versioned_title(window.tr("app_title")))
            self.assertIn(APP_VERSION_LABEL, window.windowTitle())
            self.assertIn(APP_VERSION_LABEL, window.copyright_label.text())

            window.change_language("IT")
            self.assertEqual(window.windowTitle(), format_versioned_title(window.tr("app_title")))
            self.assertIn(APP_VERSION_LABEL, window.copyright_label.text())
        finally:
            window.deleteLater()

    def test_start_page_shows_app_icon_next_to_title(self):
        from qt_ui.qt_startup import StartWindow

        with patch("qt_ui.qt_startup.QTimer.singleShot"):
            window = StartWindow()
        try:
            title_pixmap = window.title_icon.pixmap()

            self.assertEqual(window.title_icon.objectName(), "startTitleIcon")
            self.assertIsNotNone(title_pixmap)
            self.assertFalse(title_pixmap.isNull())
            self.assertEqual(window.title.text(), window.tr("app_title"))
        finally:
            window.deleteLater()

    def test_workspace_footer_shows_ap_memory_status(self):
        previous = os.environ.get("WIFI_HEATMAP_AP_MEMORY_FILE")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.environ["WIFI_HEATMAP_AP_MEMORY_FILE"] = os.path.join(temp_dir, "ap_memory.memory")
                window = WifiHeatmapQtApp()
                try:
                    self.assertEqual(window.memory_status_label.text(), "AP Memory: Empty")
                    update_ap_memory_from_groups([
                        build_manual_ap_group(
                            "office-ap",
                            ["70:4f:57:aa:bb:10"],
                            alias="Office AP",
                        )
                    ])
                    window.refresh_session_labels()
                    self.assertEqual(window.memory_status_label.text(), "AP Memory: Saved (1 AP)")
                    self.assertIn("ap_memory.memory", window.memory_status_label.toolTip())
                finally:
                    window.deleteLater()
        finally:
            if previous is None:
                os.environ.pop("WIFI_HEATMAP_AP_MEMORY_FILE", None)
            else:
                os.environ["WIFI_HEATMAP_AP_MEMORY_FILE"] = previous

    def test_analysis_toolbar_matches_recommended_workflow_order(self):
        window = WifiHeatmapQtApp()
        try:
            analysis_layout = window.quality_button.parentWidget().layout().itemAt(1).layout()
            ordered_buttons = [
                analysis_layout.itemAt(index).widget()
                for index in range(analysis_layout.count())
            ]

            self.assertEqual(
                ordered_buttons,
                [window.quality_button, window.ap_groups_button, window.help_button],
            )
        finally:
            window.deleteLater()

    def test_settings_clear_ap_memory_refreshes_footer_status(self):
        previous = os.environ.get("WIFI_HEATMAP_AP_MEMORY_FILE")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.environ["WIFI_HEATMAP_AP_MEMORY_FILE"] = os.path.join(temp_dir, "ap_memory.memory")
                update_ap_memory_from_groups([
                    build_manual_ap_group(
                        "office-ap",
                        ["70:4f:57:aa:bb:10"],
                        alias="Office AP",
                    )
                ])
                window = WifiHeatmapQtApp()
                try:
                    window.refresh_session_labels()
                    self.assertEqual(window.memory_status_label.text(), "AP Memory: Saved (1 AP)")
                    with patch("qt_ui.qt_settings_memory.confirm_clear_ap_memory_dialog", return_value=True):
                        self.assertTrue(confirm_clear_ap_memory(window))
                    self.assertEqual(get_ap_memory_summary()["group_count"], 0)
                    self.assertEqual(window.memory_status_label.text(), "AP Memory: Empty")
                finally:
                    window.deleteLater()
        finally:
            if previous is None:
                os.environ.pop("WIFI_HEATMAP_AP_MEMORY_FILE", None)
            else:
                os.environ["WIFI_HEATMAP_AP_MEMORY_FILE"] = previous

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

    def test_ap_memory_dialog_uses_themed_message_box_style(self):
        from qt_ui.qt_settings_memory import ap_memory_message_box_stylesheet

        window = WifiHeatmapQtApp()
        try:
            style = ap_memory_message_box_stylesheet(window)

            self.assertIn("QMessageBox QPushButton", style)
            self.assertIn("apMemoryDialogDestructiveButton", style)
            self.assertIn(f"min-width: {window.spx(96)}px", style)
        finally:
            window.deleteLater()

    def test_workspace_primary_tabs_fill_bar_and_track_selection(self):
        window = WifiHeatmapQtApp()
        try:
            style = window.styleSheet()
            window.tabs.resize(800, 400)

            self.assertEqual(window.tabs.objectName(), "workspaceTabs")
            self.assertEqual(window.tabs.tabBar().objectName(), "workspaceTabBar")
            self.assertTrue(window.tabs.tabBar().expanding())
            self.assertEqual(window.tabs.tabBar().tabSizeHint(0).width(), 400)
            self.assertEqual(window.tabs.tabBar().tabSizeHint(1).width(), 400)
            left_text_rect = window.tabs.tabBar().workspace_text_rect(0)
            right_text_rect = window.tabs.tabBar().workspace_text_rect(1)
            self.assertAlmostEqual(left_text_rect.center().x(), 300, delta=window.spx(8))
            self.assertAlmostEqual(right_text_rect.center().x(), 500, delta=window.spx(8))
            underline_rect = window.tabs.tabBar().workspace_underline_rect(0)
            self.assertEqual(underline_rect.left(), 0)
            self.assertEqual(underline_rect.width(), 400)
            self.assertEqual(underline_rect.height(), window.spx(3))
            self.assertEqual(window.tabs.tabBar().property("workspaceUnderlineHeight"), window.spx(3))
            self.assertEqual(window.tabs.tabText(0), "SURVEY")
            self.assertEqual(window.tabs.tabText(1), "LIVE MAP")
            self.assertEqual(window.tabs.widget(0).layout().contentsMargins().top(), 0)
            self.assertEqual(window.tabs.widget(1).layout().contentsMargins().top(), 0)
            self.assertIn("QTabWidget#workspaceTabs::tab-bar", style)
            self.assertIn("alignment: left", style)
            self.assertIn("QTabBar#workspaceTabBar::tab:selected", style)
            self.assertIn("QTabBar#workspaceTabBar::tab:first:selected", style)
            self.assertIn("QTabBar#workspaceTabBar::tab:last:selected", style)
            self.assertIn(f"border-bottom: {window.spx(3)}px solid transparent", style)
            self.assertIn("QTabBar#workspaceTabBar::tab:first", style)
            self.assertIn("QTabBar#workspaceTabBar::tab:last", style)
            self.assertIn("border-top-right-radius: 0", style)
            self.assertIn("border-top-left-radius: 0", style)
            self.assertIn("QTabBar#workspaceTabBar", style)
            self.assertIn("padding: 0", style)
            self.assertIn("margin: 0", style)
            self.assertIn("border-bottom:", style)
            self.assertIn("font-weight: 800", style)
        finally:
            window.deleteLater()

    def test_help_center_uses_structured_sections_and_control_assets(self):
        window = WifiHeatmapQtApp()
        try:
            expected_keys = [
                "overview",
                "controls",
                "survey",
                "quality",
                "ap_groups",
                "live_maps",
                "reports",
                "diagnostics",
                "glossary",
            ]
            sections = build_help_sections(window, window.tr)

            self.assertEqual([section.key for section in sections], expected_keys)
            self.assertTrue(all(section.nav_title for section in sections))
            self.assertTrue(all(section.title for section in sections))
            self.assertTrue(all(section.subsections for section in sections))
            self.assertIn("Dashboard Controls", [sub.title for sub in sections[3].subsections])
            self.assertIn("Metadata, Coverage Scope And Channel Overrides", [sub.title for sub in sections[4].subsections])
            self.assertIn("right-click.png", sections[1].body_html)
            self.assertIn("left-click_2.png", sections[1].body_html)
            self.assertIn("Ctrl + Wheel", sections[1].body_html)
            self.assertIn("Shift + Wheel", sections[1].body_html)
            self.assertNotIn("wifi.png", sections[1].body_html)
            self.assertNotIn("middle-click.png", sections[1].body_html)
            self.assertIn("Decision Gates", sections[0].body_html)
            self.assertIn("workflow-grid", sections[0].body_html)
            self.assertIn('width="100%" cellspacing="0"', sections[0].body_html)
            self.assertIn("workflow-gap", sections[0].body_html)
            self.assertIn("callout-table", sections[0].body_html)
            self.assertIn("1. Setup", sections[0].body_html)
            self.assertIn("survey-grid", sections[2].body_html)
            self.assertIn("Relevant SSIDs", sections[2].body_html)
            self.assertIn("not something the user normally opens directly", sections[2].body_html)
            self.assertIn("Field Rule", sections[2].body_html)
            self.assertIn("Dashboard Controls", sections[3].body_html)
            self.assertIn("KPI Meaning", sections[3].body_html)
            self.assertIn("AP Memory Review", sections[3].body_html)
            self.assertIn("Layer 1", sections[3].body_html)
            self.assertIn("Point Quality", sections[3].body_html)
            self.assertIn("APs Without Position", sections[3].body_html)
            self.assertIn("Scalable By Design", sections[3].body_html)
            self.assertIn("Manager Layers", sections[4].body_html)
            self.assertIn("What To Review", sections[4].body_html)
            self.assertIn("BSSID Manager", sections[4].body_html)
            self.assertIn("Core Rule", sections[4].body_html)
            self.assertIn("Input Evidence", sections[4].body_html)
            self.assertIn("Filter The Evidence", sections[4].body_html)
            self.assertIn("Default Map Behavior", sections[4].body_html)
            self.assertIn('workflow-vertical-gap" colspan="3"', sections[4].body_html)
            self.assertNotIn('workflow-vertical-gap"></td><td></td><td></td>', sections[4].body_html)
            self.assertIn("Memory &gt; Confirm Selected", sections[4].body_html)
            self.assertIn("window X behaves like Cancel", sections[4].body_html)
            self.assertIn("Options Panel", sections[5].body_html)
            self.assertIn("Visible Options", sections[5].body_html)
            self.assertIn("Map Reading Rule", sections[5].body_html)
            self.assertIn("Auto labels channel/AP changes", sections[5].body_html)
            self.assertIn("workflow-grid", sections[5].body_html)
            self.assertIn("Export Workflow", sections[6].body_html)
            self.assertIn("What The First Page Represents", sections[6].body_html)
            self.assertIn("Confirm Channel Model", sections[6].body_html)
            self.assertIn("Current AP Channels Behavior", sections[6].body_html)
            self.assertIn("Troubleshooting Patterns", sections[7].body_html)
            self.assertIn("Warning Review Rule", sections[7].body_html)
            self.assertIn("Point Rescan Findings", sections[7].body_html)
            self.assertIn("Interpret Maps Last", sections[7].body_html)
            self.assertIn("Wi-Fi Evidence", sections[8].body_html)
            self.assertIn("AP Model", sections[8].body_html)
            self.assertIn("Memory And Persistence", sections[8].body_html)
            self.assertIn("From Memory", sections[8].body_html)
            self.assertIn("Analysis Channel Override", sections[8].body_html)
            self.assertIn("Map Option Memory", sections[8].body_html)

            html = build_help_html(window, help_palette(window), sections[0])
            self.assertIn("Recommended Survey Workflow", html)
            self.assertIn('name="overview-1"', html)
            self.assertIn("class=\"callout", html)
            self.assertIn("class=\"section-card", html)
            self.assertIn(".survey-grid", html)
            self.assertIn("b, strong", html)
            self.assertNotIn("class=\"eyebrow\"", html)
            self.assertNotIn(">Recommended Workflow</div>", html)

            survey_html = build_help_html(window, help_palette(window), sections[2])
            self.assertIn('name="survey-1"', survey_html)
            self.assertIn('<table class="survey-grid" width="100%" cellspacing="0" cellpadding="0">', survey_html)
            self.assertIn('<table width="100%" cellspacing="0" cellpadding="0">', survey_html)
            self.assertIn('<table class="callout-table" width="100%" cellspacing="0" cellpadding="0">', survey_html)
            self.assertIn('class="callout-accent-good" width="6">&nbsp;</td>', survey_html)
            self.assertNotIn("class=\"pill\"", survey_html)
        finally:
            window.deleteLater()

    def test_help_center_sections_exist_in_supported_languages(self):
        window = WifiHeatmapQtApp()
        try:
            for language in SUPPORTED_LANGUAGES:
                window.change_language(language)
                sections = build_help_sections(window, window.tr)

                self.assertEqual(len(sections), 9)
                self.assertTrue(all(section.nav_title.strip() for section in sections))
                self.assertTrue(all(section.body_html.strip() for section in sections))
                self.assertTrue(all(subsection.title.strip() for section in sections for subsection in section.subsections))
                self.assertIn("control-grid", sections[1].body_html)
                self.assertGreater(sum(section.body_html.count("<h2>") for section in sections), 15)
        finally:
            window.deleteLater()

    def test_localized_compact_buttons_fit_text_in_supported_languages(self):
        window = WifiHeatmapQtApp()
        try:
            for language in SUPPORTED_LANGUAGES:
                window.change_language(language)
                QApplication.processEvents()
                buttons = (
                    window.delete_scale_button,
                    window.manage_relevant_button,
                    window.clear_relevant_button,
                    window.live_pdf_export_button,
                    window.live_update_button,
                )
                for button in buttons:
                    with self.subTest(language=language, text=button.text()):
                        self.assertGreaterEqual(button.minimumWidth(), button.sizeHint().width())
                        self.assertGreaterEqual(button.maximumWidth(), button.sizeHint().width())
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

    def test_ap_manager_marks_and_updates_manual_groups_from_memory(self):
        temp_dir = tempfile.TemporaryDirectory()
        previous = os.environ.get("WIFI_HEATMAP_AP_MEMORY_FILE")
        os.environ["WIFI_HEATMAP_AP_MEMORY_FILE"] = os.path.join(temp_dir.name, "ap_memory.memory")
        ensure_ap_memory_file()
        app = None
        dialog = None
        try:
            bssid = "70:4f:57:aa:bb:10"
            rows = [build_row("p1", "MAIN", bssid, -50, 60, band="5")]
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
            session = SurveySession()
            session.rows = rows
            session.set_ap_groups(
                [
                    build_manual_ap_group(
                        "office-ap",
                        [bssid],
                        alias="Old AP",
                        metadata={"expected_channels": "40"},
                    )
                ],
                update_memory=False,
            )

            app = self.FakeApp(session)
            dialog = APGroupManagerDialog(app)
            group = dialog.get_group_by_id("office-ap")

            self.assertTrue(dialog.group_has_memory_update(group))
            self.assertIn("M", dialog.format_group_status(group))
            self.assertEqual(dialog.format_group_management_state(group), "Memory Update")
            dialog.select_group_by_id("office-ap")
            QApplication.processEvents()
            self.assertIsNotNone(dialog.memory_button.menu())
            self.assertTrue(dialog.update_memory_selected_action.isEnabled())
            self.assertIsNotNone(dialog.alias_button.menu())

            dialog.update_from_memory_for_selected_group()

            self.assertEqual(group["alias"], "Office AP")
            self.assertEqual(group["metadata"]["expected_channels"], "60")
            self.assertFalse(dialog.group_has_memory_update(group))
        finally:
            if dialog is not None:
                dialog.deleteLater()
            if app is not None:
                app.deleteLater()
            if previous is None:
                os.environ.pop("WIFI_HEATMAP_AP_MEMORY_FILE", None)
            else:
                os.environ["WIFI_HEATMAP_AP_MEMORY_FILE"] = previous
            temp_dir.cleanup()

    def test_metadata_analysis_channel_combo_uses_only_observed_group_channels(self):
        app, manager = self.make_ap_manager_dialog()
        try:
            group = manager.get_group_by_id("warning-ap")
            dialog = MetadataDialog(manager, group)
            try:
                combo_24 = dialog.analysis_channel_combos["2.4"]
                combo_5 = dialog.analysis_channel_combos["5"]
                combo_6 = dialog.analysis_channel_combos["6"]

                self.assertEqual(
                    [combo_24.itemData(index) for index in range(combo_24.count())],
                    ["", "1", "6"],
                )
                self.assertTrue(combo_24.isEnabled())
                self.assertFalse(combo_5.isEnabled())
                self.assertFalse(combo_6.isEnabled())
            finally:
                dialog.deleteLater()
        finally:
            manager.deleteLater()
            app.deleteLater()

    def test_metadata_analysis_channel_drops_stale_unobserved_override(self):
        app, manager = self.make_ap_manager_dialog()
        try:
            group = manager.get_group_by_id("neighbor-ap")
            group["metadata"] = {"analysis_channel_override_5": "44"}
            dialog = MetadataDialog(manager, group)
            try:
                combo_5 = dialog.analysis_channel_combos["5"]

                self.assertEqual(
                    [combo_5.itemData(index) for index in range(combo_5.count())],
                    ["", "36"],
                )
                self.assertEqual(combo_5.currentData(), "")
                self.assertNotIn("analysis_channel_override_5", dialog.metadata_values())
            finally:
                dialog.deleteLater()
        finally:
            manager.deleteLater()
            app.deleteLater()

    def test_metadata_coverage_scope_defaults_to_site_wide(self):
        app, manager = self.make_ap_manager_dialog()
        try:
            group = manager.get_group_by_id("warning-ap")
            group.pop("metadata", None)
            dialog = MetadataDialog(manager, group)
            try:
                self.assertEqual(dialog.coverage_scope_combo.currentData(), AP_COVERAGE_SCOPE_GLOBAL)
                self.assertTrue(dialog.coverage_auto_check.isChecked())
                self.assertFalse(dialog.coverage_auto_check.isEnabled())
                self.assertFalse(dialog.coverage_radius_spin.isEnabled())
                values = dialog.metadata_values()
                self.assertNotIn("coverage_scope", values)
                self.assertNotIn("coverage_radius_m", values)
            finally:
                dialog.deleteLater()
        finally:
            manager.deleteLater()
            app.deleteLater()

    def test_metadata_coverage_scope_saves_local_radius(self):
        app, manager = self.make_ap_manager_dialog()
        try:
            group = manager.get_group_by_id("warning-ap")
            group.pop("metadata", None)
            dialog = MetadataDialog(manager, group)
            try:
                self.set_combo_value(dialog.coverage_scope_combo, AP_COVERAGE_SCOPE_LOCAL)
                self.assertTrue(dialog.coverage_auto_check.isChecked())
                self.assertFalse(dialog.coverage_radius_spin.isEnabled())
                dialog.coverage_auto_check.setChecked(False)
                dialog.coverage_radius_spin.setValue(18.5)
                values = dialog.metadata_values()

                self.assertFalse(dialog.coverage_auto_check.isChecked())
                self.assertTrue(dialog.coverage_radius_spin.isEnabled())
                self.assertEqual(values["coverage_scope"], AP_COVERAGE_SCOPE_LOCAL)
                self.assertEqual(values["coverage_radius_m"], "18.5")
            finally:
                dialog.deleteLater()
        finally:
            manager.deleteLater()
            app.deleteLater()

    def test_metadata_coverage_scope_loads_existing_local_metadata(self):
        app, manager = self.make_ap_manager_dialog()
        try:
            group = manager.get_group_by_id("neighbor-ap")
            group["metadata"] = {"coverage_scope": "zone-only", "coverage_radius_m": "12,25"}
            dialog = MetadataDialog(manager, group)
            try:
                values = dialog.metadata_values()

                self.assertEqual(dialog.coverage_scope_combo.currentData(), AP_COVERAGE_SCOPE_LOCAL)
                self.assertFalse(dialog.coverage_auto_check.isChecked())
                self.assertTrue(dialog.coverage_radius_spin.isEnabled())
                self.assertAlmostEqual(dialog.coverage_radius_spin.value(), 12.25, places=2)
                self.assertEqual(values["coverage_scope"], AP_COVERAGE_SCOPE_LOCAL)
                self.assertEqual(values["coverage_radius_m"], "12.25")
            finally:
                dialog.deleteLater()
        finally:
            manager.deleteLater()
            app.deleteLater()

    def test_metadata_coverage_scope_loads_existing_local_auto_area(self):
        app, manager = self.make_ap_manager_dialog()
        try:
            group = manager.get_group_by_id("neighbor-ap")
            group["metadata"] = {"coverage_scope": "local"}
            dialog = MetadataDialog(manager, group)
            try:
                values = dialog.metadata_values()

                self.assertEqual(dialog.coverage_scope_combo.currentData(), AP_COVERAGE_SCOPE_LOCAL)
                self.assertTrue(dialog.coverage_auto_check.isChecked())
                self.assertTrue(dialog.coverage_auto_check.isEnabled())
                self.assertFalse(dialog.coverage_radius_spin.isEnabled())
                self.assertEqual(values["coverage_scope"], AP_COVERAGE_SCOPE_LOCAL)
                self.assertNotIn("coverage_radius_m", values)
            finally:
                dialog.deleteLater()
        finally:
            manager.deleteLater()
            app.deleteLater()

    def test_metadata_coverage_radius_uses_selected_measurement_system(self):
        app, manager = self.make_ap_manager_dialog()
        try:
            app.measurement_system = MEASUREMENT_SYSTEM_IMPERIAL
            group = manager.get_group_by_id("neighbor-ap")
            group["metadata"] = {"coverage_scope": "local", "coverage_radius_m": "10"}
            dialog = MetadataDialog(manager, group)
            try:
                self.assertEqual(dialog.coverage_radius_spin.suffix(), " ft")
                self.assertAlmostEqual(dialog.coverage_radius_spin.value(), 32.81, places=2)

                dialog.coverage_radius_spin.setValue(65.62)
                values = dialog.metadata_values()

                self.assertEqual(values["coverage_scope"], AP_COVERAGE_SCOPE_LOCAL)
                self.assertEqual(values["coverage_radius_m"], "20")
            finally:
                dialog.deleteLater()
        finally:
            manager.deleteLater()
            app.deleteLater()

    def test_metadata_coverage_controls_have_stable_widths(self):
        app, manager = self.make_ap_manager_dialog()
        try:
            group = manager.get_group_by_id("warning-ap")
            group.pop("metadata", None)
            dialog = MetadataDialog(manager, group)
            try:
                controls = (
                    dialog.coverage_scope_combo,
                    dialog.coverage_auto_check,
                    dialog.coverage_radius_spin,
                )
                for control in controls:
                    with self.subTest(control=type(control).__name__):
                        self.assertGreaterEqual(control.minimumWidth(), control.sizeHint().width())
            finally:
                dialog.deleteLater()
        finally:
            manager.deleteLater()
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

            self.assertIn("AP Group: Warning AP (warning-ap)", text)
            self.assertIn("What This Can Mean", text)
            self.assertIn("Recommended Check", text)
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


class SurveySessionWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_new_survey_loads_blank_a4_floorplan_without_dirtying_session(self):
        window = WifiHeatmapQtApp()
        try:
            self.assertTrue(window.new_survey())

            self.assertTrue(window.floorplan_view.has_floorplan())
            self.assertEqual(window.session.metadata.get(DEFAULT_FLOORPLAN_METADATA_KEY), "1")
            self.assertTrue(os.path.exists(window.session.metadata["map_file"]))
            self.assertEqual(window.map_label.text(), window.tr("default_floorplan_name"))
            self.assertFalse(window.session.dirty)

            pixmap = window.floorplan_view.pixmap_item.pixmap()
            self.assertEqual(pixmap.width(), DEFAULT_FLOORPLAN_WIDTH_PX)
            self.assertEqual(pixmap.height(), DEFAULT_FLOORPLAN_HEIGHT_PX)
        finally:
            window.deleteLater()

    def test_saving_default_floorplan_materializes_same_name_png_next_to_csv(self):
        window = WifiHeatmapQtApp()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                self.assertTrue(window.new_survey())
                csv_file = os.path.join(temp_dir, "survey.csv")
                image_file = os.path.join(temp_dir, "survey.png")
                window.session.csv_file = csv_file

                self.assertTrue(window.save_survey())

                self.assertTrue(os.path.exists(csv_file))
                self.assertTrue(os.path.exists(image_file))
                self.assertEqual(window.session.metadata["map_file"], os.path.abspath(image_file))
                self.assertNotIn(DEFAULT_FLOORPLAN_METADATA_KEY, window.session.metadata)
                self.assertEqual(window.map_label.text(), "survey.png")

                with Image.open(image_file) as image:
                    self.assertEqual(image.size, (DEFAULT_FLOORPLAN_WIDTH_PX, DEFAULT_FLOORPLAN_HEIGHT_PX))
                    self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))

                loaded = SurveySession(csv_file)
                self.assertEqual(loaded.metadata["map_file"], os.path.abspath(image_file))
                self.assertNotIn(DEFAULT_FLOORPLAN_METADATA_KEY, loaded.metadata)
        finally:
            window.deleteLater()

    def test_saving_default_floorplan_does_not_overwrite_existing_png_without_confirmation(self):
        window = WifiHeatmapQtApp()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                self.assertTrue(window.new_survey())
                csv_file = os.path.join(temp_dir, "survey.csv")
                image_file = os.path.join(temp_dir, "survey.png")
                Image.new("RGB", (10, 10), "red").save(image_file)
                window.session.csv_file = csv_file

                with patch(
                    "qt_ui.qt_floorplan_workflow.QMessageBox.question",
                    return_value=QMessageBox.StandardButton.Cancel,
                ):
                    self.assertFalse(window.save_survey())

                self.assertFalse(os.path.exists(csv_file))
                with Image.open(image_file) as image:
                    self.assertEqual(image.size, (10, 10))
                    self.assertEqual(image.getpixel((0, 0)), (255, 0, 0))
                self.assertEqual(window.session.metadata.get(DEFAULT_FLOORPLAN_METADATA_KEY), "1")
        finally:
            window.deleteLater()

    def test_loaded_plan_replaces_default_floorplan_without_same_name_png(self):
        window = WifiHeatmapQtApp()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                real_plan = os.path.join(temp_dir, "real_plan.png")
                csv_file = os.path.join(temp_dir, "survey.csv")
                Image.new("RGB", (120, 90), "white").save(real_plan)

                self.assertTrue(window.new_survey())
                window.load_plan_file(real_plan, save_metadata=True)
                window.session.csv_file = csv_file

                self.assertTrue(window.save_survey())

                self.assertEqual(window.session.metadata["map_file"], os.path.abspath(real_plan))
                self.assertNotIn(DEFAULT_FLOORPLAN_METADATA_KEY, window.session.metadata)
                self.assertFalse(os.path.exists(os.path.join(temp_dir, "survey.png")))
                self.assertEqual(window.map_label.text(), "real_plan.png")
        finally:
            window.deleteLater()


class PointCaptureWorkflowTests(unittest.TestCase):
    class FakeStatus:
        def __init__(self):
            self.messages = []

        def showMessage(self, message):
            self.messages.append(message)

    class FakePointsTable:
        def __init__(self):
            self.selected_rows = []

        def selectRow(self, row):
            self.selected_rows.append(row)

    class FakePointCaptureApp(PointCaptureMixin):
        def __init__(self):
            self.session = SurveySession()
            self.relevant_ssids = {"MAIN"}
            self.status = PointCaptureWorkflowTests.FakeStatus()
            self.points_table = PointCaptureWorkflowTests.FakePointsTable()
            self.refresh_session_labels_count = 0
            self.refresh_points_table_count = 0
            self.live_preview_updates = 0

        def tr(self, key, **kwargs):
            return translate("en", key, **kwargs)

        def refresh_session_labels(self):
            self.refresh_session_labels_count += 1

        def refresh_points_table(self):
            self.refresh_points_table_count += 1

        def maybe_update_live_preview(self):
            self.live_preview_updates += 1

    def test_save_survey_point_persists_aggregates_raw_rows_and_relevant_flags(self):
        app = self.FakePointCaptureApp()
        networks = [
            {
                "ssid": "MAIN",
                "bssid": "70:4f:57:aa:bb:10",
                "signal_percent": "80",
                "signal_dbm": -50,
                "signal_median_dbm": -51,
                "signal_max_dbm": -48,
                "signal_min_dbm": -54,
                "channel": "6",
                "channel_width_mhz": "20",
                "radio": "802.11ax",
                "frequency_mhz": "2437",
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
                        "backend": "lswifi",
                    }
                ],
            },
            {
                "ssid": "GUEST",
                "bssid": "80:11:22:33:44:10",
                "signal_percent": "60",
                "signal_dbm": -65,
                "channel": "36",
                "channel_width_mhz": "80",
                "radio": "802.11ac",
                "frequency_mhz": "5180",
                "raw_samples": [
                    {
                        "scan_attempt": "1",
                        "ssid": "GUEST",
                        "bssid": "80:11:22:33:44:10",
                        "signal_percent": "60",
                        "signal_dbm": "-65",
                        "channel": "36",
                        "channel_width_mhz": "80",
                        "radio": "802.11ac",
                        "frequency_mhz": "5180",
                        "backend": "lswifi",
                    }
                ],
            },
        ]

        app.save_survey_point(10, 20, networks)

        self.assertEqual(len(app.session.rows), 2)
        self.assertEqual([row["is_relevant"] for row in app.session.rows], ["1", "0"])
        self.assertEqual(app.session.rows[0]["frequency_mhz"], "2437")
        self.assertEqual(app.session.rows[1]["band"], "5")
        self.assertEqual(len(app.session.raw_scan_rows), 2)
        self.assertEqual({row["backend"] for row in app.session.raw_scan_rows}, {"lswifi"})
        self.assertEqual({row["point_id"] for row in app.session.raw_scan_rows}, {app.session.rows[0]["point_id"]})
        self.assertTrue(app.session.dirty)
        self.assertEqual(app.refresh_session_labels_count, 1)
        self.assertEqual(app.refresh_points_table_count, 1)
        self.assertEqual(app.live_preview_updates, 1)
        self.assertEqual(app.points_table.selected_rows, [0])
        self.assertIn("Point saved", app.status.messages[-1])


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
            self.assertLess(expanded_geometry.width(), window.live_view_container.width() * 0.7)

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
            self.assertEqual(grid_position(window.live_survey_bounds_check), (10, 0, 1, 2))
            self.assertEqual(window.live_band_combo.width(), window.live_interpolation_combo.width())
            self.assertEqual(window.live_band_combo.width(), window.live_max_distance_spin.width())
            required_group_width = window.live_ap_group_combo.fontMetrics().horizontalAdvance(
                window.tr("all_ap_groups_option")
            )
            self.assertGreater(window.live_ap_group_combo.width(), required_group_width + window.spx(50))
            self.assertLess(window.live_band_combo.width(), window.spx(300))
            self.assertFalse(window.live_band_combo.isHidden())
            self.assertFalse(window.live_aggregation_combo.isHidden())
            self.assertFalse(window.live_color_scale_combo.isHidden())
            self.assertFalse(window.live_interpolation_combo.isHidden())
            self.assertFalse(window.live_max_distance_spin.isHidden())
            self.assertFalse(window.live_smoothing_spin.isHidden())
            self.assertFalse(window.live_usable_check.isHidden())
            self.assertFalse(window.live_survey_bounds_check.isHidden())
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
            self.assertEqual(grid_position(window.live_checkbox_separator), (7, 0, 1, 2))
            self.assertEqual(grid_position(window.live_survey_bounds_check), (8, 0, 1, 2))
            self.assertFalse(window.live_band_combo.isHidden())
            self.assertFalse(window.live_color_scale_combo.isHidden())
            self.assertFalse(window.live_interference_mode_combo.isHidden())
            self.assertFalse(window.live_interpolation_combo.isHidden())
            self.assertFalse(window.live_max_distance_spin.isHidden())
            self.assertFalse(window.live_smoothing_spin.isHidden())
            self.assertTrue(window.live_aggregation_combo.isHidden())
            self.assertTrue(window.live_usable_check.isHidden())
            self.assertFalse(window.live_survey_bounds_check.isHidden())
            self.assertTrue(window.live_ap_group_combo.isHidden())
            self.assertTrue(window.live_point_labels_combo.isHidden())
            self.assertFalse(window.live_options_separator.isHidden())
            self.assertFalse(window.live_checkbox_separator.isHidden())

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
            self.assertTrue(window.live_survey_bounds_check.isHidden())
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
            self.assertTrue(window.live_survey_bounds_check.isHidden())
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
            window.live_survey_bounds_check.blockSignals(True)
            window.live_survey_bounds_check.setChecked(True)
            window.live_survey_bounds_check.blockSignals(False)
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
            self.assertTrue(window.live_survey_bounds_check.isChecked())

            set_map_type("interference")
            self.assertEqual(window.current_combo_value(window.live_band_combo), "5")
            self.assertEqual(window.current_combo_value(window.live_color_scale_combo), "fixed")
            self.assertEqual(window.current_combo_value(window.live_interference_mode_combo), "all")
            self.assertEqual(window.current_combo_value(window.live_interpolation_combo), "rbf")
            self.assertEqual(window.live_smoothing_spin.value(), 2.0)
            self.assertFalse(window.live_survey_bounds_check.isChecked())

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
            self.assertEqual(window.live_smoothing_spin.value(), 5.0)
            self.assertEqual(window.current_live_max_distance_px(), 260)
            self.assertFalse(window.live_usable_check.isChecked())
            self.assertFalse(window.live_survey_bounds_check.isChecked())
            set_map_type("channel")
            self.assertEqual(window.current_combo_value(window.live_point_labels_combo), "auto")
        finally:
            window.deleteLater()

    def test_live_max_distance_uses_selected_measurement_system(self):
        window = WifiHeatmapQtApp()
        try:
            class Session:
                metadata = {"px_per_meter": "10"}

            window.session = Session()
            window.measurement_system = MEASUREMENT_SYSTEM_METRIC
            self.assertEqual(
                window.default_live_option_state("signal")["max_distance_px"],
                HEATMAP_MAX_DISTANCE_PX,
            )
            window.set_live_max_distance_px_silent(100)

            self.assertEqual(window.live_max_distance_label.text(), "Max Distance (m)")
            self.assertAlmostEqual(window.live_max_distance_spin.value(), 10.0)
            self.assertEqual(window.live_max_distance_spin.suffix(), " m")
            self.assertEqual(window.current_live_max_distance_px(), 100)

            window.measurement_system = MEASUREMENT_SYSTEM_IMPERIAL
            window.set_live_max_distance_px_silent(100)

            self.assertEqual(window.live_max_distance_label.text(), "Max Distance (ft)")
            self.assertAlmostEqual(window.live_max_distance_spin.value(), 32.8, places=1)
            self.assertEqual(window.live_max_distance_spin.suffix(), " ft")
            self.assertEqual(window.current_live_max_distance_px(), 100)
        finally:
            window.deleteLater()

    def test_live_max_distance_default_uses_survey_point_spacing_when_scaled(self):
        window = WifiHeatmapQtApp()
        try:
            class Session:
                metadata = {"px_per_meter": "10"}
                rows = [
                    {"x": "0", "y": "0"},
                    {"x": "20", "y": "0"},
                    {"x": "45", "y": "0"},
                    {"x": "70", "y": "0"},
                    {"x": "95", "y": "0"},
                ]

            window.session = Session()

            self.assertEqual(window.default_live_option_state("signal")["max_distance_px"], 40)
        finally:
            window.deleteLater()

    def test_measurement_system_change_clears_existing_scale_after_confirmation(self):
        window = WifiHeatmapQtApp()
        try:
            class Session:
                metadata = {"px_per_meter": "10"}
                dirty = False

            window.session = Session()
            window.measurement_system = MEASUREMENT_SYSTEM_METRIC
            window.set_live_max_distance_px_silent(100)

            with (
                patch("qt_ui.qt_workspace_settings.save_measurement_system", return_value=True),
                patch.object(window, "confirm_measurement_system_scale_reset", return_value=True),
                patch.object(window, "refresh_session_labels") as refresh_mock,
                patch.object(window, "maybe_update_live_preview") as live_mock,
            ):
                changed = window.change_measurement_system(MEASUREMENT_SYSTEM_IMPERIAL)

            self.assertTrue(changed)
            self.assertEqual(window.measurement_system, MEASUREMENT_SYSTEM_IMPERIAL)
            self.assertNotIn("px_per_meter", window.session.metadata)
            self.assertTrue(window.session.dirty)
            self.assertEqual(window.live_max_distance_label.text(), "Max Distance (px)")
            self.assertEqual(window.live_max_distance_spin.suffix(), " px")
            self.assertEqual(window.current_live_max_distance_px(), 100)
            refresh_mock.assert_called_once()
            live_mock.assert_called_once()
        finally:
            window.deleteLater()

    def test_measurement_system_change_cancel_keeps_existing_scale(self):
        window = WifiHeatmapQtApp()
        try:
            class Session:
                metadata = {"px_per_meter": "10"}
                dirty = False

            window.session = Session()
            window.measurement_system = MEASUREMENT_SYSTEM_METRIC

            with (
                patch("qt_ui.qt_workspace_settings.save_measurement_system") as save_mock,
                patch.object(window, "confirm_measurement_system_scale_reset", return_value=False),
                patch.object(window, "maybe_update_live_preview") as live_mock,
            ):
                changed = window.change_measurement_system(MEASUREMENT_SYSTEM_IMPERIAL)

            self.assertFalse(changed)
            self.assertEqual(window.measurement_system, MEASUREMENT_SYSTEM_METRIC)
            self.assertEqual(window.session.metadata.get("px_per_meter"), "10")
            self.assertFalse(window.session.dirty)
            save_mock.assert_not_called()
            live_mock.assert_not_called()
        finally:
            window.deleteLater()
