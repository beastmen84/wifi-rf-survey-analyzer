"""Editable segment intersections and rigid planar transformations."""
from bisect import bisect_left, bisect_right, insort
from collections import defaultdict
import math
from survey.planar_geometry import cross, EPSILON, split_general_segments


def split_segments(segments, with_sources=False, limit=40000):
    """Split validated lines at crossings, T joints and collinear endpoints.

    Preserve stroke color, input order, direction and independent duplicates.
    This primitive only splits; normalize_segments also removes obsolete cuts.
    """
    if any(line["x1"] != line["x2"] and line["y1"] != line["y2"] for line in segments):
        return split_general_segments(segments, with_sources, limit)
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


def join_segments(segments, with_sources=False, protected=()):
    """Union like-colored overlapping fragments, then join unbranched ends.

    Input must already be split at every real intersection and overlap endpoint.
    Gaps, corners, real branches and differently colored strokes stay intact.
    Source sets identify every input fragment absorbed by a joined output.
    """
    unique, origins, by_stroke = [], [], {}
    for index, line in enumerate(segments):
        start, end = (line["x1"], line["y1"]), (line["x2"], line["y2"])
        key = (*sorted((start, end)), line["color"])
        if key in by_stroke:
            origins[by_stroke[key]].add(index)
        else:
            by_stroke[key] = len(unique)
            unique.append(line)
            origins.append({index})
    segments = unique
    endpoints = defaultdict(list)
    parents = list(range(len(segments)))
    for index, line in enumerate(segments):
        endpoints[(line["x1"], line["y1"])].append(index)
        endpoints[(line["x2"], line["y2"])].append(index)

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for point, incident in endpoints.items():
        if len(incident) != 2 or point in protected:
            continue
        first, second = incident
        a, b = segments[first], segments[second]
        if a["color"] != b["color"]:
            continue
        vectors = []
        for item in (a, b):
            start, end = (item["x1"], item["y1"]), (item["x2"], item["y2"])
            other = end if start == point else start
            vectors.append((other[0] - point[0], other[1] - point[1]))
        va, vb = vectors
        if (abs(cross(va, vb)) > EPSILON * math.hypot(*va) * math.hypot(*vb)
                or va[0] * vb[0] + va[1] * vb[1] >= 0):
            continue
        parents[root(second)] = root(first)

    components = defaultdict(list)
    for index in range(len(segments)):
        components[root(index)].append(index)
    result, sources = [], []
    for indices in sorted(components.values(), key=lambda group: group[0]):
        first = segments[indices[0]]
        merged = dict(first)
        dx, dy = first["x2"] - first["x1"], first["y2"] - first["y1"]
        values = [(segments[index]["x" + suffix], segments[index]["y" + suffix])
                  for index in indices for suffix in ("1", "2")]
        low = min(values, key=lambda point: point[0] * dx + point[1] * dy)
        high = max(values, key=lambda point: point[0] * dx + point[1] * dy)
        merged.update(x1=low[0], y1=low[1], x2=high[0], y2=high[1])
        result.append(merged)
        sources.append(frozenset().union(*(origins[index] for index in indices)))
    return (result, sources) if with_sources else result


def normalize_segments(segments, with_sources=False, limit=40000):
    """Rebuild current cuts, then join straight continuations without branches."""
    pieces, origins = split_segments(segments, with_sources=True, limit=limit)
    joined, groups = join_segments(pieces, with_sources=True)
    sources = [frozenset(origins[index] for index in group) for group in groups]
    return (joined, sources) if with_sources else joined


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
    return rotate_degrees(segments, turns * 90)


def rotate_degrees(segments, degrees, pivot=None):
    if not segments:
        return []
    angle = degrees % 360
    if angle == 0:
        return [dict(line) for line in segments]
    left, top, right, bottom = segment_bounds(segments)
    cx, cy = pivot if pivot is not None else ((left + right) / 2, (top + bottom) / 2)
    cosine, sine = ((1, 0), (0, 1), (-1, 0), (0, -1))[int(angle // 90)] if angle % 90 == 0 else (
        math.cos(math.radians(angle)), math.sin(math.radians(angle)))
    result = []
    for line in segments:
        updated = dict(line)
        for suffix in ("1", "2"):
            x, y = line["x" + suffix] - cx, line["y" + suffix] - cy
            updated["x" + suffix], updated["y" + suffix] = cx + x * cosine - y * sine, cy + x * sine + y * cosine
        result.append(updated)
    return result
