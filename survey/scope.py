"""Shared local-area relevance rules for quality and survey recommendations."""

from types import SimpleNamespace
from ap.groups import (AP_ROLE_TEST, build_bssid_to_manual_group_map,
    is_local_coverage_metadata, normalize_coverage_radius_m, normalize_ap_role,
    resolve_ap_group_key)
from maps.quality import normalize_ssid, parse_float

LOCAL_COVERAGE_AUTO_MIN_SIGNAL_DBM = -70.0
LOCAL_COVERAGE_AUTO_RADIUS_MARGIN_M = 2.0


def relevant_ssids_by_point(rows, groups, relevant, px_per_meter=None):
    app = SimpleNamespace(session=SimpleNamespace(rows=rows))
    scopes, global_ssids = build_local_coverage_scopes(app, groups, set(relevant))
    if not scopes:
        return {}
    grouped = {}
    for row in rows:
        if row.get("point_id"):
            grouped.setdefault(str(row["point_id"]), []).append(row)
    apply_auto_local_scope_radii(scopes, grouped, px_per_meter)
    return {
        key: set(global_ssids) | {ssid for ssid, entries in scopes.items()
            if any(local_scope_applies_to_point(scope, point_rows, px_per_meter) for scope in entries)}
        for key, point_rows in grouped.items()
    }


def build_local_coverage_scopes(app, ap_groups, relevant_ssids):
    group_map = build_bssid_to_manual_group_map(ap_groups)
    groups_by_id = {
        str(group.get("group_id", "")): group
        for group in ap_groups
        if str(group.get("group_id", ""))
    }
    ssids_by_group = {}
    groups_by_ssid = {}

    for row in app.session.rows:
        ssid = normalize_ssid(row.get("ssid"))
        if not ssid or ssid not in relevant_ssids:
            continue

        group_id = resolve_ap_group_key(row.get("bssid", ""), group_map)
        group = groups_by_id.get(group_id)
        if not group or normalize_ap_role(group.get("role")) == AP_ROLE_TEST:
            continue

        ssids_by_group.setdefault(group_id, set()).add(ssid)
        groups_by_ssid.setdefault(ssid, set()).add(group_id)

    local_only_ssids = {
        ssid
        for ssid, group_ids in groups_by_ssid.items()
        if group_ids and all(is_local_coverage_group(groups_by_id.get(group_id)) for group_id in group_ids)
    }
    if not local_only_ssids:
        return {}, set(relevant_ssids)

    scopes_by_ssid = {}
    for group_id, ssids in ssids_by_group.items():
        group = groups_by_id.get(group_id)
        if not is_local_coverage_group(group):
            continue

        for ssid in sorted(ssids & local_only_ssids):
            scopes_by_ssid.setdefault(ssid, []).append(build_local_coverage_scope(group, group_map, ssid))

    return scopes_by_ssid, set(relevant_ssids) - set(scopes_by_ssid)


def is_local_coverage_group(group):
    if not group or normalize_ap_role(group.get("role")) == AP_ROLE_TEST:
        return False
    metadata = group.get("metadata") or {}
    return is_local_coverage_metadata(metadata)


def build_local_coverage_scope(group, group_map, ssid):
    metadata = group.get("metadata") or {}
    radius = parse_float(normalize_coverage_radius_m(metadata.get("coverage_radius_m", "")))
    bssids = {
        str(bssid or "").strip().lower()
        for bssid in group.get("bssids", [])
        if str(bssid or "").strip()
    }
    return {
        "group_id": str(group.get("group_id", "")),
        "ssid": ssid,
        "bssids": bssids,
        "position": group.get("position") or {},
        "radius_m": radius,
        "group_map": group_map,
    }


def local_scope_applies_to_point(scope, point_rows, px_per_meter):
    if scope_has_manual_radius(scope, px_per_meter):
        return point_is_inside_local_radius(scope, point_rows, px_per_meter)

    if scope_has_auto_radius(scope, px_per_meter):
        return point_is_inside_local_radius(scope, point_rows, px_per_meter, radius_key="auto_radius_m")

    return point_has_auto_local_evidence(scope, point_rows)


def scope_has_manual_radius(scope, px_per_meter):
    return bool(scope.get("position")) and bool(scope.get("radius_m")) and bool(px_per_meter)


def scope_has_auto_radius(scope, px_per_meter):
    return bool(scope.get("position")) and bool(scope.get("auto_radius_m")) and bool(px_per_meter)


def apply_auto_local_scope_radii(local_scopes_by_ssid, rows_by_point, px_per_meter):
    if not px_per_meter:
        return

    for scopes in local_scopes_by_ssid.values():
        for scope in scopes:
            if scope_has_manual_radius(scope, px_per_meter):
                continue
            radius_m = estimate_auto_local_scope_radius_m(scope, rows_by_point, px_per_meter)
            if radius_m is not None:
                scope["auto_radius_m"] = radius_m


def estimate_auto_local_scope_radius_m(scope, rows_by_point, px_per_meter):
    if not scope.get("position") or not px_per_meter:
        return None

    distances_m = []
    for point_rows in rows_by_point.values():
        if not point_has_auto_local_evidence(scope, point_rows):
            continue
        distance_m = point_distance_to_scope_ap_m(scope, point_rows, px_per_meter)
        if distance_m is not None:
            distances_m.append(distance_m)

    if not distances_m:
        return None
    return max(distances_m) + LOCAL_COVERAGE_AUTO_RADIUS_MARGIN_M


def point_is_inside_local_radius(scope, point_rows, px_per_meter, radius_key="radius_m"):
    distance_m = point_distance_to_scope_ap_m(scope, point_rows, px_per_meter)
    radius_m = scope.get(radius_key)
    if distance_m is None or radius_m is None:
        return False

    return distance_m <= radius_m


def point_distance_to_scope_ap_m(scope, point_rows, px_per_meter):
    point_x, point_y = point_coordinates(point_rows)
    position = scope.get("position") or {}
    ap_x = parse_float(position.get("x"))
    ap_y = parse_float(position.get("y"))
    if None in (point_x, point_y, ap_x, ap_y) or not px_per_meter:
        return None

    distance_px = ((point_x - ap_x) ** 2 + (point_y - ap_y) ** 2) ** 0.5
    return distance_px / px_per_meter


def point_coordinates(point_rows):
    for row in point_rows:
        x = parse_float(row.get("x"))
        y = parse_float(row.get("y"))
        if x is not None and y is not None:
            return x, y
    return None, None


def point_has_auto_local_evidence(scope, point_rows):
    for row in point_rows:
        if normalize_ssid(row.get("ssid")) != scope.get("ssid"):
            continue
        if not row_matches_local_scope_group(row, scope):
            continue
        signal_dbm = parse_float(row.get("signal_dbm"))
        if signal_dbm is not None and signal_dbm >= LOCAL_COVERAGE_AUTO_MIN_SIGNAL_DBM:
            return True
    return False


def row_matches_local_scope_group(row, scope):
    bssid = str(row.get("bssid", "") or "").strip().lower()
    if not bssid:
        return False
    if bssid in scope.get("bssids", set()):
        return True
    return resolve_ap_group_key(bssid, scope.get("group_map", {})) == scope.get("group_id")
