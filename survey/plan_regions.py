"""Bounded faces of finite segment graphs, without raster closure."""
from bisect import bisect_left, bisect_right, insort
from collections import defaultdict
from dataclasses import dataclass
import math
from survey.planar_geometry import split_general_segments

# This only absorbs arithmetic noise in derived geometry, never edits the model.
COORDINATE_EPSILON = 1e-9
MAX_INTERSECTIONS = 100000


@dataclass(frozen=True)
class PlanRegions:
    faces: tuple = ()
    limited: bool = False
    boundaries: tuple = ()


@dataclass(frozen=True)
class RegionBoundary:
    lines: frozenset
    curves: frozenset
    area: float


def canonical_coordinates(values):
    result = {}
    anchor = None
    for value in sorted(set(values)):
        if anchor is None or value - anchor > COORDINATE_EPSILON:
            anchor = value
        result[value] = anchor
    return result


def merged_lines(groups):
    lines = []
    for coordinate, intervals in sorted(groups.items()):
        start = end = None
        for low, high in sorted(intervals):
            if low == high:
                continue
            if end is not None and low <= end:
                end = max(end, high)
            else:
                if end is not None:
                    lines.append((coordinate, start, end))
                start, end = low, high
        if end is not None:
            lines.append((coordinate, start, end))
    return lines


def direction(origin, point):
    if point[0] > origin[0]:
        return 0
    if point[1] > origin[1]:
        return 1
    return 2 if point[0] < origin[0] else 3


def closed_plan_regions(segments, max_intersections=MAX_INTERSECTIONS):
    """Return all bounded faces, with an optimized path for axis-aligned data.

    Merge duplicates/collinear overlaps, split T/cross intersections, then walk
    directed edges in angular order. Positive-area walks bound finite faces;
    open chains and the unbounded exterior are excluded. Nested faces use a
    nonzero winding union when painted, so nested rooms do not punch grid holes.
    A complexity limit returns no partial result and leaves all grid lines normal.
    """
    if not segments:
        return PlanRegions()
    if any(line["x1"] != line["x2"] and line["y1"] != line["y2"] for line in segments):
        try:
            pieces = split_general_segments(segments, limit=len(segments) + 2 * max_intersections)
        except ValueError:
            return PlanRegions(limited=True)
        graph = defaultdict(set)
        for line in pieces:
            a, b = (line["x1"], line["y1"]), (line["x2"], line["y2"])
            graph[a].add(b)
            graph[b].add(a)
        return PlanRegions(tuple(walk_faces(graph)))
    xs = canonical_coordinates(line[key] for line in segments for key in ("x1", "x2"))
    ys = canonical_coordinates(line[key] for line in segments for key in ("y1", "y2"))
    horizontal, vertical = defaultdict(list), defaultdict(list)
    for line in segments:
        x1, x2 = xs[line["x1"]], xs[line["x2"]]
        y1, y2 = ys[line["y1"]], ys[line["y2"]]
        if y1 == y2:
            horizontal[y1].append(tuple(sorted((x1, x2))))
        else:
            vertical[x1].append(tuple(sorted((y1, y2))))
    horizontal, vertical = merged_lines(horizontal), merged_lines(vertical)
    h_cuts = [{start, end} for _, start, end in horizontal]
    v_cuts = [{start, end} for _, start, end in vertical]
    events = [(start, 0, index) for index, (_, start, _) in enumerate(vertical)]
    events += [(end, 2, index) for index, (_, _, end) in enumerate(vertical)]
    events += [(y, 1, index) for index, (y, _, _) in enumerate(horizontal)]
    active, positions, intersections = {}, [], 0
    for y, kind, index in sorted(events):
        if kind == 0:
            x = vertical[index][0]
            active[x] = index
            insort(positions, x)
        elif kind == 2:
            x = vertical[index][0]
            del active[x]
            positions.pop(bisect_left(positions, x))
        else:
            _, start, end = horizontal[index]
            first, last = bisect_left(positions, start), bisect_right(positions, end)
            intersections += last - first
            if intersections > max_intersections:
                return PlanRegions(limited=True)
            for x in positions[first:last]:
                h_cuts[index].add(x)
                v_cuts[active[x]].add(y)

    graph = defaultdict(set)
    for lines, cuts, horizontal_axis in ((horizontal, h_cuts, True), (vertical, v_cuts, False)):
        for (coordinate, _, _), split in zip(lines, cuts):
            points = [(value, coordinate) if horizontal_axis else (coordinate, value) for value in sorted(split)]
            for a, b in zip(points, points[1:]):
                graph[a].add(b)
                graph[b].add(a)
    return PlanRegions(tuple(walk_faces(graph)))


def walk_faces(graph):
    neighbors = {point: sorted(adjacent, key=lambda other: math.atan2(other[1] - point[1], other[0] - point[0]))
                 for point, adjacent in graph.items()}
    visited, faces = set(), []
    for start, adjacent in neighbors.items():
        for following in adjacent:
            if (start, following) in visited:
                continue
            a, b, face = start, following, []
            while (a, b) not in visited:
                visited.add((a, b))
                face.append(a)
                around = neighbors[b]
                a, b = b, around[(around.index(a) - 1) % len(around)]
            if len(face) >= 3:
                ox, oy = face[0]
                area = math.fsum((a[0] - ox) * (b[1] - oy) - (b[0] - ox) * (a[1] - oy)
                                 for a, b in zip(face, face[1:] + face[:1]))
                if area > 0:
                    faces.append(tuple(face))
    return faces
