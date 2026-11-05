"""Editable plan segments in the same pixel coordinate system as survey points."""
import json
import math
import re
from hashlib import sha256

from PIL import Image, ImageDraw
from app_core.constants import DEFAULT_FLOORPLAN_METADATA_KEY, GENERATED_FLOORPLAN_METADATA_KEY
from survey.plan_geometry import split_segments

PLAN_DRAWING_KEY = "plan_drawing"


def validate_segments(segments):
    if not isinstance(segments, list) or len(segments) > 40000:
        raise ValueError("Invalid plan segment list")
    result = []
    for segment in segments:
        coordinates = {key: float(segment[key]) for key in ("x1", "y1", "x2", "y2")}
        if any(not math.isfinite(value) or not 0 <= value <= 100000 for value in coordinates.values()):
            raise ValueError("Invalid plan segment coordinates")
        if coordinates["x1"] != coordinates["x2"] and coordinates["y1"] != coordinates["y2"]:
            raise ValueError("Plan segments must be horizontal or vertical")
        if coordinates["x1"] == coordinates["x2"] and coordinates["y1"] == coordinates["y2"]:
            raise ValueError("Empty plan segment")
        color = str(segment["color"])
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("Invalid plan stroke color")
        result.append(dict(coordinates, color=color.lower()))
    return result


def drawing_segments(metadata):
    generated = any(metadata.get(key) == "1" for key in
                    (DEFAULT_FLOORPLAN_METADATA_KEY, GENERATED_FLOORPLAN_METADATA_KEY))
    if not generated or PLAN_DRAWING_KEY not in metadata:
        return None
    document = json.loads(metadata[PLAN_DRAWING_KEY])
    if not isinstance(document, dict) or document.get("version") != 1:
        raise ValueError("Unsupported plan drawing")
    return split_segments(validate_segments(document.get("segments")))


def encode_drawing(segments):
    return json.dumps(dict(version=1, segments=split_segments(validate_segments(segments))), separators=(",", ":"))


def rectangle_segments(x, y, width, height, color):
    if not all(math.isfinite(value) for value in (x, y, width, height)) or min(width, height) <= 0:
        raise ValueError("Invalid rectangle dimensions")
    corners = [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
    return validate_segments([dict(x1=a[0], y1=a[1], x2=b[0], y2=b[1], color=color)
                              for a, b in zip(corners, corners[1:] + corners[:1])])


def render_plan_drawing(image, segments):
    if segments is None:
        return image
    # Generated PNGs may contain an older baked drawing. Rebuild from vectors,
    # including an empty list after Undo, instead of leaving stale lines behind.
    output = Image.new("RGB", image.size, "white")
    painter = ImageDraw.Draw(output)
    lines = validate_segments(segments)
    for line in lines:
        if any(line[key] > image.size[index] + 1e-7
               for index, keys in enumerate((("x1", "x2"), ("y1", "y2"))) for key in keys):
            raise ValueError("Plan segment is outside the sheet")
        points = tuple(min(line[key], image.size[index % 2] - 1)
                       for index, key in enumerate(("x1", "y1", "x2", "y2")))
        painter.line(points, fill=line["color"], width=2)
    output.info["plan_drawing_fingerprint"] = sha256(json.dumps(lines, sort_keys=True).encode()).hexdigest()
    return output
