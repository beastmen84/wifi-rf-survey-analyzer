"""Main Qt workspace window for surveying, live maps, and analysis tools."""

import json
import os
import sys
import time
from pathlib import Path

try:
    from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QThread, QTimer
    from PySide6.QtGui import QCursor
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QDoubleSpinBox,
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
        QSizePolicy,
        QSplitter,
        QStackedWidget,
        QStatusBar,
        QStyle,
        QStyleOptionButton,
        QStylePainter,
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
from app_restart import start_replacement_process
from app_settings import (
    get_last_survey_directory,
    get_saved_theme,
    get_saved_ui_scale,
    save_last_survey_path,
    save_theme,
    save_ui_scale,
)
from ap_groups import (
    AP_ROLE_TEST,
    build_ap_group_role_map,
    build_bssid_to_manual_group_map,
    format_ap_label,
    normalize_ap_role,
    resolve_ap_group_key,
    serialize_ap_group_map,
    serialize_ap_group_roles,
)
from constants import HEATMAP_MAX_DISTANCE_PX, HEATMAP_SMOOTHING_SIGMA
from map_exporter import MapExportError, generate_live_pdf_export, generate_map_export
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
from qt_live_map import (
    LiveMapRenderWorker,
    LiveMapView,
    create_marker_icon,
    load_floorplan_image,
)
from qt_map_generation import MapGenerationDialog
from qt_point_workflow import MissingRelevantNetworksDialog, RelevantNetworksDialog, WifiScanWorker
from qt_quality_dashboard import open_qt_quality_dashboard
from qt_theme import QT_THEME_OPTIONS, QT_THEMES
from qt_tooltips import build_html_tooltip
from qt_windowing import (
    SKIP_CENTERING_PROPERTY,
    get_centered_open_file_name,
    get_centered_save_file_name,
    install_dialog_centering,
)
from survey_store import SurveyFormatError, SurveySession
from ui_scaling import (
    UI_SCALE_OPTIONS,
    detect_auto_ui_scale_percent,
    format_ui_scale_diagnostics,
    normalize_ui_scale_mode,
    resolve_ui_scale,
    scale_font,
    scale_px,
    ui_scale_diagnostics,
)
from wifi_scanner import get_connected_ssid


RELEVANT_SSIDS_METADATA_KEY = "relevant_ssids"
KNOWN_SSIDS_METADATA_KEY = "known_ssids"


class VerticalTabButton(QPushButton):
    def sizeHint(self):
        hint = super().sizeHint()
        return QSize(max(32, hint.height()), max(88, hint.width() + 10))

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        text = option.text
        option.text = ""
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)

        painter.save()
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(-90)
        text_rect = QRect(-self.height() // 2, -self.width() // 2, self.height(), self.width())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()


class WifiHeatmapQtApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.language = DEFAULT_LANGUAGE
        self.theme = get_saved_theme(default="light", valid_themes=QT_THEMES)
        self.ui_scale_mode = normalize_ui_scale_mode(get_saved_ui_scale())
        self.ui_scale = resolve_ui_scale(self.ui_scale_mode)
        log_event(
            f"workspace ui scale resolved {format_ui_scale_diagnostics(ui_scale_diagnostics(self.ui_scale_mode))}",
            logger_name="ui",
        )
        self.session = None
        self.relevant_ssids = set()
        self.known_ssids = set()
        self.scan_thread = None
        self.scan_worker = None
        self.scan_in_progress = False
        self.pending_scan_point = None
        self.pending_rescan_point = None
        self.last_scan_backend_used = "-"
        self.live_thread = None
        self.live_worker = None
        self.live_rendering = False
        self.live_dirty = False
        self.settings_menu_dialog = None
        self.settings_menu_suppressed_until = 0.0
        self.points_panel_expanded = False
        self.points_overlay_height = 0
        self.points_overlay_resize_active = False
        self.points_overlay_resize_start_y = 0
        self.points_overlay_resize_start_height = 0
        self.live_options_panel_expanded = False
        self.live_map_option_memory = {}
        self.live_current_map_type = "signal"
        self.live_option_state_syncing = False
        self.live_distance_spin_uses_meters = False
        self.live_distance_last_px_per_meter = None
        self.restart_requested = False

        self.setWindowTitle(self.tr("app_title"))
        self.resize(self.spx(1400), self.spx(900))

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

    def spx(self, value):
        return scale_px(value, self.ui_scale)

    def spt(self, value):
        return scale_font(value, self.ui_scale)

    def get_px_per_meter(self):
        if self.session is None:
            return None

        try:
            value = float(self.session.metadata.get("px_per_meter", ""))
        except (TypeError, ValueError):
            return None

        return value if value > 0 else None

    def has_calibrated_scale(self):
        return self.get_px_per_meter() is not None

    def build_start_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(self.spx(48), self.spx(40), self.spx(48), self.spx(32))

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
        panel_layout.setContentsMargins(self.spx(32), self.spx(32), self.spx(32), self.spx(32))
        panel_layout.setHorizontalSpacing(self.spx(28))
        panel_layout.setVerticalSpacing(self.spx(14))

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
            button.setMinimumHeight(self.spx(42))
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
        footer_layout.setContentsMargins(self.spx(12), self.spx(6), self.spx(12), self.spx(6))
        self.footer_label = QLabel()
        self.footer_label.setObjectName("mutedText")
        footer_layout.addWidget(self.footer_label)
        layout.addWidget(footer)

        return page

    def build_app_bar(self):
        bar = QFrame()
        bar.setObjectName("appBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(self.spx(14), self.spx(10), self.spx(14), self.spx(10))
        layout.setSpacing(self.spx(10))

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
        layout.addWidget(project_section, 1)

        view_section, self.view_section_label, view_row = self.build_app_bar_section()
        self.zoom_out_button = self.create_app_bar_button(self.zoom_out, "appBarIconButton")
        self.zoom_in_button = self.create_app_bar_button(self.zoom_in, "appBarIconButton")
        self.fit_view_button = self.create_app_bar_button(self.fit_floorplan)
        self.calibrate_button = self.create_app_bar_button(self.start_scale_calibration)
        self.delete_scale_button = QPushButton()
        self.delete_scale_button.setObjectName("appBarTitleDangerButton")
        self.delete_scale_button.clicked.connect(self.delete_scale_calibration)
        self.delete_scale_button.setMaximumWidth(self.spx(116))
        view_section.title_row.addWidget(self.delete_scale_button)
        for button in (
            self.zoom_out_button,
            self.zoom_in_button,
            self.fit_view_button,
            self.calibrate_button,
        ):
            view_row.addWidget(button)
        layout.addWidget(view_section, 1)

        analysis_section, self.analysis_section_label, analysis_row = self.build_app_bar_section()
        self.ap_groups_button = self.create_app_bar_button(self.open_ap_group_manager)
        self.quality_button = self.create_app_bar_button(self.open_quality_dashboard)
        self.help_button = self.create_app_bar_button(self.open_help_dialog)
        for button in (
            self.ap_groups_button,
            self.quality_button,
            self.help_button,
        ):
            analysis_row.addWidget(button)
        layout.addWidget(analysis_section)

        self.settings_menu_button = self.create_app_bar_button(self.open_settings_menu, "appBarSettingsButton")
        self.settings_menu_button.setMinimumHeight(self.app_bar_control_height())
        layout.addWidget(self.settings_menu_button)

        return bar

    def app_bar_control_height(self):
        return self.spx(68)

    def build_app_bar_section(self):
        section = QFrame()
        section.setObjectName("appBarSection")
        section.setMinimumHeight(self.app_bar_control_height())
        outer = QVBoxLayout(section)
        outer.setContentsMargins(self.spx(10), self.spx(7), self.spx(10), self.spx(8))
        outer.setSpacing(self.spx(5))

        title = QLabel()
        title.setObjectName("appBarSectionTitle")
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(self.spx(6))
        title_row.addWidget(title)
        title_row.addStretch(1)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(self.spx(6))

        outer.addLayout(title_row)
        outer.addLayout(row)
        section.title_row = title_row
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
        layout.setContentsMargins(self.spx(7), self.spx(4), self.spx(7), self.spx(5))
        layout.setSpacing(self.spx(1))

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
            title_row.setSpacing(self.spx(4))
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
        layout.setContentsMargins(self.spx(16), self.spx(16), self.spx(16), self.spx(16))
        layout.setSpacing(self.spx(12))

        summary = QFrame()
        summary.setObjectName("summaryPanel")
        self.summary_title_bindings = []
        grid = QGridLayout(summary)
        grid.setContentsMargins(self.spx(8), self.spx(8), self.spx(8), self.spx(8))
        grid.setHorizontalSpacing(self.spx(6))
        grid.setVerticalSpacing(self.spx(6))

        self.manage_relevant_button = QPushButton()
        self.clear_relevant_button = QPushButton()
        relevant_actions = QWidget()
        relevant_actions_layout = QHBoxLayout(relevant_actions)
        relevant_actions_layout.setContentsMargins(0, 0, 0, 0)
        relevant_actions_layout.setSpacing(self.spx(4))
        relevant_actions_layout.addWidget(self.manage_relevant_button)
        relevant_actions_layout.addWidget(self.clear_relevant_button)
        self.manage_relevant_button.setObjectName("summaryActionButton")
        self.clear_relevant_button.setObjectName("summaryActionButton")
        self.manage_relevant_button.setMaximumWidth(self.spx(76))
        self.clear_relevant_button.setMaximumWidth(self.spx(64))
        self.manage_relevant_button.clicked.connect(self.manage_relevant_ssids)
        self.clear_relevant_button.clicked.connect(self.clear_relevant_ssids)
        csv_card, self.csv_label, _csv_layout = self.create_summary_card("qt_csv")
        map_card, self.map_label, _map_layout = self.create_summary_card("map")
        points_card, self.points_label, _points_layout = self.create_summary_card("qt_points", compact=True)
        raw_card, self.raw_rows_label, _raw_layout = self.create_summary_card("qt_raw_rows", compact=True)
        ap_card, self.ap_groups_label, _ap_layout = self.create_summary_card("summary_ap_groups", compact=True)
        relevant_card, self.relevant_label, _relevant_layout = self.create_summary_card(
            "saved_network",
            action_widget=relevant_actions,
        )
        for card in (points_card, raw_card, ap_card):
            card.setMaximumWidth(self.spx(112))
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
        floorplan_layout.setContentsMargins(self.spx(1), self.spx(1), self.spx(1), self.spx(1))
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
        overlay_layout.setContentsMargins(self.spx(8), self.spx(8), self.spx(8), self.spx(8))
        overlay_layout.setSpacing(self.spx(6))

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
        table_layout.setSpacing(self.spx(8))

        self.points_table = QTableWidget(0, 8)
        self.points_table.setAlternatingRowColors(True)
        self.points_table.setShowGrid(False)
        self.points_table.setWordWrap(False)
        self.points_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.points_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.points_table.verticalHeader().setVisible(False)
        self.points_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.points_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.points_table.horizontalHeader().setStretchLastSection(False)
        self.points_table.horizontalHeader().setMinimumSectionSize(self.spx(34))
        self.configure_points_table_columns()
        self.points_table.itemSelectionChanged.connect(self.on_points_table_selection_changed)
        self.points_table.itemDoubleClicked.connect(lambda _item: self.focus_selected_point())
        table_layout.addWidget(self.points_table)

        point_buttons = QHBoxLayout()
        self.focus_point_button = QPushButton()
        self.rescan_point_button = QPushButton()
        self.delete_selected_button = QPushButton()
        self.delete_last_button = QPushButton()
        for button in (
            self.focus_point_button,
            self.rescan_point_button,
            self.delete_selected_button,
            self.delete_last_button,
        ):
            button.setObjectName("pointsActionButton")
        self.focus_point_button.clicked.connect(self.focus_selected_point)
        self.rescan_point_button.clicked.connect(self.rescan_selected_point)
        self.delete_selected_button.clicked.connect(self.delete_selected_point)
        self.delete_last_button.clicked.connect(self.delete_last_point)
        point_buttons.addWidget(self.focus_point_button)
        point_buttons.addWidget(self.rescan_point_button)
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

    def show_points_panel(self):
        if self.points_panel_expanded:
            self.position_points_overlay()
            return

        self.points_panel_expanded = True
        if not self.points_overlay_height:
            self.points_overlay_height = self.default_points_overlay_height()
        self.points_table_body.setVisible(True)
        self.points_panel_resize_button.setVisible(True)
        self.update_points_panel_toggle()
        self.position_points_overlay()

    def update_points_panel_toggle(self):
        if not hasattr(self, "points_panel_toggle_button"):
            return
        key = "points_panel_hide" if self.points_panel_expanded else "points_panel_show"
        self.points_panel_toggle_button.setText(self.tr(key))
        if hasattr(self, "points_overlay"):
            self.points_overlay.setObjectName(
                "floatingPointsPanel" if self.points_panel_expanded else "floatingPointsPanelCollapsed"
            )
            self.points_overlay.style().unpolish(self.points_overlay)
            self.points_overlay.style().polish(self.points_overlay)
            self.points_overlay.update()
        if hasattr(self, "points_panel_resize_button"):
            self.points_panel_resize_button.setToolTip(self.tr("points_panel_resize"))

    def default_points_overlay_height(self):
        row_height = max(self.spx(24), self.points_table.verticalHeader().defaultSectionSize())
        header_height = max(self.spx(28), self.points_table.horizontalHeader().height())
        button_height = max(self.spx(34), self.focus_point_button.sizeHint().height())
        handle_height = max(self.spx(34), self.points_panel_toggle_button.sizeHint().height())
        return handle_height + header_height + (row_height * 6) + button_height + self.spx(44)

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

        margin = self.spx(16)
        if self.points_panel_expanded:
            default_height = self.default_points_overlay_height()
            max_height = self.max_points_overlay_height()
            if not self.points_overlay_height:
                self.points_overlay_height = default_height
            self.points_overlay_height = max(default_height, min(self.points_overlay_height, max_height))
            width = min(max(self.spx(760), int(container_width * 0.84)), max(self.spx(320), container_width - (margin * 2)))
            height = min(self.points_overlay_height, max(self.spx(170), container_height - (margin * 2)))
        else:
            width = min(self.spx(280), max(self.spx(240), container_width - (margin * 2)))
            height = max(self.spx(50), self.points_panel_toggle_button.sizeHint().height() + self.spx(16))

        x = max(margin, (container_width - width) // 2)
        y = max(margin, container_height - height - margin)
        self.points_overlay.setGeometry(x, y, width, height)
        self.points_overlay.raise_()

    def eventFilter(self, source, event):
        if source is getattr(self, "floorplan_container", None) and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self.position_points_overlay)
            return False

        if source is getattr(self, "live_view_container", None) and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self.position_live_options_overlay)
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
            0: (self.spx(42), self.spx(54)),
            1: (self.spx(50), self.spx(64)),
            2: (self.spx(50), self.spx(64)),
            3: (self.spx(92), self.spx(116)),
            4: (self.spx(110), self.spx(150)),
            6: (self.spx(54), self.spx(72)),
            7: (self.spx(140), self.spx(180)),
        }
        header = self.points_table.horizontalHeader()
        for column, (minimum, maximum) in compact_limits.items():
            width = self.points_table.columnWidth(column)
            width = max(minimum, min(width + self.spx(10), maximum))
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.points_table.setColumnWidth(column, width)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

    def build_live_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(self.spx(16), self.spx(16), self.spx(16), self.spx(16))
        layout.setSpacing(self.spx(12))

        self.live_ssid_label = QLabel()
        self.live_ssid_combo = QComboBox()
        self.live_ssid_combo.setMinimumWidth(self.spx(220))
        self.live_band_label = QLabel()
        self.live_band_combo = QComboBox()
        self.live_map_type_label = QLabel()
        self.live_map_type_combo = QComboBox()
        self.live_aggregation_label = QLabel()
        self.live_aggregation_combo = QComboBox()
        self.live_interpolation_label = QLabel()
        self.live_interpolation_combo = QComboBox()
        self.live_interference_mode_label = QLabel()
        self.live_interference_mode_combo = QComboBox()
        self.live_point_labels_label = QLabel()
        self.live_point_labels_combo = QComboBox()
        self.live_color_scale_label = QLabel()
        self.live_color_scale_combo = QComboBox()
        self.live_smoothing_label = QLabel()
        self.live_smoothing_spin = QDoubleSpinBox()
        self.live_max_distance_label = QLabel()
        self.live_max_distance_spin = QDoubleSpinBox()
        self.live_ap_group_label = QLabel()
        self.live_ap_group_combo = QComboBox()
        self.live_ap_group_combo.setMinimumWidth(self.spx(220))
        self.live_usable_check = QCheckBox()
        self.live_usable_check.setObjectName("liveOptionCheckbox")
        self.live_usable_check.setContentsMargins(0, 0, 0, 0)
        self.live_auto_check = QCheckBox()
        self.live_auto_check.setChecked(True)
        self.live_pdf_export_button = QPushButton()
        self.live_pdf_export_button.setObjectName("compactButton")
        self.live_pdf_export_button.setMinimumWidth(self.spx(118))
        self.live_pdf_export_button.setEnabled(False)
        self.live_pdf_export_button.clicked.connect(self.export_live_pdf)
        self.live_update_button = QPushButton()
        self.live_update_button.setObjectName("compactButton")
        self.live_update_button.setMinimumWidth(self.spx(132))
        self.live_update_button.clicked.connect(self.update_live_preview)
        self.live_export_separator = QFrame()
        self.live_export_separator.setObjectName("toolbarSeparator")
        self.live_export_separator.setFrameShape(QFrame.Shape.VLine)
        self.live_export_separator.setFrameShadow(QFrame.Shadow.Plain)
        self.live_export_separator.setFixedHeight(self.spx(28))
        self.live_smoothing_spin.setRange(0.0, 12.0)
        self.live_smoothing_spin.setSingleStep(0.5)
        self.live_smoothing_spin.setDecimals(1)
        self.live_smoothing_spin.setValue(float(HEATMAP_SMOOTHING_SIGMA))
        self.live_max_distance_spin.setRange(40.0, 1000.0)
        self.live_max_distance_spin.setSingleStep(20.0)
        self.live_max_distance_spin.setDecimals(0)
        self.live_max_distance_spin.setValue(float(HEATMAP_MAX_DISTANCE_PX))
        self.live_option_widgets = (
            self.live_band_label,
            self.live_band_combo,
            self.live_aggregation_label,
            self.live_aggregation_combo,
            self.live_color_scale_label,
            self.live_color_scale_combo,
            self.live_interpolation_label,
            self.live_interpolation_combo,
            self.live_interference_mode_label,
            self.live_interference_mode_combo,
            self.live_smoothing_label,
            self.live_smoothing_spin,
            self.live_max_distance_label,
            self.live_max_distance_spin,
            self.live_point_labels_label,
            self.live_point_labels_combo,
            self.live_usable_check,
            self.live_ap_group_label,
            self.live_ap_group_combo,
        )

        for combo in (
            self.live_ssid_combo,
            self.live_band_combo,
            self.live_map_type_combo,
            self.live_aggregation_combo,
            self.live_color_scale_combo,
            self.live_interpolation_combo,
            self.live_interference_mode_combo,
            self.live_point_labels_combo,
            self.live_ap_group_combo,
        ):
            combo.currentIndexChanged.connect(lambda *_args: self.on_live_option_changed())
        for spin in (self.live_smoothing_spin, self.live_max_distance_spin):
            spin.valueChanged.connect(lambda *_args: self.on_live_option_changed())
        self.live_usable_check.toggled.connect(lambda *_args: self.on_live_option_changed())
        self.live_auto_check.toggled.connect(lambda *_args: self.on_live_option_changed())

        toolbar = QFrame()
        toolbar.setObjectName("summaryPanel")
        self.live_toolbar_frame = toolbar
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(self.spx(14), self.spx(10), self.spx(14), self.spx(10))
        toolbar_layout.setSpacing(self.spx(10))
        toolbar_layout.addWidget(self.live_map_type_label)
        toolbar_layout.addWidget(self.live_map_type_combo)
        toolbar_layout.addWidget(self.live_ssid_label)
        toolbar_layout.addWidget(self.live_ssid_combo)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.live_export_separator)
        toolbar_layout.addWidget(self.live_pdf_export_button)
        toolbar_layout.addWidget(self.live_update_button)
        toolbar_layout.addWidget(self.live_auto_check)
        layout.addWidget(toolbar)

        live_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.live_view_container = QFrame()
        self.live_view_container.setObjectName("floorplanContainer")
        self.live_view_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.live_view_container.installEventFilter(self)
        live_view_layout = QVBoxLayout(self.live_view_container)
        live_view_layout.setContentsMargins(0, 0, 0, 0)
        live_view_layout.setSpacing(0)
        self.live_view = LiveMapView()
        self.live_view.backgroundClicked.connect(self.clear_live_marker_selection)
        live_view_layout.addWidget(self.live_view)
        self.build_live_options_overlay()
        live_splitter.addWidget(self.live_view_container)

        self.live_legend_frame = QFrame()
        self.live_legend_frame.setObjectName("summaryPanel")
        self.live_legend_frame.setMinimumWidth(self.spx(260))
        self.live_legend_frame.setMaximumWidth(self.spx(360))
        legend_layout = QVBoxLayout(self.live_legend_frame)
        legend_layout.setContentsMargins(self.spx(12), self.spx(10), self.spx(12), self.spx(10))
        legend_layout.setSpacing(self.spx(8))
        self.live_legend_title = QLabel()
        self.live_legend_title.setObjectName("sectionTitle")
        self.live_legend_list = QListWidget()
        self.live_legend_list.setAlternatingRowColors(True)
        self.live_legend_list.setWordWrap(True)
        self.live_legend_list.itemClicked.connect(self.on_live_legend_item_clicked)
        self.live_legend_list.itemDoubleClicked.connect(self.on_live_legend_item_double_clicked)
        legend_layout.addWidget(self.live_legend_title)
        legend_layout.addWidget(self.live_legend_list, 1)
        live_splitter.addWidget(self.live_legend_frame)
        self.live_legend_frame.hide()
        live_splitter.setStretchFactor(0, 1)
        live_splitter.setStretchFactor(1, 0)
        layout.addWidget(live_splitter, 1)

        status_row = QHBoxLayout()
        self.live_status_label = QLabel()
        self.live_status_label.setObjectName("mutedText")
        status_row.addWidget(self.live_status_label, 1)
        layout.addLayout(status_row)
        QTimer.singleShot(0, self.position_live_options_overlay)
        return tab

    def build_live_options_overlay(self):
        self.live_options_overlay = QFrame(self.live_view_container)
        self.live_options_overlay.setObjectName("floatingLiveOptionsPanelCollapsed")
        self.live_options_overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        overlay_layout = QHBoxLayout(self.live_options_overlay)
        overlay_layout.setContentsMargins(self.spx(4), self.spx(6), self.spx(6), self.spx(6))
        overlay_layout.setSpacing(self.spx(7))

        self.live_options_toggle_button = VerticalTabButton()
        self.live_options_toggle_button.setObjectName("liveOptionsPanelToggle")
        self.live_options_toggle_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.live_options_toggle_button.setFixedSize(self.spx(26), self.spx(78))
        self.live_options_toggle_button.clicked.connect(self.toggle_live_options_panel)
        overlay_layout.addWidget(self.live_options_toggle_button)
        overlay_layout.setAlignment(self.live_options_toggle_button, Qt.AlignmentFlag.AlignVCenter)

        self.live_options_body = QWidget()
        self.live_options_body.setObjectName("liveOptionsBody")
        self.live_options_body.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.live_options_layout = QGridLayout(self.live_options_body)
        self.live_options_layout.setContentsMargins(self.spx(4), self.spx(2), self.spx(8), self.spx(4))
        self.live_options_layout.setHorizontalSpacing(self.spx(12))
        self.live_options_layout.setVerticalSpacing(self.spx(8))
        self.live_options_layout.setColumnMinimumWidth(0, self.spx(118))
        self.live_options_layout.setColumnStretch(1, 0)
        overlay_layout.addWidget(self.live_options_body)
        overlay_layout.setAlignment(self.live_options_body, Qt.AlignmentFlag.AlignVCenter)
        self.live_options_body.setVisible(False)
        self.live_options_separator = QFrame()
        self.live_options_separator.setObjectName("liveOptionsSeparator")
        self.live_options_separator.setFrameShape(QFrame.Shape.NoFrame)
        self.live_options_separator.setFixedHeight(self.spx(1))
        self.live_options_separator.hide()
        self.update_live_options_panel_toggle()

    def toggle_live_options_panel(self):
        self.live_options_panel_expanded = not self.live_options_panel_expanded
        self.live_options_body.setVisible(self.live_options_panel_expanded)
        self.update_live_options_panel_toggle()
        self.position_live_options_overlay()

    def update_live_options_panel_toggle(self):
        if not hasattr(self, "live_options_toggle_button"):
            return

        key = "live_options_hide" if self.live_options_panel_expanded else "live_options_show"
        self.live_options_toggle_button.setText(self.tr(key))
        if hasattr(self, "live_options_overlay"):
            self.live_options_overlay.setObjectName(
                "floatingLiveOptionsPanel" if self.live_options_panel_expanded else "floatingLiveOptionsPanelCollapsed"
            )
            self.live_options_overlay.style().unpolish(self.live_options_overlay)
            self.live_options_overlay.style().polish(self.live_options_overlay)
            self.live_options_overlay.update()

    def position_live_options_overlay(self):
        if not hasattr(self, "live_options_overlay"):
            return

        container_width = self.live_view_container.width()
        container_height = self.live_view_container.height()
        if container_width <= 0 or container_height <= 0:
            return

        margin = self.spx(16)
        if self.live_options_panel_expanded:
            expanded_min_height = self.spx(214)
            desired_width = max(self.spx(288), self.live_options_overlay.sizeHint().width())
            width = min(desired_width, max(self.spx(288), container_width - margin * 2))
            height = min(
                max(expanded_min_height, self.live_options_overlay.sizeHint().height()),
                max(expanded_min_height, container_height - margin * 2),
            )
        else:
            width = max(self.spx(34), self.live_options_toggle_button.width() + self.spx(8))
            height = max(self.spx(86), self.live_options_toggle_button.height() + self.spx(8))

        x = self.spx(3)
        y = max(margin, (container_height - height) // 2)
        self.live_options_overlay.setGeometry(x, y, width, height)
        self.live_options_overlay.raise_()

    def apply_styles(self):
        palette = QT_THEMES.get(self.theme, QT_THEMES["light"])
        combo_arrow_icon = (Path(__file__).resolve().parent / "images" / "combo_arrow_white.svg").as_posix()
        s = self.spx
        font = self.spt
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{
                background: {palette["bg"]};
                color: {palette["text"]};
                font-family: Segoe UI;
                font-size: {font(10.5)}pt;
            }}
            QLabel, QCheckBox {{
                background: transparent;
            }}
            QFrame#startPanel, QFrame#summaryPanel {{
                background: {palette["panel"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(8)}px;
            }}
            QFrame#footer {{
                background: {palette["footer"]};
                border-top: 1px solid {palette["border"]};
            }}
            QFrame#metricBox {{
                background: {palette["panel"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(6)}px;
            }}
            QFrame#floorplanContainer {{
                background: {palette["live_bg"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(8)}px;
            }}
            QGraphicsView#floorplanView {{
                background: {palette["live_bg"]};
                border: 0;
                border-radius: {s(8)}px;
            }}
            QFrame#floatingPointsPanel {{
                background: {palette["panel"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(10)}px;
            }}
            QFrame#floatingPointsPanelCollapsed {{
                background: transparent;
                border: 0;
            }}
            QFrame#floatingLiveOptionsPanel {{
                background: {palette["panel"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(10)}px;
            }}
            QFrame#floatingLiveOptionsPanelCollapsed {{
                background: transparent;
                border: 0;
            }}
            QDialog#settingsMenuPanel, QWidget#settingsMenuPanel {{
                background: {palette["panel"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(8)}px;
            }}
            QLabel#settingsMenuLabel {{
                color: {palette["muted"]};
                font-weight: 700;
            }}
            QComboBox QAbstractItemView {{
                background: {palette["panel"]};
                color: {palette["text"]};
                selection-background-color: {palette["selection"]};
                selection-color: {palette["text"]};
                border: 1px solid {palette["border"]};
                outline: 0;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: {s(24)}px;
                padding: {s(4)}px {s(8)}px;
            }}
            QWidget#pointsTableBody {{
                background: transparent;
            }}
            QWidget#liveOptionsBody {{
                background: transparent;
            }}
            QFrame#liveOptionsSeparator {{
                background: {palette["border"]};
                border: 0;
                min-height: {s(1)}px;
                max-height: {s(1)}px;
            }}
            QFrame#toolbarSeparator {{
                color: {palette["border"]};
                background: {palette["border"]};
                border: 0;
                min-width: {s(1)}px;
                max-width: {s(1)}px;
            }}
            QCheckBox#liveOptionCheckbox {{
                margin-left: 0;
                padding-left: 0;
                spacing: {s(8)}px;
            }}
            QCheckBox#liveOptionCheckbox::indicator {{
                margin-left: 0;
            }}
            QPushButton#pointsPanelToggle {{
                min-width: {s(190)}px;
                min-height: {s(30)}px;
                padding: {s(6)}px {s(18)}px;
                border-radius: {s(15)}px;
                background: {palette["metric_info"]};
                color: #FFFFFF;
                border: 1px solid {palette["metric_info"]};
                font-weight: 700;
            }}
            QPushButton#liveOptionsPanelToggle {{
                min-width: {s(26)}px;
                max-width: {s(30)}px;
                min-height: {s(76)}px;
                max-height: {s(90)}px;
                padding: {s(3)}px {s(1)}px;
                border-radius: {s(5)}px;
                background: {palette["metric_info"]};
                color: #FFFFFF;
                border: 1px solid {palette["metric_info"]};
                font-weight: 700;
            }}
            QPushButton#pointsPanelResize {{
                min-width: {s(30)}px;
                max-width: {s(34)}px;
                padding: {s(6)}px 0;
                border-radius: {s(14)}px;
                background: {palette["button_bg"]};
                color: {palette["muted"]};
                border: 1px solid {palette["border"]};
                font-weight: 700;
            }}
            QPushButton#pointsActionButton {{
                min-width: 0;
                padding: {s(6)}px {s(10)}px;
            }}
            QFrame#summaryCard, QFrame#summaryCardCompact {{
                background: {palette["panel_alt"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(5)}px;
            }}
            QLabel#summaryCardTitle {{
                color: {palette["muted"]};
                font-size: {font(8)}pt;
                font-weight: 700;
            }}
            QLabel#summaryCardValue {{
                color: {palette["title"]};
                font-size: {font(10)}pt;
                font-weight: 600;
            }}
            QLabel#summaryCardCompactValue {{
                color: {palette["title"]};
                font-size: {font(14)}pt;
                font-weight: 600;
            }}
            QLabel#startTitle {{
                font-size: {font(25)}pt;
                font-weight: 700;
                color: {palette["title"]};
            }}
            QLabel#sectionTitle {{
                font-size: {font(13)}pt;
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
                border-radius: {s(5)}px;
                padding: {s(5)}px {s(8)}px;
            }}
            QLabel#metricValue_good {{
                color: {palette["metric_good"]};
                font-size: {font(18)}pt;
                font-weight: 700;
            }}
            QLabel#metricValue_warning {{
                color: {palette["metric_warning"]};
                font-size: {font(18)}pt;
                font-weight: 700;
            }}
            QLabel#metricValue_danger {{
                color: {palette["metric_danger"]};
                font-size: {font(18)}pt;
                font-weight: 700;
            }}
            QLabel#metricValue_info {{
                color: {palette["metric_info"]};
                font-size: {font(18)}pt;
                font-weight: 700;
            }}
            QPushButton {{
                background: {palette["button_bg"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(5)}px;
                min-width: {s(240)}px;
                padding: {s(8)}px {s(12)}px;
            }}
            QPushButton:hover {{
                background: {palette["button_hover"]};
            }}
            QPushButton:disabled {{
                color: {palette["muted"]};
            }}
            QPushButton#compactButton {{
                min-width: 0;
                padding: {s(5)}px {s(8)}px;
            }}
            QPushButton#summaryActionButton {{
                min-width: 0;
                padding: {s(2)}px {s(6)}px;
                border-radius: {s(4)}px;
                font-size: {font(8)}pt;
                font-weight: 600;
            }}
            QPushButton#appBarTitleDangerButton {{
                min-width: 0;
                padding: {s(2)}px {s(7)}px;
                border-radius: {s(4)}px;
                font-size: {font(8)}pt;
                font-weight: 700;
                background: {palette["save_dirty_bg"]};
                color: {palette["save_dirty_text"]};
                border: 1px solid {palette["save_dirty_border"]};
            }}
            QPushButton#appBarTitleDangerButton:disabled {{
                background: {palette["panel_alt"]};
                color: {palette["muted"]};
                border: 1px solid {palette["border"]};
            }}
            QFrame#appBar {{
                background: {palette["toolbar"]};
                border-bottom: 1px solid {palette["border"]};
            }}
            QFrame#appBarSection {{
                background: {palette["panel"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(6)}px;
            }}
            QLabel#appBarSectionTitle {{
                color: {palette["muted"]};
                font-size: {font(8.5)}pt;
                font-weight: 700;
            }}
            QLabel#appBarInlineLabel {{
                color: {palette["muted"]};
                font-size: {font(9)}pt;
                font-weight: 600;
            }}
            QPushButton#appBarButton, QPushButton#appBarIconButton, QPushButton#primaryAppBarButton, QPushButton#dirtySaveButton {{
                min-width: 0;
                padding: {s(6)}px {s(10)}px;
                border-radius: {s(5)}px;
                font-weight: 600;
            }}
            QPushButton#appBarSettingsButton {{
                min-width: 0;
                min-height: {s(68)}px;
                padding: {s(6)}px {s(14)}px;
                border-radius: {s(6)}px;
                font-weight: 700;
                background: {palette["panel"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
            }}
            QPushButton#appBarSettingsButton:hover {{
                background: {palette["button_hover"]};
            }}
            QPushButton#appBarIconButton {{
                min-width: {s(30)}px;
                max-width: {s(34)}px;
                min-height: {s(30)}px;
                max-height: {s(30)}px;
                padding: 0;
                font-size: {font(12)}pt;
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
                border-radius: {s(5)}px;
                padding: {s(5)}px {s(8)}px;
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
                border-radius: {s(4)}px;
                padding: {s(4)}px {s(28)}px {s(4)}px {s(8)}px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: {s(22)}px;
                border-left: 1px solid {palette["metric_info"]};
                border-top-right-radius: {s(4)}px;
                border-bottom-right-radius: {s(4)}px;
                background: {palette["metric_info"]};
            }}
            QComboBox::down-arrow {{
                image: url("{combo_arrow_icon}");
                width: {s(10)}px;
                height: {s(6)}px;
            }}
            QComboBox QAbstractItemView {{
                background: {palette["panel"]};
                color: {palette["text"]};
                selection-background-color: {palette["selection"]};
            }}
            QCheckBox {{
                color: {palette["text"]};
                spacing: {s(9)}px;
                padding: {s(3)}px {s(2)}px;
            }}
            QCheckBox::indicator {{
                width: {s(18)}px;
                height: {s(18)}px;
                border-radius: {s(4)}px;
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
                padding: {s(7)}px {s(16)}px;
                margin-right: {s(2)}px;
                border-top-left-radius: {s(5)}px;
                border-top-right-radius: {s(5)}px;
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
                padding: {s(4)}px {s(6)}px;
            }}
            QTableWidget::item:selected {{
                background: {palette["selection"]};
                color: {palette["text"]};
            }}
            QTableWidget::item:focus {{
                border: 0;
                border-bottom: 1px solid {palette["border"]};
            }}
            QGraphicsView#liveMapView {{
                background: {palette["live_bg"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(4)}px;
            }}
            QListWidget {{
                background: {palette["panel"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(4)}px;
                padding: {s(4)}px;
            }}
            QListWidget::item {{
                padding: {s(4)}px;
            }}
            QHeaderView::section {{
                background: {palette["header"]};
                color: {palette["text"]};
                padding: {s(5)}px;
                border: 0;
                border-right: 1px solid {palette["border"]};
                font-weight: 600;
            }}
            QToolTip {{
                background: {palette["panel"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                padding: {s(5)}px;
            }}
            """
        )

    def retranslate(self):
        self.setWindowTitle(self.tr("app_title"))
        self.start_language_label.setText(self.tr("language"))
        self.project_section_label.setText(self.tr("toolbar_project"))
        self.view_section_label.setText(self.tr("toolbar_view"))
        self.analysis_section_label.setText(self.tr("toolbar_analysis"))
        self.settings_menu_button.setText(self.tr("toolbar_settings"))
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
        self.delete_scale_button.setText(self.tr("delete_scale"))
        self.ap_groups_button.setText(self.tr("ap_groups_title"))
        self.quality_button.setText(self.tr("quality_dashboard_title"))
        self.help_button.setText(self.tr("help"))
        self.focus_point_button.setText(self.tr("go_to_point"))
        self.rescan_point_button.setText(self.tr("rescan_point"))
        self.delete_selected_button.setText(self.tr("delete_selected"))
        self.delete_last_button.setText(self.tr("delete_last"))
        self.update_points_panel_toggle()
        self.update_live_options_panel_toggle()
        self.manage_relevant_button.setText(self.tr("manage_relevant_networks"))
        self.clear_relevant_button.setText(self.tr("forget_saved_network"))
        self.tabs.setTabText(0, self.tr("survey_tab"))
        self.tabs.setTabText(1, self.tr("live_map_tab"))
        self.live_ssid_label.setText("SSID")
        self.live_band_label.setText(self.tr("band"))
        self.live_map_type_label.setText(self.tr("map_type"))
        self.live_aggregation_label.setText(self.tr("aggregation"))
        self.live_color_scale_label.setText(self.tr("color_scale"))
        self.live_interpolation_label.setText(self.tr("interpolation"))
        self.live_interference_mode_label.setText(self.tr("interference_mode"))
        self.live_smoothing_label.setText(self.tr("smoothing"))
        self.update_live_max_distance_label()
        self.live_point_labels_label.setText(self.tr("point_labels"))
        self.live_ap_group_label.setText(self.tr("ap_group_filter"))
        self.live_usable_check.setText(self.tr("usable_only"))
        self.live_auto_check.setText(self.tr("live_auto_update"))
        self.live_pdf_export_button.setText(self.tr("live_export_pdf"))
        self.live_update_button.setText(self.tr("live_update_now"))
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

    def change_language(self, value):
        language = normalize_language(value)
        if language == self.language:
            return

        self.language = language
        self.start_language_combo.blockSignals(True)
        self.start_language_combo.setCurrentText(language.upper())
        self.start_language_combo.blockSignals(False)
        self.retranslate()
        if self.session is not None:
            self.floorplan_view.set_ap_groups(self.session.get_ap_groups())
            self.refresh_live_controls()
            self.maybe_update_live_preview()

    def change_theme(self, theme):
        if theme not in QT_THEMES or theme == self.theme:
            return

        self.theme = theme
        save_theme(theme)
        log_event(f"workspace theme changed theme={theme}", logger_name="ui")
        self.apply_styles()

    def change_ui_scale(self, mode):
        mode = normalize_ui_scale_mode(mode)
        if mode == self.ui_scale_mode:
            return

        if self.scan_in_progress or self.live_rendering:
            QMessageBox.warning(self, self.tr("warning"), self.tr("restart_blocked_busy"))
            return
        if not self.confirm_ui_scale_restart(mode):
            return
        if not self.confirm_switch_survey():
            return
        if not save_ui_scale(mode):
            QMessageBox.warning(self, self.tr("warning"), self.tr("settings_save_failed"))
            return

        log_event(
            f"workspace ui scale saved for restart {format_ui_scale_diagnostics(ui_scale_diagnostics(mode))}",
            logger_name="ui",
        )
        try:
            start_replacement_process()
        except OSError as exc:
            log_exception("workspace restart failed after ui scale change", exc, logger_name="ui")
            QMessageBox.warning(self, self.tr("warning"), self.tr("restart_failed"))
            return

        self.restart_requested = True
        QApplication.instance().quit()

    def confirm_ui_scale_restart(self, mode):
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Question)
        message_box.setWindowTitle(self.tr("ui_scale_restart_title"))
        message_box.setText(
            self.tr("ui_scale_restart_message", scale=self.ui_scale_label_for_mode(mode))
        )
        save_button = message_box.addButton(
            self.tr("save_and_restart"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        message_box.addButton(self.tr("cancel"), QMessageBox.ButtonRole.RejectRole)
        message_box.setDefaultButton(save_button)
        message_box.exec()
        return message_box.clickedButton() == save_button

    def ui_scale_label_for_mode(self, mode):
        return dict(self.ui_scale_items()).get(mode, f"{mode}%")

    def open_settings_menu(self):
        if self.should_suppress_settings_menu_toggle():
            return

        active_dialog = self.settings_menu_dialog
        if active_dialog is not None and active_dialog.isVisible():
            active_dialog.close()
            return

        dialog = QDialog(self)
        self.settings_menu_dialog = dialog
        dialog.setObjectName("settingsMenuPanel")
        dialog.setProperty(SKIP_CENTERING_PROPERTY, True)
        dialog.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(self.spx(12), self.spx(10), self.spx(12), self.spx(10))
        layout.setSpacing(self.spx(8))

        theme_combo = self.create_settings_combo(
            [(theme, self.tr(f"qt_theme_{theme}")) for theme in QT_THEME_OPTIONS],
            self.theme,
        )
        theme_combo.currentIndexChanged.connect(lambda _index: self.change_theme(theme_combo.currentData()))
        self.add_settings_row(layout, self.tr("theme"), theme_combo)

        scale_combo = self.create_settings_combo(self.ui_scale_items(), self.ui_scale_mode)
        scale_combo.currentIndexChanged.connect(lambda _index: self.change_ui_scale(scale_combo.currentData()))
        self.add_settings_row(layout, self.tr("ui_scale"), scale_combo)

        language_combo = self.create_settings_combo(
            [(code, code) for code in SUPPORTED_LANGUAGES],
            self.language.upper(),
        )
        language_combo.currentIndexChanged.connect(lambda _index: self.change_language(language_combo.currentData()))
        self.add_settings_row(layout, self.tr("language"), language_combo)

        menu_width = self.spx(230)
        dialog.setMinimumWidth(menu_width)
        dialog.adjustSize()
        position = self.settings_menu_button.mapToGlobal(
            QPoint(self.settings_menu_button.width() - menu_width, self.settings_menu_button.height())
        )
        dialog.move(position)
        try:
            dialog.exec()
        finally:
            if self.settings_menu_dialog is dialog:
                self.settings_menu_dialog = None
            if self.is_settings_button_global_pos(QCursor.pos()):
                self.settings_menu_suppressed_until = time.monotonic() + 0.35

    def should_suppress_settings_menu_toggle(self):
        if time.monotonic() < self.settings_menu_suppressed_until:
            self.settings_menu_suppressed_until = 0.0
            return True
        return False

    def is_settings_button_global_pos(self, global_pos):
        local_pos = self.settings_menu_button.mapFromGlobal(global_pos)
        return self.settings_menu_button.rect().contains(local_pos)

    def create_settings_combo(self, items, current_value):
        combo = QComboBox()
        combo.setMinimumWidth(self.spx(150))
        for value, label in items:
            combo.addItem(label, value)
        index = combo.findData(current_value)
        combo.setCurrentIndex(max(0, index))
        return combo

    def add_settings_row(self, layout, label_text, widget):
        label = QLabel(label_text)
        label.setObjectName("settingsMenuLabel")
        layout.addWidget(label)
        layout.addWidget(widget)

    def ui_scale_items(self):
        auto_percent = detect_auto_ui_scale_percent()
        return [
            (mode, self.tr("ui_scale_auto", percent=auto_percent) if mode == "auto" else f"{mode}%")
            for mode in UI_SCALE_OPTIONS
        ]

    def refresh_live_static_options(self):
        self.set_combo_items(
            self.live_map_type_combo,
            [
                ("signal", self.tr("map_type_signal")),
                ("interference", self.tr("map_type_interference")),
                ("channel", self.tr("map_type_channel")),
                ("dominant", self.tr("map_type_dominant")),
            ],
        )
        self.refresh_live_band_options(self.current_combo_value(self.live_map_type_combo, "signal"))
        self.set_combo_items(
            self.live_aggregation_combo,
            [
                ("max", self.tr("aggregation_max")),
                ("median", self.tr("aggregation_median")),
                ("mean", self.tr("aggregation_mean")),
            ],
        )
        self.set_combo_items(
            self.live_color_scale_combo,
            [
                ("fixed", self.tr("color_scale_fixed")),
                ("auto", self.tr("color_scale_auto")),
            ],
        )
        self.set_combo_items(
            self.live_interpolation_combo,
            [
                ("rbf", self.tr("interpolation_rbf")),
                ("linear", self.tr("interpolation_linear")),
            ],
        )
        self.set_combo_items(
            self.live_interference_mode_combo,
            [
                ("intra_ssid", self.tr("interference_mode_intra_ssid")),
                ("all", self.tr("interference_mode_all")),
            ],
        )
        self.set_combo_items(
            self.live_point_labels_combo,
            [
                ("auto", self.tr("point_labels_auto")),
                ("all", self.tr("point_labels_all")),
                ("none", self.tr("point_labels_none")),
            ],
        )

    def live_band_items_for_map_type(self, map_type):
        items = [
            ("all", self.tr("all_bands_option")),
            ("2.4", "2.4 GHz"),
            ("5", "5 GHz"),
        ]
        if map_type == "interference":
            return items[1:]
        return items

    def refresh_live_band_options(self, map_type=None, preferred_band=None):
        map_type = map_type or self.current_combo_value(self.live_map_type_combo, "signal")
        current_band = (
            preferred_band
            if preferred_band is not None
            else self.current_combo_value(self.live_band_combo, "all")
        )
        items = self.live_band_items_for_map_type(map_type)
        available = {str(value) for value, _label in items}
        if current_band not in available:
            current_band = "2.4" if "2.4" in available else (str(items[0][0]) if items else "")
        self.set_combo_items(self.live_band_combo, items, current_value=current_band)

    def update_live_max_distance_label(self):
        if not hasattr(self, "live_max_distance_label"):
            return

        if self.get_px_per_meter():
            self.live_max_distance_label.setText(self.tr("max_distance_m"))
        else:
            self.live_max_distance_label.setText(self.tr("max_distance_px"))

    def current_live_max_distance_px(self):
        px_per_meter = self.get_px_per_meter() or self.live_distance_last_px_per_meter
        if getattr(self, "live_distance_spin_uses_meters", False) and px_per_meter:
            return max(1, int(round(self.live_max_distance_spin.value() * px_per_meter)))

        return max(1, int(round(self.live_max_distance_spin.value())))

    def set_live_max_distance_px_silent(self, max_distance_px):
        px_per_meter = self.get_px_per_meter()
        self.live_max_distance_spin.blockSignals(True)
        try:
            if px_per_meter:
                self.live_distance_spin_uses_meters = True
                self.live_distance_last_px_per_meter = px_per_meter
                self.live_max_distance_spin.setRange(1.0, 50.0)
                self.live_max_distance_spin.setSingleStep(0.5)
                self.live_max_distance_spin.setDecimals(1)
                self.live_max_distance_spin.setSuffix(" m")
                self.live_max_distance_spin.setValue(max(1.0, float(max_distance_px) / px_per_meter))
            else:
                self.live_distance_spin_uses_meters = False
                self.live_max_distance_spin.setRange(40.0, 1000.0)
                self.live_max_distance_spin.setSingleStep(20.0)
                self.live_max_distance_spin.setDecimals(0)
                self.live_max_distance_spin.setSuffix(" px")
                self.live_max_distance_spin.setValue(float(max_distance_px or HEATMAP_MAX_DISTANCE_PX))
        finally:
            self.live_max_distance_spin.blockSignals(False)
        self.update_live_max_distance_label()

    def set_combo_value_silent(self, combo, value):
        index = combo.findData(value)
        if index < 0 and combo.count():
            index = 0
        if index < 0:
            return

        combo.blockSignals(True)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def default_live_option_state(self, map_type):
        return {
            "band": "2.4" if map_type == "interference" else "all",
            "aggregation": "max",
            "color_scale": "fixed",
            "interpolation": "rbf",
            "interference_mode": "intra_ssid",
            "point_label_mode": "auto",
            "ap_group_filter": "",
            "usable_only": False,
            "smoothing_sigma": HEATMAP_SMOOTHING_SIGMA,
            "max_distance_px": HEATMAP_MAX_DISTANCE_PX,
        }

    def current_live_option_state(self):
        return {
            "band": self.current_combo_value(self.live_band_combo, "all"),
            "aggregation": self.current_combo_value(self.live_aggregation_combo, "max"),
            "color_scale": self.current_combo_value(self.live_color_scale_combo, "fixed"),
            "interpolation": self.current_combo_value(self.live_interpolation_combo, "rbf"),
            "interference_mode": self.current_combo_value(
                self.live_interference_mode_combo,
                "intra_ssid",
            ),
            "point_label_mode": self.current_combo_value(self.live_point_labels_combo, "auto"),
            "ap_group_filter": self.current_combo_value(self.live_ap_group_combo, ""),
            "usable_only": self.live_usable_check.isChecked(),
            "smoothing_sigma": float(self.live_smoothing_spin.value()),
            "max_distance_px": self.current_live_max_distance_px(),
        }

    def remember_live_option_state(self, map_type=None):
        if self.live_option_state_syncing:
            return

        map_type = map_type or self.current_combo_value(self.live_map_type_combo, "signal")
        self.live_map_option_memory[map_type] = self.current_live_option_state()

    def restore_live_option_state(self, map_type):
        state = dict(self.default_live_option_state(map_type))
        state.update(self.live_map_option_memory.get(map_type, {}))

        self.live_option_state_syncing = True
        try:
            self.refresh_live_band_options(map_type, preferred_band=state.get("band"))
            self.set_combo_value_silent(self.live_aggregation_combo, state.get("aggregation", "max"))
            self.set_combo_value_silent(self.live_color_scale_combo, state.get("color_scale", "fixed"))
            self.set_combo_value_silent(self.live_interpolation_combo, state.get("interpolation", "rbf"))
            self.set_combo_value_silent(
                self.live_interference_mode_combo,
                state.get("interference_mode", "intra_ssid"),
            )
            self.set_combo_value_silent(self.live_point_labels_combo, state.get("point_label_mode", "auto"))
            self.live_smoothing_spin.blockSignals(True)
            self.live_smoothing_spin.setValue(float(state.get("smoothing_sigma", HEATMAP_SMOOTHING_SIGMA)))
            self.live_smoothing_spin.blockSignals(False)
            self.set_live_max_distance_px_silent(state.get("max_distance_px", HEATMAP_MAX_DISTANCE_PX))
            self.live_usable_check.blockSignals(True)
            self.live_usable_check.setChecked(bool(state.get("usable_only", False)))
            self.live_usable_check.blockSignals(False)
            self.refresh_live_ap_group_filter()
            self.set_combo_value_silent(self.live_ap_group_combo, state.get("ap_group_filter", ""))
        finally:
            self.live_option_state_syncing = False

    def reset_live_option_memory(self):
        self.live_map_option_memory = {}
        self.live_current_map_type = self.current_combo_value(self.live_map_type_combo, "signal")
        self.restore_live_option_state(self.live_current_map_type)

    def set_combo_items(self, combo, items, current_value=None):
        current = combo.currentData() if current_value is None else current_value
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

    def refresh_live_ap_group_filter(self):
        current_group = self.current_combo_value(self.live_ap_group_combo, "")
        items = [("", self.tr("all_ap_groups_option"))]
        items.extend(self.live_ap_group_filter_items())
        self.set_combo_items(self.live_ap_group_combo, items, current_value=current_group)

    def live_ap_group_filter_items(self):
        if self.session is None:
            return []

        ssid = self.live_ssid_combo.currentText().strip()
        band = self.current_combo_value(self.live_band_combo, "all")
        groups = self.session.get_ap_groups()
        group_map = build_bssid_to_manual_group_map(groups)
        role_map = build_ap_group_role_map(groups)
        aliases = self.session.get_ap_aliases()
        seen_groups = {}

        for row in self.session.rows:
            row_ssid = str(row.get("ssid", "")).strip()
            if ssid and row_ssid.casefold() != ssid.casefold():
                continue
            if not self.row_matches_live_band(row, band):
                continue

            bssid = str(row.get("bssid", "")).strip()
            if not bssid:
                continue
            group_id = resolve_ap_group_key(bssid, group_map)
            if normalize_ap_role(role_map.get(str(group_id))) == AP_ROLE_TEST:
                continue

            group_entry = seen_groups.setdefault(str(group_id), {"bssids": []})
            if bssid not in group_entry["bssids"]:
                group_entry["bssids"].append(bssid)

        return [
            (group_id, self.format_live_ap_group_filter_label(group_id, entry["bssids"], aliases))
            for group_id, entry in sorted(
                seen_groups.items(),
                key=lambda item: self.format_live_ap_group_filter_label(
                    item[0],
                    item[1]["bssids"],
                    aliases,
                ).casefold(),
            )
        ]

    def row_matches_live_band(self, row, band):
        if band == "all":
            return True

        try:
            channel = float(row.get("channel", ""))
        except (TypeError, ValueError):
            return False

        if band == "2.4":
            return 1 <= channel <= 14
        if band == "5":
            return channel >= 36
        return True

    def format_live_ap_group_filter_label(self, group_id, bssids, aliases):
        display_name = self.get_ap_group_display_name(group_id)
        if display_name and display_name != str(group_id):
            return display_name

        if bssids:
            label = format_ap_label(bssids[0], aliases, group_id)
            extra_count = len(bssids) - 1
            return f"{label} +{extra_count}" if extra_count > 0 else label

        return str(group_id or "-")

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
        self.refresh_live_ap_group_filter()

        can_render = self.can_use_live_controls(ssids)
        for widget in (
            self.live_ssid_combo,
            self.live_band_combo,
            self.live_map_type_combo,
            self.live_aggregation_combo,
            self.live_color_scale_combo,
            self.live_interpolation_combo,
            self.live_interference_mode_combo,
            self.live_smoothing_spin,
            self.live_max_distance_spin,
            self.live_point_labels_combo,
            self.live_ap_group_combo,
            self.live_usable_check,
            self.live_auto_check,
            self.live_options_toggle_button,
        ):
            widget.setEnabled(can_render)
        self.live_update_button.setEnabled(can_render and not self.live_rendering)
        self.live_pdf_export_button.setEnabled(can_render and not self.live_rendering)
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
        previous_map_type = self.live_current_map_type
        map_type_changed = map_type != previous_map_type
        if map_type_changed:
            self.remember_live_option_state(previous_map_type)
            self.live_current_map_type = map_type
            self.restore_live_option_state(map_type)
        else:
            self.refresh_live_band_options(map_type)
            self.refresh_live_ap_group_filter()

        is_signal = map_type == "signal"
        is_interference = map_type == "interference"
        is_channel = map_type == "channel"
        is_dominant = map_type == "dominant"
        is_continuous = is_signal or is_interference
        self.set_live_max_distance_px_silent(self.current_live_max_distance_px())
        self.reflow_live_option_controls(map_type)
        can_use_controls = self.can_use_live_controls()
        self.set_labeled_live_control_state(
            self.live_band_label,
            self.live_band_combo,
            visible=is_signal or is_interference or is_channel or is_dominant,
            enabled=can_use_controls,
        )
        self.set_labeled_live_control_state(
            self.live_aggregation_label,
            self.live_aggregation_combo,
            visible=is_signal,
            enabled=can_use_controls and is_signal,
        )
        self.set_labeled_live_control_state(
            self.live_interference_mode_label,
            self.live_interference_mode_combo,
            visible=is_interference,
            enabled=can_use_controls and is_interference,
        )
        self.set_labeled_live_control_state(
            self.live_interpolation_label,
            self.live_interpolation_combo,
            visible=is_continuous,
            enabled=can_use_controls and is_continuous,
        )
        self.set_labeled_live_control_state(
            self.live_color_scale_label,
            self.live_color_scale_combo,
            visible=is_continuous,
            enabled=can_use_controls and is_continuous,
        )
        self.set_labeled_live_control_state(
            self.live_smoothing_label,
            self.live_smoothing_spin,
            visible=is_continuous,
            enabled=can_use_controls and is_continuous,
        )
        self.set_labeled_live_control_state(
            self.live_max_distance_label,
            self.live_max_distance_spin,
            visible=is_continuous,
            enabled=can_use_controls and is_continuous,
        )
        self.set_labeled_live_control_state(
            self.live_point_labels_label,
            self.live_point_labels_combo,
            visible=is_channel or is_dominant,
            enabled=can_use_controls and (is_channel or is_dominant),
        )
        self.live_usable_check.setVisible(is_signal)
        self.live_usable_check.setEnabled(can_use_controls and is_signal)
        can_filter_ap_group = (
            can_use_controls
            and (is_signal or is_channel)
            and self.live_ap_group_combo.count() > 1
        )
        self.set_labeled_live_control_state(
            self.live_ap_group_label,
            self.live_ap_group_combo,
            visible=(is_signal or is_channel) and self.live_ap_group_combo.count() > 1,
            enabled=can_filter_ap_group,
        )
        self.remember_live_option_state(map_type)

    def set_labeled_live_control_state(self, label, widget, visible, enabled):
        label.setVisible(visible)
        widget.setVisible(visible)
        label.setEnabled(enabled)
        widget.setEnabled(enabled)

    def update_live_option_dropdown_widths(self, combos):
        text_width = 0
        for combo in combos:
            metrics = combo.fontMetrics()
            text_width = max(text_width, metrics.horizontalAdvance(combo.currentText()))
            for index in range(combo.count()):
                text_width = max(text_width, metrics.horizontalAdvance(combo.itemText(index)))

        width = max(self.spx(132), min(self.spx(280), text_width + self.spx(86)))
        for combo in combos:
            combo.setFixedWidth(width)
        return width

    def reflow_live_option_controls(self, map_type):
        for widget in self.live_option_widgets:
            self.live_options_layout.removeWidget(widget)
        self.live_options_layout.removeWidget(self.live_options_separator)
        self.live_options_separator.hide()

        row = 0
        dropdowns = []
        value_widgets = []

        def add_labeled(label, widget):
            nonlocal row
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.live_options_layout.addWidget(label, row, 0)
            self.live_options_layout.addWidget(widget, row, 1)
            if isinstance(widget, QComboBox):
                dropdowns.append(widget)
            elif isinstance(widget, QDoubleSpinBox):
                value_widgets.append(widget)
            row += 1

        def add_checkbox(widget):
            nonlocal row
            self.live_options_layout.addWidget(widget, row, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)
            row += 1

        def add_separator():
            nonlocal row
            self.live_options_layout.addWidget(self.live_options_separator, row, 0, 1, 2)
            self.live_options_separator.show()
            row += 1

        dropdown_controls = [(self.live_band_label, self.live_band_combo)]

        if map_type == "signal":
            dropdown_controls.extend(
                [
                    (self.live_aggregation_label, self.live_aggregation_combo),
                    (self.live_color_scale_label, self.live_color_scale_combo),
                    (self.live_interpolation_label, self.live_interpolation_combo),
                    (self.live_max_distance_label, self.live_max_distance_spin),
                    (self.live_smoothing_label, self.live_smoothing_spin),
                ]
            )
            if self.live_ap_group_combo.count() > 1:
                dropdown_controls.append((self.live_ap_group_label, self.live_ap_group_combo))
        elif map_type == "interference":
            dropdown_controls.extend(
                [
                    (self.live_color_scale_label, self.live_color_scale_combo),
                    (self.live_interference_mode_label, self.live_interference_mode_combo),
                    (self.live_interpolation_label, self.live_interpolation_combo),
                    (self.live_max_distance_label, self.live_max_distance_spin),
                    (self.live_smoothing_label, self.live_smoothing_spin),
                ]
            )
        elif map_type == "channel":
            dropdown_controls.append((self.live_point_labels_label, self.live_point_labels_combo))
            if self.live_ap_group_combo.count() > 1:
                dropdown_controls.append((self.live_ap_group_label, self.live_ap_group_combo))
        elif map_type == "dominant":
            dropdown_controls.append((self.live_point_labels_label, self.live_point_labels_combo))

        for label, widget in sorted(dropdown_controls, key=lambda pair: pair[0].text().casefold()):
            add_labeled(label, widget)

        if map_type == "signal":
            add_separator()
            add_checkbox(self.live_usable_check)

        control_width = self.update_live_option_dropdown_widths(dropdowns)
        for widget in value_widgets:
            widget.setFixedWidth(control_width)

        if hasattr(self, "live_options_overlay"):
            QTimer.singleShot(0, self.position_live_options_overlay)

    def on_workspace_tab_changed(self, index):
        self.refresh_session_labels()
        if index == 1:
            self.maybe_update_live_preview()

    def on_live_option_changed(self):
        self.refresh_session_labels()
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
        self.refresh_session_labels()

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
        map_type = self.current_combo_value(self.live_map_type_combo, "signal")
        ap_group_filter = (
            self.current_combo_value(self.live_ap_group_combo, "")
            if map_type in {"signal", "channel"}
            else ""
        )
        return MapConfig(
            ssid=self.live_ssid_combo.currentText().strip(),
            band=self.current_combo_value(self.live_band_combo, "all"),
            map_type=map_type,
            interference_mode=self.current_combo_value(self.live_interference_mode_combo, "intra_ssid"),
            interpolation=self.current_combo_value(self.live_interpolation_combo, "rbf"),
            aggregation=self.current_combo_value(self.live_aggregation_combo, "max"),
            color_scale=self.current_combo_value(self.live_color_scale_combo, "fixed"),
            point_label_mode=self.current_combo_value(self.live_point_labels_combo, "auto"),
            usable_only=self.live_usable_check.isChecked(),
            smoothing_sigma=float(self.live_smoothing_spin.value()),
            max_distance_px=self.current_live_max_distance_px(),
            ap_group_filter=ap_group_filter,
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
        map_type = self.current_combo_value(self.live_map_type_combo, "signal")
        ap_group_filter = (
            self.current_combo_value(self.live_ap_group_combo, "")
            if map_type in {"signal", "channel"}
            else ""
        )
        return MapConfig(
            ssid=current_ssid,
            band=self.current_combo_value(self.live_band_combo, "all"),
            map_type=map_type,
            interference_mode=self.current_combo_value(self.live_interference_mode_combo, "intra_ssid"),
            interpolation=self.current_combo_value(self.live_interpolation_combo, "rbf"),
            aggregation=self.current_combo_value(self.live_aggregation_combo, "max"),
            color_scale=self.current_combo_value(self.live_color_scale_combo, "fixed"),
            point_label_mode=self.current_combo_value(self.live_point_labels_combo, "auto"),
            usable_only=self.live_usable_check.isChecked(),
            smoothing_sigma=float(self.live_smoothing_spin.value()),
            max_distance_px=self.current_live_max_distance_px(),
            ap_group_filter=ap_group_filter,
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
            "ap_position_marker_title": self.tr("ap_group_position_tooltip_title"),
            "ap_group": self.tr("ap_alias_group"),
            "ap_label": self.tr("ap_label"),
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
        self.refresh_session_labels()

        if self.live_dirty and self.live_auto_check.isChecked():
            QTimer.singleShot(0, self.update_live_preview)

    def fail_live_preview(self, message):
        self.live_rendering = False
        log_event(f"qt live render failed message={message}", logger_name="main")
        self.live_status_label.setText(f"{self.tr('error')}: {message}")
        self.clear_live_legend()
        self.refresh_session_labels()

    def cleanup_live_render_thread(self):
        finished_thread = self.sender()
        if finished_thread is self.live_thread:
            self.live_thread = None
            self.live_worker = None
        log_event("qt live render thread cleaned up", logger_name="main")

    def format_live_status(self, payload):
        return self.tr("live_preview_updated")

    def update_live_legend(self, scale_payload):
        self.live_legend_list.clear()
        self.live_view.clear_gradient_legend()
        if not scale_payload:
            self.clear_live_legend()
            return

        self.live_legend_title.setText(str(scale_payload.get("title") or ""))
        kind = scale_payload.get("kind")
        if kind == "swatches":
            self.live_legend_frame.show()
            self.live_legend_list.show()
            for item in scale_payload.get("items", []):
                list_item = QListWidgetItem(str(item.get("label", "")))
                list_item.setIcon(create_marker_icon(
                    item.get("color", "#7f8c8d"),
                    shape=item.get("shape", "circle"),
                    outline_only=bool(item.get("outline_only")),
                ))
                list_item.setData(Qt.ItemDataRole.UserRole, dict(item))
                self.live_legend_list.addItem(list_item)
            return

        if kind == "gradient":
            self.live_legend_frame.hide()
            self.live_view.set_gradient_legend(scale_payload)

    def clear_live_legend(self):
        self.live_legend_title.setText("")
        self.live_legend_list.clear()
        self.clear_live_marker_selection()
        self.live_view.clear_gradient_legend()
        self.live_legend_frame.hide()
        self.live_legend_list.show()

    def clear_live_marker_selection(self):
        self.live_legend_list.clearSelection()
        self.live_legend_list.setCurrentRow(-1)
        self.live_view.clear_marker_highlight()

    def on_live_legend_item_clicked(self, item):
        payload = item.data(Qt.ItemDataRole.UserRole) if item else None
        marker_id = payload.get("marker_id") if isinstance(payload, dict) else ""
        if not marker_id or not self.live_view.highlight_marker(marker_id):
            self.clear_live_marker_selection()

    def on_live_legend_item_double_clicked(self, item):
        payload = item.data(Qt.ItemDataRole.UserRole) if item else None
        marker_id = payload.get("marker_id") if isinstance(payload, dict) else ""
        if marker_id and self.live_view.focus_marker(marker_id):
            return
        self.clear_live_marker_selection()

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
        self.reset_live_option_memory()
        self.floorplan_view.clear_floorplan()
        self.live_view.clear()
        self.show_workspace_page()
        return True

    def open_survey(self, csv_file=None):
        if not self.confirm_switch_survey():
            return False

        if csv_file is None:
            csv_file, _selected_filter = get_centered_open_file_name(
                self,
                self.tr("open_existing_survey"),
                get_last_survey_directory(),
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
        self.reset_live_option_memory()
        save_last_survey_path(csv_file)
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
            csv_file, _selected_filter = get_centered_save_file_name(
                self,
                self.tr("save"),
                get_last_survey_directory(),
                self.tr("qt_survey_file_filter"),
            )
            if not csv_file:
                return False
            if Path(csv_file).suffix.lower() != ".csv":
                csv_file = f"{csv_file}.csv"

        self.session.save(csv_file)
        save_last_survey_path(csv_file)
        self.refresh_session_labels()
        self.status.showMessage(self.tr("survey_saved", name=self.session.display_name))
        return True

    def load_plan(self):
        if self.session is None:
            self.new_survey()
            if self.session is None:
                return

        file_path, _selected_filter = get_centered_open_file_name(
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
        QTimer.singleShot(0, self.floorplan_view.fit_to_view)
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
        view = self.current_zoom_view()
        if view is None:
            return

        view.zoom_in()
        self.status.showMessage(self.tr("zoom", zoom=view.zoom_level))

    def zoom_out(self):
        view = self.current_zoom_view()
        if view is None:
            return

        view.zoom_out()
        self.status.showMessage(self.tr("zoom", zoom=view.zoom_level))

    def fit_floorplan(self):
        view = self.current_zoom_view()
        if view is None:
            return

        view.fit_to_view()
        self.status.showMessage(self.tr("zoom", zoom=view.zoom_level))

    def current_zoom_view(self):
        if self.tabs.currentIndex() == 1:
            return self.live_view if self.live_view.pixmap_item is not None else None

        return self.floorplan_view if self.floorplan_view.has_floorplan() else None

    def start_scale_calibration(self):
        if self.session is None:
            return

        if not self.floorplan_view.has_floorplan():
            QMessageBox.warning(self, self.tr("warning"), self.tr("load_plan_first"))
            return

        if self.has_calibrated_scale():
            self.status.showMessage(self.tr("calibrate_scale_already_set"))
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

    def delete_scale_calibration(self):
        if self.session is None or not self.has_calibrated_scale():
            return

        response = QMessageBox.question(
            self,
            self.tr("delete_scale_title"),
            self.tr("delete_scale_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if response != QMessageBox.StandardButton.Yes:
            return

        self.session.metadata.pop("px_per_meter", None)
        self.session.dirty = True
        self.floorplan_view.clear_scale_calibration_overlay()
        self.refresh_session_labels()
        self.status.showMessage(self.tr("delete_scale_done"))
        self.maybe_update_live_preview()

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
        if self.restart_requested:
            event.accept()
            return

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

    def export_live_pdf(self):
        if self.session is None:
            return False

        if not self.can_render_live_preview():
            QMessageBox.warning(self, self.tr("warning"), self.tr("live_preview_empty"))
            return False

        if not self.ensure_saved_for_map_export():
            return False

        map_file = self.session.metadata.get("map_file", "")
        config = self.build_live_map_config()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        result = None
        map_error = None
        unexpected_error = None
        try:
            bg_image = load_floorplan_image(map_file)
            result = generate_live_pdf_export(
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
            log_exception("qt live PDF export failed", unexpected_error, logger_name="main")
            QMessageBox.critical(self, self.tr("error"), str(unexpected_error))
            return False

        QMessageBox.information(
            self,
            self.tr("live_pdf_exported"),
            self.format_map_export_result_message(result),
        )
        self.status.showMessage(self.tr("live_pdf_exported"))
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
        self.update_relevant_row_flags()
        self.refresh_session_labels()

    def update_relevant_row_flags(self):
        if self.session is None:
            return

        relevant = {ssid.casefold() for ssid in self.relevant_ssids}
        changed = False
        for row in self.session.rows:
            is_relevant = "1" if str(row.get("ssid", "")).strip().casefold() in relevant else "0"
            if row.get("is_relevant") != is_relevant:
                row["is_relevant"] = is_relevant
                changed = True

        if changed:
            self.session.dirty = True

    def available_relevant_ssids(self):
        if self.session is None:
            return set()

        return {
            str(ssid).strip()
            for ssid in (self.known_ssids | self.relevant_ssids | set(self.session.get_ssids()))
            if str(ssid).strip()
        }

    def manage_relevant_ssids(self):
        if self.session is None:
            return

        available_ssids = self.available_relevant_ssids()
        if not available_ssids:
            QMessageBox.warning(self, self.tr("warning"), self.tr("no_relevant_networks_to_manage"))
            return

        dialog = RelevantNetworksDialog(
            self,
            available_ssids,
            self.tr("manage_relevant_networks_title"),
            self.tr("manage_relevant_networks_message"),
            connected_ssid=get_connected_ssid(),
            selected_ssids=self.relevant_ssids,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.known_ssids |= available_ssids
        self.set_relevant_ssids(dialog.selected_ssids())
        self.save_known_ssids()
        self.refresh_points_table()
        self.status.showMessage(self.tr("relevant_networks_updated"))
        self.maybe_update_live_preview()

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
        self.update_relevant_row_flags()
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

        self.pending_rescan_point = None
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

            if not networks:
                self.pending_scan_point = None
                self.pending_rescan_point = None
                QMessageBox.critical(self, self.tr("error"), self.tr("no_networks_found"))
                return

            action = self.validate_relevant_networks(networks)
            log_event(f"qt point relevant validation action={action}", logger_name="main")
            if action == "retry":
                self.start_wifi_scan(x, y)
                return
            if action == "cancel":
                self.pending_scan_point = None
                self.pending_rescan_point = None
                self.status.showMessage(self.tr("cancelled"))
                return

            rescan_point = self.pending_rescan_point
            self.pending_scan_point = None
            self.pending_rescan_point = None
            removed_rows = 0
            if rescan_point:
                removed_rows = self.delete_point(rescan_point, refresh=False)
            self.save_survey_point(
                x,
                y,
                networks,
                status_message=self.tr(
                    "point_rescanned" if rescan_point else "point_saved",
                    x=x,
                    y=y,
                    count=len(networks),
                    rows=removed_rows,
                ),
            )
        except Exception as exc:
            log_exception("finish_wifi_scan failed", exc, logger_name="main")
            self.pending_scan_point = None
            self.pending_rescan_point = None
            self.set_scan_busy(False)
            QMessageBox.critical(self, self.tr("error"), str(exc))

    def fail_wifi_scan(self, message):
        log_event(f"qt point scan failed message={message}", logger_name="main")
        self.set_scan_busy(False)
        self.pending_scan_point = None
        self.pending_rescan_point = None
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

    def save_survey_point(self, x, y, networks, status_message=None):
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
        self.status.showMessage(status_message or self.tr("point_saved", x=x, y=y, count=len(networks)))
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
        return build_html_tooltip(
            self.tr("ap_group_position_tooltip_title"),
            [
                (self.tr("ap_alias_group"), group.get("group_id", "-")),
                (self.tr("ap_alias_value"), label),
                ("x/y", f"{x}, {y}"),
                (self.tr("ap_alias_bssids"), ", ".join(group.get("bssids", [])) or "-"),
            ],
            "#0d6efd",
        )

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
        self.floorplan_view.clear_selected_point()
        self.update_point_action_state()

    def on_points_table_selection_changed(self):
        point = self.current_selected_point()
        if point:
            self.floorplan_view.select_point(point)
        else:
            self.floorplan_view.clear_selected_point()
        self.update_point_action_state()

    def update_point_action_state(self):
        has_point = bool(self.current_selected_point())
        has_any_point = bool(self.session and self.session.get_point_summaries())
        self.focus_point_button.setEnabled(has_point)
        self.rescan_point_button.setEnabled(has_point and not self.scan_in_progress)
        self.delete_selected_button.setEnabled(has_point)
        self.delete_last_button.setEnabled(has_any_point)

    def focus_selected_point(self):
        point = self.current_selected_point()
        if not point:
            QMessageBox.warning(self, self.tr("warning"), self.tr("select_point"))
            return

        self.floorplan_view.focus_on(point["x"], point["y"])

    def rescan_selected_point(self):
        if self.session is None:
            return

        point = self.current_selected_point()
        if not point:
            QMessageBox.warning(self, self.tr("warning"), self.tr("select_point"))
            return
        if self.scan_in_progress:
            return

        self.pending_rescan_point = dict(point)
        self.start_wifi_scan(point["x"], point["y"])

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
        self.manage_relevant_button.setEnabled(can_use_session and bool(self.available_relevant_ssids()))
        self.clear_relevant_button.setEnabled(
            can_use_session and bool(self.relevant_ssids or self.known_ssids)
        )
        live_tab_active = self.tabs.currentIndex() == 1
        has_map = self.floorplan_view.has_floorplan()
        has_zoom_map = self.live_view.pixmap_item is not None if live_tab_active else has_map
        has_scale = self.has_calibrated_scale()
        self.zoom_in_button.setEnabled(has_zoom_map and not self.scan_in_progress)
        self.zoom_out_button.setEnabled(has_zoom_map and not self.scan_in_progress)
        self.fit_view_button.setEnabled(has_zoom_map and not self.scan_in_progress)
        self.calibrate_button.setEnabled(
            has_map and not live_tab_active and not self.scan_in_progress and not has_scale
        )
        self.delete_scale_button.setEnabled(can_use_session and not live_tab_active and has_scale)
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
                if column_index == 5:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    item.setToolTip(value)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, point)
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
    install_dialog_centering(app)
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
