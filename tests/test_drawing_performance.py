"""Interaction caches preserve editable data and fresh vector pixels."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from PySide6.QtCore import QPoint

from qt_ui import qt_rectangle_design, qt_wall_sides
from qt_ui.qt_wall_sides import WallSidesDialog
from survey.plan_annotations import PLAN_ANNOTATIONS_KEY, encode_annotations
from survey.plan_curves import PLAN_CURVES_KEY, encode_curves
from survey.plan_drawing import PLAN_DRAWING_KEY, encode_drawing, rectangle_segments
from survey.plan_labels import PLAN_LABELS_KEY, encode_labels
from survey.plan_layers import PLAN_LAYERS_KEY
from survey.wall_sides import stage_structure
from tests.test_capture_adapter import window, qt_app
from tests.test_floorplan_pan import hand_drag
from tests.test_plan_annotations import aperture, line
from tests.test_plan_curves import circle
from tests.test_plan_text_fill import label
from tests.test_rectangle_design import editor
from tests.test_wall_pan_rendering import fresh_difference
from tests.test_wall_thickness import rectangle, state


def test_legacy_drawing_reads_reuse_validation_and_return_independent_copies(editor):
    owner, drawing = editor
    drawing.store([line()], [label()], [circle(800, 700, 50)], [aperture()])
    assert PLAN_LAYERS_KEY not in owner.session.metadata
    metadata = deepcopy(owner.session.metadata)
    expected = deepcopy(drawing.active_state())
    drawing._layer_cache_key = None
    with patch.object(qt_rectangle_design, 'read_layers', wraps=qt_rectangle_design.read_layers) as read:
        for _ in range(5):
            for key, getter in (('segments', drawing.segments), ('curves', drawing.curves),
                                ('labels', drawing.labels), ('annotations', drawing.annotations)):
                value = getter()
                assert value == expected[key]
                value[0]['color'] = '#ffffff'
                value.clear()
        assert read.call_count == 1
    assert drawing.active_state() == expected and owner.session.metadata == metadata


@pytest.mark.parametrize('key, encoded, getter, expected', [
    (PLAN_DRAWING_KEY, encode_drawing([line(), line(100, 300, 600, 300)]), 'segments',
     [line(), line(100, 300, 600, 300)]),
    (PLAN_CURVES_KEY, encode_curves([circle(800, 700, 50)]), 'curves', [circle(800, 700, 50)]),
    (PLAN_LABELS_KEY, None, 'labels', None),
    (PLAN_ANNOTATIONS_KEY, encode_annotations([aperture()]), 'annotations', [aperture()]),
])
def test_legacy_metadata_changes_invalidate_interaction_data(editor, key, encoded, getter, expected):
    owner, drawing = editor
    drawing.store([line()])
    drawing.snapshot()
    if key == PLAN_LABELS_KEY:
        expected = [label()]
        encoded = encode_labels(expected)
    owner.session.metadata[key] = encoded
    assert getattr(drawing, getter)() == expected


@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('zoom', [1, 1.25, 2.75])
def test_room_grid_pan_matches_fresh_paint_after_style_and_mask_changes(editor, qt_app, theme, zoom):
    owner, drawing = editor
    lines = [side for x, y, width, height in ((100, 100, 450, 300), (550, 250, 500, 500),
                                             (200, 800, 700, 200))
             for side in rectangle_segments(x, y, width, height, '#263238')]
    drawing.store(lines)
    owner.change_theme(theme)
    owner.set_floorplan_grid_enabled(False, show_status=False)
    owner.set_floorplan_grid_enabled(True, show_status=False)
    owner.plan_tools.select_tool(None)
    view = drawing.view
    view.set_zoom(zoom)
    view.centerOn(750, 600)
    qt_app.processEvents()
    snapshot = deepcopy(drawing.snapshot())
    for delta in (QPoint(131, -57), QPoint(-191, 83), QPoint(89, 41)):
        hand_drag(view, QPoint(view.viewport().width()*3//4, view.viewport().height()//3), delta)
        qt_app.processEvents()
        difference, _before, _after = fresh_difference(view, drawing.wall_items, qt_app)
        assert difference == 0
    assert drawing.snapshot() == snapshot


def test_wall_side_selection_reuses_preview_geometry_but_depth_changes_rebuild_it(editor):
    owner, drawing = editor
    staged, sides, anchor = stage_structure(state(), rectangle())
    with patch.object(qt_wall_sides, 'wall_commands', wraps=qt_wall_sides.wall_commands) as commands:
        dialog = WallSidesDialog(owner, staged, sides, anchor, placing=True)
        try:
            assert commands.call_count == 1  # No discarded preview before refresh.
            original = deepcopy(dialog.result.state)
            for row in (1, 2, 3, 0):
                dialog.table.selectRow(row)
                assert dialog.result.state == original
                assert len(dialog.preview.paths) == len(sides)
            assert commands.call_count == 1
            dialog.spins[0].setValue(.15)
            assert commands.call_count == 2 and dialog.result.state != original
            assert dialog.apply_button.isEnabled()
            dialog.table.selectRow(1)
            assert commands.call_count == 2
            assert drawing.segments() is None  # Preview has not modified the project.
        finally:
            dialog.close()
