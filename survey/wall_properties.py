"""Validated physical profiles on internal faces or explicit reference axes."""
import math
from survey.wall_materials import validated_appearance, appearance


def validated_wall(value):
    if not isinstance(value, dict) or not {"width", "side"} <= set(value) <= {"width", "side", "reference", "material", "pattern", "priority"}:
        raise ValueError("Invalid wall properties")
    width, side = value["width"], value["side"]
    if isinstance(width, bool) or not isinstance(width, (int, float)) or not math.isfinite(width) or not 0 < width <= 10000:
        raise ValueError("Invalid physical wall thickness")
    reference = value.get("reference")
    if reference not in (None, "axis", "face"):
        raise ValueError("Invalid wall reference")
    if type(side) is not int or side not in (-1, 0, 1) or (side == 0) != (reference == "axis"):
        raise ValueError("Invalid wall side")
    if type(value.get('priority', False)) is not bool:
        raise ValueError("wall_invalid_priority")
    result = dict(width=float(width), side=side)
    result.update(validated_appearance({k:v for k,v in value.items() if k in ('material','pattern')}))
    if reference is not None:
        result["reference"] = reference
    if value.get('priority', False):
        result['priority'] = True
    return result


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
        return wall["width"], round(-dy/length*wall["side"], 8), round(dx/length*wall["side"], 8), wall.get("reference"), appearance(wall), wall.get('priority', False)
    return wall["width"], wall["side"] * direction, wall.get("reference"), appearance(wall), wall.get('priority', False)


def wall_rank(shape):
    """Visual ownership only; ties prefer depth, then a stable style order."""
    wall = shape['wall']
    return wall.get('priority', False), wall['width'], *appearance(wall), shape['color']


def compatible_wall_style(a, b):
    """Compare physical profiles without quantization-boundary false splits."""
    first,second = a.get('wall'),b.get('wall')
    if not first or not second:
        return not first and not second
    if 'kind' in a or 'kind' in b:
        return wall_style(a) == wall_style(b)
    def profile(wall):
        return wall['width'],wall.get('reference'),appearance(wall),wall.get('priority',False)
    if profile(first) != profile(second):
        return False
    def n(shape,wall):
        dx,dy = shape['x2']-shape['x1'],shape['y2']-shape['y1']
        length = math.hypot(dx,dy)
        return -dy/length*wall['side'],dx/length*wall['side']
    return math.dist(n(a,first),n(b,second)) <= 1e-9


def copy_wall(source, target, reversed_direction=False):
    if source.get("wall"):
        target["wall"] = dict(source["wall"], side=source["wall"]["side"] * (-1 if reversed_direction else 1))
    return target
