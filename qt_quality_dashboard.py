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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ap_groups import (
    AP_ROLE_TEST,
    build_bssid_to_manual_group_map,
    normalize_ap_role,
    resolve_ap_group_key,
)
from ap_metadata_checks import build_ap_metadata_warnings
from ap_positioning import (
    AP_POSITION_NO_SCALE,
    AP_POSITION_STRONG_FAR,
    AP_POSITION_UNEXPECTED_DOMINANT,
    AP_POSITION_WEAK_CLOSE,
    analyze_dominant_ap_position,
)
from quality_engine import (
    QUALITY_GOOD,
    QUALITY_LOW_CONFIDENCE,
    QUALITY_MISSING_RELEVANT,
    QUALITY_SPARSE_DATA,
    QUALITY_UNSTABLE_SIGNAL,
    evaluate_point_quality,
    is_truthy,
    normalize_ssid,
    parse_float,
)


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
        self.setWindowTitle(app.tr("quality_dashboard_title"))
        self.resize(1420, 800)
        self.setMinimumSize(1180, 700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        hint = QLabel(app.tr("quality_dashboard_hint"))
        hint.setObjectName("mutedText")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addWidget(self.build_summary_panel(summary))
        layout.addWidget(self.build_context_panel(summary))
        layout.addLayout(self.build_controls())

        self.table = QTableWidget(0, 9)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setHorizontalHeaderLabels([
            "#",
            "X",
            "Y",
            app.tr("quality"),
            app.tr("confidence"),
            app.tr("best_dbm"),
            app.tr("rows"),
            "SSID",
            app.tr("quality_dashboard_issue"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemDoubleClicked.connect(lambda _item: self.focus_selected_point())
        layout.addWidget(self.table, 1)

        button_row = QHBoxLayout()
        self.focus_button = QPushButton(app.tr("go_to_point"))
        self.focus_button.clicked.connect(self.focus_selected_point)
        button_row.addWidget(self.focus_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.issues_only_check.toggled.connect(self.render_rows)
        self.render_rows()

    def build_summary_panel(self, summary):
        panel = QFrame()
        panel.setObjectName("summaryPanel")
        grid = QGridLayout(panel)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        metrics = [
            ("quality_dashboard_metric_points", summary["total_points"], "info"),
            ("quality_dashboard_metric_ok", summary["good_points"], "good"),
            ("quality_dashboard_metric_review", summary["review_points"], "warning"),
            ("quality_dashboard_metric_missing", summary["missing_relevant"], "danger"),
            ("quality_dashboard_metric_low_confidence", summary["low_confidence"], "warning"),
            ("quality_dashboard_metric_unstable", summary["unstable"], "warning"),
            ("quality_dashboard_metric_ap_position_warnings", summary["ap_position_warnings"], "warning"),
            ("quality_dashboard_metric_ap_missing_positions", summary["ap_missing_positions"], "warning"),
            ("quality_dashboard_metric_ap_metadata_warnings", summary["ap_metadata_warnings"], "warning"),
        ]

        for index, (label_key, value, severity) in enumerate(metrics):
            metric = self.create_metric_box(self.app.tr(label_key), value, severity if value else "good")
            grid.addWidget(metric, index // 5, index % 5)
            grid.setColumnStretch(index % 5, 1)

        return panel

    def create_metric_box(self, label, value, severity):
        box = QFrame()
        box.setObjectName("metricBox")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 8, 10, 8)
        label_widget = QLabel(label)
        label_widget.setObjectName("mutedText")
        value_widget = QLabel(str(value))
        value_widget.setObjectName(f"metricValue_{severity}")
        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        return box

    def build_context_panel(self, summary):
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        lines = [
            self.app.tr(
                "quality_dashboard_context",
                relevant=summary["relevant_networks"],
                ap_positions=summary["ap_positions"],
                test_aps=summary["test_aps"],
            ),
            self.app.tr(
                "quality_dashboard_ap_context",
                ap_warnings=summary["ap_position_warnings"],
                missing_positions=summary["ap_missing_positions"],
                missing_list=summary["missing_position_labels"],
            ),
            self.app.tr(
                "quality_dashboard_ap_metadata_context",
                warnings=summary["ap_metadata_warnings"],
                warning_list=summary["ap_metadata_warning_labels"],
            ),
        ]
        for line in lines:
            label = QLabel(line)
            label.setObjectName("mutedText")
            label.setWordWrap(True)
            layout.addWidget(label)
        return panel

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
                self.table.setItem(row_index, column_index, item)

        self.visible_count_label.setText(
            self.app.tr(
                "quality_dashboard_visible_count",
                shown=len(self.filtered_rows),
                total=len(self.rows),
            )
        )
        self.focus_button.setEnabled(bool(self.filtered_rows))

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
        self.app.select_point_in_table(row)


def open_qt_quality_dashboard(app):
    point_summaries = app.session.get_point_summaries() if app.session else []
    if not point_summaries:
        QMessageBox.warning(app, app.tr("warning"), app.tr("empty_csv"))
        return

    quality_by_point_id = evaluate_point_quality(
        app.session.rows,
        app.session.raw_scan_rows,
        relevant_ssids=app.relevant_ssids,
    )
    ap_position_by_point = build_ap_position_quality_by_point(app)
    ap_metadata_warnings = build_ap_metadata_warnings(
        app.session.rows,
        app.session.get_ap_groups(),
        app.channel_sort_key,
    )
    rows = build_dashboard_rows(app, point_summaries, quality_by_point_id, ap_position_by_point)
    summary = build_summary(app, rows, ap_metadata_warnings)
    QualityDashboardDialog(app, rows, summary).exec()


def build_dashboard_rows(app, point_summaries, quality_by_point_id, ap_position_by_point=None):
    total_points = len(point_summaries)
    rows = []
    ap_position_by_point = ap_position_by_point or {}

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
            "confidence": format_point_confidence(app.session.rows, point.get("point_id", ""), app.relevant_ssids),
            "best": f"{point['best_signal_dbm']:.1f}",
            "row_count": point["row_count"],
            "ssids": ", ".join(point["ssids"]),
            "issue": issue,
        })

    return rows


def build_summary(app, rows, ap_metadata_warnings=None):
    ap_metadata_warnings = ap_metadata_warnings or []
    status_counts = Counter(row["status"] for row in rows)
    ap_groups = app.session.get_ap_groups()
    visible_ap_groups = [
        group
        for group in ap_groups
        if normalize_ap_role(group.get("role")) != AP_ROLE_TEST
    ]
    test_ap_count = len(ap_groups) - len(visible_ap_groups)
    positioned_count = sum(1 for group in visible_ap_groups if group.get("position"))
    missing_position_groups = [group for group in visible_ap_groups if not group.get("position")]
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

    return {
        "total_points": len(rows),
        "good_points": sum(1 for row in rows if not row["needs_review"]),
        "review_points": sum(1 for row in rows if row["needs_review"]),
        "missing_relevant": status_counts.get(QUALITY_MISSING_RELEVANT, 0),
        "low_confidence": status_counts.get(QUALITY_LOW_CONFIDENCE, 0),
        "unstable": status_counts.get(QUALITY_UNSTABLE_SIGNAL, 0),
        "ap_position_warnings": sum(1 for row in rows if row.get("ap_position_warning_count", 0) > 0),
        "ap_missing_positions": len(missing_position_groups),
        "missing_position_labels": missing_position_labels,
        "relevant_networks": relevant_networks,
        "ap_positions": f"{positioned_count}/{len(visible_ap_groups)}" if visible_ap_groups else "0/0",
        "test_aps": test_ap_count,
        "ap_metadata_warnings": len(ap_metadata_warnings),
        "ap_metadata_warning_labels": format_ap_metadata_warning_labels(app, ap_metadata_warnings),
    }


def build_ap_position_quality_by_point(app):
    ap_groups = app.session.get_ap_groups()
    if not ap_groups:
        return {}

    group_map = build_bssid_to_manual_group_map(ap_groups)
    role_map = app.get_current_ap_group_roles()
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
            app.session.get_ap_groups(),
            app.get_px_per_meter(),
        )
        warnings = analysis.get("warnings", [])
        if warnings:
            result[key] = {
                "analysis": analysis,
                "dominant_ap_group": dominant_row.get("dominant_ap_group", ""),
                "dominant_bssid": dominant_row.get("dominant_bssid", ""),
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

    for row in rows:
        if row.get("point_id") != point_id:
            continue
        if relevant_ssids:
            if normalize_ssid(row.get("ssid")) not in relevant_ssids and not is_truthy(row.get("is_relevant")):
                continue
        confidence = parse_float(row.get("scan_confidence"))
        if confidence is not None:
            values.append(confidence)

    if not values:
        return "-"

    return f"{min(values):.2f}"


def format_ap_metadata_warning_labels(app, warnings):
    if not warnings:
        return app.tr("quality_dashboard_missing_positions_none")

    labels = [format_ap_metadata_warning(app, warning) for warning in warnings[:3]]
    if len(warnings) > 3:
        labels.append(app.tr("quality_dashboard_more_issues", count=len(warnings) - 3))

    return "; ".join(labels)


def format_ap_metadata_warning(app, warning):
    ap_label = app.get_ap_group_display_name(warning.get("group_id", ""))
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

    return f"{ap_label}: {', '.join(parts)}" if parts else ap_label


def format_band_label(band):
    if str(band) == "2.4":
        return "2.4 GHz"
    if str(band) in {"5", "6"}:
        return f"{band} GHz"
    return str(band)
