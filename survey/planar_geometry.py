"""Finite arbitrary-angle segment geometry, with bounded intersection work."""
from collections import defaultdict
import math

EPSILON = 1e-9
MAX_PAIR_CHECKS = 1000000


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def point_projection(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    if length2 == 0:
        length = math.hypot(dx, dy)
        if length == 0:
            return a
        ux, uy = dx / length, dy / length
        distance = min(length, max(0, (point[0] - a[0]) * ux + (point[1] - a[1]) * uy))
        return a[0] + distance * ux, a[1] + distance * uy
    t = min(1, max(0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length2))
    return a[0] + t * dx, a[1] + t * dy


def segment_intersections(a, b, c, d):
    r, s, q = (b[0] - a[0], b[1] - a[1]), (d[0] - c[0], d[1] - c[1]), (c[0] - a[0], c[1] - a[1])
    nr, ns = math.hypot(*r), math.hypot(*s)
    determinant = cross(r, s)
    if abs(determinant) > EPSILON * nr * ns:
        t, u = cross(q, s) / determinant, cross(q, r) / determinant
        if -EPSILON / nr <= t <= 1 + EPSILON / nr and -EPSILON / ns <= u <= 1 + EPSILON / ns:
            for parameter, length, point in ((t, nr, a), (t - 1, nr, b), (u, ns, c), (u - 1, ns, d)):
                if abs(parameter) * length <= EPSILON:
                    return (point,)
            return ((a[0] + t * r[0], a[1] + t * r[1]),)
        return ()
    if abs(cross(q, r)) > EPSILON * nr:
        return ()
    result = []
    for point in (a, b, c, d):
        if all(math.dist(point, point_projection(point, start, end)) <= EPSILON
               for start, end in ((a, b), (c, d))) and point not in result:
            result.append(point)
    return tuple(result)


class PointRegistry:
    def __init__(self):
        self.buckets = defaultdict(list)

    def add(self, point):
        key = (math.floor(point[0] / EPSILON), math.floor(point[1] / EPSILON))
        for x in range(key[0] - 1, key[0] + 2):
            for y in range(key[1] - 1, key[1] + 2):
                for existing in self.buckets.get((x, y), ()):
                    if math.dist(existing, point) <= EPSILON:
                        return existing
        self.buckets[key].append(point)
        return point


def split_general_segments(segments, with_sources=False, limit=40000):
    registry = PointRegistry()
    canonical = {point: registry.add(point) for point in sorted({(line[x], line[y]) for line in segments
                 for x, y in (("x1", "y1"), ("x2", "y2"))})}
    groups = defaultdict(list)
    source_keys = []
    for index, line in enumerate(segments):
        a, b = canonical[(line["x1"], line["y1"])], canonical[(line["x2"], line["y2"])]
        if a == b:
            # Legacy orthogonal cuts can leave sub-EPSILON float residues.
            # Their endpoints already coalesce in our point registry; such an
            # empty edge must not reject an otherwise valid oblique edit.
            source_keys.append(None)
            continue
        key = tuple(sorted((a, b)))
        groups[key].append(index)
        source_keys.append((key, a))
    cuts = {key: set(key) for key in groups}
    count = len(segments)
    if count > limit:
        raise ValueError("Too many editable plan segments")
    boxes = sorted((min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1]), (a, b)) for a, b in groups)
    active, checked = [], 0
    for box in boxes:
        active = [other for other in active if other[1] >= box[0] - EPSILON]
        checked += len(active)
        if checked > MAX_PAIR_CHECKS:
            raise ValueError("Plan intersection complexity limit")
        for other in active:
            if other[3] < box[2] - EPSILON or box[3] < other[2] - EPSILON:
                continue
            for point in segment_intersections(*box[4], *other[4]):
                point = registry.add(point)
                for key in (box[4], other[4]):
                    if point not in cuts[key]:
                        count += len(groups[key])
                        if count > limit:
                            raise ValueError("Too many editable plan segments")
                        cuts[key].add(point)
        active.append(box)
    result, sources = [], []
    for index, (line, source) in enumerate(zip(segments, source_keys)):
        if source is None:
            continue
        key, start = source
        end = key[1] if start == key[0] else key[0]
        dx, dy = end[0] - start[0], end[1] - start[1]
        points = sorted(cuts[key], key=lambda point: (point[0] - start[0]) * dx + (point[1] - start[1]) * dy)
        for a, b in zip(points, points[1:]):
            result.append(dict(line, x1=a[0], y1=a[1], x2=b[0], y2=b[1]))
            sources.append(index)
    return (result, sources) if with_sources else result


def segment_box_intersects(line, left, top, right, bottom):
    low, high = 0, 1
    for start, delta, minimum, maximum in ((line["x1"], line["x2"] - line["x1"], left, right),
                                           (line["y1"], line["y2"] - line["y1"], top, bottom)):
        if delta == 0:
            if not minimum <= start <= maximum:
                return False
        else:
            a, b = sorted(((minimum - start) / delta, (maximum - start) / delta))
            low, high = max(low, a), min(high, b)
            if low > high:
                return False
    return True
