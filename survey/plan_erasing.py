"""Finite-segment picking and area selection for validated plan geometry."""


def nearest_segment(segments, x, y, tolerance):
    """Pick one whole segment; equal distances prefer the last drawn segment."""
    closest, limit = None, tolerance * tolerance
    for index, line in enumerate(segments):
        px = min(max(x, min(line["x1"], line["x2"])), max(line["x1"], line["x2"]))
        py = min(max(y, min(line["y1"], line["y2"])), max(line["y1"], line["y2"]))
        distance = (x - px) ** 2 + (y - py) ** 2
        if distance <= limit:
            closest, limit = index, distance
    return closest


def intersecting_segments(segments, x1, y1, x2, y2):
    """Select whole axis-aligned segments touched by the closed selection box."""
    left, right = sorted((x1, x2))
    top, bottom = sorted((y1, y2))
    return tuple(index for index, line in enumerate(segments)
                 if max(line["x1"], line["x2"]) >= left
                 and min(line["x1"], line["x2"]) <= right
                 and max(line["y1"], line["y2"]) >= top
                 and min(line["y1"], line["y2"]) <= bottom)
