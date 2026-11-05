"""Closed faces from analytic junctions and tangents; sampling is display only."""
from collections import defaultdict, Counter
import math

from survey.plan_curve_geometry import normalize_plan
from survey.plan_curves import curve_info, point_at, sample_curve
from survey.plan_regions import PlanRegions, RegionBoundary, closed_plan_regions
from survey.planar_geometry import PointRegistry


def closed_drawing_regions(lines, curves=(), *, with_boundaries=False):
    if not curves and not with_boundaries:
        return closed_plan_regions(lines)
    try:
        lines, curves, line_sources, curve_sources = normalize_plan(lines, list(curves), with_sources=True)
        canonical = PointRegistry().add
        edges, seen, nodes, owners = [], {}, defaultdict(list), []
        points_count = 0
        for source_index, shape in enumerate(list(lines) + list(curves)):
            sources = ({("line", i) for i in line_sources[source_index]} if source_index < len(lines)
                       else {("curve", i) for i in curve_sources[source_index - len(lines)]})
            extra = 0
            if "kind" in shape:
                cx, cy, radius, start, sweep = curve_info(shape)
                a, b = canonical(point_at(shape, 0)), canonical(point_at(shape, 1))
                points = sample_curve(shape)
                # Distinguish complementary arcs with the same endpoints.
                midpoint = canonical(point_at(shape, .5))
                key = ("curve", tuple(sorted((a, b))), midpoint)
                if shape["kind"] == "circle":
                    key = ("circle", canonical((cx, cy)), canonical((cx + radius, cy)))
                first = start + math.copysign(math.pi / 2, sweep)
                last = start + sweep - math.copysign(math.pi / 2, sweep)
                square = sweep * sweep
                delta = (sweep * square * (1 / 6 - square / 120 + square * square / 5040)
                         if abs(sweep) < .001 else sweep - math.sin(sweep))
                extra = radius * radius * delta
            else:
                a = canonical((shape["x1"], shape["y1"]))
                b = canonical((shape["x2"], shape["y2"]))
                points = [a, b]
                key = ("line", tuple(sorted((a, b))))
                first, last = math.atan2(b[1] - a[1], b[0] - a[0]), math.atan2(a[1] - b[1], a[0] - b[0])
            if key in seen:
                owners[seen[key] // 2].update(sources)
                continue
            points[0], points[-1] = a, b
            points_count += len(points)
            if points_count > 200000:
                raise ValueError("Closed curved region display limit")
            index = len(edges)
            seen[key] = index
            owners.append(sources)
            edges.extend([(a, b, points, extra), (b, a, list(reversed(points)), -extra)])
            # Tiny same-direction curvature tie break puts a tangent junction
            # in the same angular order as its true outgoing branches.
            bend = math.copysign(1 / radius, sweep) if "kind" in shape else 0
            nodes[a].append((first % math.tau, bend, index))
            nodes[b].append((last % math.tau, -bend, index + 1))
        neighbors, positions = {}, {}
        for node, values in nodes.items():
            # Equal mathematical tangents may differ by a few float ulps.
            # Canonicalize only their derived angular order, including wrap.
            angles = sorted((0 if angle < 1e-12 or math.tau - angle < 1e-12 else angle, bend, index)
                            for angle, bend, index in values)
            groups = []
            for angle, bend, index in angles:
                if not groups or angle - groups[-1][0] > 1e-12:
                    groups.append((angle, []))
                groups[-1][1].append((bend, index))
            order = [index for _, group in groups for _bend, index in sorted(group)]
            neighbors[node] = order
            positions.update({index: position for position, index in enumerate(order)})
        visited, faces, boundaries = set(), [], []
        for start in range(len(edges)):
            if start in visited:
                continue
            current, polygon, walk = start, [], []
            while current not in visited:
                visited.add(current)
                walk.append(current)
                _a, b, points, _extra = edges[current]
                polygon.extend(points[:-1])
                outgoing = neighbors[b]
                current = outgoing[(positions[current ^ 1] - 1) % len(outgoing)]
            if current == start and len(polygon) >= 3:
                ox, oy = edges[start][0]
                area = math.fsum((a[0] - ox) * (b[1] - oy) - (b[0] - ox) * (a[1] - oy) + extra
                                 for a, b, _points, extra in (edges[i] for i in walk)) / 2
                if area > 1e-8:
                    faces.append(tuple(polygon))
                    counts = Counter(i // 2 for i in walk)
                    source_set = set().union(*(owners[i] for i, count in counts.items() if count == 1))
                    boundaries.append(RegionBoundary(frozenset(i for kind, i in source_set if kind == "line"),
                        frozenset(i for kind, i in source_set if kind == "curve"), area))
        return PlanRegions(tuple(faces), boundaries=tuple(boundaries) if with_boundaries else ())
    except (ValueError, OverflowError):
        return PlanRegions(limited=True)
