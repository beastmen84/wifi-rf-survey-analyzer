"""Qt quality dashboard for point-level scan diagnostics."""

from html import escape

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QTextDocument
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
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
    AP_MEMORY_APPLIED_AT_KEY,
    AP_MEMORY_APPLIED_KEY,
    AP_MEMORY_MATCH_BSSIDS_KEY,
    AP_ROLE_TEST,
    build_default_manual_groups,
    build_bssid_to_manual_group_map,
    merge_new_bssids_into_manual_groups,
    normalize_ap_role,
    resolve_ap_group_key,
)
from ap.memory import count_memory_applied_groups
from ap.metadata import build_ap_metadata_warnings, infer_band_from_channel, sort_bands
from ap.positioning import (
    AP_POSITION_NO_SCALE,
    AP_POSITION_STRONG_FAR,
    AP_POSITION_UNEXPECTED_DOMINANT,
    AP_POSITION_WEAK_CLOSE,
    analyze_dominant_ap_position,
)
from app_core.units import format_distance_meters
from maps.quality import (
    QUALITY_GOOD,
    QUALITY_LOW_CONFIDENCE,
    QUALITY_MISSING_RELEVANT,
    QUALITY_SPARSE_DATA,
    QUALITY_UNSTABLE_SIGNAL,
    SCANNER_DETAIL_FALLBACK_BACKEND,
    SCANNER_DETAIL_MISSING_6GHZ_FREQUENCY,
    SCANNER_DETAIL_MISSING_CHANNEL_WIDTH,
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

METRIC_ACCENT_KEYS = {
    "good": "metric_good",
    "warning": "metric_warning",
    "danger": "metric_danger",
    "info": "metric_info",
}

SEVERITY_COLORS = {
    "good": QColor("#e9f7ef"),
    "warning": QColor("#fff3cd"),
    "danger": QColor("#fdecea"),
}

METRIC_GRID_COLUMNS = 3
POINT_TABLE_MAX_VISIBLE_ROWS = 14
POINT_TABLE_ROW_HEIGHT = 38
SCANNER_DETAIL_DEFAULT_VISIBLE_CARDS = 4
DETAIL_ROW_HEIGHT = 78
DETAIL_FINDING_ROW_HEIGHT = 98
SCANNER_DETAIL_ROW_HEIGHT = 145
DETAIL_DIALOG_MAX_HEIGHT = 720
SCANNER_DETAIL_DIALOG_MAX_HEIGHT = 760
DETAIL_VISIBLE_CARD_LIMITS = {
    "quality_dashboard_metric_scanner_details": SCANNER_DETAIL_DEFAULT_VISIBLE_CARDS,
    "quality_dashboard_metric_ap_diagnostic_points": 5,
    "quality_dashboard_metric_ap_metadata_warnings": 5,
    "quality_dashboard_metric_channel_changes": 6,
    "quality_dashboard_metric_ap_missing_positions": 8,
    "quality_dashboard_metric_ap_memory_applied": 6,
}
DETAIL_DIALOG_MAX_HEIGHTS = {
    "quality_dashboard_metric_scanner_details": SCANNER_DETAIL_DIALOG_MAX_HEIGHT,
    "quality_dashboard_metric_ap_missing_positions": 820,
}


QUALITY_METRIC_STATUSES = {
    "quality_dashboard_metric_missing": QUALITY_MISSING_RELEVANT,
    "quality_dashboard_metric_sparse": QUALITY_SPARSE_DATA,
    "quality_dashboard_metric_low_confidence": QUALITY_LOW_CONFIDENCE,
    "quality_dashboard_metric_unstable": QUALITY_UNSTABLE_SIGNAL,
}


POINT_METRIC_FILTERS = {
    "quality_dashboard_metric_rescan": (
        lambda row: (
            row.get("status") != QUALITY_GOOD
            or row.get("scanner_detail_issue")
            or row.get("ap_position_warning_count", 0) > 0
        )
    ),
    "quality_dashboard_metric_missing": lambda row: row_has_quality_status(row, QUALITY_MISSING_RELEVANT),
    "quality_dashboard_metric_sparse": lambda row: row_has_quality_status(row, QUALITY_SPARSE_DATA),
    "quality_dashboard_metric_low_confidence": lambda row: row_has_quality_status(row, QUALITY_LOW_CONFIDENCE),
    "quality_dashboard_metric_unstable": lambda row: row_has_quality_status(row, QUALITY_UNSTABLE_SIGNAL),
}


def recommendation_detail_visible_item_count(recommendation, items):
    item_count = max(1, len(items))
    limit = DETAIL_VISIBLE_CARD_LIMITS.get(recommendation.get("metric_key"))
    return min(item_count, limit) if limit else item_count


def recommendation_detail_row_height(recommendation, items):
    if is_scanner_detail_recommendation(recommendation):
        return SCANNER_DETAIL_ROW_HEIGHT
    if any(item.get("finding") for item in items):
        return DETAIL_FINDING_ROW_HEIGHT
    return DETAIL_ROW_HEIGHT


def recommendation_detail_max_height(recommendation):
    return DETAIL_DIALOG_MAX_HEIGHTS.get(recommendation.get("metric_key"), DETAIL_DIALOG_MAX_HEIGHT)


def recommendation_detail_scroll_max_height(row_heights, spacing, visible_items):
    shown_heights = list(row_heights[:visible_items])
    if not shown_heights:
        return 0
    return sum(shown_heights) + max(0, len(shown_heights) - 1) * spacing


def is_scanner_detail_recommendation(recommendation):
    return recommendation.get("metric_key") == "quality_dashboard_metric_scanner_details"


def point_rows_for_metric(rows, metric_key):
    row_filter = POINT_METRIC_FILTERS.get(metric_key)
    if row_filter is None:
        return []
    return [row for row in rows if row_filter(row)]


class RichTextItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        option = QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        text = option.text
        option.text = ""

        widget = option.widget
        style = widget.style() if widget is not None else None
        if style is not None:
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, option, painter, widget)

        color = (
            option.palette.highlightedText().color().name()
            if option.state & QStyle.StateFlag.State_Selected
            else option.palette.text().color().name()
        )
        document = QTextDocument()
        document.setDefaultStyleSheet(f"body {{ color: {color}; margin: 0; white-space: nowrap; }}")
        document.setHtml(f"<body>{text}</body>")
        document.setTextWidth(option.rect.width())

        text_rect = option.rect.adjusted(6, 0, -6, 0)
        y_offset = max(0, int((text_rect.height() - document.size().height()) / 2))
        painter.save()
        painter.setClipRect(text_rect)
        painter.translate(text_rect.left(), text_rect.top() + y_offset)
        document.drawContents(painter, QRectF(0, 0, text_rect.width(), text_rect.height()))
        painter.restore()


def row_quality_statuses(row):
    statuses = {
        item.get("status")
        for item in row.get("quality_breakdown", [])
        if item.get("status") and item.get("status") != QUALITY_GOOD
    }
    status = row.get("status")
    if status and status != QUALITY_GOOD:
        statuses.add(status)
    return statuses


def row_has_quality_status(row, status):
    return status in row_quality_statuses(row)


def count_rows_with_quality_status(rows, status):
    return sum(1 for row in rows if row_has_quality_status(row, status))


def is_point_metric_filter(metric_key, value):
    if metric_key not in POINT_METRIC_FILTERS:
        return False

    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return bool(value)


def point_table_visible_row_count(row_count):
    try:
        count = int(row_count)
    except (TypeError, ValueError):
        count = 0
    return max(1, min(count, POINT_TABLE_MAX_VISIBLE_ROWS))


def format_metric_point_issue(app, row, metric_key):
    no_issue = app.tr("quality_dashboard_no_issue")
    if metric_key == "quality_dashboard_metric_points":
        return row.get("issue") or no_issue
    if metric_key == "quality_dashboard_metric_scan_ok":
        return no_issue
    if metric_key == "quality_dashboard_metric_rescan":
        kpis = rescan_kpi_labels_for_row(app, row)
        return app.tr("quality_dashboard_check_kpi_issue", kpis="; ".join(kpis)) if kpis else no_issue
    if metric_key in QUALITY_METRIC_STATUSES:
        return format_metric_quality_issue(app, row, QUALITY_METRIC_STATUSES[metric_key])
    if metric_key == "quality_dashboard_metric_scanner_details":
        return format_scanner_detail_summary(app, row.get("scanner_details", {}))
    if metric_key == "quality_dashboard_metric_ap_diagnostic_points":
        return format_ap_position_point_issue(app, row) or no_issue
    return row.get("issue") or no_issue


def format_metric_quality_issue(app, row, target_status):
    no_issue = app.tr("quality_dashboard_no_issue")
    issues = [
        format_quality_breakdown_issue(app, item)
        for item in row.get("quality_breakdown", [])
        if item.get("status") == target_status
    ]
    if issues:
        return "; ".join(issues)
    if row.get("status") == target_status:
        return row.get("quality_issue") or format_quality_status_issue(app, target_status)
    return no_issue


def format_quality_breakdown_issue(app, item):
    ssid = format_issue_ssid(item.get("ssid", "-"))
    status = item.get("status")
    if status == QUALITY_MISSING_RELEVANT:
        return app.tr("quality_dashboard_issue_missing_relevant", ssid=ssid)
    if status == QUALITY_LOW_CONFIDENCE:
        confidence = format_confidence_percent(item.get("min_confidence"))
        if confidence:
            return app.tr("quality_dashboard_issue_low_confidence", ssid=ssid, confidence=confidence)
    if status == QUALITY_UNSTABLE_SIGNAL:
        range_db = format_db_value(item.get("range_db"))
        if range_db:
            return app.tr("quality_dashboard_issue_unstable_signal", ssid=ssid, range=range_db)
    if status == QUALITY_GOOD:
        return app.tr("quality_dashboard_no_issue")
    return f"{ssid}: {escape(str(app.format_quality_breakdown_item(item)))}"


def format_quality_status_issue(app, status):
    if status == QUALITY_SPARSE_DATA:
        return app.tr("quality_dashboard_issue_sparse_data")
    if status == QUALITY_MISSING_RELEVANT:
        return app.tr("quality_missing_relevant")
    if status == QUALITY_LOW_CONFIDENCE:
        return app.tr("quality_low_confidence")
    if status == QUALITY_UNSTABLE_SIGNAL:
        return app.tr("quality_unstable_signal")
    return app.format_point_quality(status)


def format_issue_ssid(ssid):
    text = str(ssid or "-")
    return escape(text.upper() if text != "-" else text)


def format_confidence_percent(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return f"{number * 100:.0f}%"


def format_db_value(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return f"{number:.1f}"


def rescan_kpi_labels_for_row(app, row):
    labels = []
    seen_keys = set()
    status_metric_keys = {
        QUALITY_MISSING_RELEVANT: "quality_dashboard_metric_missing",
        QUALITY_SPARSE_DATA: "quality_dashboard_metric_sparse",
        QUALITY_LOW_CONFIDENCE: "quality_dashboard_metric_low_confidence",
        QUALITY_UNSTABLE_SIGNAL: "quality_dashboard_metric_unstable",
    }

    for status in (
        QUALITY_MISSING_RELEVANT,
        QUALITY_SPARSE_DATA,
        QUALITY_LOW_CONFIDENCE,
        QUALITY_UNSTABLE_SIGNAL,
    ):
        if status not in row_quality_statuses(row):
            continue
        metric_key = status_metric_keys.get(status)
        if metric_key and metric_key not in seen_keys:
            labels.append(app.tr(metric_key))
            seen_keys.add(metric_key)

    if row.get("scanner_detail_issue"):
        labels.append(app.tr("quality_dashboard_metric_scanner_details"))
    if row.get("ap_position_warning_count", 0) > 0:
        labels.append(app.tr("quality_dashboard_metric_ap_diagnostic_points"))
    return labels


def configure_point_table_columns(table):
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)


def populate_point_table(table, rows, owner, metric_key=None):
    table.setRowCount(len(rows))

    for row_index, row in enumerate(rows):
        issue_text = (
            format_metric_point_issue(owner.app, row, metric_key)
            if metric_key
            else row["issue"]
        )
        values = [
            row["number"],
            row["x"],
            row["y"],
            issue_text,
        ]
        background = SEVERITY_COLORS.get(row["severity"])
        for column_index, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            if column_index == 0:
                item.setData(Qt.ItemDataRole.UserRole, row)
            if background is not None:
                item.setBackground(background)
            if column_index <= 2:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item.setToolTip(str(value))
            table.setItem(row_index, column_index, item)
        table.setRowHeight(row_index, widget_px(owner, POINT_TABLE_ROW_HEIGHT))


def resolve_metric_severity(label_key, value, default_severity):
    if label_key == "quality_dashboard_metric_points":
        return "info"

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        numeric_value = None

    if numeric_value == 0 and default_severity in {"warning", "danger", "info"}:
        return "good"

    return default_severity


def hex_to_rgb(color):
    color = str(color or "").lstrip("#")
    if len(color) != 6:
        return (255, 255, 255)
    return tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))


def mix_hex(color, accent, ratio):
    base_rgb = hex_to_rgb(color)
    accent_rgb = hex_to_rgb(accent)
    mixed = [
        round(base + (target - base) * ratio)
        for base, target in zip(base_rgb, accent_rgb)
    ]
    return "#{:02X}{:02X}{:02X}".format(*mixed)


def palette_is_dark(palette):
    red, green, blue = hex_to_rgb(palette.get("panel", "#FFFFFF"))
    return (red * 0.299 + green * 0.587 + blue * 0.114) < 128


def metric_card_tokens(palette, severity):
    accent = palette.get(METRIC_ACCENT_KEYS.get(severity, "metric_info"))
    dark = palette_is_dark(palette)
    return {
        "accent": accent,
        "top": mix_hex(palette["panel"], accent, 0.12 if dark else 0.06),
        "bottom": mix_hex(palette["panel_alt"], accent, 0.16 if dark else 0.10),
        "border": mix_hex(palette["border"], accent, 0.35 if dark else 0.22),
        "shadow": QColor(0, 0, 0, 80 if dark else 32),
    }


class DiagonalPlaceholderFrame(QFrame):
    def __init__(self, stripe_color, parent=None):
        super().__init__(parent)
        self.stripe_color = QColor(stripe_color)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(self.stripe_color)
        pen.setWidth(max(1, widget_px(self, 1)))
        painter.setPen(pen)
        spacing = max(8, widget_px(self, 13))
        height = self.height()
        for x in range(-height, self.width() + height, spacing):
            painter.drawLine(x, height, x + height, 0)


class QualityDashboardDialog(QDialog):
    def __init__(self, app, rows, summary):
        super().__init__(app)
        self.app = app
        self.rows = rows
        self.summary = summary
        self.recommendations_by_metric = {
            recommendation.get("metric_key"): recommendation
            for recommendation in summary.get("recommendations", [])
            if recommendation.get("metric_key")
        }
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
        layout.addWidget(self.build_overview_panel(summary), 1)

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

    def build_overview_panel(self, summary):
        panel = QFrame()
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(widget_px(self, 10))
        layout.addWidget(self.build_summary_panel(summary), 5)
        layout.addWidget(self.build_recommendations_panel(summary), 3)
        return panel

    def build_summary_panel(self, summary):
        palette = QT_THEMES.get(getattr(self.app, "theme", "light"), QT_THEMES["light"])
        panel = QFrame()
        panel.setObjectName("summaryPanel")
        panel.setStyleSheet(
            f"""
            QFrame#summaryPanel {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {mix_hex(palette["panel"], palette["metric_info"], 0.035)},
                    stop:1 {mix_hex(palette["panel_alt"], palette["metric_info"], 0.055)}
                );
                border: 0;
                border-radius: {widget_px(self, 9)}px;
            }}
            """
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(widget_px(self, 12), widget_px(self, 10), widget_px(self, 12), widget_px(self, 12))
        layout.setSpacing(widget_px(self, 11))

        channel_change_severity = "warning" if summary.get("ambiguous_channel_changes", 0) else "info"

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
                    ("quality_dashboard_metric_scanner_details", summary["scanner_detail_points"], "warning"),
                    ("quality_dashboard_metric_low_confidence", summary["low_confidence"], "warning"),
                    ("quality_dashboard_metric_unstable", summary["unstable"], "warning"),
                ],
            ),
            (
                "quality_dashboard_metric_group_ap",
                [
                    ("quality_dashboard_metric_ap_diagnostic_points", summary["ap_diagnostic_points"], "warning"),
                    ("quality_dashboard_metric_ap_memory_applied", summary["ap_memory_applied"], "info"),
                    ("quality_dashboard_metric_ap_missing_positions", summary["ap_missing_positions"], "warning"),
                    ("quality_dashboard_metric_ap_metadata_warnings", summary["ap_metadata_warnings"], "warning"),
                    ("quality_dashboard_metric_channel_changes", summary["channel_change_count"], channel_change_severity),
                ],
            ),
        ]

        for title_key, metrics in metric_groups:
            row_count = max(1, (len(metrics) + METRIC_GRID_COLUMNS - 1) // METRIC_GRID_COLUMNS)
            layout.addWidget(self.create_metric_group(title_key, metrics), row_count)

        return panel

    def create_metric_group(self, title_key, metrics):
        palette = QT_THEMES.get(getattr(self.app, "theme", "light"), QT_THEMES["light"])
        group = QFrame()
        group.setObjectName("qualityMetricGroup")
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(widget_px(self, 7))

        heading = QHBoxLayout()
        heading.setContentsMargins(0, 0, 0, 0)
        heading.setSpacing(widget_px(self, 8))
        title = QLabel(self.app.tr(title_key))
        title.setObjectName("qualityMetricGroupTitle")
        title.setStyleSheet(
            f"""
            color: {palette["title"]};
            font-size: {widget_px(self, 17)}px;
            font-weight: 800;
            background: transparent;
            """
        )
        heading.addWidget(title, 0)
        line = QFrame()
        line.setFixedHeight(widget_px(self, 2))
        line.setStyleSheet(
            f"""
            background: {mix_hex(palette["border"], palette["metric_info"], 0.32)};
            border: 0;
            border-radius: {widget_px(self, 1)}px;
            """
        )
        heading.addWidget(line, 1)
        layout.addLayout(heading, 0)

        grid = QGridLayout()
        grid.setHorizontalSpacing(widget_px(self, 10))
        grid.setVerticalSpacing(widget_px(self, 10))
        for column in range(METRIC_GRID_COLUMNS):
            grid.setColumnStretch(column, 1)
        for index, (label_key, value, severity) in enumerate(metrics):
            metric_severity = resolve_metric_severity(label_key, value, severity)
            metric = self.create_metric_box(self.app.tr(label_key), value, metric_severity, label_key)
            row = index // METRIC_GRID_COLUMNS
            column = index % METRIC_GRID_COLUMNS
            grid.addWidget(metric, row, column)
        remainder = len(metrics) % METRIC_GRID_COLUMNS
        if remainder:
            row = len(metrics) // METRIC_GRID_COLUMNS
            for column in range(remainder, METRIC_GRID_COLUMNS):
                grid.addWidget(self.create_metric_placeholder_box(), row, column)
        row_count = max(1, (len(metrics) + METRIC_GRID_COLUMNS - 1) // METRIC_GRID_COLUMNS)
        for row in range(row_count):
            grid.setRowStretch(row, 1)
        layout.addLayout(grid, 1)
        return group

    def create_metric_placeholder_box(self):
        palette = QT_THEMES.get(getattr(self.app, "theme", "light"), QT_THEMES["light"])
        tokens = metric_card_tokens(palette, "info")
        box = DiagonalPlaceholderFrame(
            mix_hex(palette["border"], tokens["accent"], 0.28),
            self,
        )
        box.setObjectName("qualityMetricPlaceholder")
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        box.setStyleSheet(
            f"""
            QFrame#qualityMetricPlaceholder {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {mix_hex(tokens["top"], palette["panel"], 0.55)},
                    stop:1 {mix_hex(tokens["bottom"], palette["panel_alt"], 0.55)}
                );
                border: 1px solid {mix_hex(tokens["border"], palette["panel"], 0.45)};
                border-left: {widget_px(self, 6)}px solid {mix_hex(tokens["accent"], palette["panel"], 0.52)};
                border-radius: {widget_px(self, 9)}px;
            }}
            """
        )
        shadow = QGraphicsDropShadowEffect(box)
        shadow.setBlurRadius(widget_px(self, 12))
        shadow.setOffset(0, widget_px(self, 1))
        shadow.setColor(QColor(0, 0, 0, 18))
        box.setGraphicsEffect(shadow)
        return box

    def create_metric_box(self, label, value, severity, metric_key=None):
        palette = QT_THEMES.get(getattr(self.app, "theme", "light"), QT_THEMES["light"])
        tokens = metric_card_tokens(palette, severity)
        accent = tokens["accent"]
        detail_recommendation = self.metric_detail_recommendation(metric_key, value)
        is_point_clickable = is_point_metric_filter(metric_key, value)
        is_clickable = is_point_clickable or detail_recommendation is not None
        box = QFrame()
        box.setObjectName("qualityMetricBox")
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        box.setStyleSheet(
            f"""
            QFrame#qualityMetricBox {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {tokens["top"]},
                    stop:1 {tokens["bottom"]}
                );
                border: 1px solid {tokens["border"]};
                border-left: {widget_px(self, 6)}px solid {accent};
                border-radius: {widget_px(self, 9)}px;
            }}
            """
        )
        shadow = QGraphicsDropShadowEffect(box)
        shadow.setBlurRadius(widget_px(self, 17))
        shadow.setOffset(0, widget_px(self, 2))
        shadow.setColor(tokens["shadow"])
        box.setGraphicsEffect(shadow)
        if is_clickable:
            box.setCursor(Qt.CursorShape.PointingHandCursor)
            box.setToolTip(
                self.app.tr("quality_dashboard_metric_click_details")
                if detail_recommendation is not None
                else self.app.tr("quality_dashboard_metric_click_points")
            )

            def open_metric(
                event,
                selected_key=metric_key,
                selected_label=label,
                selected_recommendation=detail_recommendation,
            ):
                if event.button() != Qt.MouseButton.LeftButton:
                    return
                if selected_recommendation is not None:
                    self.open_recommendation_details(selected_recommendation)
                else:
                    self.open_metric_points(selected_key, selected_label)
                event.accept()

            box.mouseReleaseEvent = open_metric

        layout = QVBoxLayout(box)
        layout.setContentsMargins(widget_px(self, 13), widget_px(self, 10), widget_px(self, 13), widget_px(self, 10))
        layout.setSpacing(widget_px(self, 6))

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(widget_px(self, 8))
        label_widget = QLabel(label)
        if is_clickable:
            label_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        label_widget.setWordWrap(True)
        label_widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        label_widget.setStyleSheet(
            f"""
            color: {palette["muted"]};
            font-size: {widget_px(self, 14)}px;
            font-weight: 700;
            background: transparent;
            """
        )
        header.addWidget(label_widget, 1)

        indicator = QLabel()
        if is_clickable:
            indicator.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        indicator.setFixedSize(widget_px(self, 10), widget_px(self, 10))
        indicator.setStyleSheet(
            f"""
            background: {accent};
            border-radius: {widget_px(self, 5)}px;
            """
        )
        header.addWidget(indicator, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        layout.addLayout(header, 1)

        value_widget = QLabel(str(value))
        if is_clickable:
            value_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        value_widget.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        value_widget.setStyleSheet(
            f"""
            color: {accent};
            font-size: {widget_px(self, 33)}px;
            font-weight: 900;
            background: transparent;
            """
        )
        if is_clickable:
            footer = QHBoxLayout()
            footer.setContentsMargins(0, 0, 0, 0)
            footer.setSpacing(widget_px(self, 8))
            hint = QLabel(
                self.app.tr("quality_dashboard_metric_extra_details")
                if detail_recommendation is not None
                else self.app.tr("quality_dashboard_metric_view_points")
            )
            hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            hint.setStyleSheet(
                f"""
                color: {palette["muted"]};
                font-size: {widget_px(self, 12)}px;
                font-weight: 700;
                background: transparent;
                """
            )
            footer.addWidget(hint, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
            footer.addStretch(1)
            footer.addWidget(value_widget, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
            layout.addLayout(footer, 0)
        else:
            layout.addWidget(value_widget, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        return box

    def metric_detail_recommendation(self, metric_key, value):
        try:
            if float(value) <= 0:
                return None
        except (TypeError, ValueError):
            if not value:
                return None

        recommendation = self.recommendations_by_metric.get(metric_key)
        if not recommendation or not recommendation.get("detail_items"):
            return None
        return recommendation

    def open_metric_points(self, metric_key, label):
        rows = point_rows_for_metric(self.rows, metric_key)
        dialog = PointRowsDialog(self, label, rows, len(self.rows), metric_key)
        dialog.exec()

    def build_recommendations_panel(self, summary):
        panel = QFrame()
        panel.setObjectName("summaryPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(widget_px(self, 12), widget_px(self, 9), widget_px(self, 12), widget_px(self, 9))
        layout.setSpacing(widget_px(self, 6))

        title = QLabel(self.app.tr("quality_dashboard_fix_next_title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QFrame()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(widget_px(self, 6))

        recommendations = summary.get("recommendations", [])
        for recommendation in recommendations:
            content_layout.addWidget(self.create_recommendation_card(recommendation))

        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        layout.addWidget(self.create_scope_panel(summary), 0)
        return panel

    def create_scope_panel(self, summary):
        palette = QT_THEMES.get(getattr(self.app, "theme", "light"), QT_THEMES["light"])
        accent = palette["metric_info"]
        panel = QFrame()
        panel.setObjectName("qualityScopePanel")
        panel.setStyleSheet(
            f"""
            QFrame#qualityScopePanel {{
                background: {mix_hex(palette["panel_alt"], accent, 0.08)};
                border: 1px solid {mix_hex(palette["border"], accent, 0.24)};
                border-left: {widget_px(self, 4)}px solid {accent};
                border-radius: {widget_px(self, 6)}px;
            }}
            """
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(widget_px(self, 10), widget_px(self, 7), widget_px(self, 10), widget_px(self, 8))
        layout.setSpacing(widget_px(self, 3))

        title = QLabel(self.app.tr("quality_dashboard_scope_title"))
        title.setStyleSheet(f"color: {accent}; font-weight: 800; background: transparent;")
        layout.addWidget(title)

        rows = [
            self.app.tr("quality_dashboard_scope_relevant", networks=summary["relevant_networks"]),
            self.app.tr("quality_dashboard_scope_positions", positions=summary["ap_positions"]),
            self.app.tr("quality_dashboard_scope_test_aps", test_aps=summary["test_aps"]),
        ]
        for row in rows:
            label = QLabel(row)
            label.setObjectName("mutedText")
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(label)

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


class PointRowsDialog(QDialog):
    def __init__(self, owner, label, rows, total_count, metric_key=None):
        super().__init__(owner)
        self.owner = owner
        self.app = owner.app
        self.rows = list(rows)
        self.metric_key = metric_key
        self.visible_rows = point_table_visible_row_count(len(self.rows))
        self.can_expand_table = len(self.rows) > self.visible_rows
        self.setProperty(SKIP_CENTERING_PROPERTY, True)
        self.setWindowTitle(
            self.app.tr(
                "quality_dashboard_points_dialog_title",
                label=label,
                count=len(self.rows),
            )
        )
        self.setMinimumWidth(widget_px(self, 820))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(widget_px(self, 14), widget_px(self, 14), widget_px(self, 14), widget_px(self, 14))
        layout.setSpacing(widget_px(self, 8))

        title = QLabel(label)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        count_label = QLabel(
            self.app.tr(
                "quality_dashboard_visible_count",
                shown=len(self.rows),
                total=total_count,
            )
        )
        count_label.setObjectName("mutedText")
        layout.addWidget(count_label)

        self.table = QTableWidget(0, 4)
        self.table.setObjectName("qualityDashboardTable")
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerItem)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        vertical_header = self.table.verticalHeader()
        vertical_header.setVisible(False)
        vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        vertical_header.setDefaultSectionSize(widget_px(self, POINT_TABLE_ROW_HEIGHT))
        vertical_header.setMinimumSectionSize(widget_px(self, POINT_TABLE_ROW_HEIGHT))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setHorizontalHeaderLabels([
            "#",
            "X",
            "Y",
            self.app.tr("quality_dashboard_issue"),
        ])
        self.table.setItemDelegateForColumn(3, RichTextItemDelegate(self.table))
        configure_point_table_columns(self.table)
        populate_point_table(self.table, self.rows, self, self.metric_key)
        self.table.itemDoubleClicked.connect(lambda _item: self.focus_selected_point())
        layout.addWidget(self.table, 1)
        self.resize(widget_px(self, 1180), self.minimumHeight())
        self.layout().activate()
        self.apply_table_height()

        if self.rows:
            selected_row = next(
                (index for index, row in enumerate(self.rows) if row.get("needs_review")),
                0,
            )
            self.table.selectRow(selected_row)

        button_row = QHBoxLayout()
        self.focus_button = QPushButton(self.app.tr("go_to_point"))
        self.focus_button.setEnabled(bool(self.rows))
        self.focus_button.clicked.connect(self.focus_selected_point)
        button_row.addWidget(self.focus_button)
        button_row.addStretch(1)
        close_button = QPushButton(self.app.tr("close"))
        close_button.clicked.connect(self.accept)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)
        self.apply_initial_size()

    def apply_table_height(self):
        table_height = self.table_height_for_rows(self.visible_rows)
        if self.can_expand_table:
            self.table.setMinimumHeight(table_height)
            self.table.setMaximumHeight(self.table_height_for_rows(len(self.rows)))
            self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            return

        self.table.setFixedHeight(table_height)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def table_height_for_rows(self, visible_rows):
        row_height = widget_px(self, POINT_TABLE_ROW_HEIGHT)
        header_height = self.table.horizontalHeader().sizeHint().height()
        frame_height = self.table.frameWidth() * 2
        rows_height = max(1, visible_rows) * row_height
        return header_height + rows_height + frame_height + widget_px(self, 2)

    def resize_table_rows(self):
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, widget_px(self, POINT_TABLE_ROW_HEIGHT))

    def apply_initial_size(self):
        self.adjustSize()
        width = widget_px(self, 1180)
        max_height = widget_px(self, 760)
        height = min(max_height, self.sizeHint().height())
        self.resize(width, height)
        self.setMinimumHeight(height)
        if not self.can_expand_table:
            self.setMaximumHeight(height)

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
        self.owner.focus_point_action(row)


class RecommendationDetailsDialog(QDialog):
    def __init__(self, owner, recommendation):
        super().__init__(owner)
        self.owner = owner
        self.app = owner.app
        self.recommendation = recommendation
        items = recommendation.get("detail_items", [])
        detail_actions = recommendation.get("detail_actions", [])
        self.setWindowTitle(recommendation.get("title", self.app.tr("quality_dashboard_fix_next_title")))
        row_height = recommendation_detail_row_height(recommendation, items)
        visible_items = recommendation_detail_visible_item_count(recommendation, items)
        self.detail_scroll = None
        self.detail_rows = []
        self.visible_detail_items = visible_items
        self.limit_detail_scroll = len(items) > visible_items
        height = 150 + visible_items * row_height + (44 if detail_actions else 0)
        self.resize(
            widget_px(self, 980),
            min(widget_px(self, recommendation_detail_max_height(recommendation)), widget_px(self, height)),
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
        detail_rows = []
        for item in items:
            detail_row = self.create_detail_row(item)
            detail_rows.append(detail_row)
            content_layout.addWidget(detail_row)
        scroll.setWidget(content)
        self.detail_scroll = scroll
        self.detail_rows = detail_rows
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
        if self.limit_detail_scroll:
            QTimer.singleShot(0, self.apply_detail_scroll_limit)

    def apply_detail_scroll_limit(self):
        if not self.detail_scroll or not self.detail_rows:
            return

        visible_rows = self.detail_rows[:self.visible_detail_items]
        if is_scanner_detail_recommendation(self.recommendation):
            row_heights = [row.height() for row in visible_rows]
            if not row_heights or any(height <= 0 for height in row_heights):
                row_heights = [row.sizeHint().height() for row in visible_rows]
        else:
            row_heights = [row.sizeHint().height() for row in visible_rows]

        scroll_height = recommendation_detail_scroll_max_height(
            row_heights,
            self.detail_scroll.widget().layout().spacing(),
            self.visible_detail_items,
        )
        self.detail_scroll.setMinimumHeight(scroll_height)
        self.detail_scroll.setMaximumHeight(scroll_height)
        self.layout().activate()
        self.resize(
            self.width(),
            min(widget_px(self, recommendation_detail_max_height(self.recommendation)), self.sizeHint().height()),
        )

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
        scanner_details = quality.get("scanner_details", {})
        scanner_detail_issue = format_scanner_detail_issue(app, scanner_details)
        quality_issue = format_quality_issue(app, quality)
        issue = quality_issue
        if scanner_detail_issue:
            issue = join_issues(issue, scanner_detail_issue, app.tr("quality_dashboard_no_issue"))
        if ap_position_issue:
            issue = join_issues(issue, ap_position_issue, app.tr("quality_dashboard_no_issue"))

        has_scanner_detail_issue = bool(scanner_details.get("has_issue"))
        needs_review = status != QUALITY_GOOD or bool(ap_position_issue) or has_scanner_detail_issue
        severity = QUALITY_SEVERITY.get(status, "warning")
        if (ap_position_issue or has_scanner_detail_issue) and status == QUALITY_GOOD:
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
            "ap_position_issue": ap_position_issue,
            "quality_issue": quality_issue,
            "quality_breakdown": quality.get("breakdown", []),
            "scanner_detail_issue": has_scanner_detail_issue,
            "scanner_detail_issue_text": scanner_detail_issue,
            "scanner_details": scanner_details,
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
    if hasattr(app.session, "refresh_ap_groups_from_rows"):
        app.session.refresh_ap_groups_from_rows(update_memory=False)
    saved_groups = app.session.get_ap_groups()
    if saved_groups:
        return merge_new_bssids_into_manual_groups(saved_groups, app.session.rows)

    return build_default_manual_groups(app.session.rows)


def build_summary(app, rows, ap_metadata_warnings=None, ap_groups=None, ap_channel_changes=None):
    ap_metadata_warnings = ap_metadata_warnings or []
    ap_channel_changes = ap_channel_changes or []
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
    memory_applied_groups = [
        group
        for group in visible_ap_groups
        if group.get(AP_MEMORY_APPLIED_KEY)
    ]
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

    scanner_detail_points = sum(1 for row in rows if row.get("scanner_detail_issue"))
    scan_review_points = sum(
        1
        for row in rows
        if (
            row["status"] != QUALITY_GOOD
            or row.get("scanner_detail_issue")
            or row.get("ap_position_warning_count", 0) > 0
        )
    )
    summary = {
        "total_points": len(rows),
        "good_points": sum(1 for row in rows if not row["needs_review"]),
        "review_points": sum(1 for row in rows if row["needs_review"]),
        "scan_review_points": scan_review_points,
        "missing_relevant": count_rows_with_quality_status(rows, QUALITY_MISSING_RELEVANT),
        "low_confidence": count_rows_with_quality_status(rows, QUALITY_LOW_CONFIDENCE),
        "unstable": count_rows_with_quality_status(rows, QUALITY_UNSTABLE_SIGNAL),
        "sparse_data": count_rows_with_quality_status(rows, QUALITY_SPARSE_DATA),
        "scanner_detail_points": scanner_detail_points,
        "scanner_detail_items": build_scanner_detail_items(app, rows),
        "ap_position_warnings": sum(1 for row in rows if row.get("ap_position_warning_count", 0) > 0),
        "ap_missing_positions": len(missing_position_groups),
        "missing_position_labels": missing_position_labels,
        "missing_position_items": build_ap_group_items(app, missing_position_groups),
        "relevant_networks": relevant_networks,
        "ap_positions": f"{positioned_count}/{len(positioned_ap_groups)}" if positioned_ap_groups else "0/0",
        "test_aps": test_ap_count,
        "ap_memory_applied": count_memory_applied_groups(memory_applied_groups),
        "ap_memory_applied_items": build_ap_memory_applied_items(app, memory_applied_groups),
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
        metric_key=None,
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
        if metric_key:
            recommendation["metric_key"] = metric_key
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
        summary["scanner_detail_points"],
        "quality_dashboard_fix_scanner_details_title",
        "quality_dashboard_fix_scanner_details_detail",
        "warning",
        detail_items=summary.get("scanner_detail_items", []),
        detail_count_key="quality_dashboard_detail_measurement_points",
        dialog_detail_key="quality_dashboard_fix_scanner_details_dialog_detail",
        metric_key="quality_dashboard_metric_scanner_details",
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
        summary["ap_memory_applied"],
        "quality_dashboard_fix_ap_memory_title",
        "quality_dashboard_fix_ap_memory_detail",
        "info",
        actions=build_ap_group_actions(app, summary.get("ap_memory_applied_items", []), open_metadata=False),
        detail_items=build_ap_memory_detail_items(app, summary.get("ap_memory_applied_items", [])),
        detail_count_key="quality_dashboard_detail_ap_groups",
        dialog_detail_key="quality_dashboard_fix_ap_memory_dialog_detail",
        metric_key="quality_dashboard_metric_ap_memory_applied",
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
        metric_key="quality_dashboard_metric_ap_metadata_warnings",
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
        metric_key="quality_dashboard_metric_ap_diagnostic_points",
    )
    add(
        summary["ap_missing_positions"],
        "quality_dashboard_fix_ap_missing_title",
        "quality_dashboard_fix_ap_missing_detail",
        "warning",
        actions=build_ap_group_actions(app, summary.get("missing_position_items", []), open_metadata=False),
        detail_items=build_missing_position_detail_items(app, summary.get("missing_position_items", [])),
        detail_count_key="quality_dashboard_detail_ap_groups",
        metric_key="quality_dashboard_metric_ap_missing_positions",
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
        "metric_key": "quality_dashboard_metric_channel_changes",
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


def build_ap_memory_applied_items(app, groups):
    items = []
    for group in groups:
        group_id = str(group.get("group_id", ""))
        if not group_id:
            continue
        matched_bssids = ", ".join(group.get(AP_MEMORY_MATCH_BSSIDS_KEY, [])[:3]) or "-"
        items.append({
            "group_id": group_id,
            "label": app.get_ap_group_display_name(group_id),
            "detail": app.tr(
                "quality_dashboard_ap_memory_item_detail",
                matched_bssids=matched_bssids,
                applied_at=str(group.get(AP_MEMORY_APPLIED_AT_KEY, "") or "-"),
            ),
        })
    return items


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


def build_ap_memory_detail_items(app, items):
    detail_items = []
    for item in items:
        group_id = item.get("group_id", "")
        actions = []
        if group_id:
            actions.append({
                "kind": "ap_group",
                "label": app.tr("quality_dashboard_action_open_ap_group"),
                "group_id": group_id,
            })
        detail_items.append({
            "label": item.get("label", group_id),
            "detail": item.get("detail", ""),
            "actions": actions,
        })
    return detail_items


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


def build_scanner_detail_items(app, rows):
    return [
        {
            "label": app.tr(
                "quality_dashboard_point_detail_label",
                point=row.get("number", "-"),
                x=row.get("x", "-"),
                y=row.get("y", "-"),
            ),
            "finding": format_scanner_detail_finding(app, row.get("scanner_details", {})),
            "detail": format_scanner_detail_detail(app, row.get("scanner_details", {})),
            "actions": [
                {
                    "kind": "point",
                    "row": row,
                    "label": app.tr("quality_dashboard_action_focus_point"),
                },
            ],
        }
        for row in rows
        if row.get("scanner_detail_issue")
    ]


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
        return format_distance_meters(distance_m, getattr(app, "measurement_system", "metric"))

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

    return format_ap_position_point_issue(app, {"ap_position": ap_position})


def format_ap_position_point_issue(app, row):
    ap_position = row.get("ap_position") or {}
    if not ap_position:
        return row.get("ap_position_issue", "")

    warning = format_ap_position_warning_summary(app, ap_position)
    analysis = ap_position.get("analysis") or {}
    dominant_group_id = ap_position.get("dominant_ap_group", "")
    dominant_label = (
        app.get_ap_group_display_name(dominant_group_id)
        if dominant_group_id
        else "-"
    )
    nearest_group_id = analysis.get("nearest_ap_group", "")
    nearest_label = (
        app.get_ap_group_display_name(nearest_group_id)
        if nearest_group_id
        else "-"
    )
    return app.tr(
        "quality_dashboard_ap_position_issue",
        dominant=escape(str(dominant_label)),
        signal=format_dbm(ap_position.get("dominant_signal_dbm")),
        dominant_distance=format_ap_distance(app, analysis, "dominant"),
        closest=escape(str(nearest_label)),
        closest_distance=format_ap_distance(app, analysis, "nearest"),
        warning=escape(str(warning)),
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


def format_scanner_detail_issue(app, scanner_details):
    if not scanner_details or not scanner_details.get("has_issue"):
        return ""

    return app.tr(
        "quality_dashboard_scanner_details_issue",
        detail=format_scanner_detail_summary(app, scanner_details),
    )


def format_scanner_detail_detail(app, scanner_details):
    if not scanner_details or not scanner_details.get("has_issue"):
        return app.tr("quality_dashboard_no_issue")

    parts = format_scanner_detail_detail_parts(app, scanner_details)
    return "<br>".join(parts) if parts else app.tr("quality_dashboard_no_issue")


def format_scanner_detail_finding(app, scanner_details):
    if not scanner_details or not scanner_details.get("has_issue"):
        return ""

    return app.tr("quality_dashboard_scanner_details_finding")


def format_scanner_detail_summary(app, scanner_details):
    parts = format_scanner_detail_summary_parts(app, scanner_details)
    return " | ".join(parts) if parts else app.tr("quality_dashboard_no_issue")


def format_scanner_detail_summary_parts(app, scanner_details):
    issue_types = set(scanner_details.get("issue_types", []))
    parts = []
    if SCANNER_DETAIL_FALLBACK_BACKEND in issue_types:
        backends = format_scanner_backends(scanner_details)
        parts.append(app.tr("quality_dashboard_scanner_details_fallback", backends=backends))
    if SCANNER_DETAIL_MISSING_CHANNEL_WIDTH in issue_types:
        parts.append(app.tr(
            "quality_dashboard_scanner_details_missing_width",
            count=scanner_details.get("missing_channel_width_rows", 0),
        ))
    if SCANNER_DETAIL_MISSING_6GHZ_FREQUENCY in issue_types:
        parts.append(app.tr(
            "quality_dashboard_scanner_details_missing_frequency",
            count=scanner_details.get("missing_6ghz_frequency_rows", 0),
        ))
    return parts


def format_scanner_detail_detail_parts(app, scanner_details):
    issue_types = set(scanner_details.get("issue_types", []))
    fallback_suffix = (
        app.tr("quality_dashboard_scanner_details_fallback_suffix")
        if SCANNER_DETAIL_FALLBACK_BACKEND in issue_types
        else ""
    )
    parts = [
        app.tr(
            "quality_dashboard_scanner_details_scanner",
            backends=format_scanner_backends(scanner_details),
            fallback=fallback_suffix,
            count=scanner_details.get("inspected_rows", 0),
        ),
    ]
    if SCANNER_DETAIL_MISSING_CHANNEL_WIDTH in issue_types:
        parts.append(app.tr(
            "quality_dashboard_scanner_details_missing_width_detail",
            count=scanner_details.get("missing_channel_width_rows", 0),
        ))
    if SCANNER_DETAIL_MISSING_6GHZ_FREQUENCY in issue_types:
        parts.append(app.tr(
            "quality_dashboard_scanner_details_missing_frequency_detail",
            count=scanner_details.get("missing_6ghz_frequency_rows", 0),
        ))
    parts.append(app.tr("quality_dashboard_scanner_details_impact"))
    return parts


def format_scanner_backends(scanner_details):
    return ", ".join(
        format_scanner_backend_label(backend)
        for backend in scanner_details.get("backend_counts", {})
    ) or "-"


def format_scanner_backend_label(backend):
    return escape(str(backend or "-").upper())


def format_quality_issue(app, quality):
    breakdown = quality.get("breakdown", [])
    issues = [
        format_quality_breakdown_issue(app, item)
        for item in breakdown
        if item.get("status") != QUALITY_GOOD
    ]
    if issues:
        return "; ".join(issues)

    status = quality.get("status")
    if status and status != QUALITY_GOOD:
        return format_quality_status_issue(app, status)

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

    return "<br>".join(parts)


def format_band_label(band):
    if str(band) == "2.4":
        return "2.4 GHz"
    if str(band) in {"5", "6"}:
        return f"{band} GHz"
    return str(band)
