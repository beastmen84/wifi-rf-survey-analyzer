"""Deterministic grid/segment snapping in plan coordinates, independent of Qt."""
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
import math
from survey.planar_geometry import point_projection
from survey.plan_geometry import segment_bounds
from survey.plan_curves import curve_points, project_curve, arc_height_through_point, curve_bounds
from survey.plan_curve_geometry import line_curve_intersections


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


def snap_vertices_to_grid(vertices, box, bounds, spacing):
    """Translate rigidly by the smallest valid correction of any real vertex."""
    choices = []
    for vx, vy in vertices:
        gx = nearest_grid(vx, bounds[0] + vx - box[0], bounds[2] + vx - box[2], spacing)
        gy = nearest_grid(vy, bounds[1] + vy - box[1], bounds[3] + vy - box[3], spacing)
        if gx is not None and gy is not None:
            dx, dy = gx - vx, gy - vy
            choices.append((dx * dx + dy * dy, dx, dy, gx, gy))
    if not choices:
        return None
    _, dx, dy, gx, gy = min(choices)
    return SnapResult(dx, dy, (SnapGuide("grid", (gx, gy)),))


class PlanSnapper:
    def __init__(self, segments=(), curves=(), region_centers=()):
        self.segments = list(segments)
        self.curves = list(curves)
        self.oblique = [line for line in self.segments if line["x1"] != line["x2"] and line["y1"] != line["y2"]]
        self.vertical, self.horizontal, vertices = [], [], set()
        for line in self.segments:
            x1, y1, x2, y2 = (line[key] for key in ("x1", "y1", "x2", "y2"))
            vertices.update(((x1, y1), (x2, y2)))
            if x1 == x2:
                self.vertical.append((x1, min(y1, y2), max(y1, y2)))
            elif y1 == y2:
                self.horizontal.append((y1, min(x1, x2), max(x1, x2)))
        self.vertical = sorted(set(self.vertical))
        self.horizontal = sorted(set(self.horizontal))
        vertices.update(point for curve in self.curves for point in curve_points(curve, center=True))
        self.vertices = sorted(vertices)
        self.v_positions = [line[0] for line in self.vertical]
        self.h_positions = [line[0] for line in self.horizontal]
        self.vertex_x = [point[0] for point in self.vertices]
        self.midpoints = sorted({((s["x1"] + s["x2"]) / 2, (s["y1"] + s["y2"]) / 2) for s in self.segments})
        self.region_centers = region_centers
        self._centers = None

    def target_groups(self):
        yield "corner", self.vertices, self.vertex_x
        yield "midpoint", self.midpoints, [p[0] for p in self.midpoints]
        if self._centers is None:
            self._centers = sorted(set(self.region_centers() if callable(self.region_centers) else self.region_centers))
        yield "area_center", self._centers, [p[0] for p in self._centers]

    def point_snap(self, vertices, box, bounds, tolerance):
        """Corners, segment midpoints, then interior room centers; no grid."""
        for kind, targets, xs in self.target_groups():
            choices = []
            for vx, vy in vertices:
                for tx, ty in self.nearby(targets, xs, vx, tolerance):
                    dx, dy = tx - vx, ty - vy
                    distance = dx * dx + dy * dy
                    if (distance <= tolerance ** 2 and bounds[0] <= box[0] + dx and bounds[1] <= box[1] + dy
                            and box[2] + dx <= bounds[2] and box[3] + dy <= bounds[3]):
                        choices.append((distance, dx, dy, tx, ty))
            if choices:
                _, dx, dy, tx, ty = min(choices)
                return SnapResult(dx, dy, (SnapGuide(kind, (tx, ty)),))
        return None

    @staticmethod
    def nearby(values, positions, coordinate, tolerance):
        return values[bisect_left(positions, coordinate - tolerance):bisect_right(positions, coordinate + tolerance)]

    def snap(self, x, y, width, height, bounds, tolerance, grid=None, *, source_vertices=None):
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
        original_x, original_y = x, y
        x, y = min(max(x, left), max_x), min(max(y, top), max_y)
        x_offsets = (0,) if width == 0 else (0, width)
        y_offsets = (0,) if height == 0 else (0, height)
        vertices = ([(x + dx, y + dy) for dx in x_offsets for dy in y_offsets]
                    if source_vertices is None else
                    sorted({(vx + (x - original_x), vy + (y - original_y)) for vx, vy in source_vertices}))
        if any(not math.isfinite(value) for point in vertices for value in point):
            raise ValueError("Invalid snapping vertices")

        if width or height:
            vertices.append((x + width / 2, y + height / 2))
        point = self.point_snap(vertices, (x, y, x + width, y + height), bounds, tolerance)
        if point is not None:
            return SnapResult(x + point.x, y + point.y, point.guides)

        diagonal = self.edge_translation(vertices, self.oblique,
                                          (x, y, x + width, y + height), bounds, tolerance)
        if diagonal is not None:
            dx, dy, guide = diagonal
            return SnapResult(x + dx, y + dy, (guide,))
        curved = self.curve_translation(vertices, (x, y, x + width, y + height), bounds, tolerance)
        if curved is not None:
            dx, dy, guide = curved
            return SnapResult(x + dx, y + dy, (guide,))

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
        if grid and grid > 0 and xt.kind != "edge" and yt.kind != "edge":
            snapped = snap_vertices_to_grid(vertices, (x, y, x + width, y + height), bounds, grid)
            return (SnapResult(x + snapped.x, y + snapped.y, snapped.guides)
                    if snapped is not None else SnapResult(x, y))
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

    def snap_drag(self, x, y, origin, bounds, tolerance, grid=None):
        """Resize about a fixed origin, aligning the full draft's moving sides.

        A side may align with a finite target that intersects the draft's span,
        even when the pointer itself is beyond that segment. Unrelated distant
        projections are excluded. Numeric placement continues to use snap().
        """
        direct = self.snap(x, y, 0, 0, bounds, tolerance)
        left, top, right, bottom = bounds
        ox, oy = origin
        if not all(math.isfinite(value) for value in origin) or not (left <= ox <= right and top <= oy <= bottom):
            raise ValueError("Invalid drag origin")
        if any(guide.kind in ("corner", "midpoint", "area_center") or guide.axis in ("line", "curve") for guide in direct.guides):
            return direct
        x, y = min(max(x, left), right), min(max(y, top), bottom)
        xs = self.axis_targets(x, min(oy, y), abs(y - oy), (0,), self.vertical, self.v_positions,
                               left, right, tolerance, grid)
        ys = self.axis_targets(y, min(ox, x), abs(x - ox), (0,), self.horizontal, self.h_positions,
                               top, bottom, tolerance, grid)
        choices = []
        for xt in xs:
            for yt in ys:
                if xt.kind == "edge" and not overlap(min(oy, yt.value), abs(yt.value - oy), xt.span):
                    continue
                if yt.kind == "edge" and not overlap(min(ox, xt.value), abs(xt.value - ox), yt.span):
                    continue
                score = (-((xt.kind == "edge") + (yt.kind == "edge")),
                         -((xt.kind == "grid") + (yt.kind == "grid")),
                         (xt.value - x) ** 2 + (yt.value - y) ** 2, xt.value, yt.value)
                choices.append((score, xt, yt))
        _, xt, yt = min(choices, key=lambda choice: choice[0])
        guides = []
        for target, other, fixed, axis in ((xt, yt.value, oy, "x"), (yt, xt.value, ox, "y")):
            if target.kind == "edge":
                start, end = sorted((other, fixed))
                projection = (max(start, target.span[0]) + min(end, target.span[1])) / 2
                point = (target.coordinate, projection) if axis == "x" else (projection, target.coordinate)
                kind = "edge" if target.span[0] <= other <= target.span[1] else "alignment"
                guides.append(SnapGuide(kind, point, axis, target.span))
        if xt.kind == "grid" or yt.kind == "grid":
            guides.append(SnapGuide("grid", (xt.value, yt.value)))
        return SnapResult(xt.value, yt.value, tuple(guides))

    def snap_line(self, x, y, origin, horizontal, bounds, tolerance, grid=None):
        """Snap the moving endpoint on one axis, retaining the fixed line axis."""
        value, fixed = (x, origin[1]) if horizontal else (y, origin[0])
        minimum, maximum = (bounds[0], bounds[2]) if horizontal else (bounds[1], bounds[3])
        value = min(max(value, minimum), maximum)
        for kind, points, _xs in self.target_groups():
            vertices = [(vx if horizontal else vy) for vx, vy in points
                        if abs((vy if horizontal else vx) - fixed) <= 1e-9
                        and abs((vx if horizontal else vy) - value) <= tolerance]
            if vertices:
                chosen = min(vertices, key=lambda coordinate: (abs(coordinate - value), coordinate))
                point = (chosen, fixed) if horizontal else (fixed, chosen)
                return SnapResult(*point, (SnapGuide(kind, point),))
        side = dict(x1=minimum if horizontal else fixed, y1=fixed if horizontal else minimum,
                    x2=maximum if horizontal else fixed, y2=fixed if horizontal else maximum)
        points = [point for curve in self.curves for point in line_curve_intersections(side, curve)
                  if abs((point[0] if horizontal else point[1]) - value) <= tolerance]
        if points:
            chosen = min(points, key=lambda p: (abs((p[0] if horizontal else p[1]) - value), p))
            return SnapResult(*chosen, (SnapGuide("edge", chosen, "curve"),))
        lines, positions = (self.vertical, self.v_positions) if horizontal else (self.horizontal, self.h_positions)
        targets = self.axis_targets(value, fixed, 0, (0,), lines, positions, minimum, maximum, tolerance, grid)
        for line in self.oblique:
            a, b = (line["x1"], line["y1"]), (line["x2"], line["y2"])
            fixed_axis = 1 if horizontal else 0
            low, high = sorted((a[fixed_axis], b[fixed_axis]))
            if low <= fixed <= high:
                t = (fixed - a[fixed_axis]) / (b[fixed_axis] - a[fixed_axis])
                candidate = a[1 - fixed_axis] + t * (b[1 - fixed_axis] - a[1 - fixed_axis])
                if minimum <= candidate <= maximum and abs(candidate - value) <= tolerance:
                    targets.append(AxisTarget(candidate, "edge", candidate, (*a, *b)))
        target = min(targets, key=lambda entry: (0 if entry.kind == "edge" else 1 if entry.kind == "grid" else 2,
                                                abs(entry.value - value), entry.value))
        point = (target.value, fixed) if horizontal else (fixed, target.value)
        guide = () if not target.kind else (SnapGuide(target.kind, point, "x" if horizontal else "y", target.span),)
        if len(target.span) == 4:
            guide = (SnapGuide("edge", point, "line", target.span),)
        return SnapResult(*point, guide)

    def snap_arc_height(self, chord, x, y, bounds, tolerance, grid=None):
        """Bend through a real corner first, then a grid point; keep A/B fixed."""
        for kind, points, xs in self.target_groups():
            choices = []
            for vx, vy in self.nearby(points, xs, x, tolerance):
                distance = (vx - x) ** 2 + (vy - y) ** 2
                if distance > tolerance ** 2:
                    continue
                height = arc_height_through_point(chord, (vx, vy))
                if height is None:
                    continue
                left, top, right, bottom = curve_bounds(dict(chord, height=height))
                if (left >= bounds[0] - 1e-7 and top >= bounds[1] - 1e-7
                        and right <= bounds[2] + 1e-7 and bottom <= bounds[3] + 1e-7):
                    choices.append((distance, vx, vy, height))
            if choices:
                _, vx, vy, height = min(choices)
                return height, SnapGuide(kind, (vx, vy))
        if not grid or grid <= 0:
            return None
        vx = nearest_grid(x, bounds[0], bounds[2], grid)
        vy = nearest_grid(y, bounds[1], bounds[3], grid)
        if vx is None or vy is None:
            return None
        height = arc_height_through_point(chord, (vx, vy))
        if height is None:
            a, b = (chord["x1"], chord["y1"]), (chord["x2"], chord["y2"])
            if math.dist((vx, vy), point_projection((vx, vy), a, b)) <= 1e-8:
                return 0, SnapGuide("grid", (vx, vy))
            return None
        left, top, right, bottom = curve_bounds(dict(chord, height=height))
        if (left >= bounds[0] - 1e-7 and top >= bounds[1] - 1e-7
                and right <= bounds[2] + 1e-7 and bottom <= bounds[3] + 1e-7):
            return height, SnapGuide("grid", (vx, vy))
        return None

    @staticmethod
    def edge_translation(vertices, targets, box, bounds, tolerance):
        choices = []
        for point in vertices:
            for line in targets:
                if (point[0] < min(line["x1"], line["x2"]) - tolerance
                        or point[0] > max(line["x1"], line["x2"]) + tolerance
                        or point[1] < min(line["y1"], line["y2"]) - tolerance
                        or point[1] > max(line["y1"], line["y2"]) + tolerance):
                    continue
                a, b = (line["x1"], line["y1"]), (line["x2"], line["y2"])
                px, py = point_projection(point, a, b)
                dx, dy = px - point[0], py - point[1]
                distance = dx * dx + dy * dy
                if (distance <= tolerance ** 2 and bounds[0] <= box[0] + dx
                        and bounds[1] <= box[1] + dy and box[2] + dx <= bounds[2] and box[3] + dy <= bounds[3]):
                    choices.append((distance, dx, dy, px, py, a, b))
        if not choices:
            return None
        _, dx, dy, px, py, a, b = min(choices)
        return dx, dy, SnapGuide("edge", (px, py), "line", (*a, *b))

    def snap_geometry(self, segments, bounds, tolerance, grid=None, centers=None):
        """Rigidly snap real vertices of an angled shape, preserving its angle."""
        box = segment_bounds(segments)
        vertices = sorted({(line[x], line[y]) for line in segments for x, y in (("x1", "y1"), ("x2", "y2"))})
        vertices.extend(centers if centers is not None else [((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)])
        point = self.point_snap(vertices, box, bounds, tolerance)
        if point is not None:
            return point
        edge = self.edge_translation(vertices, self.segments, box, bounds, tolerance)
        if edge:
            dx, dy, guide = edge
            return SnapResult(dx, dy, (guide,))
        curved = self.curve_translation(vertices, box, bounds, tolerance)
        if curved:
            dx, dy, guide = curved
            return SnapResult(dx, dy, (guide,))
        if grid and grid > 0:
            snapped = snap_vertices_to_grid(vertices, box, bounds, grid)
            if snapped is not None:
                return snapped
        return SnapResult(0, 0)

    def curve_translation(self, vertices, box, bounds, tolerance):
        choices = []
        for vx, vy in vertices:
            for curve in self.curves:
                px, py = project_curve(curve, (vx, vy))
                dx, dy = px - vx, py - vy
                distance = dx * dx + dy * dy
                if (distance <= tolerance ** 2 and bounds[0] <= box[0] + dx and bounds[1] <= box[1] + dy
                        and box[2] + dx <= bounds[2] and box[3] + dy <= bounds[3]):
                    choices.append((distance, dx, dy, px, py))
        if not choices:
            return None
        _, dx, dy, px, py = min(choices)
        return dx, dy, SnapGuide("edge", (px, py), "curve")
