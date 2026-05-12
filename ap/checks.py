"""Validation checks for AP group definitions and survey consistency."""

from collections import OrderedDict, defaultdict

from ap.groups import (
    AP_ROLE_INTERNAL,
    AP_ROLE_TEST,
    build_bssid_to_manual_group_map,
    normalize_ap_role,
    resolve_ap_group_key,
)
from ap.metadata import normalize_channel, sort_bands, sort_channels
from wifi.band import get_row_band


AP_CHANNEL_CHANGE_CLEAN = "clean"
AP_CHANNEL_CHANGE_AMBIGUOUS = "ambiguous"


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
        band = get_row_band(row)
        if channel and band:
            observations[group_id][band][channel].add(bssid)

    conflicts = []
    for group_id, bands in observations.items():
        for band, channels in bands.items():
            if len(channels) <= 1:
                continue

            channel_bssid_sets = [channels[channel] for channel in channels]
            if len({frozenset(bssids) for bssids in channel_bssid_sets}) == 1:
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


def build_ap_channel_changes(rows, ap_groups=None, channel_sort_key=None):
    group_map = build_bssid_to_manual_group_map(ap_groups or [])
    groups_by_id = {
        str(group.get("group_id", "")): group
        for group in ap_groups or []
        if str(group.get("group_id", ""))
    }
    observations = defaultdict(lambda: defaultdict(lambda: {
        "bssids_by_channel": defaultdict(set),
        "channels_by_timestamp": OrderedDict(),
    }))

    for index, row in enumerate(rows or []):
        bssid = str(row.get("bssid", "")).strip().lower()
        if not bssid:
            continue

        if ap_groups is None:
            group_id = str(row.get("ap_group") or resolve_ap_group_key(bssid, {}))
            role = normalize_ap_role(row.get("ap_role", AP_ROLE_INTERNAL))
        else:
            group_id = resolve_ap_group_key(bssid, group_map)
            group = groups_by_id.get(group_id)
            if not group:
                continue
            role = normalize_ap_role(group.get("role"))
        if not group_id or role == AP_ROLE_TEST:
            continue

        channel = normalize_channel(row.get("channel"))
        band = get_row_band(row)
        if not channel or not band:
            continue

        timestamp = str(row.get("timestamp", "")).strip() or f"row-{index}"
        observed = observations[group_id][band]
        observed["bssids_by_channel"][channel].add(bssid)
        observed["channels_by_timestamp"].setdefault(timestamp, set()).add(channel)

    changes = []
    for group_id, bands in observations.items():
        for band, observed in bands.items():
            bssids_by_channel = observed["bssids_by_channel"]
            if len(bssids_by_channel) <= 1:
                continue

            channel_bssid_sets = {frozenset(bssids) for bssids in bssids_by_channel.values()}
            if len(channel_bssid_sets) != 1:
                continue

            sequence = []
            simultaneous_channels = []
            for timestamp, channels in observed["channels_by_timestamp"].items():
                if len(channels) != 1:
                    simultaneous_channels.append({
                        "timestamp": timestamp,
                        "channels": sort_channels(channels, channel_sort_key),
                    })
                    continue
                channel = next(iter(channels))
                if not sequence or sequence[-1]["channel"] != channel:
                    sequence.append({"timestamp": timestamp, "channel": channel})

            if len(sequence) <= 1 and not simultaneous_channels:
                continue

            sequence_channels = [item["channel"] for item in sequence]
            status = (
                AP_CHANNEL_CHANGE_CLEAN
                if not simultaneous_channels and len(set(sequence_channels)) == len(sequence_channels)
                else AP_CHANNEL_CHANGE_AMBIGUOUS
            )
            current_channel = sequence[-1]["channel"] if sequence else ""
            previous_channels = [channel for channel in sequence_channels if channel != current_channel]
            changes.append({
                "group_id": group_id,
                "band": band,
                "status": status,
                "channels": sort_channels(bssids_by_channel.keys(), channel_sort_key),
                "current_channel": current_channel,
                "previous_channels": sort_channels(previous_channels, channel_sort_key),
                "sequence": sequence,
                "transitions": [
                    {
                        "from": sequence[index - 1]["channel"],
                        "to": sequence[index]["channel"],
                        "timestamp": sequence[index]["timestamp"],
                    }
                    for index in range(1, len(sequence))
                ],
                "simultaneous_channels": simultaneous_channels,
            })

    return sorted(changes, key=lambda item: (item["group_id"], sort_bands([item["band"]])[0]))
