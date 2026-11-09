"""Covered corner extensions form one side; real shared T spans stay separate."""
from copy import deepcopy
import math

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest

from survey.plan_faces import RegionPicker
from survey.plan_geometry import normalize_segments, rotate_degrees
from survey.plan_erasing import nearest_segment
from survey.wall_layout import plan_wall_layout
from survey.wall_sides import stage_structure, apply_side_widths
from survey.wall_editing import physical_faces, remove_wall_faces
from survey.wall_geometry import wall_solids, path_area
from tests.test_capture_adapter import window, qt_app
from tests.test_rectangle_design import editor
from tests.test_plan_annotations import at
from tests.test_wall_thickness import rectangle, state, BOUNDS


def attached(top=180, bottom=420, right=380):
    original = plan_wall_layout(state(rectangle(400,200)), range(4), (), 20, BOUNDS).state
    staged, sides, anchor = stage_structure(original, rectangle(right-200, top, 200, bottom-top))
    return apply_side_widths(staged, sides, {s.index:s.shape.get('wall',{}).get('width',20) for s in sides},
                             BOUNDS, anchor=anchor).state['segments']


@pytest.mark.parametrize('right', [380,400])
@pytest.mark.parametrize('top,bottom', [(180,400),(200,420),(180,420)])
@pytest.mark.parametrize('angle', [0,35,90])
def test_covered_end_fragments_join_their_side_without_changing_rooms(qt_app, right, top, bottom, angle):
    lines = attached(top,bottom,right)
    assert len(lines) == 8
    assert not any(math.hypot(l['x2']-l['x1'], l['y2']-l['y1']) <= 20.0001 for l in lines)
    rotated = rotate_degrees(lines,angle,(400,300))
    again = normalize_segments(rotated)
    assert len(again) == 8
    assert sorted(r.area for _,r in RegionPicker(again,[]).records) == pytest.approx([40000,200*(bottom-top)])
    assert sum(path_area(p) for _,p in wall_solids(again)) == pytest.approx(
        sum(path_area(p) for _,p in wall_solids(rotated)), abs=.02)


def test_real_t_junction_keeps_two_independent_shared_spans(qt_app):
    source = state(rectangle(w=400)+rectangle(y=300)+rectangle(x=300,y=300))
    lines = plan_wall_layout(source, range(len(source['segments'])), (), 20, BOUNDS).state['segments']
    left, right = nearest_segment(lines,200,310,1), nearest_segment(lines,400,310,1)
    assert len(physical_faces(lines,left)) == 2 and len(physical_faces(lines,right)) == 2
    assert not set(physical_faces(lines,left)) & set(physical_faces(lines,right))


def test_common_wall_deletion_keeps_the_outer_perimeter_closed(qt_app):
    lines = attached()
    index = nearest_segment(lines,390,300,1)
    targets = physical_faces(lines,index)
    assert len(targets) == 2
    left = normalize_segments(remove_wall_faces(lines,targets))
    assert len(RegionPicker(left,[]).records) == 1


def test_removing_the_added_room_cleans_its_covered_corner_extensions(qt_app):
    lines = attached()
    # Three exterior sides of the left room, retaining the shared wall.
    targets = [i for i,l in enumerate(lines) if min(l['x1'],l['x2']) < 380]
    left = normalize_segments(remove_wall_faces(lines,targets))
    assert len(left) == 4
    assert len(RegionPicker(left,[]).records) == 1
    assert not any(l['x1'] == l['x2'] == 380 for l in left)


def test_hidden_corner_is_not_pickable_as_an_independent_chip_and_history_restores_it(editor):
    owner, drawing = editor
    drawing.store(attached())
    owner.plan_tools.select_tool('select')
    selected, curves = drawing.selection.pick_stroke(QPointF(390,410))
    assert not curves and len(selected) == 2
    assert all(math.hypot(drawing.segments()[i]['x2']-drawing.segments()[i]['x1'],
                          drawing.segments()[i]['y2']-drawing.segments()[i]['y1']) > 20 for i in selected)
    before, count = deepcopy(drawing.snapshot()), len(drawing.undo_stack)
    drawing.selection.set_selected(selected)
    QTest.keyClick(owner, Qt.Key.Key_Delete)
    assert len(RegionPicker(drawing.segments(),[]).records) == 1
    assert len(drawing.undo_stack) == count+1
    assert drawing.undo() and drawing.snapshot() == before
