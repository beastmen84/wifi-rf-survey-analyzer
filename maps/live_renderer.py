"""Background renderer for interactive live map previews."""

import copy
from io import BytesIO
from threading import Lock

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

from app_core.constants import HEATMAP_GRID_SIZE
from ap.groups import AP_ROLE_TEST
from maps.boundaries import boundary_mask_fingerprint, get_boundary_mask_alpha
from maps.heatmap import (
    add_ap_group_metadata,
    apply_distance_mask,
    apply_signal_threshold,
    calculate_interference_points,
    collapse_heatmap_points,
    filter_by_band,
    get_distance_alpha,
    get_scan_confidence_values,
    get_survey_bounds_alpha,
    interpolate_signal_grid,
    smooth_heatmap_grid,
)


_grid_cache = {}
_result_cache = {}
_cache_lock = Lock()
_MAX_RESULT_CACHE_ITEMS = 8


def render_live_continuous_map(
    df,
    config,
    bg_image,
    translations,
    point_tooltip_builder,
    color_scale_limits,
    boundary_mask_image=None,
):
    cache_key = build_result_cache_key(df, config, bg_image, translations, boundary_mask_image)
    with _cache_lock:
        cached = _result_cache.get(cache_key)
        if cached is not None:
            return clone_cached_result(cached)

    if config.is_interference:
        payload = build_interference_payload(
            df,
            config,
            bg_image,
            translations,
            point_tooltip_builder,
            color_scale_limits,
            boundary_mask_image=boundary_mask_image,
        )
    else:
        payload = build_signal_payload(
            df,
            config,
            bg_image,
            translations,
            point_tooltip_builder,
            color_scale_limits,
            boundary_mask_image=boundary_mask_image,
        )

    if payload is None:
        return None

    result = fig_payload_to_image_payload(payload)
    with _cache_lock:
        _result_cache[cache_key] = result
        trim_result_cache()

    return clone_cached_result(result)


def build_signal_payload(
    df,
    config,
    bg_image,
    translations,
    point_tooltip_builder,
    color_scale_limits,
    boundary_mask_image=None,
):
    rows = df[df["ssid"].str.lower() == config.ssid.lower()]
    rows = filter_by_band(rows, config.band)
    rows = add_ap_group_metadata(rows, config.ap_group_map, config.ap_group_roles)
    rows = rows[rows["ap_role"] != AP_ROLE_TEST]
    if config.ap_group_filter:
        rows = rows[rows["ap_group"] == config.ap_group_filter]
    raw_rows = len(rows)
    rows = collapse_heatmap_points(rows, aggregation=config.aggregation)
    rows["ssid"] = config.ssid

    if len(rows) < 3:
        return None

    x = rows["x"].values
    y = rows["y"].values
    signal = rows["signal_dbm"].values
    confidence = get_scan_confidence_values(rows)
    width, height = bg_image.size
    grid_x, grid_y = get_grid(width, height)
    grid_z = interpolate_signal_grid(
        x,
        y,
        signal,
        grid_x,
        grid_y,
        method=config.interpolation,
        confidence=confidence
    )
    grid_z = smooth_heatmap_grid(grid_z, sigma=config.smoothing_sigma)
    grid_z = apply_distance_mask(grid_z, grid_x, grid_y, x, y, max_distance_px=config.max_distance_px)
    bounds_alpha = get_continuous_bounds_alpha(
        config,
        grid_x,
        grid_y,
        x,
        y,
        boundary_mask_image=boundary_mask_image,
    )
    grid_z = apply_continuous_bounds_mask(grid_z, bounds_alpha)

    if config.usable_only:
        grid_z = apply_signal_threshold(grid_z, min_signal_dbm=-70)

    distance_alpha = get_distance_alpha(
        grid_x,
        grid_y,
        x,
        y,
        max_distance_px=config.max_distance_px,
        point_confidence=confidence
    )
    heatmap_alpha = np.where(np.isfinite(grid_z), distance_alpha * bounds_alpha * 0.55, 0)
    vmin, vmax = color_scale_limits(grid_z, config)
    scale_payload = {
        "kind": "gradient",
        "title": translations["signal_title"],
        "cmap": "RdYlGn",
        "min": vmin,
        "max": vmax,
        "suffix": " dBm",
    }
    fig, ax = create_base_figure(bg_image)
    ax.imshow(
        grid_z.T,
        extent=(0, width, height, 0),
        alpha=heatmap_alpha.T,
        cmap="RdYlGn",
        vmin=vmin,
        vmax=vmax,
        interpolation="bilinear"
    )
    point_infos = [
        {
            "x": float(row["x"]),
            "y": float(row["y"]),
            "color": "#111111",
            "outline": "white",
            "tooltip": point_tooltip_builder("signal", row, raw_rows),
        }
        for _index, row in rows.iterrows()
    ]
    return {"fig": fig, "point_infos": point_infos, "scale_payload": scale_payload}


def build_interference_payload(
    df,
    config,
    bg_image,
    translations,
    point_tooltip_builder,
    color_scale_limits,
    boundary_mask_image=None,
):
    if config.band not in {"2.4", "5", "6"}:
        return None

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
        return None

    x = risk_df["x"].values
    y = risk_df["y"].values
    risk = risk_df["risk"].values
    confidence = get_scan_confidence_values(risk_df)
    width, height = bg_image.size
    grid_x, grid_y = get_grid(width, height)
    grid_z = interpolate_signal_grid(
        x,
        y,
        risk,
        grid_x,
        grid_y,
        method=config.interpolation,
        confidence=confidence
    )
    grid_z = smooth_heatmap_grid(grid_z, sigma=config.smoothing_sigma)
    grid_z = apply_distance_mask(grid_z, grid_x, grid_y, x, y, max_distance_px=config.max_distance_px)
    bounds_alpha = get_continuous_bounds_alpha(
        config,
        grid_x,
        grid_y,
        x,
        y,
        boundary_mask_image=boundary_mask_image,
    )
    grid_z = apply_continuous_bounds_mask(grid_z, bounds_alpha)
    distance_alpha = get_distance_alpha(
        grid_x,
        grid_y,
        x,
        y,
        max_distance_px=config.max_distance_px,
        point_confidence=confidence
    )
    heatmap_alpha = np.where(np.isfinite(grid_z), distance_alpha * bounds_alpha * 0.58, 0)
    vmin, vmax = color_scale_limits(grid_z, config)
    scale_payload = {
        "kind": "gradient",
        "title": translations["interference_title"],
        "cmap": "RdYlGn_r",
        "min": vmin,
        "max": vmax,
        "suffix": "%",
    }

    fig, ax = create_base_figure(bg_image)
    ax.imshow(
        grid_z.T,
        extent=(0, width, height, 0),
        alpha=heatmap_alpha.T,
        cmap="RdYlGn_r",
        vmin=vmin,
        vmax=vmax,
        interpolation="bilinear"
    )
    point_infos = [
        {
            "x": float(row["x"]),
            "y": float(row["y"]),
            "color": get_interference_marker_color(float(row.get("risk", 0) or 0)),
            "outline": "black",
            "tooltip": point_tooltip_builder("interference", row, None),
        }
        for _index, row in risk_df.iterrows()
    ]
    return {"fig": fig, "point_infos": point_infos, "scale_payload": scale_payload}


def create_base_figure(bg_image):
    bg = np.array(bg_image)
    width, height = bg_image.size
    fig = plt.figure(figsize=(width / 120, height / 120), dpi=120)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(bg)
    ax.axis("off")
    return fig, ax


def get_grid(width, height):
    key = (width, height, HEATMAP_GRID_SIZE)
    with _cache_lock:
        cached = _grid_cache.get(key)
        if cached is not None:
            return cached

    grid = np.mgrid[0:width:complex(HEATMAP_GRID_SIZE), 0:height:complex(HEATMAP_GRID_SIZE)]
    grid_x, grid_y = grid[0], grid[1]
    with _cache_lock:
        _grid_cache[key] = (grid_x, grid_y)
    return grid_x, grid_y


def get_continuous_bounds_alpha(config, grid_x, grid_y, point_x, point_y, boundary_mask_image=None):
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


def apply_continuous_bounds_mask(grid_z, bounds_alpha):
    if bounds_alpha is None:
        return grid_z

    return np.where(bounds_alpha > 0, grid_z, np.nan)


def fig_payload_to_image_payload(payload):
    buffer = BytesIO()
    payload["fig"].savefig(buffer, format="png", dpi=120)
    plt.close(payload["fig"])
    buffer.seek(0)
    return {
        "image": Image.open(buffer).convert("RGB"),
        "point_infos": payload["point_infos"],
        "scale_payload": payload["scale_payload"],
    }


def build_result_cache_key(df, config, bg_image, translations, boundary_mask_image=None):
    return (
        bg_image.size,
        image_fingerprint(bg_image),
        tuple(sorted(translations.items())),
        len(df),
        tuple(df.columns),
        stable_dataframe_fingerprint(df),
        config.ssid.lower(),
        config.band,
        config.map_type,
        config.interference_mode,
        config.interpolation,
        config.aggregation,
        config.color_scale,
        config.ap_group_filter,
        config.ap_group_map,
        config.ap_group_roles,
        config.ap_group_channel_overrides,
        config.usable_only,
        config.survey_bounds,
        boundary_mask_fingerprint(boundary_mask_image),
        round(float(config.smoothing_sigma), 4),
        int(config.max_distance_px),
    )


def image_fingerprint(image):
    thumbnail = image.resize((16, 16), Image.Resampling.BILINEAR)
    return hash(thumbnail.tobytes())


def stable_dataframe_fingerprint(df):
    if df.empty:
        return 0

    columns = [
        column
        for column in (
            "timestamp",
            "x",
            "y",
            "ssid",
            "bssid",
            "signal_dbm",
            "channel",
            "channel_width_mhz",
            "band",
            "frequency_mhz",
            "samples_seen",
            "samples_total",
            "scan_confidence",
            "is_relevant",
        )
        if column in df.columns
    ]
    if not columns:
        return len(df)

    hashes = pd.util.hash_pandas_object(df[columns].astype(str), index=False)
    return int(hashes.sum())


def trim_result_cache():
    while len(_result_cache) > _MAX_RESULT_CACHE_ITEMS:
        oldest_key = next(iter(_result_cache))
        del _result_cache[oldest_key]


def clone_cached_result(result):
    return {
        "image": result["image"].copy(),
        "point_infos": copy.deepcopy(result["point_infos"]),
        "scale_payload": copy.deepcopy(result["scale_payload"]),
    }


def get_interference_marker_color(risk):
    if risk >= 60:
        return "#d73027"
    if risk >= 30:
        return "#fee08b"
    return "#1a9850"
