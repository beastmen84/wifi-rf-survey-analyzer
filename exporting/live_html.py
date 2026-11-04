"""Offline Live Map reports using the very same render payload as the Qt view."""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from matplotlib import colormaps
from matplotlib.colors import to_hex

from ap.groups import AP_ROLE_TEST
from app_core.file_io import atomic_write_text
from app_core.filenames import sanitize_filename
from exporting.html_report import document, disclosure, image_data, kpi, safe
from exporting.live_pdf import MapExportError, MapExportResult
from exporting.reports import add_ap_position_report_columns, translate_ap_position_warning
from maps.heatmap import (add_ap_group_metadata, filter_by_band, collapse_heatmap_points,
    calculate_interference_points, get_dominant_ap_points, get_scan_confidence_values, format_band_label)
from qt_ui.qt_live_map import render_live_map_payload
from translations.i18n import translate
from wifi.evidence import scan_confidence
from survey.measurement_quality import assess_survey_measurements
from survey.measurement_presentation import measurement_html


def build_live_html_output_path(csv_file, config):
    path = Path(csv_file)
    band = config.band + "GHz" if config.band in {"2.4", "5", "6"} else "all-bands"
    return str(path.with_name(f"{path.stem}.{sanitize_filename(config.ssid)}.{config.map_type}.{band}.html"))


def generate_live_html_export(df, bg_image, csv_file, config, tr, translations, language="en",
        aliases=None, ap_groups=None, px_per_meter=None, measurement_system="metric",
        output_file=None, boundary_mask_image=None, raw_rows=None, context_metadata=None):
    config = config.normalized()
    if not config.ssid:
        raise MapExportError(tr("warning"), tr("select_ssid_heatmap"))
    aliases, ap_groups = aliases or {}, ap_groups or []
    payload = render_live_map_payload(df, config, bg_image, translations, aliases,
        ap_groups, px_per_meter, boundary_mask_image)
    if not payload:
        raise MapExportError(tr("warning"), tr("live_preview_insufficient"))
    output = str(output_file or build_live_html_output_path(csv_file, config))
    if Path(output).suffix.lower() != ".html":
        raise ValueError("Choose HTML")
    label = lambda key, **kw: translate(language, "report_" + key, **kw)
    rows = add_ap_group_metadata(filter_by_band(df[df["ssid"] == config.ssid], config.band),
        config.ap_group_map, config.ap_group_roles)
    rows = rows[rows["ap_role"] != AP_ROLE_TEST]
    if config.ap_group_filter:
        rows = rows[rows["ap_group"] == config.ap_group_filter]
    diagnostics = diagnostics_for_map(df, rows, config, ap_groups, aliases, px_per_meter, tr)
    unknown = diagnostics["unknown"]
    points = payload["point_infos"]
    untrusted = int((get_scan_confidence_values(rows) <= 0).sum())
    body = ['<nav><a href="#map">' + safe(label("map")) + '</a><a href="#reviews">'
        + safe(label("reviews")) + '</a><a href="#measurements">' + safe(label("measurements")) + '</a></nav>',
        '<div class="kpis">', kpi(tr("export_points"), len(points)),
        kpi(tr("export_measurements"), len(rows)),
        kpi(diagnostics["label"], diagnostics["count"]), '</div>']
    if unknown:
        body.append(f'<div class="callout">{safe(label("unknown_risk", points=unknown))}</div>')
    if untrusted:
        body.append(f'<div class="callout">{safe(label("untrusted", points=untrusted))}</div>')
    body.append(f'<section id="map"><h2>{safe(label("map"))}</h2><p>{safe(label("map_hint"))}</p>')
    body.append(map_html(payload, label, tr))
    body.append('</section><section id="reviews">' + f'<h2>{safe(label("reviews"))}</h2>')
    for index, point in enumerate(points, 1):
        messages = diagnostics["issues"].get((point["x"], point["y"]), ())
        if messages:
            body.append(f'<article class="card data"><h3><a href="#point-{index}">{safe(tr("advisor_point"))} {index}</a>'
                f' · ({point["x"]:g}, {point["y"]:g}) px</h3><p>{safe(" · ".join(messages))}</p></article>')
    if not diagnostics["issues"]:
        body.append(f'<p class="panel">{safe(label("no_issues"))}</p>')
    body.append('</section>')
    point_details = []
    assessments = assess_survey_measurements(rows.to_dict("records"), raw_rows or [], context_metadata, {config.ssid})
    for index, point in enumerate(points, 1):
        point_rows = rows[(rows["x"] == point["x"]) & (rows["y"] == point["y"])]
        assessment_details = "".join(measurement_html(assessments[pid], tr)
            for pid in dict.fromkeys(str(value) for value in point_rows.get("point_id", [])) if pid in assessments)
        # Tooltip HTML comes from the app's escaping formatter, never source HTML.
        point_details.append(disclosure(f'{tr("advisor_point")} {index} · ({point["x"]:g}, {point["y"]:g}) px',
            assessment_details + point.get("tooltip", ""), f"point-{index}"))
    body.append(disclosure(label("measurements"), "".join(point_details), "measurements"))
    body.append(disclosure(label("provenance"), provenance_table(rows, tr, label)))
    params = [f'<p><b>SSID:</b> {safe(config.ssid)} · <b>{safe(tr("export_band"))}:</b> {safe(format_band_label(config.band, language))}</p>']
    for key, value in (("aggregation", config.aggregation), ("interpolation", config.interpolation)):
        if config.is_continuous:
            params.append(f'<p>{safe(tr(key))}: {safe(tr(key + "_" + value))}</p>')
    if config.is_interference:
        params.append(f'<p>{safe(tr("interference_mode"))}: {safe(tr("interference_mode_" + config.interference_mode))}</p>')
    params.append(f'<p>{safe(tr("advisor_ap"))}: {safe(aliases.get(config.ap_group_filter, config.ap_group_filter) or label("all_groups"))}</p>')
    for key, value in (("color_scale", config.color_scale), ("point_labels", config.point_label_mode)):
        params.append(f'<p>{safe(tr(key))}: {safe(tr(key + "_" + value))}</p>')
    params.append(f'<p>{safe(label("boundaries"))}: {safe(label("enabled" if boundary_mask_image is not None else "disabled"))}</p>')
    if config.is_continuous:
        params.append(f'<p>{safe(tr("survey_bounds"))}: {safe(label("enabled" if config.survey_bounds else "disabled"))}'
            f' · {safe(tr("usable_only"))}: {safe(label("enabled" if config.usable_only else "disabled"))}</p>'
            f'<p>{safe(tr("smoothing"))}: {config.smoothing_sigma:g} · {safe(tr("max_distance_px"))}: {config.max_distance_px:g}</p>')
    params.append(f'<p>{safe(label("snapshot"))}: {safe(Path(csv_file).name)} · {datetime.now(timezone.utc).isoformat(timespec="seconds")}</p>')
    body.append(disclosure(label("parameters"), "".join(params), "parameters"))
    body.append(f'<section class="panel"><h2>{safe(tr("advisor_limits"))}</h2><p>{safe(tr("advisor_general_limit"))}</p></section>')
    html = document(label("live_title"), "".join(body), language,
        f'{tr("map_type_" + config.map_type)} · {config.ssid} · {format_band_label(config.band, language)}')
    atomic_write_text(output, html)
    return MapExportResult(output_file=output, map_type=config.map_type)


def diagnostics_for_map(df, rows, config, groups, aliases, scale, tr):
    issues, unknown, count = {}, 0, 0
    label = tr("report_weak_points")
    if config.is_interference:
        records = calculate_interference_points(df, config.ssid, config.band,
            mode=config.interference_mode, include_details=True, ap_group_map=config.ap_group_map,
            ap_group_roles=config.ap_group_roles, ap_group_channel_overrides=config.ap_group_channel_overrides)
        label = tr("report_threshold")
        for row in records.to_dict("records"):
            value = row.get("risk")
            if not np.isfinite(value):
                unknown += 1
                issues.setdefault((row["x"], row["y"]), []).append(tr("advisor_rf_unknown"))
            elif value >= 20:
                count += 1
                issues.setdefault((row["x"], row["y"]), []).append(f'{tr("reference_risk")}: {value:.1f}%')
    elif config.is_dominant:
        records = get_dominant_ap_points(df, config.ssid, config.band,
            ap_group_map=config.ap_group_map, ap_group_roles=config.ap_group_roles)
        records = add_ap_position_report_columns(records, groups, aliases, scale)
        label = tr("report_reviews")
        for row in records.to_dict("records"):
            warnings = [translate_ap_position_warning(w, tr) for w in str(row.get("ap_position_warnings", "")).split(";") if w]
            if row.get("roaming_overlap"):
                warnings.append(tr("roaming_overlap"))
            if warnings:
                count += 1
                issues.setdefault((row["x"], row["y"]), []).extend(warnings)
    elif config.is_channel:
        label = tr("report_reviews")
        # Channel observations do not by themselves establish a recommended change.
    else:
        records = collapse_heatmap_points(rows, aggregation=config.aggregation)
        for row in records.to_dict("records"):
            if row["signal_dbm"] < -70:
                count += 1
                issues.setdefault((row["x"], row["y"]), []).append(f'{row["signal_dbm"]:g} dBm · {label}')
    return dict(issues=issues, count=count, unknown=unknown, label=label)


def map_html(payload, label, tr):
    image = payload["image"]
    width, height = image.size
    radius = max(7, min(width, height) / 65)
    parts = [f'<div class="map-frame"><svg viewBox="0 0 {width} {height}" role="img" aria-label="{safe(label("map"))}">',
        f'<image href="{image_data(image)}" width="{width}" height="{height}"/>']
    for index, point in enumerate(payload["point_infos"], 1):
        x, y = point["x"], point["y"]
        color, outline = safe(point.get("color", "#7f8c8d")), safe(point.get("outline", "white"))
        shape = (f'<polygon points="{x},{y-radius*1.3} {x-radius},{y+radius} {x+radius},{y+radius}"'
                 if point.get("shape") == "triangle" else f'<circle cx="{x}" cy="{y}" r="{radius}"')
        parts.append(f'<a href="#point-{index}" aria-label="{safe(tr("advisor_point"))} {index}"><title>{safe(tr("advisor_point"))} {index}</title>'
            + shape + f' class="map-point" fill="{color}" stroke="{outline}" stroke-width="1.5"/>'
            f'<text x="{x+radius+3}" y="{y+4}" font-size="{radius*1.6}" fill="#203246" stroke="white" stroke-width="3" paint-order="stroke">{index}</text></a>')
    for point in payload.get("ap_infos", []):
        x, y = point["x"], point["y"]
        right = x > width * .65
        label_x = max(5, min(width - 5, x - radius - 3 if right else x + radius + 3))
        label_y = max(radius * 2, min(height - radius, y - radius))
        anchor = "end" if right else "start"
        parts.append(f'<g><title>{safe(point["label"])}</title><rect x="{x-radius}" y="{y-radius}" width="{2*radius}" height="{2*radius}" fill="#235f99" stroke="white"/>'
            f'<text x="{label_x}" y="{label_y}" text-anchor="{anchor}" font-size="{radius*1.5}" fill="#203246" stroke="white" stroke-width="3" paint-order="stroke">{safe(point["label"])}</text></g>')
    parts.append('</svg>')
    scale = payload.get("scale_payload") or {}
    parts.append(f'<p><b>{safe(label("legend"))}</b></p>')
    if scale.get("kind") == "gradient":
        colors = ",".join(to_hex(colormaps[scale["cmap"]](value)) for value in np.linspace(1, 0, 9))
        parts.append(f'<div class="gradient" style="background:linear-gradient(to right,{colors})"></div>'
            f'<div class="scale-labels"><span>{scale["max"]:g}{safe(scale.get("suffix", ""))}</span>'
            f'<span>{scale["min"]:g}{safe(scale.get("suffix", ""))}</span></div>')
    else:
        # All point colors remain explained even if screen labels are suppressed.
        items = scale.get("items") or payload["point_infos"]
        unique = dict.fromkeys((str(p.get("color", "#7f8c8d")), str(p.get("label") or p.get("legend_label") or "")) for p in items)
        parts.append('<div class="legend">' + "".join(f'<span><i class="swatch" style="background:{safe(color)}"></i>{safe(text)}</span>' for color, text in unique) + '</div>')
    parts.append(f'<p class="small">● {safe(tr("advisor_point"))} · ■ {safe(tr("advisor_ap"))}</p></div>')
    return "".join(parts)


def provenance_table(rows, tr, label):
    fields = [("x", "X (px)"), ("y", "Y (px)"), ("bssid", "BSSID"), ("signal_dbm", "dBm"),
        ("channel", "CH"), ("channel_width_mhz", "MHz"), ("scan_confidence", tr("advisor_confidence")),
        ("backend", "Backend"), ("adapter_id", label("receiver")),
        ("signal_kind", label("provenance")), ("freshness", label("snapshot")), ("host_timestamp", "BSS timestamp")]
    body = ['<div class="table-scroll"><table><thead><tr>' + "".join(f'<th>{safe(title)}</th>' for _, title in fields) + '</tr></thead><tbody>']
    for row in rows.to_dict("records"):
        values = []
        for key, _ in fields:
            value = row.get(key, "")
            if key == "scan_confidence":
                value = f"{scan_confidence(row):.0%}"
            if key in {"signal_kind", "freshness"}:
                prefix = "advisor_signal_" if key == "signal_kind" else "advisor_freshness_"
                known = {"direct", "estimated"} if key == "signal_kind" else {"fresh"}
                value = tr(prefix + (value if value in known else "unknown"))
            values.append(f'<td>{safe(value)}</td>')
        body.append('<tr>' + "".join(values) + '</tr>')
    return "".join(body) + '</tbody></table></div>'
