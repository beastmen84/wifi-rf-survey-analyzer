"""Physical grid precision and measured, topology-based selection."""
import math
from copy import deepcopy
from unittest.mock import patch

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest

from app_core.survey_grid import GRID_SPACING_KEY
from app_core.units import display_units_to_meters
from qt_ui.qt_survey_setup import SurveySetupDialog
from qt_ui.qt_plan_region_selection import RegionPicker
from survey.plan_drawing import rectangle_segments
from survey.plan_geometry import rotate_degrees
from survey.plan_curves import transform_curves
from tests.test_capture_adapter import window, qt_app, RECEIVER, wait_until
from tests.test_rectangle_design import editor
from tests.test_plan_curve_ui import at, click
from tests.test_plan_curves import circle, arc, line


@pytest.mark.parametrize("system,decimals,step,default,value", [("metric", 1, .1, 1, .5), ("imperial", 0, 1, 3, 2)])
def test_setup_grid_uses_requested_unit_precision_and_truthful_conversion(window, qt_app, system, decimals, step, default, value):
    window.measurement_system = system
    with patch("qt_ui.qt_survey_setup.list_wifi_adapters", return_value=[]):
        dialog = SurveySetupDialog(window)
        wait_until(qt_app, lambda: dialog.thread is None)
        spin = dialog.grid_size_spin
        assert spin.decimals() == decimals and spin.singleStep() == step
        assert spin.minimum() == step and spin.value() == default
        spin.setValue(value)
        assert dialog.options()["grid_spacing_m"] == pytest.approx(display_units_to_meters(value, system))
        other = "imperial" if system == "metric" else "metric"
        dialog.units_combo.setCurrentIndex(dialog.units_combo.findData(other))
        assert dialog.options()["grid_spacing_m"] == pytest.approx(display_units_to_meters(spin.value(), other))
        assert spin.decimals() == (0 if other == "imperial" else 1)
        dialog.reject()
        dialog.deleteLater()


@pytest.mark.parametrize("system,value,spacing_px", [("metric", .5, 25), ("imperial", 2, 32)])
def test_custom_grid_controls_visible_spacing_snap_and_save_reopen(window, qt_app, tmp_path, system, value, spacing_px):
    spacing_m = display_units_to_meters(value, system)
    options = dict(measurement_system=system, adapter=RECEIVER, blank_plan=dict(width_m=18, height_m=12), grid_spacing_m=spacing_m)
    with patch.object(window, "choose_new_survey_options", return_value=options), patch("qt_ui.qt_session_workflow.save_measurement_system", return_value=True):
        assert window.new_survey(from_start_page=True)
    view = window.floorplan_view
    assert view.grid_spacing_pixels() == pytest.approx(spacing_px)
    assert float(window.session.metadata[GRID_SPACING_KEY]) == pytest.approx(spacing_m)
    window.plan_tools.set_open(True)
    window.plan_tools.snap_button.setChecked(True)
    result = window.plan_tools.controller.snap_position(QPointF(spacing_px + 2, spacing_px - 2))
    assert (result.x, result.y) == pytest.approx((spacing_px, spacing_px))
    window.plan_tools.set_open(False)
    path = tmp_path / "custom-grid.csv"
    window.session.csv_file = str(path)
    assert window.save_survey() and window.open_survey(str(path))
    assert window.floorplan_view.grid_spacing_pixels() == pytest.approx(spacing_px)
    assert float(window.session.metadata[GRID_SPACING_KEY]) == pytest.approx(spacing_m)


def test_existing_survey_grid_can_change_without_moving_drawings(editor):
    app, d = editor
    d.store(rectangle_segments(150, 100, 200, 160, "#123456"))
    before = deepcopy(d.snapshot())
    with patch("qt_ui.qt_floorplan_workflow.QInputDialog.getDouble", return_value=(.5, True)) as dialog:
        assert app.choose_grid_size()
        assert dialog.call_args.kwargs["step"] == .1
    assert d.view.grid_spacing_pixels() == 25 and d.snapshot() == before
    with patch("qt_ui.qt_floorplan_workflow.QInputDialog.getDouble", return_value=(.2, False)):
        assert not app.choose_grid_size()
    assert d.view.grid_spacing_pixels() == 25


def test_legacy_survey_retains_automatic_grid_and_custom_grid_survives_scale_change(editor):
    app, d = editor
    app.session.metadata.pop(GRID_SPACING_KEY, None)
    app.session.metadata["px_per_meter"] = "100"
    app.set_floorplan_grid_enabled(True, show_status=False)
    assert d.view.grid_interval_m is None and d.view.grid_spacing_pixels() == 50
    app.session.metadata[GRID_SPACING_KEY] = "1"
    app.set_floorplan_grid_enabled(True, show_status=False)
    assert d.view.grid_interval_m == 1 and d.view.grid_spacing_pixels() == 100


@pytest.mark.parametrize("angle", [0, 35, 90])
def test_region_picker_has_exact_circle_semicircle_and_oblique_area(angle):
    curves = transform_curves([circle()], angle, (300, 300))
    picker = RegionPicker([], curves)
    picked = picker.pick(QPointF(300, 300))
    assert picked.curves == (0,) and picked.area == pytest.approx(math.pi * 10000, rel=1e-12)
    curve = dict(arc(-100), y1=300, y2=300)
    lines = [line((200, 300), (400, 300))]
    lines = rotate_degrees(lines, angle, (300, 300))
    curves = transform_curves([curve], angle, (300, 300))
    picker = RegionPicker(lines, curves)
    assert len(picker.records) == 1
    assert picker.records[0][1].area == pytest.approx(math.pi * 10000 / 2, rel=1e-12)
    polygon = rotate_degrees(rectangle_segments(150, 100, 200, 160, "#123456"), angle)
    picked = RegionPicker(polygon, []).pick(QPointF(250, 180))
    assert picked.lines == (0, 1, 2, 3) and picked.area == pytest.approx(32000, abs=1e-8)


def test_nested_regions_exclude_holes_and_select_their_inner_boundaries():
    outer = rectangle_segments(100, 100, 500, 350, "#123456")
    inner = rectangle_segments(200, 180, 100, 100, "#123456")
    picker = RegionPicker(outer + inner, [circle(250, 230, 20)])
    outside_room = picker.pick(QPointF(150, 230))
    assert outside_room.lines == tuple(range(8)) and outside_room.curves == ()
    assert outside_room.area == pytest.approx(175000 - 10000)
    inside_room = picker.pick(QPointF(210, 190))
    assert inside_room.lines == (4, 5, 6, 7) and inside_room.curves == (0,)
    assert inside_room.area == pytest.approx(10000 - math.pi * 400)
    disk = picker.pick(QPointF(250, 230))
    assert disk.lines == () and disk.curves == (0,) and disk.area == pytest.approx(math.pi * 400)


def test_connected_inner_hole_excludes_the_bridge_from_selected_perimeter():
    outer = rectangle_segments(100, 100, 500, 350, "#123456")
    inner = rectangle_segments(200, 180, 100, 100, "#123456")
    bridge = line((100, 200), (200, 200))
    picked = RegionPicker(outer + inner + [bridge], []).pick(QPointF(150, 250))
    assert picked.lines == tuple(range(8))
    assert picked.area == pytest.approx(165000)


def test_open_contours_and_dangling_strokes_do_not_become_region_boundaries():
    walls = rectangle_segments(100, 100, 300, 200, "#123456")
    assert RegionPicker(walls[:3], []).pick(QPointF(250, 200)) is None
    picked = RegionPicker(walls + [line((100, 200), (200, 200))], []).pick(QPointF(250, 200))
    assert picked.lines == (0, 1, 2, 3) and picked.area == 60000


def test_duplicate_circle_ink_does_not_double_area_or_lose_source_membership():
    picker = RegionPicker([], [circle(), dict(circle(), phase=35)])
    picked = picker.pick(QPointF(300, 300))
    assert picked.curves == (0, 1) and picked.area == pytest.approx(math.pi * 10000)


@pytest.mark.parametrize("zoom", [.75, 1.5])
def test_click_margin_prefers_single_stroke_then_closed_area_and_open_space_is_noop(editor, zoom):
    app, d = editor
    d.store(rectangle_segments(150, 100, 200, 160, "#123456"))
    app.plan_tools.select_tool("select")
    d.view.resetTransform()
    d.view.scale(zoom, zoom)
    d.view.centerOn(450, 300)
    app.session.dirty = False
    state = deepcopy(d.snapshot())
    edge = at(app, 250, 100)
    QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=edge + QPoint(0, 4))
    assert len(d.selection.selected) == 1 and d.selection.selected_region_area is None
    assert app.tr("line_length") in d.measurement.text()
    QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=edge + QPoint(0, 15))
    assert d.selection.selected == (0, 1, 2, 3) and d.selection.selected_region_area == pytest.approx(32000)
    assert d.selection.measure("selection_area", 32000, 2) in d.measurement.text()
    click(app, 700, 450)
    assert d.selection.selected == (0, 1, 2, 3)
    assert not app.session.dirty and d.snapshot() == state
    assert " · " not in d.measurement.text()
    for key in ("selection_action_rotate", "selection_action_move", "selection_action_delete", "selection_action_cancel"):
        assert app.tr(key) in d.measurement.text().splitlines()


def test_single_line_circle_and_arc_show_their_measurements(editor):
    app, d = editor
    d.store([line((100, 100), (400, 300))])
    app.plan_tools.select_tool("select")
    click(app, 250, 200)
    assert d.selection.measure("line_length", math.hypot(300, 200)) in d.measurement.text()
    d.store([], curves=[circle()])
    click(app, 400, 300)
    assert d.selection.selected_region_area is None
    assert d.selection.measure("curve_radius", 100) in d.measurement.text()
    assert app.tr("selection_action_rotate") not in d.measurement.text()
    d.store([], curves=[arc(50)])
    click(app, 300, 250)
    assert app.tr("selection_arc_length") in d.measurement.text()
    assert app.tr("curve_radius") in d.measurement.text()
    assert app.tr("curve_chord") in d.measurement.text()
    assert app.tr("curve_sagitta") in d.measurement.text()


def test_circle_interior_and_region_transforms_keep_exact_area_and_undo(editor):
    app, d = editor
    d.store([], curves=[circle()])
    app.plan_tools.select_tool("select")
    click(app, 300, 300)
    assert d.selection.selected_curves == (0,) and d.selection.selected_region_area == pytest.approx(math.pi * 10000)
    assert d.selection.begin_move()
    d.selection.last_pointer = QPointF(at(app, 500, 300))
    d.selection.update_move(d.selection.last_pointer, bypass=True)
    expected = deepcopy(d.selection.move_curve_preview)
    assert d.selection.apply_transformed([], [], expected)
    assert d.selection.selected_region_area == pytest.approx(math.pi * 10000)
    d.undo()
    assert d.curves()[0]["cx"] == 300
    d.store(rectangle_segments(150, 100, 200, 160, "#123456"), curves=[])
    click(app, 250, 180)
    assert d.selection.apply_rotation(90)
    assert d.selection.selected_region_area == pytest.approx(32000)
