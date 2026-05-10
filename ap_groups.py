import pandas as pd

AP_GROUPS_METADATA_KEY = "ap_groups"
AP_ROLE_INTERNAL = "internal"
AP_ROLE_EXTERNAL = "external"
AP_ROLE_INTERFERER = "interferer"
AP_ROLE_TEST = "test"
AP_ROLE_CHOICES = (
    AP_ROLE_INTERNAL,
    AP_ROLE_EXTERNAL,
    AP_ROLE_INTERFERER,
    AP_ROLE_TEST,
)


def normalize_bssid(bssid):
    return str(bssid or "").strip().lower()


def get_ap_group_key(bssid):
    parts = normalize_bssid(bssid).split(":")

    if len(parts) == 6:
        last_prefix = parts[5][:1] or parts[5]
        return f"{':'.join(parts[1:5])}:{last_prefix}*"

    return normalize_bssid(bssid)


def get_ap_group_display_key(bssid):
    parts = normalize_bssid(bssid).split(":")

    if len(parts) == 6:
        last_prefix = parts[5][:1] or parts[5]
        return f"{':'.join(parts[:5])}:{last_prefix}*"

    return normalize_bssid(bssid)


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


def normalize_ap_position(value):
    if not isinstance(value, dict):
        return None

    try:
        x = int(round(float(value.get("x"))))
        y = int(round(float(value.get("y"))))
    except (TypeError, ValueError):
        return None

    return {"x": x, "y": y}


def normalize_ap_role(value):
    role = str(value or "").strip().lower()
    return role if role in AP_ROLE_CHOICES else AP_ROLE_INTERNAL


def build_manual_ap_group(group_id, bssids, alias="", locked=True, position=None, role=AP_ROLE_INTERNAL):
    clean_bssids = sorted({
        normalize_bssid(bssid)
        for bssid in bssids
        if normalize_bssid(bssid)
    })
    if not group_id:
        group_id = clean_bssids[0] if clean_bssids else ""

    group = {
        "group_id": str(group_id),
        "alias": str(alias or "").strip(),
        "bssids": clean_bssids,
        "locked": bool(locked),
        "role": normalize_ap_role(role),
    }

    clean_position = normalize_ap_position(position)
    if clean_position:
        group["position"] = clean_position

    return group


def build_default_manual_groups(rows):
    groups = []
    for detected_group in build_detected_ap_groups(rows):
        groups.append(build_manual_ap_group(
            detected_group["ap_group"],
            detected_group["bssids"],
            locked=False,
        ))

    return groups


def merge_new_bssids_into_manual_groups(manual_groups, rows):
    assigned_bssids = {
        normalize_bssid(bssid)
        for group in manual_groups
        for bssid in group.get("bssids", [])
        if normalize_bssid(bssid)
    }
    merged_groups = [
        build_manual_ap_group(
            group.get("group_id", ""),
            group.get("bssids", []),
            alias=group.get("alias", ""),
            locked=group.get("locked", True),
            position=group.get("position"),
            role=group.get("role", AP_ROLE_INTERNAL),
        )
        for group in manual_groups
    ]
    existing_group_ids = {
        str(group.get("group_id", ""))
        for group in merged_groups
        if str(group.get("group_id", ""))
    }

    for detected_group in build_default_manual_groups(rows):
        new_bssids = [
            bssid
            for bssid in detected_group["bssids"]
            if bssid not in assigned_bssids
        ]
        if not new_bssids:
            continue

        group_id = build_unique_group_id(detected_group["group_id"], existing_group_ids)
        existing_group_ids.add(group_id)
        merged_groups.append(build_manual_ap_group(
            group_id,
            new_bssids,
            locked=False,
        ))
        assigned_bssids.update(new_bssids)

    return merged_groups


def build_unique_group_id(group_id, existing_group_ids):
    clean_group_id = str(group_id or "").strip()
    if clean_group_id not in existing_group_ids:
        return clean_group_id

    suffix = 2
    while f"{clean_group_id}#{suffix}" in existing_group_ids:
        suffix += 1

    return f"{clean_group_id}#{suffix}"


def build_bssid_to_manual_group_map(manual_groups):
    mapping = {}
    for group in manual_groups:
        group_id = str(group.get("group_id", ""))
        if not group_id:
            continue

        for bssid in group.get("bssids", []):
            clean_bssid = normalize_bssid(bssid)
            if clean_bssid:
                mapping[clean_bssid] = group_id

    return mapping


def resolve_ap_group_key(bssid, bssid_group_map=None):
    clean_bssid = normalize_bssid(bssid)
    if bssid_group_map and clean_bssid in bssid_group_map:
        return bssid_group_map[clean_bssid]

    return get_ap_group_key(clean_bssid)


def normalize_ap_group_map(ap_group_map):
    if isinstance(ap_group_map, dict):
        return {
            normalize_bssid(bssid): str(group_id)
            for bssid, group_id in ap_group_map.items()
            if normalize_bssid(bssid) and str(group_id)
        }

    return {
        normalize_bssid(bssid): str(group_id)
        for bssid, group_id in (ap_group_map or ())
        if normalize_bssid(bssid) and str(group_id)
    }


def serialize_ap_group_map(ap_group_map):
    normalized = normalize_ap_group_map(ap_group_map)
    return tuple(sorted(normalized.items()))


def build_ap_group_role_map(manual_groups):
    return {
        str(group.get("group_id", "")): normalize_ap_role(group.get("role"))
        for group in manual_groups
        if str(group.get("group_id", ""))
    }


def normalize_ap_role_map(ap_group_roles):
    if isinstance(ap_group_roles, dict):
        items = ap_group_roles.items()
    else:
        items = ap_group_roles or ()

    return {
        str(group_id): normalize_ap_role(role)
        for group_id, role in items
        if str(group_id)
    }


def serialize_ap_group_roles(ap_group_roles):
    normalized = normalize_ap_role_map(ap_group_roles)
    return tuple(sorted(normalized.items()))


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
