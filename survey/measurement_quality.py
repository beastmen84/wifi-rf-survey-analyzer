"""Independent acquisition, signal variation and observed coverage assessments.

These describe evidence, not calibration or the probability of a correct RSSI.
RF recommendations continue to use the advisor's existing conservative rules.
"""

from collections import defaultdict
import json
from dataclasses import dataclass, field

from maps.quality import get_dominant_candidate_rows
from wifi.adapters import adapter_identity
from wifi.evidence import finite_number, fresh_observation, integer, observation_key, raw_evidence_complete, valid_signal

MIN_STABILITY_SAMPLES = 3
UNSTABLE_RANGE_DB = 12
COVERAGE_REFERENCE_DBM = -70


@dataclass
class MeasurementAssessment:
    collection: str = "unverified"
    stability: str = "unknown"
    coverage: str = "unknown"
    completed: int | None = None
    total: int | None = None
    fresh_samples: int = 0
    minimum_samples: int | None = None
    spread_db: float | None = None
    weakest_ssid_dbm: float | None = None
    reference_dbm: float = COVERAGE_REFERENCE_DBM
    missing_ssids: list = field(default_factory=list)
    weak_ssids: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    can_save: bool = False


def assess_measurement(rows, raw_rows=None, capture=None, relevant_ssids=(), expected_adapter_id="", coverage_dbm=COVERAGE_REFERENCE_DBM):
    rows = list(rows or [])
    capture = capture if isinstance(capture, dict) else {}
    raw_rows = list(raw_rows) if raw_rows is not None else [sample for row in rows for sample in row.get("raw_samples", [])]
    result = MeasurementAssessment(reference_dbm=coverage_dbm)
    result.can_save = bool(rows) or (capture.get("status") == "complete" and capture.get("freshness") == "fresh")
    selected = adapter_identity(expected_adapter_id or capture.get("adapter_id"))
    identities = {adapter_identity(row.get("adapter_id")) for row in rows + raw_rows}
    if (selected and any(identity != selected for identity in identities)
            or len(identities - {""}) > 1
            or (expected_adapter_id and capture.get("adapter_id")
                and adapter_identity(capture["adapter_id"]) != adapter_identity(expected_adapter_id))):
        result.collection, result.can_save = "invalid", False
        result.notes.append("receiver_mismatch")
        return result

    attempts = capture.get("attempts")
    if isinstance(attempts, list) and attempts and all(isinstance(item, dict) for item in attempts):
        expected = integer(capture.get("expected_attempts")) or len(attempts)
        result.total = expected
        result.completed = sum(item.get("status") == "complete" for item in attempts)
    complete = (result.total is not None and len(attempts) == result.total
                and {integer(item.get("attempt")) for item in attempts} == set(range(1, result.total + 1))
                and result.completed == result.total and capture.get("status") == "complete"
                and integer(capture.get("successful_reads")) == result.total
                and capture.get("freshness") == "fresh" and bool(capture.get("adapter_id")))
    raw_verified = bool(rows) and all(row.get("signal_kind") == "direct" and fresh_observation(row)
        and valid_signal(row.get("signal_dbm")) and raw_evidence_complete(row, raw_rows)
        and row.get("capture_quality") != "incomplete" for row in rows)
    valid_raw = [row for row in raw_rows if row.get("signal_kind") == "direct"
                 and fresh_observation(row) and valid_signal(row.get("signal_dbm"))]
    result.fresh_samples = len({observation_key(row) for row in valid_raw})
    if raw_verified or (not rows and complete):
        result.collection = "verified" if complete else "limited"
    if not complete:
        result.notes.append("incomplete_capture" if result.total is not None else "unknown_capture")
    if rows and not raw_verified:
        result.notes.append("unverified_evidence")
    if integer(capture.get("cached_excluded")):
        result.notes.append("cache_excluded")

    scope = {str(ssid) for ssid in relevant_ssids if str(ssid)}
    scoped_rows = [row for row in rows if not scope or str(row.get("ssid", "")) in scope]
    by_network = defaultdict(list)
    for row in scoped_rows:
        by_network[(row.get("ssid", ""), row.get("band", ""))].append(row)
    candidates = [row for group in by_network.values() for row in get_dominant_candidate_rows(group)]
    counts, spreads = [], []
    for row in candidates:
        if not raw_evidence_complete(row, valid_raw):
            counts.append(0)
            continue
        samples = [raw for raw in valid_raw if str(raw.get("point_id", "")) == str(row.get("point_id", ""))
                   and str(raw.get("ssid", "")) == str(row.get("ssid", ""))
                   and str(raw.get("bssid", "")).lower() == str(row.get("bssid", "")).lower()
                   and str(raw.get("frequency_mhz", "")) == str(row.get("frequency_mhz", ""))
                   and integer(raw.get("channel")) == integer(row.get("channel"))]
        unique = {observation_key(raw): finite_number(raw["signal_dbm"]) for raw in samples}
        counts.append(len(unique))
        if len(unique) >= MIN_STABILITY_SAMPLES:
            spreads.append(max(unique.values()) - min(unique.values()))
    if counts:
        result.minimum_samples = min(counts)
        if min(counts) < MIN_STABILITY_SAMPLES:
            result.notes.append("few_samples")
            if result.collection == "verified":
                result.collection = "limited"
    if spreads:
        result.spread_db = max(spreads)
        result.stability = "variable" if result.spread_db >= UNSTABLE_RANGE_DB else "stable" if min(counts) >= MIN_STABILITY_SAMPLES else "limited"

    if scope:
        best = {}
        for row in scoped_rows:
            value = finite_number(row.get("signal_dbm"))
            if valid_signal(value):
                ssid = str(row.get("ssid", ""))
                best[ssid] = max(best.get(ssid, -120), value)
        result.missing_ssids = sorted(scope - best.keys())
        result.weak_ssids = sorted(ssid for ssid, signal in best.items() if signal < coverage_dbm)
        result.weakest_ssid_dbm = min(best.values()) if best else None
        result.coverage = "missing" if result.missing_ssids else "weak" if result.weak_ssids else "within" if best else "unknown"
    else:
        result.notes.append("choose_scope")
    return result


def assess_survey_measurements(rows, raw_rows, metadata, relevant_ssids=(), coverage_dbm=COVERAGE_REFERENCE_DBM):
    """Group once by point, preserving unknown acquisition history in old files."""
    grouped, grouped_raw = defaultdict(list), defaultdict(list)
    for row in rows:
        grouped[str(row.get("point_id", ""))].append(row)
    for row in raw_rows:
        grouped_raw[str(row.get("point_id", ""))].append(row)
    try:
        ledger = json.loads((metadata or {}).get("measurement_points", "[]"))
        captures = {str(point["point_id"]): point.get("capture", {}) for point in ledger}
    except (ValueError, TypeError, KeyError):
        captures = {}
    return {pid: assess_measurement(grouped[pid], grouped_raw[pid], captures.get(pid), relevant_ssids,
                                   coverage_dbm=coverage_dbm) for pid in grouped.keys() | captures.keys()}
