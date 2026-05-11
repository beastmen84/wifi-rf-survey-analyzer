"""Checks that compare AP group metadata with observed scan data."""

import re

from ap_groups import (
    AP_ROLE_TEST,
    build_bssid_to_manual_group_map,
    normalize_ap_metadata,
    normalize_ap_role,
    resolve_ap_group_key,
)
from wifi_band import get_row_band, infer_band_from_channel as infer_wifi_band_from_channel


def build_ap_metadata_warnings(rows, ap_groups, channel_sort_key=None):
    group_map = build_bssid_to_manual_group_map(ap_groups)
    groups_by_id = {
        str(group.get("group_id", "")): group
        for group in ap_groups or []
        if str(group.get("group_id", ""))
    }
    observed_by_group = {}

    for row in rows:
        bssid = row.get("bssid", "")
        group_id = resolve_ap_group_key(bssid, group_map)
        group = groups_by_id.get(group_id)
        if not group or normalize_ap_role(group.get("role")) == AP_ROLE_TEST:
            continue

        channel = normalize_channel(row.get("channel"))
        if not channel:
            continue

        observed = observed_by_group.setdefault(group_id, {"channels": set(), "bands": set()})
        observed["channels"].add(channel)
        band = get_row_band(row)
        if band:
            observed["bands"].add(band)

    warnings = []
    for group_id, group in groups_by_id.items():
        if normalize_ap_role(group.get("role")) == AP_ROLE_TEST:
            continue

        metadata = normalize_ap_metadata(group.get("metadata"))
        expected_channels = parse_expected_channels(metadata.get("expected_channels", ""))
        expected_bands = parse_expected_bands(metadata.get("expected_bands", ""))
        if not expected_channels and not expected_bands:
            continue

        observed = observed_by_group.get(group_id, {"channels": set(), "bands": set()})
        observed_channels = observed["channels"]
        observed_bands = observed["bands"]
        unexpected_channels = observed_channels - expected_channels if expected_channels else set()
        unexpected_bands = observed_bands - expected_bands if expected_bands else set()

        if not unexpected_channels and not unexpected_bands:
            continue

        warnings.append({
            "group_id": group_id,
            "unexpected_channels": sort_channels(unexpected_channels, channel_sort_key),
            "expected_channels": sort_channels(expected_channels, channel_sort_key),
            "observed_channels": sort_channels(observed_channels, channel_sort_key),
            "unexpected_bands": sort_bands(unexpected_bands),
            "expected_bands": sort_bands(expected_bands),
            "observed_bands": sort_bands(observed_bands),
        })

    return sorted(warnings, key=lambda item: item["group_id"])


def parse_expected_channels(value):
    channels = set()
    text = str(value or "").strip()
    if not text:
        return channels

    for start, end in re.findall(r"(\d+)\s*-\s*(\d+)", text):
        start_number = int(start)
        end_number = int(end)
        if start_number > end_number:
            start_number, end_number = end_number, start_number
        channels.update(str(channel) for channel in range(start_number, end_number + 1))

    text_without_ranges = re.sub(r"\d+\s*-\s*\d+", " ", text)
    channels.update(re.findall(r"\d+", text_without_ranges))
    return channels


def parse_expected_bands(value):
    text = str(value or "").strip().lower()
    if not text:
        return set()

    bands = set()
    for token in re.split(r"[,;/\s]+", text):
        clean_token = token.replace("ghz", "").replace("g", "").replace(",", ".").strip()
        if clean_token in {"2", "2.4", "24"}:
            bands.add("2.4")
        elif clean_token == "5":
            bands.add("5")
        elif clean_token == "6":
            bands.add("6")

    if re.search(r"2(?:[.,]4)?\s*g(?:hz)?|2(?:[.,]4)", text):
        bands.add("2.4")
    if re.search(r"\b5\s*g(?:hz)?\b|\b5ghz\b", text):
        bands.add("5")
    if re.search(r"\b6\s*g(?:hz)?\b|\b6ghz\b", text):
        bands.add("6")

    return bands


def normalize_channel(value):
    text = str(value or "").strip()
    if not text:
        return ""

    match = re.search(r"\d+", text)
    return str(int(match.group(0))) if match else ""


def infer_band_from_channel(channel):
    return infer_wifi_band_from_channel(channel)


def sort_channels(channels, channel_sort_key=None):
    key = channel_sort_key or numeric_channel_sort_key
    return sorted((str(channel) for channel in channels if str(channel)), key=key)


def numeric_channel_sort_key(channel):
    try:
        return int(channel)
    except (TypeError, ValueError):
        return 9999


def sort_bands(bands):
    order = {"2.4": 0, "5": 1, "6": 2}
    return sorted((str(band) for band in bands if str(band)), key=lambda band: order.get(band, 99))
