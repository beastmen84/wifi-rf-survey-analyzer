"""Shared constants for survey files, scan attempts, and map rendering."""

APP_ID = "wifi_heatmap"
SURVEY_SCHEMA_VERSION = "2"
RAW_DATA_FILE_METADATA_KEY = "raw_data_file"
HEATMAP_GRID_SIZE = 700
HEATMAP_SMOOTHING_SIGMA = 3.0
HEATMAP_MAX_DISTANCE_PX = 180
WIFI_SCAN_ATTEMPTS = 5
WIFI_SCAN_DELAY_SECONDS = 1.5
MIN_GOOD_SCAN_NETWORKS = 4
SUSPICIOUS_SCAN_RATIO = 0.5
SURVEY_FIELDNAMES = [
    "point_id",
    "timestamp",
    "x",
    "y",
    "ssid",
    "bssid",
    "signal_percent",
    "signal_dbm",
    "signal_median_dbm",
    "signal_max_dbm",
    "signal_min_dbm",
    "signal_samples_dbm",
    "samples_seen",
    "samples_total",
    "scan_confidence",
    "channel",
    "channel_width_mhz",
    "radio",
    "is_relevant",
]

RAW_SCAN_FIELDNAMES = [
    "point_id",
    "scan_attempt",
    "timestamp",
    "x",
    "y",
    "ssid",
    "bssid",
    "signal_percent",
    "signal_dbm",
    "channel",
    "channel_width_mhz",
    "radio",
    "backend"
]
