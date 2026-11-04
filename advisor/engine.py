"""Deterministic survey analysis. Inputs are copied; AP/survey data is never changed."""

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import math

from ap.groups import (AP_ROLE_INTERNAL, AP_ROLE_TEST, build_default_manual_groups,
    build_bssid_to_manual_group_map, build_ap_group_channel_override_map,
    normalize_ap_role, resolve_ap_group_key, is_ap_group_confirmed)
from ap.positioning import analyze_dominant_ap_position, AP_POSITION_STRONG_FAR, parse_point
from ap.metadata import build_ap_metadata_warnings
from maps.heatmap import channel_overlap_weight, get_channel_frequency_range, radio_geometry_supported
from maps.quality import evaluate_point_quality, QUALITY_GOOD, is_truthy
from survey.scope import relevant_ssids_by_point
from wifi.band import get_row_band
from wifi.evidence import scan_confidence, raw_evidence_complete
from survey.store import MEASUREMENT_POINTS_KEY
import json
from advisor.models import (AnalysisProfile, AnalysisReport, EvidencePoint, EvidenceReading, Finding,
    analysis_fingerprint, valid_channel)


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def row_confidence(row):
    return scan_confidence(row, require_samples=True)


def analyze_survey(rows, raw_rows=(), groups=(), relevant_ssids=(), profile=None,
                   px_per_meter=None, survey_name="", context_metadata=None):
    profile = profile or AnalysisProfile()
    rows, raw_rows, groups = deepcopy(list(rows)), deepcopy(list(raw_rows)), deepcopy(list(groups))
    relevant = {str(ssid) for ssid in relevant_ssids if str(ssid)}
    fingerprint = analysis_fingerprint(rows, raw_rows, groups, relevant, px_per_meter, profile, survey_name, context_metadata)
    px_per_meter = number(px_per_meter)
    if px_per_meter is not None and px_per_meter <= 0:
        px_per_meter = None
    if not groups:
        groups = build_default_manual_groups(rows)
    unconfirmed = {str(g.get("group_id")) for g in groups if not is_ap_group_confirmed(g)}
    # Keep the UI's proposed grouping, but do not suppress RF neighbors based on it.
    expanded = []
    for group in groups:
        if not is_ap_group_confirmed(group) and len(group.get("bssids", ())) > 1:
            for bssid in group["bssids"]:
                expanded.append({**group, "group_id": bssid.lower(), "bssids": [bssid],
                    "alias": f"{group.get('alias') or group['group_id']} ({bssid})", "position": None})
                unconfirmed.add(bssid.lower())
        else:
            expanded.append(group)
    groups = expanded
    group_map = build_bssid_to_manual_group_map(groups)
    by_group = {str(g["group_id"]): g for g in groups if g.get("group_id")}
    labels = {key: str(g.get("alias") or key) for key, g in by_group.items()}
    clean, points, invalid, invalid_points = [], {}, 0, set()
    for source in rows:
        x, y, signal = number(source.get("x")), number(source.get("y")), number(source.get("signal_dbm"))
        if None in (x, y, signal) or not -120 <= signal <= 0 or not source.get("bssid"):
            invalid += 1
            if source.get("point_id"):
                invalid_points.add(str(source["point_id"]))
            continue
        group_id = resolve_ap_group_key(source["bssid"], group_map)
        group = by_group.get(group_id, {})
        role = normalize_ap_role(group.get("role"))
        if role == AP_ROLE_TEST:
            continue
        timestamp = str(source.get("timestamp", ""))
        point_id = str(source.get("point_id") or f"{timestamp}|{x}|{y}")
        points.setdefault(point_id, EvidencePoint(point_id, x, y, timestamp))
        channel = number(source.get("channel"))
        width = number(source.get("channel_width_mhz"))
        clean.append({**source, "point_id": point_id, "x": x, "y": y,
            "signal_dbm": signal, "ssid": str(source.get("ssid", "")),
            "group_id": group_id, "role": role, "band": get_row_band(source),
            "channel": int(channel) if channel is not None and channel.is_integer() else None,
            "width": int(width) if width in {20, 40, 80, 160, 320} else None,
            "confidence": row_confidence(source) if raw_evidence_complete(source, raw_rows) else 0.0})
    empty_points = []
    try:
        ledger = (context_metadata or {}).get(MEASUREMENT_POINTS_KEY, "[]")
        for point in json.loads(ledger):
            if point.get("status") == "empty" and point.get("capture", {}).get("status") == "complete":
                x, y = number(point.get("x")), number(point.get("y"))
                if x is not None and y is not None:
                    pid = str(point["point_id"])
                    points[pid] = EvidencePoint(pid, x, y, str(point["timestamp"]))
                    empty_points.append(pid)
    except (ValueError, TypeError, KeyError):
        invalid += 1
    findings = []

    def add(rule, category, point_ids=(), group_ids=(), ssid="", band="", metrics=None,
            severity="warning", confidence="medium", action="", limitations=()):
        point_ids, group_ids = tuple(sorted(set(point_ids))), tuple(sorted(set(group_ids)))
        identity = repr((rule, group_ids, ssid, band)).encode()
        findings.append(Finding(sha256(identity).hexdigest()[:16], rule, category, severity, confidence,
            group_ids, ssid, band, point_ids, metrics or {}, action or rule, tuple(limitations)))

    if invalid:
        add("invalid_data", "data", metrics={"rows": invalid}, confidence="high")
    if empty_points:
        add("empty_measurement", "coverage", empty_points,
            metrics={"points": len(empty_points)}, confidence="high", limitations=("missing_is_not_proven",))
    for group_id in sorted(unconfirmed & by_group.keys()):
        pids = {r["point_id"] for r in clean if r["group_id"] == group_id}
        if pids:
            add("unconfirmed_group", "data", pids, (group_id,), metrics={"points": len(pids)}, confidence="high")
    if not relevant:
        add("scope_required", "data", points, metrics={"points": len(points)}, confidence="high")
    if len(points) < profile.minimum_points:
        add("sparse_survey", "data", points, metrics={"points": len(points), "minimum": profile.minimum_points},
            confidence="high", severity="notice")
    scope = relevant_ssids_by_point(clean, groups, relevant, px_per_meter)
    quality = evaluate_point_quality(clean, raw_rows, relevant_ssids=relevant,
        relevant_ssids_by_point=scope) if relevant else {}
    poor = {pid for pid, result in quality.items() if result["status"] != QUALITY_GOOD}
    poor.update(invalid_points & points.keys())
    poor.update(row["point_id"] for row in clean if row["ssid"] in relevant
                and (row["confidence"] < profile.minimum_confidence or not row["band"]))
    adapters = {str(r.get("adapter_id")) for r in clean if r["ssid"] in relevant and r.get("adapter_id")}
    if len(adapters) > 1:
        poor.update(r["point_id"] for r in clean)
        add("mixed_receivers", "data", points, metrics={"points": len(points)}, confidence="high")
    poor.update(empty_points)
    if poor:
        add("low_quality", "data", poor, metrics={"points": len(poor), "total": len(points)}, confidence="high")
    for ssid in sorted(relevant):
        missing = [pid for pid, result in quality.items() if ssid in result.get("missing_relevant", ())]
        if missing:
            add("missing_network", "coverage", missing, ssid=ssid,
                metrics={"points": len(missing)}, confidence="medium", limitations=("missing_is_not_proven",))

    selected = [r for r in clean if r["ssid"] in relevant and r["role"] == AP_ROLE_INTERNAL]
    if selected and px_per_meter is None:
        add("scale_required", "data", (r["point_id"] for r in selected),
            confidence="high", severity="notice")
    model_conflicts = set(unconfirmed) | {r["group_id"] for r in clean if not r["band"]}
    for warning in build_ap_metadata_warnings(clean, groups):
        group_id = warning["group_id"]
        pids = {r["point_id"] for r in selected if r["group_id"] == group_id}
        if pids:
            model_conflicts.add(group_id)
            add("metadata_mismatch", "data", pids, (group_id,), confidence="high",
                metrics={key: ", ".join(warning[key]) for key in (
                    "expected_channels", "observed_channels", "expected_bands", "observed_bands")})
    selected_points = {r["point_id"] for r in selected}
    limited = {r["point_id"] for r in clean if r["point_id"] in selected_points and r["signal_dbm"] >= -85 and (r["width"] is None
        or r.get("freshness") != "fresh" or r.get("signal_kind") != "direct"
        or not radio_geometry_supported(r["channel"], r["width"], r["band"], r.get("secondary_channel_offset"))
        or r["band"] not in {"2.4", "5", "6"}
        or (r["band"] == "6" and get_row_band({"frequency_mhz": r.get("frequency_mhz")}) != "6"))}
    if limited:
        add("scanner_limits", "data", limited, metrics={"points": len(limited)}, confidence="high")
    trusted = lambda r: r["confidence"] >= profile.minimum_confidence and r["point_id"] not in poor
    buckets = defaultdict(list)
    for row in selected:
        if row["band"] in {"2.4", "5", "6"}:
            buckets[(row["ssid"], row["band"], row["point_id"])].append(row)
    weak, dominance, roaming = defaultdict(set), defaultdict(set), defaultdict(set)
    dominance_neighbors, roaming_neighbors, dominance_distances = defaultdict(set), defaultdict(set), defaultdict(list)
    weak_totals, power_safe = defaultdict(set), defaultdict(set)
    for (ssid, band, pid), readings in sorted(buckets.items()):
        if ssid not in scope.get(pid, relevant):
            continue
        best = max(readings, key=lambda r: r["signal_dbm"])
        if not trusted(best):
            continue
        weak_totals[(ssid, band)].add(pid)
        if best["signal_dbm"] < profile.coverage_dbm:
            weak[(ssid, band)].add(pid)
        physical = {}
        for row in readings:
            if trusted(row) and (row["group_id"] not in physical
                    or row["signal_dbm"] > physical[row["group_id"]]["signal_dbm"]):
                physical[row["group_id"]] = row
        available_groups = [g for g in groups if g.get("group_id") in physical]
        position = analyze_dominant_ap_position({**best, "dominant_ap_group": best["group_id"],
            "dominant_signal_dbm": best["signal_dbm"]}, available_groups, px_per_meter)
        if position.get("warnings"):
            key = (best["group_id"], ssid, band)
            dominance[key].add(pid)
            dominance_neighbors[key].update(set(physical) - {best["group_id"]})
            dominance_distances[key].append(position["dominant_distance_m"])
            if AP_POSITION_STRONG_FAR in position["warnings"] and any(
                r["group_id"] != best["group_id"] and r["signal_dbm"] >= profile.coverage_dbm
                for r in physical.values()):
                power_safe[key].add(pid)
        connected = [r for r in readings if is_truthy(r.get("is_connected")) and trusted(r)]
        if connected:
            connected = max(connected, key=lambda r: r["signal_dbm"])
            if connected["group_id"] != best["group_id"] and best["signal_dbm"] - connected["signal_dbm"] >= 8:
                key = (connected["group_id"], ssid, band)
                roaming[key].add(pid)
                roaming_neighbors[key].add(best["group_id"])
    for (ssid, band), pids in sorted(weak.items()):
        add("weak_coverage", "coverage", pids, ssid=ssid, band=band,
            metrics={"points": len(pids), "total": len(weak_totals[(ssid, band)]), "threshold": profile.coverage_dbm},
            confidence="high" if len(pids) >= profile.minimum_points else "medium",
            limitations=("measured_points_only",))
    for (group_id, ssid, band), pids in sorted(dominance.items()):
        safe_locations = {(points[pid].x, points[pid].y) for pid in power_safe[(group_id, ssid, band)]}
        spaced_locations = []
        for location in sorted(safe_locations):
            if px_per_meter and all(math.dist(location, other) / px_per_meter >= 2.0 for other in spaced_locations):
                spaced_locations.append(location)
        # Also inspect every measured location served by this AP: reductions must
        # not strand locations with no independently observed alternative.
        dependent = any(r["group_id"] == group_id and r["ssid"] == ssid and r["band"] == band
            and not any(other["point_id"] == r["point_id"] and other["ssid"] == ssid
                and other["band"] == band and other["group_id"] != group_id and trusted(other)
                and other["signal_dbm"] >= profile.coverage_dbm for other in selected)
            for r in selected)
        can_test_power = (len(spaced_locations) >= profile.minimum_points and not dependent
                          and not weak.get((ssid, band)) and not poor and not invalid and group_id not in model_conflicts)
        key = (group_id, ssid, band)
        add("dominance", "position", pids, (group_id,), ssid, band,
            {"points": len(pids), "neighbor_ids": tuple(sorted(dominance_neighbors[key])),
                "distance_min_m": round(min(dominance_distances[key]), 1),
                "distance_max_m": round(max(dominance_distances[key]), 1)},
            confidence="medium" if len(pids) >= profile.minimum_points else "low",
            action="power_trial" if can_test_power else "position_review", limitations=("no_propagation_model",))
    for (group_id, ssid, band), pids in sorted(roaming.items()):
        add("roaming", "roaming", pids, (group_id,), ssid, band,
            {"points": len(pids), "delta": 8, "neighbor_ids": tuple(sorted(roaming_neighbors[(group_id, ssid, band)]))},
            confidence="medium", limitations=("client_decides",))
    for group_id in sorted({r["group_id"] for r in selected}):
        if parse_point(by_group.get(group_id, {}).get("position")) is None:
            pids = {r["point_id"] for r in selected if r["group_id"] == group_id}
            add("missing_position", "position", pids, (group_id,), metrics={"points": len(pids)},
                confidence="high", severity="notice")
    _channel_analysis(clean, selected, groups, profile, trusted, add, model_conflicts)
    order = {"data": 0, "channels": 1, "coverage": 2, "position": 3, "roaming": 4}
    findings.sort(key=lambda f: (order[f.category], 0 if f.rule == "channel_change" else 1,
                                  {"warning": 0, "notice": 1}.get(f.severity, 2),
                                  f.metrics.get("step", 0), f.finding_id))
    from survey.measurement_quality import assess_survey_measurements
    measurements = assess_survey_measurements(rows, raw_rows, context_metadata, relevant, profile.coverage_dbm)
    return AnalysisReport(fingerprint, profile, tuple(findings), tuple(points[k] for k in sorted(points)),
        labels, tuple(sorted(relevant)), len(rows), len(raw_rows), invalid,
        datetime.now(timezone.utc).isoformat(timespec="seconds"), survey_name,
        tuple(EvidenceReading(r["point_id"], r["group_id"], r["ssid"], r["band"], r["signal_dbm"],
            r["channel"], r["width"], r["confidence"], str(r.get("backend", "")), str(r.get("adapter_id", "")),
            str(r.get("signal_kind") or "unknown"), str(r.get("freshness") or "unknown")) for r in clean), measurements=measurements)


def _channel_analysis(clean, selected, groups, profile, trusted, add, model_conflicts):
    """One node per physical AP/band; optimize a single coherent channel plan."""
    observations = defaultdict(dict)
    channel_sets, widths = defaultdict(set), defaultdict(set)
    managed = {(r["group_id"], r["band"]) for r in selected}
    unknown_band = [r for r in clean if r["band"] not in {"2.4", "5", "6"} and r["signal_dbm"] >= -85]
    overrides = build_ap_group_channel_override_map(groups)
    for row in clean:
        if row["band"] not in {"2.4", "5", "6"} or row["signal_dbm"] < -85:
            continue
        node = (row["group_id"], row["band"])
        channel_sets[node].add(row["channel"])
        widths[node].add(row["width"])
        previous = observations[node].get(row["point_id"])
        if previous is None or row["signal_dbm"] > previous["signal_dbm"]:
            observations[node][row["point_id"]] = row
    for band in ("2.4", "5", "6"):
        nodes = sorted(node for node in observations if node[1] == band)
        graph = defaultdict(dict)
        uncertain = defaultdict(set)
        edge_points = {}
        for index, first in enumerate(nodes):
            for second in nodes[index + 1:]:
                common = set(observations[first]) & set(observations[second])
                if any(trusted(observations[first][pid]) and not trusted(observations[second][pid]) for pid in common):
                    uncertain[first].add(second)
                if any(trusted(observations[second][pid]) and not trusted(observations[first][pid]) for pid in common):
                    uncertain[second].add(first)
                usable = {pid for pid in common if trusted(observations[first][pid]) and trusted(observations[second][pid])}
                if not usable:
                    continue
                weight = sum(min(1.0, 10 ** ((min(observations[first][pid]["signal_dbm"],
                    observations[second][pid]["signal_dbm"]) + 70) / 20)) for pid in usable)
                graph[first][second] = graph[second][first] = weight
                edge_points[(first, second)] = usable
        channels = {node: next(iter(channel_sets[node])) if len(channel_sets[node]) == 1 else None for node in nodes}
        node_widths = {node: next(iter(widths[node])) if len(widths[node]) == 1 else None for node in nodes}
        eligible = []
        for node in nodes:
            if node not in managed:
                continue
            group_id = node[0]
            pids = set(observations[node])
            if channels[node] is None or not valid_channel(channels[node], band):
                add("channel_unstable", "channels", pids, (group_id,), band=band,
                    metrics={"points": len(pids)}, confidence="high")
            affected = set().union(*(pids & set(observations[other]) for other in uncertain[node]))
            affected.update(r["point_id"] for r in unknown_band if r["point_id"] in pids)
            if affected:
                add("channel_evidence", "data", affected, (group_id,), band=band,
                    metrics={"points": len(affected), "neighbor_ids": tuple(sorted({other[0] for other in uncertain[node]}
                        | {r["group_id"] for r in unknown_band if r["point_id"] in pids}))},
                    confidence="high")
            if node in overrides:
                add("model_override", "channels", pids, (group_id,), band=band,
                    metrics={"channel": overrides[node]}, confidence="high", severity="notice")
            if node_widths[node] and node_widths[node] > 20 and graph[node]:
                add("channel_width", "channels", pids, (group_id,), band=band,
                    metrics={"width": node_widths[node]}, confidence="medium", severity="notice")
            overlapping = set()
            for neighbor in graph[node]:
                for pid in set(observations[node]) & set(observations[neighbor]):
                    a, b = observations[node][pid], observations[neighbor][pid]
                    if trusted(a) and trusted(b) and a["channel"] and b["channel"] and channel_overlap_weight(
                            a["channel"], b["channel"], band, a["width"], b["width"]) > 0:
                        overlapping.add(pid)
            if overlapping:
                add("channel_overlap", "channels", overlapping, (group_id,), band=band,
                    metrics={"points": len(overlapping), "neighbors": len(graph[node]),
                        "neighbor_ids": tuple(n[0] for n in graph[node])},
                    confidence="medium", limitations=("not_airtime",))
            candidates = tuple(sorted(set(profile.channels(band))))
            complete = not affected and all(channels[n] is not None and valid_channel(channels[n], band)
                and node_widths[n] is not None and (band != "2.4" or node_widths[n] == 20)
                and node_widths[n] != 320
                and n[0] not in model_conflicts
                and (band != "6" or all(get_row_band({"frequency_mhz": r.get("frequency_mhz")}) == "6"
                    for r in observations[n].values()))
                for n in (node, *graph[node]))
            if (complete and node not in overrides and group_id not in model_conflicts and candidates
                    and len(overlapping) >= profile.minimum_points
                    and all(band == "2.4" or get_channel_frequency_range(c, node_widths[node], band)
                            for c in candidates)):
                eligible.append(node)
        # Coordinate descent only accepts strict global improvements. All proposals
        # below are steps in this same plan; neighbors do not independently pick
        # the same supposedly empty channel.
        assignment = dict(channels)

        def plan_cost(plan):
            return sum(weight * channel_overlap_weight(plan[first], plan[second], band,
                node_widths[first], node_widths[second]) for first in nodes for second, weight in graph[first].items()
                if first < second and plan[first] is not None and plan[second] is not None
                and node_widths[first] is not None and node_widths[second] is not None)

        baseline_cost = plan_cost(assignment)

        def node_cost(node, channel):
            return sum(weight * channel_overlap_weight(channel, assignment[other], band,
                node_widths[node], node_widths[other]) for other, weight in graph[node].items())

        moves = []
        for _pass in range(3):
            changed = False
            for node in eligible:
                before = node_cost(node, assignment[node])
                best = min(profile.channels(band), key=lambda c: (node_cost(node, c), c != assignment[node], c))
                after = node_cost(node, best)
                if best != assignment[node] and before > 0 and after < before * 0.9:
                    old = assignment[node]
                    assignment[node] = best
                    moves.append((node, old, best, before, after))
                    changed = True
            if not changed:
                break
        # Present final assignments, not intermediate changes to the same AP.
        final_moves = []
        for node, _old, _new, _before, _after in moves:
            if node not in final_moves and assignment[node] != channels[node]:
                final_moves.append(node)
        for step, node in enumerate(final_moves, 1):
            pids = set().union(*(edge_points.get(tuple(sorted((node, other))), set()) for other in graph[node]))
            add("channel_change", "channels", pids, (node[0],), band=band,
                metrics={"old_channel": channels[node], "new_channel": assignment[node], "step": step,
                    "points": len(pids), "neighbor_ids": tuple(n[0] for n in graph[node]),
                    "modeled_before": round(baseline_cost, 3), "modeled_after": round(plan_cost(assignment), 3)},
                confidence="medium", limitations=("joint_plan", "not_airtime", "channel_policy"))
