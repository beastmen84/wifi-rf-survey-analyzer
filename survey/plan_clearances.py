"""Analytic footprint-to-structure gaps; decorative stroke width is excluded."""
from dataclasses import dataclass
import math

from survey.plan_objects import object_vertices, object_is_round
from survey.planar_geometry import point_projection, segment_intersections
from survey.plan_curves import curve_bounds, curve_info, curve_points, point_at, parameter_at, project_curve
from survey.plan_curve_geometry import line_curve_intersections

EPS = 1e-7


@dataclass(frozen=True)
class Clearance:
    direction: str
    distance: float
    start: tuple
    end: tuple
    overlap: bool = False


def inside(point, vertices):
    crossing = False
    x, y = point
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        if math.dist(point, point_projection(point, a, b)) <= EPS:
            return False
        if (a[1] > y) != (b[1] > y) and x < a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            crossing = not crossing
    return crossing


def segment_pairs(a, b, c, d):
    hits = segment_intersections(a, b, c, d)
    pairs = [(p, p) for p in hits]
    if not hits:
        pairs = [(p, point_projection(p, c, d)) for p in (a, b)]
        pairs += [(point_projection(p, a, b), p) for p in (c, d)]
        ux, uy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(ux, uy)
        if abs(ux * (d[1] - c[1]) - uy * (d[0] - c[0])) <= EPS * length * math.dist(c, d):
            ux, uy = ux / length, uy / length
            low, high = sorted((p[0] - a[0]) * ux + (p[1] - a[1]) * uy for p in (c, d))
            low, high = max(0, low), min(length, high)
            if low <= high:
                p = (a[0] + (low + high) / 2 * ux, a[1] + (low + high) / 2 * uy)
                pairs.append((p, point_projection(p, c, d)))
    return pairs, hits


def minimum_pairs(pairs, center):
    minimum = min(math.dist(a, b) for a, b in pairs)
    # Keep equal minima in different directions (e.g. a concentric circle).
    return sorted(((a, b) for a, b in pairs if math.dist(a, b) <= minimum + EPS),
                  key=lambda pair: (math.dist(pair[0], center), pair))


def line_gaps(item, vertices, line):
    a, b = (line["x1"], line["y1"]), (line["x2"], line["y2"])
    center = (item["cx"], item["cy"])
    if object_is_round(item):
        wall = point_projection(center, a, b)
        distance, radius = math.dist(center, wall), item["width"] / 2
        if distance < radius - EPS:
            return [(wall, wall)], True
        edge = tuple(center[i] + (wall[i] - center[i]) * radius / distance for i in (0, 1))
        return [(edge, wall)], False
    pairs, contacts = [], [a, b]
    for start, end in zip(vertices, vertices[1:] + vertices[:1]):
        candidates, hits = segment_pairs(start, end, a, b)
        pairs.extend(candidates)
        contacts.extend(hits)
    contacts = sorted(set(contacts), key=lambda p: math.dist(a, p))
    if any(inside(tuple((p[i] + q[i]) / 2 for i in (0, 1)), vertices) for p, q in zip(contacts, contacts[1:])):
        wall = point_projection(center, a, b)
        return [(wall, wall)], True
    return minimum_pairs(pairs, center), False


def curve_gaps(item, vertices, curve):
    center = (item["cx"], item["cy"])
    cx, cy, radius, _start, _sweep = curve_info(curve)
    if object_is_round(item):
        wall = project_curve(curve, center)
        distance, own_radius = math.dist(center, wall), item["width"] / 2
        if distance < own_radius - EPS:
            return [(wall, wall)], True
        walls = curve_points(curve) if math.dist((cx, cy), center) <= EPS else [wall]
        pairs = [(tuple(center[i] + (p[i] - center[i]) * own_radius / math.dist(center, p) for i in (0, 1)), p) for p in walls]
        return minimum_pairs(pairs, center), False
    pairs, fractions = [], [0, 1]
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        edge = dict(x1=a[0], y1=a[1], x2=b[0], y2=b[1])
        for hit in line_curve_intersections(edge, curve):
            pairs.append((hit, hit))
            fractions.append(parameter_at(curve, hit))
        pairs.extend((p, project_curve(curve, p)) for p in (a, b))
        pairs.extend((point_projection(p, a, b), p) for p in (point_at(curve, 0), point_at(curve, 1)))
        length = math.dist(a, b)
        normal = (-(b[1] - a[1]) / length, (b[0] - a[0]) / length)
        for sign in (-1, 1):
            p = (cx + sign * radius * normal[0], cy + sign * radius * normal[1])
            parameter = parameter_at(curve, p)
            if parameter is not None:
                p = point_at(curve, parameter)
                pairs.append((point_projection(p, a, b), p))
    fractions = sorted(set(t for t in fractions if t is not None))
    for a, b in zip(fractions, fractions[1:]):
        point = point_at(curve, (a + b) / 2)
        if inside(point, vertices):
            return [(point, point)], True
    return minimum_pairs(pairs, center), False


class ClearanceIndex:
    """Committed primitive boxes; at most one nearest quote per principal axis."""
    def __init__(self, lines=(), curves=()):
        self.records = [(False, line, (min(line["x1"], line["x2"]), min(line["y1"], line["y2"]),
                        max(line["x1"], line["x2"]), max(line["y1"], line["y2"]))) for line in lines]
        self.records += [(True, curve, curve_bounds(curve)) for curve in curves]
        self.last_key, self.last_result = None, ()

    def query(self, item):
        key = tuple(item.get(k) for k in ("kind", "variant", "cx", "cy", "width", "height", "arm", "angle"))
        if key == self.last_key:
            return self.last_result
        vertices = object_vertices(item)
        box = (min(p[0] for p in vertices), min(p[1] for p in vertices), max(p[0] for p in vertices), max(p[1] for p in vertices))
        center = (item["cx"], item["cy"])
        radius = max(math.dist(center, p) for p in vertices)
        candidates = []
        for index, (curved, primitive, bounds) in enumerate(self.records):
            dx = max(0, box[0] - bounds[2], bounds[0] - box[2])
            dy = max(0, box[1] - bounds[3], bounds[1] - box[3])
            distance = math.hypot(dx, dy)
            if curved:
                cx, cy, r, _, _ = curve_info(primitive)
                # Subtraction of large radii on shallow arcs must remain a
                # conservative lower bound, otherwise a close wall is pruned.
                error = 32 * math.ulp(max(abs(cx), abs(cy), r, *map(abs, center), 1))
                distance = max(distance, abs(math.dist(center, (cx, cy)) - r) - radius - error)
            candidates.append((distance, index))
        best = {}
        overlap = None
        for lower, index in sorted(candidates):
            if len(best) == 2 and lower > max(value.distance for value in best.values()) + EPS:
                break
            curved, primitive, _bounds = self.records[index]
            pairs, intersecting = (curve_gaps if curved else line_gaps)(item, vertices, primitive)
            for a, b in pairs:
                distance = math.dist(a, b)
                dx, dy = ((b[i] - a[i]) if distance > EPS else (b[i] - center[i]) for i in (0, 1))
                axes = (0, 1) if abs(abs(dx) - abs(dy)) <= EPS else (0,) if abs(dx) > abs(dy) else (1,)
                for axis in axes:
                    direction = ("right" if dx >= 0 else "left") if axis == 0 else ("below" if dy >= 0 else "above")
                    quote = Clearance(direction, 0 if distance <= EPS else distance, a, b, intersecting)
                    if axis not in best or quote.distance < best[axis].distance - EPS:
                        best[axis] = quote
                if intersecting:
                    overlap = quote
                    break
            if overlap:
                break
        unique = {}
        for quote in best.values():
            unique.setdefault((quote.start, quote.end), quote)
        result = (overlap,) if overlap else tuple(unique.values())
        self.last_key, self.last_result = key, result
        return result
