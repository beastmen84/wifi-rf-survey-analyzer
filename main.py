import os
import sys
from pathlib import Path

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QComboBox,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
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
from survey_store import SurveyFormatError, SurveySession


class WifiHeatmapQtApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.language = DEFAULT_LANGUAGE
        self.session = None

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
        self.ap_groups_action = QAction(self)
        self.quality_action = QAction(self)
        self.generate_action = QAction(self)
        self.new_action.triggered.connect(self.new_survey)
        self.open_action.triggered.connect(self.open_survey)
        self.save_action.triggered.connect(self.save_survey)
        self.load_plan_action.triggered.connect(self.load_plan)
        self.ap_groups_action.triggered.connect(self.show_not_migrated_message)
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
        for row, label in enumerate((
            self.csv_label,
            self.map_label,
            self.points_label,
            self.raw_rows_label,
            self.ap_groups_label,
        )):
            grid.addWidget(label, row // 2, row % 2)
        layout.addWidget(summary)

        self.points_table = QTableWidget(0, 6)
        self.points_table.setAlternatingRowColors(True)
        self.points_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.points_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.points_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.points_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.points_table, 1)
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
        self.ap_groups_action.setText(self.tr("ap_groups_title"))
        self.quality_action.setText(self.tr("quality_dashboard_title"))
        self.generate_action.setText(self.tr("generate_heatmap"))
        self.tabs.setTabText(0, self.tr("survey_tab"))
        self.tabs.setTabText(1, self.tr("live_map_tab"))
        self.live_title.setText(self.tr("qt_live_placeholder_title"))
        self.live_body.setText(self.tr("qt_live_placeholder_body"))
        self.points_table.setHorizontalHeaderLabels([
            "#",
            "X",
            "Y",
            self.tr("qt_table_networks"),
            self.tr("qt_table_best_dbm"),
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

        self.show_workspace_page()
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

        self.session.update_metadata({"map_file": os.path.abspath(file_path)})
        self.refresh_session_labels()
        self.status.showMessage(self.tr("map_loaded", name=self.session_display_name()))

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

    def session_display_name(self):
        if self.session is None:
            return self.tr("unsaved_survey")
        if self.session.csv_file:
            return self.session.display_name
        return self.tr("unsaved_survey")

    def refresh_session_labels(self):
        if self.session is None:
            csv_name = self.tr("unsaved_survey")
            map_name = self.tr("no_map")
            point_count = 0
            raw_count = 0
            ap_group_count = 0
            dirty_suffix = ""
        else:
            csv_name = self.session_display_name()
            map_file = self.session.metadata.get("map_file", "")
            map_name = os.path.basename(map_file) if map_file else self.tr("no_map")
            point_count = len(self.session.get_point_summaries())
            raw_count = len(self.session.raw_scan_rows)
            ap_group_count = len(self.session.get_ap_groups())
            dirty_suffix = " *" if self.session.dirty else ""

        self.csv_label.setText(f"{self.tr('qt_csv')}: {csv_name}{dirty_suffix}")
        self.map_label.setText(f"{self.tr('map')}: {map_name}")
        self.points_label.setText(f"{self.tr('qt_points')}: {point_count}")
        self.raw_rows_label.setText(f"{self.tr('qt_raw_rows')}: {raw_count}")
        self.ap_groups_label.setText(f"{self.tr('ap_groups_title')}: {ap_group_count}")
        self.footer_label.setText(
            self.tr(
                "footer_survey_info",
                csv=f"{csv_name}{dirty_suffix}",
                map=map_name,
                points=point_count,
                last="-",
            )
        )
        self.save_action.setEnabled(self.session is not None)
        self.load_plan_action.setEnabled(self.session is not None)

    def refresh_points_table(self):
        self.points_table.setRowCount(0)
        if self.session is None:
            return

        summaries = list(reversed(self.session.get_point_summaries()))
        self.points_table.setRowCount(len(summaries))
        for row_index, point in enumerate(summaries):
            values = [
                str(len(summaries) - row_index),
                str(point.get("x", "")),
                str(point.get("y", "")),
                ", ".join(point.get("ssids", [])),
                f"{point.get('best_signal_dbm', '')}",
                str(point.get("timestamp", "")),
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.points_table.setItem(row_index, column_index, item)


def main():
    app = QApplication(sys.argv)
    window = WifiHeatmapQtApp()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
