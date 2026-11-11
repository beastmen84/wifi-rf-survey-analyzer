"""Analytic intersections and reversible cuts for mixed straight/curved plans."""
from collections import defaultdict
import math

from survey.plan_curves import (EPS, TAU, curve_bounds, curve_info, parameter_at, point_at,
                                subcurve, arc_sagitta)
from survey.plan_geometry import join_segments, normalize_segments
from survey.planar_geometry import PointRegistry, point_projection
from survey.wall_properties import wall_style, copy_wall


def line_curve_intersections(line, curve):
    a = (line["x1"], line["y1"])
    dx, dy = line["x2"] - a[0], line["y2"] - a[1]
    if not (dx or dy):
        return []
    if curve["kind"] == "arc":
        ax, ay = curve["x1"], curve["y1"]
        ux, uy = curve["x2"] - ax, curve["y2"] - ay
        length = math.hypot(ux, uy)
        fx, fy = a[0] - ax, a[1] - ay
        px, py = (ux * fx + uy * fy) / length, (ux * fy - uy * fx) / length
        vx, vy = (ux * dx + uy * dy) / length, (ux * dy - uy * dx) / length
        h = curve["height"]
        offset = h / 2 - length * length / (8 * h)
        qa = vx * vx + vy * vy
        qb = 2 * (px * vx + py * vy) - length * vx - 2 * offset * vy
        qc = px * px + py * py - length * px - 2 * offset * py
    else:
        fx, fy = a[0] - curve["cx"], a[1] - curve["cy"]
        radius = curve["radius"]
        qa, qb = dx * dx + dy * dy, 2 * (fx * dx + fy * dy)
        distance = math.hypot(fx, fy)
        qc = (distance - radius) * (distance + radius)
    disc = math.fsum((qb * qb, -4 * qa * qc))
    closest = -qb / (2 * qa)
    if curve["kind"] == "arc":
        tx, ty = px + closest * vx, py + closest * vy
        terms = (tx * tx, ty * ty, -length * tx, -2 * offset * ty)
        radius = curve_info(curve)[2]
        # The chord-local implicit equation avoids subtracting huge squared
        # radii for shallow arcs, while retaining exact tangent contacts.
        tangent = abs(math.fsum(terms)) <= max(2 * radius * EPS, 16 * sum(math.ulp(term) for term in terms))
    else:
        tangent = abs(math.hypot(fx + closest * dx, fy + closest * dy) - radius) <= EPS
    if tangent:
        disc = 0
    scale = max(1, abs(qb * qb), abs(4 * qa * qc))
    if disc < -1e-14 * scale:
        return []
    disc = max(0, disc)
    q = -.5 * (qb + math.copysign(math.sqrt(disc), qb))
    parameters = [closest] if disc == 0 or not q else [q / qa, qc / q]
    result = []
    for t in parameters:
        if -1e-10 <= t <= 1 + 1e-10:
            t = min(1, max(0, t))
            point = (a[0] + t * dx, a[1] + t * dy)
            if parameter_at(curve, point) is not None and not any(math.dist(point, old) < EPS for old in result):
                result.append(point)
    # Keep explicitly shared endpoints exact, including very shallow arcs.
    if curve["kind"] == "arc":
        for point in (point_at(curve, 0), point_at(curve, 1)):
            projected = point_projection(point, a, (line["x2"], line["y2"]))
            if math.dist(point, projected) <= EPS:
                result = [old for old in result if math.dist(old, point) > EPS]
                result.append(point)
    return result


def same_circle(first, second):
    a, b = curve_info(first), curve_info(second)
    tolerance = max(EPS, 16 * math.ulp(max(abs(value) for value in a[:3] + b[:3])))
    return math.dist(a[:2], b[:2]) <= tolerance and abs(a[2] - b[2]) <= tolerance


def curve_intersections(first, second):
    cx, cy, radius, _, _ = curve_info(first)
    ox, oy, other, _, _ = curve_info(second)
    if radius > other:
        return curve_intersections(second, first)
    distance = math.hypot(ox - cx, oy - cy)
    if same_circle(first, second):
        endpoints = [point_at(curve, t) for curve in (first, second) if curve["kind"] == "arc" for t in (0, 1)]
        return [point for point in endpoints if parameter_at(first, point) is not None
                and parameter_at(second, point) is not None]
    known = []
    for source, target in ((first, second), (second, first)):
        if source["kind"] != "arc":
            continue
        tx, ty, tr, _, _ = curve_info(target)
        for point in (point_at(source, 0), point_at(source, 1)):
            if (abs(math.hypot(point[0] - tx, point[1] - ty) - tr) <= EPS
                    and parameter_at(target, point) is not None
                    and not any(math.dist(point, old) <= EPS for old in known)):
                known.append(point)
    # Two distinct exact stored endpoints already exhaust the possible roots.
    # This avoids angular rejection from center subtraction in shallow arcs.
    if len(known) == 2:
        return known
    if distance <= EPS or distance > radius + other + EPS or distance < abs(radius - other) - EPS:
        return known
    along = ((distance - other) * (distance + other) + radius * radius) / (2 * distance)
    height2 = (radius - along) * (radius + along)
    if height2 < -EPS:
        return known
    tangent = abs(distance - (radius + other)) <= EPS or abs(distance - abs(radius - other)) <= EPS
    height = 0 if tangent else math.sqrt(max(0, height2))
    ux, uy = (ox - cx) / distance, (oy - cy) / distance
    base = (cx + along * ux, cy + along * uy)
    points = [(base[0] - uy * height, base[1] + ux * height)]
    if height > EPS:
        points.append((base[0] + uy * height, base[1] - ux * height))
    precision = max(EPS, 16 * math.ulp(max(abs(cx), abs(cy), abs(ox), abs(oy), radius, other)))
    return known + [p for p in points if parameter_at(first, p) is not None and parameter_at(second, p) is not None
                    and not any(math.dist(p, old) <= precision for old in known)]


def join_curves(curves, lines, origins):
    incidence = defaultdict(list)
    registry = PointRegistry().add
    for line in lines:
        for key in ("1", "2"):
            incidence[registry((line["x" + key], line["y" + key]))].append(("line", -1))
    endpoints = []
    for index, curve in enumerate(curves):
        pair = (registry(point_at(curve, 0)), registry(point_at(curve, 1)))
        endpoints.append(pair)
        for point in pair:
            incidence[point].append(("curve", index))
    parents = list(range(len(curves)))

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for point, items in incidence.items():
        if len(items) != 2 or any(kind != "curve" for kind, _index in items):
            continue
        first, second = (item[1] for item in items)
        if (first == second or curves[first]["color"] != curves[second]["color"]
                or wall_style(curves[first]) != wall_style(curves[second]) or not same_circle(curves[first], curves[second])):
            continue
        vectors = []
        for index in (first, second):
            _, _, _, start, sweep = curve_info(curves[index])
            at_start = math.dist(point, endpoints[index][0]) <= EPS
            angle = start if at_start else start + sweep
            direction = math.copysign(1, sweep) * (1 if at_start else -1)
            vectors.append((-math.sin(angle) * direction, math.cos(angle) * direction))
        if sum(a * b for a, b in zip(*vectors)) < -1 + 1e-8:
            parents[root(second)] = root(first)
    groups = defaultdict(list)
    for index in range(len(curves)):
        groups[root(index)].append(index)
    result, sources = [], []
    for indices in sorted(groups.values(), key=lambda group: group[0]):
        if len(indices) == 1:
            result.append(curves[indices[0]])
        else:
            reference = curves[indices[0]]
            cx, cy, radius, _, direction = curve_info(reference)
            total = sum(abs(curve_info(curves[index])[4]) for index in indices)
            counts = defaultdict(int)
            for index in indices:
                for point in endpoints[index]:
                    counts[point] += 1
            boundary = [point for point, count in counts.items() if count == 1]
            if abs(total - TAU) < 1e-7:
                anchor = next((point for point in counts if len(incidence[point]) != 2), endpoints[indices[0]][0])
                result.append(copy_wall(reference, dict(kind="circle", cx=cx, cy=cy, radius=radius,
                    phase=math.degrees(math.atan2(anchor[1] - cy, anchor[0] - cx)) % 360, color=reference["color"]), direction < 0))
            elif len(boundary) == 2 and total < TAU:
                a, b = boundary
                angle_a, angle_b = math.atan2(a[1] - cy, a[0] - cx), math.atan2(b[1] - cy, b[0] - cx)
                span = ((angle_b - angle_a) if direction > 0 else (angle_a - angle_b)) % TAU
                if abs(span - total) > 1e-7:
                    a, b = b, a
                signed = math.copysign(total, direction)
                result.append(copy_wall(reference, dict(kind="arc", x1=a[0], y1=a[1], x2=b[0], y2=b[1],
                                   height=arc_sagitta(a, b, radius, signed), color=reference["color"])))
            else:
                for index in indices:
                    result.append(curves[index])
                    sources.append(origins[index])
                continue
        sources.append(frozenset().union(*(origins[index] for index in indices)))
    return result, sources


def normalize_plan(lines, curves, with_sources=False):
    if not curves:
        result, sources = normalize_segments(lines, with_sources=True)
        return (result, [], sources, []) if with_sources else (result, [])
    lines, line_origins = normalize_segments(lines, with_sources=True)
    if len(lines) + len(curves) > 40000:
        raise ValueError("Too many drawing primitives")
    registry = PointRegistry().add
    line_cuts = []
    for line in lines:
        line_cuts.append({0.0: registry((line["x1"], line["y1"])), 1.0: registry((line["x2"], line["y2"]))})
    curve_cuts = [{0.0: registry(point_at(curve, 0)), 1.0: registry(point_at(curve, 1))}
                  if curve["kind"] == "arc" else {} for curve in curves]
    boxes = [(min(l["x1"], l["x2"]), min(l["y1"], l["y2"]), max(l["x1"], l["x2"]), max(l["y1"], l["y2"])) for l in lines]
    boxes += [curve_bounds(curve) for curve in curves]
    active, checks, cut_count = [], 0, len(lines) + len(curves)

    def cut(index, point):
        nonlocal cut_count
        point = registry(point)
        if index < len(lines):
            line = lines[index]
            dx, dy = line["x2"] - line["x1"], line["y2"] - line["y1"]
            fraction = ((point[0] - line["x1"]) * dx + (point[1] - line["y1"]) * dy) / (dx * dx + dy * dy)
            mapping = line_cuts[index]
        else:
            fraction = parameter_at(curves[index - len(lines)], point)
            mapping = curve_cuts[index - len(lines)]
        if fraction is not None and not any(math.dist(point, old) < EPS for old in mapping.values()):
            mapping[min(1.0, max(0.0, fraction))] = point
            cut_count += 1
            if cut_count > 40000:
                raise ValueError("Too many curved drawing cuts")

    for index in sorted(range(len(boxes)), key=lambda i: (boxes[i][0], i)):
        box = boxes[index]
        active = [other for other in active if boxes[other][2] >= box[0] - EPS]
        for other in active:
            if index < len(lines) and other < len(lines):
                continue
            old = boxes[other]
            if old[3] < box[1] - EPS or box[3] < old[1] - EPS:
                continue
            checks += 1
            if checks > 1000000:
                raise ValueError("Too many curved intersection candidates")
            if index >= len(lines) and other >= len(lines):
                points = curve_intersections(curves[index - len(lines)], curves[other - len(lines)])
            else:
                li, ci = (index, other) if index < len(lines) else (other, index)
                points = line_curve_intersections(lines[li], curves[ci - len(lines)])
            for point in points:
                cut(index, point)
                cut(other, point)
        active.append(index)
    split_lines, split_origins = [], []
    for index, mapping in enumerate(line_cuts):
        ordered = sorted(mapping.items())
        for (_t, a), (_u, b) in zip(ordered, ordered[1:]):
            if math.dist(a, b) > EPS:
                split_lines.append(dict(lines[index], x1=a[0], y1=a[1], x2=b[0], y2=b[1]))
                split_origins.append(line_origins[index])
    pieces, origins = [], []
    for index, (curve, mapping) in enumerate(zip(curves, curve_cuts)):
        ordered = sorted(mapping.items())
        if curve["kind"] == "circle":
            if len(ordered) < 2:
                phase = math.degrees(math.atan2(ordered[0][1][1] - curve["cy"], ordered[0][1][0] - curve["cx"])) % 360 if ordered else curve.get("phase", 0)
                pieces.append(dict(curve, phase=phase))
                origins.append(frozenset((index,)))
                continue
            ordered.append((ordered[0][0] + 1, ordered[0][1]))
        for (low, a), (high, b) in zip(ordered, ordered[1:]):
            if math.dist(a, b) > EPS:
                pieces.append(subcurve(curve, low, high, a, b))
                origins.append(frozenset((index,)))
    protected = {registry(point_at(curve, t)) for curve in pieces for t in (0, 1)}
    from survey.wall_editing import split_faces, face_join_protection
    if any(line.get("wall") for line in split_lines):
        split_lines, groups = join_segments(split_lines, with_sources=True, protected=protected)
        split_origins = [frozenset().union(*(split_origins[i] for i in group)) for group in groups]
    split_lines, parents, wall_protected = split_faces(split_lines)
    split_origins = [split_origins[i] for i in parents]
    from survey.plan_geometry import split_segments
    split_lines, parents = split_segments(split_lines, with_sources=True)
    split_origins = [split_origins[i] for i in parents]
    wall_protected = face_join_protection(split_lines, wall_protected, pieces)
    protected.update(wall_protected)
    result_lines, joins = join_segments(split_lines, with_sources=True, protected=protected)
    line_sources = [frozenset().union(*(split_origins[index] for index in group)) for group in joins]
    result_curves, curve_sources = join_curves(pieces, result_lines, origins)
    if len(result_curves) > 5000:
        raise ValueError("Too many editable curve fragments")
    return (result_lines, result_curves, line_sources, curve_sources) if with_sources else (result_lines, result_curves)
