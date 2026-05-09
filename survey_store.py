import csv
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from constants import RAW_SCAN_FIELDNAMES, SURVEY_FIELDNAMES


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
            self.metadata.update(read_survey_metadata(csv_file))
            self.rows = read_survey_rows(csv_file)
            self.raw_scan_rows = read_raw_scan_rows(csv_file)
            self.migrate_loaded_data()

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

    def migrate_loaded_data(self):
        changed = False

        for key, value in {
            "app": "wifi_heatmap",
            "created_at": self.metadata.get("created_at") or datetime.now().isoformat(timespec="seconds"),
        }.items():
            if not self.metadata.get(key):
                self.metadata[key] = value
                changed = True

        for row in self.rows:
            for field in SURVEY_FIELDNAMES:
                if field not in row:
                    row[field] = ""
                    changed = True

            if not row.get("point_id"):
                row["point_id"] = build_legacy_point_id(
                    row.get("timestamp", ""),
                    row.get("x", ""),
                    row.get("y", "")
                )
                changed = True

        for row in self.raw_scan_rows:
            for field in RAW_SCAN_FIELDNAMES:
                if field not in row:
                    row[field] = ""
                    changed = True

        if changed:
            self.dirty = True

    def add_points(self, x, y, networks, raw_networks=None):
        timestamp = datetime.now().isoformat(timespec="seconds")
        point_id = build_new_point_id()

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
                "radio": net["radio"]
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


def build_legacy_point_id(timestamp, x, y):
    source = f"{timestamp}|{x}|{y}"
    digest = hashlib.sha1(source.encode("utf-8", errors="ignore")).hexdigest()[:12]
    return f"legacy_{digest}"


def build_raw_scan_file_path(csv_file):
    path = Path(csv_file)
    return str(path.with_name(f"{path.stem}_raw_scans.csv"))


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


def update_survey_metadata(csv_file, updates):
    metadata = read_survey_metadata(csv_file)
    metadata.update(updates)
    rows = read_survey_rows(csv_file)
    write_survey_file(csv_file, metadata, rows)
def get_survey_points(csv_file):
    return get_survey_points_from_rows(read_survey_rows(csv_file))


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
                "timestamp": timestamp,
                "x": x,
                "y": y,
                "signal_dbm": signal_dbm
            }

    return list(points.values())
def get_survey_point_summaries(csv_file):
    return get_survey_point_summaries_from_rows(read_survey_rows(csv_file))


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
def find_survey_point_summary(csv_file, x, y):
    for point in get_survey_point_summaries(csv_file):
        if point["x"] == x and point["y"] == y:
            return point

    return None
def format_point_id(timestamp, x, y):
    return f"{timestamp}|{x}|{y}"
def save_points(csv_file, x, y, networks):
    file_exists = os.path.exists(csv_file)
    timestamp = datetime.now().isoformat(timespec="seconds")
    point_id = build_new_point_id()

    if not file_exists:
        initialize_survey_file(csv_file)

    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=SURVEY_FIELDNAMES
        )

        for net in networks:
            writer.writerow({
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
                "radio": net["radio"]
            })

    return timestamp
def delete_points_from_csv(csv_file, timestamp, x, y):
    if not os.path.exists(csv_file):
        return 0

    metadata = read_survey_metadata(csv_file)
    rows = read_survey_rows(csv_file)

    kept_rows = []
    removed_rows = 0
    removed_point_ids = set()

    for row in rows:
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

    write_survey_file(csv_file, metadata, kept_rows)

    if removed_point_ids:
        raw_rows = [
            row
            for row in read_raw_scan_rows(csv_file)
            if row.get("point_id") not in removed_point_ids
        ]
        write_raw_scan_file(csv_file, raw_rows)

    return removed_rows
