"""Deleting a room leaves one reference face on its surviving shared wall."""
from copy import deepcopy

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest

from survey.plan_annotation_rendering import annotation_path
from survey.plan_annotations import supported
from survey.plan_faces import RegionPicker
from survey.plan_geometry import normalize_segments, rotate_degrees
from survey.wall_editing import paired_lines, remove_wall_faces, retained_wall_annotations
from survey.wall_geometry import path_area, wall_solids
from survey.wall_layout import plan_wall_layout
from tests.test_capture_adapter import window, qt_app
from tests.test_plan_annotations import aperture, at
from tests.test_rectangle_design import editor
from tests.test_wall_thickness import rectangle, state, BOUNDS


def rooms(lines, curves=()):
    return sorted(RegionPicker(lines, curves).records, key=lambda pair: pair[0].boundingRect().left())


def layout(partial=False):
    source = state(rectangle()+rectangle(x=300, y=150 if partial else 100, h=100 if partial else 200))
    return plan_wall_layout(source, range(len(source['segments'])), (), 20, BOUNDS).state['segments']


def exterior(lines, room):
    return tuple(i for i in room.lines if len(paired_lines(lines, i)) == 1)


def signature(lines):
    return sorted((tuple(round(line[k], 6) for k in ('x1', 'y1', 'x2', 'y2')),
                   line['color'], repr(line.get('wall'))) for line in normalize_segments(lines))


@pytest.mark.parametrize('partial', [False, True])
@pytest.mark.parametrize('deleted', [0, 1])
@pytest.mark.parametrize('angle', [0, 35, 90, 180])
def test_removed_room_face_disappears_but_survivor_geometry_and_material_stay(qt_app, partial, deleted, angle):
    lines = layout(partial)
    records = rooms(lines)
    target = exterior(lines, records[deleted][1])
    expected = [lines[i] for i in records[1-deleted][1].lines]
    for line in lines:
        line['wall'].update(material='brick', pattern='cross')
    rotated = rotate_degrees(lines, angle, (300, 300))
    before = deepcopy(rotated)
    left = normalize_segments(remove_wall_faces(rotated, target))
    assert signature(left) == signature(rotate_degrees(expected, angle, (300, 300)))
    assert len(rooms(left)) == 1
    assert rotated == before
    assert sum(path_area(p) for _, p in wall_solids(left)) == pytest.approx(
        sum(path_area(p) for _, p in wall_solids(rotate_degrees(expected, angle, (300, 300)))), abs=.01)


def test_other_closed_rooms_keep_both_faces_and_unowned_strokes_are_not_pruned(qt_app):
    lines = layout()
    # An intentional open face on another room must survive unrelated deletion.
    extra = plan_wall_layout(state(rectangle(x=700)), range(4), (), 20, BOUNDS).state['segments']
    extra.append(dict(x1=920, y1=180, x2=920, y2=220, color='#263238', wall=dict(width=20, side=1)))
    lines = normalize_segments(lines+extra)
    first, second, _third = rooms(lines)
    assert remove_wall_faces(lines, ()) == lines
    left = normalize_segments(remove_wall_faces(lines, exterior(lines, second[1])))
    assert len(rooms(left)) == 2
    assert any(line['x1'] == line['x2'] == 920 for line in left)
    assert signature([lines[i] for i in first[1].lines]) == signature([left[i] for i in rooms(left)[0][1].lines])


@pytest.mark.parametrize('kind,variant', [('door', 'single'), ('door', 'double'), ('door', 'sliding'),
                                         ('door', 'frame'), ('window', 'single')])
@pytest.mark.parametrize('angle', [0, 35])
def test_opening_on_discarded_face_keeps_its_world_geometry_and_identity(qt_app, kind, variant, angle):
    from survey.plan_annotations import transform_annotations
    lines = layout(True)
    target = exterior(lines, rooms(lines)[1][1])
    item = aperture(kind, variant=variant, x1=320, y1=170, x2=320, y2=220)
    lines = rotate_degrees(lines, angle, (300, 300))
    item = transform_annotations([item], angle, (300, 300))[0]
    before = deepcopy(item)
    left = normalize_segments(remove_wall_faces(lines, target))
    result = retained_wall_annotations([item], lines, left)
    assert len(result) == 1 and supported(result[0], left)
    assert {k:v for k,v in result[0].items() if k not in ('x1', 'y1', 'x2', 'y2')} == {
        k:v for k,v in item.items() if k not in ('x1', 'y1', 'x2', 'y2')}
    old_path, new_path = annotation_path(item, lines), annotation_path(result[0], left)
    assert old_path.elementCount() == new_path.elementCount()
    for i in range(old_path.elementCount()):
        a, b = old_path.elementAt(i), new_path.elementAt(i)
        assert (a.x, a.y) == pytest.approx((b.x, b.y))
    assert item == before


def test_deleting_actual_shared_wall_still_removes_its_opening(qt_app):
    lines = layout()
    selected = next(i for i in range(len(lines)) if len(paired_lines(lines, i)) > 1)
    item = aperture(x1=320, y1=170, x2=320, y2=220)
    left = remove_wall_faces(lines, (selected,))
    assert retained_wall_annotations([item], lines, left) == []
    assert len(rooms(left)) == 1


@pytest.mark.parametrize('delete_curve', [False, True])
def test_curved_room_ownership_is_respected_during_face_cleanup(qt_app, delete_curve):
    lines = layout()
    target = exterior(lines, rooms(lines)[1][1])
    lines = [line for i, line in enumerate(lines) if i not in target]
    arc = dict(kind='arc', x1=320, y1=100, x2=320, y2=300, height=-100,
               color='#263238', wall=dict(width=20, side=1))
    assert len(rooms(lines, [arc])) == 2
    kept_curves = [] if delete_curve else [arc]
    left = normalize_segments(remove_wall_faces(lines, (), curves=[arc], remaining_curves=kept_curves))
    assert len(rooms(left, kept_curves)) == (1 if delete_curve else 2)
    assert any(line['x1'] == line['x2'] == 320 for line in left) != delete_curve


@pytest.mark.parametrize('tool', ['select', 'eraser'])
def test_ui_deletion_cleans_face_preserves_opening_and_supports_history_and_reopen(editor, tmp_path, tool):
    owner, drawing = editor
    lines = layout(True)
    item = aperture(x1=320, y1=170, x2=320, y2=220)
    drawing.store(lines, annotations=[item])
    before, count = deepcopy(drawing.snapshot()), len(drawing.undo_stack)
    target = exterior(lines, rooms(lines)[1][1])
    owner.plan_tools.select_tool(tool)
    if tool == 'select':
        drawing.selection.set_selected(target)
        QTest.keyClick(owner, Qt.Key.Key_Delete)
        steps = 1
    else:
        for i in target:
            line = lines[i]
            QTest.mouseClick(drawing.view.viewport(), Qt.MouseButton.RightButton,
                             pos=at(owner, (line['x1']+line['x2'])/2, (line['y1']+line['y2'])/2))
        steps = len(target)
    assert len(drawing.undo_stack) == count+steps
    assert len(drawing.segments()) == 4 and len(rooms(drawing.segments())) == 1
    assert len(drawing.annotations()) == 1 and drawing.annotations()[0]['id'] == item['id']
    assert drawing.annotations()[0]['x1'] == pytest.approx(300)
    assert supported(drawing.annotations()[0], drawing.segments())
    after = deepcopy(drawing.snapshot())
    for _ in range(steps):
        assert drawing.undo()
    assert drawing.snapshot() == before
    for _ in range(steps):
        assert drawing.redo()
    assert drawing.snapshot() == after
    owner.session.csv_file = str(tmp_path/'deleted-room.csv')
    assert owner.save_survey() and owner.open_survey(owner.session.csv_file)
    assert drawing.segments() == after['segments'] and drawing.annotations() == after['annotations']
    # Only the retained face remains available for picking.
    assert drawing.selection.pick_stroke(QPointF(310, 230))[0] == (1,)
