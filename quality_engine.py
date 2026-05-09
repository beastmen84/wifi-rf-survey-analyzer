from collections import defaultdict


QUALITY_GOOD = "GOOD"
QUALITY_MISSING_RELEVANT = "MISSING_RELEVANT"
QUALITY_LOW_CONFIDENCE = "LOW_CONFIDENCE"
QUALITY_UNSTABLE_SIGNAL = "UNSTABLE_SIGNAL"
QUALITY_SPARSE_DATA = "SPARSE_DATA"


def evaluate_point_quality(rows, raw_scan_rows=None, relevant_ssids=None):
    raw_scan_rows = raw_scan_rows or []
    relevant_ssids = normalize_ssids(relevant_ssids or get_relevant_ssids_from_rows(rows))
    grouped_rows = group_by_point_id(rows)
    grouped_raw_rows = group_by_point_id(raw_scan_rows)
    results = {}

    for point_id, point_rows in grouped_rows.items():
        raw_rows = grouped_raw_rows.get(point_id, [])
        results[point_id] = evaluate_single_point(point_rows, raw_rows, relevant_ssids)

    return results


def group_by_point_id(rows):
    grouped = defaultdict(list)

    for row in rows:
        point_id = row.get("point_id")
        if point_id:
            grouped[point_id].append(row)

    return grouped


def evaluate_single_point(rows, raw_rows, relevant_ssids=None):
    if not rows:
        return build_quality_result(QUALITY_SPARSE_DATA)

    relevant_ssids = normalize_ssids(relevant_ssids or get_relevant_ssids_from_rows(rows))
    quality_rows = get_quality_rows(rows, relevant_ssids)
    missing_relevant = sorted(relevant_ssids - normalize_ssids(row.get("ssid") for row in rows))
    if missing_relevant:
        return build_quality_result(QUALITY_MISSING_RELEVANT, missing_relevant=missing_relevant)

    if not quality_rows:
        return build_quality_result(QUALITY_SPARSE_DATA)

    confidence_values = parse_float_values(row.get("scan_confidence") for row in quality_rows)
    if confidence_values:
        min_confidence = min(confidence_values)
        avg_confidence = sum(confidence_values) / len(confidence_values)
        if min_confidence < 0.25 or avg_confidence < 0.45:
            return build_quality_result(QUALITY_LOW_CONFIDENCE)

    ranges = get_signal_ranges(quality_rows, raw_rows, relevant_ssids)
    if ranges and max(ranges) >= 12:
        return build_quality_result(QUALITY_UNSTABLE_SIGNAL)

    raw_sample_count = len(raw_rows)
    aggregate_sample_count = sum(parse_int(row.get("samples_seen"), default=1) for row in quality_rows)
    if raw_sample_count < 3 and aggregate_sample_count < 3:
        return build_quality_result(QUALITY_SPARSE_DATA)

    return build_quality_result(QUALITY_GOOD)


def build_quality_result(status, **details):
    result = {"status": status}
    result.update(details)
    return result


def get_quality_rows(rows, relevant_ssids):
    if not relevant_ssids:
        return rows

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


def get_raw_signal_ranges(raw_rows, relevant_ssids=None):
    by_network = defaultdict(list)
    relevant_ssids = normalize_ssids(relevant_ssids or [])

    for row in raw_rows:
        if relevant_ssids and normalize_ssid(row.get("ssid")) not in relevant_ssids:
            continue

        key = (
            str(row.get("ssid", "")),
            str(row.get("bssid", "")),
            str(row.get("channel", ""))
        )
        signal_dbm = parse_float(row.get("signal_dbm"))
        if signal_dbm is not None:
            by_network[key].append(signal_dbm)

    return [
        max(values) - min(values)
        for values in by_network.values()
        if len(values) >= 2
    ]


def normalize_ssids(values):
    return {
        normalize_ssid(value)
        for value in values
        if normalize_ssid(value)
    }


def normalize_ssid(value):
    return str(value or "").strip().lower()


def is_truthy(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "si", "sì"}


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
