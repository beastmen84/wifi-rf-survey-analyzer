"""Validation checks for AP group definitions and survey consistency."""

from collections import defaultdict

from ap_groups import (
    AP_ROLE_TEST,
    build_bssid_to_manual_group_map,
    normalize_ap_role,
    resolve_ap_group_key,
)
from ap_metadata_checks import infer_band_from_channel, normalize_channel, sort_bands, sort_channels


def build_ap_group_conflicts(rows, ap_groups, channel_sort_key=None):
    group_map = build_bssid_to_manual_group_map(ap_groups)
    groups_by_id = {
        str(group.get("group_id", "")): group
        for group in ap_groups or []
        if str(group.get("group_id", ""))
    }
    observations = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

    for row in rows:
        bssid = str(row.get("bssid", "")).strip().lower()
        if not bssid:
            continue

        group_id = resolve_ap_group_key(bssid, group_map)
        group = groups_by_id.get(group_id)
        if not group or normalize_ap_role(group.get("role")) == AP_ROLE_TEST:
            continue

        channel = normalize_channel(row.get("channel"))
        band = infer_band_from_channel(channel)
        if channel and band:
            observations[group_id][band][channel].add(bssid)

    conflicts = []
    for group_id, bands in observations.items():
        for band, channels in bands.items():
            if len(channels) <= 1:
                continue

            conflicts.append({
                "group_id": group_id,
                "band": band,
                "channels": sort_channels(channels.keys(), channel_sort_key),
                "bssids_by_channel": {
                    channel: sorted(channels[channel])
                    for channel in channels
                },
            })

    return sorted(conflicts, key=lambda item: (item["group_id"], sort_bands([item["band"]])[0]))
