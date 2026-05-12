"""Shared HTML tooltip helpers for Qt graphics items."""

import html


def build_html_tooltip(title, rows, accent):
    safe_title = html.escape(str(title or "-"))
    safe_accent = html.escape(str(accent or "#444444"))
    body_rows = []
    for label, value in rows:
        body_rows.append(
            "<tr>"
            f"<td style='padding:2px 10px 2px 0;color:#5b6472;'>{html.escape(str(label))}</td>"
            f"<td style='padding:2px 0;font-weight:600;'>{format_tooltip_value(value)}</td>"
            "</tr>"
        )
    return (
        "<div style='font-family:Segoe UI,Arial,sans-serif;font-size:10pt;'>"
        f"<div style='border-left:4px solid {safe_accent};padding-left:7px;"
        "font-weight:700;margin-bottom:5px;'>"
        f"{safe_title}</div>"
        "<table cellspacing='0' cellpadding='0'>"
        f"{''.join(body_rows)}"
        "</table></div>"
    )


def format_tooltip_value(value):
    if value in (None, ""):
        return "-"

    if isinstance(value, (list, tuple)):
        parts = [str(part) for part in value if str(part)]
    else:
        parts = str(value).splitlines() or [str(value)]

    return "<br>".join(html.escape(part) for part in parts) if parts else "-"
