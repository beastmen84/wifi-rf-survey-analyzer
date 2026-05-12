"""PNG and report export workflow for generated Wi-Fi maps."""

from base64 import a85encode
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from textwrap import wrap

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image as PILImage

from ap_groups import (
    AP_ROLE_TEST,
    build_dominant_ap_group_labels,
    format_ap_label,
    normalize_ap_role,
    resolve_ap_alias,
)
from ap_positioning import (
    AP_POSITION_STRONG_FAR,
    AP_POSITION_UNEXPECTED_DOMINANT,
    AP_POSITION_WEAK_CLOSE,
    analyze_dominant_ap_position,
)
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
    get_channel_band_prefix,
    get_channel_color,
    get_channel_display_band,
    get_channel_display_sort_key,
    get_channel_label_identity,
    get_limited_bssid_color_map,
    should_label_channel_point,
    should_label_dominant_point,
)
from utils import sanitize_filename


LIVE_PDF_POINT_SIZE = 105
LIVE_PDF_POINT_WARNING_SIZE = 132
LIVE_PDF_AP_ICON_SIZE_PX = 22
LIVE_PDF_INFO_HEIGHT_PX = 360
INTERFERENCE_PROBLEM_RISK_THRESHOLD = 30
INTERFERENCE_PROBLEM_REPORT_LIMIT = 12
INTERFERENCE_PROBLEM_ROWS_PER_PAGE = 4
_PDF_AP_ICON_CACHE = None


@dataclass(frozen=True)
class InlinePdfPageImage:
    jpeg_bytes: bytes
    width_px: int
    height_px: int
    width_pt: float
    height_pt: float


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


def generate_live_pdf_export(
    df,
    bg_image,
    csv_file,
    config,
    tr,
    language="it",
    aliases=None,
    ap_groups=None,
    px_per_meter=None,
    output_file=None,
):
    config = config.normalized()
    aliases = aliases or {}
    ap_groups = ap_groups or []
    if not config.ssid:
        raise MapExportError(tr("warning"), tr("select_ssid_heatmap"))

    output_file = str(output_file or build_live_pdf_output_path(csv_file, config))
    figures = []
    summary = {}

    if config.is_interference:
        map_fig, risk_df = build_live_pdf_interference_figure(
            df,
            bg_image,
            config,
            tr,
            language,
            aliases,
            ap_groups,
        )
        summary = build_interference_summary(risk_df, output_file, "", config.band, tr, language)
        figures.append(map_fig)
        figures.extend(build_interference_problem_report_pages(risk_df, config, tr, language, aliases))
    elif config.is_channel:
        figures.append(build_live_pdf_channel_figure(df, bg_image, config, tr, language, aliases, ap_groups))
    elif config.is_dominant:
        map_fig, dominant_df = build_live_pdf_dominant_figure(
            df,
            bg_image,
            config,
            tr,
            language,
            aliases,
            ap_groups,
            px_per_meter,
        )
        figures.append(map_fig)
        figures.extend(build_dominant_problem_report_pages(dominant_df, config, tr, language, aliases))
    else:
        figures.append(build_live_pdf_signal_figure(df, bg_image, config, tr, language, aliases, ap_groups))

    try:
        write_figures_as_live_pdf(figures, output_file)
    finally:
        for fig in figures:
            plt.close(fig)

    return MapExportResult(output_file=output_file, map_type=config.map_type, summary=summary)


def write_figures_as_live_pdf(figures, output_file):
    write_figures_as_inline_image_pdf(figures, output_file)


def write_figures_as_inline_image_pdf(figures, output_file):
    pages = [render_figure_to_pdf_page(fig) for fig in figures]
    if not pages:
        return

    write_inline_image_pdf(pages, output_file)


def render_figure_to_pdf_page(fig):
    render_dpi = 150
    buffer = BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=render_dpi,
        facecolor="white",
        edgecolor="white",
        transparent=False,
    )
    buffer.seek(0)
    with PILImage.open(buffer) as image:
        rgb_image = image.convert("RGB")
        jpeg_buffer = BytesIO()
        rgb_image.save(jpeg_buffer, format="JPEG", quality=92, optimize=True)
        width_px, height_px = rgb_image.size
        return InlinePdfPageImage(
            jpeg_bytes=jpeg_buffer.getvalue(),
            width_px=width_px,
            height_px=height_px,
            width_pt=(width_px / render_dpi) * 72.0,
            height_pt=(height_px / render_dpi) * 72.0,
        )


def write_inline_image_pdf(pages, output_file):
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        build_inline_pdf_pages_object(len(pages)),
    ]
    for index, page in enumerate(pages):
        page_object_number = 3 + index * 2
        content_object_number = page_object_number + 1
        objects.append(build_inline_pdf_page_object(page, content_object_number))
        objects.append(build_inline_pdf_content_object(page))

    output = BytesIO()
    output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, payload in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{object_number} 0 obj\n".encode("ascii"))
        output.write(payload)
        output.write(b"\nendobj\n")

    xref_position = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_position}\n%%EOF\n"
        ).encode("ascii")
    )
    Path(output_file).write_bytes(output.getvalue())


def build_inline_pdf_pages_object(page_count):
    kids = " ".join(f"{3 + index * 2} 0 R" for index in range(page_count))
    return f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii")


def build_inline_pdf_page_object(page, content_object_number):
    return (
        f"<< /Type /Page /Parent 2 0 R "
        f"/MediaBox [0 0 {page.width_pt:.4f} {page.height_pt:.4f}] "
        f"/Resources << /ProcSet [/PDF /ImageC] >> "
        f"/Contents {content_object_number} 0 R >>"
    ).encode("ascii")


def build_inline_pdf_content_object(page):
    content = build_inline_pdf_image_content(page)
    return b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream"


def build_inline_pdf_image_content(page):
    encoded_image = a85encode(page.jpeg_bytes, adobe=False) + b"~>"
    header = (
        f"q\n{page.width_pt:.4f} 0 0 {page.height_pt:.4f} 0 0 cm\n"
        "BI\n"
        f"/W {page.width_px}\n"
        f"/H {page.height_px}\n"
        "/CS /RGB\n"
        "/BPC 8\n"
        "/F [/ASCII85Decode /DCTDecode]\n"
        "ID\n"
    ).encode("ascii")
    return header + encoded_image + b"\nEI\nQ\n"


def build_live_pdf_signal_figure(df, bg_image, config, tr, language, aliases, ap_groups):
    rows = df[df["ssid"].str.lower() == config.ssid.lower()]
    rows = filter_by_band(rows, config.band)
    rows = add_ap_group_metadata(rows, config.ap_group_map, config.ap_group_roles)
    rows = rows[rows["ap_role"] != AP_ROLE_TEST]
    if config.ap_group_filter:
        rows = rows[rows["ap_group"] == config.ap_group_filter]
    raw_rows = len(rows)
    rows = collapse_heatmap_points(rows, aggregation=config.aggregation)

    if len(rows) < 3:
        raise_insufficient_data(tr, config.band, language)

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
    vmin, vmax = get_live_signal_color_scale_limits(grid_z, config)
    title = f"{tr('export_signal_title')} - {config.ssid}"
    fig, ax, side_ax = create_live_pdf_map_figure(bg_image, title)
    layer = ax.imshow(
        grid_z.T,
        extent=(0, bg_image.size[0], bg_image.size[1], 0),
        alpha=heatmap_alpha.T,
        cmap="RdYlGn",
        vmin=vmin,
        vmax=vmax,
        interpolation="bilinear",
        zorder=2,
    )
    ax.scatter(
        x,
        y,
        c="black",
        s=LIVE_PDF_POINT_SIZE,
        edgecolors="white",
        linewidths=0.9,
        zorder=4,
    )
    draw_ap_position_markers(ax, ap_groups, aliases, config.ap_group_filter)
    add_live_pdf_side_header(
        side_ax,
        title,
        config,
        tr,
        language,
        [
            (tr("export_points"), len(rows)),
            (tr("export_measurements"), raw_rows),
            (tr("aggregation"), tr(f"aggregation_{config.aggregation}")),
            (tr("interpolation"), tr(f"interpolation_{config.interpolation}")),
        ],
    )
    add_live_pdf_colorbar(fig, side_ax, layer, tr("export_signal_colorbar"))
    return fig


def build_live_pdf_interference_figure(df, bg_image, config, tr, language, aliases, ap_groups):
    if config.band not in {"2.4", "5", "6"}:
        raise MapExportError(tr("warning"), tr("interference_requires_band"))

    risk_df = calculate_interference_points(
        df,
        config.ssid,
        config.band,
        mode=config.interference_mode,
        include_details=True,
        ap_group_map=config.ap_group_map,
        ap_group_roles=config.ap_group_roles,
    )
    if len(risk_df) < 3:
        raise_insufficient_data(tr, config.band, language)

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
    vmin, vmax = get_risk_color_scale_limits(grid_z, config)
    title = f"{tr('export_interference_title')} - {config.ssid}"
    fig, ax, side_ax = create_live_pdf_map_figure(bg_image, title)
    layer = ax.imshow(
        grid_z.T,
        extent=(0, bg_image.size[0], bg_image.size[1], 0),
        alpha=heatmap_alpha.T,
        cmap="RdYlGn_r",
        vmin=vmin,
        vmax=vmax,
        interpolation="bilinear",
        zorder=2,
    )
    point_sizes = np.clip(LIVE_PDF_POINT_SIZE + (risk * 0.85), LIVE_PDF_POINT_SIZE, 185)
    ax.scatter(
        x,
        y,
        c=risk,
        s=point_sizes,
        cmap="RdYlGn_r",
        vmin=vmin,
        vmax=vmax,
        edgecolors="black",
        linewidths=0.75,
        zorder=4,
    )
    draw_ap_position_markers(ax, ap_groups, aliases, "")
    annotate_interference_problem_numbers(ax, get_interference_problem_df(risk_df))
    add_live_pdf_side_header(
        side_ax,
        title,
        config,
        tr,
        language,
        [
            (tr("interference_mode"), get_interference_mode_label(config, tr)),
            (tr("interference_top_risk"), f"{float(risk_df['risk'].max()):.1f}%"),
            (tr("interpolation"), tr(f"interpolation_{config.interpolation}")),
        ],
    )
    add_live_pdf_colorbar(fig, side_ax, layer, tr("interference_colorbar"))
    return fig, risk_df


def build_live_pdf_channel_figure(df, bg_image, config, tr, language, aliases, ap_groups):
    channel_df = get_channel_map_points(
        df,
        config.ssid,
        config.band,
        ap_group_map=config.ap_group_map,
        ap_group_roles=config.ap_group_roles,
        ap_group_filter=config.ap_group_filter,
    )
    if channel_df.empty:
        raise_insufficient_data(tr, config.band, language)

    title = f"{tr('export_channel_title')} - {config.ssid}"
    fig, ax, side_ax = create_live_pdf_map_figure(bg_image, title)
    colors = [
        get_channel_color(row["channel"], get_channel_display_band(row, config.band))
        for _index, row in channel_df.iterrows()
    ]
    ax.scatter(
        channel_df["x"].values,
        channel_df["y"].values,
        c=colors,
        s=LIVE_PDF_POINT_SIZE,
        edgecolors="black",
        linewidths=0.75,
        zorder=4,
    )
    draw_ap_position_markers(ax, ap_groups, aliases, config.ap_group_filter)
    legend_items = build_channel_point_legend_items(channel_df, config, aliases)
    add_live_pdf_side_header(
        side_ax,
        title,
        config,
        tr,
        language,
        [(tr("export_points"), len(channel_df))],
    )
    add_live_pdf_swatch_list(side_ax, legend_items, tr("channel_map_legend_title"), y=0.66)
    return fig


def build_live_pdf_dominant_figure(df, bg_image, config, tr, language, aliases, ap_groups, px_per_meter):
    dominant_df = get_dominant_ap_points(
        df,
        config.ssid,
        config.band,
        ap_group_map=config.ap_group_map,
        ap_group_roles=config.ap_group_roles,
    )
    if dominant_df.empty:
        raise_insufficient_data(tr, config.band, language)

    dominant_df = add_ap_position_report_columns(dominant_df, ap_groups, aliases, px_per_meter)
    dominant_df["ap_position_has_warning"] = dominant_df["ap_position_warnings"].astype(str).str.len() > 0
    title = f"{tr('export_dominant_title')} - {config.ssid}"
    fig, ax, side_ax = create_live_pdf_map_figure(bg_image, title)
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
        1.35 if row.get("roaming_overlap") else 0.75
        for _index, row in dominant_df.iterrows()
    ]
    warning_mask = dominant_df["ap_position_has_warning"]
    if (~warning_mask).any():
        ax.scatter(
            dominant_df.loc[~warning_mask, "x"].values,
            dominant_df.loc[~warning_mask, "y"].values,
            c=[color for color, is_warning in zip(colors, warning_mask) if not is_warning],
            s=LIVE_PDF_POINT_SIZE,
            edgecolors=[color for color, is_warning in zip(edge_colors, warning_mask) if not is_warning],
            linewidths=[width for width, is_warning in zip(line_widths, warning_mask) if not is_warning],
            marker="o",
            zorder=4,
        )
    if warning_mask.any():
        ax.scatter(
            dominant_df.loc[warning_mask, "x"].values,
            dominant_df.loc[warning_mask, "y"].values,
            c=[color for color, is_warning in zip(colors, warning_mask) if is_warning],
            s=LIVE_PDF_POINT_WARNING_SIZE,
            edgecolors=[color for color, is_warning in zip(edge_colors, warning_mask) if is_warning],
            linewidths=[width for width, is_warning in zip(line_widths, warning_mask) if is_warning],
            marker="^",
            zorder=4,
        )
    draw_ap_position_markers(ax, ap_groups, aliases, "")
    legend_items = build_dominant_point_legend_items(dominant_df, config, aliases, color_map)
    if config.point_label_mode != "none":
        legend_items.extend(build_dominant_marker_legend_items(dominant_df, tr))
    add_live_pdf_side_header(
        side_ax,
        title,
        config,
        tr,
        language,
        [
            (tr("export_points"), len(dominant_df)),
            (tr("export_roaming_overlap"), int(dominant_df["roaming_overlap"].sum())),
        ],
    )
    add_live_pdf_swatch_list(side_ax, legend_items, tr("dominant_map_legend_title"), y=0.66)
    return fig, dominant_df


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
        ap_group_filter=config.ap_group_filter,
    )

    if channel_df.empty:
        raise_insufficient_data(tr, band, language)

    output_file = build_map_output_path(csv_file, ssid, f"channels_{band}")
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.imshow(np.array(bg_image))
    colors = [
        get_channel_color(row["channel"], get_channel_display_band(row, band))
        for _index, row in channel_df.iterrows()
    ]
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
    if band not in {"2.4", "5", "6"}:
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
        "6": "6ghz",
        "interference_2.4": "interference_2.4ghz",
        "interference_5": "interference_5ghz",
        "interference_6": "interference_6ghz",
        "channels_all": "channels_all",
        "channels_2.4": "channels_2.4ghz",
        "channels_5": "channels_5ghz",
        "channels_6": "channels_6ghz",
        "dominant_all": "dominant_all",
        "dominant_2.4": "dominant_2.4ghz",
        "dominant_5": "dominant_5ghz",
        "dominant_6": "dominant_6ghz",
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


def build_live_pdf_output_path(csv_file, config):
    csv_path = Path(csv_file)
    token = {
        "signal": "coverage",
        "interference": f"interference_{format_band_token(config.band)}",
        "channel": f"channels_{format_band_token(config.band)}",
        "dominant": f"dominant_{format_band_token(config.band)}",
    }.get(config.map_type, sanitize_filename(config.map_type))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = (
        f"{sanitize_filename(csv_path.stem)}_"
        f"{sanitize_filename(config.ssid)}_"
        f"{token}_{timestamp}.pdf"
    )
    return str(csv_path.with_name(file_name))


def format_band_token(band):
    return {
        "all": "all",
        "2.4": "2.4ghz",
        "5": "5ghz",
        "6": "6ghz",
    }.get(band, sanitize_filename(str(band or "all")))


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


def get_live_signal_color_scale_limits(grid_z, config):
    if config.color_scale != "auto":
        return -90, -40
    return get_color_scale_limits(grid_z, config)


def get_risk_color_scale_limits(grid_z, config):
    if config.color_scale != "auto":
        return 0, 100

    valid_values = grid_z[np.isfinite(grid_z)]
    if len(valid_values) == 0:
        return 0, 100

    vmin = max(0.0, float(np.percentile(valid_values, 5)))
    vmax = min(100.0, float(np.percentile(valid_values, 95)))
    if vmax - vmin < 5:
        center = (vmin + vmax) / 2
        return max(0, center - 2.5), min(100, center + 2.5)

    return vmin, vmax


def create_live_pdf_map_figure(bg_image, title):
    width, height = bg_image.size
    info_height = max(LIVE_PDF_INFO_HEIGHT_PX, min(520, int(height * 0.18)))
    total_height = height + info_height
    dpi = 100
    fig = plt.figure(figsize=(width / dpi, total_height / dpi), dpi=dpi)
    info_fraction = info_height / total_height
    map_fraction = height / total_height
    ax = fig.add_axes([0, info_fraction, 1, map_fraction])
    ax.imshow(np.array(bg_image), zorder=1)
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.set_title("")
    ax.axis("off")

    info_ax = fig.add_axes([0, 0, 1, info_fraction])
    info_ax.set_xlim(0, 1)
    info_ax.set_ylim(0, 1)
    info_ax.axis("off")
    info_ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=info_ax.transAxes, color="#ffffff", zorder=0))
    info_ax.plot([0.02, 0.98], [0.94, 0.94], color="#d0d5dd", linewidth=1.0, transform=info_ax.transAxes)
    return fig, ax, info_ax


def add_live_pdf_side_header(side_ax, title, config, tr, language, extra_rows=None):
    side_ax.text(0.025, 0.78, title, fontsize=15, fontweight="bold", va="top", wrap=True)
    rows = [
        ("SSID", config.ssid),
        (tr("band"), format_band_label(config.band, language)),
    ]
    if config.is_continuous:
        rows.append((tr("color_scale"), tr(f"color_scale_{config.color_scale}")))
    rows.extend(extra_rows or [])
    columns = 3 if len(rows) > 4 else 2
    x_positions = [0.025, 0.245, 0.465] if columns == 3 else [0.025, 0.345]
    row_spacing = 0.16 if columns == 3 else 0.19
    for index, (label, value) in enumerate(rows):
        column = index % columns
        row = index // columns
        x = x_positions[column]
        y = 0.50 - (row * row_spacing)
        side_ax.text(x, y, str(label), fontsize=7.4, color="#667085", va="top")
        side_ax.text(x, y - 0.065, str(value), fontsize=8.8, color="#101828", va="top", fontweight="bold")


def add_live_pdf_colorbar(fig, side_ax, mappable, label):
    bbox = side_ax.get_position()
    side_ax.text(0.68, 0.62, label, fontsize=9.0, fontweight="bold", va="top", wrap=True)
    cax = fig.add_axes([
        bbox.x0 + bbox.width * 0.68,
        bbox.y0 + bbox.height * 0.28,
        bbox.width * 0.28,
        bbox.height * 0.14,
    ])
    cbar = fig.colorbar(mappable, cax=cax, orientation="horizontal")
    cbar.ax.tick_params(labelsize=7)


def add_live_pdf_swatch_list(side_ax, legend_items, title, y=0.66):
    if not legend_items:
        return

    x_start = 0.50
    side_ax.text(x_start, y, title, fontsize=9.5, fontweight="bold", va="top")
    y -= 0.12

    rows_per_column = 4
    max_columns = 4
    max_items = rows_per_column * max_columns
    column_width = 0.12
    for index, item in enumerate(legend_items[:max_items]):
        column = index // rows_per_column
        row = index % rows_per_column
        item_x = x_start + (column * column_width)
        item_y = y - (row * 0.11)
        marker = "^" if item.get("shape") == "triangle" else "o"
        side_ax.scatter(
            [item_x],
            [item_y + 0.006],
            s=38,
            marker=marker,
            facecolors=item.get("color", "#7f8c8d"),
            edgecolors=item.get("outline", "black"),
            linewidths=float(item.get("outline_width", 0.4)),
            transform=side_ax.transAxes,
            clip_on=False,
        )
        side_ax.text(item_x + 0.02, item_y, str(item.get("label", "")), fontsize=7.4, va="top", wrap=True)
    if len(legend_items) > max_items:
        side_ax.text(x_start, 0.08, f"+{len(legend_items) - max_items}", fontsize=7.4, va="top")


def draw_ap_position_markers(ax, ap_groups, aliases, selected_group=""):
    for group in build_visible_ap_position_groups(ap_groups):
        position = group.get("position") or {}
        try:
            x = float(position.get("x"))
            y = float(position.get("y"))
        except (TypeError, ValueError):
            continue

        group_id = str(group.get("group_id", ""))
        add_pdf_ap_icon(ax, x, y, zorder=6)
        if selected_group and group_id == str(selected_group):
            ax.scatter(
                [x],
                [y],
                marker="o",
                s=235,
                facecolors="none",
                edgecolors="#f1c40f",
                linewidths=2.2,
                zorder=7,
            )


def load_pdf_ap_icon():
    global _PDF_AP_ICON_CACHE
    if _PDF_AP_ICON_CACHE is not None:
        return _PDF_AP_ICON_CACHE

    icon_path = Path(__file__).resolve().parent / "images" / "wifi.png"
    if not icon_path.exists():
        _PDF_AP_ICON_CACHE = False
        return None

    _PDF_AP_ICON_CACHE = plt.imread(str(icon_path))
    return _PDF_AP_ICON_CACHE


def add_pdf_ap_icon(ax, x, y, xycoords="data", icon_size_px=LIVE_PDF_AP_ICON_SIZE_PX, zorder=6):
    icon = load_pdf_ap_icon()
    if icon is None or icon is False:
        scatter_kwargs = {}
        if xycoords != "data":
            scatter_kwargs["transform"] = xycoords
        ax.scatter(
            [x],
            [y],
            marker="o",
            s=LIVE_PDF_POINT_SIZE,
            c="#0d6efd",
            edgecolors="white",
            linewidths=0.9,
            zorder=zorder,
            clip_on=False,
            **scatter_kwargs,
        )
        return

    zoom = icon_size_px / max(icon.shape[0], icon.shape[1])
    image = OffsetImage(icon, zoom=zoom)
    artist = AnnotationBbox(
        image,
        (x, y),
        xycoords=xycoords,
        frameon=False,
        pad=0,
        box_alignment=(0.5, 0.5),
        annotation_clip=False,
        zorder=zorder,
    )
    ax.add_artist(artist)


def build_visible_ap_position_groups(ap_groups):
    visible = []
    for group in ap_groups or []:
        if normalize_ap_role(group.get("role")) == AP_ROLE_TEST:
            continue
        position = group.get("position") or {}
        try:
            float(position.get("x"))
            float(position.get("y"))
        except (TypeError, ValueError):
            continue
        visible.append(group)
    return visible


def build_channel_point_legend_items(channel_df, config, aliases):
    if config.point_label_mode == "none":
        return []

    items = []
    seen = set()
    previous_channel = None
    for _index, row in channel_df.iterrows():
        channel = row.get("channel", "")
        display_band = get_channel_display_band(row, config.band)
        if should_label_channel_point(row, previous_channel, config.point_label_mode, config.band):
            label = format_channel_point_legend_label(row, config, aliases)
            color = get_channel_color(channel, display_band)
            key = (label, color)
            if key in seen:
                previous_channel = get_channel_label_identity(row, config.band)
                continue
            seen.add(key)
            items.append({
                "label": label,
                "color": color,
                "sort_key": get_channel_display_sort_key(channel, display_band) + (label.casefold(),),
            })
        previous_channel = get_channel_label_identity(row, config.band)
    return sorted(items, key=lambda item: item.get("sort_key", ()))


def format_channel_point_legend_label(row, config, aliases):
    band_prefix = ""
    if config.band == "all":
        band_prefix = get_channel_band_prefix(row.get("channel", ""), get_channel_display_band(row, config.band))
    label_prefix = f"{band_prefix} " if band_prefix else ""
    return (
        f"{label_prefix}CH {format_report_value(row.get('channel', ''))} - "
        f"{format_ap_label(row.get('bssid', ''), aliases, row.get('ap_group', ''))}"
    )


def build_dominant_point_legend_items(dominant_df, config, aliases, color_map):
    if config.point_label_mode == "none":
        return []

    items = []
    seen_groups = set()
    group_labels = build_dominant_ap_group_labels(dominant_df, aliases)
    previous_group = None
    previous_roaming_overlap = False
    for _index, row in dominant_df.iterrows():
        group = row.get("dominant_ap_group", "")
        if (
            group not in seen_groups
            and should_label_dominant_point(row, previous_group, previous_roaming_overlap, config.point_label_mode)
        ):
            label = group_labels.get(
                group,
                format_ap_label(row.get("dominant_bssid", ""), aliases, group),
            )
            items.append({
                "label": label,
                "color": color_map.get(group, "#7f8c8d"),
                "shape": "circle",
                "sort_key": (label.casefold(),),
            })
            seen_groups.add(group)
        previous_group = group
        previous_roaming_overlap = bool(row.get("roaming_overlap"))
    return sorted(items, key=lambda item: item.get("sort_key", ()))


def build_dominant_marker_legend_items(dominant_df, tr):
    items = []
    if column_has_true(dominant_df, "roaming_overlap"):
        items.append({
            "label": tr("dominant_map_roaming_overlap"),
            "color": "#ffffff",
            "outline": "#f1c40f",
            "outline_width": 1.2,
            "shape": "circle",
        })
    if column_has_true(dominant_df, "ap_position_has_warning"):
        items.append({
            "label": tr("ap_position_warning_legend"),
            "color": "#ffffff",
            "outline": "black",
            "outline_width": 0.8,
            "shape": "triangle",
        })
    return items


def column_has_true(df, column):
    if column not in df:
        return False
    return bool(df[column].fillna(False).astype(bool).any())


def get_interference_problem_df(risk_df):
    if risk_df.empty or "risk" not in risk_df.columns:
        return risk_df.head(0).copy()

    problem_df = (
        risk_df[risk_df["risk"] >= INTERFERENCE_PROBLEM_RISK_THRESHOLD]
        .sort_values("risk", ascending=False)
        .head(INTERFERENCE_PROBLEM_REPORT_LIMIT)
        .copy()
    )
    problem_df["report_number"] = range(1, len(problem_df) + 1)
    return problem_df


def annotate_interference_problem_numbers(ax, problem_df):
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
    card_height = (content_top - content_bottom - gap * (len(rows) - 1)) / len(rows)

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
            f"{tr('reference_risk')}: {risk:.1f}%",
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


def build_dominant_problem_report_pages(dominant_df, config, tr, language, aliases):
    group_labels = build_dominant_ap_group_labels(dominant_df, aliases)
    rows = []
    for _index, row in dominant_df.iterrows():
        issues = []
        if bool(row.get("roaming_overlap")):
            issues.append(tr("dominant_map_roaming_overlap"))
        warnings = [
            warning
            for warning in str(row.get("ap_position_warnings", "")).split(";")
            if warning
        ]
        issues.extend(translate_ap_position_warning(warning, tr) for warning in warnings)
        if not issues:
            continue

        group = row.get("dominant_ap_group", "")
        rows.append([
            f"{format_report_value(row.get('x'))}, {format_report_value(row.get('y'))}",
            group_labels.get(group, format_ap_label(row.get("dominant_bssid", ""), aliases, group)),
            format_report_value(row.get("delta_db"), suffix=" dB"),
            "; ".join(issues),
        ])

    return build_problem_report_pages(
        tr("live_pdf_problem_report_title"),
        f"{tr('export_dominant_title')} - {config.ssid} - {format_band_label(config.band, language)}",
        [tr("interference_summary_point"), tr("dominant_map_legend_title"), tr("reference_delta"),
         tr("live_pdf_issue")],
        rows[:14],
        tr("live_pdf_no_dominant_issues"),
    )


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
        ))
    return pages


def clean_report_text(value):
    if value is None:
        return "-"
    text = str(value).strip()
    return text or "-"


def wrap_report_text(value, width, max_lines):
    lines = wrap(
        clean_report_text(value),
        width=width,
        break_long_words=False,
        replace_whitespace=True,
    ) or ["-"]
    if len(lines) <= max_lines:
        return lines

    lines = lines[:max_lines]
    lines[-1] = f"{lines[-1].rstrip('.')}..."
    return lines


def build_problem_report_page(
    title,
    subtitle,
    headers,
    rows,
    empty_message,
    page_number=None,
    page_count=None,
    first_item_number=1,
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
    card_height = (content_top - content_bottom - gap * (len(rows) - 1)) / len(rows)
    first_header = clean_report_text(headers[0]) if headers else ""
    detail_header = clean_report_text(headers[-1]) if headers else ""

    for row_index, row in enumerate(rows):
        values = [clean_report_text(value) for value in row]
        if len(values) < len(headers):
            values.extend(["-"] * (len(headers) - len(values)))

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
        ax.text(
            card_left + 0.022,
            card_top - 0.026,
            f"{card_number}. {first_header}: {values[0] if values else '-'}",
            fontsize=10.2,
            fontweight="bold",
            va="top",
            color="#111827",
        )

        metadata = list(zip(headers[1:-1], values[1:-1]))
        for meta_index, (label, value) in enumerate(metadata):
            meta_x = card_left + 0.022 + (meta_index % 2) * 0.205
            meta_y = card_top - 0.065 - (meta_index // 2) * 0.052
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

        detail_x = card_left + 0.49
        detail_y = card_top - 0.050
        ax.text(detail_x, detail_y, detail_header, fontsize=6.8, va="top", color="#6b7280")
        max_detail_lines = max(2, int((card_height - 0.068) / 0.023))
        for line_index, line in enumerate(wrap_report_text(values[-1], width=66, max_lines=max_detail_lines)):
            ax.text(
                detail_x,
                detail_y - 0.023 - line_index * 0.023,
                line,
                fontsize=8.5,
                va="top",
                color="#111827",
            )
    return fig


def translate_ap_position_warning(warning, tr):
    return {
        AP_POSITION_STRONG_FAR: tr("ap_position_strong_far"),
        AP_POSITION_WEAK_CLOSE: tr("ap_position_weak_close"),
        AP_POSITION_UNEXPECTED_DOMINANT: tr("ap_position_unexpected_dominant"),
    }.get(warning, warning)


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

    if band_label in {"5 GHz", "6 GHz"}:
        return tr("interference_quality_warning_5ghz")

    return tr("interference_quality_warning")
