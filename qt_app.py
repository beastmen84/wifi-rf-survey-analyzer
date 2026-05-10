import json
import os
import sys
from pathlib import Path

try:
    from PySide6.QtCore import QEvent, Qt, QThread, QTimer
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QInputDialog,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSplitter,
        QStackedWidget,
        QStatusBar,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, normalize_language, translate
from app_logging import configure_logging, log_event, log_exception, log_unhandled_exception
from ap_groups import (
    build_ap_group_role_map,
    build_bssid_to_manual_group_map,
    serialize_ap_group_map,
    serialize_ap_group_roles,
)
from map_exporter import MapExportError, generate_map_export
from map_config import MapConfig
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
from qt_help_dialog import open_qt_help_dialog
from qt_live_map import LiveMapRenderWorker, LiveMapView, create_marker_icon, load_floorplan_image
from qt_map_generation import MapGenerationDialog
from qt_point_workflow import MissingRelevantNetworksDialog, RelevantNetworksDialog, WifiScanWorker
from qt_quality_dashboard import open_qt_quality_dashboard
from qt_theme import QT_THEME_OPTIONS, QT_THEMES
from survey_store import SurveyFormatError, SurveySession
from wifi_scanner import get_connected_ssid


RELEVANT_SSIDS_METADATA_KEY = "relevant_ssids"
KNOWN_SSIDS_METADATA_KEY = "known_ssids"


class WifiHeatmapQtApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.language = DEFAULT_LANGUAGE
        self.theme = "light"
        self.session = None
        self.relevant_ssids = set()
        self.known_ssids = set()
        self.scan_thread = None
        self.scan_worker = None
        self.scan_in_progress = False
        self.pending_scan_point = None
        self.last_scan_backend_used = "-"
        self.live_thread = None
        self.live_worker = None
        self.live_rendering = False
        self.live_dirty = False
        self.points_panel_expanded = False
        self.points_overlay_height = 0
        self.points_overlay_resize_active = False
        self.points_overlay_resize_start_y = 0
        self.points_overlay_resize_start_height = 0

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

    def get_px_per_meter(self):
        if self.session is None:
            return None

        try:
            value = float(self.session.metadata.get("px_per_meter", ""))
        except (TypeError, ValueError):
            return None

        return value if value > 0 else None

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
        title_box.addWidget(self.start_title)
        title_box.addWidget(self.start_subtitle)
        panel_layout.addLayout(title_box, 0, 0, 1, 2)

        action_box = QVBoxLayout()
        self.new_button = QPushButton()
        self.open_button = QPushButton()
        self.exit_button = QPushButton()
        self.new_button.clicked.connect(self.new_survey)
        self.open_button.clicked.connect(lambda _checked=False: self.open_survey())
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
        layout.setSpacing(0)

        self.app_bar = self.build_app_bar()
        layout.addWidget(self.app_bar)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_survey_tab(), "")
        self.tabs.addTab(self.build_live_tab(), "")
        self.tabs.currentChanged.connect(self.on_workspace_tab_changed)
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

    def build_app_bar(self):
        bar = QFrame()
        bar.setObjectName("appBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        project_section, self.project_section_label, project_row = self.build_app_bar_section()
        self.new_workspace_button = self.create_app_bar_button(self.new_survey)
        self.open_workspace_button = self.create_app_bar_button(lambda: self.open_survey())
        self.save_workspace_button = self.create_app_bar_button(self.save_survey)
        self.load_plan_button = self.create_app_bar_button(self.load_plan)
        self.save_tool_button = self.save_workspace_button
        for button in (
            self.new_workspace_button,
            self.open_workspace_button,
            self.save_workspace_button,
            self.load_plan_button,
        ):
            project_row.addWidget(button)
        layout.addWidget(project_section)

        view_section, self.view_section_label, view_row = self.build_app_bar_section()
        self.zoom_out_button = self.create_app_bar_button(self.zoom_out, "appBarIconButton")
        self.zoom_in_button = self.create_app_bar_button(self.zoom_in, "appBarIconButton")
        self.fit_view_button = self.create_app_bar_button(self.fit_floorplan)
        self.calibrate_button = self.create_app_bar_button(self.start_scale_calibration)
        for button in (
            self.zoom_out_button,
            self.zoom_in_button,
            self.fit_view_button,
            self.calibrate_button,
        ):
            view_row.addWidget(button)
        layout.addWidget(view_section)

        analysis_section, self.analysis_section_label, analysis_row = self.build_app_bar_section()
        self.ap_groups_button = self.create_app_bar_button(self.open_ap_group_manager)
        self.quality_button = self.create_app_bar_button(self.open_quality_dashboard)
        self.help_button = self.create_app_bar_button(self.open_help_dialog)
        self.generate_map_button = self.create_app_bar_button(
            self.open_generate_map_dialog,
            "primaryAppBarButton",
        )
        for button in (
            self.ap_groups_button,
            self.quality_button,
            self.help_button,
            self.generate_map_button,
        ):
            analysis_row.addWidget(button)
        layout.addWidget(analysis_section, 1)

        settings_section, self.settings_section_label, settings_row = self.build_app_bar_section()
        self.workspace_theme_label = QLabel()
        self.workspace_theme_label.setObjectName("appBarInlineLabel")
        self.workspace_theme_combo = QComboBox()
        self.workspace_theme_combo.currentIndexChanged.connect(self.change_theme)
        self.workspace_language_label = QLabel()
        self.workspace_language_label.setObjectName("appBarInlineLabel")
        self.workspace_language_combo = QComboBox()
        self.workspace_language_combo.addItems(SUPPORTED_LANGUAGES)
        self.workspace_language_combo.setCurrentText(self.language.upper())
        self.workspace_language_combo.currentTextChanged.connect(self.change_language)
        for widget in (
            self.workspace_theme_label,
            self.workspace_theme_combo,
            self.workspace_language_label,
            self.workspace_language_combo,
        ):
            settings_row.addWidget(widget)
        layout.addWidget(settings_section)

        return bar

    def build_app_bar_section(self):
        section = QFrame()
        section.setObjectName("appBarSection")
        outer = QVBoxLayout(section)
        outer.setContentsMargins(10, 7, 10, 8)
        outer.setSpacing(5)

        title = QLabel()
        title.setObjectName("appBarSectionTitle")
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        outer.addWidget(title)
        outer.addLayout(row)
        return section, title, row

    def create_app_bar_button(self, callback, object_name="appBarButton"):
        button = QPushButton()
        button.setObjectName(object_name)
        button.clicked.connect(lambda _checked=False: callback())
        return button

    def create_summary_card(self, title_key, compact=False, action_widget=None):
        card = QFrame()
        card.setObjectName("summaryCardCompact" if compact else "summaryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(7, 4, 7, 5)
        layout.setSpacing(1)

        title = QLabel()
        title.setObjectName("summaryCardTitle")
        value = QLabel()
        value.setObjectName("summaryCardCompactValue" if compact else "summaryCardValue")
        value.setWordWrap(True)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        if action_widget is None:
            layout.addWidget(title)
        else:
            title_row = QHBoxLayout()
            title_row.setContentsMargins(0, 0, 0, 0)
            title_row.setSpacing(4)
            title_row.addWidget(title)
            title_row.addStretch(1)
            title_row.addWidget(action_widget)
            layout.addLayout(title_row)
        layout.addWidget(value, 1)
        self.summary_title_bindings.append((title, title_key))
        return card, value, layout

    def build_survey_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        summary = QFrame()
        summary.setObjectName("summaryPanel")
        self.summary_title_bindings = []
        grid = QGridLayout(summary)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)

        self.clear_relevant_button = QPushButton()
        self.clear_relevant_button.setObjectName("summaryActionButton")
        self.clear_relevant_button.setMaximumWidth(118)
        self.clear_relevant_button.clicked.connect(self.clear_relevant_ssids)
        csv_card, self.csv_label, _csv_layout = self.create_summary_card("qt_csv")
        map_card, self.map_label, _map_layout = self.create_summary_card("map")
        points_card, self.points_label, _points_layout = self.create_summary_card("qt_points", compact=True)
        raw_card, self.raw_rows_label, _raw_layout = self.create_summary_card("qt_raw_rows", compact=True)
        ap_card, self.ap_groups_label, _ap_layout = self.create_summary_card("summary_ap_groups", compact=True)
        relevant_card, self.relevant_label, _relevant_layout = self.create_summary_card(
            "saved_network",
            action_widget=self.clear_relevant_button,
        )
        for card in (points_card, raw_card, ap_card):
            card.setMaximumWidth(112)
        for index, card in enumerate((
            csv_card,
            map_card,
            points_card,
            raw_card,
            ap_card,
            relevant_card,
        )):
            grid.addWidget(card, 0, index)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 0)
        grid.setColumnStretch(4, 0)
        grid.setColumnStretch(5, 2)
        layout.addWidget(summary)

        self.floorplan_container = QFrame()
        self.floorplan_container.setObjectName("floorplanContainer")
        self.floorplan_container.installEventFilter(self)
        floorplan_layout = QVBoxLayout(self.floorplan_container)
        floorplan_layout.setContentsMargins(1, 1, 1, 1)
        floorplan_layout.setSpacing(0)
        self.floorplan_view = FloorplanView()
        self.floorplan_view.ap_tooltip_formatter = self.format_ap_position_tooltip
        self.floorplan_view.surveyPointRequested.connect(self.create_point_from_floorplan)
        self.floorplan_view.apPositionPicked.connect(self.save_ap_position)
        self.floorplan_view.apPositionCancelled.connect(self.cancel_ap_positioning)
        self.floorplan_view.scaleCalibrationFirstPointPicked.connect(self.on_scale_calibration_first_point)
        self.floorplan_view.scaleCalibrationCompleted.connect(self.finish_scale_calibration)
        self.floorplan_view.scaleCalibrationCancelled.connect(self.cancel_scale_calibration)
        self.floorplan_view.pointSelected.connect(self.select_point_in_table)
        self.floorplan_view.pointSelectionCleared.connect(self.clear_point_selection)
        floorplan_layout.addWidget(self.floorplan_view)

        self.points_overlay = QFrame(self.floorplan_container)
        self.points_overlay.setObjectName("floatingPointsPanel")
        self.points_overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        overlay_layout = QVBoxLayout(self.points_overlay)
        overlay_layout.setContentsMargins(8, 8, 8, 8)
        overlay_layout.setSpacing(6)

        points_handle_row = QHBoxLayout()
        points_handle_row.setContentsMargins(0, 0, 0, 0)
        points_handle_row.addStretch(1)
        self.points_panel_toggle_button = QPushButton()
        self.points_panel_toggle_button.setObjectName("pointsPanelToggle")
        self.points_panel_toggle_button.clicked.connect(self.toggle_points_panel)
        points_handle_row.addWidget(self.points_panel_toggle_button)
        self.points_panel_resize_button = QPushButton("↕")
        self.points_panel_resize_button.setObjectName("pointsPanelResize")
        self.points_panel_resize_button.installEventFilter(self)
        points_handle_row.addWidget(self.points_panel_resize_button)
        points_handle_row.addStretch(1)
        overlay_layout.addLayout(points_handle_row)

        self.points_table_body = QWidget()
        self.points_table_body.setObjectName("pointsTableBody")
        table_layout = QVBoxLayout(self.points_table_body)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(8)

        self.points_table = QTableWidget(0, 8)
        self.points_table.setAlternatingRowColors(True)
        self.points_table.setShowGrid(False)
        self.points_table.setWordWrap(False)
        self.points_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.points_table.verticalHeader().setVisible(False)
        self.points_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.points_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.points_table.horizontalHeader().setStretchLastSection(False)
        self.points_table.horizontalHeader().setMinimumSectionSize(34)
        self.configure_points_table_columns()
        self.points_table.itemSelectionChanged.connect(self.update_point_action_state)
        self.points_table.itemDoubleClicked.connect(lambda _item: self.focus_selected_point())
        table_layout.addWidget(self.points_table)

        point_buttons = QHBoxLayout()
        self.focus_point_button = QPushButton()
        self.delete_selected_button = QPushButton()
        self.delete_last_button = QPushButton()
        for button in (self.focus_point_button, self.delete_selected_button, self.delete_last_button):
            button.setObjectName("pointsActionButton")
        self.focus_point_button.clicked.connect(self.focus_selected_point)
        self.delete_selected_button.clicked.connect(self.delete_selected_point)
        self.delete_last_button.clicked.connect(self.delete_last_point)
        point_buttons.addWidget(self.focus_point_button)
        point_buttons.addWidget(self.delete_selected_button)
        point_buttons.addWidget(self.delete_last_button)
        point_buttons.addStretch(1)
        table_layout.addLayout(point_buttons)

        overlay_layout.addWidget(self.points_table_body, 1)
        self.points_table_body.setVisible(False)
        self.points_panel_resize_button.setVisible(False)
        self.update_points_panel_toggle()
        layout.addWidget(self.floorplan_container, 1)
        QTimer.singleShot(0, self.position_points_overlay)
        return tab

    def toggle_points_panel(self):
        self.points_panel_expanded = not self.points_panel_expanded
        if self.points_panel_expanded and not self.points_overlay_height:
            self.points_overlay_height = self.default_points_overlay_height()
        self.points_table_body.setVisible(self.points_panel_expanded)
        self.points_panel_resize_button.setVisible(self.points_panel_expanded)
        self.update_points_panel_toggle()
        self.position_points_overlay()

    def update_points_panel_toggle(self):
        if not hasattr(self, "points_panel_toggle_button"):
            return
        key = "points_panel_hide" if self.points_panel_expanded else "points_panel_show"
        self.points_panel_toggle_button.setText(self.tr(key))
        if hasattr(self, "points_panel_resize_button"):
            self.points_panel_resize_button.setToolTip(self.tr("points_panel_resize"))

    def default_points_overlay_height(self):
        row_height = max(24, self.points_table.verticalHeader().defaultSectionSize())
        header_height = max(28, self.points_table.horizontalHeader().height())
        button_height = max(34, self.focus_point_button.sizeHint().height())
        handle_height = max(34, self.points_panel_toggle_button.sizeHint().height())
        return handle_height + header_height + (row_height * 6) + button_height + 44

    def max_points_overlay_height(self):
        container_height = self.floorplan_container.height() if hasattr(self, "floorplan_container") else 0
        return max(self.default_points_overlay_height(), int(container_height * 0.78))

    def position_points_overlay(self):
        if not hasattr(self, "points_overlay"):
            return

        container_width = self.floorplan_container.width()
        container_height = self.floorplan_container.height()
        if container_width <= 0 or container_height <= 0:
            return

        margin = 16
        if self.points_panel_expanded:
            default_height = self.default_points_overlay_height()
            max_height = self.max_points_overlay_height()
            if not self.points_overlay_height:
                self.points_overlay_height = default_height
            self.points_overlay_height = max(default_height, min(self.points_overlay_height, max_height))
            width = min(max(760, int(container_width * 0.84)), max(320, container_width - (margin * 2)))
            height = min(self.points_overlay_height, max(170, container_height - (margin * 2)))
        else:
            width = min(260, max(220, container_width - (margin * 2)))
            height = max(42, self.points_panel_toggle_button.sizeHint().height() + 18)

        x = max(margin, (container_width - width) // 2)
        y = max(margin, container_height - height - margin)
        self.points_overlay.setGeometry(x, y, width, height)
        self.points_overlay.raise_()

    def eventFilter(self, source, event):
        if source is getattr(self, "floorplan_container", None) and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self.position_points_overlay)
            return False

        if source is getattr(self, "points_panel_resize_button", None):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self.points_overlay_resize_active = True
                self.points_overlay_resize_start_y = int(event.globalPosition().y())
                self.points_overlay_resize_start_height = self.points_overlay_height or self.default_points_overlay_height()
                return True
            if event.type() == QEvent.Type.MouseMove and self.points_overlay_resize_active:
                current_y = int(event.globalPosition().y())
                delta = self.points_overlay_resize_start_y - current_y
                new_height = self.points_overlay_resize_start_height + delta
                self.points_overlay_height = max(
                    self.default_points_overlay_height(),
                    min(new_height, self.max_points_overlay_height()),
                )
                self.position_points_overlay()
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and self.points_overlay_resize_active:
                self.points_overlay_resize_active = False
                return True

        return super().eventFilter(source, event)

    def configure_points_table_columns(self):
        if not hasattr(self, "points_table"):
            return

        header = self.points_table.horizontalHeader()
        header.setStretchLastSection(False)
        for column in range(self.points_table.columnCount()):
            mode = QHeaderView.ResizeMode.Stretch if column == 5 else QHeaderView.ResizeMode.ResizeToContents
            header.setSectionResizeMode(column, mode)

    def resize_points_table_columns(self):
        if not hasattr(self, "points_table"):
            return

        self.configure_points_table_columns()
        self.points_table.resizeColumnsToContents()
        compact_limits = {
            0: (42, 54),
            1: (50, 64),
            2: (50, 64),
            3: (92, 116),
            4: (110, 150),
            6: (54, 72),
            7: (140, 180),
        }
        header = self.points_table.horizontalHeader()
        for column, (minimum, maximum) in compact_limits.items():
            width = self.points_table.columnWidth(column)
            width = max(minimum, min(width + 10, maximum))
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.points_table.setColumnWidth(column, width)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

    def build_live_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        controls = QFrame()
        controls.setObjectName("summaryPanel")
        controls_layout = QGridLayout(controls)
        controls_layout.setContentsMargins(14, 12, 14, 12)
        controls_layout.setHorizontalSpacing(10)
        controls_layout.setVerticalSpacing(8)

        self.live_ssid_label = QLabel()
        self.live_ssid_combo = QComboBox()
        self.live_ssid_combo.setMinimumWidth(220)
        self.live_band_label = QLabel()
        self.live_band_combo = QComboBox()
        self.live_map_type_label = QLabel()
        self.live_map_type_combo = QComboBox()
        self.live_aggregation_label = QLabel()
        self.live_aggregation_combo = QComboBox()
        self.live_interference_mode_label = QLabel()
        self.live_interference_mode_combo = QComboBox()
        self.live_usable_check = QCheckBox()
        self.live_auto_check = QCheckBox()
        self.live_auto_check.setChecked(True)
        self.live_update_button = QPushButton()
        self.live_update_button.clicked.connect(self.update_live_preview)

        for combo in (
            self.live_ssid_combo,
            self.live_band_combo,
            self.live_map_type_combo,
            self.live_aggregation_combo,
            self.live_interference_mode_combo,
        ):
            combo.currentIndexChanged.connect(lambda *_args: self.on_live_option_changed())
        self.live_usable_check.toggled.connect(lambda *_args: self.on_live_option_changed())
        self.live_auto_check.toggled.connect(lambda *_args: self.on_live_option_changed())

        controls_layout.addWidget(self.live_ssid_label, 0, 0)
        controls_layout.addWidget(self.live_ssid_combo, 0, 1)
        controls_layout.addWidget(self.live_band_label, 0, 2)
        controls_layout.addWidget(self.live_band_combo, 0, 3)
        controls_layout.addWidget(self.live_map_type_label, 0, 4)
        controls_layout.addWidget(self.live_map_type_combo, 0, 5)
        controls_layout.addWidget(self.live_auto_check, 0, 6)
        controls_layout.addWidget(self.live_update_button, 0, 7)
        controls_layout.addWidget(self.live_aggregation_label, 1, 0)
        controls_layout.addWidget(self.live_aggregation_combo, 1, 1)
        controls_layout.addWidget(self.live_interference_mode_label, 1, 2)
        controls_layout.addWidget(self.live_interference_mode_combo, 1, 3)
        controls_layout.addWidget(self.live_usable_check, 1, 4, 1, 2)
        controls_layout.setColumnStretch(8, 1)
        layout.addWidget(controls)

        live_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.live_view = LiveMapView()
        live_splitter.addWidget(self.live_view)

        self.live_legend_frame = QFrame()
        self.live_legend_frame.setObjectName("summaryPanel")
        self.live_legend_frame.setMinimumWidth(260)
        self.live_legend_frame.setMaximumWidth(360)
        legend_layout = QVBoxLayout(self.live_legend_frame)
        legend_layout.setContentsMargins(12, 10, 12, 10)
        legend_layout.setSpacing(8)
        self.live_legend_title = QLabel()
        self.live_legend_title.setObjectName("sectionTitle")
        self.live_legend_list = QListWidget()
        self.live_legend_list.setAlternatingRowColors(True)
        self.live_legend_list.setWordWrap(True)
        legend_layout.addWidget(self.live_legend_title)
        legend_layout.addWidget(self.live_legend_list, 1)
        live_splitter.addWidget(self.live_legend_frame)
        live_splitter.setStretchFactor(0, 1)
        live_splitter.setStretchFactor(1, 0)
        layout.addWidget(live_splitter, 1)

        status_row = QHBoxLayout()
        self.live_status_label = QLabel()
        self.live_status_label.setObjectName("mutedText")
        status_row.addWidget(self.live_status_label, 1)
        self.live_zoom_out_button = QPushButton("-")
        self.live_zoom_in_button = QPushButton("+")
        self.live_fit_button = QPushButton()
        for button in (self.live_zoom_out_button, self.live_zoom_in_button, self.live_fit_button):
            button.setObjectName("compactButton")
        self.live_zoom_out_button.setMaximumWidth(42)
        self.live_zoom_in_button.setMaximumWidth(42)
        self.live_fit_button.setMaximumWidth(80)
        self.live_fit_button.clicked.connect(self.live_view.fit_to_view)
        self.live_zoom_out_button.clicked.connect(self.live_view.zoom_out)
        self.live_zoom_in_button.clicked.connect(self.live_view.zoom_in)
        status_row.addWidget(self.live_zoom_out_button)
        status_row.addWidget(self.live_zoom_in_button)
        status_row.addWidget(self.live_fit_button)
        layout.addLayout(status_row)
        return tab

    def apply_styles(self):
        palette = QT_THEMES.get(self.theme, QT_THEMES["light"])
        combo_arrow_icon = (Path(__file__).resolve().parent / "images" / "combo_arrow_white.svg").as_posix()
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{
                background: {palette["bg"]};
                color: {palette["text"]};
                font-family: Segoe UI;
                font-size: 10.5pt;
            }}
            QLabel, QCheckBox {{
                background: transparent;
            }}
            QFrame#startPanel, QFrame#summaryPanel {{
                background: {palette["panel"]};
                border: 1px solid {palette["border"]};
                border-radius: 8px;
            }}
            QFrame#footer {{
                background: {palette["footer"]};
                border-top: 1px solid {palette["border"]};
            }}
            QFrame#metricBox {{
                background: {palette["panel"]};
                border: 1px solid {palette["border"]};
                border-radius: 6px;
            }}
            QFrame#floorplanContainer {{
                background: {palette["live_bg"]};
                border: 1px solid {palette["border"]};
                border-radius: 8px;
            }}
            QGraphicsView#floorplanView {{
                background: {palette["live_bg"]};
                border: 0;
                border-radius: 8px;
            }}
            QFrame#floatingPointsPanel {{
                background: {palette["panel"]};
                border: 1px solid {palette["border"]};
                border-radius: 10px;
            }}
            QWidget#pointsTableBody {{
                background: transparent;
            }}
            QPushButton#pointsPanelToggle {{
                min-width: 150px;
                padding: 6px 14px;
                border-radius: 14px;
                background: {palette["metric_info"]};
                color: #FFFFFF;
                border: 1px solid {palette["metric_info"]};
                font-weight: 700;
            }}
            QPushButton#pointsPanelResize {{
                min-width: 30px;
                max-width: 34px;
                padding: 6px 0;
                border-radius: 14px;
                background: {palette["button_bg"]};
                color: {palette["muted"]};
                border: 1px solid {palette["border"]};
                font-weight: 700;
            }}
            QPushButton#pointsActionButton {{
                min-width: 0;
                padding: 6px 10px;
            }}
            QFrame#summaryCard, QFrame#summaryCardCompact {{
                background: {palette["panel_alt"]};
                border: 1px solid {palette["border"]};
                border-radius: 5px;
            }}
            QLabel#summaryCardTitle {{
                color: {palette["muted"]};
                font-size: 8pt;
                font-weight: 700;
            }}
            QLabel#summaryCardValue {{
                color: {palette["title"]};
                font-size: 10pt;
                font-weight: 600;
            }}
            QLabel#summaryCardCompactValue {{
                color: {palette["title"]};
                font-size: 14pt;
                font-weight: 600;
            }}
            QLabel#startTitle {{
                font-size: 25pt;
                font-weight: 700;
                color: {palette["title"]};
            }}
            QLabel#sectionTitle {{
                font-size: 13pt;
                font-weight: 600;
                color: {palette["title"]};
            }}
            QLabel#mutedText {{
                color: {palette["muted"]};
            }}
            QLabel#badge {{
                color: {palette["badge_text"]};
                background: {palette["badge_bg"]};
                border: 1px solid {palette["badge_border"]};
                border-radius: 5px;
                padding: 5px 8px;
            }}
            QLabel#metricValue_good {{
                color: {palette["metric_good"]};
                font-size: 18pt;
                font-weight: 700;
            }}
            QLabel#metricValue_warning {{
                color: {palette["metric_warning"]};
                font-size: 18pt;
                font-weight: 700;
            }}
            QLabel#metricValue_danger {{
                color: {palette["metric_danger"]};
                font-size: 18pt;
                font-weight: 700;
            }}
            QLabel#metricValue_info {{
                color: {palette["metric_info"]};
                font-size: 18pt;
                font-weight: 700;
            }}
            QPushButton {{
                background: {palette["button_bg"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                border-radius: 5px;
                min-width: 240px;
                padding: 8px 12px;
            }}
            QPushButton:hover {{
                background: {palette["button_hover"]};
            }}
            QPushButton:disabled {{
                color: {palette["muted"]};
            }}
            QPushButton#compactButton {{
                min-width: 0;
                padding: 5px 8px;
            }}
            QPushButton#summaryActionButton {{
                min-width: 0;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 8pt;
                font-weight: 600;
            }}
            QFrame#appBar {{
                background: {palette["toolbar"]};
                border-bottom: 1px solid {palette["border"]};
            }}
            QFrame#appBarSection {{
                background: {palette["panel"]};
                border: 1px solid {palette["border"]};
                border-radius: 6px;
            }}
            QLabel#appBarSectionTitle {{
                color: {palette["muted"]};
                font-size: 8.5pt;
                font-weight: 700;
            }}
            QLabel#appBarInlineLabel {{
                color: {palette["muted"]};
                font-size: 9pt;
                font-weight: 600;
            }}
            QPushButton#appBarButton, QPushButton#appBarIconButton, QPushButton#primaryAppBarButton, QPushButton#dirtySaveButton {{
                min-width: 0;
                padding: 6px 10px;
                border-radius: 5px;
                font-weight: 600;
            }}
            QPushButton#appBarIconButton {{
                min-width: 30px;
                max-width: 34px;
                padding: 6px 0;
                font-size: 12pt;
            }}
            QPushButton#primaryAppBarButton {{
                background: {palette["metric_info"]};
                color: #FFFFFF;
                border: 1px solid {palette["metric_info"]};
            }}
            QPushButton#primaryAppBarButton:disabled {{
                background: {palette["button_bg"]};
                color: {palette["muted"]};
                border: 1px solid {palette["border"]};
            }}
            QPushButton#dirtySaveButton {{
                background: {palette["save_dirty_bg"]};
                color: {palette["save_dirty_text"]};
                border: 1px solid {palette["save_dirty_border"]};
            }}
            QToolButton {{
                background: {palette["button_bg"]};
                color: {palette["text"]};
                border: 1px solid transparent;
                border-radius: 5px;
                padding: 5px 8px;
            }}
            QToolButton:hover {{
                background: {palette["button_hover"]};
                border: 1px solid {palette["border"]};
            }}
            QToolButton#dirtySaveButton {{
                background: {palette["save_dirty_bg"]};
                color: {palette["save_dirty_text"]};
                border: 1px solid {palette["save_dirty_border"]};
                font-weight: 600;
            }}
            QComboBox {{
                background: {palette["button_bg"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                border-radius: 4px;
                padding: 4px 28px 4px 8px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 22px;
                border-left: 1px solid {palette["metric_info"]};
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background: {palette["metric_info"]};
            }}
            QComboBox::down-arrow {{
                image: url("{combo_arrow_icon}");
                width: 10px;
                height: 6px;
            }}
            QComboBox QAbstractItemView {{
                background: {palette["panel"]};
                color: {palette["text"]};
                selection-background-color: {palette["selection"]};
            }}
            QCheckBox {{
                color: {palette["text"]};
                spacing: 9px;
                padding: 3px 2px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid {palette["border"]};
                background: {palette["panel"]};
            }}
            QCheckBox::indicator:hover {{
                border: 1px solid {palette["metric_info"]};
            }}
            QCheckBox::indicator:checked {{
                background: {palette["metric_info"]};
                border: 1px solid {palette["metric_info"]};
            }}
            QTabWidget::pane {{
                border: 1px solid {palette["border"]};
                top: -1px;
            }}
            QTabBar::tab {{
                background: {palette["header"]};
                color: {palette["muted"]};
                border: 1px solid {palette["border"]};
                border-bottom: 0;
                padding: 7px 16px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }}
            QTabBar::tab:selected {{
                background: {palette["panel"]};
                color: {palette["text"]};
                font-weight: 600;
            }}
            QTableWidget {{
                background: {palette["panel"]};
                alternate-background-color: {palette["panel_alt"]};
                color: {palette["text"]};
                selection-background-color: {palette["selection"]};
            }}
            QTableWidget::item {{
                border: 0;
                border-bottom: 1px solid {palette["border"]};
                padding: 4px 6px;
            }}
            QTableWidget::item:selected {{
                background: {palette["selection"]};
                color: {palette["text"]};
            }}
            QGraphicsView#liveMapView {{
                background: {palette["live_bg"]};
                border: 1px solid {palette["border"]};
                border-radius: 4px;
            }}
            QListWidget {{
                background: {palette["panel"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                border-radius: 4px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 4px;
            }}
            QHeaderView::section {{
                background: {palette["header"]};
                color: {palette["text"]};
                padding: 5px;
                border: 0;
                border-right: 1px solid {palette["border"]};
                font-weight: 600;
            }}
            QToolTip {{
                background: {palette["panel"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                padding: 5px;
            }}
            """
        )

    def retranslate(self):
        self.setWindowTitle(self.tr("app_title"))
        self.start_language_label.setText(self.tr("language"))
        self.workspace_theme_label.setText(self.tr("theme"))
        self.workspace_language_label.setText(self.tr("language"))
        self.project_section_label.setText(self.tr("toolbar_project"))
        self.view_section_label.setText(self.tr("toolbar_view"))
        self.analysis_section_label.setText(self.tr("toolbar_analysis"))
        self.settings_section_label.setText(self.tr("toolbar_settings"))
        for title_label, title_key in self.summary_title_bindings:
            title_label.setText(self.tr(title_key))
        self.start_title.setText(self.tr("app_title"))
        self.start_subtitle.setText(self.tr("start_subtitle"))
        self.start_hint_title.setText(self.tr("qt_start_hint_title"))
        self.start_hint_text.setText(self.tr("qt_start_hint"))
        self.copyright_label.setText(self.tr("copyright"))
        self.new_button.setText(self.tr("new_survey"))
        self.open_button.setText(self.tr("open_existing_survey"))
        self.exit_button.setText(self.tr("exit"))
        self.new_workspace_button.setText(self.tr("new_survey"))
        self.open_workspace_button.setText(self.tr("open_existing_survey"))
        self.save_workspace_button.setText(self.tr("save"))
        self.load_plan_button.setText(self.tr("load_plan"))
        self.zoom_out_button.setText("-")
        self.zoom_in_button.setText("+")
        self.fit_view_button.setText(self.tr("fit"))
        self.calibrate_button.setText(self.tr("calibrate_scale"))
        self.ap_groups_button.setText(self.tr("ap_groups_title"))
        self.quality_button.setText(self.tr("quality_dashboard_title"))
        self.help_button.setText(self.tr("help"))
        self.generate_map_button.setText(self.tr("generate_heatmap"))
        self.focus_point_button.setText(self.tr("go_to_point"))
        self.delete_selected_button.setText(self.tr("delete_selected"))
        self.delete_last_button.setText(self.tr("delete_last"))
        self.update_points_panel_toggle()
        self.clear_relevant_button.setText(self.tr("forget_saved_network"))
        self.tabs.setTabText(0, self.tr("survey_tab"))
        self.tabs.setTabText(1, self.tr("live_map_tab"))
        self.live_ssid_label.setText("SSID")
        self.live_band_label.setText(self.tr("band"))
        self.live_map_type_label.setText(self.tr("map_type"))
        self.live_aggregation_label.setText(self.tr("aggregation"))
        self.live_interference_mode_label.setText(self.tr("interference_mode"))
        self.live_usable_check.setText(self.tr("usable_only"))
        self.live_auto_check.setText(self.tr("live_auto_update"))
        self.live_update_button.setText(self.tr("live_update_now"))
        self.live_fit_button.setText(self.tr("fit"))
        self.refresh_theme_options()
        self.refresh_live_static_options()
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
        self.resize_points_table_columns()
        self.refresh_session_labels()

    def refresh_theme_options(self):
        self.set_combo_items(
            self.workspace_theme_combo,
            [(theme, self.tr(f"qt_theme_{theme}")) for theme in QT_THEME_OPTIONS],
        )

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
            self.refresh_live_controls()
            self.maybe_update_live_preview()

    def change_theme(self, _index=None):
        theme = self.workspace_theme_combo.currentData()
        if theme not in QT_THEMES or theme == self.theme:
            return

        self.theme = theme
        self.apply_styles()

    def refresh_live_static_options(self):
        self.set_combo_items(
            self.live_band_combo,
            [
                ("all", self.tr("all_bands_option")),
                ("2.4", "2.4 GHz"),
                ("5", "5 GHz"),
            ],
        )
        self.set_combo_items(
            self.live_map_type_combo,
            [
                ("signal", self.tr("map_type_signal")),
                ("interference", self.tr("map_type_interference")),
                ("channel", self.tr("map_type_channel")),
                ("dominant", self.tr("map_type_dominant")),
            ],
        )
        self.set_combo_items(
            self.live_aggregation_combo,
            [
                ("max", self.tr("aggregation_max")),
                ("median", self.tr("aggregation_median")),
                ("mean", self.tr("aggregation_mean")),
            ],
        )
        self.set_combo_items(
            self.live_interference_mode_combo,
            [
                ("intra_ssid", self.tr("interference_mode_intra_ssid")),
                ("all", self.tr("interference_mode_all")),
            ],
        )

    def set_combo_items(self, combo, items):
        current = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for value, label in items:
            combo.addItem(label, value)
        index = combo.findData(current)
        if index < 0 and combo.count():
            index = 0
        if index >= 0:
            combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def current_combo_value(self, combo, default=""):
        value = combo.currentData()
        return default if value is None else str(value)

    def refresh_live_controls(self):
        ssids = []
        if self.session is not None:
            ssids = self.session.get_ssids()

        current_ssid = self.live_ssid_combo.currentText().strip()
        self.live_ssid_combo.blockSignals(True)
        self.live_ssid_combo.clear()
        self.live_ssid_combo.addItems(ssids)
        if current_ssid and current_ssid in ssids:
            self.live_ssid_combo.setCurrentText(current_ssid)
        elif ssids:
            self.live_ssid_combo.setCurrentIndex(0)
        self.live_ssid_combo.blockSignals(False)

        can_render = self.can_use_live_controls(ssids)
        for widget in (
            self.live_ssid_combo,
            self.live_band_combo,
            self.live_map_type_combo,
            self.live_aggregation_combo,
            self.live_interference_mode_combo,
            self.live_usable_check,
            self.live_auto_check,
        ):
            widget.setEnabled(can_render)
        self.live_update_button.setEnabled(can_render and not self.live_rendering)
        self.live_zoom_out_button.setEnabled(self.live_view.pixmap_item is not None)
        self.live_zoom_in_button.setEnabled(self.live_view.pixmap_item is not None)
        self.live_fit_button.setEnabled(self.live_view.pixmap_item is not None)
        self.update_live_option_state()

        if not can_render and not self.live_rendering:
            self.live_status_label.setText(self.tr("live_preview_empty"))
            self.clear_live_legend()

    def can_use_live_controls(self, ssids=None):
        has_session = self.session is not None
        has_map = bool(has_session and self.session.metadata.get("map_file"))
        has_rows = bool(has_session and self.session.get_point_summaries())
        if ssids is None:
            ssids = self.session.get_ssids() if has_session else []
        return has_session and has_map and has_rows and bool(ssids) and not self.scan_in_progress

    def update_live_option_state(self):
        map_type = self.current_combo_value(self.live_map_type_combo, "signal")
        is_signal = map_type == "signal"
        is_interference = map_type == "interference"
        can_use_controls = self.can_use_live_controls()
        self.live_aggregation_combo.setEnabled(can_use_controls and is_signal)
        self.live_interference_mode_combo.setEnabled(can_use_controls and is_interference)
        self.live_usable_check.setEnabled(can_use_controls and is_signal)
        if is_interference and self.current_combo_value(self.live_band_combo) == "all":
            index = self.live_band_combo.findData("2.4")
            if index >= 0:
                self.live_band_combo.blockSignals(True)
                self.live_band_combo.setCurrentIndex(index)
                self.live_band_combo.blockSignals(False)

    def on_workspace_tab_changed(self, index):
        if index == 1:
            self.refresh_live_controls()
            self.maybe_update_live_preview()

    def on_live_option_changed(self):
        self.update_live_option_state()
        self.refresh_live_controls()
        self.maybe_update_live_preview()

    def maybe_update_live_preview(self):
        if self.tabs.currentIndex() != 1:
            return
        if not self.live_auto_check.isChecked():
            return
        self.update_live_preview()

    def update_live_preview(self):
        if not self.can_render_live_preview():
            self.live_view.clear()
            self.live_status_label.setText(self.tr("live_preview_empty"))
            self.clear_live_legend()
            self.refresh_live_controls()
            return

        if self.live_rendering:
            self.live_dirty = True
            return

        map_file = self.session.metadata.get("map_file", "")
        config = self.build_live_map_config()
        translations = self.build_live_renderer_translations()
        self.live_rendering = True
        self.live_dirty = False
        self.live_status_label.setText(self.tr("live_preview_rendering"))
        self.refresh_live_controls()

        thread = QThread(self)
        worker = LiveMapRenderWorker(
            self.session.rows,
            map_file,
            config,
            translations,
            aliases=self.session.get_ap_aliases(),
            ap_groups=self.session.get_ap_groups(),
            px_per_meter=self.get_px_per_meter(),
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self.finish_live_preview)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(self.fail_live_preview)
        worker.failed.connect(thread.quit)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(self.cleanup_live_render_thread)
        thread.finished.connect(thread.deleteLater)
        self.live_thread = thread
        self.live_worker = worker
        thread.start()

    def can_render_live_preview(self):
        if self.session is None:
            return False

        map_file = self.session.metadata.get("map_file", "")
        if not map_file or not os.path.exists(map_file):
            return False

        point_count = len(self.session.get_point_summaries())
        map_type = self.current_combo_value(self.live_map_type_combo, "signal")
        required_points = 1 if map_type in {"channel", "dominant"} else 3
        if point_count < required_points:
            return False

        return bool(self.live_ssid_combo.currentText().strip())

    def build_live_map_config(self):
        groups = self.session.get_ap_groups() if self.session is not None else []
        ap_group_map = serialize_ap_group_map(build_bssid_to_manual_group_map(groups))
        ap_group_roles = serialize_ap_group_roles(build_ap_group_role_map(groups))
        return MapConfig(
            ssid=self.live_ssid_combo.currentText().strip(),
            band=self.current_combo_value(self.live_band_combo, "all"),
            map_type=self.current_combo_value(self.live_map_type_combo, "signal"),
            interference_mode=self.current_combo_value(self.live_interference_mode_combo, "intra_ssid"),
            interpolation="rbf",
            aggregation=self.current_combo_value(self.live_aggregation_combo, "max"),
            color_scale="fixed",
            usable_only=self.live_usable_check.isChecked(),
            ap_group_map=ap_group_map,
            ap_group_roles=ap_group_roles,
        ).normalized()

    def get_current_ap_group_map(self):
        if self.session is None:
            return {}

        return build_bssid_to_manual_group_map(self.session.get_ap_groups())

    def get_current_ap_group_roles(self):
        if self.session is None:
            return {}

        return build_ap_group_role_map(self.session.get_ap_groups())

    def build_export_default_config(self):
        if self.session is None:
            return MapConfig()

        ssids = self.session.get_ssids()
        current_ssid = self.live_ssid_combo.currentText().strip()
        if current_ssid not in ssids:
            current_ssid = ssids[0] if ssids else ""

        groups = self.session.get_ap_groups()
        return MapConfig(
            ssid=current_ssid,
            band=self.current_combo_value(self.live_band_combo, "all"),
            map_type=self.current_combo_value(self.live_map_type_combo, "signal"),
            interference_mode=self.current_combo_value(self.live_interference_mode_combo, "intra_ssid"),
            interpolation="rbf",
            aggregation=self.current_combo_value(self.live_aggregation_combo, "max"),
            color_scale="fixed",
            usable_only=self.live_usable_check.isChecked(),
            ap_group_map=serialize_ap_group_map(build_bssid_to_manual_group_map(groups)),
            ap_group_roles=serialize_ap_group_roles(build_ap_group_role_map(groups)),
        ).normalized()

    def build_live_renderer_translations(self):
        return {
            "signal_title": self.tr("map_type_signal"),
            "interference_title": self.tr("map_type_interference"),
            "channel_title": self.tr("map_type_channel"),
            "dominant_title": self.tr("map_type_dominant"),
            "risk": self.tr("interference_top_risk"),
            "serving_ap": self.tr("interference_summary_serving_ap"),
            "serving_channel": self.tr("interference_summary_serving_channel"),
            "interferer": self.tr("interference_summary_interferer"),
            "interferer_channel": self.tr("interference_summary_interferer_channel"),
            "source_rows": self.tr("rows"),
            "reference_ap": self.tr("reference_ap"),
            "reference_channel": self.tr("reference_channel"),
            "ap_group_role": self.tr("ap_group_role"),
            "ap_group_role_internal": self.tr("ap_group_role_internal"),
            "ap_group_role_external": self.tr("ap_group_role_external"),
            "ap_group_role_interferer": self.tr("ap_group_role_interferer"),
            "ap_group_role_test": self.tr("ap_group_role_test"),
            "best": self.tr("best"),
            "confidence": self.tr("confidence"),
            "second_ap": self.tr("second_ap"),
            "second_ap_role": self.tr("second_ap_role"),
            "second_confidence": self.tr("second_confidence"),
            "roaming_overlap": self.tr("dominant_map_roaming_overlap"),
            "ap_position_warning_legend": self.tr("ap_position_warning_legend"),
            "ap_position_distance": self.tr("ap_position_distance"),
            "ap_position_nearest": self.tr("ap_position_nearest"),
            "ap_position_analysis": self.tr("ap_position_analysis"),
            "ap_position_distance_m": self.tr("ap_position_distance_m", distance="{distance}"),
            "ap_position_distance_px": self.tr("ap_position_distance_px", distance="{distance}"),
            "ap_position_ok": self.tr("ap_position_ok"),
            "ap_position_no_scale": self.tr("ap_position_no_scale"),
            "ap_position_strong_far": self.tr("ap_position_strong_far"),
            "ap_position_weak_close": self.tr("ap_position_weak_close"),
            "ap_position_unexpected_dominant": self.tr("ap_position_unexpected_dominant"),
            "ap_position_unknown_warning": self.tr("ap_position_unknown_warning"),
        }

    def finish_live_preview(self, payload):
        self.live_rendering = False
        log_event("qt live render finished", logger_name="main")
        if payload:
            self.live_view.set_payload(payload)
            self.update_live_legend(payload.get("scale_payload"))
            self.live_status_label.setText(self.format_live_status(payload))
        else:
            self.live_view.clear()
            self.clear_live_legend()
            self.live_status_label.setText(self.tr("live_preview_insufficient"))
        self.refresh_live_controls()

        if self.live_dirty and self.live_auto_check.isChecked():
            QTimer.singleShot(0, self.update_live_preview)

    def fail_live_preview(self, message):
        self.live_rendering = False
        log_event(f"qt live render failed message={message}", logger_name="main")
        self.live_status_label.setText(f"{self.tr('error')}: {message}")
        self.clear_live_legend()
        self.refresh_live_controls()

    def cleanup_live_render_thread(self):
        finished_thread = self.sender()
        if finished_thread is self.live_thread:
            self.live_thread = None
            self.live_worker = None
        log_event("qt live render thread cleaned up", logger_name="main")

    def format_live_status(self, payload):
        scale = payload.get("scale_payload", {}) if payload else {}
        title = scale.get("title") or self.tr("live_preview_updated")
        if scale.get("kind") == "gradient":
            suffix = scale.get("suffix", "")
            return (
                f"{self.tr('live_preview_updated')} "
                f"{title}: {scale.get('min')}{suffix} / {scale.get('max')}{suffix}"
            )
        if scale.get("kind") == "swatches":
            return f"{self.tr('live_preview_updated')} {title}: {len(scale.get('items', []))}"
        return self.tr("live_preview_updated")

    def update_live_legend(self, scale_payload):
        self.live_legend_list.clear()
        if not scale_payload:
            self.clear_live_legend()
            return

        self.live_legend_title.setText(str(scale_payload.get("title") or ""))
        kind = scale_payload.get("kind")
        if kind == "swatches":
            for item in scale_payload.get("items", []):
                list_item = QListWidgetItem(str(item.get("label", "")))
                list_item.setIcon(create_marker_icon(
                    item.get("color", "#7f8c8d"),
                    shape=item.get("shape", "circle"),
                    outline_only=bool(item.get("outline_only")),
                ))
                self.live_legend_list.addItem(list_item)
            return

        if kind == "gradient":
            suffix = scale_payload.get("suffix", "")
            item = QListWidgetItem(
                f"{scale_payload.get('min')}{suffix} / {scale_payload.get('max')}{suffix}"
            )
            self.live_legend_list.addItem(item)

    def clear_live_legend(self):
        self.live_legend_title.setText("")
        self.live_legend_list.clear()

    def show_start_page(self):
        self.stack.setCurrentWidget(self.start_page)
        self.status.clearMessage()

    def show_workspace_page(self):
        self.stack.setCurrentWidget(self.workspace_page)
        self.refresh_session_labels()
        self.refresh_points_table()
        self.maybe_update_live_preview()

    def new_survey(self):
        if not self.confirm_switch_survey():
            return False
        self.session = SurveySession()
        self.load_session_ssid_state()
        self.floorplan_view.clear_floorplan()
        self.live_view.clear()
        self.show_workspace_page()
        return True

    def open_survey(self, csv_file=None):
        if not self.confirm_switch_survey():
            return False

        if csv_file is None:
            csv_file, _selected_filter = QFileDialog.getOpenFileName(
                self,
                self.tr("open_existing_survey"),
                "",
                self.tr("qt_survey_file_filter"),
            )
        if not csv_file:
            return False

        try:
            self.session = SurveySession(csv_file)
        except SurveyFormatError as exc:
            self.show_survey_format_error(str(exc))
            return False

        self.load_session_ssid_state()
        self.live_view.clear()
        self.show_workspace_page()
        self.load_saved_plan()
        self.status.showMessage(self.tr("active_survey", name=self.session_display_name()))
        return True

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
            self.live_view.clear()
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
        self.maybe_update_live_preview()

    def zoom_in(self):
        self.floorplan_view.zoom_in()
        self.status.showMessage(self.tr("zoom", zoom=self.floorplan_view.zoom_level))

    def zoom_out(self):
        self.floorplan_view.zoom_out()
        self.status.showMessage(self.tr("zoom", zoom=self.floorplan_view.zoom_level))

    def fit_floorplan(self):
        self.floorplan_view.fit_to_view()
        self.status.showMessage(self.tr("zoom", zoom=self.floorplan_view.zoom_level))

    def start_scale_calibration(self):
        if self.session is None:
            return

        if not self.floorplan_view.has_floorplan():
            QMessageBox.warning(self, self.tr("warning"), self.tr("load_plan_first"))
            return

        if self.floorplan_view.start_scale_calibration_pick():
            self.tabs.setCurrentIndex(0)
            self.status.showMessage(self.tr("calibrate_scale_start"))

    def on_scale_calibration_first_point(self):
        self.status.showMessage(self.tr("calibrate_scale_second_point"))

    def finish_scale_calibration(self, pixel_distance):
        if self.session is None:
            self.floorplan_view.clear_scale_calibration_overlay()
            return

        if pixel_distance <= 0:
            self.floorplan_view.clear_scale_calibration_overlay()
            self.status.showMessage(self.tr("calibrate_scale_invalid"))
            return

        meters, accepted = QInputDialog.getDouble(
            self,
            self.tr("calibrate_scale_title"),
            self.tr("calibrate_scale_distance_prompt"),
            1.0,
            0.01,
            10000.0,
            2,
        )
        self.floorplan_view.clear_scale_calibration_overlay()
        if not accepted or meters <= 0:
            self.status.showMessage(self.tr("calibrate_scale_invalid"))
            return

        px_per_meter = float(pixel_distance) / float(meters)
        self.session.update_metadata({"px_per_meter": f"{px_per_meter:.6f}"})
        self.refresh_session_labels()
        self.status.showMessage(self.tr("calibrate_scale_saved", px_per_meter=px_per_meter))
        self.maybe_update_live_preview()

    def cancel_scale_calibration(self):
        self.status.showMessage(self.tr("calibrate_scale_cancelled"))

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
        if self.live_rendering:
            self.status.showMessage(self.tr("live_preview_rendering"))
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

    def open_generate_map_dialog(self):
        if self.session is None:
            return

        map_file = self.session.metadata.get("map_file", "")
        if not map_file or not os.path.exists(map_file):
            QMessageBox.warning(self, self.tr("warning"), self.tr("load_plan_first"))
            return

        ssids = self.session.get_ssids()
        if not ssids:
            QMessageBox.warning(self, self.tr("warning"), self.tr("no_ssid"))
            return

        dialog = MapGenerationDialog(
            self,
            ssids,
            self.tr,
            current_config=self.build_export_default_config(),
            px_per_meter=self.get_px_per_meter(),
        )
        while dialog.exec() == QDialog.DialogCode.Accepted:
            if self.generate_map_from_dialog(dialog):
                break

    def ensure_saved_for_map_export(self):
        if self.session is None:
            return False

        if not self.session.csv_file:
            QMessageBox.information(
                self,
                self.tr("save_required_title"),
                self.tr("save_required"),
            )

        if self.session.dirty or not self.session.csv_file:
            saved = self.save_survey()
            if not saved:
                self.status.showMessage(self.tr("save_failed"))
            return saved

        return True

    def generate_map_from_dialog(self, dialog):
        if self.session is None:
            return False

        config = dialog.get_config(
            ap_group_map=serialize_ap_group_map(self.get_current_ap_group_map()),
            ap_group_roles=serialize_ap_group_roles(self.get_current_ap_group_roles()),
        )
        if not config.ssid:
            QMessageBox.warning(self, self.tr("warning"), self.tr("select_ssid_heatmap"))
            return False

        if not self.ensure_saved_for_map_export():
            return False

        map_file = self.session.metadata.get("map_file", "")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        result = None
        map_error = None
        unexpected_error = None
        try:
            bg_image = load_floorplan_image(map_file)
            result = generate_map_export(
                self.session.to_dataframe(),
                bg_image,
                self.session.csv_file,
                config,
                self.tr,
                language=self.language,
                aliases=self.session.get_ap_aliases(),
                ap_groups=self.session.get_ap_groups(),
                px_per_meter=self.get_px_per_meter(),
            )
        except MapExportError as exc:
            map_error = exc
        except Exception as exc:
            unexpected_error = exc
        finally:
            QApplication.restoreOverrideCursor()

        if map_error is not None:
            QMessageBox.warning(self, map_error.title, map_error.message)
            return False
        if unexpected_error is not None:
            QMessageBox.critical(self, self.tr("error"), str(unexpected_error))
            return False
        if result is None:
            return False

        QMessageBox.information(
            self,
            self.tr("heatmap_generated"),
            self.format_map_export_result_message(result),
        )
        self.status.showMessage(self.tr("heatmap_generated"))
        return True

    def format_map_export_result_message(self, result):
        files_message = (
            self.tr("files_created", paths="\n".join(result.files))
            if len(result.files) > 1
            else self.tr("file_created", path=result.output_file)
        )
        if result.map_type != "interference" or not result.summary:
            return files_message

        summary = result.summary
        rows = [
            (self.tr("interference_summary_band"), summary.get("band", "-")),
            (self.tr("interference_summary_max_risk"), summary.get("max_risk", "-")),
            (self.tr("interference_summary_point"), summary.get("point", "-")),
            (self.tr("interference_summary_serving_ap"), summary.get("serving_ap", "-")),
            (self.tr("interference_summary_serving_role"), summary.get("serving_role", "-")),
            (self.tr("interference_summary_serving_channel"), summary.get("serving_channel", "-")),
            (self.tr("interference_summary_serving_width"), summary.get("serving_width", "-")),
            (self.tr("interference_summary_interferer"), summary.get("interferer", "-")),
            (self.tr("interference_summary_interferer_role"), summary.get("interferer_role", "-")),
            (self.tr("interference_summary_interferer_ssid"), summary.get("interferer_ssid", "-")),
            (self.tr("interference_summary_interferer_channel"), summary.get("interferer_channel", "-")),
            (self.tr("interference_summary_interferer_width"), summary.get("interferer_width", "-")),
            (self.tr("interference_summary_interferer_dbm"), summary.get("interferer_dbm", "-")),
            (self.tr("interference_summary_test_ignored"), summary.get("test_ignored", "-")),
        ]
        quality = summary.get("quality", {})
        quality_text = self.tr(
            "interference_quality_width_coverage",
            available=quality.get("available", 0),
            total=quality.get("total", 0),
            percent=quality.get("percent", 0),
        )
        details = "\n".join(f"{label}: {value or '-'}" for label, value in rows)
        return (
            f"{self.tr('interference_summary_title')}\n"
            f"{details}\n\n"
            f"{self.tr('interference_summary_diagnosis')}: {summary.get('diagnosis', '-')}\n\n"
            f"{self.tr('interference_quality_title')}: {quality_text}\n"
            f"{summary.get('quality_message', '')}\n\n"
            f"{files_message}"
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

    def clear_relevant_ssids(self):
        if self.session is None:
            return

        changed = bool(self.relevant_ssids or self.known_ssids)
        for key in (RELEVANT_SSIDS_METADATA_KEY, KNOWN_SSIDS_METADATA_KEY):
            if key in self.session.metadata:
                self.session.metadata.pop(key, None)
                changed = True

        self.relevant_ssids = set()
        self.known_ssids = set()
        self.refresh_session_labels()
        self.refresh_points_table()

        if changed:
            self.session.dirty = True
            self.refresh_session_labels()
            self.status.showMessage(self.tr("relevant_networks_cleared"))

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
        log_event(f"qt point scan start x={int(x)} y={int(y)}", logger_name="main")

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
        thread.finished.connect(self.cleanup_wifi_scan_thread)
        thread.finished.connect(thread.deleteLater)
        self.scan_thread = thread
        self.scan_worker = worker
        thread.start()

    def finish_wifi_scan(self, networks, backend_used):
        try:
            x, y = self.pending_scan_point or (None, None)
            self.set_scan_busy(False)
            self.last_scan_backend_used = backend_used
            log_event(f"qt point scan finished backend={backend_used} networks={len(networks or [])}", logger_name="main")

            if x is None or y is None:
                return

            action = self.validate_relevant_networks(networks)
            log_event(f"qt point relevant validation action={action}", logger_name="main")
            if action == "retry":
                self.start_wifi_scan(x, y)
                return
            if action == "cancel":
                self.pending_scan_point = None
                self.status.showMessage(self.tr("cancelled"))
                return

            self.pending_scan_point = None
            self.save_survey_point(x, y, networks)
        except Exception as exc:
            log_exception("finish_wifi_scan failed", exc, logger_name="main")
            self.pending_scan_point = None
            self.set_scan_busy(False)
            QMessageBox.critical(self, self.tr("error"), str(exc))

    def fail_wifi_scan(self, message):
        log_event(f"qt point scan failed message={message}", logger_name="main")
        self.set_scan_busy(False)
        self.pending_scan_point = None
        QMessageBox.critical(self, self.tr("error"), message)

    def cleanup_wifi_scan_thread(self):
        finished_thread = self.sender()
        if finished_thread is self.scan_thread:
            self.scan_thread = None
            self.scan_worker = None
        log_event("qt point scan thread cleaned up", logger_name="main")

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
                connected_ssid=get_connected_ssid(),
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

        log_event(f"qt save point start x={x} y={y} networks={len(networks or [])}", logger_name="main")
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
        self.maybe_update_live_preview()
        log_event(f"qt save point done timestamp={timestamp}", logger_name="main")

    def open_ap_group_manager(self):
        if self.session is None:
            return

        if open_qt_ap_group_manager(self):
            self.refresh_session_labels()
            self.refresh_points_table()
            if not self.floorplan_view.pending_ap_position_group_id:
                self.status.showMessage(self.tr("ap_groups_saved"))
            self.maybe_update_live_preview()

    def open_quality_dashboard(self):
        if self.session is None:
            return

        open_qt_quality_dashboard(self)

    def open_help_dialog(self):
        open_qt_help_dialog(self, self.tr)

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
        self.maybe_update_live_preview()

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

    def select_point_in_table(self, point):
        point_id = str(point.get("point_id", ""))
        timestamp = point.get("timestamp")
        x = point.get("x")
        y = point.get("y")

        for row_index in range(self.points_table.rowCount()):
            item = self.points_table.item(row_index, 0)
            row_point = item.data(Qt.ItemDataRole.UserRole) if item else None
            if not row_point:
                continue

            same_point_id = point_id and str(row_point.get("point_id", "")) == point_id
            same_position = (
                row_point.get("timestamp") == timestamp
                and row_point.get("x") == x
                and row_point.get("y") == y
            )
            if same_point_id or same_position:
                self.points_table.selectRow(row_index)
                self.points_table.scrollToItem(item)
                return True

        return False

    def clear_point_selection(self):
        self.points_table.clearSelection()
        self.update_point_action_state()

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
        self.maybe_update_live_preview()

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
            self.maybe_update_live_preview()
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

        self.csv_label.setText(f"{csv_name}{dirty_suffix}")
        self.map_label.setText(map_name)
        self.points_label.setText(str(point_count))
        self.raw_rows_label.setText(str(raw_count))
        self.ap_groups_label.setText(str(ap_group_count))
        self.relevant_label.setText(relevant_label)
        self.footer_label.setText(
            self.tr(
                "footer_survey_info",
                csv=f"{csv_name}{dirty_suffix}",
                map=map_name,
                points=point_count,
                last=last_point,
            )
        )
        self.new_workspace_button.setEnabled(not self.scan_in_progress)
        self.open_workspace_button.setEnabled(not self.scan_in_progress)
        can_use_session = self.session is not None and not self.scan_in_progress
        self.save_workspace_button.setEnabled(can_use_session)
        self.load_plan_button.setEnabled(can_use_session)
        self.ap_groups_button.setEnabled(can_use_session)
        self.quality_button.setEnabled(can_use_session)
        self.help_button.setEnabled(True)
        self.generate_map_button.setEnabled(can_use_session)
        self.clear_relevant_button.setEnabled(
            can_use_session and bool(self.relevant_ssids or self.known_ssids)
        )
        has_map = self.floorplan_view.has_floorplan()
        self.zoom_in_button.setEnabled(has_map and not self.scan_in_progress)
        self.zoom_out_button.setEnabled(has_map and not self.scan_in_progress)
        self.fit_view_button.setEnabled(has_map and not self.scan_in_progress)
        self.calibrate_button.setEnabled(has_map and not self.scan_in_progress)
        self.update_save_action_state()
        self.refresh_live_controls()
        self.update_point_action_state()

    def update_save_action_state(self):
        is_dirty = bool(self.session is not None and self.session.dirty)
        self.save_workspace_button.setToolTip(
            self.tr("save_dirty_tooltip") if is_dirty else self.tr("save_clean_tooltip")
        )
        if self.save_tool_button is None:
            return

        self.save_tool_button.setObjectName("dirtySaveButton" if is_dirty else "appBarButton")
        self.save_tool_button.style().unpolish(self.save_tool_button)
        self.save_tool_button.style().polish(self.save_tool_button)
        self.save_tool_button.update()

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
                if value:
                    item.setToolTip(value)
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, point)
                if column_index == 4 and self.should_show_quality_tooltip(quality):
                    item.setToolTip(self.build_quality_tooltip_text(quality))
                self.points_table.setItem(row_index, column_index, item)
        self.resize_points_table_columns()
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
    configure_logging()
    log_event("qt app start", logger_name="main")
    install_exception_logging()
    app = QApplication(sys.argv)
    window = WifiHeatmapQtApp()
    window.showMaximized()
    sys.exit(app.exec())


def install_exception_logging():
    def handle_exception(exc_type, exc_value, exc_traceback):
        log_unhandled_exception(exc_type, exc_value, exc_traceback)
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception


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
