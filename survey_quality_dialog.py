import tkinter as tk
from collections import Counter
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import DANGER, PRIMARY, SECONDARY, SUCCESS, WARNING

from ap_groups import AP_ROLE_TEST, normalize_ap_role
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
from survey_store import format_point_id


QUALITY_SEVERITY = {
    QUALITY_GOOD: "good",
    QUALITY_MISSING_RELEVANT: "danger",
    QUALITY_LOW_CONFIDENCE: "warning",
    QUALITY_UNSTABLE_SIGNAL: "warning",
    QUALITY_SPARSE_DATA: "warning",
}


def open_survey_quality_dashboard(app):
    point_summaries = app.session.get_point_summaries()
    if not point_summaries:
        messagebox.showwarning(app.tr("warning"), app.tr("empty_csv"), parent=app.root)
        return

    quality_by_point_id = evaluate_point_quality(
        app.session.rows,
        app.session.raw_scan_rows,
        relevant_ssids=app.relevant_ssids
    )
    ap_position_by_point = build_ap_position_quality_by_point(app)
    rows = build_dashboard_rows(app, point_summaries, quality_by_point_id, ap_position_by_point)
    summary = build_summary(app, rows)

    dialog = app.create_modal_dialog(app.tr("quality_dashboard_title"))
    dialog.geometry("1320x760")
    dialog.minsize(1120, 680)
    dialog.resizable(True, True)

    frame = ttk.Frame(dialog, padding=12)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(
        frame,
        text=app.tr("quality_dashboard_hint"),
        wraplength=1240,
        style="ReadableMuted.TLabel"
    ).pack(anchor="w", pady=(0, 10))

    build_summary_panel(app, frame, summary)
    build_details_panel(app, frame, rows)

    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    app.center_dialog(dialog)


def build_summary_panel(app, parent, summary):
    panel = ttk.Frame(parent)
    panel.pack(fill=tk.X, pady=(0, 10))

    metrics = [
        ("quality_dashboard_metric_points", summary["total_points"], PRIMARY),
        ("quality_dashboard_metric_ok", summary["good_points"], SUCCESS),
        ("quality_dashboard_metric_review", summary["review_points"], WARNING if summary["review_points"] else SUCCESS),
        ("quality_dashboard_metric_missing", summary["missing_relevant"], DANGER if summary["missing_relevant"] else SUCCESS),
        ("quality_dashboard_metric_low_confidence", summary["low_confidence"], WARNING if summary["low_confidence"] else SUCCESS),
        ("quality_dashboard_metric_unstable", summary["unstable"], WARNING if summary["unstable"] else SUCCESS),
        (
            "quality_dashboard_metric_ap_position_warnings",
            summary["ap_position_warnings"],
            WARNING if summary["ap_position_warnings"] else SUCCESS
        ),
        (
            "quality_dashboard_metric_ap_missing_positions",
            summary["ap_missing_positions"],
            WARNING if summary["ap_missing_positions"] else SUCCESS
        ),
    ]

    for column, (label_key, value, bootstyle) in enumerate(metrics):
        create_metric_box(panel, app.tr(label_key), value, bootstyle).grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(0, 8 if column < len(metrics) - 1 else 0)
        )
        panel.grid_columnconfigure(column, weight=1)

    details = ttk.Frame(parent)
    details.pack(fill=tk.X, pady=(0, 10))
    ttk.Label(
        details,
        text=app.tr(
            "quality_dashboard_context",
            relevant=summary["relevant_networks"],
            ap_positions=summary["ap_positions"],
            test_aps=summary["test_aps"]
        ),
        style="ReadableMuted.TLabel"
    ).pack(anchor="w")
    ttk.Label(
        details,
        text=app.tr(
            "quality_dashboard_ap_context",
            ap_warnings=summary["ap_position_warnings"],
            missing_positions=summary["ap_missing_positions"],
            missing_list=summary["missing_position_labels"]
        ),
        style="ReadableMuted.TLabel",
        wraplength=1240
    ).pack(anchor="w", pady=(2, 0))


def create_metric_box(parent, label, value, bootstyle):
    box = ttk.Frame(parent, padding=10, borderwidth=1, relief=tk.SOLID)
    ttk.Label(box, text=label, style="ReadableMuted.TLabel").pack(anchor="w")
    ttk.Label(box, text=str(value), font=("Segoe UI", 18, "bold"), bootstyle=bootstyle).pack(anchor="w", pady=(2, 0))
    return box


def build_details_panel(app, parent, rows):
    show_issues_only = tk.BooleanVar(value=False)
    row_by_item = {}

    controls = ttk.Frame(parent)
    controls.pack(fill=tk.X, pady=(0, 8))

    visible_count_var = tk.StringVar(value="")
    filter_check = ttk.Checkbutton(
        controls,
        text=app.tr("quality_dashboard_show_issues_only"),
        variable=show_issues_only,
        bootstyle=SECONDARY
    )
    filter_check.pack(side=tk.LEFT)
    ttk.Label(controls, textvariable=visible_count_var, style="ReadableMuted.TLabel").pack(side=tk.LEFT, padx=(12, 0))

    table_frame = ttk.Frame(parent)
    table_frame.pack(fill=tk.BOTH, expand=True)

    columns = ("number", "x", "y", "quality", "confidence", "best", "rows", "ssids", "issue")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)
    headings = {
        "number": "#",
        "x": "X",
        "y": "Y",
        "quality": app.tr("quality"),
        "confidence": app.tr("confidence"),
        "best": app.tr("best_dbm"),
        "rows": app.tr("rows"),
        "ssids": "SSID",
        "issue": app.tr("quality_dashboard_issue"),
    }
    widths = {
        "number": 52,
        "x": 68,
        "y": 68,
        "quality": 120,
        "confidence": 92,
        "best": 104,
        "rows": 70,
        "ssids": 270,
        "issue": 440,
    }
    anchors = {
        "number": "center",
        "x": "center",
        "y": "center",
        "quality": "center",
        "confidence": "center",
        "best": "center",
        "rows": "center",
        "ssids": "w",
        "issue": "w",
    }
    for column in columns:
        tree.heading(column, text=headings[column])
        tree.column(column, width=widths[column], minwidth=max(44, widths[column] - 30), anchor=anchors[column])

    configure_quality_tags(app, tree)

    y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=y_scroll.set)
    tree.grid(row=0, column=0, sticky="nsew")
    y_scroll.grid(row=0, column=1, sticky="ns")
    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(0, weight=1)

    buttons = ttk.Frame(parent)
    buttons.pack(fill=tk.X, pady=(10, 0))
    focus_button = ttk.Button(
        buttons,
        text=app.tr("go_to_point"),
        bootstyle=PRIMARY,
        command=lambda: focus_selected_dashboard_point(app, tree, row_by_item)
    )
    focus_button.pack(side=tk.LEFT)

    def render_rows():
        tree.delete(*tree.get_children())
        row_by_item.clear()
        visible_rows = [
            row
            for row in rows
            if not show_issues_only.get() or row["needs_review"]
        ]
        for row in visible_rows:
            item_id = row["item_id"]
            row_by_item[item_id] = row
            tree.insert(
                "",
                tk.END,
                iid=item_id,
                values=(
                    row["number"],
                    row["x"],
                    row["y"],
                    row["quality"],
                    row["confidence"],
                    row["best"],
                    row["row_count"],
                    row["ssids"],
                    row["issue"],
                ),
                tags=(row["severity"],)
            )
        visible_count_var.set(app.tr("quality_dashboard_visible_count", shown=len(visible_rows), total=len(rows)))
        focus_button.configure(state=tk.NORMAL if visible_rows else tk.DISABLED)

    filter_check.configure(command=render_rows)
    tree.bind("<Double-1>", lambda _event: focus_selected_dashboard_point(app, tree, row_by_item))
    render_rows()


def configure_quality_tags(app, tree):
    if getattr(app, "is_dark_theme", False):
        tree.tag_configure("good", background="#183828", foreground="#e8f5ee")
        tree.tag_configure("warning", background="#3c331d", foreground="#fff3cd")
        tree.tag_configure("danger", background="#452222", foreground="#fde2e2")
    else:
        tree.tag_configure("good", background="#e9f7ef", foreground="#1f2d24")
        tree.tag_configure("warning", background="#fff3cd", foreground="#2f2a18")
        tree.tag_configure("danger", background="#fdecea", foreground="#3a1f1f")


def focus_selected_dashboard_point(app, tree, row_by_item):
    selection = tree.selection()
    if not selection:
        messagebox.showwarning(app.tr("warning"), app.tr("select_point"), parent=tree.winfo_toplevel())
        return

    row = row_by_item.get(selection[0])
    if not row:
        return

    dialog = tree.winfo_toplevel()
    dialog.destroy()

    def focus_point():
        if hasattr(app, "main_notebook"):
            app.main_notebook.select(0)
        app.focus_point(row["x"], row["y"])
        app.highlight_point(row["timestamp"], row["x"], row["y"])
        point_item_id = row["point_table_item_id"]
        if hasattr(app, "points_table") and app.points_table.exists(point_item_id):
            app.points_table.selection_set(point_item_id)
            app.points_table.focus(point_item_id)
            app.points_table.see(point_item_id)

    app.root.after(80, focus_point)


def build_dashboard_rows(app, point_summaries, quality_by_point_id, ap_position_by_point=None):
    total_points = len(point_summaries)
    rows = []
    ap_position_by_point = ap_position_by_point or {}

    for index, point in enumerate(reversed(point_summaries), start=1):
        survey_number = total_points - index + 1
        quality = quality_by_point_id.get(point.get("point_id", ""), {})
        status = quality.get("status", QUALITY_SPARSE_DATA)
        point_table_item_id = format_point_id(point["timestamp"], point["x"], point["y"])
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
            "item_id": f"{point.get('point_id') or survey_number}|{point_table_item_id}",
            "point_table_item_id": point_table_item_id,
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


def build_summary(app, rows):
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
    relevant_networks = ", ".join(sorted(app.relevant_ssids)) if app.relevant_ssids else app.tr("relevant_networks_none")
    missing_position_labels = ", ".join(
        app.get_ap_group_display_name(group.get("group_id", ""))
        for group in missing_position_groups[:4]
    )
    if len(missing_position_groups) > 4:
        missing_position_labels = app.tr(
            "quality_dashboard_missing_positions_more",
            names=missing_position_labels,
            count=len(missing_position_groups) - 4
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
    }


def build_ap_position_quality_by_point(app):
    if not app.session.get_ap_groups():
        return {}

    role_map = app.get_current_ap_group_roles()
    relevant_ssids = {normalize_ssid(ssid) for ssid in app.relevant_ssids or [] if normalize_ssid(ssid)}
    best_by_point = {}

    for row in app.session.rows:
        if not row_is_relevant_for_position(row, relevant_ssids):
            continue

        bssid = row.get("bssid", "")
        group_id = app.resolve_ap_group_key(bssid)
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
        analysis = app.analyze_dominant_ap_position_for_row(dominant_row)
        warnings = analysis.get("warnings", [])
        if not warnings:
            continue

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

    return format_point_id(row.get("timestamp", ""), row.get("x", ""), row.get("y", ""))


def point_key(point):
    if point.get("point_id"):
        return point.get("point_id")

    return format_point_id(point.get("timestamp", ""), point.get("x", ""), point.get("y", ""))


def format_ap_position_issue(app, ap_position):
    if not ap_position:
        return ""

    warning_labels = [
        app.tr(app.ap_position_warning_translation_key(warning))
        for warning in ap_position.get("warnings", [])
    ]
    if not warning_labels:
        return ""

    ap_label = app.get_ap_group_display_name(ap_position.get("dominant_ap_group", ""))
    return app.tr(
        "quality_dashboard_ap_position_issue",
        ap=ap_label,
        warning="; ".join(warning_labels)
    )


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
    relevant_ssids = {normalize_ssid(ssid) for ssid in relevant_ssids or [] if normalize_ssid(ssid)}

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
