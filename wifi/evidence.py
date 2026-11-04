"""Shared, conservative validation of measurement evidence (not RF calibration)."""

import math
import re


PROVENANCE_FIELDS = [
    "backend", "adapter_id", "signal_kind", "freshness", "host_timestamp",
    "observed_at", "scan_started_at", "scan_completed_at", "ssid_hex",
    "channel_geometry", "secondary_channel_offset", "radio_status", "capture_quality",
]


def finite_number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def integer(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value.strip()):
        return int(value)
    result = finite_number(value)
    return int(result) if result is not None and result.is_integer() else None


def fresh_observation(row):
    stamps = [integer(row.get(field)) for field in
              ("scan_started_at", "scan_completed_at", "observed_at", "host_timestamp")]
    if any(stamp is None or stamp <= 0 for stamp in stamps):
        return False
    started, completed, observed, host = stamps
    return (row.get("freshness") == "fresh" and bool(row.get("adapter_id"))
            and started <= host <= observed and started <= completed <= observed)


def ssid_text(value):
    """SSID names are identities: spaces and words such as 'unknown' are valid."""
    return "" if value is None else str(value)


def valid_signal(value):
    value = finite_number(value)
    return value is not None and -120 <= value <= 0


def observation_key(row):
    """Never use RSSI equality as a freshness or independence test."""
    adapter = str(row.get("adapter_id") or "")
    stamp = integer(row.get("host_timestamp"))
    if not adapter or stamp is None or stamp <= 0:
        return None
    return (adapter, str(row.get("bssid", "")).lower(),
            str(row.get("frequency_mhz", "")), stamp)


def scan_confidence(row, require_samples=False):
    """Unknown/invalid evidence has zero confidence, never implicit 100%."""
    value = finite_number(row.get("scan_confidence"))
    seen, total = integer(row.get("samples_seen")), integer(row.get("samples_total"))
    if value is None or not 0 <= value <= 1:
        return 0.0
    # Older files do not establish freshness; retain their observations for viewing.
    if not fresh_observation(row) or row.get("capture_quality") == "incomplete":
        return 0.0
    if seen is None or total is None or total < seen or seen < (3 if require_samples else 1):
        return 0.0
    return min(value, seen / total)


def raw_evidence_complete(row, raw_rows):
    """Validate aggregate counts against unique, associated raw observations."""
    seen, total = integer(row.get("samples_seen")), integer(row.get("samples_total"))
    if seen is None or total is None or not 1 <= seen <= total:
        return False
    from wifi.band import get_row_band
    relevant = [raw for raw in raw_rows if
        str(raw.get("point_id", "")) == str(row.get("point_id", ""))
        and ssid_text(raw.get("ssid")) == ssid_text(row.get("ssid"))
        and str(raw.get("bssid", "")).lower() == str(row.get("bssid", "")).lower()
        and str(raw.get("adapter_id", "")) == str(row.get("adapter_id", ""))
        and integer(raw.get("channel")) == integer(row.get("channel"))]
    keys, attempts = set(), set()
    for raw in relevant:
        key = observation_key(raw)
        attempt = integer(raw.get("scan_attempt"))
        if (key is None or not fresh_observation(raw) or attempt is None
                or not 1 <= attempt <= total or not valid_signal(raw.get("signal_dbm"))
                or get_row_band(raw) != get_row_band(row)
                or finite_number(raw.get("x")) != finite_number(row.get("x"))
                or finite_number(raw.get("y")) != finite_number(row.get("y"))):
            return False
        keys.add(key)
        attempts.add(attempt)
    return len(keys) == seen and len(attempts) == seen
