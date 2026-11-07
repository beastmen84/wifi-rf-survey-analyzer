"""Existing-plan conversion is explicit, coordinate-stable and reversible."""
from copy import deepcopy
import math

import pytest
from PySide6.QtCore import QPointF
from survey.plan_drawing import encode_drawing, drawing_segments
from app_core.constants import GENERATED_FLOORPLAN_METADATA_KEY
from survey.plan_faces import RegionPicker
from survey.plan_geometry import rotate_degrees, translate_segments
from survey.wall_conversion import convert_wall_reference, reference_regions
from survey.wall_geometry import wall_solids, united
from survey.wall_layout import plan_wall_layout, WallLayoutError
from survey.wall_properties import validated_wall
from tests.test_capture_adapter import qt_app, window
from tests.test_rectangle_design import editor
from tests.test_wall_thickness import state, rectangle, BOUNDS
from tests.test_wall_workflow import select_all
from tests.test_plan_annotations import aperture
from qt_ui.qt_wall_properties import WallPropertiesDialog, validate_survey_layout
from unittest.mock import patch


def convert(original, width=20, **options):
    return convert_wall_reference(original, range(len(original['segments'])), range(len(original['curves'])), width, BOUNDS, **options)


@pytest.mark.parametrize('angle', [0, 1, 5, 15, 25, 35, 45, 65, 89, 90, 135, 180, 225, 270, 315, 359])
@pytest.mark.parametrize('width', [.1, 1, 10, 20])
def test_centered_rectangle_has_exact_net_area_without_moving_reference(qt_app, angle, width):
    original = state(translate_segments(rotate_degrees(rectangle(), angle), 200, 200))
    before = deepcopy(original)
    result = convert(original, width)
    assert original == before and not result.changed_positions
    assert result.areas == pytest.approx((40000,))
    assert result.usable_areas == pytest.approx([(200-width)**2], abs=.01)
    rooms = RegionPicker(result.state['segments'], [])
    assert len(rooms.records) == 1
    region = rooms.records[0][1]
    assert region.area == pytest.approx(40000) and region.usable_area == pytest.approx((200-width)**2, abs=.01)
    assert not region.approximate
    assert [dict((k,v) for k,v in item.items() if k != 'wall') for item in result.state['segments']] == original['segments']
    assert drawing_segments({GENERATED_FLOORPLAN_METADATA_KEY:'1', 'plan_drawing':encode_drawing(result.state['segments'])}) == result.state['segments']
    removed = convert(result.state, 0)
    assert removed.state == original and removed.usable_areas == pytest.approx((40000,))


def test_enclosed_island_and_corridor_are_convertible_without_impossible_rigid_moves(qt_app):
    original = state(rectangle(w=500, h=500)+rectangle(200, 200, 100, 100))
    with pytest.raises(WallLayoutError) as raised:
        plan_wall_layout(original, range(len(original['segments'])), (), 20, BOUNDS)
    assert str(raised.value) == 'wall_constraints_conflict' and raised.value.rooms
    result = convert(original)
    assert sorted(result.areas) == [10000, 240000]
    assert sorted(result.usable_areas) == pytest.approx([6400, 216000])
    assert not result.changed_positions
    # Preserve the island's internal dimensions, accepting loss in the corridor.
    refs = reference_regions(original)
    index = next(i for i,(_p,r) in enumerate(refs.records) if r.area == 10000)
    room = refs.records[index][1]
    face = convert_wall_reference(original, room.lines, room.curves, 20, BOUNDS, mode='face', room_index=index)
    assert face.usable_areas[index] == 10000
    assert sorted(face.usable_areas) == [10000, 230400]
    with pytest.raises(ValueError, match='wall_select_room'):
        convert(original, mode='face', room_index=index)


def test_shared_divider_gets_one_physical_width_not_two(qt_app):
    original = state(rectangle()+rectangle(x=300))
    result = convert(original)
    assert len(result.state['segments']) == 7
    assert result.usable_areas == pytest.approx([32400, 32400])
    material = united(p for _c,p in wall_solids(result.state['segments']))
    assert material.contains(QPointF(309, 200)) and not material.contains(QPointF(311, 200))
    # Door masks cut both halves without damaging room topology.
    material = united(p for _c,p in wall_solids(result.state['segments'], (), [aperture(x1=300,y1=150,x2=300,y2=200)]))
    assert not material.contains(QPointF(305, 175)) and material.contains(QPointF(305, 210))


def test_absorbed_tiny_regions_remain_editable_and_return_when_thickness_removed(qt_app):
    original = state(rectangle(w=500, h=500)+rectangle(200, 200, 100, 5))
    result = convert(original)
    assert min(result.usable_areas) == 0
    assert len(reference_regions(result.state).records) == 2
    assert len(RegionPicker(result.state['segments'], []).records) == 1
    assert convert(result.state, 0).state == original


@pytest.mark.parametrize('mode', ['axis', 'face'])
def test_circle_reference_radius_is_retained_and_net_area_marked_approximate(qt_app, mode):
    original = state(curves=[dict(kind='circle', cx=400, cy=400, radius=100, phase=0, color='#263238')])
    result = convert(original, mode=mode)
    assert result.state['curves'][0]['radius'] == 100
    assert result.usable_areas == pytest.approx([math.pi*(90 if mode == 'axis' else 100)**2], rel=.002)
    picked = RegionPicker([], result.state['curves']).records[0][1]
    if mode == 'axis':
        assert picked.approximate and picked.usable_area == pytest.approx(result.usable_areas[0])
    assert result.approximate_areas


def test_keep_does_not_silently_change_reference_side_or_reference_profile(qt_app):
    original = state(rectangle())
    for mode in ('axis', 'face'):
        converted = convert(original, mode=mode)
        changed = convert(converted.state, 30, mode='keep')
        assert all(s['wall']['reference'] == mode and s['wall']['width'] == 30 for s in changed.state['segments'])
        assert changed.usable_areas == pytest.approx([(170 if mode == 'axis' else 200)**2])
        with pytest.raises(ValueError, match='wall_reference_mode'):
            plan_wall_layout(changed.state, range(4), (), 30, BOUNDS)


@pytest.mark.parametrize('wall', [dict(width=20,side=0),dict(width=20,side=1,reference='axis'),dict(width=20,side=0,reference='face'),dict(width=20,side=1,reference='unknown')])
def test_invalid_reference_combinations_rejected(wall):
    with pytest.raises(ValueError):
        validated_wall(wall)


def test_conversion_bounds_failure_is_atomic(qt_app):
    original = state(rectangle(0, 0))
    before = deepcopy(original)
    with pytest.raises(ValueError, match='wall_outside'):
        convert(original)
    assert original == before


def test_dialog_conversion_keeps_rf_coordinates_and_history_and_defaults_to_keep(editor):
    owner, drawing = editor
    drawing.store(rectangle(w=400,h=400)+rectangle(200,200,100,100))
    select_all(owner, drawing)
    before = deepcopy(drawing.layer_document())
    with patch.object(owner.session, 'get_points', return_value=[dict(x=400,y=400)]):
        dialog = WallPropertiesDialog(owner)
        assert dialog.candidate is None and dialog.problem_rooms
        dialog.mode.setCurrentIndex(dialog.mode.findData('axis'))
        assert dialog.candidate and not dialog.result.changed_positions, dialog.error
        assert dialog.rooms.columnCount() == 4
        validate_survey_layout(owner, dialog.result)
        drawing.change_layers(dialog.candidate)
        dialog.deleteLater()
    select_all(owner,drawing)
    review = WallPropertiesDialog(owner)
    assert review.mode.currentData() == 'keep' and review.candidate
    review.deleteLater()
    drawing.undo()
    assert drawing.layer_document() == before
    drawing.redo()
    assert all(s.get('wall',{}).get('reference') == 'axis' for s in drawing.segments())
