import re


def percent_to_dbm(percent):
    return round((percent / 2) - 100, 1)


def dbm_to_percent(dbm):
    return max(0, min(100, int(round((dbm + 100) * 2))))


def signal_to_color(signal_dbm):
    if signal_dbm is None:
        return "#d62728"

    if signal_dbm >= -60:
        return "#2ca02c"

    if signal_dbm >= -70:
        return "#f2c94c"

    return "#d62728"


def sanitize_filename(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "ssid"
