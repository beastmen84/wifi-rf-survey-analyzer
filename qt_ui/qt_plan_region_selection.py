"""Click regions with exact areas and source boundaries, including nested holes."""
from dataclasses import dataclass
import math

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainterPath

from survey.curved_regions import closed_drawing_regions


@dataclass(frozen=True)
class PickedRegion:
    lines: tuple
    curves: tuple
    area: float


class RegionPicker:
    def __init__(self, lines, curves):
        regions = closed_drawing_regions(lines, curves, with_boundaries=True)
        self.limited = regions.limited or len(regions.faces) > 2000
        self.records = []
        if self.limited:
            return
        paths = []
        for face in regions.faces:
            path = QPainterPath()
            path.setFillRule(Qt.FillRule.WindingFill)
            path.moveTo(*face[0])
            for point in face[1:]:
                path.lineTo(*point)
            path.closeSubpath()
            paths.append(path)
        parents = {}
        for index, inner in enumerate(paths):
            candidates = [outer for outer, path in enumerate(paths) if outer != index
                          and path.boundingRect() != inner.boundingRect()
                          and path.boundingRect().contains(inner.boundingRect()) and path.contains(inner)]
            if candidates:
                parents[index] = min(candidates, key=lambda i: regions.boundaries[i].area)
        for index, (path, boundary) in enumerate(zip(paths, regions.boundaries)):
            shape = QPainterPath(path)
            lines, curves, area = set(boundary.lines), set(boundary.curves), boundary.area
            for child, parent in parents.items():
                if parent == index:
                    shape = shape.subtracted(paths[child])
                    child_boundary = regions.boundaries[child]
                    lines.update(child_boundary.lines)
                    curves.update(child_boundary.curves)
                    area -= child_boundary.area
            if area > 1e-8 and not shape.isEmpty():
                self.records.append((shape, PickedRegion(tuple(sorted(lines)), tuple(sorted(curves)), area)))

    def pick(self, point):
        hits = [region for path, region in self.records if path.contains(point)]
        return min(hits, key=lambda region: region.area) if hits else None

    def matching_area(self, lines, curves):
        lines, curves = tuple(sorted(lines)), tuple(sorted(curves))
        matches = [region.area for _path, region in self.records if region.lines == lines and region.curves == curves]
        return min(matches) if matches else None

    def centers(self):
        """Interior centroids, with an interior fallback for concave/holed rooms."""
        result = []
        for path, _region in self.records:
            polygon = [(p.x(), p.y()) for p in path.toFillPolygon()]
            if len(polygon) < 3:
                continue
            ox, oy = polygon[0]
            local = [(x - ox, y - oy) for x, y in polygon]
            pairs = list(zip(local, local[1:] + local[:1]))
            cross = [a[0] * b[1] - b[0] * a[1] for a, b in pairs]
            area2 = math.fsum(cross)
            box = path.boundingRect()
            center = (box.center().x(), box.center().y())
            if abs(area2) > 1e-10:
                center = (ox + math.fsum((a[0] + b[0]) * c for (a, b), c in zip(pairs, cross)) / (3 * area2),
                          oy + math.fsum((a[1] + b[1]) * c for (a, b), c in zip(pairs, cross)) / (3 * area2))
            if path.contains(QPointF(*center)):
                result.append(center)
                continue
            # A centroid inside a courtyard or outside a concave L is not a
            # useful snap point. Pick the nearest central interior scan span.
            candidates = []
            levels = [center[1]] + [box.top() + box.height() * t for t in (.25, .5, .75)]
            edges = list(zip(polygon, polygon[1:] + polygon[:1]))
            for y in levels:
                xs = sorted(a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]) for a, b in edges
                            if (a[1] <= y < b[1]) or (b[1] <= y < a[1]))
                for left, right in zip(xs, xs[1:]):
                    point = ((left + right) / 2, y)
                    if right - left > 1e-8 and path.contains(QPointF(*point)):
                        candidates.append((math.dist(point, center), -(right - left), point))
            if candidates:
                result.append(min(candidates)[2])
        return result
