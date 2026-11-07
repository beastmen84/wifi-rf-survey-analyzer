"""Persistent AP group and metadata memory."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from ap.groups import (
    AP_MEMORY_APPLIED_AT_KEY,
    AP_MEMORY_APPLIED_KEY,
    AP_MEMORY_MATCH_BSSIDS_KEY,
    AP_ROLE_INTERNAL,
    normalize_ap_metadata,
    normalize_ap_position,
    normalize_ap_role,
    normalize_bssid,
    is_ap_group_confirmed,
    invalidate_ap_group_confirmation,
)
from app_core.settings import APP_SETTINGS_DIR
from app_core.file_io import atomic_write_text
from wifi.band import get_row_band


AP_MEMORY_ENV_FILE = "WIFI_HEATMAP_AP_MEMORY_FILE"
AP_MEMORY_FILE_NAME = "ap_memory.memory"
AP_MEMORY_SCHEMA_VERSION = 1


def get_ap_memory_path():
    override = os.environ.get(AP_MEMORY_ENV_FILE)
    if override:
        return Path(override)

    appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    if appdata:
        return Path(appdata) / APP_SETTINGS_DIR / AP_MEMORY_FILE_NAME

    return Path.home() / ".wifi_heatmap" / AP_MEMORY_FILE_NAME


def empty_ap_memory():
    return {
        "schema_version": AP_MEMORY_SCHEMA_VERSION,
        "groups": [],
    }


def ensure_ap_memory_file(path=None):
    memory_path = Path(path) if path else get_ap_memory_path()
    if memory_path.exists():
        return memory_path

    try:
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(memory_path,
            json.dumps(empty_ap_memory(), indent=2, ensure_ascii=False, sort_keys=True),
        )
    except OSError:
        pass

    return memory_path


def clear_ap_memory(path=None):
    return save_ap_memory(empty_ap_memory(), path)


def load_ap_memory(path=None):
    memory_path = ensure_ap_memory_file(path)
    try:
        data = json.loads(memory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_ap_memory()

    if not isinstance(data, dict):
        return empty_ap_memory()

    groups = data.get("groups", [])
    if not isinstance(groups, list):
        groups = []

    return {
        "schema_version": AP_MEMORY_SCHEMA_VERSION,
        "created_at": str(data.get("created_at", "")).strip(),
        "updated_at": str(data.get("updated_at", "")).strip(),
        "groups": [normalize_memory_record(record) for record in groups],
    }


def get_ap_memory_summary(path=None):
    memory_path = Path(path) if path else get_ap_memory_path()
    was_present = memory_path.exists()
    data = load_ap_memory(memory_path)
    groups = [record for record in data.get("groups", []) if record.get("bssids")]
    return {
        "path": str(memory_path),
        "exists": was_present or memory_path.exists(),
        "group_count": len(groups),
        "updated_at": str(data.get("updated_at", "")).strip(),
    }


def save_ap_memory(data, path=None):
    memory_path = Path(path) if path else get_ap_memory_path()
    groups = [
        normalize_memory_record(record)
        for record in data.get("groups", [])
        if normalize_memory_record(record).get("bssids")
    ]
    payload = {
        "schema_version": AP_MEMORY_SCHEMA_VERSION,
        "created_at": str(data.get("created_at", "")).strip() or utc_now(),
        "updated_at": utc_now(),
        "groups": sorted(groups, key=lambda record: record.get("label", "") or " ".join(record.get("bssids", []))),
    }

    try:
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(memory_path,
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
        )
    except OSError:
        return False

    return True


def update_ap_memory_from_groups(groups, rows=None, map_file="", path=None):
    data = load_ap_memory(path)
    records = data.get("groups", [])
    rows = rows or []
    now = utc_now()

    for group in groups or []:
        bssids = clean_bssids(group.get("bssids", []))
        if not bssids:
            continue

        record = find_best_memory_record(records, bssids)
        explicit_confirmation = not group_has_memory_flag(group) and (
            is_ap_group_confirmed(group) or group.get("physical_confirmation_revoked"))
        if explicit_confirmation:
            # Approval refers to one exact membership, never the historical union
            # of overlapping MAC-based suggestions used for metadata matching.
            for existing in records:
                if set(existing.get("bssids", [])) & set(bssids):
                    existing["physical_confirmed"] = False
            if record and clean_bssids(record.get("bssids", [])) != bssids:
                record = None
        if record is None:
            record = build_empty_memory_record(bssids)
            records.append(record)

        observed = summarize_observed_group_rows(rows, bssids)
        previous_bssids = clean_bssids(record.get("bssids", []))
        record["bssids"] = sorted(set(previous_bssids) | set(bssids))
        if record["bssids"] != previous_bssids:
            record["physical_confirmed"] = False
        if explicit_confirmation:
            record["physical_confirmed"] = is_ap_group_confirmed(group)
        record["last_seen_at"] = now
        record["last_seen_group_id"] = str(group.get("group_id", "")).strip()
        record["ssids"] = sorted(set(record.get("ssids", [])) | observed["ssids"])
        record["channels"] = sorted(set(record.get("channels", [])) | observed["channels"], key=numeric_text_key)
        record["bands"] = sorted(set(record.get("bands", [])) | observed["bands"], key=band_sort_key)

        if group_has_memory_flag(group):
            continue

        alias = str(group.get("alias", "")).strip()
        if alias:
            record["alias"] = alias
            record["label"] = alias
        else:
            record["label"] = record.get("label", "") or str(group.get("group_id", "")).strip()

        role = normalize_ap_role(group.get("role"))
        if role != AP_ROLE_INTERNAL or group.get("locked"):
            record["role"] = role

        metadata = normalize_ap_metadata(group.get("metadata"))
        if metadata:
            record["metadata"] = metadata

        position = normalize_ap_position(group.get("position"))
        if position:
            position.pop("symbol_id", None)  # Drawing identities belong to the survey.
        map_key = build_map_memory_key(map_file)
        if position and map_key:
            positions = record.setdefault("map_positions", {})
            positions[map_key] = {
                **position,
                "map": build_map_descriptor(map_file),
                "updated_at": now,
            }

    data["groups"] = records
    return save_ap_memory(data, path)


def apply_ap_memory_to_groups(groups, rows=None, map_file="", path=None):
    data = load_ap_memory(path)
    records = data.get("groups", [])
    if not records:
        return list(groups or []), 0

    applied_count = 0
    updated_groups = []
    for group in groups or []:
        updated_group = dict(group)
        bssids = clean_bssids(updated_group.get("bssids", []))
        record = find_best_memory_record(records, bssids)
        matched_bssids = sorted(set(record.get("bssids", [])) & set(bssids)) if record else []
        if record and not updated_group.get("physical_confirmation_revoked") and apply_memory_record_to_group(updated_group, record, map_file):
            mark_group_from_memory(updated_group, matched_bssids)
            applied_count += 1
        restore_physical_confirmation(updated_group, records)
        updated_groups.append(updated_group)

    return updated_groups, applied_count


def restore_physical_confirmation(group, records):
    """Restore only an exact approved membership; local edits/revocations win."""
    if group.get("physical_confirmation_revoked") or is_ap_group_confirmed(group):
        return False
    bssids = clean_bssids(group.get("bssids", []))
    if bssids and any(record.get("physical_confirmed") is True
                      and clean_bssids(record.get("bssids", [])) == bssids
                      for record in records):
        group["physical_confirmed"] = True
        group["locked"] = True
        return True
    return False


def find_memory_record_for_group(group, path=None, records=None):
    bssids = clean_bssids((group or {}).get("bssids", []))
    source_records = records if records is not None else load_ap_memory(path).get("groups", [])
    record = find_best_memory_record(source_records, bssids)
    if not record:
        return None, []
    return record, sorted(set(record.get("bssids", [])) & set(bssids))


def apply_memory_record_to_group(group, record, map_file=""):
    changed = False

    alias = str(record.get("alias", "")).strip()
    if alias and not str(group.get("alias", "")).strip():
        group["alias"] = alias
        changed = True

    record_role = normalize_ap_role(record.get("role"))
    current_role = normalize_ap_role(group.get("role"))
    if record_role != current_role and (not group.get("locked") or current_role == AP_ROLE_INTERNAL):
        group["role"] = record_role
        changed = True

    current_metadata = normalize_ap_metadata(group.get("metadata"))
    record_metadata = normalize_ap_metadata(record.get("metadata"))
    for field, value in record_metadata.items():
        if value and not current_metadata.get(field):
            current_metadata[field] = value
            changed = True
    if current_metadata:
        group["metadata"] = current_metadata

    if not normalize_ap_position(group.get("position")) and not group.get("position_cleared"):
        map_position = find_memory_position_for_map(record, map_file)
        if map_position:
            group["position"] = map_position
            changed = True

    if changed:
        group["locked"] = True

    return changed


def get_group_memory_update_fields(group, map_file="", path=None, records=None):
    if not isinstance(group, dict) or group_has_memory_flag(group):
        return []

    record, _matched_bssids = find_memory_record_for_group(group, path=path, records=records)
    if not record:
        return []

    fields = []
    record_alias = str(record.get("alias", "")).strip()
    if record_alias and record_alias != str(group.get("alias", "")).strip():
        fields.append("alias")

    record_role = normalize_ap_role(record.get("role"))
    if record.get("role") and record_role != normalize_ap_role(group.get("role")):
        fields.append("role")

    current_metadata = normalize_ap_metadata(group.get("metadata"))
    record_metadata = normalize_ap_metadata(record.get("metadata"))
    if any(value and current_metadata.get(field) != value for field, value in record_metadata.items()):
        fields.append("metadata")

    map_position = find_memory_position_for_map(record, map_file)
    if (map_position and not (group.get("position") or {}).get("symbol_id") and not group.get("position_cleared")
            and normalize_ap_position(group.get("position")) != map_position):
        fields.append("position")

    return fields


def apply_group_memory_update(group, map_file="", path=None, records=None):
    if not isinstance(group, dict):
        return False

    record, _matched_bssids = find_memory_record_for_group(group, path=path, records=records)
    if not record:
        return False

    changed = False
    alias = str(record.get("alias", "")).strip()
    if alias and alias != str(group.get("alias", "")).strip():
        group["alias"] = alias
        changed = True

    if record.get("role"):
        role = normalize_ap_role(record.get("role"))
        if role != normalize_ap_role(group.get("role")):
            group["role"] = role
            changed = True

    current_metadata = normalize_ap_metadata(group.get("metadata"))
    record_metadata = normalize_ap_metadata(record.get("metadata"))
    for field, value in record_metadata.items():
        if value and current_metadata.get(field) != value:
            current_metadata[field] = value
            changed = True
    if current_metadata:
        group["metadata"] = current_metadata

    map_position = find_memory_position_for_map(record, map_file)
    if (map_position and not (group.get("position") or {}).get("symbol_id") and not group.get("position_cleared")
            and normalize_ap_position(group.get("position")) != map_position):
        group["position"] = map_position
        changed = True

    if changed:
        clear_group_memory_flag(group)
        group["locked"] = True
        invalidate_ap_group_confirmation(group)

    return changed


def group_has_memory_flag(group):
    return bool(group and group.get(AP_MEMORY_APPLIED_KEY))


def clear_group_memory_flag(group):
    if not isinstance(group, dict):
        return group

    group.pop(AP_MEMORY_APPLIED_KEY, None)
    group.pop(AP_MEMORY_APPLIED_AT_KEY, None)
    group.pop(AP_MEMORY_MATCH_BSSIDS_KEY, None)
    return group


def mark_group_from_memory(group, matched_bssids=None):
    group[AP_MEMORY_APPLIED_KEY] = True
    group[AP_MEMORY_APPLIED_AT_KEY] = utc_now()
    matches = clean_bssids(matched_bssids or [])
    if matches:
        group[AP_MEMORY_MATCH_BSSIDS_KEY] = matches
    return group


def count_memory_applied_groups(groups):
    return sum(1 for group in groups or [] if group_has_memory_flag(group))


def normalize_memory_record(record):
    if not isinstance(record, dict):
        return build_empty_memory_record([])

    bssids = clean_bssids(record.get("bssids", []))
    normalized = {
        "memory_id": str(record.get("memory_id", "")).strip() or build_memory_id(bssids),
        "label": str(record.get("label", "")).strip(),
        "alias": str(record.get("alias", "")).strip(),
        "role": normalize_ap_role(record.get("role")),
        "bssids": bssids,
        "physical_confirmed": record.get("physical_confirmed") is True,
        "ssids": sorted({str(value) for value in record.get("ssids", []) if str(value)}),
        "channels": sorted({str(value).strip() for value in record.get("channels", []) if str(value).strip()}, key=numeric_text_key),
        "bands": sorted({str(value).strip() for value in record.get("bands", []) if str(value).strip()}, key=band_sort_key),
        "metadata": normalize_ap_metadata(record.get("metadata")),
        "map_positions": normalize_map_positions(record.get("map_positions", {})),
        "last_seen_at": str(record.get("last_seen_at", "")).strip(),
        "last_seen_group_id": str(record.get("last_seen_group_id", "")).strip(),
    }
    return {key: value for key, value in normalized.items() if value not in ("", [], {})}


def build_empty_memory_record(bssids):
    clean = clean_bssids(bssids)
    return {
        "memory_id": build_memory_id(clean),
        "bssids": clean,
    }


def build_memory_id(bssids):
    text = "|".join(clean_bssids(bssids))
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12] if text else "empty"
    return f"ap_{digest}"


def find_best_memory_record(records, bssids):
    bssid_set = set(clean_bssids(bssids))
    if not bssid_set:
        return None

    best_record = None
    best_score = 0
    for record in records:
        if bssid_set == set(record.get("bssids", [])):
            return record
        overlap = len(bssid_set & set(record.get("bssids", [])))
        if overlap > best_score:
            best_record = record
            best_score = overlap

    return best_record if best_score > 0 else None


def summarize_observed_group_rows(rows, bssids):
    bssid_set = set(clean_bssids(bssids))
    summary = {
        "ssids": set(),
        "channels": set(),
        "bands": set(),
    }
    for row in rows or []:
        if normalize_bssid(row.get("bssid", "")) not in bssid_set:
            continue
        ssid = str(row.get("ssid", ""))
        channel = str(row.get("channel", "")).strip()
        band = get_row_band(row)
        if ssid:
            summary["ssids"].add(ssid)
        if channel:
            summary["channels"].add(channel)
        if band:
            summary["bands"].add(band)
    return summary


def build_map_memory_key(map_file):
    descriptor = build_map_descriptor(map_file)
    if not descriptor:
        return ""

    return "|".join(
        str(descriptor.get(key, ""))
        for key in ("name", "size")
        if str(descriptor.get(key, ""))
    )


def build_map_descriptor(map_file):
    path_text = str(map_file or "").strip()
    if not path_text:
        return {}

    path = Path(path_text)
    descriptor = {"name": path.name.lower()}
    try:
        if path.exists():
            descriptor["size"] = str(path.stat().st_size)
    except OSError:
        pass
    return descriptor


def find_memory_position_for_map(record, map_file):
    map_key = build_map_memory_key(map_file)
    if not map_key:
        return None

    position = normalize_ap_position((record.get("map_positions") or {}).get(map_key))
    return position


def normalize_map_positions(value):
    if not isinstance(value, dict):
        return {}

    positions = {}
    for map_key, position in value.items():
        clean_position = normalize_ap_position(position)
        if not clean_position:
            continue
        positions[str(map_key)] = {
            **clean_position,
            "map": build_map_descriptor((position or {}).get("map", {}).get("name", "")),
            "updated_at": str((position or {}).get("updated_at", "")).strip(),
        }
        if isinstance(position, dict) and isinstance(position.get("map"), dict):
            positions[str(map_key)]["map"] = position["map"]
    return positions


def clean_bssids(bssids):
    return sorted({
        normalize_bssid(bssid)
        for bssid in bssids or []
        if normalize_bssid(bssid)
    })


def numeric_text_key(value):
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 9999


def band_sort_key(value):
    return {"2.4": 0, "5": 1, "6": 2}.get(str(value), 99)


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
