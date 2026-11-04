"""PDF report pages and summaries for live-map exports."""

from textwrap import wrap

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ap.groups import build_dominant_ap_group_labels, format_ap_label, normalize_ap_role, resolve_ap_alias
from ap.positioning import (
    AP_POSITION_STRONG_FAR,
    AP_POSITION_UNEXPECTED_DOMINANT,
    AP_POSITION_WEAK_CLOSE,
    analyze_dominant_ap_position,
)
from app_core.units import format_distance_meters
from maps.heatmap import format_band_label, get_interference_data_quality


INTERFERENCE_PROBLEM_RISK_THRESHOLD = 30
INTERFERENCE_PROBLEM_REPORT_LIMIT = 12
INTERFERENCE_PROBLEM_ROWS_PER_PAGE = 4
DOMINANT_PROBLEM_REPORT_LIMIT = 14
PROBLEM_REPORT_ROWS_PER_PAGE = 4


def get_interference_problem_df(risk_df):
    if risk_df.empty or "risk" not in risk_df.columns:
        return risk_df.head(0).copy()

    problem_df = (
        risk_df[(risk_df["risk"] >= INTERFERENCE_PROBLEM_RISK_THRESHOLD) | risk_df["risk"].isna()]
        .sort_values("risk", ascending=False)
        .head(INTERFERENCE_PROBLEM_REPORT_LIMIT)
        .copy()
    )
    problem_df["report_number"] = range(1, len(problem_df) + 1)
    return problem_df


def annotate_interference_problem_numbers(ax, problem_df):
    annotate_problem_numbers(ax, problem_df)


def annotate_dominant_problem_numbers(ax, problem_df):
    annotate_problem_numbers(ax, problem_df)


def annotate_problem_numbers(ax, problem_df):
    for _index, row in problem_df.iterrows():
        try:
            x = float(row.get("x"))
            y = float(row.get("y"))
        except (TypeError, ValueError):
            continue

        ax.annotate(
            str(int(row.get("report_number", 0) or 0)),
            xy=(x, y),
            xytext=(11, -11),
            textcoords="offset points",
            ha="center",
            va="center",
            fontsize=8.4,
            fontweight="bold",
            color="#ffffff",
            bbox={
                "boxstyle": "square,pad=0.22",
                "facecolor": "#111827",
                "edgecolor": "#ffffff",
                "linewidth": 0.8,
            },
            zorder=8,
            clip_on=False,
        )


def build_interference_problem_report_pages(risk_df, config, tr, language, aliases):
    problem_df = get_interference_problem_df(risk_df)
    title = tr("live_pdf_problem_report_title")
    subtitle = f"{tr('export_interference_title')} - {config.ssid} - {format_band_label(config.band, language)}"
    if problem_df.empty:
        return [build_interference_problem_report_page(
            title,
            subtitle,
            [],
            tr("live_pdf_no_interference_issues"),
            tr,
            aliases,
        )]

    pages = []
    page_count = int(np.ceil(len(problem_df) / INTERFERENCE_PROBLEM_ROWS_PER_PAGE))
    for page_index in range(page_count):
        start = page_index * INTERFERENCE_PROBLEM_ROWS_PER_PAGE
        stop = start + INTERFERENCE_PROBLEM_ROWS_PER_PAGE
        pages.append(build_interference_problem_report_page(
            title,
            subtitle,
            list(problem_df.iloc[start:stop].to_dict("records")),
            tr("live_pdf_no_interference_issues"),
            tr,
            aliases,
            page_number=page_index + 1,
            page_count=page_count,
            layout_rows=INTERFERENCE_PROBLEM_ROWS_PER_PAGE,
        ))
    return pages


def build_interference_problem_report_page(
    title,
    subtitle,
    rows,
    empty_message,
    tr,
    aliases,
    page_number=None,
    page_count=None,
    layout_rows=INTERFERENCE_PROBLEM_ROWS_PER_PAGE,
):
    fig = plt.figure(figsize=(11.69, 8.27), dpi=100)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.05, 0.94, title, fontsize=17, fontweight="bold", va="top", color="#111827")
    ax.text(0.05, 0.895, subtitle, fontsize=10.5, va="top", color="#4b5563")
    if page_count and page_count > 1:
        ax.text(0.95, 0.94, f"{page_number}/{page_count}", fontsize=10, ha="right", va="top", color="#6b7280")
    ax.plot([0.05, 0.95], [0.855, 0.855], color="#2f6fed", linewidth=1.1, alpha=0.75)

    if not rows:
        ax.text(0.05, 0.79, empty_message, fontsize=11, va="top", color="#374151")
        return fig

    card_left = 0.05
    card_width = 0.90
    content_top = 0.82
    content_bottom = 0.07
    gap = 0.018
    card_height = calculate_report_card_height(len(rows), content_top, content_bottom, gap, layout_rows)

    for row_index, row in enumerate(rows):
        card_top = content_top - row_index * (card_height + gap)
        card_bottom = card_top - card_height
        risk = float(row.get("risk", 0) or 0)
        risk_color = "#d73027" if risk >= 60 else "#f59e0b"

        ax.add_patch(plt.Rectangle(
            (card_left, card_bottom),
            card_width,
            card_height,
            facecolor="#fbfcfd",
            edgecolor="#d1d5db",
            linewidth=0.8,
        ))
        ax.add_patch(plt.Rectangle(
            (card_left, card_bottom),
            0.006,
            card_height,
            facecolor=risk_color,
            edgecolor=risk_color,
            linewidth=0,
        ))

        badge_size = 0.044
        badge_x = card_left + 0.022
        badge_y = card_top - 0.065
        ax.add_patch(plt.Rectangle(
            (badge_x, badge_y),
            badge_size,
            badge_size,
            facecolor="#111827",
            edgecolor="#ffffff",
            linewidth=0.9,
        ))
        ax.text(
            badge_x + badge_size / 2,
            badge_y + badge_size / 2,
            str(int(row.get("report_number", row_index + 1) or row_index + 1)),
            fontsize=10.2,
            fontweight="bold",
            ha="center",
            va="center",
            color="#ffffff",
        )

        point_x = card_left + 0.083
        ax.text(
            point_x,
            badge_y + badge_size / 2,
            f"({format_report_value(row.get('x'))}, {format_report_value(row.get('y'))})",
            fontsize=9.2,
            va="center",
            color="#6b7280",
        )

        risk_x = card_left + card_width - 0.19
        ax.add_patch(plt.Rectangle(
            (risk_x, card_top - 0.061),
            0.145,
            0.038,
            facecolor="#fff7ed" if risk < 60 else "#fef2f2",
            edgecolor=risk_color,
            linewidth=0.8,
        ))
        ax.text(
            risk_x + 0.0725,
            card_top - 0.042,
            f"{tr('reference_risk')}: {risk:.1f}%" if np.isfinite(risk) else f"{tr('reference_risk')}: —",
            fontsize=8.6,
            fontweight="bold",
            ha="center",
            va="center",
            color="#111827",
        )

        value_top = card_top - 0.088
        draw_interference_report_ap_block(
            ax,
            card_left + 0.040,
            value_top,
            tr("interference_summary_serving_ap"),
            format_interference_ap_label(row, "serving", aliases),
            format_report_channel_with_width(
                row.get("serving_channel"),
                row.get("serving_channel_width_mhz"),
            ),
        )
        draw_interference_report_ap_block(
            ax,
            card_left + 0.485,
            value_top,
            tr("interference_summary_interferer"),
            format_interference_ap_label(row, "strongest_interferer", aliases),
            format_report_channel_with_width(
                row.get("strongest_interferer_channel"),
                row.get("strongest_interferer_channel_width_mhz"),
            ),
        )
    return fig


def draw_interference_report_ap_block(ax, x, y, label, value, channel_value):
    ax.text(x, y, clean_report_text(label), fontsize=6.9, va="top", color="#6b7280")
    value_lines = wrap_report_text(value, width=58, max_lines=2)
    for line_index, line in enumerate(value_lines):
        ax.text(
            x,
            y - 0.020 - line_index * 0.020,
            line,
            fontsize=8.3,
            va="top",
            color="#111827",
        )
    channel_y = y - 0.023 - len(value_lines) * 0.020
    ax.text(
        x,
        channel_y,
        clean_report_text(channel_value),
        fontsize=8.0,
        va="top",
        color="#374151",
    )


def format_interference_ap_label(row, prefix, aliases):
    bssid_key = "serving_bssid" if prefix == "serving" else f"{prefix}_bssid"
    group_key = "serving_ap_group" if prefix == "serving" else f"{prefix}_ap_group"
    bssid = row.get(bssid_key, "")
    if clean_report_text(bssid) == "-":
        return "-"
    alias = resolve_ap_alias(bssid, aliases, row.get(group_key, ""))
    return f"{alias} ({bssid})" if alias else str(bssid)


def format_report_channel_with_width(channel, width):
    channel_label = format_report_value(channel)
    width_label = format_report_value(width)
    if width_label == "-":
        return f"CH {channel_label}"
    return f"CH {channel_label} / {width_label} MHz"


def build_dominant_problem_report_pages(dominant_df, config, tr, language, aliases, measurement_system="metric"):
    problem_df = get_dominant_problem_df(dominant_df)
    group_labels = build_dominant_ap_group_labels(dominant_df, aliases)
    rows = []
    for _index, row in problem_df.iterrows():
        warnings = [
            warning
            for warning in str(row.get("ap_position_warnings", "")).split(";")
            if warning
        ]
        detail_items = build_dominant_problem_detail_items(row, warnings, tr, aliases, measurement_system)
        if not detail_items:
            continue

        group = row.get("dominant_ap_group", "")
        rows.append([
            f"{format_report_value(row.get('x'))}, {format_report_value(row.get('y'))}",
            group_labels.get(group, format_ap_label(row.get("dominant_bssid", ""), aliases, group)),
            format_report_value(row.get("delta_db"), suffix=" dB"),
            detail_items,
        ])

    limited_rows = rows[:DOMINANT_PROBLEM_REPORT_LIMIT]
    rows_per_page = get_dominant_problem_rows_per_page(limited_rows)
    return build_problem_report_pages(
        tr("live_pdf_problem_report_title"),
        f"{tr('export_dominant_title')} - {config.ssid} - {format_band_label(config.band, language)}",
        [tr("interference_summary_point"), tr("dominant_map_legend_title"), tr("reference_delta"),
         tr("live_pdf_issue")],
        limited_rows,
        tr("live_pdf_no_dominant_issues"),
        rows_per_page=rows_per_page,
    )


def get_dominant_problem_rows_per_page(rows):
    has_combined_issue = any(
        is_problem_detail_items(row[-1]) and len(row[-1]) >= 3
        for row in rows
        if row
    )
    return 2 if has_combined_issue else 3


def get_dominant_problem_df(dominant_df):
    if dominant_df.empty:
        return dominant_df.head(0).copy()

    mask = (
        dominant_df.get("roaming_overlap", pd.Series(False, index=dominant_df.index))
        .fillna(False)
        .astype(bool)
    )
    if "ap_position_warnings" in dominant_df:
        mask = mask | dominant_df["ap_position_warnings"].fillna("").astype(str).str.len().gt(0)

    problem_df = dominant_df[mask].head(DOMINANT_PROBLEM_REPORT_LIMIT).copy()
    problem_df["report_number"] = range(1, len(problem_df) + 1)
    return problem_df


def build_problem_report_pages(title, subtitle, headers, rows, empty_message, rows_per_page=4):
    if not rows:
        return [build_problem_report_page(title, subtitle, headers, [], empty_message)]

    pages = []
    page_count = int(np.ceil(len(rows) / rows_per_page))
    for page_index in range(page_count):
        start = page_index * rows_per_page
        stop = start + rows_per_page
        pages.append(build_problem_report_page(
            title,
            subtitle,
            headers,
            rows[start:stop],
            empty_message,
            page_number=page_index + 1,
            page_count=page_count,
            first_item_number=start + 1,
            layout_rows=rows_per_page,
        ))
    return pages


def clean_report_text(value):
    if value is None:
        return "-"
    text = str(value).strip()
    return text or "-"


def wrap_report_text(value, width, max_lines):
    lines = []
    for paragraph in clean_report_text(value).splitlines():
        lines.extend(wrap(
            paragraph.strip() or "-",
            width=width,
            break_long_words=False,
            replace_whitespace=True,
        ) or ["-"])
    if len(lines) <= max_lines:
        return lines

    lines = lines[:max_lines]
    lines[-1] = f"{lines[-1].rstrip('.')}..."
    return lines


def is_problem_detail_items(value):
    return (
        isinstance(value, list)
        and all(isinstance(item, dict) for item in value)
    )


def draw_problem_report_detail(ax, x, y, value, max_lines):
    if not is_problem_detail_items(value):
        for line_index, line in enumerate(wrap_report_text(value, width=66, max_lines=max_lines)):
            ax.text(
                x,
                y - 0.023 - line_index * 0.023,
                line,
                fontsize=8.5,
                va="top",
                color="#111827",
            )
        return

    cursor_y = y - 0.022
    remaining_lines = max_lines
    for item in value:
        if remaining_lines <= 0:
            break

        label = clean_report_text(item.get("label"))
        detail = clean_report_text(item.get("value"))
        if label != "-":
            ax.text(
                x,
                cursor_y,
                label,
                fontsize=7.6,
                fontweight="bold",
                va="top",
                color="#374151",
            )
            cursor_y -= 0.018
            remaining_lines -= 1

        if remaining_lines <= 0:
            break

        for line in wrap_report_text(detail, width=76, max_lines=min(remaining_lines, 5)):
            ax.text(
                x,
                cursor_y,
                line,
                fontsize=8.3,
                va="top",
                color="#111827",
            )
            cursor_y -= 0.020
            remaining_lines -= 1
            if remaining_lines <= 0:
                break

        cursor_y -= 0.004


def build_problem_report_page(
    title,
    subtitle,
    headers,
    rows,
    empty_message,
    page_number=None,
    page_count=None,
    first_item_number=1,
    layout_rows=PROBLEM_REPORT_ROWS_PER_PAGE,
):
    fig = plt.figure(figsize=(11.69, 8.27), dpi=100)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.05, 0.94, title, fontsize=17, fontweight="bold", va="top", color="#111827")
    ax.text(0.05, 0.895, subtitle, fontsize=10.5, va="top", color="#4b5563")
    if page_count and page_count > 1:
        ax.text(0.95, 0.94, f"{page_number}/{page_count}", fontsize=10, ha="right", va="top", color="#6b7280")
    ax.plot([0.05, 0.95], [0.855, 0.855], color="#2f6fed", linewidth=1.1, alpha=0.75)

    if not rows:
        ax.text(0.05, 0.79, empty_message, fontsize=11, va="top", color="#374151")
        return fig

    card_left = 0.05
    card_width = 0.90
    content_top = 0.82
    content_bottom = 0.07
    gap = 0.018
    card_height = calculate_report_card_height(len(rows), content_top, content_bottom, gap, layout_rows)
    detail_header = clean_report_text(headers[-1]) if headers else ""

    for row_index, row in enumerate(rows):
        raw_values = list(row)
        if len(raw_values) < len(headers):
            raw_values.extend(["-"] * (len(headers) - len(raw_values)))
        values = [clean_report_text(value) for value in raw_values]

        card_top = content_top - row_index * (card_height + gap)
        card_bottom = card_top - card_height
        ax.add_patch(plt.Rectangle(
            (card_left, card_bottom),
            card_width,
            card_height,
            facecolor="#fbfcfd",
            edgecolor="#d1d5db",
            linewidth=0.8,
        ))
        ax.add_patch(plt.Rectangle(
            (card_left, card_bottom),
            0.006,
            card_height,
            facecolor="#2f6fed",
            edgecolor="#2f6fed",
            linewidth=0,
        ))

        card_number = first_item_number + row_index
        badge_size = 0.044
        badge_x = card_left + 0.022
        badge_y = card_top - 0.065
        ax.add_patch(plt.Rectangle(
            (badge_x, badge_y),
            badge_size,
            badge_size,
            facecolor="#111827",
            edgecolor="#ffffff",
            linewidth=0.9,
        ))
        ax.text(
            badge_x + badge_size / 2,
            badge_y + badge_size / 2,
            str(card_number),
            fontsize=10.2,
            fontweight="bold",
            ha="center",
            va="center",
            color="#ffffff",
        )
        ax.text(
            card_left + 0.083,
            badge_y + badge_size / 2,
            format_problem_report_point_value(values[0] if values else "-"),
            fontsize=9.2,
            va="center",
            color="#6b7280",
        )

        metadata = list(zip(headers[1:-1], values[1:-1]))
        for meta_index, (label, value) in enumerate(metadata):
            meta_x = card_left + 0.022 + (meta_index % 2) * 0.205
            meta_y = card_top - 0.100 - (meta_index // 2) * 0.052
            ax.text(meta_x, meta_y, clean_report_text(label), fontsize=6.8, va="top", color="#6b7280")
            for line_index, line in enumerate(wrap_report_text(value, width=24, max_lines=2)):
                ax.text(
                    meta_x,
                    meta_y - 0.020 - line_index * 0.020,
                    line,
                    fontsize=8.3,
                    va="top",
                    color="#111827",
                )

        detail_x = card_left + 0.46
        detail_y = card_top - 0.050
        ax.text(detail_x, detail_y, detail_header, fontsize=6.8, va="top", color="#6b7280")
        max_detail_lines = max(2, int((card_height - 0.060) / 0.020))
        draw_problem_report_detail(ax, detail_x, detail_y, raw_values[-1], max_detail_lines)
    return fig


def format_problem_report_point_value(value):
    point = clean_report_text(value)
    if point.startswith("(") and point.endswith(")"):
        return point
    return f"({point})"


def calculate_report_card_height(row_count, content_top, content_bottom, gap, layout_rows=None):
    slot_count = max(row_count, layout_rows or row_count, 1)
    return (content_top - content_bottom - gap * (slot_count - 1)) / slot_count


def translate_ap_position_warning(warning, tr):
    return {
        AP_POSITION_STRONG_FAR: tr("ap_position_strong_far"),
        AP_POSITION_WEAK_CLOSE: tr("ap_position_weak_close"),
        AP_POSITION_UNEXPECTED_DOMINANT: tr("ap_position_unexpected_dominant"),
    }.get(warning, warning)


def build_dominant_problem_detail_items(row, warnings, tr, aliases, measurement_system="metric"):
    items = []
    if bool(row.get("roaming_overlap")):
        items.append({
            "label": tr("dominant_roaming_issue_title"),
            "value": format_dominant_roaming_detail(row, tr, aliases),
        })

    if warnings:
        items.append({
            "label": tr("ap_position_analysis"),
            "value": "; ".join(translate_ap_position_warning(warning, tr) for warning in warnings),
        })
        position_detail = format_dominant_position_detail(row, tr, aliases, measurement_system)
        if position_detail:
            items.append({
                "label": tr("ap_position_detail"),
                "value": position_detail,
            })

    return items


def format_dominant_roaming_detail(row, tr, aliases):
    dominant = format_ap_label(
        row.get("dominant_bssid", ""),
        aliases,
        row.get("dominant_ap_group", ""),
    )
    second = format_ap_label(
        row.get("second_bssid", ""),
        aliases,
        row.get("second_ap_group", ""),
    )
    return tr(
        "dominant_roaming_issue_detail",
        dominant=clean_report_text(dominant),
        second=clean_report_text(second),
        dominant_signal=format_report_value(row.get("dominant_signal_dbm"), suffix=" dBm"),
        second_signal=format_report_value(row.get("second_signal_dbm"), suffix=" dBm"),
        delta=format_report_value(row.get("delta_db"), suffix=" dB"),
        threshold="5 dB",
    )


def format_dominant_position_detail(row, tr, aliases=None, measurement_system="metric"):
    aliases = aliases or {}
    dominant_distance = format_position_report_distance(row, "dominant_ap_distance", measurement_system)
    nearest_distance = format_position_report_distance(row, "nearest_physical_ap_distance", measurement_system)
    if dominant_distance == "-" and nearest_distance == "-":
        return ""

    dominant = format_ap_label(
        row.get("dominant_bssid", ""),
        aliases,
        row.get("dominant_ap_group", ""),
    )
    nearest_label = clean_report_text(row.get("nearest_physical_ap_label"))
    return tr(
        "quality_dashboard_ap_position_detail",
        dominant=clean_report_text(dominant),
        signal=format_report_value(row.get("dominant_signal_dbm"), suffix=" dBm"),
        dominant_distance=dominant_distance,
        closest=nearest_label,
        closest_distance=nearest_distance,
    )


def format_position_report_distance(row, prefix, measurement_system="metric"):
    distance_m = row.get(f"{prefix}_m")
    if format_report_value(distance_m) != "-":
        return format_distance_meters(distance_m, measurement_system)

    distance_px = row.get(f"{prefix}_px")
    if format_report_value(distance_px) != "-":
        return format_report_value(distance_px, suffix=" px")

    return "-"


def format_report_value(value, suffix=""):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value or "-")

    if np.isnan(number):
        return "-"

    if number.is_integer():
        return f"{int(number)}{suffix}"

    return f"{number:.1f}{suffix}"


def parse_optional_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if np.isnan(number):
        return None

    return number


def clean_report_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""

    if not np.isfinite(number):
        return ""

    return round(number, 2)


def get_interference_mode_label(config, tr):
    if config.interference_mode == "all":
        return tr("interference_mode_all")

    return tr("interference_mode_intra_ssid")


def get_interference_diagnosis(row, tr):
    risk = float(row.get("risk", 0) or 0)
    if not np.isfinite(risk):
        return tr("advisor_rf_unknown")
    serving_channel = row.get("serving_channel", "")
    interferer_channel = row.get("strongest_interferer_channel", "")
    interferer_dbm = row.get("strongest_interferer_dbm", "")
    serving_width = parse_optional_float(row.get("serving_channel_width_mhz", ""))
    interferer_width = parse_optional_float(row.get("strongest_interferer_channel_width_mhz", ""))
    overlap = parse_optional_float(row.get("strongest_interferer_overlap", ""))

    if risk < 30:
        return tr("interference_diagnosis_low")

    try:
        same_channel = float(serving_channel) == float(interferer_channel)
    except (TypeError, ValueError):
        same_channel = False

    try:
        strong_interferer = float(interferer_dbm) >= -67
    except (TypeError, ValueError):
        strong_interferer = False

    if same_channel and strong_interferer:
        return tr("interference_diagnosis_same_channel_strong")
    if same_channel:
        return tr("interference_diagnosis_same_channel")
    if overlap and overlap > 0 and (
        (serving_width and serving_width > 20)
        or (interferer_width and interferer_width > 20)
    ):
        return tr("interference_diagnosis_wide_channel")
    if strong_interferer:
        return tr("interference_diagnosis_strong")

    return tr("interference_diagnosis_nearby")


def add_ap_position_report_columns(report_df, ap_groups, aliases, px_per_meter):
    if report_df.empty:
        return report_df

    enriched_rows = []
    for _index, row in report_df.iterrows():
        analysis = analyze_dominant_ap_position(row, ap_groups, px_per_meter)
        enriched_rows.append({
            "dominant_ap_distance_px": clean_report_number(analysis.get("dominant_distance_px")),
            "dominant_ap_distance_m": clean_report_number(analysis.get("dominant_distance_m")),
            "nearest_physical_ap_group": analysis.get("nearest_ap_group", ""),
            "nearest_physical_ap_label": get_ap_group_display_name(
                analysis.get("nearest_ap_group", ""),
                ap_groups,
                aliases,
            ),
            "nearest_physical_ap_distance_px": clean_report_number(analysis.get("nearest_distance_px")),
            "nearest_physical_ap_distance_m": clean_report_number(analysis.get("nearest_distance_m")),
            "ap_position_status": analysis.get("status", ""),
            "ap_position_warnings": ";".join(analysis.get("warnings", [])),
        })

    position_df = pd.DataFrame(enriched_rows, index=report_df.index)
    return pd.concat([report_df, position_df], axis=1)


def get_ap_group_display_name(group_id, ap_groups, aliases):
    group_id = str(group_id or "")
    if not group_id:
        return ""

    for group in ap_groups or []:
        if str(group.get("group_id", "")) == group_id:
            alias = str(group.get("alias", "")).strip()
            return alias or group_id

    return aliases.get(group_id) or group_id


def format_ap_role(role, tr):
    return tr(f"ap_group_role_{normalize_ap_role(role)}")


def build_interference_summary(risk_df, output_file, report_file, band, tr, language):
    known = risk_df.dropna(subset=["risk"])
    worst_row = known.loc[known["risk"].idxmax()] if not known.empty else risk_df.iloc[0]
    quality = get_interference_data_quality(risk_df)
    band_label = format_band_label(band, language)
    return {
        "band": band_label,
        "max_risk": f"{float(worst_row['risk']):.1f}%" if not known.empty else "—",
        "point": (
            f"{format_report_value(worst_row.get('x', ''))}, "
            f"{format_report_value(worst_row.get('y', ''))}"
        ),
        "serving_ap": worst_row.get("serving_bssid", "-"),
        "serving_role": format_ap_role(worst_row.get("serving_ap_role"), tr),
        "serving_channel": format_report_value(worst_row.get("serving_channel", "")),
        "serving_width": format_report_value(
            worst_row.get("serving_channel_width_mhz", ""),
            suffix=" MHz",
        ),
        "interferer": worst_row.get("strongest_interferer_bssid", "-"),
        "interferer_role": (
            format_ap_role(worst_row.get("strongest_interferer_ap_role"), tr)
            if worst_row.get("strongest_interferer_ap_role")
            else "-"
        ),
        "interferer_ssid": worst_row.get("strongest_interferer_ssid", "-"),
        "interferer_channel": format_report_value(worst_row.get("strongest_interferer_channel", "")),
        "interferer_width": format_report_value(
            worst_row.get("strongest_interferer_channel_width_mhz", ""),
            suffix=" MHz",
        ),
        "interferer_dbm": format_report_value(
            worst_row.get("strongest_interferer_dbm", ""),
            suffix=" dBm",
        ),
        "test_ignored": format_report_value(worst_row.get("test_ap_ignored_count", "")),
        "diagnosis": get_interference_diagnosis(worst_row, tr),
        "quality": quality,
        "quality_message": get_interference_quality_message(quality, band_label, tr),
        "output_file": output_file,
        "report_file": report_file,
    }


def get_interference_quality_message(quality, band_label, tr):
    if quality["percent"] >= 70:
        return tr("interference_quality_good")

    if band_label in {"5 GHz", "6 GHz"}:
        return tr("interference_quality_warning_5ghz")

    return tr("interference_quality_warning")
