"""A committed topology must not acquire cuts on its next edit or reload."""
from copy import deepcopy
from itertools import permutations
import random
import math

import pytest

from survey.plan_geometry import normalize_segments, rotate_degrees
from survey.plan_drawing import rectangle_segments
from survey.wall_editing import WallFaceIndex, relation
from survey.wall_properties import wall_style


def line(x1,y1,x2,y2,width=20,side=-1,material='brick'):
    return dict(x1=x1,y1=y1,x2=x2,y2=y2,color='#263238',
                wall=dict(width=width,side=side,material=material))


def signature(lines):
    return sorted((tuple(sorted(((round(s['x1'],7),round(s['y1'],7)),
                                (round(s['x2'],7),round(s['y2'],7))))),s['color'],wall_style(s)) for s in lines)


@pytest.mark.parametrize('angle', [0,35,90,175,231])
@pytest.mark.parametrize('geometry', [
    [line(340,340,340,240,30),line(320,200,320,300),line(340,440,340,240,20,material='drywall')],
    [line(120,260,320,260),line(340,260,120,260),line(180,280,400,280,material='drywall')],
])
def test_offset_face_cuts_propagate_across_overlapping_profiles_in_one_pass(angle, geometry):
    original = rotate_degrees(deepcopy(geometry),angle,(400,400))
    expected = None
    for sequence in permutations(original):
        normalized,sources = normalize_segments(list(sequence),with_sources=True)
        actual = signature(normalized)
        assert actual == signature(normalize_segments(normalized))
        assert len(actual) == len(set(actual))
        assert all(source and set(source) <= set(range(len(sequence))) for source in sources)
        if expected is None:
            expected = actual
        assert actual == expected


def random_wall_graph(seed):
    rng = random.Random(seed)
    lines = []
    for _ in range(rng.randint(1,5)):
        x,y = rng.randrange(100,501,20),rng.randrange(100,501,20)
        for s in rectangle_segments(x,y,rng.choice((100,120,200)),rng.choice((100,200,220)),'#263238'):
            s['wall'] = dict(width=rng.choice((5,10,20,30)),side=-1,material=rng.choice(('brick','drywall')))
            lines.append(s)
    for _ in range(rng.randint(0,4)):
        s = rng.choice(lines)
        lo,hi = rng.choice((0,.2)),rng.choice((.5,.8,1))
        part = dict(s,x1=s['x1']+(s['x2']-s['x1'])*lo,y1=s['y1']+(s['y2']-s['y1'])*lo,
                    x2=s['x1']+(s['x2']-s['x1'])*hi,y2=s['y1']+(s['y2']-s['y1'])*hi)
        if rng.random() < .5:
            part = dict(part,x1=part['x2'],x2=part['x1'],y1=part['y2'],y2=part['y1'],wall=dict(part['wall'],side=-part['wall']['side']))
        lines.append(part)
    return rotate_degrees(lines,rng.choice((0,35,90,175,231)),(400,400))


@pytest.mark.parametrize('seed', range(120))
def test_generated_overlap_graph_is_stable_and_spatial_matches_equal_brute_force(seed):
    lines = random_wall_graph(seed)
    before = deepcopy(lines)
    normalized = normalize_segments(lines)
    assert signature(normalized) == signature(normalize_segments(normalized))
    assert lines == before
    faces = WallFaceIndex(normalized)
    for i,a in enumerate(normalized):
        expected = {j for j,b in enumerate(normalized) if i != j and relation(a,b) is not None}
        assert set(faces.matches[i]) == expected


def test_spatial_pruning_keeps_long_nearly_parallel_faces_and_width_tolerance():
    a = line(0,0,100000,0)
    b = line(100000,-20,0,-20.0000001,width=20.0000005)
    faces = WallFaceIndex([a,b])
    assert set(faces.matches[0]) == {1} and set(faces.matches[1]) == {0}


@pytest.mark.parametrize('angle', [0,35,90])
@pytest.mark.parametrize('depth', [5,20,30])
@pytest.mark.parametrize('colored', [False,True])
def test_repeated_attach_delete_cycles_leave_no_duplicate_corner_fragments(angle, depth, colored):
    from PySide6.QtCore import QRectF
    from survey.wall_layout import plan_wall_layout
    from survey.wall_sides import stage_structure,apply_side_widths
    from survey.wall_editing import paired_lines,remove_wall_faces
    from survey.plan_faces import RegionPicker
    bounds = QRectF(0,0,3000,3000)
    base = dict(segments=rectangle_segments(600,600,200,200,'#263238'),curves=[],labels=[],annotations=[])
    original = plan_wall_layout(base,range(4),(),20,bounds).state
    for s in original['segments']:
        s['wall'].update(material='reinforced_concrete',priority=True)
    original['segments'] = rotate_degrees(original['segments'],angle,(700,700))
    expected = signature(original['segments'])
    current = deepcopy(original)
    for _ in range(3):
        new = rotate_degrees(rectangle_segments(380,580,200,240,'#cc3300' if colored else '#263238'),angle,(700,700))
        staged,sides,anchor = stage_structure(current,new)
        values = {s.index:s.shape.get('wall',{}).get('width',depth) for s in sides}
        decorations = {s.index:dict(material=s.shape.get('wall',{}).get('material','brick')) for s in sides}
        built = apply_side_widths(staged,sides,values,bounds,anchor=anchor,appearances=decorations,fixed_state=current).state
        records = RegionPicker(built['segments'],[]).records
        assert len(records) == 2
        added = next(r for _p,r in records if abs(r.area-48000) < .01)
        targets = [i for i in added.lines if len(paired_lines(built['segments'],i)) == 1]
        current = dict(original,segments=normalize_segments(remove_wall_faces(built['segments'],targets)))
        assert signature(current['segments']) == expected


def test_projection_of_a_collapsed_fragment_is_a_finite_endpoint():
    from survey.planar_geometry import point_projection
    assert point_projection((10,20),(1,2),(1,2)) == (1,2)


@pytest.mark.parametrize('reverse', [False,True])
def test_collinear_wall_fragments_join_across_direction_rounding_boundaries(reverse):
    angle = math.degrees(math.asin(.678901235))
    lines = rotate_degrees([line(100,100,200,100),line(200,100,300,100)],angle,(100,100))
    if reverse:
        s = lines[1]
        lines[1] = dict(s,x1=s['x2'],y1=s['y2'],x2=s['x1'],y2=s['y1'],wall=dict(s['wall'],side=-s['wall']['side']))
    assert wall_style(lines[0]) != wall_style(lines[1])  # Rounded normals straddle the old key boundary.
    normalized,sources = normalize_segments(lines,with_sources=True)
    assert len(normalized) == 1 and sources == [frozenset((0,1))]
    assert math.dist((normalized[0]['x1'],normalized[0]['y1']),
                     (normalized[0]['x2'],normalized[0]['y2'])) == pytest.approx(200)
