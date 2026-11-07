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


def remove_wall_faces(lines, selected):
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
    return remaining+caps
