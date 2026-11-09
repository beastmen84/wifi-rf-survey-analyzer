"""Parametric circles and chord/sagitta arcs; no sampled model coordinates."""
import json
import math
import re
from copy import deepcopy

from survey.plan_mode import is_drawn_plan

PLAN_CURVES_KEY = "plan_curves"
TAU = 2 * math.pi
EPS = 1e-8


def curve_info(curve):
    """Return center, radius, start and signed sweep, in screen radians."""
    if curve["kind"] == "circle":
        return curve["cx"], curve["cy"], curve["radius"], math.radians(curve.get("phase", 0)), TAU
    ax, ay, bx, by, h = (curve[key] for key in ("x1", "y1", "x2", "y2", "height"))
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    if not length or not h:
        raise ValueError("An arc needs distinct endpoints and a nonzero sagitta")
    offset = h / 2 - length * length / (8 * h)
    cx, cy = (ax + bx) / 2 - dy / length * offset, (ay + by) / 2 + dx / length * offset
    radius = length * length / (8 * abs(h)) + abs(h) / 2
    start = math.atan2(ay - cy, ax - cx)
    sweep = -math.copysign(4 * math.atan2(2 * abs(h), length), h)
    return cx, cy, radius, start, sweep


def arc_height_through_point(chord, point):
    """Sagitta of the circular arc through a third point on either chord side."""
    dx, dy = chord["x2"] - chord["x1"], chord["y2"] - chord["y1"]
    length = math.hypot(dx, dy)
    if not length:
        return None
    px, py = point[0] - chord["x1"], point[1] - chord["y1"]
    along, across = (px * dx + py * dy) / length, (py * dx - px * dy) / length
    if abs(across) <= EPS:
        return None  # Fixed endpoints and collinear points cannot set a bend.
    offset = math.fsum((along * (along - length), across * across)) / (2 * across)
    half = length / 2
    radius = math.hypot(half, offset)
    if not math.isfinite(radius) or radius > 1e12:
        return None
    # Avoid cancellation when the center is on the opposite side of the chord.
    height = radius + abs(offset) if offset * across >= 0 else half * half / (radius + abs(offset))
    return math.copysign(height, across)


def validate_curves(curves):
    if not isinstance(curves, list) or len(curves) > 5000:
        raise ValueError("Invalid plan curve list")
    result = []
    for source in curves:
        if not isinstance(source, dict):
            raise ValueError("Invalid curve")
        kind = source.get("kind")
        keys = ("cx", "cy", "radius") if kind == "circle" else ("x1", "y1", "x2", "y2", "height") if kind == "arc" else ()
        if not keys:
            raise ValueError("Unsupported curve")
        curve = dict(kind=kind, **{key: float(source[key]) for key in keys})
        color = str(source["color"])
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color) or any(not math.isfinite(curve[key]) for key in keys):
            raise ValueError("Invalid curve data")
        curve["color"] = color.lower()
        if "wall" in source:
            from survey.wall_properties import validated_wall
            curve["wall"] = validated_wall(source["wall"])
        if kind == "circle":
            phase = float(source.get("phase", 0))
            if not math.isfinite(phase) or not 0 < curve["radius"] <= 100000:
                raise ValueError("Invalid circle radius")
            curve["phase"] = phase % 360
        else:
            if curve["x1"] == curve["x2"] and curve["y1"] == curve["y2"]:
                raise ValueError("Empty arc")
            if not curve["height"]:
                raise ValueError("Zero-height arc")
        cx, cy, radius, start, sweep = curve_info(curve)
        if not all(math.isfinite(v) for v in (cx, cy, radius, start, sweep)) or radius > 1e12:
            raise ValueError("Curve exceeds numerical limits")
        if any(value < -EPS or value > 100000 + EPS for value in curve_bounds(curve)):
            raise ValueError("Curve outside coordinate range")
        result.append(curve)
    return result


def drawing_curves(metadata):
    if not is_drawn_plan(metadata):
        return None
    if PLAN_CURVES_KEY not in metadata:
        return []
    document = json.loads(metadata[PLAN_CURVES_KEY])
    if not isinstance(document, dict) or document.get("version") not in (1, 2):
        raise ValueError("Unsupported curve document")
    return validate_curves(document.get("curves"))


def encode_curves(curves):
    curves = validate_curves(curves)
    return json.dumps(dict(version=2 if any(c.get("wall") for c in curves) else 1, curves=curves), separators=(",", ":"))


def point_at(curve, fraction):
    if curve["kind"] == "circle" and fraction == 1:
        fraction = 0
    if curve["kind"] == "arc" and fraction in (0, 1):
        suffix = "1" if fraction == 0 else "2"
        return curve["x" + suffix], curve["y" + suffix]
    cx, cy, radius, start, sweep = curve_info(curve)
    angle = start + sweep * fraction
    if curve["kind"] == "arc":
        half = sweep * fraction / 2
        distance = 2 * radius * math.sin(half)
        return curve["x1"] - math.sin(start + half) * distance, curve["y1"] + math.cos(start + half) * distance
    return cx + radius * math.cos(angle), cy + radius * math.sin(angle)


def parameter_at(curve, point):
    cx, cy, radius, start, sweep = curve_info(curve)
    if curve["kind"] == "arc":
        if math.dist(point, point_at(curve, 0)) <= EPS:
            return 0.0
        if math.dist(point, point_at(curve, 1)) <= EPS:
            return 1.0
    angle = math.atan2(point[1] - cy, point[0] - cx)
    delta = ((angle - start) if sweep > 0 else (start - angle)) % TAU
    if TAU - delta <= 1e-12:
        delta = 0
    fraction = delta / abs(sweep)
    return min(1.0, fraction) if fraction <= 1 + 1e-10 else None


def curve_points(curve, center=False):
    cx, cy, radius, start, sweep = curve_info(curve)
    points = [point_at(curve, 0), point_at(curve, 1), point_at(curve, .5)]
    for angle in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
        point = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
        fraction = parameter_at(curve, point)
        if fraction is not None:
            points.append(point_at(curve, fraction) if curve["kind"] == "arc" else point)
    if center and curve["kind"] == "circle":
        points.append((cx, cy))
    return list(dict.fromkeys(points))


def curve_bounds(curve):
    points = curve_points(curve)
    return min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)


def curves_geometry(curves):
    result = []
    for curve in curves:
        points = curve_points(curve, center=True)
        result.extend(dict(x1=a[0], y1=a[1], x2=b[0], y2=b[1], color=curve["color"])
                      for a, b in zip(points, points[1:] + points[:1]))
    return result


def project_curve(curve, point):
    cx, cy, radius, _, _ = curve_info(curve)
    dx, dy = point[0] - cx, point[1] - cy
    distance = math.hypot(dx, dy)
    candidate = (cx + radius * dx / distance, cy + radius * dy / distance) if distance else point_at(curve, 0)
    fraction = parameter_at(curve, candidate)
    if fraction is not None:
        if curve["kind"] == "circle":
            return candidate
        # Avoid subtracting huge, nearly equal center/radius coordinates on
        # shallow arcs. Refine along the stable chord-relative parameterization.
        _, _, _, start, sweep = curve_info(curve)
        for _ in range(3):
            q = point_at(curve, fraction)
            angle = start + sweep * fraction
            sine, cosine = math.sin(angle), math.cos(angle)
            ex, ey = q[0] - point[0], q[1] - point[1]
            derivative = sweep * (radius - ex * cosine - ey * sine)
            if abs(derivative) <= EPS:
                break
            fraction = max(0, min(1, fraction - (-ex * sine + ey * cosine) / derivative))
        return min((point_at(curve, fraction), point_at(curve, 0), point_at(curve, 1)),
                   key=lambda p: math.dist(p, point))
    return min((point_at(curve, 0), point_at(curve, 1)), key=lambda p: math.dist(p, point))


def transform_curves(curves, angle=0, pivot=(0, 0), dx=0, dy=0):
    result = deepcopy(curves)
    turns = angle % 360
    cosine, sine = ((1, 0), (0, 1), (-1, 0), (0, -1))[int(turns / 90)] if turns % 90 == 0 else (
        math.cos(math.radians(turns)), math.sin(math.radians(turns)))
    for curve in result:
        keys = (("cx", "cy"),) if curve["kind"] == "circle" else (("x1", "y1"), ("x2", "y2"))
        for xkey, ykey in keys:
            x, y = curve[xkey] - pivot[0], curve[ykey] - pivot[1]
            curve[xkey], curve[ykey] = pivot[0] + x * cosine - y * sine + dx, pivot[1] + x * sine + y * cosine + dy
    return result


def subcurve(curve, low, high, first=None, last=None):
    if low == 0 and high == 1:
        return dict(curve)
    cx, cy, radius, start, sweep = curve_info(curve)
    a, b = first or point_at(curve, low), last or point_at(curve, high)
    span = sweep * (high - low)
    if abs(abs(span) - TAU) < 1e-9:
        from survey.wall_properties import copy_wall
        return copy_wall(curve, dict(kind="circle", cx=cx, cy=cy, radius=radius,
            phase=math.degrees(start + sweep * low) % 360, color=curve["color"]), sweep < 0)
    height = arc_sagitta(a, b, radius, span)
    from survey.wall_properties import copy_wall
    return copy_wall(curve, dict(kind="arc", x1=a[0], y1=a[1], x2=b[0], y2=b[1], height=height, color=curve["color"]))


def arc_sagitta(a, b, radius, sweep):
    """Keep the support radius stable when canonical intersections cut an arc."""
    half = math.dist(a, b) / 2
    root = math.sqrt(max(0, (radius - half) * (radius + half)))
    if abs(abs(sweep) - math.pi) < 1e-12:
        height = radius
    elif abs(sweep) < math.pi:
        height = half * half / (radius + root)
    else:
        height = radius + root
    return -math.copysign(height, sweep)


def sample_curve(curve, tolerance=.05, limit=20000):
    _, _, radius, _, sweep = curve_info(curve)
    # Stable for very shallow arcs, unlike acos(1 - tolerance/radius).
    step = 4 * math.asin(min(1, math.sqrt(tolerance / (2 * radius))))
    count = max(1, math.ceil(abs(sweep) / max(step, 1e-12)))
    if count > limit:
        raise ValueError("Curve display too complex")
    return [point_at(curve, i / count) for i in range(count + 1)]
