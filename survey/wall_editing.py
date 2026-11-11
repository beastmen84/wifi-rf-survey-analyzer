"""Aligned shared-face fragments and reversible physical-divider removal."""
import math
import heapq
from collections import defaultdict

from survey.wall_properties import copy_wall, compatible_wall_style

EPS = 1e-6


class WallFaceIndex:
    """Exact directed matches after a conservative spatial/normal broad phase."""
    def __init__(self, lines):
        self.matches = defaultdict(dict)
        boxes = []
        for i,line in enumerate(lines):
            if not line.get('wall'):
                continue
            dx,dy = line['x2']-line['x1'],line['y2']-line['y1']
            length = math.hypot(dx,dy)
            side,width = line['wall']['side'],line['wall']['width']
            # relation allows a small normal-angle tolerance. Include its full
            # possible drift too, even for unusually long imported segments.
            margin = width/2+EPS+length*.00015
            boxes.append((min(line['x1'],line['x2'])-margin,max(line['x1'],line['x2'])+margin,
                          min(line['y1'],line['y2'])-margin,max(line['y1'],line['y2'])+margin,
                          i,width,-dy/length*side,dx/length*side))
        active,ends = {},[]
        count = 0
        for box in sorted(boxes):
            left,right,top,bottom,i,width,nx,ny = box
            while ends and ends[0][0] < left:
                _end,j = heapq.heappop(ends)
                active.pop(j,None)
            for other in active.values():
                _l,_r,t,b,j,w,mx,my = other
                if b < top or bottom < t or abs(width-w) > EPS or nx*mx+ny*my > -1+1e-8:
                    continue
                for a,b in ((i,j),(j,i)):
                    match = relation(lines[a],lines[b])
                    if match is not None:
                        self.matches[a][b] = match
                        count += 1
                        if count > 80000:
                            raise ValueError('wall_complexity')
            active[i] = box
            heapq.heappush(ends,(right,i))


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
    faces = WallFaceIndex(lines)
    for i in thick:
        a = lines[i]
        for j,match in sorted(faces.matches[i].items()):
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


def paired_lines(lines, index, *, exact=False, faces=None):
    result = {index}
    matches = (faces.matches[index].items() if faces is not None else
               ((j,relation(lines[index],other)) for j,other in enumerate(lines) if j != index))
    for j, match in matches:
        if index == j:
            continue
        if match and (not exact or (abs(match[1][0]) <= EPS and abs(match[1][1]-match[0]) <= EPS)):
            result.add(j)
    return tuple(sorted(result))


def physical_faces(lines, index):
    """Pick the physical divider, including its merged hidden corner extensions."""
    return paired_lines(lines, index)


class _WallCoverage:
    """Local coverage queries include every possible bounded miter at the cap."""
    def __init__(self, lines, curves=()):
        from PySide6.QtCore import QRectF
        from survey.plan_curves import curve_bounds
        self.line_count = len(lines)
        shapes = [*lines, *curves]
        margin = 4*max((s['wall']['width'] for s in shapes if s.get('wall')), default=0)
        self.rows = []
        for i, shape in enumerate(shapes):
            if not shape.get('wall'):
                continue
            left, top, right, bottom = curve_bounds(shape) if 'kind' in shape else (
                min(shape['x1'],shape['x2']), min(shape['y1'],shape['y2']),
                max(shape['x1'],shape['x2']), max(shape['y1'],shape['y2']))
            box = QRectF(left-margin,top-margin,right-left+2*margin,bottom-top+2*margin)
            self.rows.append((i,shape,box))
        self.shapes = shapes

    def covers(self, index, excluded=()):
        from survey.wall_geometry import solid, wall_solids, united, path_area
        body = solid(self.shapes[index])
        box, skipped = body.boundingRect(), {index, *excluded}
        nearby = [(i,shape) for i,shape,bounds in self.rows if i not in skipped and bounds.intersects(box)]
        rest = united(path for _color,path in wall_solids(
            [shape for i,shape in nearby if i < self.line_count],
            [shape for i,shape in nearby if i >= self.line_count]))
        return path_area(body.subtracted(rest)) <= EPS


def face_join_protection(lines, protected, curves=()):
    """Join hidden end caps back to their side, preserving real shared boundaries."""
    if not protected:
        return protected
    coverage = _WallCoverage(lines, curves)
    incidence = defaultdict(list)
    endpoints = defaultdict(list)
    for i, line in enumerate(lines):
        for suffix in ('1', '2'):
            point = line['x'+suffix], line['y'+suffix]
            endpoints[point].append(i)
            if point in protected:
                incidence[point].append(i)
    removable, covered = set(), {}
    faces = WallFaceIndex(lines)
    for point, indices in incidence.items():
        if len(indices) != 2:
            continue
        a, b = (lines[i] for i in indices)
        if not a.get('wall') or a['color'] != b['color'] or not compatible_wall_style(a,b):
            continue
        vectors = []
        for line in (a, b):
            other = next((line['x'+s], line['y'+s]) for s in ('1', '2')
                         if (line['x'+s], line['y'+s]) != point)
            vectors.append((other[0]-point[0], other[1]-point[1]))
        u, v = vectors
        if abs(u[0]*v[1]-u[1]*v[0]) > EPS*math.hypot(*u)*math.hypot(*v) or u[0]*v[0]+u[1]*v[1] >= 0:
            continue
        for i in indices:
            if len(paired_lines(lines, i, exact=True, faces=faces)) > 1:
                continue
            # A covered bridge between two paired spans is a real T junction,
            # not an end cap: its two dividers must remain independently editable.
            continuations = sum(any(j != i and lines[j]['color'] == lines[i]['color']
                                    and compatible_wall_style(lines[j],lines[i])
                                    for j in endpoints[(lines[i]['x'+s], lines[i]['y'+s])])
                                for s in ('1', '2'))
            if continuations == 2:
                continue
            if i not in covered:
                covered[i] = coverage.covers(i)
            if covered[i]:
                removable.add(point)
                break
    return protected-removable


def unused_room_faces(before, after, curves=(), remaining_curves=None):
    """Discard a former room face only when its retained twin still bounds a room."""
    faces = WallFaceIndex(after)
    pairs = {i: paired_lines(after, i, faces=faces) for i, line in enumerate(after) if line.get("wall")}
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
    coverage = _WallCoverage(after, curves if remaining_curves is None else remaining_curves)
    for i, line in enumerate(after):
        if i in obsolete or i in owned or id(line) not in formerly_owned or not line.get('wall'):
            continue
        if coverage.covers(i, obsolete):
            obsolete.add(i)
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
    faces = WallFaceIndex(pieces)
    targets = {i for i, source in enumerate(sources) if source in selected}
    paired_sources = {sources[i] for i in targets if len(paired_lines(pieces, i, exact=True, faces=faces)) > 1}
    # Normalized shared sides may include covered corner extensions. Preserve
    # those needed by a retained perimeter when removing only the divider.
    caps_to_keep = {i for i in targets if sources[i] in paired_sources and len(paired_lines(pieces, i, exact=True, faces=faces)) == 1
                    and any(math.dist((pieces[i]['x'+s], pieces[i]['y'+s]),
                                      (other['x'+t], other['y'+t])) <= EPS
                            for j,other in enumerate(pieces) if j not in targets for s in ('1','2') for t in ('1','2'))}
    targets.difference_update(caps_to_keep)
    for i in tuple(targets):
        targets.update(paired_lines(pieces, i, exact=True, faces=faces))
    remaining = [line for i, line in enumerate(pieces) if i not in targets]
    caps = []
    for i in sorted(targets):
        for j in paired_lines(pieces, i, exact=True, faces=faces):
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
                             if left["color"] == right["color"] and compatible_wall_style(left,right)]
                if templates:
                    template = templates[0]
                    reverse = (template["x2"]-template["x1"])*(q[0]-p[0])+(template["y2"]-template["y1"])*(q[1]-p[1]) < 0
                    cap["color"] = template["color"]
                    copy_wall(template, cap, reverse)
                caps.append(cap)
    return unused_room_faces(pieces, remaining+caps, curves, remaining_curves)
