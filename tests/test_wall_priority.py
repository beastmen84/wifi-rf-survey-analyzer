"""Explicit visual priority, independent of input order and physical dimensions."""
from copy import deepcopy
import math
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, QSize
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QDialog

from qt_ui.qt_clean_plan import VectorPlanSource
from qt_ui.qt_wall_sides import WallSidesDialog, edit_wall_sides
from survey.plan_drawing import encode_drawing, render_plan_drawing, drawing_segments, PLAN_DRAWING_KEY
from survey.plan_geometry import normalize_segments, rotate_degrees
from survey.wall_conversion import convert_wall_reference
from survey.wall_geometry import wall_solids, path_area, united
from survey.wall_properties import validated_wall
from survey.wall_sides import wall_sides, apply_side_widths, stage_structure
from tests.test_capture_adapter import window, qt_app
from tests.test_rectangle_design import editor
from tests.test_wall_materials import rendered
from tests.test_wall_thickness import rectangle, state, BOUNDS
from tests.test_wall_face_cleanup import layout
from tests.test_plan_annotations import aperture


def corner(priority=None):
    vertical = dict(x1=200, y1=100, x2=200, y2=200, color='#263238',
                    wall=dict(width=20, side=-1, material='reinforced_concrete', pattern='solid'))
    horizontal = dict(x1=200, y1=200, x2=340, y2=200, color='#263238',
                      wall=dict(width=5, side=1, material='drywall', pattern='solid'))
    result = [vertical, horizontal]
    if priority is not None:
        result[priority]['wall']['priority'] = True
    return result


@pytest.mark.parametrize('value', [0, 1, 'true', None, [], {}])
def test_priority_requires_a_boolean(value):
    with pytest.raises(ValueError, match='wall_invalid_priority'):
        validated_wall(dict(width=20, side=1, priority=value))


def test_old_defaults_and_priority_persistence_are_compatible():
    old = dict(width=20, side=1)
    assert validated_wall(dict(old, priority=False)) == validated_wall(old)
    lines = corner(0)
    result = drawing_segments({'_generated_floorplan':'1', 'plan_mode':'draw', PLAN_DRAWING_KEY:encode_drawing(lines)})
    assert result[0]['wall']['priority'] is True
    assert 'priority' not in result[1]['wall']


@pytest.mark.parametrize('priority', [None, 0, 1])
@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('angle', [0, 35, 90])
def test_winning_material_and_reference_ink_are_stable_in_vector_and_raster(qt_app, priority, reverse, angle):
    lines = corner(priority)
    if reverse:
        lines.reverse()
    lines = rotate_degrees(lines, angle, (250, 200))
    angle_rad = math.radians(angle)
    def transformed(x, y):
        return (250+(x-250)*math.cos(angle_rad)-(y-200)*math.sin(angle_rad),
                200+(x-250)*math.sin(angle_rad)+(y-200)*math.cos(angle_rad))
    source = VectorPlanSource(QSize(500, 400), lines, [], [], [])
    image = rendered(source, 4)
    expected = '#e6e9f2' if priority == 1 else '#cbd1d8'
    # The miter and the lower wall's reference stroke must both obey priority.
    for point in ([(210, 202), (210, 200)] if priority != 1 else [(210, 202)]):
        x, y = transformed(*point)
        assert image.pixelColor(round(x*4), round(y*4)).name() == expected
    raster = render_plan_drawing(Image.new('RGB', (500, 400), 'white'), lines)
    x, y = transformed(210, 202)
    assert '#%02x%02x%02x' % raster.getpixel((round(x), round(y))) == expected


@pytest.mark.parametrize('checked', [False, True])
def test_equal_priority_prefers_thickness_and_keeps_physical_union(qt_app, checked):
    lines = corner()
    for line in lines:
        line['wall']['priority'] = checked
    before = united(path for _,path in wall_solids(lines))
    styled = wall_solids(lines, styled=True)
    assert path_area(united(path for _,path in styled)) == pytest.approx(path_area(before))
    concrete = next(path for (_color,material,_pattern),path in styled if material == 'reinforced_concrete')
    assert concrete.contains(QPointF(210, 202))
    assert path_area(styled[0][1].intersected(styled[1][1])) <= 1e-6


def test_priority_preserves_aperture_cuts(qt_app):
    lines = corner(0)
    opening = aperture(variant='frame', x1=200, y1=130, x2=200, y2=160)
    source = VectorPlanSource(QSize(500,400), lines, [], [], [opening])
    image = rendered(source, 2)
    assert image.pixelColor(210*2,145*2).name() == '#ffffff'


@pytest.mark.parametrize('priority', [False, True])
def test_curved_priority_and_reference_ink_share_the_same_rendering_rule(qt_app, priority):
    line = dict(x1=200,y1=130,x2=400,y2=130,color='#263238',
                wall=dict(width=30,side=1,material='reinforced_concrete',pattern='solid'))
    circle = dict(kind='circle',cx=300,cy=250,radius=100,phase=0,color='#263238',
                  wall=dict(width=20,side=-1,material='glass',pattern='solid',priority=priority))
    source = VectorPlanSource(QSize(600,500),[line],[circle],[],[])
    image = rendered(source,4)
    assert image.pixelColor(300*4,140*4).name() == ('#e0f3f6' if priority else '#cbd1d8')
    if not priority:
        assert image.pixelColor(300*4,150*4).name() == '#cbd1d8'


@pytest.mark.parametrize('converted', [False, True])
def test_priority_propagates_to_shared_face_without_changing_room_geometry(qt_app, converted):
    original = state(layout())
    if converted:
        for line in original['segments']:
            line['wall']['reference'] = 'face'
    sides = wall_sides(original, (1,))
    result = apply_side_widths(original, sides, {1:20}, BOUNDS, priorities={1:True})
    assert not result.changed_positions
    assert sum(s['wall'].get('priority', False) for s in result.state['segments']) == 2
    assert [{k:v for k,v in s.items() if k != 'wall'} for s in result.state['segments']] == [
        {k:v for k,v in s.items() if k != 'wall'} for s in original['segments']]
    sides = wall_sides(result.state, (1,))
    cleared = apply_side_widths(result.state, sides, {1:20}, BOUNDS, priorities={1:False})
    assert not any(s['wall'].get('priority', False) for s in cleared.state['segments'])


def test_new_shared_faces_and_reference_conversion_keep_priority(qt_app):
    original = state([dict(s, wall=dict(width=20, side=-1, priority=True)) for s in rectangle()])
    staged, sides, anchor = stage_structure(original, rectangle(x=320))
    assert next(s for s in sides if s.shared).shape['wall']['priority'] is True
    converted = convert_wall_reference(original, range(4), (), 20, BOUNDS, mode='axis').state
    assert all(s['wall']['priority'] is True for s in converted['segments'])


def test_priority_changes_do_not_merge_distinct_collinear_settings(qt_app):
    a = dict(x1=100, y1=100, x2=200, y2=100, color='#263238', wall=dict(width=20, side=1))
    b = dict(a, x1=200, x2=300, wall=dict(width=20, side=1, priority=True))
    assert len(normalize_segments([a,b])) == 2


@pytest.mark.parametrize('outcome', ['cancel', 'apply'])
def test_ui_priority_is_transactional_shared_and_persistent(editor, tmp_path, outcome):
    owner, drawing = editor
    drawing.store(layout())
    owner.plan_tools.select_tool('select')
    drawing.selection.set_selected((1,))
    before, count = deepcopy(drawing.snapshot()), len(drawing.undo_stack)
    def review(dialog):
        assert dialog.table.columnCount() == 4
        assert dialog.priority_checks[0].isEnabled()
        dialog.priority_checks[0].setChecked(True)
        assert dialog.candidate is not None and dialog.shared_signature
        assert not dialog.apply_button.isEnabled()
        dialog.confirm_shared.setChecked(True)
        assert dialog.apply_button.isEnabled()
        return QDialog.DialogCode.Accepted if outcome == 'apply' else QDialog.DialogCode.Rejected
    with patch.object(WallSidesDialog, 'exec', review):
        assert edit_wall_sides(owner) == (outcome == 'apply')
    if outcome == 'cancel':
        assert drawing.snapshot() == before and len(drawing.undo_stack) == count
        return
    assert len(drawing.undo_stack) == count+1
    after = deepcopy(drawing.snapshot())
    assert sum(s['wall'].get('priority', False) for s in drawing.segments()) == 2
    assert drawing.undo() and drawing.snapshot() == before
    assert drawing.redo() and drawing.snapshot() == after
    owner.session.csv_file = str(tmp_path/'priority.csv')
    assert owner.save_survey() and owner.open_survey(owner.session.csv_file)
    assert drawing.segments() == after['segments']


def test_priority_checkbox_requires_positive_depth_and_shared_rows_stay_synced(editor):
    owner, _drawing = editor
    staged, sides, anchor = stage_structure(state(), rectangle())
    dialog = WallSidesDialog(owner, staged, sides, anchor)
    assert not any(check.isEnabled() for check in dialog.priority_checks)
    dialog.spins[0].setValue(.2)
    assert dialog.priority_checks[0].isEnabled()
    dialog.reject()
    dialog.deleteLater()
    original = state(layout())
    dialog = WallSidesDialog(owner, original, wall_sides(original, range(8)))
    dialog.priority_checks[1].setChecked(True)
    assert dialog.priority_checks[2].isChecked()
    dialog.reject()
    dialog.deleteLater()


def test_preview_tracks_shared_material_reset_and_priority(editor):
    owner, _drawing = editor
    original = state(layout())
    for line in original['segments']:
        line['wall'].update(material='reinforced_concrete', pattern='solid')
    dialog = WallSidesDialog(owner, original, wall_sides(original, (1,)))
    dialog.priority_checks[0].setChecked(True)
    for material, expected in [('drywall', '#e6e9f2'), ('unspecified', '#d1d5db')]:
        dialog.material.setCurrentIndex(dialog.material.findData(material))
        image = QImage(400,400,QImage.Format.Format_RGB32)
        image.fill(0xffffffff)
        painter = QPainter(image)
        dialog.preview.scene().render(painter, QRectF(0,0,400,400), QRectF(250,200,100,100))
        painter.end()
        assert image.pixelColor(240,200).name() == expected
    dialog.reject()
    dialog.deleteLater()
