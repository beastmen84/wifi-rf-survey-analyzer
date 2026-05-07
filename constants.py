CSV_PREFIX = "wifi_survey"
HEATMAP_GRID_SIZE = 700
HEATMAP_SMOOTHING_SIGMA = 3.0
HEATMAP_MAX_DISTANCE_PX = 180
WIFI_SCAN_ATTEMPTS = 5
WIFI_SCAN_DELAY_SECONDS = 1.5
MIN_GOOD_SCAN_NETWORKS = 4
SUSPICIOUS_SCAN_RATIO = 0.5
SURVEY_FIELDNAMES = [
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
    "radio"
]
