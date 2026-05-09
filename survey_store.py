import csv
import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from constants import RAW_SCAN_FIELDNAMES, SURVEY_FIELDNAMES


class SurveyFormatError(ValueError):
    pass


class SurveySession:
    def __init__(self, csv_file=None):
        self.csv_file = csv_file
        self.metadata = {
            "app": "wifi_heatmap",
            "created_at": datetime.now().isoformat(timespec="seconds")
        }
        self.rows = []
        self.raw_scan_rows = []
        self.dirty = False

        if csv_file and os.path.exists(csv_file):
            validate_survey_file(csv_file)
            self.metadata.update(read_survey_metadata(csv_file))
            self.rows = read_survey_rows(csv_file)
            self.raw_scan_rows = read_raw_scan_rows(csv_file)

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

    def add_points(self, x, y, networks, raw_networks=None, relevant_ssids=None):
        timestamp = datetime.now().isoformat(timespec="seconds")
        point_id = build_new_point_id()
        relevant_ssids = {
            str(ssid).lower()
            for ssid in (relevant_ssids or [])
            if str(ssid).strip()
        }

        for net in networks:
            self.rows.append({
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
                "radio": net["radio"],
                "is_relevant": "1" if str(net.get("ssid", "")).lower() in relevant_ssids else "0"
            })

        for net in raw_networks or networks:
            self.add_raw_scan_rows(point_id, timestamp, x, y, net)

        self.dirty = True
        return timestamp

    def add_raw_scan_rows(self, point_id, timestamp, x, y, network):
        raw_samples = network.get("raw_samples") or []
        for sample in raw_samples:
            self.raw_scan_rows.append({
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
                "radio": sample.get("radio", ""),
                "backend": sample.get("backend", "")
            })

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
        try:
            aliases = json.loads(self.metadata.get("ap_aliases", "{}"))
        except json.JSONDecodeError:
            aliases = {}

        if not isinstance(aliases, dict):
            return {}

        return {str(key): str(value) for key, value in aliases.items() if value}

    def set_ap_aliases(self, aliases):
        clean_aliases = {
            str(key): str(value).strip()
            for key, value in aliases.items()
            if str(value).strip()
        }
        serialized_aliases = json.dumps(clean_aliases, ensure_ascii=False, sort_keys=True)
        changed = self.metadata.get("ap_aliases") != serialized_aliases
        self.update_metadata({"ap_aliases": serialized_aliases})
        return changed

    def to_dataframe(self):
        import pandas as pd

        return pd.DataFrame(self.rows, columns=SURVEY_FIELDNAMES)

    def save(self, csv_file=None):
        if csv_file:
            self.csv_file = csv_file

        if not self.csv_file:
            raise ValueError("Percorso CSV non impostato")

        self.metadata["raw_data_file"] = os.path.basename(build_raw_scan_file_path(self.csv_file))
        write_survey_file(self.csv_file, self.metadata, self.rows)
        write_raw_scan_file(self.csv_file, self.raw_scan_rows)
        self.dirty = False
        return self.csv_file


def initialize_survey_file(csv_file):
    metadata = {
        "app": "wifi_heatmap",
        "created_at": datetime.now().isoformat(timespec="seconds")
    }
    write_survey_file(csv_file, metadata, [])


def build_new_point_id():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"p_{timestamp}_{uuid4().hex[:8]}"


def build_raw_scan_file_path(csv_file):
    path = Path(csv_file)
    raw_data_file = read_survey_metadata(csv_file).get("raw_data_file") if os.path.exists(csv_file) else ""
    if raw_data_file:
        return str(path.with_name(raw_data_file))

    return str(path.with_name(f"{path.stem}_raw_data.scan"))


def is_raw_scan_file(csv_file):
    path = Path(csv_file)
    return path.name.endswith("_raw_data.scan") or path.stem.endswith("_raw_scans")


def validate_survey_file(csv_file):
    if is_raw_scan_file(csv_file):
        raise SurveyFormatError("raw_scan_file")

    header = read_csv_header(csv_file)
    missing_fields = [field for field in SURVEY_FIELDNAMES if field not in header]
    if missing_fields:
        raise SurveyFormatError("invalid_survey_format")

    raw_scan_file = build_raw_scan_file_path(csv_file)
    if os.path.exists(raw_scan_file):
        raw_header = read_csv_header(raw_scan_file)
        missing_raw_fields = [field for field in RAW_SCAN_FIELDNAMES if field not in raw_header]
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
    raw_scan_file = build_raw_scan_file_path(csv_file)
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


def write_raw_scan_file(csv_file, rows):
    raw_scan_file = build_raw_scan_file_path(csv_file)
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
                "ssids": set(),
                "row_count": 0
            }
        )
        point["best_signal_dbm"] = max(point["best_signal_dbm"], signal_dbm)
        point["row_count"] += 1

        if ssid:
            point["ssids"].add(ssid)

    summaries = []

    for point in points.values():
        summaries.append({
            **point,
            "ssids": sorted(point["ssids"])
        })

    return sorted(summaries, key=lambda point: point["timestamp"])
def format_point_id(timestamp, x, y):
    return f"{timestamp}|{x}|{y}"
