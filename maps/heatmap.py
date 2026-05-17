"""Data preparation and numerical map-generation helpers."""

import pandas as pd
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.interpolate import RBFInterpolator, griddata
from scipy.spatial import Delaunay, QhullError

from ap.checks import AP_CHANNEL_CHANGE_CLEAN, build_ap_channel_changes
from ap.groups import (
    AP_ROLE_INTERNAL,
    AP_ROLE_TEST,
    normalize_ap_group_channel_overrides,
    normalize_ap_group_map,
    normalize_ap_role_map,
    resolve_ap_group_key,
)
from translations.i18n import translate
from wifi.band import channel_center_frequency_mhz, get_row_band, normalize_band


def filter_by_band(df, band):
    normalized_band = normalize_band(band)
    if not normalized_band:
        return df

    if df.empty:
        return df

    return df[df.apply(lambda row: get_row_band(row) == normalized_band, axis=1)]


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

    aggregation_spec = {"signal_dbm": aggregation_function}
    optional_aggregations = {
        "scan_confidence": "mean",
        "samples_seen": "max",
        "samples_total": "max",
    }

    for column, function in optional_aggregations.items():
        if column in heatmap_df.columns:
            heatmap_df[column] = pd.to_numeric(heatmap_df[column], errors="coerce")
            aggregation_spec[column] = function

    return (
        heatmap_df
        .groupby(["timestamp", "x", "y"], as_index=False)
        .agg(aggregation_spec)
    )


def get_channel_map_points(
    df,
    ssid,
    band,
    ap_group_map=None,
    ap_group_roles=None,
    ap_group_filter=None,
    ap_group_channel_overrides=None,
):
    rows = df.copy()
    rows["x"] = pd.to_numeric(rows["x"], errors="coerce")
    rows["y"] = pd.to_numeric(rows["y"], errors="coerce")
    rows["channel"] = pd.to_numeric(rows["channel"], errors="coerce")
    rows["band"] = rows.apply(get_row_band, axis=1)
    rows["signal_dbm"] = pd.to_numeric(rows["signal_dbm"], errors="coerce")
    if "channel_width_mhz" in rows.columns:
        rows["channel_width_mhz"] = pd.to_numeric(rows["channel_width_mhz"], errors="coerce")
    else:
        rows["channel_width_mhz"] = np.nan
    rows = rows.dropna(subset=["timestamp", "x", "y", "channel", "signal_dbm", "ssid", "bssid"])

    if rows.empty:
        return rows

    rows = add_ap_group_metadata(rows, ap_group_map, ap_group_roles)
    rows = rows[rows["ap_role"] != AP_ROLE_TEST]
    rows, _channel_changes = apply_ap_channel_analysis_overrides(rows, ap_group_channel_overrides)
    rows = filter_by_band(rows, band)
    rows = rows[rows["ssid"].astype(str).str.lower() == ssid.lower()]
    if ap_group_filter:
        rows = rows[rows["ap_group"] == str(ap_group_filter)]
    if rows.empty:
        return rows

    strongest_indexes = rows.groupby(["timestamp", "x", "y"])["signal_dbm"].idxmax()
    return rows.loc[strongest_indexes].sort_values("timestamp")


def get_dominant_ap_points(df, ssid, band, ap_group_map=None, ap_group_roles=None):
    rows = df[df["ssid"].str.lower() == ssid.lower()].copy()
    rows = filter_by_band(rows, band)
    rows["x"] = pd.to_numeric(rows["x"], errors="coerce")
    rows["y"] = pd.to_numeric(rows["y"], errors="coerce")
    rows["channel"] = pd.to_numeric(rows["channel"], errors="coerce")
    rows["band"] = rows.apply(get_row_band, axis=1)
    rows["signal_dbm"] = pd.to_numeric(rows["signal_dbm"], errors="coerce")
    if "channel_width_mhz" in rows.columns:
        rows["channel_width_mhz"] = pd.to_numeric(rows["channel_width_mhz"], errors="coerce")
    else:
        rows["channel_width_mhz"] = np.nan
    rows = rows.dropna(subset=["timestamp", "x", "y", "signal_dbm", "bssid"])
    rows = add_ap_group_metadata(rows, ap_group_map, ap_group_roles)
    rows = rows[rows["ap_role"] != AP_ROLE_TEST]
    if rows.empty:
        return pd.DataFrame()

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
            "dominant_ap_role": dominant.get("ap_role", AP_ROLE_INTERNAL),
            "dominant_bssid": dominant["bssid"],
            "dominant_signal_dbm": dominant["signal_dbm"],
            "dominant_samples_seen": clean_report_value(dominant.get("samples_seen", np.nan)),
            "dominant_samples_total": clean_report_value(dominant.get("samples_total", np.nan)),
            "dominant_scan_confidence": clean_report_value(dominant.get("scan_confidence", np.nan)),
            "dominant_channel": dominant.get("channel", np.nan),
            "dominant_channel_width_mhz": clean_report_value(dominant.get("channel_width_mhz", np.nan)),
            "dominant_band": dominant.get("band", ""),
            "second_ap_group": second["ap_group"] if second is not None else "",
            "second_ap_role": second.get("ap_role", "") if second is not None else "",
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
            "second_band": second.get("band", "") if second is not None else "",
            "delta_db": clean_report_value(delta_db),
            "roaming_overlap": bool(second is not None and delta_db <= 5)
        })

    return pd.DataFrame(dominant_rows).sort_values("timestamp") if dominant_rows else pd.DataFrame()


def add_ap_group_metadata(rows, ap_group_map=None, ap_group_roles=None):
    group_map = normalize_ap_group_map(ap_group_map)
    role_map = normalize_ap_role_map(ap_group_roles)
    rows = rows.copy()
    rows["ap_group"] = rows["bssid"].apply(lambda bssid: resolve_ap_group_key(bssid, group_map))
    rows["ap_role"] = rows["ap_group"].apply(lambda group: role_map.get(str(group), AP_ROLE_INTERNAL))
    return rows


def apply_ap_channel_analysis_overrides(rows, ap_group_channel_overrides=None):
    rows = rows.copy()
    rows["channel_original"] = rows["channel"]
    rows["channel_adjusted_for_change"] = False
    rows["channel_change_status"] = ""
    rows["channel_change_source"] = ""
    rows["channel_change_current_channel"] = ""
    rows["channel_change_previous_channels"] = ""
    rows["channel_change_observed_channels"] = ""

    channel_changes = build_ap_channel_changes(rows.to_dict("records"))
    channel_changes_by_key = {
        (str(change.get("group_id", "")), str(change.get("band", ""))): change
        for change in channel_changes
    }
    manual_overrides = normalize_ap_group_channel_overrides(ap_group_channel_overrides)
    handled_keys = set()

    for (group_id, band), channel in manual_overrides.items():
        mask = (rows["ap_group"].astype(str) == group_id) & (rows["band"].astype(str) == band)
        if not mask.any():
            continue

        change = channel_changes_by_key.get((group_id, band), {})
        observed_channels = change.get("channels") or observed_channels_for_rows(rows, mask)
        previous_channels = [item for item in observed_channels if item != channel]
        apply_channel_analysis_choice(
            rows,
            mask,
            channel,
            status=change.get("status", "manual") or "manual",
            source="manual",
            previous_channels=previous_channels,
            observed_channels=observed_channels,
        )
        handled_keys.add((group_id, band))

    clean_changes = [
        change
        for change in channel_changes
        if change.get("status") == AP_CHANNEL_CHANGE_CLEAN and change.get("current_channel")
    ]
    if not clean_changes:
        return rows, channel_changes

    for change in clean_changes:
        group_id = str(change.get("group_id", ""))
        band = str(change.get("band", ""))
        if (group_id, band) in handled_keys:
            continue

        current_channel = str(change.get("current_channel", ""))

        mask = (rows["ap_group"].astype(str) == group_id) & (rows["band"].astype(str) == band)
        if not mask.any():
            continue

        apply_channel_analysis_choice(
            rows,
            mask,
            current_channel,
            status=AP_CHANNEL_CHANGE_CLEAN,
            source="latest",
            previous_channels=change.get("previous_channels", []),
            observed_channels=change.get("channels", []),
        )

    return rows, channel_changes


def apply_clean_ap_channel_change_overrides(rows):
    return apply_ap_channel_analysis_overrides(rows)


def apply_channel_analysis_choice(rows, mask, channel, status, source, previous_channels, observed_channels):
    try:
        channel_value = float(channel)
    except (TypeError, ValueError):
        return

    matching_original_channel = rows["channel"].apply(format_channel_key) == str(channel)
    final_width = rows.loc[mask & matching_original_channel, "channel_width_mhz"].dropna()
    if not final_width.empty:
        rows.loc[mask, "channel_width_mhz"] = final_width.iloc[-1]

    rows.loc[mask, "channel_change_status"] = status
    rows.loc[mask, "channel_change_source"] = source
    rows.loc[mask, "channel_change_current_channel"] = str(channel)
    rows.loc[mask, "channel_change_previous_channels"] = ", ".join(str(item) for item in previous_channels if str(item))
    rows.loc[mask, "channel_change_observed_channels"] = ", ".join(str(item) for item in observed_channels if str(item))
    rows.loc[mask & (rows["channel"] != channel_value), "channel_adjusted_for_change"] = True
    rows.loc[mask, "channel"] = channel_value


def observed_channels_for_rows(rows, mask):
    return sorted(
        {
            format_channel_key(channel)
            for channel in rows.loc[mask, "channel"].dropna()
            if format_channel_key(channel)
        },
        key=numeric_channel_sort_key,
    )


def format_channel_key(channel):
    try:
        number = float(channel)
    except (TypeError, ValueError):
        return str(channel or "").strip()

    if pd.isna(number):
        return ""
    return str(int(number)) if number.is_integer() else str(number)


def numeric_channel_sort_key(channel):
    try:
        return int(float(channel))
    except (TypeError, ValueError):
        return 9999


def calculate_interference_points(
    df,
    ssid,
    band,
    mode="intra_ssid",
    include_details=False,
    ap_group_map=None,
    ap_group_roles=None,
    ap_group_channel_overrides=None,
):
    band = normalize_band(band)
    rows = df.copy()
    rows["x"] = pd.to_numeric(rows["x"], errors="coerce")
    rows["y"] = pd.to_numeric(rows["y"], errors="coerce")
    rows["channel"] = pd.to_numeric(rows["channel"], errors="coerce")
    rows["band"] = rows.apply(get_row_band, axis=1)
    if "channel_width_mhz" in rows.columns:
        rows["channel_width_mhz"] = pd.to_numeric(rows["channel_width_mhz"], errors="coerce")
    else:
        rows["channel_width_mhz"] = np.nan
    rows["signal_dbm"] = pd.to_numeric(rows["signal_dbm"], errors="coerce")
    rows = rows.dropna(subset=["timestamp", "x", "y", "channel", "signal_dbm", "ssid", "bssid"])
    rows = add_ap_group_metadata(rows, ap_group_map, ap_group_roles)
    rows, channel_changes = apply_ap_channel_analysis_overrides(rows, ap_group_channel_overrides)

    if band not in {"2.4", "5", "6"}:
        return pd.DataFrame(columns=["timestamp", "x", "y", "risk"])

    rows = filter_by_band(rows, band)

    if rows.empty:
        return pd.DataFrame(columns=["timestamp", "x", "y", "risk"])

    risk_rows = []

    for (timestamp, x, y), point_rows in rows.groupby(["timestamp", "x", "y"]):
        selected_test_rows = point_rows[
            (point_rows["ssid"].str.lower() == ssid.lower())
            & (point_rows["ap_role"] == AP_ROLE_TEST)
        ]
        selected_rows = point_rows[
            (point_rows["ssid"].str.lower() == ssid.lower())
            & (point_rows["ap_role"] != AP_ROLE_TEST)
        ]

        if selected_rows.empty:
            continue

        serving_ap = selected_rows.loc[selected_rows["signal_dbm"].idxmax()]
        serving_channel = serving_ap["channel"]
        serving_channel_width = serving_ap.get("channel_width_mhz", np.nan)
        serving_ap_group = serving_ap.get("ap_group", "")
        serving_ap_role = serving_ap.get("ap_role", AP_ROLE_INTERNAL)

        if mode == "intra_ssid":
            candidate_rows = selected_rows
        else:
            candidate_rows = point_rows

        risk = 0.0
        interferers = []
        same_physical_ap_ignored_count = 0
        test_ap_ignored_count = len(selected_test_rows) if mode == "intra_ssid" else 0

        for _index, candidate in candidate_rows.iterrows():
            if candidate["bssid"] == serving_ap["bssid"]:
                continue
            if candidate.get("ap_group", "") == serving_ap_group:
                same_physical_ap_ignored_count += 1
                continue
            candidate_role = candidate.get("ap_role", AP_ROLE_INTERNAL)
            if candidate_role == AP_ROLE_TEST:
                test_ap_ignored_count += 1
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
                    "ap_role": candidate_role,
                    "channel": candidate["channel"],
                    "channel_original": candidate.get("channel_original", ""),
                    "channel_adjusted_for_change": bool(candidate.get("channel_adjusted_for_change", False)),
                    "channel_change_status": candidate.get("channel_change_status", ""),
                    "channel_change_source": candidate.get("channel_change_source", ""),
                    "channel_change_current_channel": candidate.get("channel_change_current_channel", ""),
                    "channel_change_previous_channels": candidate.get("channel_change_previous_channels", ""),
                    "channel_change_observed_channels": candidate.get("channel_change_observed_channels", ""),
                    "channel_width_mhz": candidate.get("channel_width_mhz", np.nan),
                    "band": candidate.get("band", ""),
                    "signal_dbm": candidate["signal_dbm"],
                    "samples_seen": candidate.get("samples_seen", np.nan),
                    "samples_total": candidate.get("samples_total", np.nan),
                    "scan_confidence": candidate.get("scan_confidence", np.nan),
                    "overlap_weight": overlap,
                    "signal_weight": signal_weight,
                    "contribution": contribution
                })

        risk_score = min(100.0, risk * 100)
        strongest_interferer = get_strongest_interferer(interferers)
        risk_row = {
            "timestamp": timestamp,
            "x": x,
            "y": y,
            "risk": risk_score,
            "scan_confidence": get_interference_confidence(serving_ap, strongest_interferer),
        }

        if include_details:
            risk_row.update({
                "ssid": ssid,
                "serving_ap_group": serving_ap_group,
                "serving_ap_role": serving_ap_role,
                "serving_bssid": serving_ap["bssid"],
                "serving_channel": serving_channel,
                "serving_channel_original": clean_report_value(serving_ap.get("channel_original", "")),
                "serving_channel_adjusted_for_change": bool(
                    serving_ap.get("channel_adjusted_for_change", False)
                ),
                "serving_channel_change_status": serving_ap.get("channel_change_status", ""),
                "serving_channel_change_source": serving_ap.get("channel_change_source", ""),
                "serving_channel_change_current_channel": serving_ap.get("channel_change_current_channel", ""),
                "serving_channel_change_previous_channels": serving_ap.get("channel_change_previous_channels", ""),
                "serving_channel_change_observed_channels": serving_ap.get("channel_change_observed_channels", ""),
                "serving_channel_width_mhz": clean_report_value(serving_channel_width),
                "serving_band": serving_ap.get("band", ""),
                "serving_signal_dbm": serving_ap["signal_dbm"],
                "serving_samples_seen": clean_report_value(serving_ap.get("samples_seen", np.nan)),
                "serving_samples_total": clean_report_value(serving_ap.get("samples_total", np.nan)),
                "serving_scan_confidence": clean_report_value(serving_ap.get("scan_confidence", np.nan)),
                "interferer_count": len(interferers),
                "same_physical_ap_ignored_count": same_physical_ap_ignored_count,
                "test_ap_ignored_count": test_ap_ignored_count,
                "interfering_bssids": "; ".join(interferer["bssid"] for interferer in interferers),
                "strongest_interferer_ssid": strongest_interferer.get("ssid", ""),
                "strongest_interferer_ap_group": strongest_interferer.get("ap_group", ""),
                "strongest_interferer_ap_role": strongest_interferer.get("ap_role", ""),
                "strongest_interferer_bssid": strongest_interferer.get("bssid", ""),
                "strongest_interferer_channel": strongest_interferer.get("channel", ""),
                "strongest_interferer_channel_original": clean_report_value(
                    strongest_interferer.get("channel_original", "")
                ),
                "strongest_interferer_channel_adjusted_for_change": bool(
                    strongest_interferer.get("channel_adjusted_for_change", False)
                ),
                "strongest_interferer_channel_change_status": strongest_interferer.get("channel_change_status", ""),
                "strongest_interferer_channel_change_source": strongest_interferer.get("channel_change_source", ""),
                "strongest_interferer_channel_change_current_channel": strongest_interferer.get(
                    "channel_change_current_channel", ""
                ),
                "strongest_interferer_channel_change_previous_channels": strongest_interferer.get(
                    "channel_change_previous_channels", ""
                ),
                "strongest_interferer_channel_change_observed_channels": strongest_interferer.get(
                    "channel_change_observed_channels", ""
                ),
                "strongest_interferer_channel_width_mhz": clean_report_value(
                    strongest_interferer.get("channel_width_mhz", "")
                ),
                "strongest_interferer_band": strongest_interferer.get("band", ""),
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

    return max(
        interferers,
        key=lambda interferer: (
            interferer.get("contribution", 0),
            parse_signal_dbm(interferer.get("signal_dbm")),
        ),
    )


def parse_signal_dbm(value):
    try:
        signal = float(value)
    except (TypeError, ValueError):
        return float("-inf")

    if np.isnan(signal):
        return float("-inf")

    return signal


def get_interference_confidence(serving_ap, strongest_interferer):
    confidence_values = [parse_scan_confidence(serving_ap.get("scan_confidence", 1.0))]

    if strongest_interferer:
        confidence_values.append(parse_scan_confidence(strongest_interferer.get("scan_confidence", 1.0)))

    return round(min(confidence_values), 3)


def parse_scan_confidence(value, default=1.0):
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return default

    if np.isnan(confidence):
        return default

    return float(np.clip(confidence, 0.05, 1.0))


def channel_overlap_weight(base_channel, other_channel, band, base_width_mhz=None, other_width_mhz=None):
    band = normalize_band(band)
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

    if band in {"5", "6"}:
        width_overlap = channel_width_overlap_weight(
            base_channel,
            other_channel,
            base_width_mhz,
            other_width_mhz,
            band=band,
        )
        if width_overlap is not None:
            return width_overlap

        return 1.0 if channel_distance == 0 else 0

    return 0


def channel_width_overlap_weight(base_channel, other_channel, base_width_mhz, other_width_mhz, band="5"):
    base_width = normalize_width_mhz(base_width_mhz)
    other_width = normalize_width_mhz(other_width_mhz)

    if not base_width or not other_width:
        return None

    base_range = get_channel_frequency_range(base_channel, base_width, band)
    other_range = get_channel_frequency_range(other_channel, other_width, band)
    if not base_range or not other_range:
        return None

    overlap_mhz = min(base_range[1], other_range[1]) - max(base_range[0], other_range[0])

    if overlap_mhz <= 0:
        return 0.0

    return min(1.0, overlap_mhz / min(base_width, other_width))


def get_channel_frequency_range(channel, width_mhz, band="5"):
    if band == "6":
        return get_6ghz_channel_frequency_range(channel, width_mhz)

    return get_5ghz_channel_frequency_range(channel, width_mhz)


def get_5ghz_channel_frequency_range(channel, width_mhz):
    try:
        primary_channel = int(float(channel))
    except (TypeError, ValueError):
        return None

    width = int(round(width_mhz))
    if width <= 20:
        return channel_group_frequency_range([primary_channel])

    for group in get_5ghz_channel_groups(width):
        if primary_channel in group:
            return channel_group_frequency_range(group)

    return None


def get_6ghz_channel_frequency_range(channel, width_mhz):
    try:
        primary_channel = int(float(channel))
    except (TypeError, ValueError):
        return None

    width = int(round(width_mhz))
    if width <= 20:
        center = channel_center_frequency_mhz(primary_channel, "6")
        if center is None:
            return None
        return center - 10, center + 10

    for group in get_6ghz_channel_groups(width):
        if primary_channel in group:
            return channel_group_frequency_range(group, band="6")

    return None


def get_6ghz_channel_groups(width_mhz):
    base_channels = list(range(1, 234, 4))
    if width_mhz <= 40:
        group_size = 2
    elif width_mhz <= 80:
        group_size = 4
    elif width_mhz <= 160:
        group_size = 8
    else:
        group_size = 16

    return [
        base_channels[index:index + group_size]
        for index in range(0, len(base_channels), group_size)
        if len(base_channels[index:index + group_size]) == group_size
    ]


def get_5ghz_channel_groups(width_mhz):
    if width_mhz <= 40:
        return [
            [36, 40], [44, 48],
            [52, 56], [60, 64],
            [100, 104], [108, 112], [116, 120], [124, 128],
            [132, 136], [140, 144],
            [149, 153], [157, 161],
            [165, 169], [173, 177],
        ]

    if width_mhz <= 80:
        return [
            [36, 40, 44, 48],
            [52, 56, 60, 64],
            [100, 104, 108, 112],
            [116, 120, 124, 128],
            [132, 136, 140, 144],
            [149, 153, 157, 161],
        ]

    return [
        [36, 40, 44, 48, 52, 56, 60, 64],
        [100, 104, 108, 112, 116, 120, 124, 128],
    ]


def channel_group_frequency_range(channels, band="5"):
    centers = [
        channel_center_frequency_mhz(channel, band)
        for channel in channels
    ]
    centers = [center for center in centers if center is not None]
    if not centers:
        return None

    return min(centers) - 10, max(centers) + 10


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
    band = normalize_band(band)
    if band == "2.4":
        return "2.4 GHz"

    if band == "5":
        return "5 GHz"

    if band == "6":
        return "6 GHz"

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


def get_scan_confidence_values(rows, default=1.0):
    if rows is None or len(rows) == 0:
        return np.array([], dtype=float)

    if not hasattr(rows, "columns") or "scan_confidence" not in rows.columns:
        return np.full(len(rows), default, dtype=float)

    values = pd.to_numeric(rows["scan_confidence"], errors="coerce").fillna(default).to_numpy(dtype=float)
    return np.clip(values, 0.05, 1.0)


def normalize_confidence_array(confidence, expected_length):
    if confidence is None:
        return None

    values = np.asarray(confidence, dtype=float)
    if values.size != expected_length:
        return None

    values = np.where(np.isfinite(values), values, 1.0)
    return np.clip(values, 0.05, 1.0)


def get_confidence_rbf_smoothing(confidence, point_count, base_smoothing=4.0):
    values = normalize_confidence_array(confidence, point_count)
    if values is None:
        return base_smoothing

    return base_smoothing + ((1.0 - values) ** 2 * 24.0)


def interpolate_signal_grid(x, y, signal, grid_x, grid_y, method="rbf", confidence=None):
    points = np.column_stack([x, y])
    if len(points) < 3:
        return interpolate_nearest_grid(x, y, signal, grid_x, grid_y)

    if method == "linear":
        return interpolate_linear_grid(x, y, signal, grid_x, grid_y)

    grid_points = np.column_stack([grid_x.ravel(), grid_y.ravel()])

    try:
        interpolator = RBFInterpolator(
            points,
            signal,
            kernel="thin_plate_spline",
            smoothing=get_confidence_rbf_smoothing(confidence, len(points))
        )
        return interpolator(grid_points).reshape(grid_x.shape)
    except Exception:
        return interpolate_linear_grid(x, y, signal, grid_x, grid_y)


def interpolate_linear_grid(x, y, signal, grid_x, grid_y):
    try:
        return griddata(
            points=(x, y),
            values=signal,
            xi=(grid_x, grid_y),
            method="linear"
        )
    except Exception:
        return interpolate_nearest_grid(x, y, signal, grid_x, grid_y)


def interpolate_nearest_grid(x, y, signal, grid_x, grid_y):
    return griddata(
        points=(x, y),
        values=signal,
        xi=(grid_x, grid_y),
        method="nearest"
    )


def get_distance_alpha(
    grid_x,
    grid_y,
    point_x,
    point_y,
    max_distance_px,
    fade_ratio=0.25,
    point_confidence=None,
    min_confidence_alpha=0.45
):
    min_distance_sq = np.full(grid_x.shape, np.inf)
    confidence = normalize_confidence_array(point_confidence, len(point_x))
    nearest_confidence = np.ones(grid_x.shape) if confidence is not None else None

    for index, (x, y) in enumerate(zip(point_x, point_y)):
        distance_sq = (grid_x - x) ** 2 + (grid_y - y) ** 2
        nearest_mask = distance_sq < min_distance_sq
        min_distance_sq[nearest_mask] = distance_sq[nearest_mask]
        if nearest_confidence is not None:
            nearest_confidence[nearest_mask] = confidence[index]

    min_distance = np.sqrt(min_distance_sq)
    fade_width = max(1, max_distance_px * fade_ratio)
    fade_start = max(0, max_distance_px - fade_width)
    alpha = np.ones(grid_x.shape)
    fade_zone = min_distance > fade_start

    alpha[fade_zone] = 1 - ((min_distance[fade_zone] - fade_start) / fade_width)
    alpha[min_distance > max_distance_px] = 0

    if nearest_confidence is not None:
        nearest_confidence = smooth_confidence_surface(
            nearest_confidence,
            grid_x,
            grid_y,
            max_distance_px,
        )
        confidence_alpha = min_confidence_alpha + ((1 - min_confidence_alpha) * nearest_confidence)
        alpha *= confidence_alpha

    return np.clip(alpha, 0, 1)


def smooth_confidence_surface(confidence_grid, grid_x, grid_y, max_distance_px):
    cell_size_px = get_grid_cell_size_px(grid_x, grid_y)
    sigma_cells = max(1.0, (max_distance_px * 0.25) / cell_size_px)
    return gaussian_filter(confidence_grid, sigma=sigma_cells)


def get_grid_cell_size_px(grid_x, grid_y):
    steps = []

    if grid_x.shape[0] > 1:
        x_steps = np.abs(np.diff(grid_x[:, 0]))
        x_steps = x_steps[np.isfinite(x_steps) & (x_steps > 0)]
        if x_steps.size:
            steps.append(float(np.median(x_steps)))

    if grid_y.shape[1] > 1:
        y_steps = np.abs(np.diff(grid_y[0, :]))
        y_steps = y_steps[np.isfinite(y_steps) & (y_steps > 0)]
        if y_steps.size:
            steps.append(float(np.median(y_steps)))

    if not steps:
        return 1.0

    return max(1.0, float(np.mean(steps)))


def apply_distance_mask(grid_z, grid_x, grid_y, point_x, point_y, max_distance_px):
    min_distance_sq = np.full(grid_z.shape, np.inf)

    for x, y in zip(point_x, point_y):
        distance_sq = (grid_x - x) ** 2 + (grid_y - y) ** 2
        min_distance_sq = np.minimum(min_distance_sq, distance_sq)

    masked_grid = grid_z.copy()
    masked_grid[min_distance_sq > max_distance_px ** 2] = np.nan
    return masked_grid


def get_survey_bounds_alpha(grid_x, grid_y, point_x, point_y, max_distance_px, margin_ratio=0.45):
    points = unique_finite_points(point_x, point_y)
    if len(points) < 3:
        return np.ones(grid_x.shape)

    try:
        triangulation = Delaunay(points)
    except QhullError:
        return np.ones(grid_x.shape)

    kept_simplices = get_local_delaunay_simplices(points, triangulation, max_distance_px)
    if not kept_simplices.any():
        return np.ones(grid_x.shape)

    grid_points = np.column_stack([grid_x.ravel(), grid_y.ravel()])
    simplex_indexes = triangulation.find_simplex(grid_points).reshape(grid_x.shape)
    inside_bounds = np.zeros(grid_x.shape, dtype=bool)
    valid_simplex = simplex_indexes >= 0
    inside_bounds[valid_simplex] = kept_simplices[simplex_indexes[valid_simplex]]

    margin_px = max(1.0, float(max_distance_px) * margin_ratio)
    outside_distance = distance_transform_edt(
        ~inside_bounds,
        sampling=get_grid_sampling_px(grid_x, grid_y),
    )
    alpha = 1.0 - (outside_distance / margin_px)
    return np.clip(alpha, 0, 1)


def get_local_delaunay_simplices(points, triangulation, max_distance_px):
    triangles = points[triangulation.simplices]
    side_a = np.linalg.norm(triangles[:, 1] - triangles[:, 0], axis=1)
    side_b = np.linalg.norm(triangles[:, 2] - triangles[:, 1], axis=1)
    side_c = np.linalg.norm(triangles[:, 0] - triangles[:, 2], axis=1)
    vector_a = triangles[:, 1] - triangles[:, 0]
    vector_b = triangles[:, 2] - triangles[:, 0]
    double_area = np.abs((vector_a[:, 0] * vector_b[:, 1]) - (vector_a[:, 1] * vector_b[:, 0]))

    with np.errstate(invalid="ignore", divide="ignore"):
        circumradius = (side_a * side_b * side_c) / (2.0 * double_area)

    max_radius = max(1.0, float(max_distance_px) * 1.5)
    return np.isfinite(circumradius) & (double_area > 1e-6) & (circumradius <= max_radius)


def get_grid_sampling_px(grid_x, grid_y):
    x_step = 1.0
    y_step = 1.0

    if grid_x.shape[0] > 1:
        x_steps = np.abs(np.diff(grid_x[:, 0]))
        x_steps = x_steps[np.isfinite(x_steps) & (x_steps > 0)]
        if x_steps.size:
            x_step = float(np.median(x_steps))

    if grid_y.shape[1] > 1:
        y_steps = np.abs(np.diff(grid_y[0, :]))
        y_steps = y_steps[np.isfinite(y_steps) & (y_steps > 0)]
        if y_steps.size:
            y_step = float(np.median(y_steps))

    return x_step, y_step


def unique_finite_points(point_x, point_y):
    points = []
    seen = set()

    for x, y in zip(point_x, point_y):
        try:
            x = float(x)
            y = float(y)
        except (TypeError, ValueError):
            continue

        if not np.isfinite(x) or not np.isfinite(y):
            continue

        key = (x, y)
        if key in seen:
            continue

        seen.add(key)
        points.append(key)

    return np.asarray(points, dtype=float)


def apply_signal_threshold(grid_z, min_signal_dbm):
    threshold_grid = grid_z.copy()
    threshold_grid[threshold_grid < min_signal_dbm] = np.nan
    return threshold_grid
