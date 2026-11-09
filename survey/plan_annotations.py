"""Non-structural paths and geometric wall-hosted apertures in plan pixels."""
from copy import deepcopy
import json
import math
import re

from survey.plan_mode import supports_plan_annotations
from survey.planar_geometry import point_projection
from survey.plan_objects import (FREE_ANNOTATIONS, HOSTED_ANNOTATIONS, DESK_VARIANTS,
                                 SYMBOL_VARIANTS, NUMBERED_SYMBOLS, object_vertices, object_is_round)

PLAN_ANNOTATIONS_KEY = "plan_annotations"
EPS = 1e-5


def validate_annotations(items):
    if not isinstance(items, list) or len(items) > 1000:
        raise ValueError("Too many annotations")
    result, identities, total = [], set(), 0
    for source in items:
        identity, kind = str(source["id"]), source["kind"]
        if not identity or len(identity) > 80 or identity in identities or kind not in ("marker", *HOSTED_ANNOTATIONS, *FREE_ANNOTATIONS):
            raise ValueError("Invalid annotation identity/type")
        identities.add(identity)
        if 'rack' in source and (kind!='symbol' or source.get('variant')!='rack'):
            raise ValueError('Inventory requires a rack symbol')
        color = str(source["color"]).lower()
        width = float(source.get("stroke", 2))
        if not re.fullmatch(r"#[0-9a-f]{6}", color) or not math.isfinite(width) or not .5 <= width <= 20:
            raise ValueError("Invalid annotation appearance")
        item = dict(id=identity, kind=kind, color=color, stroke=width)
        if kind in FREE_ANNOTATIONS:
            variant = source["variant"]
            if variant not in (DESK_VARIANTS if kind == "desk" else SYMBOL_VARIANTS):
                raise ValueError("Invalid object variant")
            numbers = {key: float(source[key]) for key in ("cx", "cy", "width", "height", "angle")}
            fill = source.get("fill")
            if fill is not None:
                fill = str(fill).lower()
                if not re.fullmatch(r"#[0-9a-f]{6}", fill):
                    raise ValueError("Invalid object fill")
            if any(not math.isfinite(v) for v in numbers.values()) or not all(EPS < numbers[k] <= 100000 for k in ("width", "height")):
                raise ValueError("Invalid object dimensions")
            item.update(numbers, variant=variant, fill=fill)
            if (kind == "symbol" and variant != "rack") or variant in ("square", "l_equal", "round"):
                if abs(item["width"] - item["height"]) > EPS:
                    raise ValueError("Object sides must be equal")
                item["height"] = item["width"]
            if kind == "desk" and variant in ("l", "l_equal"):
                arm = float(source["arm"])
                if not math.isfinite(arm) or not EPS < arm < min(item["width"], item["height"]) - EPS:
                    raise ValueError("Invalid desk arm depth")
                item["arm"] = arm
            item["angle"] = 0 if object_is_round(item) else item["angle"] % 360
            if kind == "symbol":
                if "number" in source:
                    number = source["number"]
                    if variant not in NUMBERED_SYMBOLS or type(number) is not int or not 1 <= number <= 999999:
                        raise ValueError("Invalid symbol number")
                    item["number"] = number
                if "description" in source:
                    description = source["description"]
                    if not isinstance(description, str) or len(description) > 2000 or "\0" in description:
                        raise ValueError("Invalid symbol description")
                    item["description"] = description
                if 'rack' in source:
                    from survey.rack_inventory import validate_rack
                    if variant != 'rack':
                        raise ValueError('Inventory requires a rack symbol')
                    rack = validate_rack(source['rack'])
                    if rack:
                        item['rack'] = rack
                if "ap_group" in source:
                    group = source["ap_group"]
                    if variant != "wifi_ap" or not isinstance(group, str) or not group.strip() or len(group) > 256:
                        raise ValueError("Invalid symbol AP association")
                    item["ap_group"] = group
                if "ap_label" in source and item.get("ap_group"):
                    label = source["ap_label"]
                    if not isinstance(label, str) or len(label) > 256 or "\0" in label:
                        raise ValueError("Invalid AP symbol label")
                    item["ap_label"] = label
        elif kind == "marker":
            points = source["points"]
            if not isinstance(points, list) or not 2 <= len(points) <= 10000:
                raise ValueError("Invalid marker path")
            clean = []
            for point in points:
                if not isinstance(point, (tuple, list)) or len(point) != 2:
                    raise ValueError("Invalid marker point")
                clean.append([float(v) for v in point])
            if all(point == clean[0] for point in clean):
                raise ValueError("Empty marker")
            item["points"] = clean
        else:
            item.update({key: float(source[key]) for key in ("x1", "y1", "x2", "y2")})
            if math.dist((item["x1"], item["y1"]), (item["x2"], item["y2"])) <= EPS:
                raise ValueError("Empty aperture")
            side, hinge = source.get("side", 1), source.get("hinge", 0)
            variant = source.get("variant", "single")
            if side not in (-1, 1) or hinge not in (0, 1) or variant not in ("single", "double", "sliding", "frame"):
                raise ValueError("Invalid door configuration")
            item.update(side=side, hinge=hinge, variant=variant)
        points = annotation_points(item)
        total += len(points)
        # Parametric rotations/translations can put an edge an ulp from zero.
        # Use the same tolerance as annotation_fits without rounding dimensions.
        precision = 1e-7 if kind in FREE_ANNOTATIONS else 0
        if total > 100000 or any(not math.isfinite(v) or not -precision <= v <= 100000 + precision for p in points for v in p):
            raise ValueError("Annotation coordinate limits exceeded")
        result.append(item)
    from survey.rack_inventory import validate_inventory_totals
    validate_inventory_totals(result)
    return result


def annotation_points(item):
    if item["kind"] in FREE_ANNOTATIONS:
        return object_vertices(item)
    return item["points"] if item["kind"] == "marker" else [[item["x1"], item["y1"]], [item["x2"], item["y2"]]]


def drawing_annotations(metadata):
    if not supports_plan_annotations(metadata):
        return []
    if PLAN_ANNOTATIONS_KEY not in metadata:
        return []
    document = json.loads(metadata[PLAN_ANNOTATIONS_KEY])
    if not isinstance(document, dict) or document.get("version") not in (1,2):
        raise ValueError("Unsupported annotation format")
    return validate_annotations(document.get("items"))


def encode_annotations(items):
    items=validate_annotations(items)
    return json.dumps(dict(version=2 if any(a.get('rack') for a in items) else 1, items=items), separators=(",", ":"))


def support_intervals(a, b, lines):
    """Project collinear finite hosts onto AB, preserving genuine gaps."""
    length = math.dist(a, b)
    if length <= EPS:
        return []
    ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    intervals = []
    for line in lines:
        points = [(line["x1"], line["y1"]), (line["x2"], line["y2"])]
        if any(abs((p[0] - a[0]) * uy - (p[1] - a[1]) * ux) > EPS for p in points):
            continue
        low, high = sorted((p[0] - a[0]) * ux + (p[1] - a[1]) * uy for p in points)
        if high >= -EPS and low <= length + EPS:
            intervals.append((max(0, low), min(length, high)))
    merged = []
    for low, high in sorted(intervals):
        if merged and low <= merged[-1][1] + EPS:
            merged[-1] = (merged[-1][0], max(merged[-1][1], high))
        else:
            merged.append((low, high))
    return merged


def supported(item, lines):
    if item["kind"] not in HOSTED_ANNOTATIONS:
        return True
    a, b = annotation_points(item)
    return any(low <= EPS and high >= math.dist(a, b) - EPS for low, high in support_intervals(a, b, lines))


def overlaps(item, others):
    if item["kind"] not in HOSTED_ANNOTATIONS:
        return False
    a, b = annotation_points(item)
    for other in others:
        if other["kind"] not in HOSTED_ANNOTATIONS or other["id"] == item["id"]:
            continue
        host = {k: other[k] for k in ("x1", "y1", "x2", "y2")}
        if any(high - low > EPS for low, high in support_intervals(a, b, [host])):
            return True
    return False


def visible_wall_segments(lines, annotations, with_sources=False):
    """Mask wall ink only; the structural model is never modified."""
    apertures = [a for a in annotations if a["kind"] in HOSTED_ANNOTATIONS]
    if apertures and any(line.get("wall") for line in lines):
        from survey.wall_geometry import projected_apertures
        apertures += projected_apertures(lines, apertures)
    result, sources = [], []
    hosts = [{k: item[k] for k in ("x1", "y1", "x2", "y2")} for item in apertures]
    for index, line in enumerate(lines):
        a, b = (line["x1"], line["y1"]), (line["x2"], line["y2"])
        length = math.dist(a, b)
        cursor = 0
        for low, high in support_intervals(a, b, hosts) + [(length, length)]:
            if low - cursor > EPS:
                values = [a[i] + (b[i] - a[i]) * t / length for t in (cursor, low) for i in (0, 1)]
                result.append(dict(line, **dict(zip(("x1", "y1", "x2", "y2"), values))))
                sources.append(index)
            cursor = max(cursor, high)
    return (result, sources) if with_sources else result


def transform_annotations(items, angle=0, pivot=(0, 0), dx=0, dy=0):
    result = deepcopy(items)
    cosine, sine = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    for item in result:
        if item["kind"] in FREE_ANNOTATIONS:
            x, y = item["cx"] - pivot[0], item["cy"] - pivot[1]
            item.update(cx=pivot[0] + x * cosine - y * sine + dx,
                        cy=pivot[1] + x * sine + y * cosine + dy,
                        angle=0 if object_is_round(item) else (item["angle"] + angle) % 360)
            continue
        points = []
        for x, y in annotation_points(item):
            x, y = x - pivot[0], y - pivot[1]
            points.append([pivot[0] + x * cosine - y * sine + dx, pivot[1] + x * sine + y * cosine + dy])
        if item["kind"] == "marker":
            item["points"] = points
        else:
            item.update(x1=points[0][0], y1=points[0][1], x2=points[1][0], y2=points[1][1])
    return result


def follow_hosts(items, before, after):
    """Rigid structural moves carry apertures supported by the moved run."""
    if not before or len(before) != len(after):
        return items
    first, last = before[0], after[0]
    old = (first["x1"], first["y1"])
    angle = math.degrees(math.atan2(last["y2"] - last["y1"], last["x2"] - last["x1"])
                         - math.atan2(first["y2"] - first["y1"], first["x2"] - first["x1"]))
    return [transform_annotations([item], angle, old, last["x1"] - old[0], last["y1"] - old[1])[0]
            if item["kind"] in HOSTED_ANNOTATIONS and supported(item, before) else item for item in items]


def place_aperture(point, width, lines, tolerance, template):
    choices = []
    for line in lines:
        a, b = (line["x1"], line["y1"]), (line["x2"], line["y2"])
        p, distance, axis_distance = aperture_projection(point, line)
        length = math.dist(a, b)
        # Extend over normalization cuts, but stop at real collinear gaps.
        ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        start = (p[0] - width / 2 * ux, p[1] - width / 2 * uy)
        end = (p[0] + width / 2 * ux, p[1] + width / 2 * uy)
        item = dict(template, x1=start[0], y1=start[1], x2=end[0], y2=end[1])
        if distance <= tolerance and supported(item, lines):
            choices.append((distance, axis_distance, item))
    return min(choices, key=lambda choice: choice[:2])[2] if choices else None


def aperture_projection(point, line):
    """Reference-face grip, distance to the physical wall, distance to its axis."""
    a, b = (line['x1'], line['y1']), (line['x2'], line['y2'])
    p = point_projection(point, a, b)
    wall = line.get('wall')
    if not wall:
        distance = math.dist(point, p)
        return p, distance, distance
    length = math.dist(a, b)
    ux, uy = (b[0]-a[0])/length, (b[1]-a[1])/length
    along = (point[0]-a[0])*ux+(point[1]-a[1])*uy
    across = -(point[0]-a[0])*uy+(point[1]-a[1])*ux
    low, high = ((-wall['width']/2, wall['width']/2) if wall['side'] == 0
                 else sorted((0, wall['side']*wall['width'])))
    distance = math.hypot(max(0, -along, along-length), max(0, low-across, across-high))
    return p, distance, math.hypot(max(0, -along, along-length), across-(low+high)/2)


def aperture_host_span(item, lines):
    """Use the containing segment, joining fragments only for a straddling opening."""
    a, b = annotation_points(item)
    length = math.dist(a, b)
    ux, uy = (b[0]-a[0])/length, (b[1]-a[1])/length
    intervals = []
    for index, line in enumerate(lines):
        points = [(line['x1'], line['y1']), (line['x2'], line['y2'])]
        if any(abs((p[0]-a[0])*uy-(p[1]-a[1])*ux) > EPS for p in points):
            continue
        low, high = sorted((p[0]-a[0])*ux+(p[1]-a[1])*uy for p in points)
        intervals.append((low, high, index))
    containing = [record for record in intervals if record[0] <= EPS and record[1] >= length-EPS]
    if containing:
        low, high, index = min(containing, key=lambda record: (record[1]-record[0], record[2]))
        return index, (a[0]+low*ux, a[1]+low*uy), (a[0]+high*ux, a[1]+high*uy)
    merged = []
    for low, high, index in sorted(intervals):
        if merged and low <= merged[-1][1]+EPS:
            merged[-1] = (merged[-1][0], max(high, merged[-1][1]), merged[-1][2])
        else:
            merged.append((low, high, index))
    for low, high, index in merged:
        if low <= EPS and high >= length-EPS:
            return index, (a[0]+low*ux, a[1]+low*uy), (a[0]+high*ux, a[1]+high*uy)
    return None


def align_aperture(item, lines, snapper, bounds, tolerance, grid=None, *, cursor=None):
    """Align jambs or the opening center without losing geometric wall support."""
    from survey.plan_snapping import SnapGuide, nearest_grid
    a, b = annotation_points(item)
    anchors = [a, b, [(a[i] + b[i]) / 2 for i in (0, 1)]]

    def candidate(anchor, target):
        dx, dy = target[0] - anchor[0], target[1] - anchor[1]
        moved = transform_annotations([item], dx=dx, dy=dy)[0]
        if (supported(moved, lines) and all(bounds[0] - EPS <= p[0] <= bounds[2] + EPS
                and bounds[1] - EPS <= p[1] <= bounds[3] + EPS for p in annotation_points(moved))):
            return moved
        return None

    choices = []
    for priority, (kind, points, xs) in enumerate(snapper.target_groups()):
        for anchor in anchors:
            for target in snapper.nearby(points, xs, anchor[0], tolerance):
                distance = math.dist(anchor, target)
                if distance <= tolerance:
                    moved = candidate(anchor, target)
                    if moved is not None:
                        # A short host puts both jambs close to its ends. Compare
                        # cursor intent across all magnets instead of always
                        # taking an incidental jamb/corner match before center.
                        score = (math.dist(cursor, target) if cursor is not None else distance,
                                 distance, priority, tuple(target))
                        choices.append((score, kind, target, moved))
    if choices:
        _score, kind, target, moved = min(choices, key=lambda c: c[0])
        return moved, (SnapGuide(kind, tuple(target)),)
    if grid and grid > 0:
        axis = 0 if abs(b[0] - a[0]) >= abs(b[1] - a[1]) else 1
        choices = []
        for anchor in anchors:
            value = nearest_grid(anchor[axis], bounds[axis], bounds[axis + 2], grid)
            if value is None:
                continue
            t = (value - anchor[axis]) / (b[axis] - a[axis])
            target = [anchor[i] + t * (b[i] - a[i]) for i in (0, 1)]
            moved = candidate(anchor, target)
            if moved is not None:
                choices.append((math.dist(anchor, target), tuple(target), moved))
        if choices:
            _distance, target, moved = min(choices, key=lambda c: c[:2])
            return moved, (SnapGuide("grid", target),)
    return item, ()
