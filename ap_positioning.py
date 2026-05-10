import math


AP_POSITION_OK = "OK"
AP_POSITION_MISSING = "MISSING_POSITION"
AP_POSITION_NO_SCALE = "NO_SCALE"
AP_POSITION_STRONG_FAR = "STRONG_FAR"
AP_POSITION_WEAK_CLOSE = "WEAK_CLOSE"
AP_POSITION_UNEXPECTED_DOMINANT = "UNEXPECTED_DOMINANT"


def analyze_dominant_ap_position(row, ap_groups, px_per_meter=None):
    positions = build_ap_position_map(ap_groups)
    group_id = str(row.get("dominant_ap_group", "")).strip()
    point = parse_point(row)

    if not group_id or point is None or group_id not in positions:
        return {
            "status": AP_POSITION_MISSING,
            "has_position": False,
            "warnings": [],
        }

    ap_point = positions[group_id]
    dominant_distance_px = distance(point, ap_point)
    nearest_group_id, nearest_distance_px = find_nearest_ap(point, positions)
    scale = parse_positive_float(px_per_meter)
    dominant_distance_m = pixels_to_meters(dominant_distance_px, scale)
    nearest_distance_m = pixels_to_meters(nearest_distance_px, scale)
    warnings = []

    if scale is None:
        status = AP_POSITION_NO_SCALE
    else:
        signal = parse_float(row.get("dominant_signal_dbm"))
        warnings = classify_position_warnings(
            signal,
            dominant_distance_m,
            nearest_group_id,
            nearest_distance_m,
            group_id,
        )
        status = warnings[0] if warnings else AP_POSITION_OK

    return {
        "status": status,
        "has_position": True,
        "warnings": warnings,
        "dominant_ap_group": group_id,
        "dominant_distance_px": dominant_distance_px,
        "dominant_distance_m": dominant_distance_m,
        "nearest_ap_group": nearest_group_id,
        "nearest_distance_px": nearest_distance_px,
        "nearest_distance_m": nearest_distance_m,
    }


def build_ap_position_map(ap_groups):
    positions = {}

    for group in ap_groups or []:
        group_id = str(group.get("group_id", "")).strip()
        position = group.get("position") or {}
        point = parse_point(position)
        if group_id and point is not None:
            positions[group_id] = point

    return positions


def classify_position_warnings(signal_dbm, dominant_distance_m, nearest_group_id, nearest_distance_m, dominant_group_id):
    warnings = []

    if dominant_distance_m is None:
        return warnings

    if signal_dbm is not None and signal_dbm >= -55 and dominant_distance_m >= 25:
        warnings.append(AP_POSITION_STRONG_FAR)

    if signal_dbm is not None and signal_dbm <= -78 and dominant_distance_m <= 5:
        warnings.append(AP_POSITION_WEAK_CLOSE)

    if (
        nearest_group_id
        and nearest_group_id != dominant_group_id
        and nearest_distance_m is not None
        and dominant_distance_m - nearest_distance_m >= 12
        and dominant_distance_m >= nearest_distance_m * 2
    ):
        warnings.append(AP_POSITION_UNEXPECTED_DOMINANT)

    return warnings


def find_nearest_ap(point, positions):
    nearest_group_id = ""
    nearest_distance = None

    for group_id, ap_point in positions.items():
        current_distance = distance(point, ap_point)
        if nearest_distance is None or current_distance < nearest_distance:
            nearest_group_id = group_id
            nearest_distance = current_distance

    return nearest_group_id, nearest_distance


def parse_point(value):
    try:
        x = float(value.get("x"))
        y = float(value.get("y"))
    except (AttributeError, TypeError, ValueError):
        return None

    if not math.isfinite(x) or not math.isfinite(y):
        return None

    return x, y


def distance(first, second):
    return math.hypot(first[0] - second[0], first[1] - second[1])


def pixels_to_meters(distance_px, px_per_meter):
    if distance_px is None or px_per_meter is None:
        return None

    return distance_px / px_per_meter


def parse_positive_float(value):
    number = parse_float(value)
    if number is None or number <= 0:
        return None

    return number


def parse_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    return number if math.isfinite(number) else None
