"""Physical one-sided offsets from immutable internal measurement faces (pixels)."""
import math


def validated_wall(value):
    if not isinstance(value, dict) or set(value) != {"width", "side"}:
        raise ValueError("Invalid wall properties")
    width, side = value["width"], value["side"]
    if isinstance(width, bool) or not isinstance(width, (int, float)) or not math.isfinite(width) or not 0 < width <= 10000:
        raise ValueError("Invalid physical wall thickness")
    if type(side) is not int or side not in (-1, 1):
        raise ValueError("Invalid wall side")
    return dict(width=float(width), side=side)


def wall_style(shape):
    """Direction-independent compatibility: reversal must reverse the wall side."""
    wall = shape.get("wall")
    if not wall:
        return None
    if "kind" in shape:
        from survey.plan_curves import curve_info
        direction = 1 if curve_info(shape)[4] > 0 else -1
    else:
        dx, dy = shape["x2"]-shape["x1"], shape["y2"]-shape["y1"]
        length = math.hypot(dx, dy)
        return wall["width"], round(-dy/length*wall["side"], 8), round(dx/length*wall["side"], 8)
    return wall["width"], wall["side"] * direction


def copy_wall(source, target, reversed_direction=False):
    if source.get("wall"):
        target["wall"] = dict(source["wall"], side=source["wall"]["side"] * (-1 if reversed_direction else 1))
    return target
