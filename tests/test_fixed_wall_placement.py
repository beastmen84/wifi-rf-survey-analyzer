"""New forms move beyond an existing wall; its reference and depth stay put."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QDialog

from qt_ui.qt_wall_sides import WallSidesDialog, place_structure
from survey.plan_faces import RegionPicker
from survey.plan_annotations import supported
from survey.plan_geometry import rotate_degrees, translate_segments
from survey.wall_geometry import wall_solids, path_area, normal
from survey.wall_layout import plan_wall_layout
from survey.wall_sides import stage_structure, apply_side_widths
from tests.test_capture_adapter import window, qt_app
from tests.test_rectangle_design import editor
from tests.test_wall_thickness import rectangle,state,BOUNDS
from tests.test_plan_annotations import marker,aperture
from tests.test_plan_text_fill import label


def host(side=1,width=20,y=400):
    return dict(x1=100,y1=y,x2=700,y2=y,color='#263238',
                wall=dict(width=width,side=side,material='drywall',priority=True))


def place(original, new_lines, width=None):
    staged,sides,anchor = stage_structure(original,new_lines)
    values = {s.index:s.shape.get('wall',{}).get('width',0) for s in sides}
    if width is not None:
        values.update({s.index:width for s in sides if s.shared})
    return apply_side_widths(staged,sides,values,BOUNDS,anchor=anchor,fixed_state=original)


@pytest.mark.parametrize('side', [-1,1])
@pytest.mark.parametrize('width', [10,20])
@pytest.mark.parametrize('angle', [0,35,90,180])
def test_complete_form_clears_the_wall_without_reversing_or_moving_it(qt_app, side, width, angle):
    wall = host(side,width)
    new = rectangle(300,400 if side == 1 else 200,200,200)
    wall = rotate_degrees([wall],angle,(500,500))[0]
    new = rotate_degrees(new,angle,(500,500))
    original = state([wall])
    before = deepcopy(original)
    result = place(original,new)
    nx,ny = normal(wall,wall['wall']['side'])
    expected = RegionPicker(translate_segments(new,nx*width,ny*width),[]).records[0][0]
    room = RegionPicker(result.state['segments'],[]).records
    assert len(room) == 1 and room[0][1].area == pytest.approx(40000)
    assert room[0][0].boundingRect().getRect() == pytest.approx(expected.boundingRect().getRect())
    assert sum(path_area(p) for _,p in wall_solids(result.state['segments'])) == pytest.approx(600*width,abs=.005)
    # The original reference still supports its full run at the same location.
    reference = aperture(x1=wall['x1'],y1=wall['y1'],x2=wall['x2'],y2=wall['y2'])
    assert supported(reference,result.state['segments'])
    assert original == before


def test_three_new_sides_also_close_against_the_fixed_open_wall(qt_app):
    original = state([host()])
    result = place(original,rectangle(300,400,200,200)[1:])
    room = RegionPicker(result.state['segments'],[]).records[0]
    assert room[0].boundingRect().top() == pytest.approx(420)
    assert room[1].area == pytest.approx(40000)
    assert any(l['y1'] == l['y2'] == 400 and l['wall']['side'] == 1 for l in result.state['segments'] if l.get('wall'))


@pytest.mark.parametrize('dual', [False,True])
def test_existing_opposite_face_does_not_reduce_the_requested_room_size(qt_app, dual):
    lines = [host()]
    if dual:
        lines.append(dict(host(),y1=420,y2=420,wall=dict(width=20,side=-1,material='drywall',priority=True)))
    original = state(lines)
    for width in (20,30):
        result = place(original,rectangle(300,400,200,200),width)
        room = RegionPicker(result.state['segments'],[]).records[0]
        assert room[0].boundingRect().getRect() == pytest.approx((300,400+width,200,200))
        assert room[1].area == pytest.approx(40000)
        assert supported(aperture(x1=100,y1=400,x2=700,y2=400),result.state['segments'])


def test_closing_on_the_clear_side_does_not_shift_the_form(qt_app):
    result = place(state([host()]),rectangle(300,200,200,200))
    assert RegionPicker(result.state['segments'],[]).records[0][0].boundingRect().getRect() == pytest.approx((300,200,200,200))


def test_existing_closed_rooms_and_objects_remain_fixed(qt_app):
    source = state(rectangle(300,200,300,300)+rectangle(900,200,200,200))
    original = plan_wall_layout(source,range(len(source['segments'])),(),20,BOUNDS).state
    original['annotations'] = [marker(points=[[650,300],[680,300]])]
    original['labels'] = [dict(label(),x=640,y=320)]
    result = place(original,rectangle(600,250,100,100))
    records = RegionPicker(result.state['segments'],[]).records
    for path,_room in RegionPicker(original['segments'],[]).records:
        assert any(path.boundingRect().getRect() == pytest.approx(p.boundingRect().getRect()) for p,_r in records)
    assert result.state['annotations'] == original['annotations']
    assert result.state['labels'] == original['labels']


def test_cannot_force_an_unchanged_size_between_two_fixed_walls(qt_app):
    original = state([host(),host(-1,y=600)])
    before = deepcopy(original)
    with pytest.raises(ValueError,match='wall_constraints_conflict'):
        place(original,rectangle(300,400,200,200))
    assert original == before


def test_adjustment_outside_the_sheet_is_rejected_even_for_thin_sides(qt_app):
    original = state([host(y=1400)])
    with pytest.raises(ValueError,match='wall_outside'):
        place(original,rectangle(300,1400,200,90))


def test_outer_face_opening_is_rehosted_when_shared_depth_changes(qt_app):
    original = state([host(),dict(host(),y1=420,y2=420,
                                 wall=dict(width=20,side=-1,material='drywall',priority=True))],
                     annotations=[aperture(x1=350,y1=420,x2=400,y2=420,variant='frame')])
    result = place(original,rectangle(300,400,200,200),30)
    assert len(result.state['annotations']) == 1
    item = result.state['annotations'][0]
    assert item['id'] == original['annotations'][0]['id']
    assert item['x1'] == 350 and item['x2'] == 400
    assert item['y1'] == item['y2'] == pytest.approx(430)
    assert supported(item,result.state['segments'])


def test_preview_tracks_extra_depth_without_moving_the_original_reference(editor):
    owner,_drawing = editor
    original = state([host(y=200)])
    staged,sides,anchor = stage_structure(original,rectangle(250,200,200,200))
    dialog = WallSidesDialog(owner,staged,sides,anchor,placing=True,fixed_state=original)
    row = next(i for i,s in enumerate(sides) if s.shared)
    dialog.spins[row].setValue(30/owner.get_px_per_meter())
    assert dialog.candidate is not None
    shape = dialog.preview_shape(sides[row])
    assert shape['y1'] == shape['y2'] == pytest.approx(230)
    assert supported(aperture(x1=100,y1=200,x2=700,y2=200),dialog.result.state['segments'])
    assert not dialog.apply_button.isEnabled()
    dialog.confirm_shared.setChecked(True)
    assert dialog.apply_button.isEnabled()
    dialog.reject()
    dialog.deleteLater()


@pytest.mark.parametrize('outcome', ['apply','cancel'])
def test_preview_and_placement_show_the_new_form_below_the_unchanged_wall(editor,tmp_path,outcome):
    owner,drawing = editor
    original = state([host(y=200)],annotations=[marker(points=[[300,300],[330,300]])])
    drawing.store(original['segments'],annotations=original['annotations'])
    before,count = deepcopy(drawing.snapshot()),len(drawing.undo_stack)
    def review(dialog):
        assert dialog.candidate is not None
        shared = next(s for s in dialog.sides if s.shared)
        shown = dialog.preview_shape(shared)
        assert shown['y1'] == shown['y2'] == pytest.approx(220)
        assert drawing.snapshot() == before
        return QDialog.DialogCode.Accepted if outcome == 'apply' else QDialog.DialogCode.Rejected
    with patch.object(WallSidesDialog,'exec',review):
        assert place_structure(drawing,rectangle(250,200,200,200)) == (outcome == 'apply')
    if outcome == 'cancel':
        assert drawing.snapshot() == before and len(drawing.undo_stack) == count
        return
    after = deepcopy(drawing.snapshot())
    assert len(drawing.undo_stack) == count+1
    assert drawing.annotations() == before['annotations']
    assert drawing.undo() and drawing.snapshot() == before
    assert drawing.redo() and drawing.snapshot() == after
    owner.session.csv_file = str(tmp_path/'fixed-support.csv')
    assert owner.save_survey() and owner.open_survey(owner.session.csv_file)
    assert drawing.segments() == after['segments']
