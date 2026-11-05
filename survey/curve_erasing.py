"""Hit tests on finite curves, never on a circle's empty bounding box."""
import math

from survey.plan_curves import point_at, project_curve
from survey.plan_curve_geometry import line_curve_intersections


def nearest_curve(curves, x, y, tolerance):
    choices = [(math.dist((x, y), project_curve(curve, (x, y))), -index)
               for index, curve in enumerate(curves)]
    if not choices:
        return None
    distance, negative = min(choices)
    return -negative if distance <= tolerance else None


def intersecting_curves(curves, left, top, right, bottom):
    def inside(p):
        return left <= p[0] <= right and top <= p[1] <= bottom
    corners = [(left, top), (right, top), (right, bottom), (left, bottom)]
    sides = [dict(x1=a[0], y1=a[1], x2=b[0], y2=b[1]) for a, b in zip(corners, corners[1:] + corners[:1]) if a != b]
    return tuple(index for index, curve in enumerate(curves)
                 if inside(point_at(curve, 0)) or inside(point_at(curve, 1))
                 or any(line_curve_intersections(side, curve) for side in sides))
