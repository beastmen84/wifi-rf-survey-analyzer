import pandas as pd


def get_ap_group_key(bssid):
    parts = str(bssid or "").lower().split(":")

    if len(parts) == 6:
        last_prefix = parts[5][:1] or parts[5]
        return f"{':'.join(parts[1:5])}:{last_prefix}*"

    return str(bssid or "").lower()


def get_ap_group_display_key(bssid):
    parts = str(bssid or "").lower().split(":")

    if len(parts) == 6:
        last_prefix = parts[5][:1] or parts[5]
        return f"{':'.join(parts[:5])}:{last_prefix}*"

    return str(bssid or "").lower()


def format_short_bssid(bssid):
    if not bssid:
        return "-"

    parts = str(bssid).split(":")
    if len(parts) >= 3:
        return ":".join(parts[-3:])

    return str(bssid)


def resolve_ap_alias(bssid, aliases, ap_group=None):
    group_key = ap_group or get_ap_group_key(bssid)
    return aliases.get(group_key) or aliases.get(get_ap_group_display_key(bssid)) or ""


def format_ap_label(bssid, aliases, ap_group=None):
    alias = resolve_ap_alias(bssid, aliases, ap_group)
    short_bssid = format_short_bssid(bssid)

    if alias:
        return f"{alias} ({short_bssid})"

    return short_bssid


def build_detected_ap_groups(rows, channel_sort_key=None):
    groups = {}

    for row in rows:
        bssid = row.get("bssid", "")
        if not bssid:
            continue

        group_key = get_ap_group_key(bssid)
        group = groups.setdefault(group_key, {
            "ap_group": group_key,
            "display_groups": set(),
            "bssids": set(),
            "ssids": set(),
            "channels": set(),
        })
        group["display_groups"].add(get_ap_group_display_key(bssid))
        group["bssids"].add(bssid)
        if row.get("ssid"):
            group["ssids"].add(row["ssid"])
        if row.get("channel"):
            group["channels"].add(str(row["channel"]))

    sort_channels = channel_sort_key or (lambda value: value)
    result = []
    for group in groups.values():
        result.append({
            "ap_group": group["ap_group"],
            "display_groups": sorted(group["display_groups"]),
            "bssids": sorted(group["bssids"]),
            "ssids": sorted(group["ssids"]),
            "channels": sorted(group["channels"], key=sort_channels),
        })

    return sorted(result, key=lambda item: " ".join(item["display_groups"]))


def build_dominant_ap_group_labels(dominant_df, aliases):
    labels = {}
    if dominant_df.empty or "dominant_ap_group" not in dominant_df.columns:
        return labels

    for ap_group, group_df in dominant_df.groupby("dominant_ap_group", dropna=False):
        bssids = [
            str(bssid)
            for bssid in group_df.get("dominant_bssid", pd.Series(dtype=str)).dropna().unique()
            if str(bssid)
        ]
        if not bssids:
            labels[ap_group] = str(ap_group or "-")
            continue

        alias = resolve_ap_alias(bssids[0], aliases, ap_group)
        short_bssids = sorted({format_short_bssid(bssid) for bssid in bssids})

        if alias:
            labels[ap_group] = f"{alias} ({', '.join(short_bssids)})"
        elif len(short_bssids) == 1:
            labels[ap_group] = format_ap_label(bssids[0], aliases, ap_group)
        else:
            labels[ap_group] = ", ".join(short_bssids)

    return labels
