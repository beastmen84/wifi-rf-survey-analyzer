"""PDF export workflow for generated Wi-Fi live maps."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

from ap.groups import (
    AP_ROLE_TEST,
    build_dominant_ap_group_labels,
    format_ap_label,
    normalize_ap_role,
)
from app_core.constants import HEATMAP_GRID_SIZE
from maps.boundaries import get_boundary_mask_alpha
from maps.heatmap import (
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
    get_scan_confidence_values,
    get_survey_bounds_alpha,
    interpolate_signal_grid,
    smooth_heatmap_grid,
)
from maps.rendering import (
    get_channel_band_prefix,
    get_channel_color,
    get_channel_display_band,
    get_channel_display_sort_key,
    get_channel_label_identity,
    get_limited_bssid_color_map,
    should_label_channel_point,
    should_label_dominant_point,
)
from exporting.reports import (
    add_ap_position_report_columns,
    annotate_dominant_problem_numbers,
    annotate_interference_problem_numbers,
    build_dominant_problem_report_pages,
    build_interference_problem_report_pages,
    build_interference_summary,
    build_problem_report_pages,
    format_report_value,
    get_dominant_problem_df,
    get_interference_mode_label,
    get_interference_problem_df,
)
from exporting.pdf_writer import write_figures_as_live_pdf
from app_core.filenames import sanitize_filename


LIVE_PDF_POINT_SIZE = 105
LIVE_PDF_POINT_WARNING_SIZE = 132
LIVE_PDF_AP_ICON_SIZE_PX = 22
LIVE_PDF_INFO_HEIGHT_PX = 360
LIVE_PDF_INFO_MAX_HEIGHT_PX = 760
LIVE_PDF_BOTTOM_WHITESPACE_MAX_PX = 180
LIVE_PDF_BOTTOM_BACKGROUND_SAMPLE_ROWS = 32
LIVE_PDF_BOTTOM_BACKGROUND_COLOR_DELTA = 12
LIVE_PDF_BOTTOM_BACKGROUND_VARIATION = 6.0
LIVE_PDF_MAP_DATA_MARGIN_PX = 80
LIVE_PDF_SWATCH_COLUMNS = 4
LIVE_PDF_SWATCH_BASE_ROWS = 4
LIVE_PDF_SWATCH_MAX_ROWS = 8
_PDF_AP_ICON_CACHE = None


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
    measurement_system="metric",
    output_file=None,
    boundary_mask_image=None,
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
            boundary_mask_image=boundary_mask_image,
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
        figures.extend(build_dominant_problem_report_pages(
            dominant_df,
            config,
            tr,
            language,
            aliases,
            measurement_system=measurement_system,
        ))
    else:
        figures.append(
            build_live_pdf_signal_figure(
                df,
                bg_image,
                config,
                tr,
                language,
                aliases,
                ap_groups,
                boundary_mask_image=boundary_mask_image,
            )
        )

    try:
        write_figures_as_live_pdf(figures, output_file)
    finally:
        for fig in figures:
            plt.close(fig)

    return MapExportResult(output_file=output_file, map_type=config.map_type, summary=summary)


def build_live_pdf_signal_figure(
    df,
    bg_image,
    config,
    tr,
    language,
    aliases,
    ap_groups,
    boundary_mask_image=None,
):
    rows = df[df["ssid"] == config.ssid]
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
    bounds_alpha = get_live_pdf_bounds_alpha(
        config,
        grid_x,
        grid_y,
        x,
        y,
        boundary_mask_image=boundary_mask_image,
    )
    grid_z = apply_live_pdf_bounds_mask(grid_z, bounds_alpha)

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
    heatmap_alpha = np.where(np.isfinite(grid_z), distance_alpha * bounds_alpha * 0.55, 0)
    vmin, vmax = get_live_signal_color_scale_limits(grid_z, config)
    title = f"{tr('export_signal_title')} - {config.ssid}"
    map_bottom = calculate_live_pdf_map_bottom(bg_image, y, ap_groups=ap_groups)
    fig, ax, side_ax = create_live_pdf_map_figure(bg_image, title, map_bottom=map_bottom)
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


def build_live_pdf_interference_figure(
    df,
    bg_image,
    config,
    tr,
    language,
    aliases,
    ap_groups,
    boundary_mask_image=None,
):
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
        ap_group_channel_overrides=config.ap_group_channel_overrides,
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
    bounds_alpha = get_live_pdf_bounds_alpha(
        config,
        grid_x,
        grid_y,
        x,
        y,
        boundary_mask_image=boundary_mask_image,
    )
    grid_z = apply_live_pdf_bounds_mask(grid_z, bounds_alpha)
    distance_alpha = get_distance_alpha(
        grid_x,
        grid_y,
        x,
        y,
        config.max_distance_px,
        point_confidence=confidence,
    )
    heatmap_alpha = np.where(np.isfinite(grid_z), distance_alpha * bounds_alpha * 0.58, 0)
    vmin, vmax = get_risk_color_scale_limits(grid_z, config)
    title = f"{tr('export_interference_title')} - {config.ssid}"
    map_bottom = calculate_live_pdf_map_bottom(bg_image, y, ap_groups=ap_groups)
    fig, ax, side_ax = create_live_pdf_map_figure(bg_image, title, map_bottom=map_bottom)
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
            (tr("interference_top_risk"), f"{float(risk_df['risk'].max()):.1f}%"
                if risk_df["risk"].notna().any() else tr("advisor_rf_unknown")),
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
        ap_group_channel_overrides=config.ap_group_channel_overrides,
    )
    if channel_df.empty:
        raise_insufficient_data(tr, config.band, language)

    colors = [
        get_channel_color(row["channel"], get_channel_display_band(row, config.band))
        for _index, row in channel_df.iterrows()
    ]
    legend_items = build_channel_point_legend_items(channel_df, config, aliases)
    title = f"{tr('export_channel_title')} - {config.ssid}"
    map_bottom = calculate_live_pdf_map_bottom(
        bg_image,
        channel_df["y"].values,
        ap_groups=ap_groups,
    )
    fig, ax, side_ax = create_live_pdf_map_figure(
        bg_image,
        title,
        map_bottom=map_bottom,
        legend_item_count=len(legend_items),
    )
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
    legend_items = build_dominant_point_legend_items(dominant_df, config, aliases, color_map)
    if config.point_label_mode != "none":
        legend_items.extend(build_dominant_marker_legend_items(dominant_df, tr))
    map_bottom = calculate_live_pdf_map_bottom(
        bg_image,
        dominant_df["y"].values,
        ap_groups=ap_groups,
    )
    fig, ax, side_ax = create_live_pdf_map_figure(
        bg_image,
        title,
        map_bottom=map_bottom,
        legend_item_count=len(legend_items),
    )
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
    annotate_dominant_problem_numbers(ax, get_dominant_problem_df(dominant_df))
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


def build_grid(bg_image):
    width, height = bg_image.size
    return np.mgrid[
        0:width:complex(HEATMAP_GRID_SIZE),
        0:height:complex(HEATMAP_GRID_SIZE),
    ]


def get_live_pdf_bounds_alpha(config, grid_x, grid_y, point_x, point_y, boundary_mask_image=None):
    if not getattr(config, "survey_bounds", False):
        return np.ones(grid_x.shape)

    boundary_alpha = get_boundary_mask_alpha(boundary_mask_image, grid_x, grid_y)
    if boundary_alpha is not None:
        return boundary_alpha

    return get_survey_bounds_alpha(
        grid_x,
        grid_y,
        point_x,
        point_y,
        max_distance_px=config.max_distance_px,
    )


def apply_live_pdf_bounds_mask(grid_z, bounds_alpha):
    return np.where(bounds_alpha > 0, grid_z, np.nan)


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


def create_live_pdf_map_figure(bg_image, title, map_bottom=None, legend_item_count=0):
    width, height = bg_image.size
    map_height = normalize_live_pdf_map_bottom(map_bottom, height)
    info_height = calculate_live_pdf_info_height(map_height, legend_item_count)
    total_height = map_height + info_height
    dpi = 100
    fig = plt.figure(figsize=(width / dpi, total_height / dpi), dpi=dpi)
    info_fraction = info_height / total_height
    map_fraction = map_height / total_height
    ax = fig.add_axes([0, info_fraction, 1, map_fraction])
    display_image = bg_image.crop((0, 0, width, map_height)) if map_height < height else bg_image
    ax.imshow(np.array(display_image), zorder=1)
    ax.set_xlim(0, width)
    ax.set_ylim(map_height, 0)
    ax.set_title("")
    ax.axis("off")

    info_ax = fig.add_axes([0, 0, 1, info_fraction])
    info_ax.set_xlim(0, 1)
    info_ax.set_ylim(0, 1)
    info_ax.axis("off")
    info_ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=info_ax.transAxes, color="#ffffff", zorder=0))
    info_ax.plot([0.02, 0.98], [0.94, 0.94], color="#d0d5dd", linewidth=1.0, transform=info_ax.transAxes)
    return fig, ax, info_ax


def calculate_live_pdf_info_height(map_height, legend_item_count=0):
    base_height = max(LIVE_PDF_INFO_HEIGHT_PX, min(520, int(map_height * 0.18)))
    rows_per_column = calculate_live_pdf_swatch_rows_per_column(legend_item_count)
    extra_rows = max(0, rows_per_column - LIVE_PDF_SWATCH_BASE_ROWS)
    if extra_rows:
        base_height = max(base_height, LIVE_PDF_INFO_HEIGHT_PX + extra_rows * 48)
    return min(LIVE_PDF_INFO_MAX_HEIGHT_PX, base_height)


def calculate_live_pdf_map_bottom(bg_image, y_values=None, ap_groups=None):
    width, height = bg_image.size
    image_bottom = detect_live_pdf_image_content_bottom(bg_image)
    data_bottom = detect_live_pdf_data_bottom(y_values, ap_groups)
    target_bottom = max(image_bottom, data_bottom)
    return normalize_live_pdf_map_bottom(target_bottom, height)


def detect_live_pdf_image_content_bottom(bg_image):
    width, height = bg_image.size
    if width <= 0 or height <= 0:
        return height

    pixels = np.asarray(bg_image.convert("RGB"))
    if pixels.size == 0:
        return height

    blank_tail_top = detect_live_pdf_uniform_bottom_tail_top(pixels)
    if blank_tail_top is None:
        return height

    blank_tail = height - blank_tail_top
    if blank_tail <= LIVE_PDF_BOTTOM_WHITESPACE_MAX_PX:
        return height

    return blank_tail_top + LIVE_PDF_BOTTOM_WHITESPACE_MAX_PX


def detect_live_pdf_uniform_bottom_tail_top(pixels):
    height = pixels.shape[0]
    if height <= 0:
        return None

    sample_rows = min(LIVE_PDF_BOTTOM_BACKGROUND_SAMPLE_ROWS, height)
    bottom_sample = pixels[-sample_rows:]
    background = np.median(bottom_sample.reshape(-1, 3), axis=0)

    row_medians = np.median(pixels, axis=1)
    row_color_delta = np.max(
        np.abs(row_medians.astype(np.float32) - background.astype(np.float32)),
        axis=1,
    )
    row_variation = pixels.astype(np.float32).std(axis=1).mean(axis=1)
    bottom_variation = float(np.percentile(row_variation[-sample_rows:], 95))
    variation_limit = max(
        LIVE_PDF_BOTTOM_BACKGROUND_VARIATION,
        bottom_variation + 2.5,
    )
    background_rows = (
        (row_color_delta <= LIVE_PDF_BOTTOM_BACKGROUND_COLOR_DELTA)
        & (row_variation <= variation_limit)
    )

    row_index = height - 1
    while row_index >= 0 and background_rows[row_index]:
        row_index -= 1

    return row_index + 1 if row_index < height - 1 else None


def detect_live_pdf_data_bottom(y_values=None, ap_groups=None):
    values = []
    if y_values is not None:
        for value in y_values:
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue

    for group in build_visible_ap_position_groups(ap_groups):
        position = group.get("position") or {}
        try:
            values.append(float(position.get("y")))
        except (TypeError, ValueError):
            continue

    if not values:
        return 0

    return int(np.ceil(max(values) + LIVE_PDF_MAP_DATA_MARGIN_PX))


def normalize_live_pdf_map_bottom(map_bottom, image_height):
    try:
        bottom = int(np.ceil(float(map_bottom)))
    except (TypeError, ValueError):
        bottom = int(image_height)
    return min(max(1, bottom), int(image_height))


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

    rows_per_column = calculate_live_pdf_swatch_rows_per_column(len(legend_items))
    max_columns = LIVE_PDF_SWATCH_COLUMNS
    max_items = rows_per_column * max_columns
    column_width = 0.12
    row_spacing = min(0.11, max(0.055, (y - 0.08) / max(1, rows_per_column - 1)))
    for index, item in enumerate(legend_items[:max_items]):
        column = index // rows_per_column
        row = index % rows_per_column
        item_x = x_start + (column * column_width)
        item_y = y - (row * row_spacing)
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


def calculate_live_pdf_swatch_rows_per_column(item_count):
    try:
        count = int(item_count)
    except (TypeError, ValueError):
        count = 0
    if count <= 0:
        return LIVE_PDF_SWATCH_BASE_ROWS

    required_rows = int(np.ceil(count / LIVE_PDF_SWATCH_COLUMNS))
    return min(max(LIVE_PDF_SWATCH_BASE_ROWS, required_rows), LIVE_PDF_SWATCH_MAX_ROWS)


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

    icon_path = Path(__file__).resolve().parent.parent / "images" / "wifi.png"
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


def raise_insufficient_data(tr, band, language):
    raise MapExportError(
        tr("insufficient_data_title"),
        tr("insufficient_data", band=format_band_label(band, language)),
    )
