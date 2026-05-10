from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ap_groups import (
    AP_ROLE_TEST,
    build_dominant_ap_group_labels,
    normalize_ap_role,
)
from ap_positioning import analyze_dominant_ap_position
from constants import HEATMAP_GRID_SIZE
from heatmap_tools import (
    add_ap_group_metadata,
    apply_distance_mask,
    apply_signal_threshold,
    calculate_interference_points,
    collapse_heatmap_points,
    filter_by_band,
    format_band_label,
    get_channel_map_points,
    get_dominant_ap_points,
    get_distance_alpha,
    get_interference_data_quality,
    get_scan_confidence_values,
    interpolate_signal_grid,
    smooth_heatmap_grid,
)
from map_rendering import (
    add_reference_table,
    annotate_channel_references,
    annotate_dominant_ap_references,
    annotate_interference_references,
    build_channel_legend_handles,
    build_dominant_ap_legend_handles,
    build_interference_legend_handles,
    get_channel_color,
    get_limited_bssid_color_map,
)
from utils import sanitize_filename


@dataclass
class MapExportResult:
    output_file: str
    report_file: str = ""
    map_type: str = ""
    summary: dict = field(default_factory=dict)

    @property
    def files(self):
        return [path for path in (self.output_file, self.report_file) if path]


class MapExportError(ValueError):
    def __init__(self, title, message):
        super().__init__(message)
        self.title = title
        self.message = message


def generate_map_export(
    df,
    bg_image,
    csv_file,
    config,
    tr,
    language="it",
    aliases=None,
    ap_groups=None,
    px_per_meter=None,
):
    config = config.normalized()
    aliases = aliases or {}
    ap_groups = ap_groups or []

    if not config.ssid:
        raise MapExportError(tr("warning"), tr("select_ssid_heatmap"))

    if config.is_interference:
        return generate_interference_map(
            df,
            bg_image,
            csv_file,
            config,
            tr,
            language,
        )

    if config.is_channel:
        return generate_channel_map(df, bg_image, csv_file, config, tr, language)

    if config.is_dominant:
        return generate_dominant_ap_map(
            df,
            bg_image,
            csv_file,
            config,
            tr,
            language,
            aliases,
            ap_groups,
            px_per_meter,
        )

    return generate_signal_map(df, bg_image, csv_file, config, tr, language)


def generate_signal_map(df, bg_image, csv_file, config, tr, language):
    ssid = config.ssid
    band = config.band
    rows = df[df["ssid"].str.lower() == ssid.lower()]
    rows = filter_by_band(rows, band)
    rows = add_ap_group_metadata(rows, config.ap_group_map, config.ap_group_roles)
    rows = rows[rows["ap_role"] != AP_ROLE_TEST]
    raw_rows = len(rows)
    rows = collapse_heatmap_points(rows, aggregation=config.aggregation)

    if len(rows) < 3:
        raise_insufficient_data(tr, band, language)

    x = rows["x"].values
    y = rows["y"].values
    signal = rows["signal_dbm"].values
    confidence = get_scan_confidence_values(rows)
    grid_x, grid_y = build_grid(bg_image)
    grid_z = interpolate_signal_grid(
        x,
        y,
        signal,
        grid_x,
        grid_y,
        method=config.interpolation,
        confidence=confidence,
    )
    grid_z = smooth_heatmap_grid(grid_z, sigma=config.smoothing_sigma)
    grid_z = apply_distance_mask(grid_z, grid_x, grid_y, x, y, config.max_distance_px)

    if config.usable_only:
        grid_z = apply_signal_threshold(grid_z, min_signal_dbm=-70)

    distance_alpha = get_distance_alpha(
        grid_x,
        grid_y,
        x,
        y,
        config.max_distance_px,
        point_confidence=confidence,
    )
    heatmap_alpha = np.where(np.isfinite(grid_z), distance_alpha * 0.55, 0)
    vmin, vmax = get_color_scale_limits(grid_z, config)
    output_file = build_map_output_path(csv_file, ssid, band)

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.imshow(np.array(bg_image))
    layer = ax.imshow(
        grid_z.T,
        extent=(0, bg_image.size[0], bg_image.size[1], 0),
        alpha=heatmap_alpha.T,
        cmap="RdYlGn",
        vmin=vmin,
        vmax=vmax,
        interpolation="bilinear",
    )
    fig.colorbar(layer, ax=ax, fraction=0.035, pad=0.02, label=tr("export_signal_colorbar"))
    ax.scatter(x, y, c="black", s=8)
    ax.set_title(
        f"{tr('export_signal_title')} - {ssid} - {format_band_label(band, language)} "
        f"({len(rows)} {tr('export_points')}, {raw_rows} {tr('export_measurements')}"
        f"{', >= -70 dBm' if config.usable_only else ''})"
    )
    ax.axis("off")
    save_figure(fig, output_file)
    return MapExportResult(output_file=output_file, map_type="signal")


def generate_channel_map(df, bg_image, csv_file, config, tr, language):
    ssid = config.ssid
    band = config.band
    channel_df = get_channel_map_points(
        df,
        ssid,
        band,
        ap_group_map=config.ap_group_map,
        ap_group_roles=config.ap_group_roles,
    )

    if channel_df.empty:
        raise_insufficient_data(tr, band, language)

    output_file = build_map_output_path(csv_file, ssid, f"channels_{band}")
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.imshow(np.array(bg_image))
    colors = [get_channel_color(row["channel"], band) for _index, row in channel_df.iterrows()]
    ax.scatter(
        channel_df["x"].values,
        channel_df["y"].values,
        c=colors,
        s=26,
        edgecolors="black",
        linewidths=0.42,
        zorder=3,
    )
    references = annotate_channel_references(
        ax,
        channel_df,
        format_report_value,
        mode=config.point_label_mode,
        band=band,
        labels=get_reference_label_terms(tr),
    )
    add_reference_table(
        ax,
        references,
        tr("reference_table_info"),
        overflow_label=tr("reference_more_in_report", count=max(0, len(references) - 10)),
    )
    ax.legend(
        handles=build_channel_legend_handles(
            channel_df,
            band,
            tr("channel_map_intermediate_24"),
            format_report_value,
            other_label=tr("legend_other"),
        ),
        title=tr("channel_map_legend_title"),
        loc="lower right",
        framealpha=0.88,
        facecolor="white",
        edgecolor="#333333",
    )
    ax.set_title(
        f"{tr('export_channel_title')} - {ssid} - {format_band_label(band, language)} "
        f"({len(channel_df)} {tr('export_points')})"
    )
    ax.axis("off")
    save_figure(fig, output_file)
    return MapExportResult(output_file=output_file, map_type="channel")


def generate_dominant_ap_map(
    df,
    bg_image,
    csv_file,
    config,
    tr,
    language,
    aliases,
    ap_groups,
    px_per_meter,
):
    ssid = config.ssid
    band = config.band
    dominant_df = get_dominant_ap_points(
        df,
        ssid,
        band,
        ap_group_map=config.ap_group_map,
        ap_group_roles=config.ap_group_roles,
    )

    if dominant_df.empty:
        raise_insufficient_data(tr, band, language)

    dominant_df = add_ap_position_report_columns(dominant_df, ap_groups, aliases, px_per_meter)
    dominant_df["ap_position_has_warning"] = (
        dominant_df["ap_position_warnings"].astype(str).str.len() > 0
    )
    output_file = build_map_output_path(csv_file, ssid, f"dominant_{band}")
    report_file = build_report_output_path(output_file)

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.imshow(np.array(bg_image))
    color_map, _visible_ap_groups, _hidden_ap_count = get_limited_bssid_color_map(dominant_df)
    colors = [
        color_map.get(row["dominant_ap_group"], "#7f8c8d")
        for _index, row in dominant_df.iterrows()
    ]
    edge_colors = [
        "#f1c40f" if row.get("roaming_overlap") else "black"
        for _index, row in dominant_df.iterrows()
    ]
    line_widths = [
        1.2 if row.get("roaming_overlap") else 0.42
        for _index, row in dominant_df.iterrows()
    ]
    warning_mask = dominant_df["ap_position_has_warning"]

    if (~warning_mask).any():
        ax.scatter(
            dominant_df.loc[~warning_mask, "x"].values,
            dominant_df.loc[~warning_mask, "y"].values,
            c=[color for color, is_warning in zip(colors, warning_mask) if not is_warning],
            s=30,
            edgecolors=[color for color, is_warning in zip(edge_colors, warning_mask) if not is_warning],
            linewidths=[width for width, is_warning in zip(line_widths, warning_mask) if not is_warning],
            marker="o",
            zorder=3,
        )
    if warning_mask.any():
        ax.scatter(
            dominant_df.loc[warning_mask, "x"].values,
            dominant_df.loc[warning_mask, "y"].values,
            c=[color for color, is_warning in zip(colors, warning_mask) if is_warning],
            s=36,
            edgecolors=[color for color, is_warning in zip(edge_colors, warning_mask) if is_warning],
            linewidths=[width for width, is_warning in zip(line_widths, warning_mask) if is_warning],
            marker="^",
            zorder=3,
        )

    references = annotate_dominant_ap_references(
        ax,
        dominant_df,
        format_report_value,
        mode=config.point_label_mode,
        labels=get_reference_label_terms(tr),
    )
    add_reference_table(
        ax,
        references,
        tr("reference_table_info"),
        overflow_label=tr("reference_more_in_report", count=max(0, len(references) - 10)),
    )
    ax.legend(
        handles=build_dominant_ap_legend_handles(
            dominant_df,
            color_map,
            tr("dominant_map_roaming_overlap"),
            other_label=tr("legend_other"),
            group_labels=build_dominant_ap_group_labels(dominant_df, aliases),
            position_warning_label=tr("ap_position_warning_legend"),
        ),
        title=tr("dominant_map_legend_title"),
        loc="lower right",
        framealpha=0.88,
        facecolor="white",
        edgecolor="#333333",
    )
    roaming_count = int(dominant_df["roaming_overlap"].sum())
    ax.set_title(
        f"{tr('export_dominant_title')} - {ssid} - {format_band_label(band, language)} "
        f"({len(dominant_df)} {tr('export_points')}, "
        f"{roaming_count} {tr('export_roaming_overlap')})"
    )
    ax.axis("off")
    save_figure(fig, output_file)
    save_dominant_ap_report(dominant_df, report_file)
    return MapExportResult(output_file=output_file, report_file=report_file, map_type="dominant")


def generate_interference_map(df, bg_image, csv_file, config, tr, language):
    ssid = config.ssid
    band = config.band
    if band not in {"2.4", "5"}:
        raise MapExportError(tr("warning"), tr("interference_requires_band"))

    risk_df = calculate_interference_points(
        df,
        ssid,
        band,
        mode=config.interference_mode,
        include_details=True,
        ap_group_map=config.ap_group_map,
        ap_group_roles=config.ap_group_roles,
    )
    if len(risk_df) < 3:
        raise_insufficient_data(tr, band, language)

    x = risk_df["x"].values
    y = risk_df["y"].values
    risk = risk_df["risk"].values
    confidence = get_scan_confidence_values(risk_df)
    grid_x, grid_y = build_grid(bg_image)
    grid_z = interpolate_signal_grid(
        x,
        y,
        risk,
        grid_x,
        grid_y,
        method=config.interpolation,
        confidence=confidence,
    )
    grid_z = smooth_heatmap_grid(grid_z, sigma=config.smoothing_sigma)
    grid_z = apply_distance_mask(grid_z, grid_x, grid_y, x, y, config.max_distance_px)
    distance_alpha = get_distance_alpha(
        grid_x,
        grid_y,
        x,
        y,
        config.max_distance_px,
        point_confidence=confidence,
    )
    heatmap_alpha = np.where(np.isfinite(grid_z), distance_alpha * 0.58, 0)
    output_file = build_map_output_path(csv_file, ssid, f"interference_{band}")
    report_file = build_report_output_path(output_file)

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.imshow(np.array(bg_image))
    heatmap_layer = ax.imshow(
        grid_z.T,
        extent=(0, bg_image.size[0], bg_image.size[1], 0),
        alpha=heatmap_alpha.T,
        cmap="RdYlGn_r",
        vmin=0,
        vmax=100,
        interpolation="bilinear",
    )
    cbar = fig.colorbar(heatmap_layer, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label(tr("interference_colorbar"))
    cbar.set_ticks([0, 30, 60, 100])
    cbar.set_ticklabels([
        f"0 {tr('interference_low')}",
        f"30 {tr('interference_medium')}",
        f"60 {tr('interference_high')}",
        "100",
    ])

    point_sizes = np.clip(14 + (risk * 0.24), 14, 38)
    ax.scatter(
        x,
        y,
        c=risk,
        s=point_sizes,
        cmap="RdYlGn_r",
        vmin=0,
        vmax=100,
        edgecolors="black",
        linewidths=0.42,
        zorder=3,
    )
    references = annotate_interference_references(
        ax,
        risk_df,
        format_report_value,
        mode=config.point_label_mode,
        labels=get_reference_label_terms(tr),
    )
    add_reference_table(
        ax,
        references,
        tr("reference_table_info"),
        overflow_label=tr("reference_more_in_report", count=max(0, len(references) - 10)),
    )
    ax.legend(
        handles=build_interference_legend_handles(
            tr("interference_low"),
            tr("interference_medium"),
            tr("interference_high"),
        ),
        title=tr("interference_legend_title"),
        loc="lower right",
        framealpha=0.88,
        facecolor="white",
        edgecolor="#333333",
    )
    ax.set_title(
        f"{tr('export_interference_title')} - {ssid} - {format_band_label(band, language)} "
        f"({get_interference_mode_label(config, tr)}) - "
        f"{tr('interference_top_risk')}: {float(risk_df['risk'].max()):.1f}%"
    )
    ax.axis("off")
    save_figure(fig, output_file)
    save_interference_report(risk_df, report_file, tr)
    summary = build_interference_summary(risk_df, output_file, report_file, band, tr, language)
    return MapExportResult(
        output_file=output_file,
        report_file=report_file,
        map_type="interference",
        summary=summary,
    )


def build_grid(bg_image):
    width, height = bg_image.size
    return np.mgrid[
        0:width:complex(HEATMAP_GRID_SIZE),
        0:height:complex(HEATMAP_GRID_SIZE),
    ]


def save_figure(fig, output_file):
    fig.savefig(output_file, dpi=200, bbox_inches="tight")
    plt.close(fig)


def build_map_output_path(csv_file, ssid, band_token):
    csv_path = Path(csv_file)
    token = {
        "all": "all",
        "2.4": "2.4ghz",
        "5": "5ghz",
        "interference_2.4": "interference_2.4ghz",
        "interference_5": "interference_5ghz",
        "channels_all": "channels_all",
        "channels_2.4": "channels_2.4ghz",
        "channels_5": "channels_5ghz",
        "dominant_all": "dominant_all",
        "dominant_2.4": "dominant_2.4ghz",
        "dominant_5": "dominant_5ghz",
    }.get(band_token, sanitize_filename(band_token))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = (
        f"{sanitize_filename(csv_path.stem)}_"
        f"{sanitize_filename(ssid)}_"
        f"{token}_{timestamp}.png"
    )
    return str(csv_path.with_name(file_name))


def build_report_output_path(map_output_file):
    output_path = Path(map_output_file)
    return str(output_path.with_name(f"{output_path.stem}_report.csv"))


def get_color_scale_limits(grid_z, config):
    if config.color_scale != "auto":
        return -90, -35

    valid_values = grid_z[np.isfinite(grid_z)]
    if len(valid_values) == 0:
        return -90, -35

    vmin = float(np.percentile(valid_values, 5))
    vmax = float(np.percentile(valid_values, 95))
    if vmax - vmin < 10:
        center = (vmin + vmax) / 2
        return center - 5, center + 5

    return vmin, vmax


def get_reference_label_terms(tr):
    return {
        "channel": tr("reference_channel"),
        "width": tr("reference_width"),
        "ap": tr("reference_ap"),
        "delta": tr("reference_delta"),
        "risk": tr("reference_risk"),
        "serving_channel": tr("reference_serving_channel"),
        "interferer_channel": tr("reference_interferer_channel"),
        "channel_short": "CH",
    }


def raise_insufficient_data(tr, band, language):
    raise MapExportError(
        tr("insufficient_data_title"),
        tr("insufficient_data", band=format_band_label(band, language)),
    )


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


def save_interference_report(risk_df, report_file, tr):
    report_df = risk_df.copy()
    report_df["diagnosis"] = report_df.apply(lambda row: get_interference_diagnosis(row, tr), axis=1)
    report_columns = [
        "timestamp",
        "x",
        "y",
        "ssid",
        "serving_ap_group",
        "serving_ap_role",
        "serving_bssid",
        "serving_channel",
        "serving_channel_width_mhz",
        "serving_signal_dbm",
        "serving_samples_seen",
        "serving_samples_total",
        "serving_scan_confidence",
        "risk",
        "interferer_count",
        "same_physical_ap_ignored_count",
        "test_ap_ignored_count",
        "interfering_bssids",
        "strongest_interferer_ssid",
        "strongest_interferer_ap_group",
        "strongest_interferer_ap_role",
        "strongest_interferer_bssid",
        "strongest_interferer_channel",
        "strongest_interferer_channel_width_mhz",
        "strongest_interferer_dbm",
        "strongest_interferer_samples_seen",
        "strongest_interferer_samples_total",
        "strongest_interferer_scan_confidence",
        "strongest_interferer_overlap",
        "diagnosis",
    ]
    write_existing_columns(report_df, report_columns, report_file)


def save_dominant_ap_report(dominant_df, report_file):
    report_df = dominant_df.copy()
    report_df["roaming_status"] = report_df["roaming_overlap"].map({
        True: "roaming_overlap",
        False: "stable",
    })
    report_columns = [
        "timestamp",
        "x",
        "y",
        "ssid",
        "dominant_ap_group",
        "dominant_ap_role",
        "dominant_bssid",
        "dominant_signal_dbm",
        "dominant_samples_seen",
        "dominant_samples_total",
        "dominant_scan_confidence",
        "dominant_channel",
        "dominant_channel_width_mhz",
        "second_ap_group",
        "second_ap_role",
        "second_bssid",
        "second_signal_dbm",
        "second_samples_seen",
        "second_samples_total",
        "second_scan_confidence",
        "second_channel",
        "second_channel_width_mhz",
        "delta_db",
        "roaming_status",
        "dominant_ap_distance_px",
        "dominant_ap_distance_m",
        "nearest_physical_ap_group",
        "nearest_physical_ap_label",
        "nearest_physical_ap_distance_px",
        "nearest_physical_ap_distance_m",
        "ap_position_status",
        "ap_position_warnings",
    ]
    write_existing_columns(report_df, report_columns, report_file)


def write_existing_columns(df, columns, output_file):
    existing_columns = [column for column in columns if column in df.columns]
    df[existing_columns].to_csv(output_file, index=False, encoding="utf-8")


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
    worst_row = risk_df.loc[risk_df["risk"].idxmax()]
    quality = get_interference_data_quality(risk_df)
    band_label = format_band_label(band, language)
    return {
        "band": band_label,
        "max_risk": f"{float(worst_row.get('risk', 0) or 0):.1f}%",
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

    if band_label == "5 GHz":
        return tr("interference_quality_warning_5ghz")

    return tr("interference_quality_warning")
