from copy import deepcopy
import math
from unittest.mock import Mock, patch

import pytest
from PIL import Image
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog

from app_core.units import meters_to_display_units
from qt_ui.qt_curve_design import CurveSizeDialog
from qt_ui.qt_plan_fill import fill_closed_boundaries
from qt_ui.scaling import widget_px
from survey.plan_curves import PLAN_CURVES_KEY, curve_bounds, curve_info, transform_curves
from survey.plan_drawing import render_plan_drawing, drawing_geometry
from survey.curved_regions import closed_drawing_regions
from survey.plan_snapping import PlanSnapper
from survey.curve_erasing import intersecting_curves, nearest_curve
from tests.test_rectangle_design import editor, move, drag
from tests.test_capture_adapter import window, qt_app
from tests.test_plan_rotation import orbit
from tests.test_plan_curves import circle, arc, line


def at(app, x, y):
    return app.floorplan_view.mapFromScene(QPointF(x, y))


def click(app, x, y):
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, x, y))


def test_circle_drag_commits_radius_and_undo_redo_without_rf(editor):
    app, d = editor
    app.plan_tools.select_tool("circle")
    with patch.object(app, "start_wifi_scan") as scan:
        drag(d.view, at(app, 300, 200), at(app, 400, 200))
        scan.assert_not_called()
    assert d.segments() == [] and len(d.curves()) == len(d.curve.items) == 1
    original = d.curves()[0]
    assert original["radius"] == pytest.approx(100, abs=2)
    assert len(d.regions.faces) == 1
    d.undo()
    assert not d.curves() and not d.curve.items and not d.regions.faces
    d.redo()
    assert d.curves() == [original]


@pytest.mark.parametrize("height", [50, -50, 150])
def test_arc_drag_freezes_chord_then_pulls_and_commits(editor, height):
    app, d = editor
    app.plan_tools.select_tool("arc")
    drag(d.view, at(app, 250, 250), at(app, 450, 250))
    assert not d.curves() and d.curve.chord is not None and d.curve.current is None
    move(d.view, at(app, 350, 250 + height))
    expected = dict(d.curve.current)
    assert expected["height"] == pytest.approx(height, abs=2)
    assert d.curve.chord["x1"] == expected["x1"] and d.curve.chord["x2"] == expected["x2"]
    click(app, 350, 250 + height)
    assert d.curves() == [expected] and d.curve.chord is None
    assert not d.regions.faces


def test_zero_height_arc_and_escape_make_no_edit(editor):
    app, d = editor
    app.plan_tools.select_tool("arc")
    drag(d.view, at(app, 250, 250), at(app, 450, 250))
    click(app, 350, 250)
    assert not d.curves() and not app.session.dirty
    app.plan_tools.on_escape()
    assert d.curve.chord is None and app.plan_tools.open


@pytest.mark.parametrize("kind,dimensions", [("circle", (70,)), ("arc", (160, -45))])
def test_simple_click_numeric_dialog_then_preview_rotation_and_placement(editor, kind, dimensions):
    app, d = editor
    app.plan_tools.select_tool(kind)
    dialog = Mock()
    dialog.exec.return_value = QDialog.DialogCode.Accepted
    dialog.dimensions.return_value = dimensions
    with patch("qt_ui.qt_curve_design.CurveSizeDialog", return_value=dialog):
        click(app, 300, 220)
    assert d.curve.pending is not None and not d.curves()
    original = dict(d.curve.pending)
    QTest.keyClick(d.view, Qt.Key.Key_R)
    rotated = d.curve.pending
    assert curve_info(rotated)[2] == pytest.approx(curve_info(original)[2])
    move(d.view, at(app, 450, 300))
    placed = dict(d.curve.pending)
    click(app, 450, 300)
    assert d.curves() == [placed] and d.curve.pending is None
    assert d.curve.last_dimensions[kind] == dimensions


@pytest.mark.parametrize("kind,dimensions", [("arc", (160, 45))])
def test_held_rotation_keeps_true_curve_and_cursor_grip(editor, kind, dimensions):
    app, d = editor
    app.plan_tools.select_tool(kind)
    d.curve.begin_placement(kind, dimensions, QPointF(300, 250))
    original = dict(d.curve.pending)
    QTest.keyPress(d.view, Qt.Key.Key_R)
    assert d.rotation.active
    orbit(app, d, 0)
    position = orbit(app, d, 35)
    assert d.rotation.angle == 35
    pivot = d.rotation.pivot
    QTest.keyRelease(d.view, Qt.Key.Key_R)
    expected = transform_curves([original], 35, pivot)[0]
    assert d.curve.pending == expected
    move(d.view, position)
    for key in ("radius",) if kind == "circle" else ("height",):
        assert d.curve.pending[key] == expected[key]
    assert curve_bounds(d.curve.pending) == pytest.approx(curve_bounds(expected), abs=1e-7)


def test_curve_selection_move_rotation_delete_and_mixed_history(editor):
    app, d = editor
    source = arc(50)
    d.store([line((100, 100), (200, 100))], curves=[source])
    app.plan_tools.select_tool("select")
    click(app, 300, 250)
    assert d.selection.selected_curves == (0,) and not d.selection.selected
    assert d.selection.apply_rotation(90)
    rotated = d.curves()[0]
    assert rotated["height"] == 50
    QTest.keyClick(d.view, Qt.Key.Key_M)
    assert d.selection.moving
    move(d.view, at(app, 550, 300))
    moved = deepcopy(d.selection.move_curve_preview)
    click(app, 550, 300)
    assert d.curves() == moved
    assert d.selection.selected_curves == (0,)
    QTest.keyClick(d.view, Qt.Key.Key_Delete)
    assert d.curves() == [] and len(d.segments()) == 1
    d.undo()
    assert d.curves() == moved
    d.undo()
    assert d.curves() == [rotated]
    d.undo()
    assert d.curves() == [source]


def test_curve_eraser_removes_one_intersection_fragment_and_heals(editor):
    app, d = editor
    d.store([line((100, 300), (500, 300))], curves=[circle()])
    assert len(d.curves()) == 2 and len(d.segments()) == 3
    app.plan_tools.select_tool("eraser")
    click(app, 300, 400)
    assert len(d.curves()) == 1
    assert d.curves()[0]["kind"] == "arc"
    assert len(d.segments()) == 3  # Upper arc endpoints still meet the wall.
    d.undo()
    assert len(d.curves()) == 2
    # Remove the crossing wall; obsolete arc cuts should heal into a circle.
    d.apply_edit([], curves=d.curves())
    assert len(d.curves()) == 1 and d.curves()[0]["kind"] == "circle"


def test_rectangle_area_does_not_hit_empty_circle_center_or_arc_bbox():
    curves = [circle(), arc(50)]
    assert intersecting_curves(curves[:1], 290, 290, 310, 310) == ()
    assert nearest_curve(curves[:1], 300, 300, 8) is None
    assert intersecting_curves(curves[:1], 390, 290, 410, 310) == (0,)
    assert intersecting_curves(curves[1:], 205, 240, 215, 250) == ()


@pytest.mark.parametrize("curves,lines,faces", [([circle()], [], 1), ([circle(), circle(400)], [], 3),
    ([circle()], [line((100, 300), (500, 300))], 2), ([arc(50)], [], 0),
    ([arc(50)], [line((200, 200), (400, 200))], 1), ([circle(), circle(500)], [], 2)])
def test_closed_curve_faces_use_real_intersections(curves, lines, faces):
    result = closed_drawing_regions(lines, curves)
    assert not result.limited and len(result.faces) == faces


def test_curve_fill_and_auto_fill_respect_nested_contours(editor):
    app, d = editor
    d.store([], curves=[circle(radius=140), circle(radius=60), circle(650, 300, 70)])
    app.plan_tools.set_open(False)
    app.set_boundaries_mode_enabled(True, show_status=False)
    assert fill_closed_boundaries(app, QPointF(400, 300))
    mask = d.view.boundaries_mask_image
    assert mask.pixelColor(400, 300).alpha() == 255
    assert mask.pixelColor(300, 300).alpha() == 0
    assert mask.pixelColor(650, 300).alpha() == 0
    assert fill_closed_boundaries(app)
    assert mask.pixelColor(300, 300).alpha() == mask.pixelColor(650, 300).alpha() == 255
    assert mask.pixelColor(500, 300).alpha() == 0


def test_curve_save_reopen_png_and_import_clear_vectors(editor, tmp_path):
    app, d = editor
    original = [circle(), arc(-50)]
    assert d.apply_edit([], curves=original)
    before = deepcopy(drawing_geometry(app.session.metadata))
    app.plan_tools.set_open(False)
    path = tmp_path / "curves.csv"
    app.session.csv_file = str(path)
    assert app.save_survey()
    image = Image.open(path.with_suffix(".png")).convert("RGB")
    assert image.getpixel((400, 300)) != (255, 255, 255)
    assert app.open_survey(str(path))
    assert drawing_geometry(app.session.metadata) == before
    assert len(d.curve.items) == len(before[1])
    external = tmp_path / "import.png"
    Image.new("RGB", (900, 600), "white").save(external)
    app.load_plan_file(str(external), save_metadata=True)
    assert PLAN_CURVES_KEY not in app.session.metadata and not d.curve.items


@pytest.mark.parametrize("system", ["metric", "imperial"])
def test_numeric_curve_units_and_dimensions_repeat(editor, system):
    app, d = editor
    app.measurement_system = system
    density = app.get_px_per_meter()
    for kind, dimensions in (("circle", (100,)), ("arc", (200, -50))):
        dialog = CurveSizeDialog(app, kind, d.view.scene.sceneRect(), density, dimensions)
        for spin, expected in zip(dialog.spins, dimensions):
            assert spin.value() == pytest.approx(meters_to_display_units(abs(expected) / density, system), abs=.005)
        assert dialog.dimensions() == pytest.approx(dimensions, abs=density * .002)
        dialog.deleteLater()


def test_fixed_measurement_hud_stays_top_right_after_pointer_and_resize(editor, qt_app):
    app, d = editor
    d.show_measurement("123.00 × 45.00 m\nR: 90°", QPointF(200, 250))
    margin = widget_px(app, 12)
    assert d.measurement.y() == margin
    assert d.measurement.geometry().right() == d.view.viewport().width() - margin - 1
    first = d.measurement.pos()
    d.show_measurement(d.measurement.text(), QPointF(500, 500))
    assert d.measurement.pos() == first
    app.resize(app.width() + 100, app.height() + 60)
    qt_app.processEvents()
    assert d.measurement.y() == margin
    assert d.measurement.geometry().right() == d.view.viewport().width() - margin - 1


def test_snapping_projects_to_true_curve_not_its_chord():
    snapper = PlanSnapper([], [circle()])
    angle = math.radians(35)
    target = (300 + 100 * math.cos(angle), 300 + 100 * math.sin(angle))
    result = snapper.snap(target[0] + 2, target[1] + 2, 0, 0, (0, 0, 900, 600), 8)
    assert math.dist((result.x, result.y), (300, 300)) == pytest.approx(100)
    assert result.guides[0].kind == "edge"
    result = snapper.snap_line(398, 300, (50, 300), True, (0, 0, 900, 600), 8)
    assert (result.x, result.y) == pytest.approx((400, 300))


def test_worker_snapshot_and_stale_curve_pixels_removed(qt_app, tmp_path):
    from maps.config import MapConfig
    from qt_ui.qt_live_map import LiveMapRenderWorker
    curves = [circle()]
    path = tmp_path / "plan.png"
    stale = render_plan_drawing(Image.new("RGB", (900, 600), "white"), [], curves=curves)
    stale.save(path)
    worker = LiveMapRenderWorker([], str(path), MapConfig(), {}, plan_segments=[], plan_curves=curves)
    curves.clear()
    with patch("qt_ui.qt_live_map.render_live_map_payload", return_value={}) as render:
        worker.run()
    image = render.call_args.kwargs["bg_image"]
    assert image.getpixel((400, 300)) != (255, 255, 255)
    assert render_plan_drawing(image, [], curves=[]).getpixel((400, 300)) == (255, 255, 255)


def test_curve_editor_preserves_rotated_chord_orientation(editor):
    app, d = editor
    source = transform_curves([arc(50)], 35, (300, 200))[0]
    d.store([], curves=[source])
    app.plan_tools.select_tool("select")
    d.selection.set_selected((), (), (0,))
    assert app.plan_tools.edit_text_button.isEnabled()
    dialog = Mock()
    dialog.exec.return_value = QDialog.DialogCode.Accepted
    dialog.dimensions.return_value = (240, 70)
    with patch("qt_ui.qt_curve_design.CurveSizeDialog", return_value=dialog):
        assert d.curve.edit(0)
    changed = d.curves()[0]
    assert math.hypot(changed["x2"] - changed["x1"], changed["y2"] - changed["y1"]) == pytest.approx(240)
    assert math.degrees(math.atan2(changed["y2"] - changed["y1"], changed["x2"] - changed["x1"])) == pytest.approx(35)
    assert (changed["x1"] + changed["x2"], changed["y1"] + changed["y2"]) == pytest.approx((600, 400))
    assert changed["height"] == 70


def test_move_previously_cut_circle_heals_both_shapes_and_tracks_only_moved_source(editor):
    app, d = editor
    d.store([], curves=[circle(), circle(400)])
    assert len(d.curves()) == 4
    app.plan_tools.select_tool("select")
    d.selection.set_selected((), (), (2, 3))
    changed = transform_curves(d.selection.selected_curve_shapes(), dx=300)
    assert d.selection.apply_transformed([], [], changed)
    assert len(d.curves()) == 2 and all(c["kind"] == "circle" for c in d.curves())
    assert d.selection.selected_curves == (1,)
    assert d.selection.selected_curve_shapes()[0]["cx"] == pytest.approx(700)


def test_pending_curve_cancelled_on_tool_scene_and_mode_changes(editor, tmp_path):
    app, d = editor
    app.plan_tools.select_tool("arc")
    d.curve.begin_placement("arc", (150, 30), QPointF(300, 250))
    app.plan_tools.select_tool("circle")
    assert d.curve.pending is None and d.curve.preview is None
    d.curve.begin_placement("circle", (60,), QPointF(300, 250))
    app.plan_tools.set_open(False)
    assert d.curve.pending is None and not app.session.dirty
    app.plan_tools.set_open(True)
    app.plan_tools.select_tool("arc")
    drag(d.view, at(app, 250, 250), at(app, 450, 250))
    external = tmp_path / "replacement.png"
    Image.new("RGB", (900, 600), "white").save(external)
    app.load_plan_file(str(external), save_metadata=True)
    assert d.curve.chord is None and d.curve.preview is None and not app.plan_tools.open


def test_circle_has_no_rotation_in_numeric_preview_or_single_selection(editor):
    app, d = editor
    app.plan_tools.select_tool("circle")
    d.curve.begin_placement("circle", (70,), QPointF(300, 250))
    original = dict(d.curve.pending)
    QTest.keyPress(d.view, Qt.Key.Key_R)
    assert not d.rotation.active and d.curve.pending == original
    QTest.keyRelease(d.view, Qt.Key.Key_R)
    assert not d.curve.rotate()
    assert "90" not in d.measurement.text()
    d.cancel()
    d.store([], curves=[circle()])
    app.plan_tools.select_tool("select")
    click(app, 400, 300)
    assert d.selection.selected_curves == (0,) and not d.selection.can_rotate()
    snapshot, count = deepcopy(d.snapshot()), len(d.undo_stack)
    QTest.keyClick(d.view, Qt.Key.Key_R)
    assert not d.rotation.active and not d.selection.apply_rotation(90)
    assert d.snapshot() == snapshot and len(d.undo_stack) == count
    QTest.keyClick(d.view, Qt.Key.Key_M)
    assert d.selection.moving
    preview = deepcopy(d.selection.move_curve_preview)
    QTest.keyClick(d.view, Qt.Key.Key_R)
    assert not d.rotation.active and d.selection.move_curve_preview == preview
    assert "R:" not in d.measurement.text()


def test_circle_center_rotates_with_a_mixed_group_without_own_orientation(editor):
    app, d = editor
    original = dict(circle(radius=50), phase=60)
    d.store([line((500, 300), (600, 300))], curves=[original])
    app.plan_tools.select_tool("select")
    d.selection.set_selected((0,), (), (0,))
    assert d.selection.can_rotate() and d.selection.apply_rotation(90)
    changed = d.curves()[0]
    assert (changed["cx"], changed["cy"]) == pytest.approx((425, 175))
    assert changed["radius"] == 50 and changed["phase"] == 60
