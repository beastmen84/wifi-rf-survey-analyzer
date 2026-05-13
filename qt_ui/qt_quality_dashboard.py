"""Qt quality dashboard for point-level scan diagnostics."""

from collections import Counter

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ap.checks import (
    AP_CHANNEL_CHANGE_AMBIGUOUS,
    AP_CHANNEL_CHANGE_CLEAN,
    build_ap_channel_changes,
)
from ap.groups import (
    AP_ROLE_TEST,
    build_default_manual_groups,
    build_bssid_to_manual_group_map,
    merge_new_bssids_into_manual_groups,
    normalize_ap_role,
    resolve_ap_group_key,
)
from ap.metadata import build_ap_metadata_warnings, infer_band_from_channel, sort_bands
from ap.positioning import (
    AP_POSITION_NO_SCALE,
    AP_POSITION_STRONG_FAR,
    AP_POSITION_UNEXPECTED_DOMINANT,
    AP_POSITION_WEAK_CLOSE,
    analyze_dominant_ap_position,
)
from maps.quality import (
    QUALITY_GOOD,
    QUALITY_LOW_CONFIDENCE,
    QUALITY_MISSING_RELEVANT,
    QUALITY_SPARSE_DATA,
    QUALITY_UNSTABLE_SIGNAL,
    evaluate_point_quality,
    get_dominant_candidate_rows,
    get_relevant_ssids_from_rows,
    group_rows_by_ssid,
    is_truthy,
    normalize_ssid,
    parse_float,
)
from qt_ui.scaling import widget_px
from qt_ui.qt_theme import QT_THEMES
from qt_ui.qt_windowing import SKIP_CENTERING_PROPERTY


QUALITY_SEVERITY = {
    QUALITY_GOOD: "good",
    QUALITY_MISSING_RELEVANT: "danger",
    QUALITY_LOW_CONFIDENCE: "warning",
    QUALITY_UNSTABLE_SIGNAL: "warning",
    QUALITY_SPARSE_DATA: "warning",
}

SEVERITY_COLORS = {
    "good": QColor("#e9f7ef"),
    "warning": QColor("#fff3cd"),
    "danger": QColor("#fdecea"),
}


class QualityDashboardDialog(QDialog):
    def __init__(self, app, rows, summary):
        super().__init__(app)
        self.app = app
        self.rows = rows
        self.filtered_rows = []
        self.setObjectName("qualityDashboardDialog")
        self.setProperty(SKIP_CENTERING_PROPERTY, True)
        self.setWindowTitle(app.tr("quality_dashboard_title"))
        self.resize(widget_px(self, 1480), widget_px(self, 860))
        self.setMinimumSize(widget_px(self, 1180), widget_px(self, 720))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(widget_px(self, 14), widget_px(self, 14), widget_px(self, 14), widget_px(self, 14))
        layout.setSpacing(widget_px(self, 8))

        hint = QLabel(app.tr("quality_dashboard_hint"))
        hint.setObjectName("mutedText")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addWidget(self.build_status_panel(summary))
        layout.addWidget(self.build_overview_panel(summary))
        layout.addLayout(self.build_controls())

        self.table = QTableWidget(0, 9)
        self.table.setObjectName("qualityDashboardTable")
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setHorizontalHeaderLabels([
            "#",
            "X",
            "Y",
            app.tr("quality_dashboard_scan_quality"),
            app.tr("quality_dashboard_confidence"),
            app.tr("best_dbm"),
            app.tr("rows"),
            app.tr("quality_dashboard_relevant_ssids"),
            app.tr("quality_dashboard_issue"),
        ])
        self.configure_table_columns()
        self.table.itemDoubleClicked.connect(lambda _item: self.focus_selected_point())
        layout.addWidget(self.table, 1)

        button_row = QHBoxLayout()
        self.focus_button = QPushButton(app.tr("go_to_point"))
        self.focus_button.clicked.connect(self.focus_selected_point)
        button_row.addWidget(self.focus_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.issues_only_check.toggled.connect(self.render_rows)
        self.issues_only_check.setChecked(summary.get("review_points", 0) > 0)
        self.render_rows()

    def build_status_panel(self, summary):
        panel = QFrame()
        panel.setObjectName("summaryPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(widget_px(self, 14), widget_px(self, 8), widget_px(self, 14), widget_px(self, 8))
        layout.setSpacing(widget_px(self, 3))

        title_key, message_key, severity = quality_status_text_keys(summary)
        title = QLabel(self.app.tr(title_key))
        title.setObjectName(f"metricValue_{severity}")
        message = QLabel(
            self.app.tr(
                message_key,
                count=summary.get("scan_review_points", summary["review_points"]),
                total=summary["total_points"],
            )
        )
        message.setObjectName("mutedText")
        message.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(message)
        return panel

    def configure_table_columns(self):
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        for column in range(7):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)

    def build_overview_panel(self, summary):
        panel = QFrame()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(widget_px(self, 10))
        layout.addWidget(self.build_summary_panel(summary), 4)
        layout.addWidget(self.build_recommendations_panel(summary), 3)
        return panel

    def build_summary_panel(self, summary):
        panel = QFrame()
        panel.setObjectName("summaryPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(widget_px(self, 10), widget_px(self, 9), widget_px(self, 10), widget_px(self, 10))
        layout.setSpacing(widget_px(self, 8))

        metric_groups = [
            (
                "quality_dashboard_metric_group_survey",
                [
                    ("quality_dashboard_metric_points", summary["total_points"], "info"),
                    ("quality_dashboard_metric_scan_ok", summary["scan_ok_points"], "good"),
                    ("quality_dashboard_metric_rescan", summary["scan_review_points"], "warning"),
                ],
            ),
            (
                "quality_dashboard_metric_group_scan",
                [
                    ("quality_dashboard_metric_missing", summary["missing_relevant"], "danger"),
                    ("quality_dashboard_metric_sparse", summary["sparse_data"], "warning"),
                    ("quality_dashboard_metric_low_confidence", summary["low_confidence"], "warning"),
                    ("quality_dashboard_metric_unstable", summary["unstable"], "warning"),
                ],
            ),
            (
                "quality_dashboard_metric_group_ap",
                [
                    ("quality_dashboard_metric_ap_diagnostic_points", summary["ap_diagnostic_points"], "warning"),
                    ("quality_dashboard_metric_ap_missing_positions", summary["ap_missing_positions"], "warning"),
                    ("quality_dashboard_metric_ap_metadata_warnings", summary["ap_metadata_warnings"], "warning"),
                    ("quality_dashboard_metric_channel_changes", summary["channel_change_count"], "info"),
                ],
            ),
        ]

        for title_key, metrics in metric_groups:
            layout.addWidget(self.create_metric_group(title_key, metrics), 1)

        return panel

    def create_metric_group(self, title_key, metrics):
        group = QFrame()
        group.setObjectName("qualityMetricGroup")
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(widget_px(self, 4))
        title = QLabel(self.app.tr(title_key))
        title.setObjectName("qualityMetricGroupTitle")
        layout.addWidget(title, 0)

        grid = QGridLayout()
        grid.setHorizontalSpacing(widget_px(self, 7))
        grid.setVerticalSpacing(0)
        for index, (label_key, value, severity) in enumerate(metrics):
            metric = self.create_metric_box(self.app.tr(label_key), value, severity if value else "good")
            grid.addWidget(metric, 0, index)
            grid.setColumnStretch(index, 1)
        grid.setRowStretch(0, 1)
        layout.addLayout(grid, 1)
        return group

    def create_metric_box(self, label, value, severity):
        palette = QT_THEMES.get(getattr(self.app, "theme", "light"), QT_THEMES["light"])
        accent = palette.get(
            {
                "good": "metric_good",
                "warning": "metric_warning",
                "danger": "metric_danger",
                "info": "metric_info",
            }.get(severity, "metric_info")
        )
        box = QFrame()
        box.setObjectName("qualityMetricBox")
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        box.setStyleSheet(
            f"""
            QFrame#qualityMetricBox {{
                background: {palette["panel_alt"]};
                border: 1px solid {palette["border"]};
                border-left: {widget_px(self, 5)}px solid {accent};
                border-radius: {widget_px(self, 7)}px;
            }}
            """
        )
        layout = QVBoxLayout(box)
        layout.setContentsMargins(widget_px(self, 11), widget_px(self, 9), widget_px(self, 11), widget_px(self, 9))
        layout.setSpacing(widget_px(self, 4))
        label_widget = QLabel(label)
        label_widget.setObjectName("mutedText")
        label_widget.setWordWrap(True)
        label_widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        label_widget.setStyleSheet(f"color: {palette['title']}; font-weight: 600; background: transparent;")
        value_widget = QLabel(str(value))
        value_widget.setObjectName(f"metricValue_{severity}")
        value_widget.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        value_widget.setStyleSheet(
            f"color: {accent}; font-size: {widget_px(self, 28)}px; font-weight: 800; background: transparent;"
        )
        layout.addWidget(label_widget, 1)
        layout.addWidget(value_widget, 0)
        return box

    def build_recommendations_panel(self, summary):
        panel = QFrame()
        panel.setObjectName("summaryPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(widget_px(self, 12), widget_px(self, 9), widget_px(self, 12), widget_px(self, 9))
        layout.setSpacing(widget_px(self, 6))

        title = QLabel(self.app.tr("quality_dashboard_fix_next_title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        recommendations = summary.get("recommendations", [])
        visible_recommendations = recommendations[:4]
        for recommendation in visible_recommendations:
            layout.addWidget(self.create_recommendation_card(recommendation))

        if len(recommendations) > len(visible_recommendations):
            more = QLabel(self.app.tr("quality_dashboard_more_issues", count=len(recommendations) - len(visible_recommendations)))
            more.setObjectName("mutedText")
            layout.addWidget(more)

        for line in summary.get("context_lines", []):
            context = QLabel(line)
            context.setObjectName("mutedText")
            context.setWordWrap(True)
            context.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(context)

        layout.addStretch(1)
        return panel

    def create_recommendation_card(self, recommendation):
        palette = QT_THEMES.get(getattr(self.app, "theme", "light"), QT_THEMES["light"])
        severity = recommendation.get("severity", "info")
        accent = palette.get(
            {
                "good": "metric_good",
                "warning": "metric_warning",
                "danger": "metric_danger",
                "info": "metric_info",
            }.get(severity, "metric_info")
        )

        card = QFrame()
        card.setObjectName("qualityRecommendationRow")
        card.setStyleSheet(
            f"""
            QFrame#qualityRecommendationRow {{
                background: {palette["panel_alt"]};
                border: 1px solid {palette["border"]};
                border-left: {widget_px(self, 4)}px solid {accent};
                border-radius: {widget_px(self, 5)}px;
            }}
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(widget_px(self, 9), widget_px(self, 5), widget_px(self, 8), widget_px(self, 6))
        layout.setSpacing(widget_px(self, 2))

        title = QLabel(recommendation.get("title", ""))
        title.setStyleSheet(f"color: {accent}; font-weight: 700; background: transparent;")
        title.setWordWrap(True)
        detail = QLabel(recommendation.get("detail", ""))
        detail.setObjectName("mutedText")
        detail.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(detail)
        actions = recommendation.get("actions", [])
        detail_items = recommendation.get("detail_items", [])
        if actions or detail_items:
            action_row = QHBoxLayout()
            action_row.setSpacing(widget_px(self, 6))
            if detail_items:
                detail_button = QPushButton(
                    self.app.tr("quality_dashboard_expand_details", count=len(detail_items))
                )
                detail_button.setObjectName("compactButton")
                detail_button.clicked.connect(
                    lambda _checked=False, selected_recommendation=recommendation:
                    self.open_recommendation_details(selected_recommendation)
                )
                action_row.addWidget(detail_button)
            inline_actions, map_actions = split_recommendation_actions(actions, has_details=bool(detail_items))
            for action in inline_actions:
                self.add_recommendation_action_button(action_row, action)
            action_row.addStretch(1)
            for action in map_actions:
                self.add_recommendation_action_button(action_row, action)
            layout.addLayout(action_row)
        return card

    def add_recommendation_action_button(self, layout, action):
        button = QPushButton(action.get("label", ""))
        button.setObjectName("compactButton")
        button.setMinimumWidth(0)
        button.clicked.connect(
            lambda _checked=False, selected_action=action: self.handle_recommendation_action(selected_action)
        )
        layout.addWidget(button)

    def open_recommendation_details(self, recommendation):
        dialog = RecommendationDetailsDialog(self, recommendation)
        dialog.exec()

    def handle_recommendation_action(self, action):
        kind = action.get("kind")
        if kind == "live_map":
            self.open_live_map_action(action)
            return
        if kind == "ap_metadata":
            self.open_ap_group_action(action.get("group_id"), open_metadata=True)
            return
        if kind == "ap_group":
            self.open_ap_group_action(action.get("group_id"), open_metadata=False)
            return
        if kind == "point":
            self.focus_point_action(action.get("row"))
            return

    def open_live_map_action(self, action):
        self.accept()
        app = self.app
        if not hasattr(app, "live_map_type_combo"):
            return

        map_type = action.get("map_type", "signal")
        band = action.get("band")
        group_id = "" if map_type == "interference" else action.get("group_id", "")
        app.tabs.setCurrentIndex(1)
        set_app_combo_data(app, app.live_map_type_combo, map_type)
        if hasattr(app, "update_live_option_state"):
            app.update_live_option_state()
        if hasattr(app, "refresh_live_band_options"):
            app.refresh_live_band_options(map_type, preferred_band=band)
        if band:
            set_app_combo_data(app, app.live_band_combo, band)
        if group_id and hasattr(app, "live_ap_group_combo"):
            if hasattr(app, "refresh_live_ap_group_filter"):
                app.refresh_live_ap_group_filter()
            set_app_combo_data(app, app.live_ap_group_combo, group_id)
        if hasattr(app, "update_live_option_state"):
            app.update_live_option_state()
        if hasattr(app, "update_live_preview") and not getattr(app, "live_rendering", False):
            app.update_live_preview()

    def open_ap_group_action(self, group_id, open_metadata=False):
        self.accept()
        if hasattr(self.app, "open_ap_group_manager"):
            self.app.open_ap_group_manager(focus_group_id=group_id, open_metadata=open_metadata)

    def focus_point_action(self, row):
        if not row:
            return

        self.accept()
        self.app.tabs.setCurrentIndex(0)
        self.app.floorplan_view.focus_on(row["x"], row["y"])
        self.app.show_points_panel()
        self.app.select_point_in_table(row)

    def build_controls(self):
        controls = QHBoxLayout()
        self.issues_only_check = QCheckBox(self.app.tr("quality_dashboard_show_issues_only"))
        self.visible_count_label = QLabel()
        self.visible_count_label.setObjectName("mutedText")
        controls.addWidget(self.issues_only_check)
        controls.addWidget(self.visible_count_label)
        controls.addStretch(1)
        return controls

    def render_rows(self):
        self.filtered_rows = [
            row
            for row in self.rows
            if not self.issues_only_check.isChecked() or row["needs_review"]
        ]
        self.table.setRowCount(len(self.filtered_rows))

        for row_index, row in enumerate(self.filtered_rows):
            values = [
                row["number"],
                row["x"],
                row["y"],
                row["quality"],
                row["confidence"],
                row["best"],
                row["row_count"],
                row["ssids"],
                row["issue"],
            ]
            background = SEVERITY_COLORS.get(row["severity"])
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row)
                if background is not None:
                    item.setBackground(background)
                if column_index <= 6:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    item.setToolTip(str(value))
                self.table.setItem(row_index, column_index, item)
            self.table.setRowHeight(row_index, widget_px(self, 38))

        self.visible_count_label.setText(
            self.app.tr(
                "quality_dashboard_visible_count",
                shown=len(self.filtered_rows),
                total=len(self.rows),
            )
        )
        self.focus_button.setEnabled(bool(self.filtered_rows))
        if self.filtered_rows:
            selected_row = next(
                (index for index, row in enumerate(self.filtered_rows) if row.get("needs_review")),
                0,
            )
            self.table.selectRow(selected_row)

    def current_row_data(self):
        selected = self.table.selectedItems()
        if not selected:
            return None

        item = self.table.item(selected[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def focus_selected_point(self):
        row = self.current_row_data()
        if not row:
            QMessageBox.warning(self, self.app.tr("warning"), self.app.tr("select_point"))
            return

        self.accept()
        self.app.tabs.setCurrentIndex(0)
        self.app.floorplan_view.focus_on(row["x"], row["y"])
        self.app.show_points_panel()
        self.app.select_point_in_table(row)


class RecommendationDetailsDialog(QDialog):
    def __init__(self, owner, recommendation):
        super().__init__(owner)
        self.owner = owner
        self.app = owner.app
        self.recommendation = recommendation
        items = recommendation.get("detail_items", [])
        detail_actions = recommendation.get("detail_actions", [])
        self.setWindowTitle(recommendation.get("title", self.app.tr("quality_dashboard_fix_next_title")))
        row_height = 98 if any(item.get("finding") for item in items) else 78
        height = 150 + max(1, len(items)) * row_height + (44 if detail_actions else 0)
        self.resize(
            widget_px(self, 980),
            min(widget_px(self, 720), widget_px(self, height)),
        )
        self.setMinimumSize(widget_px(self, 720), widget_px(self, 220))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(widget_px(self, 14), widget_px(self, 14), widget_px(self, 14), widget_px(self, 14))
        layout.setSpacing(widget_px(self, 8))

        title = QLabel(recommendation.get("title", ""))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        detail_text = recommendation.get("dialog_detail", recommendation.get("detail", ""))
        if detail_text:
            detail = QLabel(detail_text)
            detail.setObjectName("mutedText")
            detail.setWordWrap(True)
            layout.addWidget(detail)

        if detail_actions:
            actions_row = QHBoxLayout()
            actions_row.setSpacing(widget_px(self, 6))
            for action in detail_actions:
                button = QPushButton(action.get("label", ""))
                button.setObjectName("compactButton")
                button.clicked.connect(
                    lambda _checked=False, selected_action=action: self.handle_detail_action(selected_action)
                )
                actions_row.addWidget(button)
            actions_row.addStretch(1)
            layout.addLayout(actions_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QFrame()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(widget_px(self, 6))
        for item in items:
            content_layout.addWidget(self.create_detail_row(item))
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        close_button = QPushButton(self.app.tr("close"))
        close_button.setObjectName("compactButton")
        close_button.setMinimumWidth(widget_px(self, 120))
        close_button.setMaximumWidth(widget_px(self, 220))
        close_button.clicked.connect(self.accept)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

    def create_detail_row(self, item):
        palette = QT_THEMES.get(getattr(self.app, "theme", "light"), QT_THEMES["light"])
        row = QFrame()
        row.setObjectName("qualityDetailRow")
        row.setStyleSheet(
            f"""
            QFrame#qualityDetailRow {{
                background: {palette["panel_alt"]};
                border: 1px solid {palette["border"]};
                border-radius: {widget_px(self, 5)}px;
            }}
            """
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(widget_px(self, 10), widget_px(self, 7), widget_px(self, 8), widget_px(self, 7))
        layout.setSpacing(widget_px(self, 10))

        text_column = QVBoxLayout()
        text_column.setSpacing(widget_px(self, 2))
        label = QLabel(item.get("label", ""))
        label.setStyleSheet(f"color: {palette['title']}; font-weight: 700; background: transparent;")
        text_column.addWidget(label)

        if item.get("finding"):
            finding = QLabel(item.get("finding", ""))
            finding.setStyleSheet(f"color: {palette['metric_warning']}; font-weight: 600; background: transparent;")
            finding.setWordWrap(True)
            text_column.addWidget(finding)

        detail = QLabel(item.get("detail", ""))
        detail.setObjectName("mutedText")
        detail.setWordWrap(True)
        text_column.addWidget(detail)
        layout.addLayout(text_column, 1)

        for action in item.get("actions", []):
            button = QPushButton(action.get("label", ""))
            button.setObjectName("compactButton")
            button.setMinimumWidth(0)
            button.clicked.connect(
                lambda _checked=False, selected_action=action: self.handle_detail_action(selected_action)
            )
            layout.addWidget(button)

        return row

    def handle_detail_action(self, action):
        self.accept()
        self.owner.handle_recommendation_action(action)


def open_qt_quality_dashboard(app):
    point_summaries = app.session.get_point_summaries() if app.session else []
    if not point_summaries:
        QMessageBox.warning(app, app.tr("warning"), app.tr("empty_csv"))
        return

    relevant_ssids = get_effective_relevant_ssids(app)
    quality_by_point_id = evaluate_point_quality(
        app.session.rows,
        app.session.raw_scan_rows,
        relevant_ssids=relevant_ssids,
    )
    ap_groups = get_effective_ap_groups(app)
    ap_position_by_point = build_ap_position_quality_by_point(app, ap_groups)
    ap_metadata_warnings = build_ap_metadata_warnings(
        app.session.rows,
        ap_groups,
        app.channel_sort_key,
    )
    ap_channel_changes = build_ap_channel_changes(app.session.rows, ap_groups, app.channel_sort_key)
    rows = build_dashboard_rows(app, point_summaries, quality_by_point_id, ap_position_by_point)
    summary = build_summary(app, rows, ap_metadata_warnings, ap_groups, ap_channel_changes)
    dialog = QualityDashboardDialog(app, rows, summary)
    dialog.showMaximized()
    dialog.exec()


def build_dashboard_rows(app, point_summaries, quality_by_point_id, ap_position_by_point=None):
    total_points = len(point_summaries)
    rows = []
    ap_position_by_point = ap_position_by_point or {}
    relevant_ssids = get_effective_relevant_ssids(app)

    for index, point in enumerate(reversed(point_summaries), start=1):
        survey_number = total_points - index + 1
        quality = quality_by_point_id.get(point.get("point_id", ""), {})
        status = quality.get("status", QUALITY_SPARSE_DATA)
        ap_position = ap_position_by_point.get(point_key(point))
        ap_position_issue = format_ap_position_issue(app, ap_position)
        issue = format_quality_issue(app, quality)
        if ap_position_issue:
            issue = join_issues(issue, ap_position_issue, app.tr("quality_dashboard_no_issue"))

        needs_review = status != QUALITY_GOOD or bool(ap_position_issue)
        severity = QUALITY_SEVERITY.get(status, "warning")
        if ap_position_issue and status == QUALITY_GOOD:
            severity = "warning"

        rows.append({
            "point_id": point.get("point_id", ""),
            "timestamp": point["timestamp"],
            "number": survey_number,
            "x": point["x"],
            "y": point["y"],
            "quality": app.format_point_quality(status),
            "status": status,
            "needs_review": needs_review,
            "severity": severity,
            "ap_position_warning_count": len(ap_position.get("warnings", [])) if ap_position else 0,
            "ap_position": ap_position or {},
            "confidence": format_point_confidence(app.session.rows, point.get("point_id", ""), relevant_ssids),
            "best": f"{point['best_signal_dbm']:.1f}",
            "row_count": point["row_count"],
            "ssids": format_relevant_ssids(app.session.rows, point.get("point_id", ""), relevant_ssids),
            "issue": issue,
        })

    return rows


def get_effective_relevant_ssids(app):
    relevant_ssids = {
        normalize_ssid(ssid)
        for ssid in getattr(app, "relevant_ssids", set()) or []
        if normalize_ssid(ssid)
    }
    if relevant_ssids:
        return relevant_ssids

    if getattr(app, "session", None):
        return {
            normalize_ssid(ssid)
            for ssid in get_relevant_ssids_from_rows(app.session.rows)
            if normalize_ssid(ssid)
        }

    return set()


def get_effective_ap_groups(app):
    saved_groups = app.session.get_ap_groups()
    if saved_groups:
        return merge_new_bssids_into_manual_groups(saved_groups, app.session.rows)

    return build_default_manual_groups(app.session.rows)


def build_summary(app, rows, ap_metadata_warnings=None, ap_groups=None, ap_channel_changes=None):
    ap_metadata_warnings = ap_metadata_warnings or []
    ap_channel_changes = ap_channel_changes or []
    status_counts = Counter(row["status"] for row in rows)
    ap_groups = ap_groups if ap_groups is not None else get_effective_ap_groups(app)
    visible_ap_groups = [
        group
        for group in ap_groups
        if normalize_ap_role(group.get("role")) != AP_ROLE_TEST
    ]
    positioned_ap_groups = filter_ap_groups_for_relevant_ssids(app, visible_ap_groups)
    test_ap_count = len(ap_groups) - len(visible_ap_groups)
    positioned_count = sum(1 for group in positioned_ap_groups if group.get("position"))
    missing_position_groups = [group for group in positioned_ap_groups if not group.get("position")]
    relevant_networks = (
        ", ".join(sorted(app.relevant_ssids))
        if app.relevant_ssids
        else app.tr("relevant_networks_none")
    )
    missing_position_labels = ", ".join(
        app.get_ap_group_display_name(group.get("group_id", ""))
        for group in missing_position_groups[:4]
    )
    if len(missing_position_groups) > 4:
        missing_position_labels = app.tr(
            "quality_dashboard_missing_positions_more",
            names=missing_position_labels,
            count=len(missing_position_groups) - 4,
        )
    if not missing_position_labels:
        missing_position_labels = app.tr("quality_dashboard_missing_positions_none")

    summary = {
        "total_points": len(rows),
        "good_points": sum(1 for row in rows if not row["needs_review"]),
        "review_points": sum(1 for row in rows if row["needs_review"]),
        "scan_review_points": sum(1 for row in rows if row["status"] != QUALITY_GOOD),
        "missing_relevant": status_counts.get(QUALITY_MISSING_RELEVANT, 0),
        "low_confidence": status_counts.get(QUALITY_LOW_CONFIDENCE, 0),
        "unstable": status_counts.get(QUALITY_UNSTABLE_SIGNAL, 0),
        "sparse_data": status_counts.get(QUALITY_SPARSE_DATA, 0),
        "ap_position_warnings": sum(1 for row in rows if row.get("ap_position_warning_count", 0) > 0),
        "ap_missing_positions": len(missing_position_groups),
        "missing_position_labels": missing_position_labels,
        "missing_position_items": build_ap_group_items(app, missing_position_groups),
        "relevant_networks": relevant_networks,
        "ap_positions": f"{positioned_count}/{len(positioned_ap_groups)}" if positioned_ap_groups else "0/0",
        "test_aps": test_ap_count,
        "ap_metadata_warnings": len(ap_metadata_warnings),
        "ap_metadata_warning_labels": format_ap_metadata_warning_labels(app, ap_metadata_warnings),
        "ap_metadata_warning_items": build_ap_metadata_warning_items(app, ap_metadata_warnings),
        "channel_change_count": len(ap_channel_changes),
        "clean_channel_changes": sum(
            1 for change in ap_channel_changes if change.get("status") == AP_CHANNEL_CHANGE_CLEAN
        ),
        "ambiguous_channel_changes": sum(
            1 for change in ap_channel_changes if change.get("status") == AP_CHANNEL_CHANGE_AMBIGUOUS
        ),
        "channel_change_labels": format_ap_channel_change_labels(app, ap_channel_changes),
        "channel_change_items": build_ap_channel_change_items(app, ap_channel_changes),
    }
    summary["scan_ok_points"] = summary["total_points"] - summary["scan_review_points"]
    summary["ap_diagnostic_points"] = summary["ap_position_warnings"]
    summary["ap_position_warning_items"] = build_ap_position_warning_items(app, rows)
    summary["recommendations"] = build_quality_recommendations(app, summary)
    summary["context_lines"] = build_quality_context_lines(app, summary)
    return summary


def quality_status_text_keys(summary):
    if summary.get("scan_review_points", summary.get("review_points", 0)):
        return (
            "quality_dashboard_status_review_title",
            "quality_dashboard_status_review_message",
            "warning",
        )
    if (
        summary.get("ap_position_warnings", 0)
        or summary.get("ap_metadata_warnings", 0)
        or summary.get("ap_missing_positions", 0)
        or summary.get("channel_change_count", 0)
    ):
        return (
            "quality_dashboard_status_setup_title",
            "quality_dashboard_status_setup_message",
            "warning",
        )
    if summary["total_points"] < 5:
        return (
            "quality_dashboard_status_early_title",
            "quality_dashboard_status_early_message",
            "info",
        )
    return (
        "quality_dashboard_status_ok_title",
        "quality_dashboard_status_ok_message",
        "good",
    )


def build_quality_recommendations(app, summary):
    recommendations = []

    def add(
        count,
        title_key,
        detail_key,
        severity,
        actions=None,
        detail_items=None,
        detail_count_key=None,
        detail_actions=None,
        dialog_detail_key=None,
        **kwargs,
    ):
        if not count:
            return
        recommendation = {
            "severity": severity,
            "title": app.tr(title_key),
            "detail": app.tr(
                detail_key,
                count=count,
                total=summary["total_points"],
                **kwargs,
            ),
            "actions": actions or [],
            "detail_items": detail_items or [],
            "detail_count_label": app.tr(detail_count_key, count=count) if detail_count_key else "",
            "detail_actions": detail_actions or [],
        }
        if dialog_detail_key:
            recommendation["dialog_detail"] = app.tr(dialog_detail_key)
        recommendations.append(recommendation)

    add(
        summary["missing_relevant"],
        "quality_dashboard_fix_missing_title",
        "quality_dashboard_fix_missing_detail",
        "danger",
    )
    add(
        summary["sparse_data"],
        "quality_dashboard_fix_sparse_title",
        "quality_dashboard_fix_sparse_detail",
        "warning",
    )
    add(
        summary["low_confidence"],
        "quality_dashboard_fix_low_confidence_title",
        "quality_dashboard_fix_low_confidence_detail",
        "warning",
    )
    add(
        summary["unstable"],
        "quality_dashboard_fix_unstable_title",
        "quality_dashboard_fix_unstable_detail",
        "warning",
    )
    add(
        summary["ap_metadata_warnings"],
        "quality_dashboard_fix_ap_metadata_title",
        "quality_dashboard_fix_ap_metadata_detail",
        "warning",
        actions=build_ap_metadata_actions(app, summary),
        detail_items=build_ap_metadata_detail_items(app, summary.get("ap_metadata_warning_items", [])),
        detail_count_key="quality_dashboard_detail_ap_groups",
        dialog_detail_key="quality_dashboard_fix_ap_metadata_dialog_detail",
        details=summary["ap_metadata_warning_labels"],
    )
    add_channel_change_recommendation(app, summary, recommendations)
    add(
        summary["ap_position_warnings"],
        "quality_dashboard_fix_ap_position_title",
        "quality_dashboard_fix_ap_position_detail",
        "warning",
        actions=[
            {
                "kind": "live_map",
                "label": app.tr("quality_dashboard_action_open_dominant"),
                "map_type": "dominant",
                "band": "all",
            }
        ],
        detail_items=summary.get("ap_position_warning_items", []),
        detail_count_key="quality_dashboard_detail_measurement_points",
        dialog_detail_key="quality_dashboard_fix_ap_position_dialog_detail",
    )
    add(
        summary["ap_missing_positions"],
        "quality_dashboard_fix_ap_missing_title",
        "quality_dashboard_fix_ap_missing_detail",
        "warning",
        actions=build_ap_group_actions(app, summary.get("missing_position_items", []), open_metadata=False),
        detail_items=build_missing_position_detail_items(app, summary.get("missing_position_items", [])),
        detail_count_key="quality_dashboard_detail_ap_groups",
        names=summary["missing_position_labels"],
    )

    if not recommendations:
        if summary["total_points"] < 5:
            recommendations.append({
                "severity": "info",
                "title": app.tr("quality_dashboard_fix_more_points_title"),
                "detail": app.tr(
                    "quality_dashboard_fix_more_points_detail",
                    total=summary["total_points"],
                ),
            })
        else:
            recommendations.append({
                "severity": "good",
                "title": app.tr("quality_dashboard_fix_ready_title"),
                "detail": app.tr("quality_dashboard_fix_ready_detail"),
            })

    return recommendations


def build_quality_context_lines(app, summary):
    return [
        app.tr(
            "quality_dashboard_context_scope",
            networks=summary["relevant_networks"],
            positions=summary["ap_positions"],
            test_aps=summary["test_aps"],
        ),
    ]


def split_recommendation_actions(actions, has_details=False):
    action_limit = 2 if has_details else 4
    visible_actions = list(actions or [])[:action_limit]
    inline_actions = [
        action
        for action in visible_actions
        if action.get("kind") != "live_map"
    ]
    map_actions = [
        action
        for action in visible_actions
        if action.get("kind") == "live_map"
    ]
    return inline_actions, map_actions


def add_channel_change_recommendation(app, summary, recommendations):
    if not summary["channel_change_count"]:
        return

    has_ambiguous = summary["ambiguous_channel_changes"] > 0
    first_change = (summary.get("channel_change_items") or [{}])[0]
    actions = [
        {
            "kind": "live_map",
            "label": app.tr("quality_dashboard_action_open_ap_channels"),
            "map_type": "channel",
            "band": first_change.get("band", "all"),
            "group_id": first_change.get("group_id", ""),
        },
        {
            "kind": "live_map",
            "label": app.tr("quality_dashboard_action_open_interference"),
            "map_type": "interference",
            "band": first_change.get("band", "2.4"),
            "group_id": first_change.get("group_id", ""),
        },
    ]
    if first_change.get("group_id"):
        actions.append({
            "kind": "ap_metadata",
            "label": app.tr("quality_dashboard_action_open_ap_metadata"),
            "group_id": first_change["group_id"],
        })

    recommendations.append({
        "severity": "warning" if has_ambiguous else "info",
        "title": app.tr(
            "quality_dashboard_fix_channel_change_ambiguous_title"
            if has_ambiguous
            else "quality_dashboard_fix_channel_change_clean_title"
        ),
        "detail": app.tr(
            "quality_dashboard_fix_channel_change_detail",
            count=summary["channel_change_count"],
            clean=summary["clean_channel_changes"],
            ambiguous=summary["ambiguous_channel_changes"],
            details=summary["channel_change_labels"],
        ),
        "actions": actions,
        "detail_items": build_channel_change_detail_items(app, summary.get("channel_change_items", [])),
        "detail_count_label": app.tr(
            "quality_dashboard_detail_channel_changes",
            count=summary["channel_change_count"],
        ),
        "detail_actions": [],
        "dialog_detail": app.tr("quality_dashboard_fix_channel_change_dialog_detail"),
    })


def build_ap_metadata_actions(app, summary):
    items = summary.get("ap_metadata_warning_items", [])
    actions = []
    first = items[0] if items else {}
    if first:
        actions.extend([
            {
                "kind": "live_map",
                "label": app.tr("quality_dashboard_action_open_ap_channels"),
                "map_type": "channel",
                "band": first.get("band", "all"),
                "group_id": first.get("group_id", ""),
            },
            {
                "kind": "live_map",
                "label": app.tr("quality_dashboard_action_open_interference"),
                "map_type": "interference",
                "band": first.get("band", "2.4"),
                "group_id": first.get("group_id", ""),
            },
        ])
        if first.get("group_id"):
            actions.append({
                "kind": "ap_metadata",
                "label": app.tr("quality_dashboard_action_open_ap_metadata"),
                "group_id": first["group_id"],
            })
    return actions


def build_ap_group_actions(app, items, open_metadata=False):
    actions = []
    for item in items[:2]:
        group_id = item.get("group_id", "")
        if not group_id:
            continue
        actions.append({
            "kind": "ap_metadata" if open_metadata else "ap_group",
            "group_id": group_id,
            "label": app.tr(
                "quality_dashboard_action_metadata_for" if open_metadata else "quality_dashboard_action_group_for",
                ap=item.get("label", group_id),
            ),
        })
    return actions


def build_ap_group_items(app, groups):
    return [
        {
            "group_id": str(group.get("group_id", "")),
            "label": app.get_ap_group_display_name(group.get("group_id", "")),
        }
        for group in groups
        if str(group.get("group_id", ""))
    ]


def build_ap_metadata_warning_items(app, warnings):
    return [
        {
            "group_id": str(warning.get("group_id", "")),
            "label": app.get_ap_group_display_name(warning.get("group_id", "")),
            "detail": format_ap_metadata_warning_detail(app, warning),
            "band": metadata_warning_primary_band(warning),
        }
        for warning in warnings
    ]


def build_ap_channel_change_items(app, changes):
    return [
        {
            "group_id": str(change.get("group_id", "")),
            "label": app.get_ap_group_display_name(change.get("group_id", "")),
            "band": str(change.get("band", "")) or "all",
            "status": change.get("status", ""),
            "channels": change.get("channels", []),
            "current_channel": change.get("current_channel", ""),
            "detail": app.tr(
                "quality_dashboard_channel_change_item_detail",
                band=format_band_label(change.get("band", "")),
                status=app.tr(
                    "quality_dashboard_channel_change_status_ambiguous"
                    if change.get("status") == AP_CHANNEL_CHANGE_AMBIGUOUS
                    else "quality_dashboard_channel_change_status_clean"
                ),
                channels=", ".join(change.get("channels", [])) or "-",
                current=change.get("current_channel", "") or "-",
            ),
        }
        for change in changes
    ]


def build_ap_metadata_detail_items(app, items):
    detail_items = []
    for item in items:
        group_id = item.get("group_id", "")
        actions = []
        if group_id:
            actions.append({
                "kind": "ap_metadata",
                "label": app.tr("quality_dashboard_action_open_ap_metadata"),
                "group_id": group_id,
            })
        detail_items.append({
            "label": item.get("label", group_id),
            "detail": item.get("detail", ""),
            "actions": actions,
        })
    return detail_items


def build_channel_change_detail_items(app, items):
    detail_items = []
    for item in items:
        group_id = item.get("group_id", "")
        actions = []
        if group_id:
            actions.append({
                "kind": "ap_metadata",
                "label": app.tr("quality_dashboard_action_open_ap_metadata"),
                "group_id": group_id,
            })
        detail_items.append({
            "label": item.get("label", group_id),
            "detail": item.get("detail", ""),
            "actions": actions,
        })
    return detail_items


def build_missing_position_detail_items(app, items):
    return [
        {
            "label": item.get("label", item.get("group_id", "")),
            "detail": app.tr("quality_dashboard_missing_position_item_detail"),
            "actions": [
                {
                    "kind": "ap_group",
                    "group_id": item.get("group_id", ""),
                    "label": app.tr("quality_dashboard_action_open_ap_group"),
                }
            ],
        }
        for item in items
    ]


def build_ap_position_warning_items(app, rows):
    items = []
    for row in rows:
        if not row.get("ap_position_warning_count", 0):
            continue
        items.append({
            "label": app.tr(
                "quality_dashboard_point_detail_label",
                point=row.get("number", "-"),
                x=row.get("x", "-"),
                y=row.get("y", "-"),
            ),
            "finding": format_ap_position_finding(app, row),
            "detail": format_ap_position_detail(app, row),
            "actions": [
                {
                    "kind": "point",
                    "row": row,
                    "label": app.tr("quality_dashboard_action_focus_point"),
                },
            ],
        })
    return items


def format_ap_position_finding(app, row):
    ap_position = row.get("ap_position") or {}
    return app.tr(
        "quality_dashboard_ap_position_finding",
        finding=format_ap_position_warning_summary(app, ap_position),
    )


def format_ap_position_detail(app, row):
    ap_position = row.get("ap_position") or {}
    analysis = ap_position.get("analysis") or {}
    dominant_group_id = ap_position.get("dominant_ap_group", "")
    dominant_label = app.get_ap_group_display_name(dominant_group_id) if dominant_group_id else "-"
    nearest_group_id = analysis.get("nearest_ap_group", "")
    nearest_label = app.get_ap_group_display_name(nearest_group_id) if nearest_group_id else "-"
    return app.tr(
        "quality_dashboard_ap_position_detail",
        dominant=dominant_label,
        signal=format_dbm(ap_position.get("dominant_signal_dbm")),
        dominant_distance=format_ap_distance(app, analysis, "dominant"),
        closest=nearest_label,
        closest_distance=format_ap_distance(app, analysis, "nearest"),
    )


def format_ap_position_warning_summary(app, ap_position):
    warning_labels = [
        app.tr(ap_position_warning_translation_key(warning))
        for warning in ap_position.get("warnings", [])
    ]
    if warning_labels:
        return "; ".join(warning_labels)
    return app.tr("ap_position_unknown_warning")


def format_ap_distance(app, analysis, prefix):
    distance_m = analysis.get(f"{prefix}_distance_m")
    if distance_m is not None:
        return app.tr("ap_position_distance_m", distance=f"{distance_m:.1f}")

    distance_px = analysis.get(f"{prefix}_distance_px")
    if distance_px is not None:
        return app.tr("ap_position_distance_px", distance=f"{distance_px:.0f}")

    return "-"


def format_dbm(value):
    number = parse_float(value)
    return f"{number:.1f} dBm" if number is not None else "-"


def format_ap_channel_change_labels(app, changes):
    if not changes:
        return app.tr("quality_dashboard_missing_positions_none")

    labels = []
    for change in changes[:3]:
        labels.append(app.tr(
            "quality_dashboard_channel_change_label",
            ap=app.get_ap_group_display_name(change.get("group_id", "")),
            band=format_band_label(change.get("band", "")),
            status=app.tr(
                "quality_dashboard_channel_change_status_ambiguous"
                if change.get("status") == AP_CHANNEL_CHANGE_AMBIGUOUS
                else "quality_dashboard_channel_change_status_clean"
            ),
            channels=", ".join(change.get("channels", [])) or "-",
            current=change.get("current_channel", "") or "-",
        ))
    if len(changes) > 3:
        labels.append(app.tr("quality_dashboard_more_issues", count=len(changes) - 3))
    return "; ".join(labels)


def metadata_warning_primary_band(warning):
    bands = set(warning.get("unexpected_bands", []) or warning.get("observed_bands", []))
    for channel in warning.get("unexpected_channels", []):
        band = infer_band_from_channel(channel)
        if band:
            bands.add(band)
    sorted_bands = sort_bands(bands)
    return sorted_bands[0] if sorted_bands else "all"


def set_app_combo_data(app, combo, value):
    if hasattr(app, "set_combo_value_silent"):
        app.set_combo_value_silent(combo, value)
        return combo.currentData() == value
    return set_combo_data(combo, value)


def set_combo_data(combo, value):
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)
        return True
    return False


def filter_ap_groups_for_relevant_ssids(app, ap_groups):
    relevant_ssids = {
        normalize_ssid(ssid)
        for ssid in app.relevant_ssids or []
        if normalize_ssid(ssid)
    }
    if not relevant_ssids:
        return list(ap_groups)

    group_map = build_bssid_to_manual_group_map(ap_groups)
    relevant_group_ids = set()
    for row in app.session.rows:
        if normalize_ssid(row.get("ssid")) not in relevant_ssids:
            continue

        group_id = resolve_ap_group_key(row.get("bssid", ""), group_map)
        if group_id:
            relevant_group_ids.add(group_id)

    return [
        group
        for group in ap_groups
        if str(group.get("group_id", "")) in relevant_group_ids
    ]


def build_ap_position_quality_by_point(app, ap_groups=None):
    ap_groups = ap_groups if ap_groups is not None else get_effective_ap_groups(app)
    if not ap_groups:
        return {}

    group_map = build_bssid_to_manual_group_map(ap_groups)
    position_ap_groups = filter_ap_groups_for_relevant_ssids(app, ap_groups)
    role_map = {
        str(group.get("group_id", "")): normalize_ap_role(group.get("role"))
        for group in ap_groups
    }
    relevant_ssids = {
        normalize_ssid(ssid)
        for ssid in app.relevant_ssids or []
        if normalize_ssid(ssid)
    }
    best_by_point = {}

    for row in app.session.rows:
        if not row_is_relevant_for_position(row, relevant_ssids):
            continue

        bssid = row.get("bssid", "")
        group_id = resolve_ap_group_key(bssid, group_map)
        if role_map.get(group_id) == AP_ROLE_TEST:
            continue

        signal_dbm = parse_float(row.get("signal_dbm"))
        if signal_dbm is None:
            continue

        key = row_point_key(row)
        current = best_by_point.get(key)
        if current and signal_dbm <= current["dominant_signal_dbm"]:
            continue

        best_by_point[key] = {
            "timestamp": row.get("timestamp", ""),
            "x": row.get("x", ""),
            "y": row.get("y", ""),
            "dominant_ap_group": group_id,
            "dominant_bssid": bssid,
            "dominant_signal_dbm": signal_dbm,
        }

    result = {}
    for key, dominant_row in best_by_point.items():
        analysis = analyze_dominant_ap_position(
            dominant_row,
            position_ap_groups,
            app.get_px_per_meter(),
        )
        warnings = analysis.get("warnings", [])
        if warnings:
            result[key] = {
                "analysis": analysis,
                "dominant_ap_group": dominant_row.get("dominant_ap_group", ""),
                "dominant_bssid": dominant_row.get("dominant_bssid", ""),
                "dominant_signal_dbm": dominant_row.get("dominant_signal_dbm"),
                "warnings": warnings,
            }

    return result


def row_is_relevant_for_position(row, relevant_ssids):
    if not relevant_ssids:
        return True

    return normalize_ssid(row.get("ssid")) in relevant_ssids or is_truthy(row.get("is_relevant"))


def row_point_key(row):
    if row.get("point_id"):
        return row.get("point_id")

    return f"{row.get('timestamp', '')}|{row.get('x', '')}|{row.get('y', '')}"


def point_key(point):
    if point.get("point_id"):
        return point.get("point_id")

    return f"{point.get('timestamp', '')}|{point.get('x', '')}|{point.get('y', '')}"


def format_ap_position_issue(app, ap_position):
    if not ap_position:
        return ""

    warning_labels = [
        app.tr(ap_position_warning_translation_key(warning))
        for warning in ap_position.get("warnings", [])
    ]
    if not warning_labels:
        return ""

    ap_label = app.get_ap_group_display_name(ap_position.get("dominant_ap_group", ""))
    return app.tr(
        "quality_dashboard_ap_position_issue",
        ap=ap_label,
        warning="; ".join(warning_labels),
    )


def ap_position_warning_translation_key(warning):
    return {
        AP_POSITION_NO_SCALE: "ap_position_no_scale",
        AP_POSITION_STRONG_FAR: "ap_position_strong_far",
        AP_POSITION_WEAK_CLOSE: "ap_position_weak_close",
        AP_POSITION_UNEXPECTED_DOMINANT: "ap_position_unexpected_dominant",
    }.get(warning, "ap_position_unknown_warning")


def join_issues(current_issue, extra_issue, no_issue_label):
    if not current_issue or current_issue == no_issue_label:
        return extra_issue

    return f"{current_issue}; {extra_issue}"


def format_quality_issue(app, quality):
    breakdown = quality.get("breakdown", [])
    issues = [
        f"{item.get('ssid', '-')}: {app.format_quality_breakdown_item(item)}"
        for item in breakdown
        if item.get("status") != QUALITY_GOOD
    ]
    if issues:
        return "; ".join(issues)

    status = quality.get("status")
    if status and status != QUALITY_GOOD:
        return app.format_point_quality(status)

    return app.tr("quality_dashboard_no_issue")


def format_point_confidence(rows, point_id, relevant_ssids):
    values = []
    relevant_ssids = {
        normalize_ssid(ssid)
        for ssid in relevant_ssids or []
        if normalize_ssid(ssid)
    }
    point_rows = []

    for row in rows:
        if row.get("point_id") != point_id:
            continue
        if relevant_ssids:
            if normalize_ssid(row.get("ssid")) not in relevant_ssids and not is_truthy(row.get("is_relevant")):
                continue
        point_rows.append(row)

    if relevant_ssids:
        confidence_rows = []
        for ssid_rows in group_rows_by_ssid(point_rows).values():
            confidence_rows.extend(get_dominant_candidate_rows(ssid_rows))
    else:
        confidence_rows = get_dominant_candidate_rows(point_rows)

    for row in confidence_rows:
        confidence = parse_float(row.get("scan_confidence"))
        if confidence is not None:
            values.append(confidence)

    if not values:
        return "-"

    return f"{min(values):.2f}"


def format_relevant_ssids(rows, point_id, relevant_ssids):
    relevant_ssids = {
        normalize_ssid(ssid)
        for ssid in relevant_ssids or []
        if normalize_ssid(ssid)
    }
    labels_by_key = {}

    for row in rows:
        if row.get("point_id") != point_id:
            continue

        ssid = str(row.get("ssid") or "").strip()
        ssid_key = normalize_ssid(ssid)
        if not ssid_key:
            continue

        if relevant_ssids:
            if ssid_key not in relevant_ssids:
                continue
        elif not is_truthy(row.get("is_relevant")):
            continue

        labels_by_key.setdefault(ssid_key, ssid)

    labels = sorted(labels_by_key.values(), key=str.casefold)
    return ", ".join(labels) if labels else "-"


def format_ap_metadata_warning_labels(app, warnings):
    if not warnings:
        return app.tr("quality_dashboard_missing_positions_none")

    labels = [format_ap_metadata_warning(app, warning) for warning in warnings[:3]]
    if len(warnings) > 3:
        labels.append(app.tr("quality_dashboard_more_issues", count=len(warnings) - 3))

    return "; ".join(labels)


def format_ap_metadata_warning(app, warning):
    ap_label = app.get_ap_group_display_name(warning.get("group_id", ""))
    detail = format_ap_metadata_warning_detail(app, warning)
    return f"{ap_label}: {detail}" if detail else ap_label


def format_ap_metadata_warning_detail(app, warning):
    parts = []
    unexpected_channels = warning.get("unexpected_channels", [])
    unexpected_bands = warning.get("unexpected_bands", [])
    if unexpected_channels:
        parts.append(
            app.tr(
                "quality_dashboard_ap_metadata_channels",
                channels=", ".join(unexpected_channels),
                expected=", ".join(warning.get("expected_channels", [])) or "-",
            )
        )
    if unexpected_bands:
        parts.append(
            app.tr(
                "quality_dashboard_ap_metadata_bands",
                bands=", ".join(format_band_label(band) for band in unexpected_bands),
                expected=", ".join(format_band_label(band) for band in warning.get("expected_bands", [])) or "-",
            )
        )

    return ", ".join(parts)


def format_band_label(band):
    if str(band) == "2.4":
        return "2.4 GHz"
    if str(band) in {"5", "6"}:
        return f"{band} GHz"
    return str(band)
