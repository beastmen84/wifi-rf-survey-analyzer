"""Resize is a canvas edit, never an RF coordinate transform."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog
from qt_ui.qt_plan_resize import resize_canvas, canvas_size, ResizePlanDialog, open_plan_resize
from qt_ui.qt_plan_printing import clean_plan_source
from survey.plan_layers import add_layer, active_layer
from survey.plan_mode import PLAN_MODE_KEY, LOAD_PLAN
from survey.wall_layout import plan_wall_layout
from tests.test_wall_thickness import state, rectangle, BOUNDS
from tests.test_rectangle_design import editor
from tests.test_capture_adapter import window, qt_app
from tests._common import build_row
from tests.test_network_plan_symbols import ap
from app_core.survey_grid import GRID_SPACING_KEY


def row_at(x,y):
    return dict(build_row('point-a','Office','02:00:00:00:00:01',-60,1),x=str(x),y=str(y))


def test_resize_keeps_rf_evidence_calibration_grid_and_item_coordinates(editor):
    owner,drawing = editor
    drawing.store(rectangle())
    row = row_at(200,200)
    owner.session.rows = [row]
    owner.session.raw_scan_rows = [dict(point_id='point-a',x=200,y=200,signal_dbm=-60)]
    before = deepcopy(owner.session.rows),deepcopy(owner.session.raw_scan_rows)
    owner.floorplan_view.set_points(owner.session.get_point_summaries())
    items = list(owner.floorplan_view.marker_items)
    positions = [i.pos() for i in items]
    density = owner.get_px_per_meter()
    owner.session.metadata[GRID_SPACING_KEY] = '.5'
    pixmap = owner.floorplan_view.pixmap_item
    assert resize_canvas(owner,(1200,900))
    assert canvas_size(owner) == (1200,900) and owner.get_px_per_meter() == density
    assert (owner.session.rows,owner.session.raw_scan_rows) == before
    assert owner.floorplan_view.pixmap_item is pixmap
    assert owner.floorplan_view.marker_items == items
    assert [i.pos() for i in items] == positions
    assert owner.session.metadata[GRID_SPACING_KEY] == '.5'
    with Image.open(owner.session.metadata['map_file']) as image:
        assert image.size == (1200,900)  # Live/Analysis use resized temp base immediately.
    assert (clean_plan_source(owner.floorplan_view,owner.session.metadata).width(),clean_plan_source(owner.floorplan_view,owner.session.metadata).height()) == (1200,900)


@pytest.mark.parametrize('content',['point','empty_point','ap','hidden','wall','mask'])
def test_shrink_never_discards_content_even_hidden(editor,content):
    owner,drawing = editor
    if content=='point':
        owner.session.rows = [row_at(600,200)]
    elif content=='empty_point':
        with patch.object(owner.session,'measurement_points',return_value=[dict(x=600,y=200,status='empty')]):
            with pytest.raises(ValueError,match='resize_points'):
                resize_canvas(owner,(500,500))
        return
    elif content=='ap':
        owner.session.set_ap_groups([ap(position=dict(x=600,y=200))],update_memory=False)
    elif content=='hidden':
        doc = add_layer(drawing.layer_document(),'Hidden')
        active_layer(doc)['drawing']['segments'] = rectangle(x=600)
        active_layer(doc)['visible'] = False
        doc['active'] = '0'
        drawing.change_layers(doc)
    elif content=='wall':
        drawing.store(plan_wall_layout(state(rectangle(x=290)),range(4),(),20,BOUNDS).state['segments'])
    elif content=='mask':
        view = owner.floorplan_view
        view.ensure_boundaries_mask()
        view.boundaries_mask_image.setPixelColor(600,200,QColor('red'))
        view.boundaries_mask_has_content = True
    before = deepcopy(owner.session.metadata),canvas_size(owner),len(drawing.undo_stack)
    with pytest.raises(ValueError,match={'point':'resize_points','ap':'resize_points','hidden':'resize_content','wall':'resize_content','mask':'resize_mask'}[content]):
        resize_canvas(owner,(500,500))
    assert (owner.session.metadata,canvas_size(owner),len(drawing.undo_stack)) == before


def test_mask_growth_and_safe_shrink_preserve_pixels_and_undo(editor):
    owner,drawing = editor
    view = owner.floorplan_view
    view.ensure_boundaries_mask()
    view.boundaries_mask_image.setPixelColor(120,150,QColor('red'))
    view.boundaries_mask_has_content = True
    old = canvas_size(owner)
    assert resize_canvas(owner,(1200,900))
    assert view.boundaries_mask_image.size() == view.pixmap_item.pixmap().size()
    assert view.boundaries_mask_image.pixelColor(120,150) == QColor('red')
    assert view.boundaries_mask_image.pixelColor(1100,800).alpha() == 0
    assert drawing.undo() and canvas_size(owner) == old
    assert drawing.redo() and canvas_size(owner) == (1200,900)
    assert resize_canvas(owner,(500,400))
    assert view.boundaries_mask_image.pixelColor(120,150) == QColor('red')


def test_canvas_undo_cannot_cut_newly_acquired_points_and_retains_history(editor):
    owner,drawing = editor
    resize_canvas(owner,(1200,900))
    owner.session.rows = [row_at(1100,800)]
    before = len(drawing.undo_stack),len(drawing.redo_stack)
    assert drawing.undo() is False
    assert (len(drawing.undo_stack),len(drawing.redo_stack)) == before
    assert canvas_size(owner) == (1200,900)
    owner.session.rows = []
    assert drawing.undo() and canvas_size(owner) == (900,600)


def test_resize_and_drawing_share_undo_stack_without_losing_outside_geometry(editor):
    owner,drawing = editor
    drawing.store(rectangle())
    resize_canvas(owner,(1200,900))
    drawing.apply_edit(drawing.segments()+rectangle(x=1000,y=600,w=100,h=100))
    assert drawing.undo() and len(drawing.segments()) == 4
    assert drawing.undo() and canvas_size(owner) == (900,600)
    assert drawing.redo() and canvas_size(owner) == (1200,900)
    assert drawing.redo() and len(drawing.segments()) == 8


def test_resize_save_reopen_replaces_only_generated_png_without_extra_confirmation(editor,tmp_path):
    owner,drawing = editor
    drawing.store(rectangle())
    csv = tmp_path/'page.csv'
    owner.session.csv_file = str(csv)
    assert owner.save_survey()
    original = (tmp_path/'page.png').read_bytes()
    resize_canvas(owner,(1200,900))
    assert (tmp_path/'page.png').read_bytes() == original
    with patch('qt_ui.qt_floorplan_workflow.QMessageBox.question') as question:
        assert owner.save_survey()
    assert not question.called
    assert owner.open_survey(str(csv))
    assert canvas_size(owner) == (1200,900) and len(drawing.segments()) == 4
    assert owner.get_px_per_meter() == 50
    assert not hasattr(owner.session,'canvas_source_file')


@pytest.mark.parametrize('outcome',['cancel','apply','stale'])
def test_resize_dialog_is_transactional(editor,outcome):
    owner,drawing = editor
    metadata = deepcopy(owner.session.metadata)
    def choose(dialog):
        dialog.spins[0].setValue(24)
        assert owner.session.metadata == metadata
        if outcome=='stale':
            owner.session.metadata['notes'] = 'changed'
        return QDialog.DialogCode.Rejected if outcome=='cancel' else QDialog.DialogCode.Accepted
    with patch.object(ResizePlanDialog,'exec',choose):
        assert open_plan_resize(owner) == (outcome=='apply')
    assert canvas_size(owner) == ((1200,600) if outcome=='apply' else (900,600))
    assert not drawing.wall_dialog_open


@pytest.mark.parametrize('size',[(0,400),(5000,400),(500,0),(True,400)])
def test_invalid_dimensions_cannot_change_plan(editor,size):
    owner,_drawing = editor
    with pytest.raises(ValueError,match='resize_limit'):
        resize_canvas(owner,size)


def test_resize_draw_only_and_shared_legend_in_analysis_header(editor):
    owner,_drawing = editor
    assert not owner.resize_plan_button.isHidden()
    assert owner.legend_button.parentWidget() == owner.analysis_section_label.parentWidget()
    assert owner.resize_plan_button.parentWidget() == owner.project_section_label.parentWidget()
    owner.session.metadata[PLAN_MODE_KEY] = LOAD_PLAN
    owner.refresh_session_labels()
    assert owner.resize_plan_button.isHidden() and not owner.legend_button.isHidden()
    assert not open_plan_resize(owner)


def test_imperial_rounded_fields_do_not_resize_unchanged_canvas(editor):
    owner,_drawing = editor
    owner.measurement_system = 'imperial'
    dialog = ResizePlanDialog(owner)
    assert dialog.dimensions() == (900,600)
    assert not resize_canvas(owner,dialog.dimensions())
    dialog.deleteLater()


def test_resize_requires_calibration_and_keeps_history_when_undo_is_blocked(editor):
    owner,drawing = editor
    resize_canvas(owner,(1200,900))
    owner.session.metadata.pop('px_per_meter')
    owner.refresh_session_labels()
    assert not owner.resize_plan_button.isEnabled()
    assert not open_plan_resize(owner)
    before = len(drawing.undo_stack)
    assert not drawing.undo() and len(drawing.undo_stack) == before
    assert canvas_size(owner) == (1200,900)


def test_resize_rejects_extreme_grid_density_before_allocating(editor):
    owner,_drawing = editor
    with patch.object(owner.floorplan_view,'grid_spacing_pixels',return_value=1e-9):
        with pytest.raises(ValueError,match='resize_grid_limit'):
            resize_canvas(owner,(1200,900))


def test_points_at_sheet_edges_keep_their_valid_coordinates(editor):
    owner,_drawing = editor
    owner.session.rows = [row_at(500,400)]
    assert resize_canvas(owner,(500,400))
    assert owner.session.get_points()[0]['x'] == 500


def test_base_image_failure_leaves_metadata_history_and_mask_unchanged(editor):
    owner,drawing = editor
    before = deepcopy(owner.session.metadata),canvas_size(owner),len(drawing.undo_stack)
    with patch('qt_ui.qt_plan_resize.ensure_default_floorplan',side_effect=OSError('disk unavailable')):
        with pytest.raises(OSError):
            resize_canvas(owner,(1200,900))
    assert (owner.session.metadata,canvas_size(owner),len(drawing.undo_stack)) == before
    assert not hasattr(owner.session,'canvas_source_file')


def test_save_failure_after_resize_retains_recoverable_source_and_old_files(editor,tmp_path):
    owner,_drawing = editor
    csv = tmp_path/'page.csv'
    owner.session.csv_file = str(csv)
    assert owner.save_survey()
    old_csv,old_png = csv.read_bytes(),(tmp_path/'page.png').read_bytes()
    resize_canvas(owner,(1200,900))
    source = owner.session.canvas_source_file
    with (patch.object(owner.session,'save',side_effect=OSError('save failed')),
          patch('qt_ui.qt_session_workflow.QMessageBox.warning')):
        assert not owner.save_survey()
    assert csv.read_bytes() == old_csv and (tmp_path/'page.png').read_bytes() == old_png
    assert canvas_size(owner) == (1200,900) and owner.session.canvas_source_file == source
    assert owner.save_survey()
