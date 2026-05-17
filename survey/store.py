"""Survey CSV and raw scan sidecar persistence layer."""

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app_core.constants import (
    APP_ID,
    MEASUREMENT_SYSTEM_METADATA_KEY,
    RAW_DATA_FILE_METADATA_KEY,
    RAW_SCAN_FIELDNAMES,
    REQUIRED_RAW_SCAN_FIELDNAMES,
    REQUIRED_SURVEY_FIELDNAMES,
    SCAN_DETAIL_FIELDNAMES,
    SURVEY_FIELDNAMES,
    SURVEY_SCHEMA_VERSION,
)
from app_core.units import (
    MEASUREMENT_SYSTEM_METRIC,
    normalize_measurement_system,
)
from ap.groups import (
    AP_GROUPS_METADATA_KEY,
    AP_MEMORY_APPLIED_AT_KEY,
    AP_MEMORY_APPLIED_KEY,
    AP_MEMORY_MATCH_BSSIDS_KEY,
    build_default_manual_groups,
    merge_new_bssids_into_manual_groups,
    normalize_bssid,
    normalize_ap_metadata,
    normalize_ap_position,
    normalize_ap_role,
)
from ap.memory import apply_ap_memory_to_groups, update_ap_memory_from_groups
from wifi.band import get_row_band


class SurveyFormatError(ValueError):
    pass


class SurveySession:
    def __init__(self, csv_file=None):
        self.csv_file = csv_file
        self.metadata = build_default_metadata()
        self.rows = []
        self.raw_scan_rows = []
        self.dirty = False

        if csv_file and os.path.exists(csv_file):
            validate_survey_file(csv_file)
            loaded_metadata = read_survey_metadata(csv_file)
            self.metadata.update(loaded_metadata)
            self.metadata[MEASUREMENT_SYSTEM_METADATA_KEY] = normalize_survey_measurement_system(self.metadata)
            self.rows = read_survey_rows(csv_file)
            self.raw_scan_rows = read_raw_scan_rows(csv_file)
            self.refresh_ap_groups_from_rows(update_memory=False)

    @property
    def display_name(self):
        if self.csv_file:
            return os.path.basename(self.csv_file)

        return "Rilievo non salvato"

    def update_metadata(self, updates):
        changed = any(self.metadata.get(key) != value for key, value in updates.items())
        self.metadata.update(updates)

        if changed:
            self.dirty = True

    def measurement_system(self, default=MEASUREMENT_SYSTEM_METRIC):
        return normalize_survey_measurement_system(self.metadata, default=default)

    def set_measurement_system(self, measurement_system, mark_dirty=True):
        measurement_system = normalize_measurement_system(measurement_system)
        changed = self.metadata.get(MEASUREMENT_SYSTEM_METADATA_KEY) != measurement_system
        self.metadata[MEASUREMENT_SYSTEM_METADATA_KEY] = measurement_system
        if changed and mark_dirty:
            self.dirty = True
        return measurement_system

    def add_points(self, x, y, networks, raw_networks=None, relevant_ssids=None):
        timestamp = datetime.now().isoformat(timespec="seconds")
        point_id = build_new_point_id()
        relevant_ssids = {
            str(ssid).lower()
            for ssid in (relevant_ssids or [])
            if str(ssid).strip()
        }

        for net in networks:
            row = {
                "point_id": point_id,
                "timestamp": timestamp,
                "x": x,
                "y": y,
                "ssid": net["ssid"],
                "bssid": net["bssid"],
                "signal_percent": net["signal_percent"],
                "signal_dbm": net["signal_dbm"],
                "signal_median_dbm": net.get("signal_median_dbm", net["signal_dbm"]),
                "signal_max_dbm": net.get("signal_max_dbm", net["signal_dbm"]),
                "signal_min_dbm": net.get("signal_min_dbm", net["signal_dbm"]),
                "signal_samples_dbm": net.get("signal_samples_dbm", ""),
                "samples_seen": net.get("samples_seen", ""),
                "samples_total": net.get("samples_total", ""),
                "scan_confidence": net.get("scan_confidence", ""),
                "channel": net["channel"],
                "channel_width_mhz": net.get("channel_width_mhz", ""),
                "band": get_row_band(net),
                "radio": net["radio"],
                "is_connected": bool_flag(net.get("is_connected")),
                "is_relevant": "1" if str(net.get("ssid", "")).lower() in relevant_ssids else "0"
            }
            row.update(copy_scan_detail_fields(net))
            self.rows.append(row)

        for net in raw_networks or networks:
            self.add_raw_scan_rows(point_id, timestamp, x, y, net)

        self.refresh_ap_groups_from_rows(update_memory=True)
        self.dirty = True
        return timestamp

    def add_raw_scan_rows(self, point_id, timestamp, x, y, network):
        raw_samples = network.get("raw_samples") or []
        for sample in raw_samples:
            row = {
                "point_id": point_id,
                "scan_attempt": sample.get("scan_attempt", ""),
                "timestamp": timestamp,
                "x": x,
                "y": y,
                "ssid": sample.get("ssid", ""),
                "bssid": sample.get("bssid", ""),
                "signal_percent": sample.get("signal_percent", ""),
                "signal_dbm": sample.get("signal_dbm", ""),
                "channel": sample.get("channel", ""),
                "channel_width_mhz": sample.get("channel_width_mhz", ""),
                "band": get_row_band(sample),
                "radio": sample.get("radio", ""),
                "is_connected": bool_flag(sample.get("is_connected")),
                "backend": sample.get("backend", "")
            }
            row.update(copy_scan_detail_fields(sample))
            self.raw_scan_rows.append(row)

    def delete_point(self, timestamp, x, y):
        kept_rows = []
        removed_rows = 0
        removed_point_ids = set()

        for row in self.rows:
            try:
                row_x = int(float(row.get("x", "")))
                row_y = int(float(row.get("y", "")))
            except ValueError:
                row_x = None
                row_y = None

            is_same_point = (
                row.get("timestamp") == timestamp
                and row_x == x
                and row_y == y
            )

            if is_same_point:
                if row.get("point_id"):
                    removed_point_ids.add(row.get("point_id"))
                removed_rows += 1
            else:
                kept_rows.append(row)

        if removed_rows:
            self.rows = kept_rows
            self.raw_scan_rows = [
                row
                for row in self.raw_scan_rows
                if row.get("point_id") not in removed_point_ids
            ]
            self.dirty = True

        return removed_rows

    def get_points(self):
        return get_survey_points_from_rows(self.rows)

    def get_point_summaries(self):
        return get_survey_point_summaries_from_rows(self.rows)

    def find_point_summary(self, x, y):
        for point in self.get_point_summaries():
            if point["x"] == x and point["y"] == y:
                return point

        return None

    def get_ssids(self):
        return sorted({
            row.get("ssid", "")
            for row in self.rows
            if row.get("ssid")
        })

    def get_ap_aliases(self):
        aliases = {}
        ap_groups = self.get_ap_groups()
        for group in ap_groups:
            group_id = str(group.get("group_id", ""))
            alias = str(group.get("alias", "")).strip()
            if group_id and alias:
                aliases[group_id] = alias

        return aliases

    def get_ap_groups(self):
        try:
            groups = json.loads(self.metadata.get(AP_GROUPS_METADATA_KEY, "[]"))
        except json.JSONDecodeError:
            groups = []

        return groups if isinstance(groups, list) else []

    def set_ap_groups(self, groups, update_memory=True, force_memory_update=False):
        clean_groups = []
        for group in groups:
            if not isinstance(group, dict):
                continue

            group_id = str(group.get("group_id", "")).strip()
            bssids = [
                str(bssid).strip().lower()
                for bssid in group.get("bssids", [])
                if str(bssid).strip()
            ]
            if not group_id or not bssids:
                continue

            clean_group = {
                "group_id": group_id,
                "alias": str(group.get("alias", "")).strip(),
                "bssids": sorted(set(bssids)),
                "locked": bool(group.get("locked", False)),
                "role": normalize_ap_role(group.get("role")),
            }
            position = normalize_ap_position(group.get("position"))
            if position:
                clean_group["position"] = position

            metadata = normalize_ap_metadata(group.get("metadata"))
            if metadata:
                clean_group["metadata"] = metadata

            if group.get(AP_MEMORY_APPLIED_KEY):
                clean_group[AP_MEMORY_APPLIED_KEY] = True
                applied_at = str(group.get(AP_MEMORY_APPLIED_AT_KEY, "")).strip()
                if applied_at:
                    clean_group[AP_MEMORY_APPLIED_AT_KEY] = applied_at
                match_bssids = sorted({
                    normalize_bssid(bssid)
                    for bssid in group.get(AP_MEMORY_MATCH_BSSIDS_KEY, [])
                    if normalize_bssid(bssid)
                })
                if match_bssids:
                    clean_group[AP_MEMORY_MATCH_BSSIDS_KEY] = match_bssids

            clean_groups.append(clean_group)

        serialized_groups = json.dumps(clean_groups, ensure_ascii=False, sort_keys=True)
        changed = self.metadata.get(AP_GROUPS_METADATA_KEY) != serialized_groups
        self.update_metadata({AP_GROUPS_METADATA_KEY: serialized_groups})
        if update_memory and (changed or force_memory_update):
            update_ap_memory_from_groups(clean_groups, self.rows, self.metadata.get("map_file", ""))
        return changed

    def refresh_ap_groups_from_rows(self, update_memory=True):
        if not self.rows:
            return False

        saved_groups = self.get_ap_groups()
        groups = (
            merge_new_bssids_into_manual_groups(saved_groups, self.rows)
            if saved_groups
            else build_default_manual_groups(self.rows)
        )
        groups, _applied_count = apply_ap_memory_to_groups(
            groups,
            self.rows,
            self.metadata.get("map_file", ""),
        )

        return self.set_ap_groups(groups, update_memory=update_memory)

    def to_dataframe(self):
        import pandas as pd

        return pd.DataFrame(self.rows, columns=SURVEY_FIELDNAMES)

    def save(self, csv_file=None):
        if csv_file:
            self.csv_file = csv_file

        if not self.csv_file:
            raise ValueError("Percorso CSV non impostato")

        self.metadata.update({
            "app": APP_ID,
            "schema_version": SURVEY_SCHEMA_VERSION,
        })
        self.metadata[MEASUREMENT_SYSTEM_METADATA_KEY] = normalize_survey_measurement_system(self.metadata)
        self.metadata[RAW_DATA_FILE_METADATA_KEY] = os.path.basename(
            str(self.metadata.get(RAW_DATA_FILE_METADATA_KEY, "")).strip()
            or build_default_raw_data_filename(self.csv_file)
        )
        write_survey_file(self.csv_file, self.metadata, self.rows)
        write_raw_scan_file(self.csv_file, self.raw_scan_rows, self.metadata)
        self.dirty = False
        return self.csv_file


def build_default_metadata(csv_file=None):
    metadata = {
        "app": APP_ID,
        "schema_version": SURVEY_SCHEMA_VERSION,
        MEASUREMENT_SYSTEM_METADATA_KEY: MEASUREMENT_SYSTEM_METRIC,
        "created_at": datetime.now().isoformat(timespec="seconds")
    }
    if csv_file:
        metadata[RAW_DATA_FILE_METADATA_KEY] = build_default_raw_data_filename(csv_file)

    return metadata


def normalize_survey_measurement_system(metadata, default=MEASUREMENT_SYSTEM_METRIC):
    metadata = metadata or {}
    return normalize_measurement_system(metadata.get(MEASUREMENT_SYSTEM_METADATA_KEY), default=default)


def copy_scan_detail_fields(network):
    return {
        field: network.get(field, "")
        for field in SCAN_DETAIL_FIELDNAMES
    }


def bool_flag(value):
    if isinstance(value, str):
        return "1" if value.strip().lower() in {"1", "true", "yes", "y", "connected"} else "0"

    return "1" if bool(value) else "0"


def build_new_point_id():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"p_{timestamp}_{uuid4().hex[:8]}"


def build_default_raw_data_filename(csv_file):
    path = Path(csv_file)
    return f"{path.stem}_raw_data.scan"


def build_raw_scan_file_path(csv_file, metadata=None):
    path = Path(csv_file)
    metadata = metadata if metadata is not None else read_survey_metadata(csv_file)
    raw_data_file = str(metadata.get(RAW_DATA_FILE_METADATA_KEY, "")).strip()
    if not raw_data_file:
        raise SurveyFormatError("invalid_survey_format")

    return str(path.with_name(os.path.basename(raw_data_file)))


def is_raw_scan_file(csv_file):
    path = Path(csv_file)
    return path.suffix.lower() == ".scan"


def validate_survey_file(csv_file):
    if is_raw_scan_file(csv_file):
        raise SurveyFormatError("raw_scan_file")

    metadata = read_survey_metadata(csv_file)
    if (
        metadata.get("app") != APP_ID
        or metadata.get("schema_version") != SURVEY_SCHEMA_VERSION
        or not metadata.get(RAW_DATA_FILE_METADATA_KEY)
        or normalize_survey_measurement_system(metadata, default="") == ""
    ):
        raise SurveyFormatError("invalid_survey_format")

    header = read_csv_header(csv_file)
    missing_fields = [field for field in REQUIRED_SURVEY_FIELDNAMES if field not in header]
    if missing_fields:
        raise SurveyFormatError("invalid_survey_format")

    raw_scan_file = build_raw_scan_file_path(csv_file, metadata)
    if not os.path.exists(raw_scan_file):
        raise SurveyFormatError("invalid_raw_scan_format")

    raw_header = read_csv_header(raw_scan_file)
    missing_raw_fields = [field for field in REQUIRED_RAW_SCAN_FIELDNAMES if field not in raw_header]
    if missing_raw_fields:
        raise SurveyFormatError("invalid_raw_scan_format")


def read_csv_header(csv_file):
    if not os.path.exists(csv_file):
        raise SurveyFormatError("missing_survey_file")

    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        data_lines = [line for line in f if not line.lstrip().startswith("#")]

    if not data_lines:
        raise SurveyFormatError("invalid_survey_format")

    reader = csv.DictReader(data_lines)
    return reader.fieldnames or []


def read_survey_metadata(csv_file):
    metadata = {}

    if not os.path.exists(csv_file):
        return metadata

    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        for line in f:
            stripped_line = line.strip()

            if not stripped_line:
                continue

            if not stripped_line.startswith("#"):
                break

            entry = stripped_line[1:].strip()
            if "=" not in entry:
                continue

            key, value = entry.split("=", 1)
            metadata[key.strip()] = value.strip()

    return metadata
def read_survey_rows(csv_file):
    if not os.path.exists(csv_file):
        return []

    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        data_lines = [line for line in f if not line.lstrip().startswith("#")]

    if not data_lines:
        return []

    reader = csv.DictReader(data_lines)
    return list(reader)


def read_raw_scan_rows(csv_file):
    metadata = read_survey_metadata(csv_file)
    raw_scan_file = build_raw_scan_file_path(csv_file, metadata)
    if not os.path.exists(raw_scan_file):
        return []

    with open(raw_scan_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_survey_file(csv_file, metadata, rows):
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        for key, value in metadata.items():
            f.write(f"# {key}={value}\n")

        writer = csv.DictWriter(f, fieldnames=SURVEY_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_raw_scan_file(csv_file, rows, metadata=None):
    raw_scan_file = build_raw_scan_file_path(csv_file, metadata)
    with open(raw_scan_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_SCAN_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def get_survey_points_from_rows(rows):
    points = {}

    for row in rows:
        timestamp = row.get("timestamp")

        try:
            x = int(float(row.get("x", "")))
            y = int(float(row.get("y", "")))
            signal_dbm = float(row.get("signal_dbm", ""))
        except ValueError:
            continue

        if not timestamp:
            continue

        key = (timestamp, x, y)
        if key not in points or signal_dbm > points[key]["signal_dbm"]:
            points[key] = {
                "point_id": row.get("point_id", ""),
                "timestamp": timestamp,
                "x": x,
                "y": y,
                "signal_dbm": signal_dbm
            }

    return list(points.values())
def get_survey_point_summaries_from_rows(rows):
    points = {}

    for row in rows:
        timestamp = row.get("timestamp")
        ssid = row.get("ssid")

        try:
            x = int(float(row.get("x", "")))
            y = int(float(row.get("y", "")))
            signal_dbm = float(row.get("signal_dbm", ""))
        except ValueError:
            continue

        if not timestamp:
            continue

        key = (timestamp, x, y)
        point = points.setdefault(
            key,
            {
                "point_id": row.get("point_id", ""),
                "timestamp": timestamp,
                "x": x,
                "y": y,
                "best_signal_dbm": signal_dbm,
                "best_relevant_signal_dbm": None,
                "ssids": set(),
                "row_count": 0,
                "relevant_row_count": 0
            }
        )
        point["best_signal_dbm"] = max(point["best_signal_dbm"], signal_dbm)
        point["row_count"] += 1
        if str(row.get("is_relevant", "")).strip() == "1":
            point["best_relevant_signal_dbm"] = (
                signal_dbm
                if point["best_relevant_signal_dbm"] is None
                else max(point["best_relevant_signal_dbm"], signal_dbm)
            )
            point["relevant_row_count"] += 1

        if ssid:
            point["ssids"].add(ssid)

    summaries = []

    for point in points.values():
        if point["best_relevant_signal_dbm"] is not None:
            best_signal_dbm = point["best_relevant_signal_dbm"]
            signal_scope = "relevant"
        else:
            best_signal_dbm = point["best_signal_dbm"]
            signal_scope = "all"

        summaries.append({
            **point,
            "best_signal_dbm": best_signal_dbm,
            "signal_scope": signal_scope,
            "ssids": sorted(point["ssids"])
        })

    return sorted(summaries, key=lambda point: point["timestamp"])
def format_point_id(timestamp, x, y):
    return f"{timestamp}|{x}|{y}"
