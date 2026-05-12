"""Main Qt workspace window for surveying, live maps, and analysis tools."""

import sys
from pathlib import Path

try:
    from PySide6.QtCore import QEvent, QRect, QSize, Qt, QTimer
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QComboBox,
        QDoubleSpinBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QListWidget,
        QMainWindow,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QStackedWidget,
        QStatusBar,
        QStyle,
        QStyleOptionButton,
        QStylePainter,
        QTableWidget,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from translations.i18n import DEFAULT_LANGUAGE, LANGUAGE_OPTIONS, translate
from app_core.logging import configure_logging, log_event, log_exception, log_unhandled_exception
from app_core.settings import (
    get_saved_theme,
    get_saved_ui_scale,
)
from app_core.constants import HEATMAP_MAX_DISTANCE_PX, HEATMAP_SMOOTHING_SIGMA
from qt_ui.qt_ap_workflow import ApWorkflowMixin
from qt_ui.qt_floorplan import FloorplanView
from qt_ui.qt_floorplan_workflow import FloorplanWorkflowMixin
from qt_ui.qt_help_dialog import open_qt_help_dialog
from qt_ui.qt_live_export import LivePdfExportMixin
from qt_ui.qt_live_options import LiveOptionsMixin
from qt_ui.qt_live_preview import LivePreviewMixin
from qt_ui.qt_live_map import LiveMapView
from qt_ui.qt_point_workflow import PointCaptureMixin
from qt_ui.qt_quality_dashboard import open_qt_quality_dashboard
from qt_ui.qt_relevant_networks import (
    KNOWN_SSIDS_METADATA_KEY,
    RELEVANT_SSIDS_METADATA_KEY,
    RelevantNetworksMixin,
)
from qt_ui.qt_survey_points import SurveyPointTableMixin
from qt_ui.qt_session_workflow import SurveySessionWorkflowMixin
from qt_ui.qt_theme import QT_THEMES, build_scrollbar_stylesheet
from qt_ui.qt_windowing import (
    install_dialog_centering,
)
from qt_ui.qt_workspace_settings import WorkspaceSettingsMixin
from qt_ui.scaling import (
    format_ui_scale_diagnostics,
    normalize_ui_scale_mode,
    resolve_ui_scale,
    scale_font,
    scale_px,
    ui_scale_diagnostics,
)


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


class WifiHeatmapQtApp(
    PointCaptureMixin,
    SurveyPointTableMixin,
    RelevantNetworksMixin,
    ApWorkflowMixin,
    LivePreviewMixin,
    LiveOptionsMixin,
    LivePdfExportMixin,
    FloorplanWorkflowMixin,
    SurveySessionWorkflowMixin,
    WorkspaceSettingsMixin,
    QMainWindow,
):
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
        for code, label in LANGUAGE_OPTIONS:
            self.start_language_combo.addItem(label, code)
        start_language_index = self.start_language_combo.findData(self.language.upper())
        self.start_language_combo.setCurrentIndex(max(0, start_language_index))
        self.start_language_combo.currentIndexChanged.connect(
            lambda _index: self.change_language(self.start_language_combo.currentData())
        )
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
        self.delete_scale_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        view_section.title_row.addWidget(self.delete_scale_button)
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
        for button in (
            self.ap_groups_button,
            self.quality_button,
            self.help_button,
        ):
            analysis_row.addWidget(button)
        layout.addWidget(analysis_section, 1)

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

    def fit_text_button_width(self, button, min_width=0):
        button.setMinimumWidth(max(self.spx(min_width), button.sizeHint().width()))

    def fit_localized_button_widths(self):
        for button, min_width in (
            (self.delete_scale_button, 0),
            (self.manage_relevant_button, 0),
            (self.clear_relevant_button, 0),
            (self.live_pdf_export_button, 118),
            (self.live_update_button, 132),
        ):
            self.fit_text_button_width(button, min_width)

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
        for button in (self.manage_relevant_button, self.clear_relevant_button):
            button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
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
        self.points_table.setObjectName("measurementPointsTable")
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
        toolbar_layout.addWidget(self.live_pdf_export_button)
        toolbar_layout.addWidget(self.live_export_separator)
        toolbar_layout.addWidget(self.live_update_button)
        toolbar_layout.addWidget(self.live_auto_check)
        layout.addWidget(toolbar)

        self.live_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.live_splitter.setChildrenCollapsible(False)
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
        self.live_splitter.addWidget(self.live_view_container)

        self.live_legend_frame = QFrame()
        self.live_legend_frame.setObjectName("summaryPanel")
        self.live_legend_frame.setMinimumWidth(self.spx(240))
        self.live_legend_frame.setMaximumWidth(16777215)
        self.live_legend_user_resized = False
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
        self.live_splitter.addWidget(self.live_legend_frame)
        self.live_legend_frame.hide()
        self.live_splitter.setStretchFactor(0, 1)
        self.live_splitter.setStretchFactor(1, 0)
        self.live_splitter.setCollapsible(0, False)
        self.live_splitter.setCollapsible(1, False)
        self.live_splitter.splitterMoved.connect(self.on_live_splitter_moved)
        layout.addWidget(self.live_splitter, 1)

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
        self.live_checkbox_separator = QFrame()
        self.live_checkbox_separator.setObjectName("liveOptionsSeparator")
        self.live_checkbox_separator.setFrameShape(QFrame.Shape.NoFrame)
        self.live_checkbox_separator.setFixedHeight(self.spx(1))
        self.live_checkbox_separator.hide()
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
        combo_arrow_icon = (
            Path(__file__).resolve().parent.parent / "images" / "combo_arrow_white.svg"
        ).as_posix()
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
            QTableWidget#measurementPointsTable {{
                selection-background-color: {palette["metric_info"]};
                selection-color: #FFFFFF;
            }}
            QTableWidget#measurementPointsTable::item:selected {{
                background: {palette["metric_info"]};
                color: #FFFFFF;
                border-bottom: 1px solid {palette["metric_info"]};
            }}
            QTableWidget::item:focus {{
                border: 0;
                border-bottom: 1px solid {palette["border"]};
            }}
            {build_scrollbar_stylesheet(palette, s)}
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
        self.fit_localized_button_widths()
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

    def open_quality_dashboard(self):
        if self.session is None:
            return

        open_qt_quality_dashboard(self)

    def open_help_dialog(self):
        open_qt_help_dialog(self, self.tr)

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



if __name__ == "__main__":
    main()
