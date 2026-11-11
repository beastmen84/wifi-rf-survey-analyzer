"""Per-side construction, inherited dividers and atomic native gestures."""
from copy import deepcopy
from unittest.mock import patch
import math

import pytest
from PySide6.QtCore import QPointF, QRectF, QLineF, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QApplication
from survey.wall_sides import stage_structure, wall_sides, apply_side_widths
from survey.wall_layout import plan_wall_layout
from survey.plan_faces import RegionPicker
from qt_ui.qt_wall_sides import WallSidesDialog, place_structure, edit_wall_sides
from tests.test_wall_thickness import rectangle, state, BOUNDS
from tests.test_capture_adapter import window, qt_app
from tests.test_rectangle_design import editor, drag


def test_per_side_values_preserve_internal_rectangle_and_different_depths(qt_app):
    staged, sides, anchor = stage_structure(state(), rectangle())
    assert len(sides) == 4 and not any(s.shared for s in sides)
    result = apply_side_widths(staged, sides, dict(zip([s.index for s in sides], [10,20,30,0])), BOUNDS, anchor=anchor)
    assert len(RegionPicker(result.state['segments'], []).records) == 1
    assert result.areas == (40000,) and not result.changed_positions
    assert [l.get('wall',{}).get('width',0) for l in result.state['segments']] == [10,20,30,0]


@pytest.mark.parametrize('width', [0, 10, 20, 30])
def test_new_attached_room_inherits_common_side_and_propagates_changes(qt_app, width):
    old = plan_wall_layout(state(rectangle()), range(4), (), 20, BOUNDS).state
    staged, sides, anchor = stage_structure(old, rectangle(x=300))
    assert len(sides) == 4
    common = [s for s in sides if s.shared]
    assert len(common) == 1 and common[0].shape['wall']['width'] == 20
    assert all(s.shape.get('wall') is None for s in sides if not s.shared)
    values = {s.index:s.shape.get('wall',{}).get('width',0) for s in sides}
    values[common[0].index] = width
    result = apply_side_widths(staged, sides, values, BOUNDS, anchor=anchor)
    rooms = sorted((p.boundingRect() for p,_r in RegionPicker(result.state['segments'],[]).records),key=lambda b:b.left())
    assert len(rooms) == 2 and rooms[0] == QRectF(100,100,200,200)
    assert rooms[1].left()-rooms[0].right() == pytest.approx(width)
    assert all(r.area == 40000 for _p,r in RegionPicker(result.state['segments'],[]).records)
    assert old['segments'][1]['wall']['width'] == 20  # Source never changed.


def test_edit_existing_shared_divider_updates_both_faces(qt_app):
    built = plan_wall_layout(state(rectangle()+rectangle(x=300)),range(7),(),20,BOUNDS).state
    room = RegionPicker(built['segments'],[]).records[0][1]
    sides = wall_sides(built,room.lines)
    shared = [s for s in sides if s.shared]
    assert shared
    result = apply_side_widths(built,sides,{s.index:30 if s.shared else s.shape['wall']['width'] for s in sides},BOUNDS)
    assert len([s for s in result.state['segments'] if s.get('wall',{}).get('width') == 30]) == 2


def test_attachment_to_existing_outer_face_inherits_width_without_moving_room(qt_app):
    old = plan_wall_layout(state(rectangle()),range(4),(),20,BOUNDS).state
    staged,sides,anchor = stage_structure(old,rectangle(x=320))
    shared = [s for s in sides if s.shared]
    assert len(shared) == 1 and shared[0].shape['wall']['width'] == 20
    values = {s.index:s.shape.get('wall',{}).get('width',0) for s in sides}
    result = apply_side_widths(staged,sides,values,BOUNDS,anchor=anchor)
    assert not result.changed_positions
    values[shared[0].index] = 30
    changed = apply_side_widths(staged,sides,values,BOUNDS,anchor=anchor)
    rooms = sorted(p.boundingRect().left() for p,r in RegionPicker(changed.state['segments'],[]).records)
    assert rooms == [100,330]


def test_shared_side_uses_existing_depth_even_when_new_stroke_color_differs(qt_app):
    old = plan_wall_layout(state(rectangle()),range(4),(),20,BOUNDS).state
    new = [dict(s,color='#cc3300') for s in rectangle(x=300)]
    staged,sides,anchor = stage_structure(old,new)
    shared = [s for s in sides if s.shared]
    assert shared and all(s.shape.get('wall',{}).get('width') == 20 for s in shared)
    result = apply_side_widths(staged,sides,{s.index:s.shape.get('wall',{}).get('width',0) for s in sides},BOUNDS,anchor=anchor)
    assert len(RegionPicker(result.state['segments'],[]).records) == 2


def test_partial_common_side_is_cut_and_only_overlap_inherits_existing_thickness(qt_app):
    old = plan_wall_layout(state(rectangle()),range(4),(),20,BOUNDS).state
    staged,sides,anchor = stage_structure(old,rectangle(x=300,y=200,w=200,h=200))
    assert any(s.shared and s.shape.get('wall',{}).get('width') == 20 for s in sides)
    result = apply_side_widths(staged,sides,{s.index:s.shape.get('wall',{}).get('width',0) for s in sides},BOUNDS,anchor=anchor)
    assert len(RegionPicker(result.state['segments'],[]).records) == 2


def test_imperial_review_preserves_exact_values_and_uses_inches_free_depth_input(editor):
    owner,drawing = editor
    owner.measurement_system = 'imperial'
    staged,sides,anchor = stage_structure(state(),rectangle())
    for s in sides:
        s.shape['wall'] = dict(width=7.123456,side=s.side)
    dialog = WallSidesDialog(owner,staged,sides,anchor)
    assert dialog.candidate and all(v == 7.123456 for v in dialog.values.values())
    dialog.try_accept()
    assert all(s['wall']['width'] == 7.123456 for s in dialog.result.state['segments'])
    dialog.deleteLater()


def test_accept_reuses_validated_candidate_without_rebuilding_layout(editor):
    owner,_drawing = editor
    staged,sides,anchor = stage_structure(state(),rectangle())
    dialog = WallSidesDialog(owner,staged,sides,anchor)
    candidate = dialog.candidate
    with patch('qt_ui.qt_wall_sides.apply_side_widths',side_effect=AssertionError('layout already validated')):
        dialog.try_accept()
    assert dialog.candidate is candidate
    assert QDialog.result(dialog) == QDialog.DialogCode.Accepted
    dialog.deleteLater()


def test_accept_commits_pending_keyboard_depth_and_revalidates_it(editor):
    owner,_drawing = editor
    staged,sides,anchor = stage_structure(state(),rectangle())
    dialog = WallSidesDialog(owner,staged,sides,anchor)
    spin = dialog.spins[0]
    spin.lineEdit().setText(spin.locale().toString(.2,'f',2)+spin.suffix())
    assert dialog.values[sides[0].index] == 0
    dialog.try_accept()
    assert dialog.values[sides[0].index] == pytest.approx(10)
    assert QDialog.result(dialog) == QDialog.DialogCode.Accepted
    assert dialog.candidate is not None
    assert any(s.get('wall',{}).get('width') == 10 for s in dialog.result.state['segments'])
    dialog.deleteLater()


def test_accept_pending_depth_cannot_bypass_physical_bounds(editor):
    owner,_drawing = editor
    staged,sides,anchor = stage_structure(state(),rectangle(0,0))
    dialog = WallSidesDialog(owner,staged,sides,anchor)
    assert dialog.candidate is not None
    spin = dialog.spins[0]
    spin.lineEdit().setText(spin.locale().toString(.2,'f',2)+spin.suffix())
    dialog.try_accept()
    assert dialog.error == 'wall_outside' and dialog.candidate is None
    assert QDialog.result(dialog) != QDialog.DialogCode.Accepted
    dialog.deleteLater()


@pytest.mark.parametrize('kind', ['line','circle','arc'])
def test_open_or_round_structure_has_editable_side(qt_app, kind):
    line = dict(x1=100,y1=200,x2=400,y2=200,color='#263238')
    curve = dict(kind='circle',cx=400,cy=400,radius=100,phase=0,color='#263238') if kind=='circle' else dict(kind='arc',x1=100,y1=200,x2=400,y2=200,height=40,color='#263238')
    staged,sides,anchor = stage_structure(state(),[line] if kind=='line' else [],[] if kind=='line' else [curve])
    assert len(sides) == 1
    result = apply_side_widths(staged,sides,{sides[0].index:10},BOUNDS,anchor=anchor)
    assert (result.state['segments'] or result.state['curves'])[0]['wall']['width'] == 10


@pytest.mark.parametrize('outcome', ['apply','cancel','stale'])
def test_placement_is_one_transaction_and_keeps_history_clean_on_cancel(editor, outcome):
    owner,drawing = editor
    before = deepcopy(owner.session.metadata)
    history = len(drawing.undo_stack)
    def review(dialog):
        assert dialog.placing and len(dialog.sides) == 4
        assert owner.session.metadata == before  # Nothing stored before review.
        dialog.spins[0].setValue(.2)
        assert dialog.candidate
        if outcome == 'stale':
            owner.session.metadata['notes'] = 'changed'
        return QDialog.DialogCode.Rejected if outcome=='cancel' else QDialog.DialogCode.Accepted
    with patch.object(WallSidesDialog,'exec',review):
        assert place_structure(drawing,rectangle()) == (outcome=='apply')
    assert not drawing.wall_dialog_open
    if outcome=='apply':
        assert len(drawing.undo_stack) == history+1
        assert sum('wall' in s for s in drawing.segments()) == 1
        drawing.undo(); assert not drawing.segments()
        drawing.redo(); assert len(drawing.segments()) == 4
    else:
        assert len(drawing.undo_stack) == history and not drawing.segments()
        if outcome=='cancel':
            assert owner.session.metadata == before


def test_shared_side_inheritance_requires_explicit_ack_only_when_changed(editor):
    owner,drawing = editor
    old = plan_wall_layout(state(rectangle()),range(4),(),20,BOUNDS).state
    drawing.store(old['segments'])
    staged,sides,anchor = stage_structure(old,rectangle(x=300))
    dialog = WallSidesDialog(owner,staged,sides,anchor,placing=True)
    common = next(i for i,s in enumerate(sides) if s.shared)
    assert dialog.spins[common].value() == .4  # Test canvas density is 50 px/m.
    assert dialog.apply_button.isEnabled() and not dialog.shared_signature
    dialog.spins[common].setValue(.6)
    assert dialog.candidate and dialog.shared_signature
    assert not dialog.apply_button.isEnabled()
    dialog.confirm_shared.setChecked(True)
    assert dialog.apply_button.isEnabled()
    dialog.spins[common].setValue(.8)
    assert not dialog.confirm_shared.isChecked() and not dialog.apply_button.isEnabled()
    dialog.spins[common].setValue(.4)
    assert not dialog.shared_signature and dialog.apply_button.isEnabled()
    dialog.deleteLater()


def test_clicking_preview_selects_corresponding_side(editor, qt_app):
    owner,_drawing = editor
    staged,sides,anchor = stage_structure(state(),rectangle())
    dialog = WallSidesDialog(owner,staged,sides,anchor,placing=True)
    dialog.show(); qt_app.processEvents()
    side = sides[2].shape
    p = dialog.preview.mapFromScene(QPointF((side['x1']+side['x2'])/2,(side['y1']+side['y2'])/2))
    QTest.mouseClick(dialog.preview.viewport(),Qt.MouseButton.LeftButton,pos=p)
    assert dialog.table.currentRow() == 2
    dialog.reject();dialog.deleteLater()


@pytest.mark.parametrize('tool', ['rectangle','line','circle','arc'])
def test_each_tool_placement_calls_review_once(editor, tool):
    owner,drawing = editor
    calls=[]
    def review(dialog):
        calls.append(dialog)
        return QDialog.DialogCode.Accepted
    with patch.object(WallSidesDialog,'exec',review):
        if tool=='rectangle':
            drawing.commit(QRectF(100,100,200,200))
        elif tool=='line':
            drawing.line.commit(QLineF(100,100,300,300))
        else:
            curve = dict(kind='circle',cx=300,cy=300,radius=100,phase=0) if tool=='circle' else dict(kind='arc',x1=100,y1=200,x2=400,y2=200,height=40)
            drawing.curve.commit(curve)
    assert len(calls) == 1 and calls[0].placing


@pytest.mark.parametrize('button', [Qt.MouseButton.LeftButton,Qt.MouseButton.RightButton])
def test_selection_double_click_inside_room_reopens_sides_not_curve_editor(editor, button):
    owner,drawing = editor
    drawing.store(rectangle())
    owner.plan_tools.select_tool('select')
    point = drawing.view.mapFromScene(QPointF(200,200))
    with patch('qt_ui.qt_wall_sides.edit_wall_sides',return_value=True) as edit:
        QTest.mouseDClick(drawing.view.viewport(),button,pos=point)
    assert edit.call_count == 1
    assert edit.call_args.args[1].area == 40000


def test_invalid_physical_bounds_disable_apply_without_losing_drawing(editor):
    owner,_drawing = editor
    staged,sides,anchor = stage_structure(state(),rectangle(0,0))
    dialog = WallSidesDialog(owner,staged,sides,anchor)
    dialog.spins[0].setValue(.2)
    assert dialog.error == 'wall_outside' and not dialog.apply_button.isEnabled()
    dialog.deleteLater()


def test_per_side_values_survive_save_reopen_and_area_review(editor,tmp_path):
    owner,drawing = editor
    def choose(dialog):
        for spin,value in zip(dialog.spins,[.2,.4,0,.1]):
            spin.setValue(value)
        assert dialog.candidate
        return QDialog.DialogCode.Accepted
    with patch.object(WallSidesDialog,'exec',choose):
        assert place_structure(drawing,rectangle())
    saved = deepcopy(drawing.segments())
    csv = tmp_path/'per-side.csv'
    owner.session.csv_file = str(csv)
    assert owner.save_survey() and owner.open_survey(str(csv))
    assert drawing.segments() == saved
    region = RegionPicker(saved,[]).records[0][1]
    dialogs=[]
    def inspect(dialog):
        dialogs.append(dialog)
        assert sorted(dialog.values.values()) == [0,5,10,20]
        return QDialog.DialogCode.Rejected
    with patch.object(WallSidesDialog,'exec',inspect):
        edit_wall_sides(owner,region)
    assert len(dialogs) == 1 and drawing.segments() == saved


@pytest.mark.parametrize('outcome',['apply','cancel'])
@pytest.mark.parametrize('mode',['drag','measured'])
def test_actual_modal_after_right_gesture_has_no_reentry_or_capture(editor, qt_app, outcome, mode):
    owner,drawing = editor
    view = drawing.view
    captures, reviews = [], []
    view.surveyPointRequested.connect(lambda *args:captures.append(args))
    def answer():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog,WallSidesDialog)
        reviews.append(dialog)
        dialog.spins[0].setValue(.2)
        if outcome=='apply':
            dialog.try_accept()
        else:
            dialog.reject()
    with patch.object(WallSidesDialog,'exec',QDialog.exec):
        QTimer.singleShot(0,answer)
        if mode=='drag':
            drag(view,view.mapFromScene(QPointF(100,100)),view.mapFromScene(QPointF(300,300)))
        else:
            drawing.begin_placement(200,200,anchor=QPointF(100,100))
            QTest.mouseClick(view.viewport(),Qt.MouseButton.RightButton,pos=view.mapFromScene(QPointF(100,100)))
    assert len(reviews) == 1 and not captures
    assert not drawing.pending_size and drawing.origin is None
    assert bool(drawing.segments()) == (outcome=='apply')
    assert len(drawing.undo_stack) == (1 if outcome=='apply' else 0)
