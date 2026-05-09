from collections import defaultdict


QUALITY_GOOD = "GOOD"
QUALITY_LOW_CONFIDENCE = "LOW_CONFIDENCE"
QUALITY_UNSTABLE_SIGNAL = "UNSTABLE_SIGNAL"
QUALITY_SPARSE_DATA = "SPARSE_DATA"


def evaluate_point_quality(rows, raw_scan_rows=None):
    raw_scan_rows = raw_scan_rows or []
    grouped_rows = group_by_point_id(rows)
    grouped_raw_rows = group_by_point_id(raw_scan_rows)
    results = {}

    for point_id, point_rows in grouped_rows.items():
        raw_rows = grouped_raw_rows.get(point_id, [])
        results[point_id] = evaluate_single_point(point_rows, raw_rows)

    return results


def group_by_point_id(rows):
    grouped = defaultdict(list)

    for row in rows:
        point_id = row.get("point_id")
        if point_id:
            grouped[point_id].append(row)

    return grouped


def evaluate_single_point(rows, raw_rows):
    if not rows:
        return build_quality_result(QUALITY_SPARSE_DATA)

    confidence_values = parse_float_values(row.get("scan_confidence") for row in rows)
    if confidence_values:
        min_confidence = min(confidence_values)
        avg_confidence = sum(confidence_values) / len(confidence_values)
        if min_confidence < 0.25 or avg_confidence < 0.45:
            return build_quality_result(QUALITY_LOW_CONFIDENCE)

    ranges = get_signal_ranges(rows, raw_rows)
    if ranges and max(ranges) >= 12:
        return build_quality_result(QUALITY_UNSTABLE_SIGNAL)

    raw_sample_count = len(raw_rows)
    aggregate_sample_count = sum(parse_int(row.get("samples_seen"), default=1) for row in rows)
    if raw_sample_count < 3 and aggregate_sample_count < 3:
        return build_quality_result(QUALITY_SPARSE_DATA)

    return build_quality_result(QUALITY_GOOD)


def build_quality_result(status):
    return {
        "status": status
    }


def get_signal_ranges(rows, raw_rows):
    raw_ranges = get_raw_signal_ranges(raw_rows)
    if raw_ranges:
        return raw_ranges

    ranges = []
    for row in rows:
        min_dbm = parse_float(row.get("signal_min_dbm"))
        max_dbm = parse_float(row.get("signal_max_dbm"))
        if min_dbm is not None and max_dbm is not None:
            ranges.append(max_dbm - min_dbm)

    return ranges


def get_raw_signal_ranges(raw_rows):
    by_network = defaultdict(list)

    for row in raw_rows:
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
