import json
import os
import sys
from pathlib import Path

try:
    from PySide6.QtCore import Qt, QThread
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSplitter,
        QStackedWidget,
        QStatusBar,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QToolBar,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, normalize_language, translate
from quality_engine import (
    QUALITY_GOOD,
    QUALITY_LOW_CONFIDENCE,
    QUALITY_MISSING_RELEVANT,
    QUALITY_SPARSE_DATA,
    QUALITY_UNSTABLE_SIGNAL,
    evaluate_point_quality,
)
from qt_ap_groups import open_qt_ap_group_manager
from qt_floorplan import FloorplanView
from qt_point_workflow import MissingRelevantNetworksDialog, RelevantNetworksDialog, WifiScanWorker
from survey_store import SurveyFormatError, SurveySession
from wifi_scanner import get_connected_ssid


RELEVANT_SSIDS_METADATA_KEY = "relevant_ssids"
KNOWN_SSIDS_METADATA_KEY = "known_ssids"


class WifiHeatmapQtApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.language = DEFAULT_LANGUAGE
        self.session = None
        self.relevant_ssids = set()
        self.known_ssids = set()
        self.scan_thread = None
        self.scan_worker = None
        self.scan_in_progress = False
        self.pending_scan_point = None
        self.last_scan_backend_used = "-"

        self.setWindowTitle(self.tr("app_title"))
        self.resize(1400, 900)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.start_page = self.build_start_page()
        self.workspace_page = self.build_workspace_page()
        self.stack.addWidget(self.start_page)
        self.stack.addWidget(self.workspace_page)

        self.apply_styles()
        self.retranslate()
        self.show_start_page()

    def tr(self, key, **kwargs):
        return translate(self.language, key, **kwargs)

    def build_start_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(48, 40, 48, 32)

        top_row = QHBoxLayout()
        top_row.addStretch(1)
        self.start_language_label = QLabel()
        self.start_language_combo = QComboBox()
        self.start_language_combo.addItems(SUPPORTED_LANGUAGES)
        self.start_language_combo.setCurrentText(self.language.upper())
        self.start_language_combo.currentTextChanged.connect(self.change_language)
        top_row.addWidget(self.start_language_label)
        top_row.addWidget(self.start_language_combo)
        outer.addLayout(top_row)

        outer.addStretch(1)

        panel = QFrame()
        panel.setObjectName("startPanel")
        panel_layout = QGridLayout(panel)
        panel_layout.setContentsMargins(32, 32, 32, 32)
        panel_layout.setHorizontalSpacing(28)
        panel_layout.setVerticalSpacing(14)

        title_box = QVBoxLayout()
        self.start_title = QLabel()
        self.start_title.setObjectName("startTitle")
        self.start_subtitle = QLabel()
        self.start_subtitle.setObjectName("mutedText")
        self.start_subtitle.setWordWrap(True)
        self.qt_badge = QLabel()
        self.qt_badge.setObjectName("badge")
        title_box.addWidget(self.start_title)
        title_box.addWidget(self.start_subtitle)
        title_box.addSpacing(12)
        title_box.addWidget(self.qt_badge, 0, Qt.AlignmentFlag.AlignLeft)
        panel_layout.addLayout(title_box, 0, 0, 1, 2)

        action_box = QVBoxLayout()
        self.new_button = QPushButton()
        self.open_button = QPushButton()
        self.exit_button = QPushButton()
        self.new_button.clicked.connect(self.new_survey)
        self.open_button.clicked.connect(self.open_survey)
        self.exit_button.clicked.connect(self.close)
        for button in (self.new_button, self.open_button, self.exit_button):
            button.setMinimumHeight(42)
            action_box.addWidget(button)
        action_box.addStretch(1)
        panel_layout.addLayout(action_box, 1, 0)

        info_box = QVBoxLayout()
        self.start_hint_title = QLabel()
        self.start_hint_title.setObjectName("sectionTitle")
        self.start_hint_text = QLabel()
        self.start_hint_text.setObjectName("mutedText")
        self.start_hint_text.setWordWrap(True)
        info_box.addWidget(self.start_hint_title)
        info_box.addWidget(self.start_hint_text)
        info_box.addStretch(1)
        panel_layout.addLayout(info_box, 1, 1)

        outer.addWidget(panel, 0, Qt.AlignmentFlag.AlignCenter)
        outer.addStretch(1)

        self.copyright_label = QLabel()
        self.copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.copyright_label.setObjectName("mutedText")
        outer.addWidget(self.copyright_label)
        return page

    def build_workspace_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(self.toolbar)

        self.new_action = QAction(self)
        self.open_action = QAction(self)
        self.save_action = QAction(self)
        self.load_plan_action = QAction(self)
        self.zoom_out_action = QAction("-", self)
        self.zoom_in_action = QAction("+", self)
        self.fit_action = QAction(self)
        self.ap_groups_action = QAction(self)
        self.quality_action = QAction(self)
        self.generate_action = QAction(self)
        self.new_action.triggered.connect(self.new_survey)
        self.open_action.triggered.connect(self.open_survey)
        self.save_action.triggered.connect(self.save_survey)
        self.load_plan_action.triggered.connect(self.load_plan)
        self.zoom_out_action.triggered.connect(self.zoom_out)
        self.zoom_in_action.triggered.connect(self.zoom_in)
        self.fit_action.triggered.connect(self.fit_floorplan)
        self.ap_groups_action.triggered.connect(self.open_ap_group_manager)
        self.quality_action.triggered.connect(self.show_not_migrated_message)
        self.generate_action.triggered.connect(self.show_not_migrated_message)

        for action in (
            self.new_action,
            self.open_action,
            self.save_action,
            self.load_plan_action,
        ):
            self.toolbar.addAction(action)
        self.toolbar.addSeparator()
        for action in (self.zoom_out_action, self.zoom_in_action, self.fit_action):
            self.toolbar.addAction(action)
        self.toolbar.addSeparator()
        for action in (self.ap_groups_action, self.quality_action, self.generate_action):
            self.toolbar.addAction(action)

        self.toolbar.addSeparator()
        self.toolbar.addWidget(QLabel("  "))
        self.workspace_language_label = QLabel()
        self.workspace_language_combo = QComboBox()
        self.workspace_language_combo.addItems(SUPPORTED_LANGUAGES)
        self.workspace_language_combo.setCurrentText(self.language.upper())
        self.workspace_language_combo.currentTextChanged.connect(self.change_language)
        self.toolbar.addWidget(self.workspace_language_label)
        self.toolbar.addWidget(self.workspace_language_combo)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_survey_tab(), "")
        self.tabs.addTab(self.build_live_tab(), "")
        layout.addWidget(self.tabs)

        footer = QFrame()
        footer.setObjectName("footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 6, 12, 6)
        self.footer_label = QLabel()
        self.footer_label.setObjectName("mutedText")
        footer_layout.addWidget(self.footer_label)
        layout.addWidget(footer)

        return page

    def build_survey_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        summary = QFrame()
        summary.setObjectName("summaryPanel")
        grid = QGridLayout(summary)
        grid.setContentsMargins(16, 14, 16, 14)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(8)

        self.csv_label = QLabel()
        self.map_label = QLabel()
        self.points_label = QLabel()
        self.raw_rows_label = QLabel()
        self.ap_groups_label = QLabel()
        self.relevant_label = QLabel()
        for row, label in enumerate((
            self.csv_label,
            self.map_label,
            self.points_label,
            self.raw_rows_label,
            self.ap_groups_label,
            self.relevant_label,
        )):
            grid.addWidget(label, row // 2, row % 2)
        layout.addWidget(summary)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.floorplan_view = FloorplanView()
        self.floorplan_view.ap_tooltip_formatter = self.format_ap_position_tooltip
        self.floorplan_view.surveyPointRequested.connect(self.create_point_from_floorplan)
        self.floorplan_view.apPositionPicked.connect(self.save_ap_position)
        self.floorplan_view.apPositionCancelled.connect(self.cancel_ap_positioning)
        splitter.addWidget(self.floorplan_view)

        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(8)

        self.points_table = QTableWidget(0, 8)
        self.points_table.setAlternatingRowColors(True)
        self.points_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.points_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.points_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.points_table.horizontalHeader().setStretchLastSection(True)
        self.points_table.itemSelectionChanged.connect(self.update_point_action_state)
        self.points_table.itemDoubleClicked.connect(lambda _item: self.focus_selected_point())
        table_layout.addWidget(self.points_table)

        point_buttons = QHBoxLayout()
        self.focus_point_button = QPushButton()
        self.delete_selected_button = QPushButton()
        self.delete_last_button = QPushButton()
        self.focus_point_button.clicked.connect(self.focus_selected_point)
        self.delete_selected_button.clicked.connect(self.delete_selected_point)
        self.delete_last_button.clicked.connect(self.delete_last_point)
        point_buttons.addWidget(self.focus_point_button)
        point_buttons.addWidget(self.delete_selected_button)
        point_buttons.addWidget(self.delete_last_button)
        point_buttons.addStretch(1)
        table_layout.addLayout(point_buttons)

        splitter.addWidget(table_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)
        return tab

    def build_live_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        self.live_title = QLabel()
        self.live_title.setObjectName("sectionTitle")
        self.live_body = QLabel()
        self.live_body.setObjectName("mutedText")
        self.live_body.setWordWrap(True)
        layout.addWidget(self.live_title)
        layout.addWidget(self.live_body)
        layout.addStretch(1)
        return tab

    def apply_styles(self):
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #f6f7f9;
                color: #1f2933;
                font-family: Segoe UI;
                font-size: 10.5pt;
            }
            QFrame#startPanel, QFrame#summaryPanel {
                background: #ffffff;
                border: 1px solid #d7dde3;
                border-radius: 8px;
            }
            QFrame#footer {
                background: #ffffff;
                border-top: 1px solid #d7dde3;
            }
            QLabel#startTitle {
                font-size: 25pt;
                font-weight: 700;
                color: #243447;
            }
            QLabel#sectionTitle {
                font-size: 13pt;
                font-weight: 600;
                color: #243447;
            }
            QLabel#mutedText {
                color: #586575;
            }
            QLabel#badge {
                color: #155724;
                background: #d4edda;
                border: 1px solid #b8dfc2;
                border-radius: 5px;
                padding: 5px 8px;
            }
            QPushButton {
                min-width: 240px;
                padding: 8px 12px;
            }
            QToolBar {
                background: #ffffff;
                border-bottom: 1px solid #d7dde3;
                spacing: 8px;
                padding: 6px;
            }
            QTableWidget {
                background: #ffffff;
                alternate-background-color: #f1f4f7;
                gridline-color: #d7dde3;
            }
            QHeaderView::section {
                background: #e9edf2;
                padding: 5px;
                border: 0;
                border-right: 1px solid #d7dde3;
                font-weight: 600;
            }
            """
        )

    def retranslate(self):
        self.setWindowTitle(self.tr("app_title"))
        self.start_language_label.setText(self.tr("language"))
        self.workspace_language_label.setText(self.tr("language"))
        self.start_title.setText(self.tr("app_title"))
        self.start_subtitle.setText(self.tr("start_subtitle"))
        self.qt_badge.setText(self.tr("qt_migration_badge"))
        self.start_hint_title.setText(self.tr("qt_start_hint_title"))
        self.start_hint_text.setText(self.tr("qt_start_hint"))
        self.copyright_label.setText(self.tr("copyright"))
        self.new_button.setText(self.tr("new_survey"))
        self.open_button.setText(self.tr("open_existing_survey"))
        self.exit_button.setText(self.tr("exit"))
        self.new_action.setText(self.tr("new_survey"))
        self.open_action.setText(self.tr("open_existing_survey"))
        self.save_action.setText(self.tr("save"))
        self.load_plan_action.setText(self.tr("load_plan"))
        self.fit_action.setText(self.tr("fit"))
        self.ap_groups_action.setText(self.tr("ap_groups_title"))
        self.quality_action.setText(self.tr("quality_dashboard_title"))
        self.generate_action.setText(self.tr("generate_heatmap"))
        self.focus_point_button.setText(self.tr("go_to_point"))
        self.delete_selected_button.setText(self.tr("delete_selected"))
        self.delete_last_button.setText(self.tr("delete_last"))
        self.tabs.setTabText(0, self.tr("survey_tab"))
        self.tabs.setTabText(1, self.tr("live_map_tab"))
        self.live_title.setText(self.tr("qt_live_placeholder_title"))
        self.live_body.setText(self.tr("qt_live_placeholder_body"))
        self.points_table.setHorizontalHeaderLabels([
            "#",
            "X",
            "Y",
            self.tr("qt_table_best_dbm"),
            self.tr("quality"),
            self.tr("qt_table_networks"),
            self.tr("rows"),
            self.tr("qt_table_timestamp"),
        ])
        self.refresh_session_labels()

    def change_language(self, value):
        language = normalize_language(value)
        if language == self.language:
            return

        self.language = language
        self.start_language_combo.blockSignals(True)
        self.workspace_language_combo.blockSignals(True)
        self.start_language_combo.setCurrentText(language.upper())
        self.workspace_language_combo.setCurrentText(language.upper())
        self.start_language_combo.blockSignals(False)
        self.workspace_language_combo.blockSignals(False)
        self.retranslate()
        if self.session is not None:
            self.floorplan_view.set_ap_groups(self.session.get_ap_groups())

    def show_start_page(self):
        self.stack.setCurrentWidget(self.start_page)
        self.toolbar.setVisible(False)
        self.status.clearMessage()

    def show_workspace_page(self):
        self.stack.setCurrentWidget(self.workspace_page)
        self.toolbar.setVisible(True)
        self.refresh_session_labels()
        self.refresh_points_table()

    def new_survey(self):
        if not self.confirm_switch_survey():
            return
        self.session = SurveySession()
        self.load_session_ssid_state()
        self.floorplan_view.clear_floorplan()
        self.show_workspace_page()

    def open_survey(self):
        if not self.confirm_switch_survey():
            return

        csv_file, _selected_filter = QFileDialog.getOpenFileName(
            self,
            self.tr("open_existing_survey"),
            "",
            self.tr("qt_survey_file_filter"),
        )
        if not csv_file:
            return

        try:
            self.session = SurveySession(csv_file)
        except SurveyFormatError as exc:
            self.show_survey_format_error(str(exc))
            return

        self.load_session_ssid_state()
        self.show_workspace_page()
        self.load_saved_plan()
        self.status.showMessage(self.tr("active_survey", name=self.session_display_name()))

    def save_survey(self):
        if self.session is None:
            return False

        csv_file = self.session.csv_file
        if not csv_file:
            csv_file, _selected_filter = QFileDialog.getSaveFileName(
                self,
                self.tr("save"),
                "",
                self.tr("qt_survey_file_filter"),
            )
            if not csv_file:
                return False
            if Path(csv_file).suffix.lower() != ".csv":
                csv_file = f"{csv_file}.csv"

        self.session.save(csv_file)
        self.refresh_session_labels()
        self.status.showMessage(self.tr("survey_saved", name=self.session.display_name))
        return True

    def load_plan(self):
        if self.session is None:
            self.new_survey()
            if self.session is None:
                return

        file_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            self.tr("select_plan_title"),
            "",
            self.tr("qt_plan_file_filter"),
        )
        if not file_path:
            return

        self.load_plan_file(file_path, save_metadata=True)

    def load_saved_plan(self):
        if self.session is None:
            return

        map_file = self.session.metadata.get("map_file", "")
        if not map_file:
            self.floorplan_view.clear_floorplan()
            return

        if os.path.exists(map_file):
            self.load_plan_file(map_file, save_metadata=False)
            return

        QMessageBox.warning(
            self,
            self.tr("map_not_found_title"),
            self.tr("map_not_found", path=map_file),
        )

    def load_plan_file(self, file_path, save_metadata=False):
        if self.session is None:
            return

        try:
            self.floorplan_view.load_floorplan(file_path)
        except Exception as exc:
            QMessageBox.warning(
                self,
                self.tr("warning"),
                str(exc),
            )
            return

        if save_metadata:
            self.session.update_metadata({"map_file": os.path.abspath(file_path)})

        self.floorplan_view.set_points(self.session.get_point_summaries())
        self.floorplan_view.set_ap_groups(self.session.get_ap_groups())
        self.refresh_session_labels()
        point_count = len(self.session.get_point_summaries())
        if point_count:
            self.status.showMessage(
                self.tr("map_loaded_points", count=point_count, name=self.session_display_name())
            )
        else:
            self.status.showMessage(self.tr("map_loaded", name=self.session_display_name()))

    def zoom_in(self):
        self.floorplan_view.zoom_in()
        self.status.showMessage(self.tr("zoom", zoom=self.floorplan_view.zoom_level))

    def zoom_out(self):
        self.floorplan_view.zoom_out()
        self.status.showMessage(self.tr("zoom", zoom=self.floorplan_view.zoom_level))

    def fit_floorplan(self):
        self.floorplan_view.fit_to_view()
        self.status.showMessage(self.tr("zoom", zoom=self.floorplan_view.zoom_level))

    def confirm_switch_survey(self):
        if self.session is None or not self.session.dirty:
            return True

        response = QMessageBox.question(
            self,
            self.tr("unsaved_changes_title"),
            self.tr("unsaved_changes"),
            (
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel
            ),
            QMessageBox.StandardButton.Save,
        )
        if response == QMessageBox.StandardButton.Save:
            return self.save_survey()
        if response == QMessageBox.StandardButton.Discard:
            return True
        return False

    def closeEvent(self, event):
        if self.scan_in_progress:
            x, y = self.pending_scan_point or ("-", "-")
            self.status.showMessage(self.tr("scanning", x=x, y=y))
            event.ignore()
            return

        if self.confirm_switch_survey():
            event.accept()
        else:
            event.ignore()

    def show_survey_format_error(self, error_key):
        message_key = {
            "raw_scan_file": "raw_scan_file_selected",
            "invalid_raw_scan_format": "invalid_raw_scan_format",
            "missing_survey_file": "invalid_survey_format",
        }.get(error_key, "invalid_survey_format")
        QMessageBox.critical(
            self,
            self.tr("invalid_survey_title"),
            self.tr(message_key),
        )

    def show_not_migrated_message(self):
        QMessageBox.information(
            self,
            self.tr("qt_not_migrated_title"),
            self.tr("qt_not_migrated_message"),
        )

    def load_session_ssid_state(self):
        self.relevant_ssids = self.load_relevant_ssids()
        self.known_ssids = self.load_known_ssids()

    def load_relevant_ssids(self):
        if self.session is None:
            return set()

        return load_json_string_set(self.session.metadata.get(RELEVANT_SSIDS_METADATA_KEY))

    def load_known_ssids(self):
        if self.session is None:
            return set(self.relevant_ssids)

        known = load_json_string_set(self.session.metadata.get(KNOWN_SSIDS_METADATA_KEY))
        return known or set(self.relevant_ssids)

    def save_known_ssids(self):
        if self.session is None:
            return

        serialized = json.dumps(sorted(self.known_ssids), ensure_ascii=False)
        self.session.update_metadata({KNOWN_SSIDS_METADATA_KEY: serialized})

    def set_relevant_ssids(self, ssids):
        if self.session is None:
            return

        self.relevant_ssids = {
            str(ssid).strip()
            for ssid in ssids
            if str(ssid).strip()
        }
        serialized = json.dumps(sorted(self.relevant_ssids), ensure_ascii=False)
        self.session.update_metadata({RELEVANT_SSIDS_METADATA_KEY: serialized})
        self.known_ssids |= self.relevant_ssids
        self.refresh_session_labels()

    def create_point_from_floorplan(self, x, y):
        if self.session is None:
            self.new_survey()
            if self.session is None:
                return

        if not self.floorplan_view.has_floorplan():
            QMessageBox.warning(self, self.tr("warning"), self.tr("load_plan_first"))
            return

        if self.scan_in_progress:
            return

        self.start_wifi_scan(x, y)

    def start_wifi_scan(self, x, y):
        self.pending_scan_point = (int(x), int(y))
        self.set_scan_busy(True, self.tr("scanning", x=int(x), y=int(y)))

        thread = QThread(self)
        worker = WifiScanWorker("auto")
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self.finish_wifi_scan)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(self.fail_wifi_scan)
        worker.failed.connect(thread.quit)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self.scan_thread = thread
        self.scan_worker = worker
        thread.start()

    def finish_wifi_scan(self, networks, backend_used):
        x, y = self.pending_scan_point or (None, None)
        self.scan_thread = None
        self.scan_worker = None
        self.set_scan_busy(False)
        self.last_scan_backend_used = backend_used

        if x is None or y is None:
            return

        action = self.validate_relevant_networks(networks)
        if action == "retry":
            self.start_wifi_scan(x, y)
            return
        if action == "cancel":
            self.pending_scan_point = None
            self.status.showMessage(self.tr("cancelled"))
            return

        self.pending_scan_point = None
        self.save_survey_point(x, y, networks)

    def fail_wifi_scan(self, message):
        self.scan_thread = None
        self.scan_worker = None
        self.set_scan_busy(False)
        self.pending_scan_point = None
        QMessageBox.critical(self, self.tr("error"), message)

    def set_scan_busy(self, is_busy, message=None):
        self.scan_in_progress = is_busy
        if is_busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            if QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()

        if message:
            self.status.showMessage(message)
        self.refresh_session_labels()

    def validate_relevant_networks(self, networks):
        detected_ssids = self.get_detected_ssids(networks)
        if not detected_ssids:
            return "keep"

        if not self.relevant_ssids and not self.known_ssids:
            dialog = RelevantNetworksDialog(
                self,
                detected_ssids,
                self.tr("relevant_networks_title"),
                self.tr("relevant_networks_first_message"),
                connected_ssid=get_connected_ssid(),
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return "cancel"

            self.set_relevant_ssids(dialog.selected_ssids())
            self.known_ssids |= detected_ssids
            self.save_known_ssids()
            return "keep"

        missing_ssids = sorted(self.relevant_ssids - detected_ssids, key=str.casefold)
        if self.relevant_ssids and missing_ssids:
            dialog = MissingRelevantNetworksDialog(self, missing_ssids)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return "cancel"
            return dialog.action

        new_ssids = sorted(detected_ssids - self.known_ssids, key=str.casefold)
        if new_ssids:
            dialog = RelevantNetworksDialog(
                self,
                new_ssids,
                self.tr("new_relevant_networks_title"),
                self.tr("new_relevant_networks_message"),
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return "cancel"

            selected = dialog.selected_ssids()
            if selected:
                self.set_relevant_ssids(self.relevant_ssids | selected)
            self.known_ssids |= detected_ssids
            self.save_known_ssids()

        return "keep"

    def get_detected_ssids(self, networks):
        return {
            str(network.get("ssid", "")).strip()
            for network in networks or []
            if str(network.get("ssid", "")).strip()
        }

    def save_survey_point(self, x, y, networks):
        if self.session is None:
            return

        if not networks:
            QMessageBox.critical(self, self.tr("error"), self.tr("no_networks_found"))
            return

        timestamp = self.session.add_points(
            x,
            y,
            networks,
            raw_networks=networks,
            relevant_ssids=self.relevant_ssids,
        )
        self.refresh_session_labels()
        self.refresh_points_table()
        self.status.showMessage(self.tr("point_saved", x=x, y=y, count=len(networks)))
        self.points_table.selectRow(0)

    def open_ap_group_manager(self):
        if self.session is None:
            return

        if open_qt_ap_group_manager(self):
            self.refresh_session_labels()
            self.refresh_points_table()
            if not self.floorplan_view.pending_ap_position_group_id:
                self.status.showMessage(self.tr("ap_groups_saved"))

    def start_ap_positioning(self, group_id):
        if self.session is None:
            return False

        if not self.floorplan_view.has_floorplan():
            QMessageBox.warning(self, self.tr("warning"), self.tr("load_plan_first"))
            return False

        label = self.get_ap_group_display_name(group_id)
        started = self.floorplan_view.start_ap_position_pick(group_id, label)
        if started:
            self.tabs.setCurrentIndex(0)
            self.status.showMessage(self.tr("ap_position_pick", group=label))
        return started

    def save_ap_position(self, group_id, x, y):
        if self.session is None:
            return

        groups = self.session.get_ap_groups()
        updated = False
        for group in groups:
            if str(group.get("group_id", "")) == str(group_id):
                group["position"] = {"x": int(x), "y": int(y)}
                group["locked"] = True
                updated = True
                break

        if not updated:
            QMessageBox.warning(self, self.tr("warning"), self.tr("ap_group_not_found"))
            return

        self.session.set_ap_groups(groups)
        self.refresh_session_labels()
        self.refresh_points_table()
        self.status.showMessage(
            self.tr("ap_position_saved", group=self.get_ap_group_display_name(group_id), x=x, y=y)
        )

    def cancel_ap_positioning(self):
        self.status.showMessage(self.tr("ap_position_cancelled"))

    def get_ap_group_display_name(self, group_id):
        if self.session is None:
            return str(group_id)

        group_id = str(group_id)
        for group in self.session.get_ap_groups():
            if str(group.get("group_id", "")) == group_id:
                alias = str(group.get("alias", "")).strip()
                return alias or group_id

        return group_id

    def format_ap_position_tooltip(self, group, label, x, y):
        return "\n".join([
            self.tr("ap_group_position_tooltip_title"),
            f"{self.tr('ap_alias_value')}: {label}",
            f"{self.tr('ap_alias_group')}: {group.get('group_id', '-')}",
            f"x/y: {x}, {y}",
            f"{self.tr('ap_alias_bssids')}: {', '.join(group.get('bssids', [])) or '-'}",
        ])

    def current_selected_point(self):
        selected = self.points_table.selectedItems()
        if not selected:
            return None

        row = selected[0].row()
        item = self.points_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def update_point_action_state(self):
        has_point = bool(self.current_selected_point())
        has_any_point = bool(self.session and self.session.get_point_summaries())
        self.focus_point_button.setEnabled(has_point)
        self.delete_selected_button.setEnabled(has_point)
        self.delete_last_button.setEnabled(has_any_point)

    def focus_selected_point(self):
        point = self.current_selected_point()
        if not point:
            QMessageBox.warning(self, self.tr("warning"), self.tr("select_point"))
            return

        self.floorplan_view.focus_on(point["x"], point["y"])

    def delete_selected_point(self):
        point = self.current_selected_point()
        if not point:
            QMessageBox.warning(self, self.tr("warning"), self.tr("select_point"))
            return

        self.delete_point(point)

    def delete_last_point(self):
        if self.session is None:
            return

        points = self.session.get_point_summaries()
        if not points:
            QMessageBox.warning(self, self.tr("warning"), self.tr("no_point_to_delete"))
            return

        point = points[-1]
        removed_rows = self.delete_point(point, refresh=False)
        self.refresh_session_labels()
        self.refresh_points_table()
        self.status.showMessage(
            self.tr("last_point_deleted", x=point["x"], y=point["y"], rows=removed_rows)
        )

    def delete_point(self, point, refresh=True):
        if self.session is None:
            return 0

        removed_rows = self.session.delete_point(point["timestamp"], int(point["x"]), int(point["y"]))
        if refresh:
            self.refresh_session_labels()
            self.refresh_points_table()
            self.status.showMessage(
                self.tr("point_deleted", x=point["x"], y=point["y"], rows=removed_rows)
            )
        return removed_rows

    def session_display_name(self):
        if self.session is None:
            return self.tr("unsaved_survey")
        if self.session.csv_file:
            return self.session.display_name
        return self.tr("unsaved_survey")

    def channel_sort_key(self, channel):
        try:
            return int(str(channel).strip())
        except (TypeError, ValueError):
            return 9999

    def refresh_session_labels(self):
        if self.session is None:
            csv_name = self.tr("unsaved_survey")
            map_name = self.tr("no_map")
            point_count = 0
            raw_count = 0
            ap_group_count = 0
            relevant_label = self.tr("relevant_networks_none")
            last_point = "-"
            dirty_suffix = ""
        else:
            csv_name = self.session_display_name()
            map_file = self.session.metadata.get("map_file", "")
            map_name = os.path.basename(map_file) if map_file else self.tr("no_map")
            point_summaries = self.session.get_point_summaries()
            point_count = len(point_summaries)
            raw_count = len(self.session.raw_scan_rows)
            ap_group_count = len(self.session.get_ap_groups())
            relevant_label = (
                ", ".join(sorted(self.relevant_ssids, key=str.casefold))
                if self.relevant_ssids
                else self.tr("relevant_networks_none")
            )
            last_point = (
                f"x={point_summaries[-1]['x']}, y={point_summaries[-1]['y']}"
                if point_summaries
                else "-"
            )
            dirty_suffix = " *" if self.session.dirty else ""

        self.csv_label.setText(f"{self.tr('qt_csv')}: {csv_name}{dirty_suffix}")
        self.map_label.setText(f"{self.tr('map')}: {map_name}")
        self.points_label.setText(f"{self.tr('qt_points')}: {point_count}")
        self.raw_rows_label.setText(f"{self.tr('qt_raw_rows')}: {raw_count}")
        self.ap_groups_label.setText(f"{self.tr('ap_groups_title')}: {ap_group_count}")
        self.relevant_label.setText(f"{self.tr('saved_network')}: {relevant_label}")
        self.footer_label.setText(
            self.tr(
                "footer_survey_info",
                csv=f"{csv_name}{dirty_suffix}",
                map=map_name,
                points=point_count,
                last=last_point,
            )
        )
        self.new_action.setEnabled(not self.scan_in_progress)
        self.open_action.setEnabled(not self.scan_in_progress)
        can_use_session = self.session is not None and not self.scan_in_progress
        self.save_action.setEnabled(can_use_session)
        self.load_plan_action.setEnabled(can_use_session)
        self.ap_groups_action.setEnabled(can_use_session)
        self.quality_action.setEnabled(can_use_session)
        self.generate_action.setEnabled(can_use_session)
        has_map = self.floorplan_view.has_floorplan()
        self.zoom_in_action.setEnabled(has_map and not self.scan_in_progress)
        self.zoom_out_action.setEnabled(has_map and not self.scan_in_progress)
        self.fit_action.setEnabled(has_map and not self.scan_in_progress)
        self.update_point_action_state()

    def refresh_points_table(self):
        self.points_table.setRowCount(0)
        if self.session is None:
            self.update_point_action_state()
            return

        summaries = list(reversed(self.session.get_point_summaries()))
        quality_by_point_id = evaluate_point_quality(
            self.session.rows,
            self.session.raw_scan_rows,
            relevant_ssids=self.relevant_ssids,
        )
        self.floorplan_view.set_points(summaries)
        self.floorplan_view.set_ap_groups(self.session.get_ap_groups())
        self.points_table.setRowCount(len(summaries))
        for row_index, point in enumerate(summaries):
            quality = quality_by_point_id.get(point.get("point_id", ""), {})
            values = [
                str(len(summaries) - row_index),
                str(point.get("x", "")),
                str(point.get("y", "")),
                f"{point.get('best_signal_dbm', '')}",
                self.format_point_quality(quality.get("status")),
                ", ".join(point.get("ssids", [])),
                str(point.get("row_count", "")),
                str(point.get("timestamp", "")),
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, point)
                if column_index == 4 and self.should_show_quality_tooltip(quality):
                    item.setToolTip(self.build_quality_tooltip_text(quality))
                self.points_table.setItem(row_index, column_index, item)
        self.update_point_action_state()

    def format_point_quality(self, status):
        return {
            QUALITY_GOOD: self.tr("quality_good"),
            QUALITY_MISSING_RELEVANT: self.tr("quality_missing_relevant"),
            QUALITY_LOW_CONFIDENCE: self.tr("quality_low_confidence"),
            QUALITY_UNSTABLE_SIGNAL: self.tr("quality_unstable_signal"),
            QUALITY_SPARSE_DATA: self.tr("quality_sparse_data"),
        }.get(status, "-")

    def should_show_quality_tooltip(self, quality):
        breakdown = quality.get("breakdown", []) if quality else []
        if len(breakdown) > 1:
            return True
        if not breakdown:
            return False

        return breakdown[0].get("status") in {QUALITY_LOW_CONFIDENCE, QUALITY_UNSTABLE_SIGNAL}

    def build_quality_tooltip_text(self, quality):
        lines = [self.tr("quality_breakdown_title")]
        lines.append(f"{self.tr('quality')}: {self.format_point_quality(quality.get('status'))}")
        for item in quality.get("breakdown", []):
            lines.append(f"{item.get('ssid', '-')}: {self.format_quality_breakdown_item(item)}")
        return "\n".join(lines)

    def format_quality_breakdown_item(self, item):
        status = item.get("status")
        if status == QUALITY_GOOD:
            return self.tr("quality_good")
        if status == QUALITY_MISSING_RELEVANT:
            return self.tr("quality_missing_relevant")
        if status == QUALITY_LOW_CONFIDENCE:
            confidence = item.get("min_confidence")
            suffix = f" ({confidence:.2f})" if isinstance(confidence, float) else ""
            return f"{self.tr('quality_low_confidence')}{suffix}"
        if status == QUALITY_UNSTABLE_SIGNAL:
            range_db = item.get("range_db")
            suffix = f" ({range_db:.1f} dB)" if isinstance(range_db, float) else ""
            return f"{self.tr('quality_unstable_signal')}{suffix}"
        return self.format_point_quality(status)


def main():
    app = QApplication(sys.argv)
    window = WifiHeatmapQtApp()
    window.showMaximized()
    sys.exit(app.exec())


def load_json_string_set(value):
    if not value:
        return set()

    try:
        values = json.loads(value)
    except json.JSONDecodeError:
        return set()

    if not isinstance(values, list):
        return set()

    return {
        str(item).strip()
        for item in values
        if str(item).strip()
    }


if __name__ == "__main__":
    main()
