"""Per-side wall requests, inherited supports and atomic placement staging."""
from copy import deepcopy
from dataclasses import dataclass
import math

from survey.plan_curve_geometry import normalize_plan
from survey.wall_conversion import reference_regions
from survey.wall_editing import relation
from survey.wall_layout import plan_wall_layout, room_side, WallLayout
from survey.wall_geometry import validate_wall_bounds
from survey.planar_geometry import point_projection
from survey.wall_properties import copy_wall
from survey.wall_materials import appearance, validated_appearance


@dataclass(frozen=True)
class WallSide:
    index: int  # Lines followed by curves in the staged drawing.
    shape: dict
    shared: bool
    side: int
    open: bool = False


def wall_sides(state, indices, existing=()):
    lines, curves = state['segments'] or [], state['curves']
    shapes = [*lines, *curves]
    rooms = reference_regions(state).records
    selected = set(indices)
    def boundary(room):
        return set(room.lines) | {len(lines)+i for i in room.curves}
    preferred = max(rooms, key=lambda item:(len(boundary(item[1]) & selected), -len(boundary(item[1])-selected)))[0] if rooms else None
    result = []
    for index in indices:
        shape = shapes[index]
        owners = [path for path, r in rooms if index in (r.lines if index < len(lines) else [len(lines)+c for c in r.curves])]
        paired = index < len(lines) and any(j != index and relation(shape, other) for j, other in enumerate(lines))
        side = shape.get('wall', {}).get('side', 0)
        if not shape.get('wall', {}).get('reference') and preferred is not None and any(path == preferred for path in owners):
            side = room_side(shape, preferred)
        elif not side:
            side = room_side(shape, owners[0]) if owners else 1
        result.append(WallSide(index, shape, index in existing or len(owners) > 1 or bool(paired), side, not owners))
    return result


def stage_structure(state, new_lines=(), new_curves=()):
    old_lines, old_curves = state['segments'] or [], state['curves']
    lines, curves, line_sources, curve_sources = normalize_plan([*old_lines, *new_lines], [*old_curves, *new_curves], with_sources=True)
    indices, inherited = [], set()
    for offset, sources, old_count in ((0, line_sources, len(old_lines)), (len(lines), curve_sources, len(old_curves))):
        for i, source in enumerate(sources):
            if any(j >= old_count for j in source):
                indices.append(offset+i)
                if any(j < old_count for j in source):
                    inherited.add(offset+i)
    staged = dict(deepcopy(state), segments=lines, curves=curves)
    # A newly drawn face may coincide with the *outer* face of an existing
    # physical wall rather than its internal reference line.
    rooms = reference_regions(staged).records
    for index in indices:
        if index >= len(lines) or lines[index].get('wall'):
            continue
        line = lines[index]
        coincident = [old for old in old_lines if old.get('wall') and all(
            math.dist(p, point_projection(p,(old['x1'],old['y1']),(old['x2'],old['y2']))) < 1e-6
            for p in ((line['x1'],line['y1']),(line['x2'],line['y2'])))]
        if coincident:
            old = coincident[0]
            if len({s['wall']['width'] for s in coincident}) > 1:
                raise ValueError('wall_shared_width_conflict')
            if len({appearance(s['wall']) for s in coincident}) > 1:
                raise ValueError('wall_shared_material_conflict')
            reverse = (line['x2']-line['x1'])*(old['x2']-old['x1'])+(line['y2']-line['y1'])*(old['y2']-old['y1']) < 0
            copy_wall(old,line,reverse)
            line['color'] = old['color']  # A shared physical wall retains its existing style.
            inherited.add(index)
            continue
        owners = [path for path, room in rooms if index in room.lines]
        if not owners:
            continue
        side = room_side(line, owners[0])
        matches = []
        for old in old_lines:
            if not old.get('wall') or old['wall'].get('reference'):
                continue
            candidate = dict(line, wall=dict(old['wall'], side=side))
            if relation(candidate, old):
                matches.append(candidate['wall'])
        if matches:
            if len({m['width'] for m in matches}) != 1:
                raise ValueError('wall_shared_width_conflict')
            if len({appearance(m) for m in matches}) != 1:
                raise ValueError('wall_shared_material_conflict')
            line['wall'] = matches[0]
            inherited.add(index)
    # Inheritance can make differently colored duplicates one physical face.
    # Remap the piece selection through this final normalization, not by indices
    # from the first pass (which may now have disappeared).
    selected, previous_line_count = set(indices), len(lines)
    lines, curves, ls, cs = normalize_plan(lines,curves,with_sources=True)
    remapped, common = [], set()
    for offset,sources,source_offset in ((0,ls,0),(len(lines),cs,previous_line_count)):
        for i,group in enumerate(sources):
            source = {source_offset+j for j in group}
            if source & selected:
                remapped.append(offset+i)
                if source & inherited:
                    common.add(offset+i)
    indices, inherited = remapped, common
    staged.update(segments=lines,curves=curves)
    rooms = reference_regions(staged).records
    # Keep an already placed room fixed when the new room shares its boundary.
    old_rooms = reference_regions(state).records
    anchor = next((i for i, (path, _r) in enumerate(rooms)
                   if any(path == old_path for old_path, _old in old_rooms)), 0)
    return staged, wall_sides(staged, indices, inherited), anchor


def same_wall_faces(a, b):
    """Physical association ignores decorative material/style differences."""
    if 'kind' in a or 'kind' in b or not a.get('wall') or not b.get('wall'):
        return False
    if relation(a,b):
        return True
    from survey.wall_properties import wall_style
    def profile(shape):
        return dict(shape,wall={k:v for k,v in shape['wall'].items() if k not in ('material','pattern','priority')})
    if wall_style(profile(a)) != wall_style(profile(b)):
        return False
    return all(math.dist(p,point_projection(p,(b['x1'],b['y1']),(b['x2'],b['y2']))) < 1e-6
               for p in ((a['x1'],a['y1']),(a['x2'],a['y2'])))


def side_appearances(state, sides, requested):
    if set(requested) != {s.index for s in sides}:
        raise ValueError('wall_invalid_material')
    shapes = [*(state['segments'] or []), *state['curves']]
    requests = {i:validated_appearance(v) for i,v in requested.items()}
    changed = {i:v for i,v in requests.items() if appearance(v) != appearance(shapes[i].get('wall',{}))}
    # A material-only edit must update the other face of a shared physical wall.
    # Staged drawings are already split at overlap limits, so unrelated spans stay.
    propagated = {}
    for i,value in changed.items():
        for j,other in enumerate(shapes):
            if j == i or same_wall_faces(shapes[i],other):
                if j in propagated and appearance(propagated[j]) != appearance(value):
                    raise ValueError('wall_shared_material_conflict')
                propagated[j] = value
    return {**requests, **propagated}


def side_priorities(state, sides, requested):
    if set(requested) != {s.index for s in sides} or any(type(v) is not bool for v in requested.values()):
        raise ValueError('wall_invalid_priority')
    shapes = [*(state['segments'] or []), *state['curves']]
    propagated = {}
    for i,value in requested.items():
        if value == shapes[i].get('wall', {}).get('priority', False):
            continue
        for j,other in enumerate(shapes):
            if j == i or same_wall_faces(shapes[i], other):
                if j in propagated and propagated[j] != value:
                    raise ValueError('wall_invalid_priority')
                propagated[j] = value
    return {**requested, **propagated}


def apply_side_widths(state, sides, values, bounds, *, anchor=0, appearances=None, priorities=None):
    count = len(state['segments'] or [])
    indices = [s.index for s in sides]
    if set(values) != set(indices):
        raise ValueError('wall_invalid_width')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 10000 for v in values.values()):
        raise ValueError('wall_invalid_width')
    decorations = side_appearances(state,sides,appearances) if appearances is not None else {}
    priorities = side_priorities(state,sides,priorities) if priorities is not None else {}
    if any(s.get('wall', {}).get('reference') for s in [*(state['segments'] or []), *state['curves']]):
        # Existing converted documents retain their explicit reference profiles.
        from survey.wall_properties import validated_wall
        result = deepcopy(state)
        shapes = [*(result['segments'] or []), *result['curves']]
        for side in sides:
            value, shape = values[side.index], shapes[side.index]
            if side.index < count and value != shape.get('wall',{}).get('width',0) and any(j != side.index and relation(shape,other) for j,other in enumerate(shapes[:count])):
                raise ValueError('wall_reference_mode')
            profile = shape.pop('wall', None)
            if value:
                shape['wall'] = validated_wall(dict(profile or dict(side=side.side, reference='face'), width=value))
        for index,decoration in decorations.items():
            if shapes[index].get('wall'):
                for key in ('material','pattern'):
                    shapes[index]['wall'].pop(key,None)
                shapes[index]['wall'].update(decoration)
        for index,priority in priorities.items():
            if shapes[index].get('wall'):
                shapes[index]['wall'].pop('priority', None)
                if priority:
                    shapes[index]['wall']['priority'] = True
        validate_wall_bounds(result['segments'] or [], result['curves'], bounds)
        return WallLayout(result, (), (), False)
    return plan_wall_layout(state, [i for i in indices if i < count], [i-count for i in indices if i >= count],
        0, bounds, anchor=anchor, widths=values, open_sides={s.index:s.side for s in sides}, appearances=decorations, priorities=priorities)
