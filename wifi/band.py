"""Wi-Fi band normalization and channel/frequency helpers."""

import re
from wifi.evidence import finite_number, integer


WIFI_BANDS = ("2.4", "5", "6")


def normalize_band(value):
    text = str(value or "").strip().lower()
    if not text:
        return ""

    text = text.replace("_", " ").replace("-", " ")
    text = text.replace("ghz", "g")
    text = text.replace(",", ".")

    if re.search(r"\b2(?:\.4)?\s*g?\b", text) or text in {"24", "2.4g"}:
        return "2.4"
    if re.search(r"\b5\s*g?\b", text):
        return "5"
    if re.search(r"\b6\s*g?\b", text):
        return "6"

    return ""


def normalize_frequency_mhz(value):
    text = str(value or "").strip().lower().replace(",", ".")
    if not text:
        return None

    match = re.fullmatch(r"([-+]?\d+(?:\.\d+)?)\s*(ghz|mhz|khz|hz)?", text)
    if not match:
        return None

    try:
        frequency = float(match.group(1))
    except (TypeError, ValueError):
        return None

    if "ghz" in text:
        frequency *= 1000.0
    elif "khz" in text:
        frequency /= 1000.0
    elif "mhz" not in text and "hz" in text:
        frequency /= 1000000.0
    elif frequency > 100000000:
        frequency /= 1000000.0
    elif frequency > 100000:
        frequency /= 1000.0
    elif 2 <= frequency <= 8:
        frequency *= 1000.0

    return frequency if finite_number(frequency) is not None and frequency > 0 else None


def infer_band_from_frequency_mhz(value):
    frequency = normalize_frequency_mhz(value)
    if frequency is None:
        return ""

    try:
        frequency = float(frequency)
    except (TypeError, ValueError):
        return ""

    if 2400 <= frequency <= 2500:
        return "2.4"
    if 4900 <= frequency < 5925:
        return "5"
    if 5925 <= frequency <= 7125:
        return "6"

    return ""


def infer_band_from_channel(channel):
    channel_number = integer(channel)
    bands = [band for band in WIFI_BANDS if valid_primary_channel(channel_number, band)]
    return bands[0] if len(bands) == 1 else ""


def valid_primary_channel(channel, band):
    channel = integer(channel)
    if channel is None:
        return False
    if band == "2.4":
        return 1 <= channel <= 14
    if band == "5":
        return channel in (*range(36, 65, 4), *range(100, 145, 4), *range(149, 178, 4))
    if band == "6":
        return channel == 2 or channel in range(1, 234, 4)
    return False


def get_row_band(row):
    """Resolve consistent evidence; ambiguous channels and contradictions stay unknown."""
    if row.get("radio_status") == "invalid":
        return ""
    evidence = set()
    for key in ("band", "wifi_band"):
        if key in row:
            band = normalize_band(row.get(key))
            if band:
                evidence.add(band)

    for key in ("frequency_mhz", "frequency", "freq"):
        if key in row:
            band = infer_band_from_frequency_mhz(row.get(key))
            if band:
                evidence.add(band)
            elif str(row.get(key) or "").strip():
                return ""
    if len(evidence) > 1:
        return ""
    band = next(iter(evidence), "") or infer_band_from_channel(row.get("channel"))
    channel = integer(row.get("channel"))
    if str(row.get("channel") or "").strip() and not valid_primary_channel(channel, band):
        return ""
    for key in ("frequency_mhz", "frequency", "freq"):
        frequency = normalize_frequency_mhz(row.get(key))
        if frequency is not None and channel is not None:
            center = channel_center_frequency_mhz(channel, band)
            if center is None or abs(center - frequency) > 0.5:
                return ""
    return band


def row_matches_band(row, band):
    band = normalize_band(band)
    if not band:
        return True

    return get_row_band(row) == band


def channel_center_frequency_mhz(channel, band):
    channel_number = integer(channel)
    band = normalize_band(band)
    if not valid_primary_channel(channel_number, band):
        return None
    if band == "2.4":
        if channel_number == 14:
            return 2484
        if 1 <= channel_number <= 13:
            return 2407 + (channel_number * 5)
        return None
    if band == "5":
        return 5000 + (channel_number * 5)
    if band == "6":
        if channel_number == 2:
            return 5935
        return 5950 + (channel_number * 5)

    return None
