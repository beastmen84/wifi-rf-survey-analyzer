"""Aligned shared-face fragments and reversible physical-divider removal."""
import math

from survey.wall_properties import copy_wall, wall_style

EPS = 1e-6


def relation(a, b):
    if not a.get("wall") or not b.get("wall") or abs(a["wall"]["width"]-b["wall"]["width"]) > EPS:
        return None
    dx, dy = a["x2"]-a["x1"], a["y2"]-a["y1"]
    length = math.hypot(dx, dy)
    ux, uy = dx/length, dy/length
    nx, ny = -uy*a["wall"]["side"], ux*a["wall"]["side"]
    vx, vy = b["x2"]-b["x1"], b["y2"]-b["y1"]
    size = math.hypot(vx, vy)
    if (nx*(-vy/size*b["wall"]["side"])+ny*(vx/size*b["wall"]["side"])) > -1+1e-8:
        return None
    gap = (b["x1"]-a["x1"])*nx+(b["y1"]-a["y1"])*ny
    if abs(gap-a["wall"]["width"]) > EPS:
        return None
    span = sorted((b["x"+s]-a["x1"])*ux+(b["y"+s]-a["y1"])*uy for s in ("1", "2"))
    if min(length, span[1])-max(0, span[0]) <= EPS:
        return None
    return length, span, (ux, uy), (nx, ny), gap


def split_faces(lines):
    thick = [i for i, line in enumerate(lines) if line.get("wall")]
    if len(thick) < 2:
        return list(lines), list(range(len(lines))), set()
    if len(thick) > 2000:
        raise ValueError("wall_complexity")
    cuts, protected = {}, set()
    for i in thick:
        a = lines[i]
        for j in thick:
            if i == j:
                continue
            match = relation(a, lines[j])
            if match is None:
                continue
            length, span, u, _n, _gap = match
            for distance in span:
                if -EPS <= distance <= length+EPS:
                    distance = min(length, max(0, distance))
                    p = (a["x1"]+u[0]*distance, a["y1"]+u[1]*distance)
                    protected.add(p)
                    if EPS < distance < length-EPS:
                        cuts.setdefault(i, set()).add(distance/length)
    result, sources = [], []
    for i, line in enumerate(lines):
        values = sorted({0, 1, *cuts.get(i, ())})
        for low, high in zip(values, values[1:]):
            if high-low <= 1e-12:
                continue
            dx, dy = line["x2"]-line["x1"], line["y2"]-line["y1"]
            result.append(dict(line, x1=line["x1"]+dx*low, y1=line["y1"]+dy*low,
                               x2=line["x1"]+dx*high, y2=line["y1"]+dy*high))
            sources.append(i)
    bins = {(round(p[0], 6), round(p[1], 6)) for p in protected}
    protected.update((line["x"+s], line["y"+s]) for line in result for s in ("1", "2")
        if (round(line["x"+s], 6), round(line["y"+s], 6)) in bins)
    return result, sources, protected


def paired_lines(lines, index):
    result = {index}
    for j, other in enumerate(lines):
        if index == j:
            continue
        match = relation(lines[index], other)
        if match and abs(match[1][0]) <= EPS and abs(match[1][1]-match[0]) <= EPS:
            result.add(j)
    return tuple(sorted(result))


def unused_room_faces(before, after, curves=(), remaining_curves=None):
    """Discard a former room face only when its retained twin still bounds a room."""
    pairs = {i: paired_lines(after, i) for i, line in enumerate(after) if line.get("wall")}
    pairs = {i: pair for i, pair in pairs.items() if len(pair) > 1}
    if not pairs:
        return after
    from survey.plan_faces import RegionPicker
    old = RegionPicker(before, curves)
    current = RegionPicker(after, curves if remaining_curves is None else remaining_curves)
    if old.limited or current.limited:
        return after
    formerly_owned = {id(before[i]) for _path, room in old.records for i in room.lines}
    owned = {i for _path, room in current.records for i in room.lines}
    obsolete = {i for i, pair in pairs.items() if i not in owned and id(after[i]) in formerly_owned
                and any(j in owned for j in pair)}
    return [line for i, line in enumerate(after) if i not in obsolete]


def retained_wall_annotations(items, before, after):
    """Rehost surviving openings from a discarded face onto its physical twin."""
    from survey.plan_annotations import annotation_points, support_intervals, supported
    result = []
    for item in items:
        if supported(item, after):
            result.append(item)
            continue
        a, b = annotation_points(item)
        length = math.dist(a, b)
        nx, ny = -(b[1]-a[1])/length, (b[0]-a[0])/length
        hosts = [line for line in before if any(hi-lo > EPS for lo, hi in support_intervals(a, b, [line]))]
        replacement = None
        for line in after:
            if not any(relation(host, line) for host in hosts):
                continue
            offset = (line["x1"]-a[0])*nx+(line["y1"]-a[1])*ny
            candidate = dict(item, x1=a[0]+nx*offset, y1=a[1]+ny*offset,
                             x2=b[0]+nx*offset, y2=b[1]+ny*offset)
            if supported(candidate, after):
                replacement = candidate
                break
        if replacement is not None:
            result.append(replacement)
    return result


def remove_wall_faces(lines, selected, *, curves=(), remaining_curves=None):
    if not any(line.get("wall") for line in lines):
        return [line for i, line in enumerate(lines) if i not in selected]
    pieces, sources, _protected = split_faces(lines)
    targets = {i for i, source in enumerate(sources) if source in selected}
    for i in tuple(targets):
        targets.update(paired_lines(pieces, i))
    remaining = [line for i, line in enumerate(pieces) if i not in targets]
    caps = []
    for i in sorted(targets):
        for j in paired_lines(pieces, i):
            if j <= i or j not in targets:
                continue
            a, b = pieces[i], pieces[j]
            _length, _span, u, n, gap = relation(a, b)
            for suffix in ("1", "2"):
                p = a["x"+suffix], a["y"+suffix]
                q = p[0]+n[0]*gap, p[1]+n[1]*gap
                from survey.plan_annotations import support_intervals
                if any(lo <= EPS and hi >= gap-EPS for lo, hi in support_intervals(p, q, remaining)):
                    continue
                cap = dict(x1=p[0], y1=p[1], x2=q[0], y2=q[1], color=a["color"])
                # Outer collinear walls continue through the removed divider;
                # otherwise this thin cross-section is a jamb, not a new wall.
                ends = []
                for point in (p, q):
                    ends.append([line for line in remaining if min(math.dist(point, (line["x"+s], line["y"+s])) for s in ("1", "2")) < EPS
                        and abs((line["x2"]-line["x1"])*u[0]+(line["y2"]-line["y1"])*u[1]) < EPS])
                templates = [left for left in ends[0] for right in ends[1]
                             if left["color"] == right["color"] and wall_style(left) == wall_style(right)]
                if templates:
                    template = templates[0]
                    reverse = (template["x2"]-template["x1"])*(q[0]-p[0])+(template["y2"]-template["y1"])*(q[1]-p[1]) < 0
                    cap["color"] = template["color"]
                    copy_wall(template, cap, reverse)
                caps.append(cap)
    return unused_room_faces(pieces, remaining+caps, curves, remaining_curves)
