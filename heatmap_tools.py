import pandas as pd
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.interpolate import RBFInterpolator, griddata

from i18n import translate


def filter_by_band(df, band):
    if band == "all":
        return df

    channels = pd.to_numeric(df["channel"], errors="coerce")

    if band == "2.4":
        return df[(channels >= 1) & (channels <= 14)]

    if band == "5":
        return df[channels >= 36]

    return df
def collapse_heatmap_points(df, aggregation="max"):
    heatmap_df = df.copy()
    heatmap_df["x"] = pd.to_numeric(heatmap_df["x"], errors="coerce")
    heatmap_df["y"] = pd.to_numeric(heatmap_df["y"], errors="coerce")
    heatmap_df["signal_dbm"] = pd.to_numeric(heatmap_df["signal_dbm"], errors="coerce")
    heatmap_df = heatmap_df.dropna(subset=["x", "y", "signal_dbm"])

    if heatmap_df.empty:
        return heatmap_df

    aggregation_functions = {
        "max": "max",
        "mean": "mean",
        "median": "median"
    }
    aggregation_function = aggregation_functions.get(aggregation, "max")

    return (
        heatmap_df
        .groupby(["timestamp", "x", "y"], as_index=False)
        .agg({"signal_dbm": aggregation_function})
    )


def get_channel_map_points(df, ssid, band):
    rows = df[df["ssid"].str.lower() == ssid.lower()].copy()
    rows = filter_by_band(rows, band)
    rows["x"] = pd.to_numeric(rows["x"], errors="coerce")
    rows["y"] = pd.to_numeric(rows["y"], errors="coerce")
    rows["channel"] = pd.to_numeric(rows["channel"], errors="coerce")
    rows["signal_dbm"] = pd.to_numeric(rows["signal_dbm"], errors="coerce")
    if "channel_width_mhz" in rows.columns:
        rows["channel_width_mhz"] = pd.to_numeric(rows["channel_width_mhz"], errors="coerce")
    else:
        rows["channel_width_mhz"] = np.nan
    rows = rows.dropna(subset=["timestamp", "x", "y", "channel", "signal_dbm", "bssid"])

    if rows.empty:
        return rows

    strongest_indexes = rows.groupby(["timestamp", "x", "y"])["signal_dbm"].idxmax()
    return rows.loc[strongest_indexes].sort_values("timestamp")


def get_dominant_ap_points(df, ssid, band):
    rows = df[df["ssid"].str.lower() == ssid.lower()].copy()
    rows = filter_by_band(rows, band)
    rows["x"] = pd.to_numeric(rows["x"], errors="coerce")
    rows["y"] = pd.to_numeric(rows["y"], errors="coerce")
    rows["channel"] = pd.to_numeric(rows["channel"], errors="coerce")
    rows["signal_dbm"] = pd.to_numeric(rows["signal_dbm"], errors="coerce")
    if "channel_width_mhz" in rows.columns:
        rows["channel_width_mhz"] = pd.to_numeric(rows["channel_width_mhz"], errors="coerce")
    else:
        rows["channel_width_mhz"] = np.nan
    rows = rows.dropna(subset=["timestamp", "x", "y", "signal_dbm", "bssid"])
    rows["ap_group"] = rows["bssid"].apply(get_ap_group_key)

    dominant_rows = []

    for (timestamp, x, y), point_rows in rows.groupby(["timestamp", "x", "y"]):
        best_by_ap = point_rows.loc[point_rows.groupby("ap_group")["signal_dbm"].idxmax()]
        sorted_rows = best_by_ap.sort_values("signal_dbm", ascending=False)
        dominant = sorted_rows.iloc[0]
        second = sorted_rows.iloc[1] if len(sorted_rows) > 1 else None
        second_signal = second["signal_dbm"] if second is not None else np.nan
        delta_db = dominant["signal_dbm"] - second_signal if second is not None else np.nan

        dominant_rows.append({
            "timestamp": timestamp,
            "x": x,
            "y": y,
            "ssid": ssid,
            "dominant_ap_group": dominant["ap_group"],
            "dominant_bssid": dominant["bssid"],
            "dominant_signal_dbm": dominant["signal_dbm"],
            "dominant_samples_seen": clean_report_value(dominant.get("samples_seen", np.nan)),
            "dominant_samples_total": clean_report_value(dominant.get("samples_total", np.nan)),
            "dominant_scan_confidence": clean_report_value(dominant.get("scan_confidence", np.nan)),
            "dominant_channel": dominant.get("channel", np.nan),
            "dominant_channel_width_mhz": clean_report_value(dominant.get("channel_width_mhz", np.nan)),
            "second_ap_group": second["ap_group"] if second is not None else "",
            "second_bssid": second["bssid"] if second is not None else "",
            "second_signal_dbm": clean_report_value(second_signal),
            "second_samples_seen": (
                clean_report_value(second.get("samples_seen", np.nan)) if second is not None else ""
            ),
            "second_samples_total": (
                clean_report_value(second.get("samples_total", np.nan)) if second is not None else ""
            ),
            "second_scan_confidence": (
                clean_report_value(second.get("scan_confidence", np.nan)) if second is not None else ""
            ),
            "second_channel": clean_report_value(second.get("channel", np.nan)) if second is not None else "",
            "second_channel_width_mhz": (
                clean_report_value(second.get("channel_width_mhz", np.nan)) if second is not None else ""
            ),
            "delta_db": clean_report_value(delta_db),
            "roaming_overlap": bool(second is not None and delta_db <= 5)
        })

    return pd.DataFrame(dominant_rows).sort_values("timestamp") if dominant_rows else pd.DataFrame()


def get_ap_group_key(bssid):
    parts = str(bssid or "").lower().split(":")

    if len(parts) == 6:
        return ":".join(parts[:5])

    return str(bssid or "").lower()


def calculate_interference_points(df, ssid, band, mode="intra_ssid", include_details=False):
    rows = df.copy()
    rows["x"] = pd.to_numeric(rows["x"], errors="coerce")
    rows["y"] = pd.to_numeric(rows["y"], errors="coerce")
    rows["channel"] = pd.to_numeric(rows["channel"], errors="coerce")
    if "channel_width_mhz" in rows.columns:
        rows["channel_width_mhz"] = pd.to_numeric(rows["channel_width_mhz"], errors="coerce")
    else:
        rows["channel_width_mhz"] = np.nan
    rows["signal_dbm"] = pd.to_numeric(rows["signal_dbm"], errors="coerce")
    rows = rows.dropna(subset=["timestamp", "x", "y", "channel", "signal_dbm", "ssid", "bssid"])
    rows["ap_group"] = rows["bssid"].apply(get_ap_group_key)

    if band not in {"2.4", "5"}:
        return pd.DataFrame(columns=["timestamp", "x", "y", "risk"])

    rows = filter_by_band(rows, band)

    if rows.empty:
        return pd.DataFrame(columns=["timestamp", "x", "y", "risk"])

    risk_rows = []

    for (timestamp, x, y), point_rows in rows.groupby(["timestamp", "x", "y"]):
        selected_rows = point_rows[point_rows["ssid"].str.lower() == ssid.lower()]

        if selected_rows.empty:
            continue

        serving_ap = selected_rows.loc[selected_rows["signal_dbm"].idxmax()]
        serving_channel = serving_ap["channel"]
        serving_channel_width = serving_ap.get("channel_width_mhz", np.nan)
        serving_ap_group = serving_ap.get("ap_group", "")

        if mode == "intra_ssid":
            candidate_rows = selected_rows
        else:
            candidate_rows = point_rows

        risk = 0.0
        interferers = []
        same_physical_ap_ignored_count = 0

        for _index, candidate in candidate_rows.iterrows():
            if candidate["bssid"] == serving_ap["bssid"]:
                continue
            if candidate.get("ap_group", "") == serving_ap_group:
                same_physical_ap_ignored_count += 1
                continue

            overlap = channel_overlap_weight(
                serving_channel,
                candidate["channel"],
                band,
                serving_channel_width,
                candidate.get("channel_width_mhz", np.nan)
            )
            signal_weight = signal_interference_weight(candidate["signal_dbm"])
            contribution = overlap * signal_weight
            risk += contribution

            if contribution > 0:
                interferers.append({
                    "ssid": candidate["ssid"],
                    "bssid": candidate["bssid"],
                    "ap_group": candidate.get("ap_group", ""),
                    "channel": candidate["channel"],
                    "channel_width_mhz": candidate.get("channel_width_mhz", np.nan),
                    "signal_dbm": candidate["signal_dbm"],
                    "samples_seen": candidate.get("samples_seen", np.nan),
                    "samples_total": candidate.get("samples_total", np.nan),
                    "scan_confidence": candidate.get("scan_confidence", np.nan),
                    "overlap_weight": overlap,
                    "signal_weight": signal_weight,
                    "contribution": contribution
                })

        risk_score = min(100.0, risk * 100)
        risk_row = {
            "timestamp": timestamp,
            "x": x,
            "y": y,
            "risk": risk_score
        }

        if include_details:
            strongest_interferer = get_strongest_interferer(interferers)
            risk_row.update({
                "ssid": ssid,
                "serving_ap_group": serving_ap_group,
                "serving_bssid": serving_ap["bssid"],
                "serving_channel": serving_channel,
                "serving_channel_width_mhz": clean_report_value(serving_channel_width),
                "serving_signal_dbm": serving_ap["signal_dbm"],
                "serving_samples_seen": clean_report_value(serving_ap.get("samples_seen", np.nan)),
                "serving_samples_total": clean_report_value(serving_ap.get("samples_total", np.nan)),
                "serving_scan_confidence": clean_report_value(serving_ap.get("scan_confidence", np.nan)),
                "interferer_count": len(interferers),
                "same_physical_ap_ignored_count": same_physical_ap_ignored_count,
                "interfering_bssids": "; ".join(interferer["bssid"] for interferer in interferers),
                "strongest_interferer_ssid": strongest_interferer.get("ssid", ""),
                "strongest_interferer_ap_group": strongest_interferer.get("ap_group", ""),
                "strongest_interferer_bssid": strongest_interferer.get("bssid", ""),
                "strongest_interferer_channel": strongest_interferer.get("channel", ""),
                "strongest_interferer_channel_width_mhz": clean_report_value(
                    strongest_interferer.get("channel_width_mhz", "")
                ),
                "strongest_interferer_dbm": strongest_interferer.get("signal_dbm", ""),
                "strongest_interferer_samples_seen": clean_report_value(
                    strongest_interferer.get("samples_seen", "")
                ),
                "strongest_interferer_samples_total": clean_report_value(
                    strongest_interferer.get("samples_total", "")
                ),
                "strongest_interferer_scan_confidence": clean_report_value(
                    strongest_interferer.get("scan_confidence", "")
                ),
                "strongest_interferer_overlap": strongest_interferer.get("overlap_weight", ""),
            })

        risk_rows.append(risk_row)

    return pd.DataFrame(risk_rows)


def get_interference_data_quality(risk_df):
    columns = [
        column
        for column in ("serving_channel_width_mhz", "strongest_interferer_channel_width_mhz")
        if column in risk_df.columns
    ]

    if not columns:
        return {"available": 0, "total": len(risk_df), "percent": 0}

    width_data = risk_df[columns].replace("", np.nan)
    rows_with_width = width_data.notna().any(axis=1).sum()
    total = len(risk_df)
    percent = round((rows_with_width / total) * 100) if total else 0

    return {"available": int(rows_with_width), "total": int(total), "percent": int(percent)}


def clean_report_value(value):
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass

    return value


def get_strongest_interferer(interferers):
    if not interferers:
        return {}

    return max(interferers, key=lambda interferer: interferer["contribution"])


def channel_overlap_weight(base_channel, other_channel, band, base_width_mhz=None, other_width_mhz=None):
    try:
        channel_distance = abs(float(base_channel) - float(other_channel))
    except (TypeError, ValueError):
        return 0

    if band == "2.4":
        if channel_distance == 0:
            return 1.0
        if channel_distance == 1:
            return 0.8
        if channel_distance == 2:
            return 0.6
        if channel_distance == 3:
            return 0.35
        if channel_distance == 4:
            return 0.15
        return 0

    if band == "5":
        width_overlap = channel_width_overlap_weight(
            base_channel,
            other_channel,
            base_width_mhz,
            other_width_mhz
        )
        if width_overlap is not None:
            return width_overlap

        return 1.0 if channel_distance == 0 else 0

    return 0


def channel_width_overlap_weight(base_channel, other_channel, base_width_mhz, other_width_mhz):
    base_width = normalize_width_mhz(base_width_mhz)
    other_width = normalize_width_mhz(other_width_mhz)

    if not base_width or not other_width:
        return None

    try:
        base_frequency = 5000 + (float(base_channel) * 5)
        other_frequency = 5000 + (float(other_channel) * 5)
    except (TypeError, ValueError):
        return None

    distance_mhz = abs(base_frequency - other_frequency)
    half_sum = (base_width / 2) + (other_width / 2)
    overlap_mhz = max(0.0, half_sum - distance_mhz)

    if overlap_mhz <= 0:
        return 0.0

    return min(1.0, overlap_mhz / min(base_width, other_width))


def normalize_width_mhz(value):
    try:
        width = float(value)
    except (TypeError, ValueError):
        return None

    if np.isnan(width) or width <= 0:
        return None

    return width


def signal_interference_weight(signal_dbm):
    try:
        signal_dbm = float(signal_dbm)
    except (TypeError, ValueError):
        return 0

    if signal_dbm >= -60:
        return 1.0
    if signal_dbm >= -67:
        return 0.7
    if signal_dbm >= -75:
        return 0.4
    if signal_dbm >= -85:
        return 0.15
    if signal_dbm >= -90:
        return 0.05
    return 0
def format_band_label(band, language="it"):
    if band == "2.4":
        return "2.4 GHz"

    if band == "5":
        return "5 GHz"

    return translate(language, "all_bands_label")
def smooth_heatmap_grid(grid_z, sigma):
    valid_mask = np.isfinite(grid_z)

    if not valid_mask.any():
        return grid_z

    filled_grid = np.where(valid_mask, grid_z, 0)
    smoothed_values = gaussian_filter(filled_grid, sigma=sigma)
    smoothed_weights = gaussian_filter(valid_mask.astype(float), sigma=sigma)

    with np.errstate(invalid="ignore", divide="ignore"):
        smoothed_grid = smoothed_values / smoothed_weights

    smoothed_grid[smoothed_weights <= 0.01] = np.nan
    return smoothed_grid


def interpolate_signal_grid(x, y, signal, grid_x, grid_y, method="rbf"):
    if method == "linear":
        return griddata(
            points=(x, y),
            values=signal,
            xi=(grid_x, grid_y),
            method="linear"
        )

    points = np.column_stack([x, y])
    grid_points = np.column_stack([grid_x.ravel(), grid_y.ravel()])

    try:
        interpolator = RBFInterpolator(
            points,
            signal,
            kernel="thin_plate_spline",
            smoothing=4.0
        )
        return interpolator(grid_points).reshape(grid_x.shape)
    except Exception:
        return griddata(
            points=(x, y),
            values=signal,
            xi=(grid_x, grid_y),
            method="linear"
        )


def get_distance_alpha(grid_x, grid_y, point_x, point_y, max_distance_px, fade_ratio=0.25):
    min_distance_sq = np.full(grid_x.shape, np.inf)

    for x, y in zip(point_x, point_y):
        distance_sq = (grid_x - x) ** 2 + (grid_y - y) ** 2
        min_distance_sq = np.minimum(min_distance_sq, distance_sq)

    min_distance = np.sqrt(min_distance_sq)
    fade_width = max(1, max_distance_px * fade_ratio)
    fade_start = max(0, max_distance_px - fade_width)
    alpha = np.ones(grid_x.shape)
    fade_zone = min_distance > fade_start

    alpha[fade_zone] = 1 - ((min_distance[fade_zone] - fade_start) / fade_width)
    alpha[min_distance > max_distance_px] = 0
    return np.clip(alpha, 0, 1)


def apply_distance_mask(grid_z, grid_x, grid_y, point_x, point_y, max_distance_px):
    min_distance_sq = np.full(grid_z.shape, np.inf)

    for x, y in zip(point_x, point_y):
        distance_sq = (grid_x - x) ** 2 + (grid_y - y) ** 2
        min_distance_sq = np.minimum(min_distance_sq, distance_sq)

    masked_grid = grid_z.copy()
    masked_grid[min_distance_sq > max_distance_px ** 2] = np.nan
    return masked_grid
def apply_signal_threshold(grid_z, min_signal_dbm):
    threshold_grid = grid_z.copy()
    threshold_grid[threshold_grid < min_signal_dbm] = np.nan
    return threshold_grid
