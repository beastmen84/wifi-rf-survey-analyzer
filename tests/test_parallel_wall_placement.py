"""Two fixed parallel supports accept an exact fit, never displace a neighbor."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog

from qt_ui.qt_wall_sides import WallSidesDialog, edit_wall_sides
from survey.plan_faces import RegionPicker
from survey.plan_geometry import rotate_degrees, translate_segments
from survey.plan_labels import transform_labels
from survey.wall_sides import stage_structure, apply_side_widths
from tests.test_blank_plan import create_survey
from tests.test_capture_adapter import window, qt_app
from tests.test_rectangle_design import editor
from tests.test_wall_thickness import rectangle, state, BOUNDS
from tests.test_plan_annotations import aperture, marker
from tests.test_plan_text_fill import label


def neighbors(left_width=20, right_width=20):
    lines = [dict(s,wall=dict(width=width,side=-1,material='reinforced_concrete',priority=True))
             for width,x in ((left_width,100),(right_width,500))
             for s in rectangle(x,100,200,600)]
    return state(lines)


def assert_neighbors_fixed(before, after):
    old = RegionPicker(before['segments'],before['curves']).records
    new = RegionPicker(after['segments'],after['curves']).records
    assert len(new) == len(old)+1
    assert all(any(candidate.boundingRect().getRect() == pytest.approx(path.boundingRect().getRect())
                   and r.area == pytest.approx(room.area) for candidate,r in new) for path,room in old)


@pytest.mark.parametrize('angle', [0,35,90,180])
@pytest.mark.parametrize('widths', [(20,20),(10,30)])
def test_exact_fit_is_translated_between_parallel_faces_without_resizing(qt_app, angle, widths):
    original = neighbors(*widths)
    new = rectangle(300,250,200-sum(widths),200)
    original['segments'] = rotate_degrees(original['segments'],angle,(500,500))
    new = rotate_degrees(new,angle,(500,500))
    if angle == 35:
        original['segments'] = translate_segments(original['segments'],300,300)
        new = translate_segments(new,300,300)
    before = deepcopy(original)
    staged,sides,anchor = stage_structure(original,new)
    result = apply_side_widths(staged,sides,{s.index:s.shape.get('wall',{}).get('width',0) for s in sides},
                               BOUNDS,anchor=anchor,fixed_state=original)
    assert_neighbors_fixed(original,result.state)
    areas = sorted(r.area for _p,r in RegionPicker(result.state['segments'],[]).records)
    assert areas == pytest.approx(sorted([120000,120000,(200-sum(widths))*200]))
    assert len([s for s in sides if s.shared]) == 2
    assert original == before


@pytest.mark.parametrize('width', [161,180,200])
def test_rectangle_wider_than_clear_gap_is_rejected_without_changes(qt_app, width):
    original = neighbors()
    before = deepcopy(original)
    with pytest.raises(ValueError):
        staged,sides,anchor = stage_structure(original,rectangle(300,250,width,200))
        apply_side_widths(staged,sides,{s.index:s.shape.get('wall',{}).get('width',0) for s in sides},
                          BOUNDS,anchor=anchor,fixed_state=original)
    assert original == before


@pytest.mark.parametrize('outcome', ['apply','cancel'])
def test_direct_placement_reviews_two_shared_faces_and_preserves_history(editor, tmp_path, outcome):
    owner,drawing = editor
    create_survey(owner,width=36,height=24)
    owner.plan_tools.set_open(True)
    original = neighbors()
    drawing.store(original['segments'])
    before,count = deepcopy(drawing.snapshot()),len(drawing.undo_stack)
    def review(dialog):
        assert dialog.candidate is not None and dialog.apply_button.isEnabled()
        assert len([s for s in dialog.sides if s.shared]) == 2
        assert drawing.snapshot() == before
        return QDialog.DialogCode.Accepted if outcome == 'apply' else QDialog.DialogCode.Rejected
    with patch.object(WallSidesDialog,'exec',review):
        assert drawing.commit(QRectF(300,250,160,200)) == (outcome == 'apply'), owner.status.currentMessage()
    if outcome == 'cancel':
        assert drawing.snapshot() == before and len(drawing.undo_stack) == count
        return
    after = deepcopy(drawing.snapshot())
    assert_neighbors_fixed(original,after)
    assert len(drawing.undo_stack) == count+1
    assert drawing.undo() and drawing.snapshot() == before
    assert drawing.redo() and drawing.snapshot() == after
    owner.session.csv_file = str(tmp_path/'parallel-fit.csv')
    assert owner.save_survey() and owner.open_survey(owner.session.csv_file)
    assert drawing.segments() == after['segments']


@pytest.mark.parametrize('width', [160,180])
def test_move_preview_respects_faces_and_flags_conflicting_opposite_supports(editor, qt_app, width):
    owner,drawing = editor
    create_survey(owner,width=36,height=24)
    owner.plan_tools.set_open(True)
    moving = rectangle(1000,250,width,200)
    drawing.store(neighbors()['segments']+moving)
    owner.plan_tools.select_tool('select')
    drawing.view.set_zoom(2)
    drawing.view.centerOn(1050,350)
    qt_app.processEvents()
    def at(x,y):
        return drawing.view.mapFromScene(QPointF(x,y))
    QTest.mouseClick(drawing.view.viewport(),Qt.MouseButton.RightButton,pos=at(1020,400))
    selection = drawing.selection
    before = deepcopy(drawing.snapshot())
    assert selection.begin_move()
    selection.update_move(QPointF(at(330,400)),bypass=True)
    assert selection.move_wall_invalid == (width != 160)
    if width == 160:
        box = RegionPicker(selection.move_preview,[]).records[0][0].boundingRect()
        assert box.left() == pytest.approx(320)
        assert box.width() == pytest.approx(160) and box.height() == pytest.approx(200)
    assert drawing.snapshot() == before
    selection.cancel()
    assert drawing.snapshot() == before


@pytest.mark.parametrize('balanced', [False,True])
def test_editing_center_room_cannot_push_either_neighbor_to_make_space(editor, balanced):
    owner,drawing = editor
    create_survey(owner,width=36,height=24)
    owner.plan_tools.set_open(True)
    central = [dict(s,wall=dict(width=20,side=-1)) for s in rectangle(320,250,160,200)]
    drawing.store(neighbors()['segments']+central)
    room = next(r for p,r in RegionPicker(drawing.segments(),[]).records if p.boundingRect() == QRectF(320,250,160,200))
    before,count = deepcopy(drawing.snapshot()),len(drawing.undo_stack)
    def review(dialog):
        assert len(dialog.fixed_rooms) == 2 and dialog.candidate is not None
        rows = sorted((i for i,s in enumerate(dialog.sides) if s.shared),key=lambda i:dialog.sides[i].shape['x1'])
        assert len(rows) == 2
        dialog.spins[rows[0]].setValue(30/owner.get_px_per_meter())
        assert dialog.candidate is None and not dialog.apply_button.isEnabled()
        assert dialog.status.text() == owner.tr('wall_fixed_fit')
        assert dialog.notice.text() == owner.tr('wall_shared_fixed_changed')
        dialog.confirm_shared.setChecked(True)
        assert not dialog.apply_button.isEnabled()
        if balanced:
            dialog.spins[rows[1]].setValue(10/owner.get_px_per_meter())
            assert dialog.candidate is not None
            dialog.confirm_shared.setChecked(True)
            assert dialog.apply_button.isEnabled()
        return QDialog.DialogCode.Accepted  # An invalid proposal still cannot apply.
    with patch.object(WallSidesDialog,'exec',review):
        assert edit_wall_sides(owner,room) == balanced
    if balanced:
        assert_neighbors_fixed(neighbors(),drawing.snapshot())
        assert any(p.boundingRect() == QRectF(330,250,160,200) for p,_r in RegionPicker(drawing.segments(),[]).records)
        assert len(drawing.undo_stack) == count+1
    else:
        assert drawing.snapshot() == before and len(drawing.undo_stack) == count


@pytest.mark.parametrize('width', [160,180,200])
def test_moving_independent_room_uses_fixed_faces_and_rejects_oversize(editor, qt_app, width):
    owner,drawing = editor
    create_survey(owner,width=36,height=24)
    owner.plan_tools.set_open(True)
    original = neighbors()
    moving = [dict(s,wall=dict(width=5,side=-1,material='brick')) for s in rectangle(1000,250,width,200)]
    contents = [aperture(x1=1040,y1=250,x2=1080,y2=250),
                marker(points=[[1050,300],[1090,300]])]
    drawing.store(original['segments']+moving,labels=[dict(label(),x=1080,y=350)],annotations=contents)
    owner.plan_tools.select_tool('select')
    drawing.view.centerOn(1050,350)
    qt_app.processEvents()
    QTest.mouseClick(drawing.view.viewport(),Qt.MouseButton.RightButton,
                     pos=drawing.view.mapFromScene(QPointF(1020,400)))
    selection = drawing.selection
    assert len(selection.selected) == 4 and len(selection.selected_annotations) == 2
    before,count = deepcopy(drawing.snapshot()),len(drawing.undo_stack)
    assert selection.begin_move()
    placed = translate_segments(moving,-700,0)
    assert selection.apply_transformed(placed,transform_labels(selection.selected_texts(),dx=-700)) == (width == 160), owner.status.currentMessage()
    if width != 160:
        assert drawing.snapshot() == before and len(drawing.undo_stack) == count
        assert selection.moving
        return
    after = deepcopy(drawing.snapshot())
    assert_neighbors_fixed(original,after)
    rooms = RegionPicker(after['segments'],[]).records
    assert any(p.boundingRect() == QRectF(320,250,160,200) for p,_r in rooms)
    shared = [s for s in after['segments'] if s['x1'] == s['x2'] and s['x1'] in (320,480)]
    assert len(shared) == 2
    assert all(s['wall']['width'] == 20 and s['wall']['material'] == 'reinforced_concrete' for s in shared)
    assert after['labels'][0]['x'] == pytest.approx(400)
    assert after['annotations'][0]['x1'] == pytest.approx(360)
    assert len(drawing.undo_stack) == count+1
    assert drawing.undo() and drawing.snapshot() == before
    assert drawing.redo() and drawing.snapshot() == after
