"""Editable plan segments in the same pixel coordinate system as survey points."""
import json
import math
import re
from hashlib import sha256

from PIL import Image, ImageDraw
from app_core.constants import DEFAULT_FLOORPLAN_METADATA_KEY, GENERATED_FLOORPLAN_METADATA_KEY

PLAN_DRAWING_KEY = "plan_drawing"


def validate_segments(segments):
    if not isinstance(segments, list) or len(segments) > 40000:
        raise ValueError("Invalid plan segment list")
    result = []
    for segment in segments:
        coordinates = {key: float(segment[key]) for key in ("x1", "y1", "x2", "y2")}
        if any(not math.isfinite(value) or not 0 <= value <= 100000 for value in coordinates.values()):
            raise ValueError("Invalid plan segment coordinates")
        if coordinates["x1"] == coordinates["x2"] and coordinates["y1"] == coordinates["y2"]:
            raise ValueError("Empty plan segment")
        color = str(segment["color"])
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("Invalid plan stroke color")
        result.append(dict(coordinates, color=color.lower()))
    return result


def drawing_segments(metadata):
    return drawing_geometry(metadata)[0]


def drawing_geometry(metadata):
    generated = any(metadata.get(key) == "1" for key in
                    (DEFAULT_FLOORPLAN_METADATA_KEY, GENERATED_FLOORPLAN_METADATA_KEY))
    if not generated or PLAN_DRAWING_KEY not in metadata:
        return None, []
    document = json.loads(metadata[PLAN_DRAWING_KEY])
    if not isinstance(document, dict) or document.get("version") != 1:
        raise ValueError("Unsupported plan drawing")
    from survey.plan_curves import drawing_curves
    from survey.plan_curve_geometry import normalize_plan
    return normalize_plan(validate_segments(document.get("segments")), drawing_curves(metadata) or [])


def encode_drawing(segments, curves=None):
    from survey.plan_curve_geometry import normalize_plan
    lines, _ = normalize_plan(validate_segments(segments), curves or [])
    return json.dumps(dict(version=1, segments=lines), separators=(",", ":"))


def rectangle_segments(x, y, width, height, color):
    if not all(math.isfinite(value) for value in (x, y, width, height)) or min(width, height) <= 0:
        raise ValueError("Invalid rectangle dimensions")
    corners = [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
    return validate_segments([dict(x1=a[0], y1=a[1], x2=b[0], y2=b[1], color=color)
                              for a, b in zip(corners, corners[1:] + corners[:1])])


def render_plan_drawing(image, segments, labels=None, curves=None, annotations=None):
    if segments is None and not labels and not curves and not annotations:
        return image
    # Generated PNGs may contain an older baked drawing. Rebuild from vectors,
    # including an empty list after Undo, instead of leaving stale lines behind.
    output = Image.new("RGB", image.size, "white")
    painter = ImageDraw.Draw(output)
    lines = validate_segments(segments or [])
    from survey.plan_annotations import validate_annotations, visible_wall_segments, supported, overlaps
    annotations = validate_annotations(annotations or [])
    for index, annotation in enumerate(annotations):
        if not supported(annotation, lines) or overlaps(annotation, annotations[:index]):
            raise ValueError("Invalid annotation host")
    for line in lines:
        if any(line[key] > image.size[index] + 1e-7
               for index, keys in enumerate((("x1", "x2"), ("y1", "y2"))) for key in keys):
            raise ValueError("Plan segment is outside the sheet")
    for line in visible_wall_segments(lines, annotations):
        points = tuple(min(line[key], image.size[index % 2] - 1)
                       for index, key in enumerate(("x1", "y1", "x2", "y2")))
        painter.line(points, fill=line["color"], width=2)
    from survey.plan_curves import validate_curves, curve_bounds
    curves = validate_curves(curves or [])
    for curve in curves:
        left, top, right, bottom = curve_bounds(curve)
        if left < -1e-7 or top < -1e-7 or right > image.width + 1e-7 or bottom > image.height + 1e-7:
            raise ValueError("Curve is outside the sheet")
    if curves:
        from survey.plan_curve_rendering import render_curves
        output = render_curves(output, curves)
    from survey.plan_labels import validate_labels, labels_geometry
    labels = validate_labels(labels or [])
    if any(line[key] < -1e-6 or line[key] > image.size[index] + 1e-6
           for line in labels_geometry(labels) for index, keys in enumerate((("x1", "x2"), ("y1", "y2"))) for key in keys):
        raise ValueError("Text label is outside the sheet")
    if annotations:
        from survey.plan_annotation_rendering import render_annotations, annotation_fits
        from PySide6.QtCore import QRectF
        bounds = QRectF(0, 0, image.width, image.height)
        if any(not annotation_fits(a, bounds) for a in annotations):
            raise ValueError("Annotation is outside the sheet")
        output = render_annotations(output, annotations)
    if labels:
        from survey.plan_label_rendering import render_labels
        output = render_labels(output, labels)
    fingerprint = [lines, labels, curves] if curves else [lines, labels]
    if annotations:
        fingerprint = [lines, labels, curves, annotations]
    output.info["plan_drawing_fingerprint"] = sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()
    return output
