"""Shared constants for survey files, scan attempts, and map rendering."""

from wifi.evidence import PROVENANCE_FIELDS

APP_ID = "wifi_heatmap"
SURVEY_SCHEMA_VERSION = "2"
RAW_DATA_FILE_METADATA_KEY = "raw_data_file"
BOUNDARIES_FILE_METADATA_KEY = "boundaries_file"
MEASUREMENT_SYSTEM_METADATA_KEY = "measurement_system"
DEFAULT_FLOORPLAN_METADATA_KEY = "_default_floorplan"
GENERATED_FLOORPLAN_METADATA_KEY = "_generated_floorplan"
DEFAULT_FLOORPLAN_WIDTH_PX = 1750
DEFAULT_FLOORPLAN_HEIGHT_PX = 1250
DEFAULT_FLOORPLAN_METRIC_PX_PER_METER = 50.0
DEFAULT_FLOORPLAN_IMPERIAL_PX_PER_FOOT = 16.0
HEATMAP_GRID_SIZE = 700
HEATMAP_SMOOTHING_SIGMA = 5.0
HEATMAP_MAX_DISTANCE_PX = 260
HEATMAP_ADAPTIVE_MAX_DISTANCE_MIN_METERS = 3.0
HEATMAP_ADAPTIVE_MAX_DISTANCE_MAX_METERS = 6.0
HEATMAP_ADAPTIVE_MAX_DISTANCE_MULTIPLIER = 1.6
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
    "is_connected",
    "is_relevant",
]
REQUIRED_SURVEY_FIELDNAMES = list(SURVEY_FIELDNAMES)
# Optional extension: old schema-2 surveys remain readable with unknown provenance.
SURVEY_FIELDNAMES += [field for field in PROVENANCE_FIELDS if field not in SURVEY_FIELDNAMES]

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
    "is_connected",
    "backend"
]
REQUIRED_RAW_SCAN_FIELDNAMES = list(RAW_SCAN_FIELDNAMES)
RAW_SCAN_FIELDNAMES += [field for field in PROVENANCE_FIELDS if field not in RAW_SCAN_FIELDNAMES]
