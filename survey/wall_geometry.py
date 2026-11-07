"""One-sided physical wall solids and aperture cuts, independent of room topology."""
import math
from collections import defaultdict

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen

from survey.plan_curves import curve_info, point_at
from survey.plan_curve_rendering import curve_path

EPS = 1e-6
MAX_WALLS = 2000


def polygon(points):
    result = QPainterPath()
    if points:
        result.moveTo(*points[0])
        for point in points[1:]:
            result.lineTo(*point)
        result.closeSubpath()
    return result


def united(paths):
    paths = [p for p in paths if not p.isEmpty()]
    while len(paths) > 1:
        paths = [paths[i].united(paths[i+1]) if i+1 < len(paths) else paths[i] for i in range(0, len(paths), 2)]
    return paths[0] if paths else QPainterPath()


def normal(line, side=1):
    dx, dy = line["x2"]-line["x1"], line["y2"]-line["y1"]
    length = math.hypot(dx, dy)
    return -dy/length*side, dx/length*side


def offset_curve(curve, width):
    """Stable cubic offset even when shallow-arc centers are very distant."""
    _cx, _cy, radius, start, sweep = curve_info(curve)
    outer = radius - curve["wall"]["side"] * math.copysign(width, sweep)
    if outer <= EPS:
        raise ValueError("wall_radius_conflict")
    delta = outer-radius
    def p(t):
        a = start+sweep*t
        q = point_at(curve, t)
        return q[0]+delta*math.cos(a), q[1]+delta*math.sin(a)
    path = QPainterPath()
    path.moveTo(*p(0))
    count = max(1, math.ceil(abs(sweep)/(math.pi/4)))
    for i in range(count):
        a, b = start+sweep*i/count, start+sweep*(i+1)/count
        first, last = p(i/count), p((i+1)/count)
        factor = outer*4/3*math.tan((b-a)/4)
        path.cubicTo(first[0]-math.sin(a)*factor, first[1]+math.cos(a)*factor,
                     last[0]+math.sin(b)*factor, last[1]-math.cos(b)*factor, *last)
    if curve["kind"] == "circle":
        path.closeSubpath()
    return path


def solid(shape):
    wall = shape.get("wall")
    if not wall:
        return QPainterPath()
    width = wall["width"]
    if "kind" not in shape:
        nx, ny = normal(shape, wall["side"])
        a, b = (shape["x1"], shape["y1"]), (shape["x2"], shape["y2"])
        return polygon([a, b, (b[0]+nx*width, b[1]+ny*width), (a[0]+nx*width, a[1]+ny*width)])
    inner, outer = curve_path(shape), offset_curve(shape, width)
    if shape["kind"] == "circle":
        inner.addPath(outer)
        inner.setFillRule(Qt.FillRule.OddEvenFill)
        return inner
    inner.connectPath(outer.toReversed())
    inner.closeSubpath()
    return inner


def endpoint_data(shape):
    wall = shape["wall"]
    if "kind" not in shape:
        n = normal(shape, wall["side"])
        return [((shape["x1"], shape["y1"]), n), ((shape["x2"], shape["y2"]), n)]
    if shape["kind"] == "circle":
        return []
    _cx, _cy, _r, start, sweep = curve_info(shape)
    sign = -wall["side"]*math.copysign(1, sweep)
    return [(point_at(shape, t), (math.cos(start+sweep*t)*sign, math.sin(start+sweep*t)*sign)) for t in (0, 1)]


def aperture_channels(lines, annotations):
    """Cut the complete physical depth, including an opposite shared wall face."""
    channels = []
    for item in annotations:
        if item["kind"] not in ("door", "window"):
            continue
        dx, dy = item["x2"]-item["x1"], item["y2"]-item["y1"]
        length = math.hypot(dx, dy)
        ux, uy, nx, ny = dx/length, dy/length, -dy/length, dx/length
        offsets = [0.0]
        for line in lines:
            if not line.get("wall"):
                continue
            vx, vy = line["x2"]-line["x1"], line["y2"]-line["y1"]
            if abs(vx*uy-vy*ux) > EPS*math.hypot(vx, vy):
                continue
            off = (line["x1"]-item["x1"])*nx+(line["y1"]-item["y1"])*ny
            along = sorted((line["x"+s]-item["x1"])*ux+(line["y"+s]-item["y1"])*uy for s in ("1", "2"))
            if abs(off) > EPS or along[1] < -EPS or along[0] > length+EPS:
                continue
            wx, wy = normal(line, line["wall"]["side"])
            offsets.append((wx*nx+wy*ny)*line["wall"]["width"])
        if len(offsets) == 1:
            continue
        low, high = min(offsets)-EPS, max(offsets)+EPS
        points = [(item["x1"]+ux*t+nx*d, item["y1"]+uy*t+ny*d)
                  for t, d in ((0, low), (length, low), (length, high), (0, high))]
        channels.append(polygon(points))
    return channels


def wall_solids(lines, curves=(), annotations=()):
    shapes = [s for s in [*lines, *curves] if s.get("wall")]
    if len(shapes) > MAX_WALLS:
        raise ValueError("wall_complexity")
    groups, endpoints = defaultdict(list), defaultdict(list)
    for shape in shapes:
        groups[shape["color"]].append(solid(shape))
        for point, n in endpoint_data(shape):
            endpoints[tuple(round(v, 6) for v in point)].append((point, n, shape))
    for incident in endpoints.values():
        if len(incident) > 12:
            raise ValueError("wall_complexity")
        for i, (p, n, first) in enumerate(incident):
            for q, m, second in incident[i+1:]:
                determinant = n[0]*m[1]-n[1]*m[0]
                if abs(determinant) < 1e-8:
                    continue
                a, b = first["wall"]["width"], second["wall"]["width"]
                # Intersection of the two physical offset faces.
                vx, vy = (a*m[1]-b*n[1])/determinant, (n[0]*b-m[0]*a)/determinant
                # Acute joins use a bevel instead of an unbounded miter spike.
                points = [p, (p[0]+n[0]*a, p[1]+n[1]*a)]
                if math.hypot(vx, vy) <= 4*max(a, b):
                    points.append((p[0]+vx, p[1]+vy))
                points.append((q[0]+m[0]*b, q[1]+m[1]*b))
                groups[first["color"]].append(polygon(points))
    cuts = united(aperture_channels(lines, annotations))
    return [(color, united(paths).subtracted(cuts)) for color, paths in groups.items()]


def wall_commands(lines, curves=(), annotations=()):
    return [(path, QPen(QColor(color), 1), QBrush(QColor("#d1d5db")))
            for color, path in wall_solids(lines, curves, annotations) if not path.isEmpty()]


def validate_wall_bounds(lines, curves, bounds):
    for _color, path in wall_solids(lines, curves):
        if not bounds.adjusted(-EPS, -EPS, EPS, EPS).contains(path.boundingRect()):
            raise ValueError("wall_outside")


def path_area(path):
    # Integrate filled scan spans rather than summing contour magnitudes: Qt
    # booleans can retain coincident opposite contours and odd-even holes.
    edges = []
    for poly in path.toSubpathPolygons():
        points = [(p.x(), p.y()) for p in poly]
        edges.extend((a, b) for a, b in zip(points, points[1:]+points[:1]) if a[1] != b[1])
    levels = sorted({p[1] for edge in edges for p in edge})
    area = 0.0
    for low, high in zip(levels, levels[1:]):
        y = (low+high)/2
        crossings = sorted((a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]), 1 if b[1] > a[1] else -1)
                           for a, b in edges if min(a[1], b[1]) < y < max(a[1], b[1]))
        winding, start = 0, 0
        for x, sign in crossings:
            before = winding % 2 != 0 if path.fillRule() == Qt.FillRule.OddEvenFill else winding != 0
            winding += sign
            after = winding % 2 != 0 if path.fillRule() == Qt.FillRule.OddEvenFill else winding != 0
            if not before and after:
                start = x
            elif before and not after:
                area += (x-start)*(high-low)
    return area


def hit_solid(shape, x, y):
    return shape.get("wall") and solid(shape).contains(QPointF(x, y))


def box_hits_solid(shape, left, top, right, bottom):
    return shape.get("wall") and solid(shape).intersects(QRectF(left, top, right-left, bottom-top))


def projected_apertures(lines, apertures):
    channels = aperture_channels(lines, apertures)
    extra = []
    if not channels:
        return extra
    cut = united(channels)
    for item in apertures:
        dx, dy = item["x2"]-item["x1"], item["y2"]-item["y1"]
        length = math.hypot(dx, dy)
        nx, ny = -dy/length, dx/length
        for line in lines:
            vx, vy = line["x2"]-line["x1"], line["y2"]-line["y1"]
            if abs(vx*dy-vy*dx) > EPS*length*math.hypot(vx, vy):
                continue
            off = (line["x1"]-item["x1"])*nx+(line["y1"]-item["y1"])*ny
            mid = QPointF((item["x1"]+item["x2"])/2+nx*off, (item["y1"]+item["y2"])/2+ny*off)
            if abs(off) > EPS and cut.contains(mid):
                extra.append(dict(item, x1=item["x1"]+nx*off, y1=item["y1"]+ny*off,
                                  x2=item["x2"]+nx*off, y2=item["y2"]+ny*off))
    return extra
