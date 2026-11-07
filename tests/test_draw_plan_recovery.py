"""Portable generated plans recover only from verified saved vectors/extents."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from survey.plan_mode import PLAN_MODE_KEY, LOAD_PLAN
from survey.plan_layers import active_layer, write_layers
from qt_ui.default_floorplan import (saved_blank_pixel_size, BLANK_PLAN_PIXEL_WIDTH_KEY,
    BLANK_PLAN_PIXEL_HEIGHT_KEY, blank_floorplan_geometry)
from tests.test_rectangle_design import editor
from tests.test_capture_adapter import window, qt_app
from tests.test_wall_thickness import rectangle
from survey.wall_conversion import convert_wall_reference
from tests.test_wall_thickness import state, BOUNDS


@pytest.mark.parametrize('legacy', [False, True])
def test_missing_generated_raster_recovers_vectors_and_original_extent_at_changed_calibration(editor, tmp_path, legacy):
    owner, drawing = editor
    built = convert_wall_reference(state(rectangle()), range(4), (), 20, BOUNDS).state
    drawing.store(built['segments'])
    owner.session.metadata['px_per_meter'] = '73.25'
    if legacy:
        for key in (BLANK_PLAN_PIXEL_WIDTH_KEY, BLANK_PLAN_PIXEL_HEIGHT_KEY):
            owner.session.metadata.pop(key, None)
    expected = deepcopy(drawing.layer_document())
    size = owner.floorplan_view.pixmap_item.pixmap().size()
    csv = tmp_path/'recover.csv'
    owner.session.csv_file = str(csv)
    assert owner.save_survey()
    if legacy:
        # Use an actual legacy CSV, not just modified in-memory metadata.
        from survey.store import write_survey_file
        for key in (BLANK_PLAN_PIXEL_WIDTH_KEY, BLANK_PLAN_PIXEL_HEIGHT_KEY):
            owner.session.metadata.pop(key, None)
        write_survey_file(str(csv), owner.session.metadata, owner.session.rows)
    before = csv.read_bytes()
    (tmp_path/'recover.png').unlink()
    with patch('qt_ui.qt_floorplan_workflow.QMessageBox.warning') as warning:
        assert owner.open_survey(str(csv))
    assert not warning.called
    assert owner.floorplan_view.pixmap_item.pixmap().size() == size
    assert drawing.layer_document() == expected
    assert owner.get_px_per_meter() == 73.25 and owner.session.dirty
    assert owner.session.recovered_floorplan
    assert csv.read_bytes() == before and not (tmp_path/'recover.png').exists()
    assert owner.save_survey() and (tmp_path/'recover.png').exists()
    assert owner.open_survey(str(csv))
    assert not getattr(owner.session, 'recovered_floorplan', False)
    assert drawing.layer_document() == expected


@pytest.mark.parametrize('problem', ['imported','missing_extent','partial_extent','oversize','bad_vectors','outside'])
def test_missing_image_does_not_guess_or_modify_unverifiable_plan(editor, tmp_path, problem):
    owner, drawing = editor
    drawing.store(rectangle())
    owner.session.metadata['map_file'] = str(tmp_path/'missing.png')
    if problem == 'imported':
        owner.session.metadata[PLAN_MODE_KEY] = LOAD_PLAN
    elif problem == 'missing_extent':
        for key in ('blank_plan_width_m','blank_plan_height_m',BLANK_PLAN_PIXEL_WIDTH_KEY,BLANK_PLAN_PIXEL_HEIGHT_KEY):
            owner.session.metadata.pop(key, None)
    elif problem == 'partial_extent':
        owner.session.metadata.pop(BLANK_PLAN_PIXEL_WIDTH_KEY)
    elif problem == 'oversize':
        owner.session.metadata[BLANK_PLAN_PIXEL_WIDTH_KEY] = '100000'
    elif problem == 'bad_vectors':
        owner.session.metadata['plan_layers'] = 'broken'
    elif problem == 'outside':
        doc = drawing.layer_document()
        active_layer(doc)['drawing']['segments'] = rectangle(x=1100)
        write_layers(owner.session.metadata, doc)
    before = deepcopy(owner.session.metadata)
    with (patch('qt_ui.qt_floorplan_workflow.QMessageBox.warning') as warning,
          patch('qt_ui.qt_floorplan_workflow.ensure_default_floorplan') as allocation):
        owner.load_saved_plan()
    assert warning.call_count == 1 and not allocation.called
    assert owner.session.metadata == before
    assert not owner.floorplan_view.has_floorplan()


@pytest.mark.parametrize('pixels', [('900','600'), ('4096','1')])
def test_saved_pixels_override_scale_and_legacy_dimensions(pixels):
    m = {BLANK_PLAN_PIXEL_WIDTH_KEY:pixels[0],BLANK_PLAN_PIXEL_HEIGHT_KEY:pixels[1], 'px_per_meter':'999'}
    assert saved_blank_pixel_size(m,'metric') == tuple(map(int,pixels))


def test_legacy_canvas_uses_initial_density_not_calibrated_density():
    metadata = dict(blank_plan_width_m='60',blank_plan_height_m='25',px_per_meter='75')
    assert saved_blank_pixel_size(metadata,'metric') == blank_floorplan_geometry('metric',60,25)[:2] == (3000,1250)
