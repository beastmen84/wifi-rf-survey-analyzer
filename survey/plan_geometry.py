"""Editable segment intersections and rigid orthogonal transformations."""
from bisect import bisect_left, bisect_right, insort
from collections import defaultdict


def split_segments(segments, with_sources=False, limit=40000):
    """Split validated lines at crossings, T joints and collinear endpoints.

    Preserve stroke color, input order, direction and independent duplicates.
    Existing cuts remain editable even after their intersecting side is erased.
    """
    groups = defaultdict(list)
    keys = []
    for index, line in enumerate(segments):
        horizontal = line["y1"] == line["y2"]
        coordinate = line["y1"] if horizontal else line["x1"]
        low, high = sorted((line["x1"], line["x2"]) if horizontal else (line["y1"], line["y2"]))
        key = (horizontal, coordinate, low, high)
        keys.append(key)
        groups[key].append(index)
    cuts = {key: {key[2], key[3]} for key in groups}
    count = len(segments)
    if count > limit:
        raise ValueError("Too many editable plan segments")

    def add_cut(key, value):
        nonlocal count
        if value not in cuts[key]:
            count += len(groups[key])
            if count > limit:
                raise ValueError("Too many editable plan segments")
            cuts[key].add(value)

    axes = defaultdict(list)
    for key in groups:
        axes[key[:2]].append(key)
    for same_axis in axes.values():
        endpoints = sorted({value for key in same_axis for value in key[2:]})
        for key in same_axis:
            for value in endpoints[bisect_right(endpoints, key[2]):bisect_left(endpoints, key[3])]:
                add_cut(key, value)
    events = []
    for key in groups:
        horizontal, coordinate, low, high = key
        if horizontal:
            events.append((coordinate, 1, key))
        else:
            events.extend(((low, 0, key), (high, 2, key)))
    active, positions = defaultdict(set), []
    for y, kind, key in sorted(events):
        x = key[1]
        if kind == 0:
            if not active[x]:
                insort(positions, x)
            active[x].add(key)
        elif kind == 2:
            active[x].remove(key)
            if not active[x]:
                positions.pop(bisect_left(positions, x))
        else:
            for x in positions[bisect_left(positions, key[2]):bisect_right(positions, key[3])]:
                add_cut(key, x)
                for vertical in active[x]:
                    add_cut(vertical, y)
    result, sources = [], []
    for index, (line, key) in enumerate(zip(segments, keys)):
        horizontal, coordinate, _, _ = key
        values = sorted(cuts[key], reverse=(line["x1"] > line["x2"] if horizontal else line["y1"] > line["y2"]))
        for low, high in zip(values, values[1:]):
            result.append(dict(x1=low if horizontal else coordinate, y1=coordinate if horizontal else low,
                               x2=high if horizontal else coordinate, y2=coordinate if horizontal else high,
                               color=line["color"]))
            sources.append(index)
    return (result, sources) if with_sources else result


def segment_bounds(segments):
    return (min(line[key] for line in segments for key in ("x1", "x2")),
            min(line[key] for line in segments for key in ("y1", "y2")),
            max(line[key] for line in segments for key in ("x1", "x2")),
            max(line[key] for line in segments for key in ("y1", "y2")))


def translate_segments(segments, dx, dy):
    return [dict(line, x1=line["x1"] + dx, x2=line["x2"] + dx,
                 y1=line["y1"] + dy, y2=line["y2"] + dy) for line in segments]


def rotate_segments(segments, turns=1):
    """Rotate clockwise in screen coordinates about the selection's box center."""
    if not segments:
        return []
    if turns % 4 == 0:
        return [dict(line) for line in segments]
    left, top, right, bottom = segment_bounds(segments)
    cx, cy = (left + right) / 2, (top + bottom) / 2
    result = []
    for line in segments:
        updated = dict(line)
        for suffix in ("1", "2"):
            x, y = line["x" + suffix] - cx, line["y" + suffix] - cy
            for _ in range(turns % 4):
                x, y = -y, x
            updated["x" + suffix], updated["y" + suffix] = cx + x, cy + y
        result.append(updated)
    return result
