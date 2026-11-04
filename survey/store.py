"""Survey CSV and raw scan sidecar persistence layer."""

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from itertools import chain

from app_core.file_io import SurveyFileTransaction, recover_survey_save

from app_core.constants import (
    APP_ID,
    BOUNDARIES_FILE_METADATA_KEY,
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
    merge_auto_ap_group_fragments,
    merge_new_bssids_into_manual_groups,
    normalize_bssid,
    normalize_ap_metadata,
    normalize_ap_position,
    normalize_ap_role,
    is_ap_group_confirmed,
)
from ap.memory import apply_ap_memory_to_groups, update_ap_memory_from_groups
from wifi.band import get_row_band
from wifi.evidence import PROVENANCE_FIELDS, finite_number, integer, valid_signal
from wifi.adapters import CAPTURE_ADAPTER_KEY, adapter_identity

MEASUREMENT_POINTS_KEY = "measurement_points"


class SurveyFormatError(ValueError):
    pass


class SurveySession:
    def __init__(self, csv_file=None):
        self.csv_file = csv_file
        self.metadata = build_default_metadata()
        self.rows = []
        self.raw_scan_rows = []
        self.dirty = False

        if csv_file:
            recover_survey_save(csv_file)
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
        validate_coordinates(x, y)
        capture = getattr(networks, "capture", {})
        selected_id = adapter_identity(self.capture_adapter().get("id"))
        if selected_id:
            observed_ids = [capture.get("adapter_id")]
            for net in networks:
                observed_ids.append(net.get("adapter_id"))
                observed_ids.extend(sample.get("adapter_id") for sample in net.get("raw_samples", []))
            for net in raw_networks or []:
                observed_ids.append(net.get("adapter_id"))
                observed_ids.extend(sample.get("adapter_id") for sample in net.get("raw_samples", []))
            if any(adapter_identity(value) != selected_id for value in observed_ids):
                raise ValueError("capture_adapter_mismatch")
        if not networks and not (capture.get("status") == "complete" and capture.get("freshness") == "fresh"):
            raise ValueError("An empty point requires a completed, verified scan")
        timestamp = datetime.now().isoformat(timespec="seconds")
        point_id = build_new_point_id()
        new_rows, new_raw = [], []
        relevant_ssids = {
            str(ssid)
            for ssid in (relevant_ssids or [])
            if str(ssid)
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
                "is_relevant": "1" if str(net.get("ssid", "")) in relevant_ssids else "0"
            }
            row.update(copy_scan_detail_fields(net))
            row.update({field: net.get(field, "") for field in PROVENANCE_FIELDS})
            validate_measurement_row(row)
            new_rows.append(row)

        for net in raw_networks or networks:
            new_raw.extend(self.add_raw_scan_rows(point_id, timestamp, x, y, net, append=False))

        points = self.measurement_points()
        points.append(dict(point_id=point_id, timestamp=timestamp, x=x, y=y,
            status="empty" if not networks else "observed", capture=capture))
        ledger = json.dumps(points, ensure_ascii=True, allow_nan=False)
        self.rows.extend(new_rows)
        self.raw_scan_rows.extend(new_raw)
        self.metadata[MEASUREMENT_POINTS_KEY] = ledger

        self.refresh_ap_groups_from_rows(update_memory=True)
        self.dirty = True
        return timestamp

    def capture_adapter(self):
        try:
            adapter = json.loads(self.metadata.get(CAPTURE_ADAPTER_KEY, "{}"))
        except (TypeError, ValueError):
            return {}
        if not isinstance(adapter, dict) or not isinstance(adapter.get("id"), str) or not adapter_identity(adapter["id"]):
            return {}
        return {key: str(adapter.get(key, "")) for key in ("id", "name", "description")}

    def set_capture_adapter(self, adapter, mark_dirty=True):
        if not adapter_identity(adapter.get("id")):
            raise ValueError("capture_adapter_unavailable")
        current = self.capture_adapter()
        if current and adapter_identity(current["id"]) != adapter_identity(adapter["id"]):
            raise ValueError("capture_adapter_mismatch")
        value = json.dumps({key: str(adapter.get(key, "")) for key in ("id", "name", "description")}, ensure_ascii=True)
        changed = self.metadata.get(CAPTURE_ADAPTER_KEY) != value
        self.metadata[CAPTURE_ADAPTER_KEY] = value
        if changed and mark_dirty:
            self.dirty = True

    def add_raw_scan_rows(self, point_id, timestamp, x, y, network, append=True):
        rows = []
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
            row.update({field: sample.get(field, "") for field in PROVENANCE_FIELDS})
            validate_measurement_row(row, raw=True)
            rows.append(row)
        if append:
            self.raw_scan_rows.extend(rows)
        return rows

    def measurement_points(self):
        try:
            points = json.loads(self.metadata.get(MEASUREMENT_POINTS_KEY, "[]"))
            if not isinstance(points, list):
                raise ValueError("Expected point list")
            for point in points:
                validate_coordinates(point["x"], point["y"])
                if not point.get("point_id") or not point.get("timestamp") or point.get("status") not in {"empty", "observed"}:
                    raise ValueError("Invalid measurement point")
                if point["status"] == "empty":
                    capture = point.get("capture", {})
                    if capture.get("status") != "complete" or capture.get("freshness") != "fresh":
                        raise ValueError("Unverified empty measurement")
            if len({p["point_id"] for p in points}) != len(points):
                raise ValueError("Duplicate measurement point ID")
            return points
        except (ValueError, TypeError, KeyError) as exc:
            raise SurveyFormatError("invalid_survey_format") from exc

    def delete_point(self, timestamp, x, y, point_id=None):
        kept_rows = []
        removed_rows = 0
        removed_point_ids = set()

        for row in self.rows:
            try:
                row_x = int(float(row.get("x", "")))
                row_y = int(float(row.get("y", "")))
            except (ValueError, TypeError, OverflowError):
                row_x = None
                row_y = None

            is_same_point = (
                row.get("point_id") == point_id if point_id else
                row.get("timestamp") == timestamp and row_x == x and row_y == y
            )

            if is_same_point:
                if row.get("point_id"):
                    removed_point_ids.add(row.get("point_id"))
                removed_rows += 1
            else:
                kept_rows.append(row)

        ledger = self.measurement_points()
        kept_points = [p for p in ledger if not (p["point_id"] == point_id if point_id else
            p["timestamp"] == timestamp and p["x"] == x and p["y"] == y)]
        removed_points = len(ledger) - len(kept_points)
        if removed_rows or removed_points:
            self.metadata[MEASUREMENT_POINTS_KEY] = json.dumps(kept_points, ensure_ascii=True)
            self.rows = kept_rows
            self.raw_scan_rows = [
                row
                for row in self.raw_scan_rows
                if row.get("point_id") not in removed_point_ids
            ]
            self.dirty = True

        return removed_rows or removed_points

    def get_points(self):
        points = get_survey_points_from_rows(self.rows)
        points.extend({**p, "signal_dbm": None} for p in self.measurement_points() if p["status"] == "empty")
        return points

    def get_point_summaries(self):
        points = get_survey_point_summaries_from_rows(self.rows)
        points.extend({**p, "best_signal_dbm": None, "best_relevant_signal_dbm": None,
            "signal_scope": "all", "ssids": [], "row_count": 0, "relevant_row_count": 0}
            for p in self.measurement_points() if p["status"] == "empty")
        return sorted(points, key=lambda p: p["timestamp"])

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
                "physical_confirmed": is_ap_group_confirmed(group),
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
        groups = merge_auto_ap_group_fragments(groups, self.rows)

        return self.set_ap_groups(groups, update_memory=update_memory)

    def to_dataframe(self):
        import pandas as pd

        return pd.DataFrame(self.rows, columns=SURVEY_FIELDNAMES)

    def save(self, csv_file=None, transaction=None):
        destination = csv_file or self.csv_file
        if not destination:
            raise ValueError("Percorso CSV non impostato")

        metadata = dict(self.metadata)
        metadata.update({
            "app": APP_ID,
            "schema_version": SURVEY_SCHEMA_VERSION,
        })
        metadata[MEASUREMENT_SYSTEM_METADATA_KEY] = normalize_survey_measurement_system(metadata)
        if self.csv_file and Path(destination).absolute() != Path(self.csv_file).absolute():
            metadata[RAW_DATA_FILE_METADATA_KEY] = build_default_raw_data_filename(destination)
        metadata[RAW_DATA_FILE_METADATA_KEY] = os.path.basename(
            str(metadata.get(RAW_DATA_FILE_METADATA_KEY, "")).strip()
            or build_default_raw_data_filename(destination)
        )
        if transaction is None:
            with SurveyFileTransaction(destination) as owned_transaction:
                self._stage_save(destination, metadata, owned_transaction)
                owned_transaction.commit()
        else:
            self._stage_save(destination, metadata, transaction)
            transaction.commit()
        self.csv_file = destination
        self.metadata = metadata
        self.dirty = False
        return self.csv_file

    def _stage_save(self, destination, metadata, transaction):
        if Path(destination).absolute() != transaction.csv_file:
            raise ValueError("Survey transaction belongs to a different CSV")
        csv_stage = transaction.stage_file(destination)
        raw_stage = transaction.stage_file(build_raw_scan_file_path(destination, metadata))
        write_survey_file(csv_stage, metadata, self.rows)
        write_raw_scan_rows(raw_stage, self.raw_scan_rows)


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


def build_default_boundaries_filename(csv_file):
    path = Path(csv_file)
    return f"{path.stem}.boundaries.png"


def build_boundaries_file_path(csv_file, metadata=None):
    path = Path(csv_file)
    metadata = metadata if metadata is not None else read_survey_metadata(csv_file)
    boundaries_file = str(metadata.get(BOUNDARIES_FILE_METADATA_KEY, "")).strip()
    if not boundaries_file:
        boundaries_file = build_default_boundaries_filename(csv_file)

    return str(path.with_name(os.path.basename(boundaries_file)))


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
    try:
        for row in read_survey_rows(csv_file):
            validate_measurement_row(row)
        for row in read_raw_scan_rows(csv_file):
            validate_measurement_row(row, raw=True)
        ledger = SurveySession()
        ledger.metadata = metadata
        ledger.measurement_points()
    except (ValueError, TypeError, OverflowError) as exc:
        raise SurveyFormatError("invalid_survey_format") from exc


def validate_coordinates(x, y):
    if any(finite_number(v) is None or not 0 <= float(v) <= 1_000_000_000 for v in (x, y)):
        raise ValueError("Invalid measurement coordinates")


def validate_measurement_row(row, raw=False):
    validate_coordinates(row.get("x"), row.get("y"))
    if not valid_signal(row.get("signal_dbm")):
        raise ValueError("Invalid RSSI")
    ranges = {"signal_percent": (0, 100), "scan_confidence": (0, 1),
              "samples_seen": (0, 1_000_000), "samples_total": (0, 1_000_000),
              "channel": (1, 233), "scan_attempt": (1, 1_000_000)}
    for field, (low, high) in ranges.items():
        value = row.get(field)
        if value is None or value == "":
            continue
        parsed = finite_number(value)
        if parsed is None or not low <= parsed <= high or (field in {"channel", "samples_seen", "samples_total", "scan_attempt"} and not parsed.is_integer()):
            raise ValueError(f"Invalid {field}")
    for field in ("signal_min_dbm", "signal_max_dbm", "signal_median_dbm"):
        if row.get(field) not in (None, "") and not valid_signal(row[field]):
            raise ValueError(f"Invalid {field}")
    width = row.get("channel_width_mhz")
    if width not in (None, "", "80+80") and finite_number(width) not in {20, 40, 80, 160, 320}:
        raise ValueError("Invalid channel width")
    seen, total = integer(row.get("samples_seen")), integer(row.get("samples_total"))
    if seen is not None and total is not None and seen > total:
        raise ValueError("Invalid sample counts")
    low, high = finite_number(row.get("signal_min_dbm")), finite_number(row.get("signal_max_dbm"))
    if low is not None and high is not None and not low <= float(row["signal_dbm"]) <= high:
        raise ValueError("Inconsistent RSSI range")
    samples = row.get("signal_samples_dbm")
    if samples and any(not valid_signal(v) for v in str(samples).split(";")):
        raise ValueError("Invalid RSSI sample")


def read_csv_header(csv_file):
    if not os.path.exists(csv_file):
        raise SurveyFormatError("missing_survey_file")

    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(iter_csv_data_lines(f))
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
        return list(csv.DictReader(iter_csv_data_lines(f)))


def iter_csv_data_lines(stream):
    """Skip only the metadata prefix; quoted CSV fields may contain '#'."""
    for line in stream:
        if line.strip() and not line.lstrip().startswith("#"):
            return chain((line,), stream)
    return iter(())


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
    write_raw_scan_rows(raw_scan_file, rows)


def write_raw_scan_rows(raw_scan_file, rows):
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
        except (ValueError, TypeError, OverflowError):
            continue

        if not timestamp:
            continue
        if not valid_signal(signal_dbm):
            continue

        key = row.get("point_id") or (timestamp, x, y)
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
        except (ValueError, TypeError, OverflowError):
            continue

        if not timestamp:
            continue
        if not valid_signal(signal_dbm):
            continue

        key = row.get("point_id") or (timestamp, x, y)
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
