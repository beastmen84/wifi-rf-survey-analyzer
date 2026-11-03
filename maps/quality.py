"""Point quality evaluation based on relevant SSIDs and scan confidence."""

from collections import defaultdict

from wifi.band import get_row_band


QUALITY_GOOD = "GOOD"
QUALITY_MISSING_RELEVANT = "MISSING_RELEVANT"
QUALITY_LOW_CONFIDENCE = "LOW_CONFIDENCE"
QUALITY_UNSTABLE_SIGNAL = "UNSTABLE_SIGNAL"
QUALITY_SPARSE_DATA = "SPARSE_DATA"
SCANNER_DETAIL_FALLBACK_BACKEND = "FALLBACK_BACKEND"
SCANNER_DETAIL_MISSING_CHANNEL_WIDTH = "MISSING_CHANNEL_WIDTH"
SCANNER_DETAIL_MISSING_6GHZ_FREQUENCY = "MISSING_6GHZ_FREQUENCY"
DOMINANT_SIGNAL_WINDOW_DB = 5


def evaluate_point_quality(rows, raw_scan_rows=None, relevant_ssids=None, relevant_ssids_by_point=None):
    raw_scan_rows = raw_scan_rows or []
    relevant_ssids = normalize_ssids(relevant_ssids or get_relevant_ssids_from_rows(rows))
    relevant_ssids_by_point = {
        str(point_id): normalize_ssids(point_relevant_ssids)
        for point_id, point_relevant_ssids in (relevant_ssids_by_point or {}).items()
        if str(point_id)
    }
    grouped_rows = group_by_point_id(rows)
    grouped_raw_rows = group_by_point_id(raw_scan_rows)
    results = {}

    for point_id, point_rows in grouped_rows.items():
        raw_rows = grouped_raw_rows.get(point_id, [])
        point_relevant_ssids = relevant_ssids_by_point.get(point_id, relevant_ssids)
        results[point_id] = evaluate_single_point(
            point_rows,
            raw_rows,
            point_relevant_ssids,
            infer_relevant=False,
        )

    return results


def group_by_point_id(rows):
    grouped = defaultdict(list)

    for row in rows:
        point_id = row.get("point_id")
        if point_id:
            grouped[point_id].append(row)

    return grouped


def evaluate_single_point(rows, raw_rows, relevant_ssids=None, infer_relevant=True):
    if not rows:
        return build_quality_result(QUALITY_SPARSE_DATA, scanner_details=build_scanner_detail_result())

    if relevant_ssids is None or (infer_relevant and not relevant_ssids):
        relevant_ssids = normalize_ssids(get_relevant_ssids_from_rows(rows))
    else:
        relevant_ssids = normalize_ssids(relevant_ssids)

    if not relevant_ssids and not infer_relevant:
        return build_quality_result(
            QUALITY_GOOD,
            breakdown=[],
            scanner_details=build_scanner_detail_result(),
        )

    quality_rows = get_quality_rows(rows, relevant_ssids, include_all_when_empty=infer_relevant)
    breakdown = build_quality_breakdown(rows, raw_rows, relevant_ssids)
    scanner_details = evaluate_scanner_details(
        rows,
        raw_rows,
        relevant_ssids,
        infer_relevant=infer_relevant,
    )
    missing_relevant = sorted(
        item["ssid"]
        for item in breakdown
        if item["status"] == QUALITY_MISSING_RELEVANT
    )
    if missing_relevant:
        return build_quality_result(
            QUALITY_MISSING_RELEVANT,
            missing_relevant=missing_relevant,
            breakdown=breakdown,
            scanner_details=scanner_details,
        )

    if not quality_rows:
        return build_quality_result(QUALITY_SPARSE_DATA, breakdown=breakdown, scanner_details=scanner_details)

    if any(item["status"] == QUALITY_LOW_CONFIDENCE for item in breakdown):
        return build_quality_result(QUALITY_LOW_CONFIDENCE, breakdown=breakdown, scanner_details=scanner_details)

    if any(item["status"] == QUALITY_UNSTABLE_SIGNAL for item in breakdown):
        return build_quality_result(QUALITY_UNSTABLE_SIGNAL, breakdown=breakdown, scanner_details=scanner_details)

    raw_sample_count = len(raw_rows)
    aggregate_sample_count = sum(parse_int(row.get("samples_seen"), default=1) for row in quality_rows)
    if raw_sample_count < 3 and aggregate_sample_count < 3:
        return build_quality_result(QUALITY_SPARSE_DATA, breakdown=breakdown, scanner_details=scanner_details)

    return build_quality_result(QUALITY_GOOD, breakdown=breakdown, scanner_details=scanner_details)


def build_quality_result(status, **details):
    result = {"status": status}
    result.update(details)
    return result


def evaluate_scanner_details(rows, raw_rows=None, relevant_ssids=None, infer_relevant=True):
    """Return point-level scanner evidence issues that affect channel-sensitive maps."""
    scan_rows = list(raw_rows or []) or list(rows or [])
    if not scan_rows:
        return build_scanner_detail_result()

    backend_counts = defaultdict(int)
    fallback_rows = 0
    missing_channel_width_rows = 0
    missing_6ghz_frequency_rows = 0
    if relevant_ssids is None or (infer_relevant and not relevant_ssids):
        relevant_ssids = normalize_ssids(get_relevant_ssids_from_rows(rows or []))
        filter_relevant = bool(relevant_ssids)
    else:
        relevant_ssids = normalize_ssids(relevant_ssids)
        filter_relevant = True

    for row in scan_rows:
        backend = str(row.get("backend", "") or "").strip().lower()
        if backend:
            backend_counts[backend] += 1
        if backend == "netsh":
            fallback_rows += 1

        if filter_relevant and normalize_ssid(row.get("ssid")) not in relevant_ssids:
            continue

        band = get_row_band(row)
        if band in {"5", "6"} and is_missing_value(row.get("channel_width_mhz")):
            missing_channel_width_rows += 1
        if band == "6" and is_missing_value(row.get("frequency_mhz")):
            missing_6ghz_frequency_rows += 1

    issue_types = []
    if fallback_rows:
        issue_types.append(SCANNER_DETAIL_FALLBACK_BACKEND)
    if missing_channel_width_rows:
        issue_types.append(SCANNER_DETAIL_MISSING_CHANNEL_WIDTH)
    if missing_6ghz_frequency_rows:
        issue_types.append(SCANNER_DETAIL_MISSING_6GHZ_FREQUENCY)

    return build_scanner_detail_result(
        issue_types=issue_types,
        backend_counts=dict(sorted(backend_counts.items())),
        fallback_rows=fallback_rows,
        missing_channel_width_rows=missing_channel_width_rows,
        missing_6ghz_frequency_rows=missing_6ghz_frequency_rows,
        inspected_rows=len(scan_rows),
    )


def build_scanner_detail_result(
    issue_types=None,
    backend_counts=None,
    fallback_rows=0,
    missing_channel_width_rows=0,
    missing_6ghz_frequency_rows=0,
    inspected_rows=0,
):
    issue_types = list(issue_types or [])
    return {
        "has_issue": bool(issue_types),
        "issue_types": issue_types,
        "backend_counts": backend_counts or {},
        "fallback_rows": int(fallback_rows or 0),
        "missing_channel_width_rows": int(missing_channel_width_rows or 0),
        "missing_6ghz_frequency_rows": int(missing_6ghz_frequency_rows or 0),
        "inspected_rows": int(inspected_rows or 0),
    }


def get_quality_rows(rows, relevant_ssids, include_all_when_empty=True):
    if not relevant_ssids:
        return rows if include_all_when_empty else []

    return [
        row
        for row in rows
        if normalize_ssid(row.get("ssid")) in relevant_ssids
    ]


def get_relevant_ssids_from_rows(rows):
    return {
        row.get("ssid")
        for row in rows
        if is_truthy(row.get("is_relevant"))
    }


def build_quality_breakdown(rows, raw_rows, relevant_ssids):
    if not relevant_ssids:
        return []

    rows_by_ssid = group_rows_by_ssid(rows)
    ranges_by_key = get_signal_ranges_by_key(rows, raw_rows, relevant_ssids)
    breakdown = []
    observed_relevant_ssids = sorted(set(rows_by_ssid) & set(relevant_ssids))
    missing_relevant_ssids = sorted(set(relevant_ssids) - set(observed_relevant_ssids))
    for ssid in missing_relevant_ssids:
        breakdown.append({
            "ssid": ssid,
            "status": QUALITY_MISSING_RELEVANT,
            "message": "missing"
        })

    for ssid in observed_relevant_ssids:
        ssid_rows = rows_by_ssid.get(ssid, [])

        confidence_rows = get_dominant_candidate_rows(ssid_rows)
        confidence_values = parse_float_values(row.get("scan_confidence") for row in confidence_rows)
        min_confidence = min(confidence_values) if confidence_values else None
        avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else None
        if min_confidence is not None and (min_confidence < 0.25 or avg_confidence < 0.45):
            breakdown.append({
                "ssid": ssid,
                "status": QUALITY_LOW_CONFIDENCE,
                "message": "low_confidence",
                "min_confidence": min_confidence,
                "avg_confidence": avg_confidence
            })
            continue

        unstable_range = get_unstable_range_for_ssid(ssid_rows, ranges_by_key)
        if unstable_range is not None:
            breakdown.append({
                "ssid": ssid,
                "status": QUALITY_UNSTABLE_SIGNAL,
                "message": "unstable",
                "range_db": unstable_range
            })
            continue

        breakdown.append({
            "ssid": ssid,
            "status": QUALITY_GOOD,
            "message": "good"
        })

    return breakdown


def get_dominant_candidate_rows(rows, signal_window_db=DOMINANT_SIGNAL_WINDOW_DB):
    scored_rows = [
        (parse_float(row.get("signal_dbm")), row)
        for row in rows
        if parse_float(row.get("signal_dbm")) is not None
    ]
    if not scored_rows:
        return list(rows)

    best_signal = max(signal for signal, _row in scored_rows)
    return [
        row
        for signal, row in scored_rows
        if best_signal - signal <= signal_window_db
    ]


def get_unstable_range_for_ssid(rows, ranges_by_key):
    strong_rows = get_dominant_candidate_rows(rows)
    if not strong_rows:
        return None

    strong_candidate_keys = {
        network_key(row)
        for row in strong_rows
    }
    strong_ranges = [
        ranges_by_key.get(key, 0)
        for key in strong_candidate_keys
    ]
    if strong_ranges and min(strong_ranges) >= 12:
        return max(strong_ranges)

    return None


def get_signal_ranges(rows, raw_rows, relevant_ssids=None):
    raw_ranges = get_raw_signal_ranges(raw_rows, relevant_ssids)
    if raw_ranges:
        return raw_ranges

    ranges = []
    for row in rows:
        min_dbm = parse_float(row.get("signal_min_dbm"))
        max_dbm = parse_float(row.get("signal_max_dbm"))
        if min_dbm is not None and max_dbm is not None:
            ranges.append(max_dbm - min_dbm)

    return ranges


def get_unstable_dominant_signal_ranges(rows, raw_rows, relevant_ssids=None):
    ranges_by_key = get_signal_ranges_by_key(rows, raw_rows, relevant_ssids)
    unstable_ranges = []

    for candidate_rows in group_rows_by_ssid(rows).values():
        unstable_range = get_unstable_range_for_ssid(candidate_rows, ranges_by_key)
        if unstable_range is not None:
            unstable_ranges.append(unstable_range)

    return unstable_ranges


def group_rows_by_ssid(rows):
    grouped = defaultdict(list)

    for row in rows:
        ssid = normalize_ssid(row.get("ssid"))
        if ssid:
            grouped[ssid].append(row)

    return grouped


def get_signal_ranges_by_key(rows, raw_rows, relevant_ssids=None):
    ranges = get_raw_signal_ranges_by_key(raw_rows, relevant_ssids)
    if ranges:
        return ranges

    ranges = {}
    for row in rows:
        min_dbm = parse_float(row.get("signal_min_dbm"))
        max_dbm = parse_float(row.get("signal_max_dbm"))
        if min_dbm is not None and max_dbm is not None:
            ranges[network_key(row)] = max_dbm - min_dbm

    return ranges


def get_raw_signal_ranges_by_key(raw_rows, relevant_ssids=None):
    by_network = defaultdict(list)
    relevant_ssids = normalize_ssids(relevant_ssids or [])

    for row in raw_rows:
        if relevant_ssids and normalize_ssid(row.get("ssid")) not in relevant_ssids:
            continue

        signal_dbm = parse_float(row.get("signal_dbm"))
        if signal_dbm is not None:
            by_network[network_key(row)].append(signal_dbm)

    return {
        key: max(values) - min(values)
        for key, values in by_network.items()
        if len(values) >= 2
    }


def get_raw_signal_ranges(raw_rows, relevant_ssids=None, allowed_keys=None):
    by_network = defaultdict(list)
    relevant_ssids = normalize_ssids(relevant_ssids or [])
    allowed_keys = set(allowed_keys or [])

    for row in raw_rows:
        if relevant_ssids and normalize_ssid(row.get("ssid")) not in relevant_ssids:
            continue

        key = network_key(row)
        if allowed_keys and key not in allowed_keys:
            continue

        signal_dbm = parse_float(row.get("signal_dbm"))
        if signal_dbm is not None:
            by_network[key].append(signal_dbm)

    return [
        max(values) - min(values)
        for values in by_network.values()
        if len(values) >= 2
    ]


def network_key(row):
    return (
        normalize_ssid(row.get("ssid")),
        str(row.get("bssid", "")).strip().lower(),
        str(row.get("channel", "")).strip()
    )


def normalize_ssids(values):
    return {
        normalize_ssid(value)
        for value in values
        if normalize_ssid(value)
    }


def normalize_ssid(value):
    return str(value or "").strip()


def is_truthy(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "si", "sì"}


def is_missing_value(value):
    text = str(value or "").strip().lower()
    return text in {"", "nan", "none", "null"}


def parse_float_values(values):
    parsed = []

    for value in values:
        number = parse_float(value)
        if number is not None:
            parsed.append(number)

    return parsed


def parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default
