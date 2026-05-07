import csv
import json
import os
from datetime import datetime

from constants import SURVEY_FIELDNAMES


class SurveySession:
    def __init__(self, csv_file=None):
        self.csv_file = csv_file
        self.metadata = {
            "app": "wifi_heatmap",
            "created_at": datetime.now().isoformat(timespec="seconds")
        }
        self.rows = []
        self.dirty = False

        if csv_file and os.path.exists(csv_file):
            self.metadata.update(read_survey_metadata(csv_file))
            self.rows = read_survey_rows(csv_file)
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

        if changed:
            self.dirty = True

    def add_points(self, x, y, networks):
        timestamp = datetime.now().isoformat(timespec="seconds")

        for net in networks:
            self.rows.append({
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

        self.dirty = True
        return timestamp

    def delete_point(self, timestamp, x, y):
        kept_rows = []
        removed_rows = 0

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
                removed_rows += 1
            else:
                kept_rows.append(row)

        if removed_rows:
            self.rows = kept_rows
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
        self.dirty = False
        return self.csv_file


def initialize_survey_file(csv_file):
    metadata = {
        "app": "wifi_heatmap",
        "created_at": datetime.now().isoformat(timespec="seconds")
    }
    write_survey_file(csv_file, metadata, [])
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
def write_survey_file(csv_file, metadata, rows):
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        for key, value in metadata.items():
            f.write(f"# {key}={value}\n")

        writer = csv.DictWriter(f, fieldnames=SURVEY_FIELDNAMES)
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

    if not file_exists:
        initialize_survey_file(csv_file)

    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=SURVEY_FIELDNAMES
        )

        for net in networks:
            writer.writerow({
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
            removed_rows += 1
        else:
            kept_rows.append(row)

    write_survey_file(csv_file, metadata, kept_rows)

    return removed_rows
