"""Shared HTML tooltip helpers for Qt graphics items."""

import html


TOOLTIP_LONG_VALUE_LIMIT = 72
TOOLTIP_SECTION_KEY = "_tooltip_section"


def build_html_tooltip(title, rows, accent):
    safe_title = html.escape(str(title or "-"))
    safe_accent = html.escape(str(accent or "#444444"))
    body_rows = []
    for row in rows:
        if is_tooltip_section(row):
            safe_section = html.escape(str(row.get(TOOLTIP_SECTION_KEY) or "-"))
            border = "border-top:1px solid #e5e7eb;" if body_rows else ""
            body_rows.append(
                "<tr>"
                f"<td colspan='2' style='padding:7px 0 3px 0;{border}"
                "color:#374151;font-size:8.5pt;font-weight:700;'>"
                f"{safe_section}</td>"
                "</tr>"
            )
            continue

        label, value = row
        safe_label = html.escape(str(label or "-"))
        safe_value = format_tooltip_value(value)
        if should_stack_tooltip_value(value):
            body_rows.append(
                "<tr>"
                "<td colspan='2' style='padding:6px 0 1px 0;color:#5b6472;"
                "font-size:8.5pt;font-weight:600;'>"
                f"{safe_label}</td>"
                "</tr>"
                "<tr>"
                "<td colspan='2' style='padding:0 0 5px 0;color:#111827;"
                "font-weight:600;line-height:1.25;'>"
                f"{safe_value}</td>"
                "</tr>"
            )
        else:
            body_rows.append(
                "<tr>"
                "<td valign='top' style='padding:3px 14px 3px 0;color:#5b6472;"
                "white-space:nowrap;'>"
                f"{safe_label}</td>"
                "<td valign='top' style='padding:3px 0;color:#111827;"
                "font-weight:600;'>"
                f"{safe_value}</td>"
                "</tr>"
            )
    return (
        "<div style='font-family:Segoe UI,Arial,sans-serif;font-size:10pt;"
        "color:#111827;line-height:1.22;'>"
        f"<div style='border-left:4px solid {safe_accent};padding:3px 0 4px 8px;"
        "font-size:10.5pt;font-weight:700;margin-bottom:6px;'>"
        f"{safe_title}</div>"
        "<table cellspacing='0' cellpadding='0' style='min-width:210px;'>"
        f"{''.join(body_rows)}"
        "</table></div>"
    )


def tooltip_section(title):
    return {TOOLTIP_SECTION_KEY: title}


def is_tooltip_section(row):
    return isinstance(row, dict) and TOOLTIP_SECTION_KEY in row


def format_tooltip_value(value):
    parts = tooltip_value_text_parts(value)
    return "<br>".join(html.escape(part) for part in parts) if parts else "-"


def should_stack_tooltip_value(value):
    parts = tooltip_value_text_parts(value)
    if len(parts) > 1:
        return True
    return any(len(part) > TOOLTIP_LONG_VALUE_LIMIT for part in parts)


def tooltip_value_text_parts(value):
    if value in (None, ""):
        return []

    if isinstance(value, (list, tuple)):
        return [str(part) for part in value if str(part)]

    return str(value).splitlines() or [str(value)]
