"""Click regions with exact areas and source boundaries, including nested holes."""
from dataclasses import dataclass

from PySide6.QtCore import Qt
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
