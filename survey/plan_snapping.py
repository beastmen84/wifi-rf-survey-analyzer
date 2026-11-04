"""Deterministic grid/segment snapping in plan coordinates, independent of Qt."""
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SnapGuide:
    kind: str
    point: tuple
    axis: str = "xy"
    span: tuple = ()


@dataclass(frozen=True)
class SnapResult:
    x: float
    y: float
    guides: tuple = ()


@dataclass(frozen=True)
class AxisTarget:
    value: float
    kind: str = ""
    coordinate: float = 0
    span: tuple = ()


def overlap(start, extent, span):
    return start <= span[1] + 1e-9 and start + extent >= span[0] - 1e-9


def nearest_grid(value, minimum, maximum, spacing):
    first, last = math.ceil(minimum / spacing - 1e-10), math.floor(maximum / spacing + 1e-10)
    if first > last:
        return None
    index = min(max(math.floor(value / spacing + .5), first), last)
    return min(max(index * spacing, minimum), maximum)


class PlanSnapper:
    def __init__(self, segments=()):
        self.vertical, self.horizontal, vertices = [], [], set()
        for line in segments:
            x1, y1, x2, y2 = (line[key] for key in ("x1", "y1", "x2", "y2"))
            vertices.update(((x1, y1), (x2, y2)))
            if x1 == x2:
                self.vertical.append((x1, min(y1, y2), max(y1, y2)))
            elif y1 == y2:
                self.horizontal.append((y1, min(x1, x2), max(x1, x2)))
        self.vertical = sorted(set(self.vertical))
        self.horizontal = sorted(set(self.horizontal))
        self.vertices = sorted(vertices)
        self.v_positions = [line[0] for line in self.vertical]
        self.h_positions = [line[0] for line in self.horizontal]
        self.vertex_x = [point[0] for point in self.vertices]

    @staticmethod
    def nearby(values, positions, coordinate, tolerance):
        return values[bisect_left(positions, coordinate - tolerance):bisect_right(positions, coordinate + tolerance)]

    def snap(self, x, y, width, height, bounds, tolerance, grid=None):
        """Translate an anchor; zero width/height means a drag point.

        Existing corners take precedence, then valid edge alignments, then grid.
        All rectangle translations retain the exact supplied dimensions.
        """
        left, top, right, bottom = bounds
        if not all(math.isfinite(value) for value in (x, y, width, height, tolerance, *bounds)) or tolerance < 0:
            raise ValueError("Invalid snapping coordinates")
        max_x, max_y = right - width, bottom - height
        if min(width, height) < 0 or max_x < left or max_y < top:
            raise ValueError("Snapping rectangle does not fit the sheet")
        x, y = min(max(x, left), max_x), min(max(y, top), max_y)
        x_offsets = (0,) if width == 0 else (0, width)
        y_offsets = (0,) if height == 0 else (0, height)

        corners = []
        for dx in x_offsets:
            for dy in y_offsets:
                for vx, vy in self.nearby(self.vertices, self.vertex_x, x + dx, tolerance):
                    distance = (vx - x - dx) ** 2 + (vy - y - dy) ** 2
                    anchor_x, anchor_y = vx - dx, vy - dy
                    if (distance <= tolerance ** 2 and left <= anchor_x <= max_x
                            and top <= anchor_y <= max_y):
                        corners.append((distance, anchor_x, anchor_y, vx, vy))
        if corners:
            _, anchor_x, anchor_y, vx, vy = min(corners)
            return SnapResult(anchor_x, anchor_y, (SnapGuide("corner", (vx, vy)),))

        xs = self.axis_targets(x, y, height, x_offsets, self.vertical, self.v_positions,
                               left, max_x, tolerance, grid)
        ys = self.axis_targets(y, x, width, y_offsets, self.horizontal, self.h_positions,
                               top, max_y, tolerance, grid)
        choices = []
        for xt in xs:
            for yt in ys:
                if xt.kind == "edge" and not overlap(yt.value, height, xt.span):
                    continue
                if yt.kind == "edge" and not overlap(xt.value, width, yt.span):
                    continue
                edge_count = (xt.kind == "edge") + (yt.kind == "edge")
                grid_count = (xt.kind == "grid") + (yt.kind == "grid")
                score = (-edge_count, -grid_count, (xt.value - x) ** 2 + (yt.value - y) ** 2,
                         xt.value, yt.value)
                choices.append((score, xt, yt))
        _, xt, yt = min(choices, key=lambda choice: choice[0])
        guides = []
        for target, other, extent, axis in ((xt, yt.value, height, "x"), (yt, xt.value, width, "y")):
            if target.kind == "edge":
                projection = (max(other, target.span[0]) + min(other + extent, target.span[1])) / 2
                point = (target.coordinate, projection) if axis == "x" else (projection, target.coordinate)
                guides.append(SnapGuide("edge", point, axis, target.span))
        if xt.kind == "grid" or yt.kind == "grid":
            guides.append(SnapGuide("grid", (xt.value, yt.value)))
        return SnapResult(xt.value, yt.value, tuple(guides))

    def axis_targets(self, value, other, extent, offsets, lines, positions, minimum, maximum, tolerance, grid):
        edges = set()
        for offset in offsets:
            for coordinate, start, end in self.nearby(lines, positions, value + offset, tolerance):
                anchor = coordinate - offset
                if minimum <= anchor <= maximum and overlap(other, extent, (start, end)):
                    edges.add(AxisTarget(anchor, "edge", coordinate, (start, end)))
        # Bound the pair search even when many nearby walls overlap.
        targets = sorted(edges, key=lambda target: (abs(target.value - value), target.value, target.span, target.coordinate))[:8]
        targets.append(AxisTarget(value))
        if grid and grid > 0:
            snapped = nearest_grid(value, minimum, maximum, grid)
            if snapped is not None:
                targets.append(AxisTarget(snapped, "grid"))
        return targets
