"""Rigid room separation with exact normal constraints; no interior resizing."""
from copy import deepcopy
from dataclasses import dataclass
import math

import numpy as np
from PySide6.QtCore import QPointF
from PySide6.QtGui import QTransform, QPainterPathStroker

from survey.plan_faces import RegionPicker
from survey.plan_curve_geometry import normalize_plan
from survey.plan_curves import curve_info, point_at, transform_curves
from survey.plan_geometry import translate_segments
from survey.plan_labels import transform_labels
from survey.plan_annotations import transform_annotations, supported, annotation_points
from survey.wall_geometry import normal, wall_solids, validate_wall_bounds, path_area

EPS = 1e-5
MAX_ROOMS = 200


@dataclass
class WallLayout:
    state: dict
    moves: tuple
    areas: tuple
    changed_positions: bool


def room_side(shape, path):
    if "kind" not in shape:
        p = ((shape["x1"]+shape["x2"])/2, (shape["y1"]+shape["y2"])/2)
        n = normal(shape)
    else:
        p = point_at(shape, .5)
        _cx, _cy, _r, start, sweep = curve_info(shape)
        angle = start+sweep/2
        sign = math.copysign(1, sweep)
        n = -math.cos(angle)*sign, -math.sin(angle)*sign
    for probe in (.0001, .001, .01, .1, 1):
        left = path.contains(QPointF(p[0]+n[0]*probe, p[1]+n[1]*probe))
        right = path.contains(QPointF(p[0]-n[0]*probe, p[1]-n[1]*probe))
        if left != right:
            return -1 if left else 1
    raise ValueError("wall_side_ambiguous")


def solve_moves(count, constraints, anchor):
    if not constraints or all(abs(c[3]) < EPS for c in constraints):
        return [(0.0, 0.0)]*count
    graph = [set() for _ in range(count)]
    matrix, target = [], []
    for a, b, n, gap in constraints:
        graph[a].add(b)
        graph[b].add(a)
        row = np.zeros(count*2)
        row[2*a:2*a+2] = (-n[0], -n[1])
        row[2*b:2*b+2] = n
        matrix.append(row)
        target.append(gap)
    seen = set()
    for start in [anchor, *range(count)]:
        if start in seen:
            continue
        component, pending = set(), [start]
        while pending:
            current = pending.pop()
            if current in component:
                continue
            component.add(current)
            pending.extend(graph[current]-component)
        seen.update(component)
        for axis in (0, 1):
            row = np.zeros(count*2)
            row[2*start+axis] = 1
            matrix.append(row)
            target.append(0)
    matrix, target = np.array(matrix), np.array(target)
    solution = np.linalg.lstsq(matrix, target, rcond=1e-12)[0]
    if not np.all(np.isfinite(solution)) or np.max(np.abs(matrix@solution-target)) > EPS:
        raise ValueError("wall_constraints_conflict")
    # Normal gaps are hard constraints. Within their null space, preserve the
    # original tangential alignment instead of arbitrarily staggering a grid.
    from scipy.linalg import null_space
    basis = null_space(matrix, rcond=1e-12)
    if basis.shape[1]:
        tangent = []
        for a, b, n, _gap in constraints:
            row = np.zeros(count*2)
            row[2*a:2*a+2] = (n[1], -n[0])
            row[2*b:2*b+2] = (-n[1], n[0])
            tangent.append(row)
        tangent = np.array(tangent)
        solution += basis@np.linalg.lstsq(tangent@basis, -tangent@solution, rcond=1e-12)[0]
    return [(0 if abs(solution[2*i]) < EPS else float(solution[2*i]),
             0 if abs(solution[2*i+1]) < EPS else float(solution[2*i+1])) for i in range(count)]


def plan_wall_layout(state, selected_lines, selected_curves, width, bounds, *, open_side=0, anchor=0):
    if not math.isfinite(width) or not 0 <= width <= 10000 or open_side not in (-1, 0, 1):
        raise ValueError("wall_invalid_width")
    lines, curves = state["segments"] or [], state["curves"]
    if not (selected_lines or selected_curves) or any(i not in range(len(lines)) for i in selected_lines) or any(i not in range(len(curves)) for i in selected_curves):
        raise ValueError("wall_no_selection")
    picker = RegionPicker(lines, curves)
    rooms = picker.records
    if picker.limited or len(rooms) > MAX_ROOMS or len(lines)+len(curves) > 4000:
        raise ValueError("wall_complexity")
    if rooms and anchor not in range(len(rooms)):
        raise ValueError("wall_no_anchor")
    owners = [[] for _ in range(len(lines)+len(curves))]
    for index, (_path, room) in enumerate(rooms):
        for li in room.lines:
            owners[li].append(index)
        for ci in room.curves:
            owners[len(lines)+ci].append(index)
    shapes = [*lines, *curves]
    chosen = set(selected_lines) | {len(lines)+i for i in selected_curves}
    requested = {i: width for i in chosen}
    sides = {(i, owner): room_side(shape, rooms[owner][0]) for i, shape in enumerate(shapes) for owner in owners[i]}
    constraints, links = [], []
    for i, own in enumerate(owners):
        if len(own) > 2:
            raise ValueError("wall_constraints_conflict")
        if len(own) != 2:
            continue
        w = requested.get(i, shapes[i].get("wall", {}).get("width", 0))
        if i >= len(lines):
            if w > 0:
                raise ValueError("wall_shared_curve")
            constraints.extend((own[0], own[1], n, 0) for n in ((1, 0), (0, 1)))
        else:
            constraints.append((own[0], own[1], normal(lines[i], sides[i, own[0]]), w))
    # Opposite, overlapping faces at exactly the current depth are one divider.
    # Geometric association survives splitting, joins and rigid movement.
    singles = [i for i, shape in enumerate(lines) if len(owners[i]) == 1 and shape.get("wall")]
    if len(singles) > 2000:
        raise ValueError("wall_complexity")
    for pos, i in enumerate(singles):
        a, n = lines[i], normal(lines[i], sides[i, owners[i][0]])
        length = math.hypot(a["x2"]-a["x1"], a["y2"]-a["y1"])
        u = (a["x2"]-a["x1"])/length, (a["y2"]-a["y1"])/length
        for j in singles[pos+1:]:
            if owners[i] == owners[j]:
                continue
            b = lines[j]
            m = normal(b, sides[j, owners[j][0]])
            if n[0]*m[0]+n[1]*m[1] > -1+1e-8:
                continue
            gap = (b["x1"]-a["x1"])*n[0]+(b["y1"]-a["y1"])*n[1]
            if abs(gap-a["wall"]["width"]) > EPS or abs(gap-b["wall"]["width"]) > EPS:
                continue
            span = sorted((b["x"+s]-a["x1"])*u[0]+(b["y"+s]-a["y1"])*u[1] for s in ("1", "2"))
            if min(length, span[1])-max(0, span[0]) <= EPS:
                continue
            links.append((i, j, n, gap))
    changed = True
    while changed:
        changed = False
        for i, j, _n, _gap in links:
            if i in requested or j in requested:
                for index in (i, j):
                    if index not in requested:
                        requested[index] = width
                        changed = True
    for i, j, n, gap in links:
        constraints.append((owners[i][0], owners[j][0], n, requested.get(i, gap)-gap))
    moves = solve_moves(len(rooms), constraints, anchor) if rooms else []
    moved_paths = [QTransform.fromTranslate(*move).map(path) for (path, _room), move in zip(rooms, moves)]
    for i, path in enumerate(moved_paths):
        for other in moved_paths[i+1:]:
            if path.boundingRect().intersects(other.boundingRect()) and path_area(path.intersected(other)) > EPS:
                raise ValueError("wall_room_collision")
    def owner_at(point):
        return [i for i, (path, _room) in enumerate(rooms) if path.contains(QPointF(*point))]
    def displacement(points, hosted=None):
        hits = set()
        for point in points:
            hits.update(owner_at(point))
        if not hits and hosted:
            hits = {owner for i, line in enumerate(lines) if supported(hosted, [line]) for owner in owners[i]}
            if hits:
                return moves[min(hits, key=lambda i: (math.hypot(*moves[i]), i))]
        values = {moves[i] for i in hits}
        if len(values) > 1:
            raise ValueError("wall_content_conflict")
        return next(iter(values), (0.0, 0.0))
    output_lines, output_curves = [], []
    closed_lines, closed_curves = [], []
    for i, shape in enumerate(shapes):
        own = owners[i]
        w = requested.get(i, shape.get("wall", {}).get("width", 0))
        if w and not own and not (open_side or shape.get("wall")):
            raise ValueError("wall_open_side")
        for owner in own or [None]:
            if owner is None:
                p = point_at(shape, .5) if "kind" in shape else ((shape["x1"]+shape["x2"])/2, (shape["y1"]+shape["y2"])/2)
                move = displacement([p])
            else:
                move = moves[owner]
            item = (transform_curves([shape], dx=move[0], dy=move[1]) if "kind" in shape
                    else translate_segments([shape], *move))[0]
            item.pop("wall", None)
            if w:
                side = sides[i, owner] if owner is not None else open_side or shape["wall"]["side"]
                item["wall"] = dict(width=w, side=side)
            (output_curves if "kind" in shape else output_lines).append(item)
            if own:
                (closed_curves if "kind" in shape else closed_lines).append(item)
    output_lines, output_curves = normalize_plan(output_lines, output_curves)
    validate_wall_bounds(output_lines, output_curves, bounds)
    display_margin = QPainterPathStroker()
    display_margin.setWidth(.02)  # Derived cubic/polygon display tolerance only.
    for _color, body in wall_solids(closed_lines, closed_curves):
        for path in moved_paths:
            interior = path.subtracted(display_margin.createStroke(path))
            if body.boundingRect().intersects(path.boundingRect()) and path_area(body.intersected(interior)) > EPS:
                raise ValueError("wall_room_collision")
    result = deepcopy(state)
    result.update(segments=output_lines, curves=output_curves)
    result["annotations"] = []
    for item in state["annotations"]:
        points = annotation_points(item)
        if item["kind"] in ("door", "window"):
            dx, dy = item["x2"]-item["x1"], item["y2"]-item["y1"]
            length = math.hypot(dx, dy)
            center = ((item["x1"]+item["x2"])/2, (item["y1"]+item["y2"])/2)
            side = item.get("side", 1)
            points = [(center[0]-dy/length*.01*side, center[1]+dx/length*.01*side)] if item["kind"] == "door" else []
        move = displacement(points, item if item["kind"] in ("door", "window") else None)
        result["annotations"].extend(transform_annotations([item], dx=move[0], dy=move[1]))
    result["labels"] = []
    for label in state["labels"]:
        move = displacement([(label["x"], label["y"])])
        result["labels"].extend(transform_labels([label], dx=move[0], dy=move[1]))
    rebuilt = RegionPicker(output_lines, output_curves)
    for path, (_old, room) in zip(moved_paths, rooms):
        matches = [new.area for candidate, new in rebuilt.records
                   if path_area(path.subtracted(candidate)) < EPS and path_area(candidate.subtracted(path)) < EPS]
        if not any(abs(area-room.area) <= max(EPS, room.area*1e-9) for area in matches):
            raise ValueError("wall_room_changed")
    return WallLayout(result, tuple(moves), tuple(room.area for _path, room in rooms), any(math.hypot(*move) > EPS for move in moves))
