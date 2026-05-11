"""Wi-Fi band normalization and channel/frequency helpers."""

import re


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


def infer_band_from_frequency_mhz(value):
    try:
        frequency = float(str(value).strip())
    except (TypeError, ValueError):
        return ""

    if frequency > 100000000:
        frequency /= 1000000.0
    elif frequency > 100000:
        frequency /= 1000.0
    elif 2 <= frequency <= 8:
        frequency *= 1000.0

    if 2400 <= frequency <= 2500:
        return "2.4"
    if 4900 <= frequency < 5925:
        return "5"
    if 5925 <= frequency <= 7125:
        return "6"

    return ""


def infer_band_from_channel(channel):
    try:
        channel_number = int(float(channel))
    except (TypeError, ValueError):
        return ""

    if 1 <= channel_number <= 14:
        return "2.4"
    if 32 <= channel_number <= 196:
        return "5"

    return ""


def get_row_band(row):
    for key in ("band", "wifi_band"):
        if key in row:
            band = normalize_band(row.get(key))
            if band:
                return band

    for key in ("frequency_mhz", "frequency", "freq"):
        if key in row:
            band = infer_band_from_frequency_mhz(row.get(key))
            if band:
                return band

    return infer_band_from_channel(row.get("channel"))


def row_matches_band(row, band):
    band = normalize_band(band)
    if not band:
        return True

    return get_row_band(row) == band


def channel_center_frequency_mhz(channel, band):
    try:
        channel_number = int(float(channel))
    except (TypeError, ValueError):
        return None

    band = normalize_band(band)
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
