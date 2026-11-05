"""Finite-segment picking and area selection for validated plan geometry."""
from survey.planar_geometry import point_projection, segment_box_intersects


def nearest_segment(segments, x, y, tolerance):
    """Pick one whole segment; equal distances prefer the last drawn segment."""
    closest, limit = None, tolerance * tolerance
    for index, line in enumerate(segments):
        px, py = point_projection((x, y), (line["x1"], line["y1"]), (line["x2"], line["y2"]))
        distance = (x - px) ** 2 + (y - py) ** 2
        if distance <= limit:
            closest, limit = index, distance
    return closest


def intersecting_segments(segments, x1, y1, x2, y2):
    """Select whole finite segments touched by the closed selection box."""
    left, right = sorted((x1, x2))
    top, bottom = sorted((y1, y2))
    return tuple(index for index, line in enumerate(segments) if segment_box_intersects(line, left, top, right, bottom))
