"""AP grouping, aliasing, role, and metadata helpers."""

import re

import pandas as pd

from wifi.band import get_row_band, normalize_band
from wifi.evidence import finite_number

AP_GROUPS_METADATA_KEY = "ap_groups"
AP_MEMORY_APPLIED_KEY = "memory_applied"
AP_MEMORY_APPLIED_AT_KEY = "memory_applied_at"
AP_MEMORY_MATCH_BSSIDS_KEY = "memory_match_bssids"
AP_METADATA_FIELDS = (
    "vendor",
    "model",
    "mounting",
    "expected_bands",
    "expected_channels",
    "analysis_channel_override_24",
    "analysis_channel_override_5",
    "analysis_channel_override_6",
    "coverage_scope",
    "coverage_radius_m",
    "notes",
)
AP_ANALYSIS_CHANNEL_OVERRIDE_FIELDS = (
    ("2.4", "analysis_channel_override_24"),
    ("5", "analysis_channel_override_5"),
    ("6", "analysis_channel_override_6"),
)
AP_ANALYSIS_CHANNEL_OVERRIDE_FIELD_BY_BAND = dict(AP_ANALYSIS_CHANNEL_OVERRIDE_FIELDS)
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
AP_COVERAGE_SCOPE_GLOBAL = "global"
AP_COVERAGE_SCOPE_LOCAL = "local"
AP_COVERAGE_SCOPE_CHOICES = (
    AP_COVERAGE_SCOPE_GLOBAL,
    AP_COVERAGE_SCOPE_LOCAL,
)
AP_GROUP_FRAGMENT_SUFFIX_RE = re.compile(r"#\d+$")
INCOMPATIBLE_AP_GROUP_VALUE = object()


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
    return aliases.get(group_key) or aliases.get(get_ap_group_display_key(bssid)) or aliases.get(get_ap_group_key(bssid)) or ""


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
            "bands": set(),
            "vendors": set(),
            "models": set(),
        })
        group["display_groups"].add(get_ap_group_display_key(bssid))
        group["bssids"].add(bssid)
        if row.get("ssid"):
            group["ssids"].add(row["ssid"])
        if row.get("channel"):
            group["channels"].add(str(row["channel"]))
        band = get_row_band(row)
        if band:
            group["bands"].add(band)
        if row.get("vendor"):
            group["vendors"].add(str(row["vendor"]).strip())
        if row.get("model"):
            group["models"].add(str(row["model"]).strip())

    sort_channels = channel_sort_key or (lambda value: value)
    result = []
    for group in groups.values():
        result.append({
            "ap_group": group["ap_group"],
            "display_groups": sorted(group["display_groups"]),
            "bssids": sorted(group["bssids"]),
            "ssids": sorted(group["ssids"]),
            "channels": sorted(group["channels"], key=sort_channels),
            "bands": sorted(group["bands"]),
            "vendors": sorted(value for value in group["vendors"] if value),
            "models": sorted(value for value in group["models"] if value),
        })

    return sorted(result, key=lambda item: " ".join(item["display_groups"]))


def normalize_ap_position(value):
    if not isinstance(value, dict):
        return None

    try:
        x = int(round(float(value.get("x"))))
        y = int(round(float(value.get("y"))))
    except (TypeError, ValueError, OverflowError):
        return None

    return {"x": x, "y": y}


def normalize_ap_role(value):
    role = str(value or "").strip().lower()
    return role if role in AP_ROLE_CHOICES else AP_ROLE_INTERNAL


def normalize_ap_metadata(value):
    if not isinstance(value, dict):
        return {}

    metadata = {
        field: str(value.get(field, "")).strip()
        for field in AP_METADATA_FIELDS
        if str(value.get(field, "")).strip()
    }
    scope = normalize_ap_coverage_scope(metadata.get("coverage_scope", ""))
    if scope == AP_COVERAGE_SCOPE_LOCAL:
        metadata["coverage_scope"] = scope
        radius = normalize_coverage_radius_m(metadata.get("coverage_radius_m", ""))
        if radius:
            metadata["coverage_radius_m"] = radius
        else:
            metadata.pop("coverage_radius_m", None)
    else:
        metadata.pop("coverage_scope", None)
        metadata.pop("coverage_radius_m", None)
    return metadata


def normalize_ap_coverage_scope(value):
    scope = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if scope in {"local", "zone", "zone_only", "local_area", "area"}:
        return AP_COVERAGE_SCOPE_LOCAL
    return AP_COVERAGE_SCOPE_GLOBAL


def normalize_coverage_radius_m(value):
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return ""

    try:
        radius = float(text)
    except ValueError:
        return ""

    if finite_number(radius) is None or radius <= 0:
        return ""

    rounded = round(radius, 2)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def is_local_coverage_metadata(value):
    if not isinstance(value, dict):
        return False
    return normalize_ap_coverage_scope(value.get("coverage_scope", "")) == AP_COVERAGE_SCOPE_LOCAL


def normalize_ap_analysis_channel_override(value):
    text = str(value or "").strip()
    if not text:
        return ""

    match = re.search(r"\d+", text)
    return str(int(match.group(0))) if match else ""


def normalize_ap_analysis_band(value):
    band = normalize_band(value)
    return band if band in AP_ANALYSIS_CHANNEL_OVERRIDE_FIELD_BY_BAND else ""


def get_ap_analysis_channel_override_field(band):
    return AP_ANALYSIS_CHANNEL_OVERRIDE_FIELD_BY_BAND.get(normalize_ap_analysis_band(band), "")


def build_manual_ap_group(
    group_id,
    bssids,
    alias="",
    locked=True,
    position=None,
    role=AP_ROLE_INTERNAL,
    metadata=None,
    memory_applied=False,
    memory_applied_at="",
    memory_match_bssids=None,
    physical_confirmed=None,
):
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
        "physical_confirmed": bool(locked) if physical_confirmed is None else bool(physical_confirmed),
        "role": normalize_ap_role(role),
    }

    clean_position = normalize_ap_position(position)
    if clean_position:
        group["position"] = clean_position

    clean_metadata = normalize_ap_metadata(metadata)
    if clean_metadata:
        group["metadata"] = clean_metadata

    if memory_applied:
        group[AP_MEMORY_APPLIED_KEY] = True
        applied_at = str(memory_applied_at or "").strip()
        if applied_at:
            group[AP_MEMORY_APPLIED_AT_KEY] = applied_at
        match_bssids = sorted({
            normalize_bssid(bssid)
            for bssid in (memory_match_bssids or [])
            if normalize_bssid(bssid)
        })
        if match_bssids:
            group[AP_MEMORY_MATCH_BSSIDS_KEY] = match_bssids

    return group


def build_default_manual_groups(rows):
    groups = []
    for detected_group in build_detected_ap_groups(rows):
        groups.append(build_manual_ap_group(
            detected_group["ap_group"],
            detected_group["bssids"],
            locked=False,
            metadata=infer_detected_ap_metadata(detected_group),
        ))

    return groups


def infer_detected_ap_metadata(detected_group):
    metadata = {}
    vendor = infer_single_detected_value(detected_group.get("vendors", []))
    model = infer_single_detected_value(detected_group.get("models", []))

    if vendor:
        metadata["vendor"] = vendor
    if model:
        metadata["model"] = model

    return metadata


def infer_single_detected_value(values):
    clean_values = sorted({
        str(value).strip()
        for value in values
        if str(value).strip()
    })

    if len(clean_values) == 1:
        return clean_values[0]

    return ""


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
            metadata=group.get("metadata"),
            memory_applied=group.get(AP_MEMORY_APPLIED_KEY),
            memory_applied_at=group.get(AP_MEMORY_APPLIED_AT_KEY, ""),
            memory_match_bssids=group.get(AP_MEMORY_MATCH_BSSIDS_KEY, []),
            physical_confirmed=is_ap_group_confirmed(group),
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
            metadata=detected_group.get("metadata"),
        ))
        assigned_bssids.update(new_bssids)

    return merged_groups


def merge_auto_ap_group_fragments(manual_groups, rows):
    auto_groups = {
        group["group_id"]: set(group.get("bssids", []))
        for group in build_default_manual_groups(rows)
        if group.get("group_id")
    }
    if not auto_groups:
        return list(manual_groups or [])

    merge_plan = {}
    consumed_indexes = set()
    groups = list(manual_groups or [])
    for auto_group_id, auto_bssids in auto_groups.items():
        candidates = []
        for index, group in enumerate(groups):
            if index in consumed_indexes:
                continue
            group_bssids = set(group.get("bssids", []))
            if not group_bssids:
                continue
            if base_ap_group_id(group.get("group_id", "")) != auto_group_id:
                continue
            if not group_bssids <= auto_bssids:
                continue
            candidates.append((index, group))

        if len(candidates) < 2:
            continue
        if not any(group.get(AP_MEMORY_APPLIED_KEY) for _index, group in candidates):
            continue

        merged_group = merge_compatible_ap_group_fragments(auto_group_id, [group for _index, group in candidates])
        if not merged_group:
            continue

        first_index = candidates[0][0]
        merge_plan[first_index] = merged_group
        consumed_indexes.update(index for index, _group in candidates[1:])

    if not merge_plan:
        return groups

    merged_groups = []
    for index, group in enumerate(groups):
        if index in consumed_indexes:
            continue
        merged_groups.append(merge_plan.get(index, group))
    return merged_groups


def base_ap_group_id(group_id):
    return AP_GROUP_FRAGMENT_SUFFIX_RE.sub("", str(group_id or "").strip())


def merge_compatible_ap_group_fragments(group_id, groups):
    alias = compatible_text_value(group.get("alias", "") for group in groups)
    if alias is INCOMPATIBLE_AP_GROUP_VALUE:
        return None

    role = compatible_role_value(group.get("role") for group in groups)
    if role is INCOMPATIBLE_AP_GROUP_VALUE:
        return None

    position = compatible_position_value(group.get("position") for group in groups)
    if position is INCOMPATIBLE_AP_GROUP_VALUE:
        return None

    metadata = compatible_metadata_value(group.get("metadata") for group in groups)
    if metadata is INCOMPATIBLE_AP_GROUP_VALUE:
        return None

    bssids = sorted({
        normalize_bssid(bssid)
        for group in groups
        for bssid in group.get("bssids", [])
        if normalize_bssid(bssid)
    })
    memory_applied = any(group.get(AP_MEMORY_APPLIED_KEY) for group in groups)
    memory_applied_at = max(
        (str(group.get(AP_MEMORY_APPLIED_AT_KEY, "")).strip() for group in groups),
        default="",
    )
    memory_match_bssids = sorted({
        normalize_bssid(bssid)
        for group in groups
        for bssid in group.get(AP_MEMORY_MATCH_BSSIDS_KEY, group.get("bssids", []))
        if normalize_bssid(bssid)
    })

    return build_manual_ap_group(
        group_id,
        bssids,
        alias=alias or "",
        locked=any(group.get("locked") for group in groups),
        position=position,
        role=role,
        metadata=metadata,
        memory_applied=memory_applied,
        memory_applied_at=memory_applied_at,
        memory_match_bssids=memory_match_bssids,
        physical_confirmed=False,  # Automatic healing does not confirm physical identity.
    )


def compatible_text_value(values):
    clean_values = {
        str(value or "").strip()
        for value in values
        if str(value or "").strip()
    }
    if len(clean_values) > 1:
        return INCOMPATIBLE_AP_GROUP_VALUE
    return next(iter(clean_values), "")


def compatible_role_value(values):
    roles = {normalize_ap_role(value) for value in values if str(value or "").strip()}
    if len(roles) > 1:
        return INCOMPATIBLE_AP_GROUP_VALUE
    return next(iter(roles), AP_ROLE_INTERNAL)


def compatible_position_value(values):
    positions = []
    for value in values:
        position = normalize_ap_position(value)
        if position:
            positions.append(position)
    unique_positions = {
        (position["x"], position["y"])
        for position in positions
    }
    if len(unique_positions) > 1:
        return INCOMPATIBLE_AP_GROUP_VALUE
    return positions[0] if positions else None


def compatible_metadata_value(values):
    merged = {}
    for value in values:
        metadata = normalize_ap_metadata(value)
        for field, field_value in metadata.items():
            if field in merged and merged[field] != field_value:
                return INCOMPATIBLE_AP_GROUP_VALUE
            merged[field] = field_value
    return merged


def build_unique_group_id(group_id, existing_group_ids):
    clean_group_id = str(group_id or "").strip()
    if clean_group_id not in existing_group_ids:
        return clean_group_id

    suffix = 2
    while f"{clean_group_id}#{suffix}" in existing_group_ids:
        suffix += 1

    return f"{clean_group_id}#{suffix}"


def build_bssid_to_manual_group_map(manual_groups, *, confirmed_only=False):
    """Keep UI/metadata membership; RF comparisons require confirmed identity."""
    mapping = {}
    for group in manual_groups:
        group_id = str(group.get("group_id", ""))
        if not group_id:
            continue

        for bssid in group.get("bssids", []):
            clean_bssid = normalize_bssid(bssid)
            if clean_bssid:
                mapping[clean_bssid] = (clean_bssid if confirmed_only and not is_ap_group_confirmed(group)
                    and len(group.get("bssids", [])) > 1 else group_id)

    return mapping


def is_ap_group_confirmed(group):
    """Legacy explicit manual groups stay valid; new auto groups need confirmation."""
    return bool(group.get("physical_confirmed", group.get("locked", True)))


def resolve_ap_group_key(bssid, bssid_group_map=None):
    clean_bssid = normalize_bssid(bssid)
    if bssid_group_map and clean_bssid in bssid_group_map:
        return bssid_group_map[clean_bssid]

    return clean_bssid


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
        group_id: normalize_ap_role(group.get("role"))
        for group in manual_groups
        for group_id in _group_analysis_ids(group)
    }


def _group_analysis_ids(group):
    """User metadata also applies to BSSIDs kept separate for RF analysis."""
    group_id = str(group.get("group_id", ""))
    ids = {group_id} if group_id else set()
    if not is_ap_group_confirmed(group) and len(group.get("bssids", [])) > 1:
        ids.update(normalize_bssid(bssid) for bssid in group["bssids"] if normalize_bssid(bssid))
    return ids


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


def build_ap_group_channel_override_map(manual_groups):
    overrides = {}
    for group in manual_groups or []:
        group_id = str(group.get("group_id", ""))
        if not group_id:
            continue

        metadata = normalize_ap_metadata(group.get("metadata"))
        for band, field in AP_ANALYSIS_CHANNEL_OVERRIDE_FIELDS:
            channel = normalize_ap_analysis_channel_override(metadata.get(field, ""))
            if channel:
                for analysis_id in _group_analysis_ids(group):
                    overrides[(analysis_id, band)] = channel

    return overrides


def normalize_ap_group_channel_overrides(ap_group_channel_overrides):
    if isinstance(ap_group_channel_overrides, dict):
        items = []
        for key, channel in ap_group_channel_overrides.items():
            if isinstance(key, (list, tuple)) and len(key) == 2:
                group_id, band = key
                items.append((group_id, band, channel))
    else:
        items = ap_group_channel_overrides or ()

    overrides = {}
    for item in items:
        try:
            group_id, band, channel = item
        except (TypeError, ValueError):
            continue

        clean_group_id = str(group_id or "").strip()
        clean_band = normalize_ap_analysis_band(band)
        clean_channel = normalize_ap_analysis_channel_override(channel)
        if clean_group_id and clean_band and clean_channel:
            overrides[(clean_group_id, clean_band)] = clean_channel

    return overrides


def serialize_ap_group_channel_overrides(ap_group_channel_overrides):
    normalized = normalize_ap_group_channel_overrides(ap_group_channel_overrides)
    return tuple(
        sorted(
            (group_id, band, channel)
            for (group_id, band), channel in normalized.items()
        )
    )


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
