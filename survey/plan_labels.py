"""Portable editable text labels with stored glyph outlines in plan pixels."""
import json
import math
import re
from copy import deepcopy

from survey.plan_mode import supports_plan_annotations
from survey.plan_geometry import rotate_degrees, segment_bounds

PLAN_LABELS_KEY = "plan_labels"


def validate_labels(labels):
    if not isinstance(labels, list) or len(labels) > 500:
        raise ValueError("Invalid plan labels")
    result, identities, commands = [], set(), 0
    for source in labels:
        identity = str(source["id"])
        text, family = str(source["text"]), str(source["family"])
        if not identity or len(identity) > 80 or identity in identities or not text.strip() or len(text) > 2048 or not family or len(family) > 128:
            raise ValueError("Invalid text identity or content")
        identities.add(identity)
        numbers = {key: float(source[key]) for key in ("x", "y", "angle", "size", "width", "height", "outline_width")}
        if (any(not math.isfinite(value) for value in numbers.values())
                or not 0 <= numbers["x"] <= 100000 or not 0 <= numbers["y"] <= 100000
                or not 1 <= numbers["size"] <= 300 or not 0 <= numbers["outline_width"] <= 16
                or not 0 < numbers["width"] <= 100000 or not 0 < numbers["height"] <= 100000):
            raise ValueError("Invalid text geometry")
        colors = {key: str(source[key]).lower() for key in ("color", "outline_color")}
        if any(not re.fullmatch(r"#[0-9a-f]{6}", color) for color in colors.values()):
            raise ValueError("Invalid text color")
        alignment = str(source.get("alignment", "left"))
        if alignment not in ("left", "center", "right"):
            raise ValueError("Invalid text alignment")
        path = source["path"]
        if not isinstance(path, list) or not path or len(path) > 25000:
            raise ValueError("Invalid glyph outline")
        clean_path = []
        for command in path:
            if not isinstance(command, (list, tuple)) or not command or command[0] not in ("M", "L", "C"):
                raise ValueError("Invalid glyph command")
            values = [float(value) for value in command[1:]]
            if len(values) != (6 if command[0] == "C" else 2) or any(not math.isfinite(value) for value in values):
                raise ValueError("Invalid glyph coordinates")
            if any(abs(value) > numbers["width" if index % 2 == 0 else "height"] / 2 + 1e-6
                   for index, value in enumerate(values)):
                raise ValueError("Glyph outside text bounds")
            clean_path.append([command[0], *values])
        if clean_path[0][0] != "M":
            raise ValueError("Glyph needs an origin")
        commands += len(clean_path)
        if commands > 250000:
            raise ValueError("Too many glyph commands")
        numbers["angle"] %= 360
        result.append(dict(id=identity, text=text, family=family, **numbers, **colors,
                           bold=bool(source.get("bold")), italic=bool(source.get("italic")),
                           alignment=alignment, path=clean_path))
    return result


def drawing_labels(metadata):
    if not supports_plan_annotations(metadata):
        return None
    if PLAN_LABELS_KEY not in metadata:
        return []
    document = json.loads(metadata[PLAN_LABELS_KEY])
    if not isinstance(document, dict) or document.get("version") != 1:
        raise ValueError("Unsupported plan labels")
    return validate_labels(document.get("labels"))


def encode_labels(labels):
    return json.dumps(dict(version=1, labels=validate_labels(labels)), separators=(",", ":"), ensure_ascii=True)


def label_geometry(label):
    x, y, w, h = label["x"], label["y"], label["width"] / 2, label["height"] / 2
    points = [(x - w, y - h), (x + w, y - h), (x + w, y + h), (x - w, y + h)]
    lines = [dict(x1=a[0], y1=a[1], x2=b[0], y2=b[1], color=label["color"])
             for a, b in zip(points, points[1:] + points[:1])]
    return rotate_degrees(lines, label["angle"], (x, y))


def labels_geometry(labels):
    return [line for label in labels for line in label_geometry(label)]


def transform_labels(labels, angle=0, pivot=None, dx=0, dy=0):
    result = deepcopy(labels)
    if not result:
        return result
    if angle % 360 == 0:
        for label in result:
            label["x"] += dx
            label["y"] += dy
        return result
    if pivot is None:
        left, top, right, bottom = segment_bounds(labels_geometry(result))
        pivot = ((left + right) / 2, (top + bottom) / 2)
    radians = math.radians(angle)
    cosine, sine = math.cos(radians), math.sin(radians)
    for label in result:
        x, y = label["x"] - pivot[0], label["y"] - pivot[1]
        label["x"] = pivot[0] + x * cosine - y * sine + dx
        label["y"] = pivot[1] + x * sine + y * cosine + dy
        label["angle"] = (label["angle"] + angle) % 360
    return result
