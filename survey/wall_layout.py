"""Rigid room separation with exact normal constraints; no interior resizing."""
from copy import deepcopy
from dataclasses import dataclass
import math

import numpy as np
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QTransform, QPainterPathStroker

from survey.plan_faces import RegionPicker
from survey.plan_curve_geometry import normalize_plan
from survey.plan_curves import curve_info, point_at, transform_curves, curve_bounds
from survey.plan_geometry import translate_segments
from survey.plan_labels import transform_labels
from survey.plan_annotations import transform_annotations, supported, annotation_points, follow_hosts
from survey.wall_geometry import normal, wall_solids, validate_wall_bounds, path_area

EPS = 1e-5
MAX_ROOMS = 200


class WallLayoutError(ValueError):
    def __init__(self, key, rooms=()):
        super().__init__(key)
        self.rooms = tuple(sorted(set(rooms)))


@dataclass
class WallLayout:
    state: dict
    moves: tuple
    areas: tuple
    changed_positions: bool
    usable_areas: tuple = ()
    approximate_areas: bool = False


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


def same_room(a, b):
    """Compare occupied geometry, independent of extra collinear boundary cuts."""
    if a == b:
        return True
    if any(abs(x-y) > EPS for x,y in zip(a.boundingRect().getRect(), b.boundingRect().getRect())):
        return False
    tolerance = max(EPS, max(path_area(a), path_area(b))*1e-9)
    return path_area(a.subtracted(b)) <= tolerance and path_area(b.subtracted(a)) <= tolerance


def solve_moves(count, constraints, anchor, *, supports=(), fixed=()):
    if not supports and (not constraints or all(abs(c[3]) < EPS for c in constraints)):
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
    for owner, n, gap in supports:
        row = np.zeros(count*2)
        row[2*owner:2*owner+2] = n
        matrix.append(row)
        target.append(gap)
    fixed = set(fixed)
    for owner in fixed:
        for axis in (0, 1):
            row = np.zeros(count*2)
            row[2*owner+axis] = 1
            matrix.append(row)
            target.append(0)
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
        if component & fixed or any(owner in component for owner, _n, _gap in supports):
            continue  # Existing references already fix this component in space.
        for axis in (0, 1):
            row = np.zeros(count*2)
            row[2*start+axis] = 1
            matrix.append(row)
            target.append(0)
    matrix, target = np.array(matrix), np.array(target)
    solution = np.linalg.lstsq(matrix, target, rcond=1e-12)[0]
    if not np.all(np.isfinite(solution)) or np.max(np.abs(matrix@solution-target)) > EPS:
        pairs, involved = {}, set()
        for a, b, n, gap in constraints:
            if a > b:
                a, b, n = b, a, (-n[0], -n[1])
            pairs.setdefault((a, b), []).append((n, gap))
        for pair, equations in pairs.items():
            normals = np.array([n for n, _g in equations])
            gaps = np.array([g for _n, g in equations])
            relative = np.linalg.lstsq(normals, gaps, rcond=1e-12)[0]
            if np.max(np.abs(normals@relative-gaps)) > EPS:
                involved.update(pair)
        if not involved:
            residuals = np.abs(matrix@solution-target)
            for i, (a, b, _n, _gap) in enumerate(constraints):
                if residuals[i] > EPS:
                    involved.update((a, b))
        raise WallLayoutError("wall_constraints_conflict", involved)
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
        if len(tangent):
            solution += basis@np.linalg.lstsq(tangent@basis, -tangent@solution, rcond=1e-12)[0]
    return [(0 if abs(solution[2*i]) < EPS else float(solution[2*i]),
             0 if abs(solution[2*i+1]) < EPS else float(solution[2*i+1])) for i in range(count)]


def plan_wall_layout(state, selected_lines, selected_curves, width, bounds, *, open_side=0, anchor=0, widths=None, open_sides=None, appearances=None, priorities=None, fixed_state=None, fixed_rooms=()):
    if not math.isfinite(width) or not 0 <= width <= 10000 or open_side not in (-1, 0, 1):
        raise ValueError("wall_invalid_width")
    lines, curves = state["segments"] or [], state["curves"]
    if any(s.get("wall", {}).get("reference") for s in [*lines, *curves]):
        raise ValueError("wall_reference_mode")
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
    from survey.wall_materials import validated_appearance
    appearances = appearances or {}
    if any(type(i) is not int or i not in range(len(shapes)) for i in appearances):
        raise ValueError('wall_invalid_material')
    appearances = {i:validated_appearance(v) for i,v in appearances.items()}
    priorities = priorities or {}
    if any(type(i) is not int or i not in range(len(shapes)) or type(v) is not bool for i,v in priorities.items()):
        raise ValueError('wall_invalid_priority')
    chosen = set(selected_lines) | {len(lines)+i for i in selected_curves}
    requested = {i: width for i in chosen}
    if widths is not None:
        if set(widths) != chosen or any(isinstance(w, bool) or not isinstance(w, (int, float)) or not math.isfinite(w) or not 0 <= w <= 10000 for w in widths.values()):
            raise ValueError("wall_invalid_width")
        requested = dict(widths)
    open_sides = open_sides or {}
    if any(i not in chosen or type(s) is not int or s not in (-1, 1) for i, s in open_sides.items()):
        raise ValueError("wall_open_side")
    sides = {(i, owner): room_side(shape, rooms[owner][0]) for i, shape in enumerate(shapes) for owner in owners[i]}
    # A pre-existing open wall is a fixed physical support. Closing a room on
    # its thickness side needs an opposite face, not a reversal of that wall.
    inward = {i:own[0] for i,own in enumerate(owners[:len(lines)]) if len(own) == 1
              and shapes[i].get('wall') and shapes[i]['wall']['side'] != sides[i,own[0]]}
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
    ground_links = []
    if fixed_state is not None:
        from survey.wall_editing import relation
        for i in singles:
            for j,own in enumerate(owners[:len(lines)]):
                if own:
                    continue
                match = relation(lines[j], lines[i])
                if match:
                    ground_links.append((i,j,match[3],match[4]))
    changed = True
    while changed:
        changed = False
        for i, j, _n, _gap in [*links, *ground_links]:
            if i in requested or j in requested:
                if i in requested and j in requested and abs(requested[i]-requested[j]) > EPS:
                    raise ValueError("wall_shared_width_conflict")
                for index in (i, j):
                    if index not in requested:
                        requested[index] = requested[j if index == i else i]
                        changed = True
    for i, j, n, gap in links:
        constraints.append((owners[i][0], owners[j][0], n, requested.get(i, gap)-gap))
    supports = [(owner, normal(lines[i], lines[i]['wall']['side']),
                 requested.get(i, lines[i]['wall']['width'])) for i,owner in inward.items()]
    supports.extend((owners[i][0],n,requested.get(i,gap)-gap) for i,_j,n,gap in ground_links)
    fixed = set(fixed_rooms)
    if any(type(i) is not int or i not in range(len(rooms)) for i in fixed):
        raise ValueError('wall_no_anchor')
    if fixed_state is not None:
        previous = RegionPicker(fixed_state['segments'] or [], fixed_state['curves']).records
        fixed.update(i for i,(path,_room) in enumerate(rooms)
                 if any(path.boundingRect().intersects(old.boundingRect()) and path_area(path.intersected(old)) > EPS
                        for old,_r in previous))
    moves = solve_moves(len(rooms), constraints, anchor, supports=supports, fixed=fixed) if rooms else []
    moved_paths = [QTransform.fromTranslate(*move).map(path) for (path, _room), move in zip(rooms, moves)]
    for i, path in enumerate(moved_paths):
        for other_index, other in enumerate(moved_paths[i+1:], i+1):
            if path.boundingRect().intersects(other.boundingRect()) and path_area(path.intersected(other)) > EPS:
                raise WallLayoutError("wall_room_collision", (i, other_index))
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
            raise WallLayoutError("wall_content_conflict", hits)
        return next(iter(values), (0.0, 0.0))
    output_lines, output_curves = [], []
    host_moves = []
    closed_lines, closed_curves = [], []
    for i, shape in enumerate(shapes):
        own = owners[i]
        w = requested.get(i, shape.get("wall", {}).get("width", 0))
        if w and not own and not (open_sides.get(i) or open_side or shape.get("wall")):
            raise ValueError("wall_open_side")
        for owner in own or [None]:
            if owner is None:
                p = point_at(shape, .5) if "kind" in shape else ((shape["x1"]+shape["x2"])/2, (shape["y1"]+shape["y2"])/2)
                move = (0.0, 0.0) if fixed_state is not None else displacement([p])
            else:
                move = moves[owner]
            item = (transform_curves([shape], dx=move[0], dy=move[1]) if "kind" in shape
                    else translate_segments([shape], *move))[0]
            item.pop("wall", None)
            if w:
                side = sides[i, owner] if owner is not None else open_sides.get(i) or open_side or shape["wall"]["side"]
                decoration = {k:v for k,v in shape.get('wall',{}).items() if k in ('material','pattern')}
                item["wall"] = dict(width=w, side=side, **appearances.get(i,decoration))
                if priorities.get(i, shape.get('wall', {}).get('priority', False)):
                    item['wall']['priority'] = True
            (output_curves if "kind" in shape else output_lines).append(item)
            if 'kind' not in shape:
                host_moves.append((shape,item))
            if i in inward:
                # Retain the original face and its side; the translated room
                # boundary is the opposite face of the same physical wall.
                reference = dict(item, **{k:shape[k] for k in ('x1','y1','x2','y2')})
                if w:
                    reference['wall'] = dict(item['wall'], side=shape['wall']['side'])
                output_lines.append(reference)
            if own:
                (closed_curves if "kind" in shape else closed_lines).append(item)
    output_lines, output_curves = normalize_plan(output_lines, output_curves)
    extent = bounds.adjusted(-EPS,-EPS,EPS,EPS)
    if any(not extent.contains(QPointF(line['x'+s],line['y'+s])) for line in output_lines for s in ('1','2')):
        raise ValueError('wall_outside')
    for curve in output_curves:
        left, top, right, bottom = curve_bounds(curve)
        if not extent.contains(QRectF(left,top,right-left,bottom-top)):
            raise ValueError('wall_outside')
    validate_wall_bounds(output_lines, output_curves, bounds)
    display_margin = QPainterPathStroker()
    display_margin.setWidth(.02)  # Derived cubic/polygon display tolerance only.
    for _color, body in wall_solids(closed_lines, closed_curves):
        for room_index, path in enumerate(moved_paths):
            interior = path.subtracted(display_margin.createStroke(path))
            if body.boundingRect().intersects(path.boundingRect()) and path_area(body.intersected(interior)) > EPS:
                raise WallLayoutError("wall_room_collision", (room_index,))
    result = deepcopy(state)
    result.update(segments=output_lines, curves=output_curves)
    result["annotations"] = []
    for item in state["annotations"]:
        if fixed_state is not None:
            preserved = deepcopy(item)
            if not supported(preserved, output_lines):
                for before, after in host_moves:
                    if supported(item, [before]):
                        moved = follow_hosts([item], [before], [after])[0]
                        if supported(moved, output_lines):
                            preserved = moved
                            break
            result['annotations'].append(preserved)
            continue
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
        if fixed_state is not None:
            result['labels'].append(deepcopy(label))
            continue
        move = displacement([(label["x"], label["y"])])
        result["labels"].extend(transform_labels([label], dx=move[0], dy=move[1]))
    rebuilt = RegionPicker(output_lines, output_curves)
    for path, (_old, room) in zip(moved_paths, rooms):
        matches = [new.area for candidate, new in rebuilt.records
                   if path_area(path.subtracted(candidate)) < EPS and path_area(candidate.subtracted(path)) < EPS]
        if not any(abs(area-room.area) <= max(EPS, room.area*1e-9) for area in matches):
            raise ValueError("wall_room_changed")
    return WallLayout(result, tuple(moves), tuple(room.area for _path, room in rooms), any(math.hypot(*move) > EPS for move in moves))
