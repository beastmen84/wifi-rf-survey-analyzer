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
SCAN_DETAIL_FIELDNAMES = [
    "frequency_mhz",
    "security",
    "auth",
    "encryption",
    "pmf",
    "country_code",
    "spatial_streams",
    "stations",
    "channel_utilization",
    "wifi_modes",
    "amendments",
    "vendor",
    "model",
    "ap_name",
]
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
    "band",
    "radio",
    *SCAN_DETAIL_FIELDNAMES,
    "is_relevant",
]
OPTIONAL_SURVEY_FIELDNAMES = ["band", *SCAN_DETAIL_FIELDNAMES]
REQUIRED_SURVEY_FIELDNAMES = [
    field for field in SURVEY_FIELDNAMES if field not in OPTIONAL_SURVEY_FIELDNAMES
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
    "band",
    "radio",
    *SCAN_DETAIL_FIELDNAMES,
    "backend"
]
OPTIONAL_RAW_SCAN_FIELDNAMES = ["band", *SCAN_DETAIL_FIELDNAMES]
REQUIRED_RAW_SCAN_FIELDNAMES = [
    field for field in RAW_SCAN_FIELDNAMES if field not in OPTIONAL_RAW_SCAN_FIELDNAMES
]
