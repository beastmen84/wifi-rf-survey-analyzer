"""Fixed-pivot 5° gestures and genuine oblique segment geometry."""
import math
from copy import deepcopy
from unittest.mock import patch

import pytest
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QKeyEvent, QPainterPath
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from qt_ui.qt_plan_rotation import angle_readout
from survey.plan_drawing import drawing_segments, encode_drawing, rectangle_segments, validate_segments
from survey.plan_erasing import intersecting_segments, nearest_segment
from survey.plan_geometry import normalize_segments, rotate_degrees, segment_bounds, translate_segments
from survey.plan_regions import closed_plan_regions
from survey.plan_snapping import PlanSnapper
from tests.test_rectangle_design import editor, move
from tests.test_capture_adapter import window, qt_app


def line(x1, y1, x2, y2, color="#123456"):
    return dict(x1=x1, y1=y1, x2=x2, y2=y2, color=color)


def orbit(app, drawing, degrees, radius=150):
    rotation = drawing.rotation
    reference = rotation.reference or 0
    angle = math.radians(reference + degrees)
    x, y = rotation.pivot
    position = app.floorplan_view.mapFromScene(QPointF(x + radius * math.cos(angle), y + radius * math.sin(angle)))
    move(app.floorplan_view, position)
    return position


@pytest.mark.parametrize("angle,text", [(90, "(+90° / -270°)"), (315, "(+315° / -45°)"), (0, "(+0° / 0°)"), (-45, "(+315° / -45°)")])
def test_equivalent_angle_readout(angle, text):
    assert angle_readout(angle) == text


@pytest.mark.parametrize("angle", range(0, 360, 5))
def test_all_five_degree_orientations_preserve_lengths_closed_regions_and_model_roundtrip(angle):
    source = rectangle_segments(200, 200, 200, 100, "#123456")
    rotated = rotate_degrees(source, angle)
    normalized = normalize_segments(validate_segments(rotated))
    assert len(normalized) == 4
    for first, second in zip(source, rotated):
        assert math.hypot(first["x2"] - first["x1"], first["y2"] - first["y1"]) == pytest.approx(
            math.hypot(second["x2"] - second["x1"], second["y2"] - second["y1"]), abs=1e-10)
    assert normalize_segments(normalized) == normalized
    assert drawing_segments({"_generated_floorplan": "1", "plan_drawing": encode_drawing(normalized)}) == normalized
    regions = closed_plan_regions(normalized)
    assert len(regions.faces) == 1 and not regions.limited
    path = QPainterPath()
    for face in regions.faces:
        path.moveTo(*face[0])
        for point in face[1:]:
            path.lineTo(*point)
        path.closeSubpath()
    assert path.contains(QPointF(300, 250))


def test_oblique_cross_t_overlap_and_join_use_real_finite_geometry():
    cross = normalize_segments([line(100, 100, 300, 300), line(100, 300, 300, 100)])
    assert len(cross) == 4
    assert all((200, 200) in ((s["x1"], s["y1"]), (s["x2"], s["y2"])) for s in cross)
    assert normalize_segments(cross[:2]) == [line(100, 100, 300, 300)]
    assert len(normalize_segments([line(100, 100, 300, 300), line(200, 200, 300, 200)])) == 3
    assert normalize_segments([line(100, 100, 300, 300), line(200, 200, 400, 400)]) == [line(100, 100, 400, 400)]
    assert len(normalize_segments([line(100, 100, 200, 200), line(200.00001, 200.00001, 300, 300)])) == 2


def test_oblique_eraser_and_marquee_ignore_empty_bounding_box_corners():
    segments = [line(100, 100, 300, 300)]
    assert nearest_segment(segments, 200, 200, 7) == 0
    assert nearest_segment(segments, 110, 290, 7) is None
    assert intersecting_segments(segments, 100, 280, 120, 300) == ()
    assert intersecting_segments(segments, 190, 190, 210, 210) == (0,)


def test_oblique_snap_uses_actual_vertices_and_finite_edge_projections():
    snapper = PlanSnapper([line(100, 100, 300, 300)])
    result = snapper.snap(224, 220, 0, 0, (0, 0, 900, 600), 10)
    assert (result.x, result.y) == (222, 222) and result.guides[0].axis == "line"
    source = [line(224, 220, 274, 270)]
    result = snapper.snap_geometry(source, (0, 0, 900, 600), 10)
    assert result.guides and result.x == -2 and result.y == 2


def test_tap_r_waits_for_release_then_rotates_ninety(editor):
    app, drawing = editor
    drawing.begin_placement(200, 100, QPointF(300, 200))
    QTest.keyPress(app, Qt.Key.Key_R)
    assert drawing.pending_size == (200, 100) and drawing.rotation.active
    QTest.keyRelease(app, Qt.Key.Key_R)
    assert drawing.pending_size == (100, 200) and not drawing.rotation.active
    assert not app.session.dirty


@pytest.mark.parametrize("requested,expected", [(43, 45), (92, 90), (-43, 315), (314, 315)])
def test_selection_hold_r_quantizes_with_fixed_center_and_one_undo_action(editor, requested, expected):
    app, drawing = editor
    drawing.apply_edit([line(250, 300, 450, 300)])
    app.plan_tools.select_button.click()
    drawing.selection.set_selected([0])
    move(app.floorplan_view, app.floorplan_view.mapFromScene(QPointF(450, 300)))
    original = drawing.segments()
    count = len(drawing.undo_stack)
    QTest.keyPress(app, Qt.Key.Key_R)
    pivot = drawing.rotation.pivot
    orbit(app, drawing, requested)
    assert drawing.rotation.angle == expected
    assert drawing.rotation.pivot == pivot and drawing.segments() == original
    assert angle_readout(expected) in drawing.measurement.text()
    QTest.keyRelease(app, Qt.Key.Key_R)
    assert drawing.segments() == normalize_segments(rotate_degrees(original, expected, pivot))
    assert len(drawing.undo_stack) == count + 1
    drawing.undo()
    assert drawing.segments() == original


@pytest.mark.parametrize("target", ["rectangle", "line", "move"])
def test_cursor_following_previews_freeze_during_r_then_keep_frozen_position_on_release(editor, target):
    app, drawing = editor
    if target == "rectangle":
        drawing.begin_placement(200, 100, QPointF(300, 200))
    elif target == "line":
        app.plan_tools.line_button.click()
        drawing.line.begin_placement(200, QPointF(300, 250))
    else:
        drawing.apply_edit([line(250, 300, 450, 300)])
        app.plan_tools.select_button.click()
        drawing.selection.set_selected([0])
        move(app.floorplan_view, app.floorplan_view.mapFromScene(QPointF(450, 300)))
        QTest.keyClick(app, Qt.Key.Key_M)
    original = deepcopy(drawing.segments())
    QTest.keyPress(app, Qt.Key.Key_R)
    pivot = drawing.rotation.pivot
    position = orbit(app, drawing, 45)
    expected = deepcopy(drawing.rotation.rotated)
    assert drawing.rotation.pivot == pivot and drawing.segments() == original
    QTest.keyRelease(app, Qt.Key.Key_R)
    if target == "rectangle":
        actual = drawing.rectangle_geometry(drawing.preview.rect())
    elif target == "line":
        actual_line = drawing.line.preview.line()
        actual = [line(actual_line.x1(), actual_line.y1(), actual_line.x2(), actual_line.y2(), "#263238")]
    else:
        actual = drawing.selection.move_preview
    assert segment_bounds(actual) == pytest.approx(segment_bounds(expected), abs=1e-9)
    captures = []
    app.floorplan_view.surveyPointRequested.connect(lambda *args: captures.append(args))
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, Qt.KeyboardModifier.AltModifier, position)
    committed = drawing.segments()
    assert any(item["x1"] != item["x2"] and item["y1"] != item["y2"] for item in committed)
    assert not captures
    if target == "rectangle":
        assert len(drawing.regions.faces) == 1


@pytest.mark.parametrize("cancel", ["escape", "exit", "deactivate"])
def test_rotation_cancellation_and_late_r_release_do_not_commit(editor, cancel):
    app, drawing = editor
    drawing.apply_edit([line(250, 300, 450, 300)])
    app.plan_tools.select_button.click()
    drawing.selection.set_selected([0])
    original = drawing.segments()
    count = len(drawing.undo_stack)
    QTest.keyPress(app, Qt.Key.Key_R)
    orbit(app, drawing, 45)
    if cancel == "escape":
        QTest.keyClick(app, Qt.Key.Key_Escape)
        assert drawing.selection.selected == (0,)
    elif cancel == "exit":
        app.plan_tools.set_open(False)
    else:
        QApplication.sendEvent(app, QEvent(QEvent.Type.WindowDeactivate))
    QTest.keyRelease(app, Qt.Key.Key_R)
    assert drawing.segments() == original and len(drawing.undo_stack) == count
    assert not drawing.rotation.items and all(item.opacity() == 1 for item in drawing.items)


def test_rotating_outside_frozen_center_is_rejected_without_clipping(editor):
    app, drawing = editor
    drawing.apply_edit([line(100, 20, 400, 20)])
    app.plan_tools.select_button.click()
    drawing.selection.set_selected([0])
    original = drawing.segments()
    QTest.keyPress(app, Qt.Key.Key_R)
    orbit(app, drawing, 90)
    assert not drawing.rotation.valid
    QTest.keyRelease(app, Qt.Key.Key_R)
    assert drawing.segments() == original


def test_oblique_saved_model_reopens_with_cuts_regions_and_unchanged_lengths(editor, tmp_path):
    app, drawing = editor
    rotated = rotate_degrees(rectangle_segments(250, 200, 200, 100, "#123456"), 35)
    assert drawing.apply_edit(rotated)
    app.plan_tools.set_open(False)
    app.session.csv_file = str(tmp_path / "angled.csv")
    assert app.save_survey() and app.open_survey(str(tmp_path / "angled.csv"))
    assert drawing.segments() == normalize_segments(rotated)
    assert len(drawing.regions.faces) == 1


def test_auto_repeat_release_does_not_end_a_held_gesture(editor):
    app, drawing = editor
    drawing.begin_placement(200, 100, QPointF(300, 200))
    QTest.keyPress(app, Qt.Key.Key_R)
    QApplication.sendEvent(app, QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_R, Qt.KeyboardModifier.NoModifier, "r", True))
    assert drawing.rotation.active and drawing.pending_size == (200, 100)
    orbit(app, drawing, 45)
    QTest.keyRelease(app, Qt.Key.Key_R)
    assert drawing.pending_angle == 45


def test_held_r_consumes_point_capture_and_placement_clicks(editor):
    app, drawing = editor
    drawing.line.begin_placement(200, QPointF(300, 250))
    app.plan_tools.select_tool("line")
    drawing.line.begin_placement(200, QPointF(300, 250))
    QTest.keyPress(app, Qt.Key.Key_R)
    position = orbit(app, drawing, 45)
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=position)
    assert drawing.rotation.active and drawing.segments() is None
    QTest.keyRelease(app, Qt.Key.Key_R)
    assert drawing.line.pending_length == 200 and drawing.segments() is None


def test_center_dead_zone_preserves_last_angle_and_avoids_a_jump(editor):
    app, drawing = editor
    drawing.begin_placement(200, 100, QPointF(300, 200))
    QTest.keyPress(app, Qt.Key.Key_R)
    orbit(app, drawing, 45)
    pivot = drawing.rotation.pivot
    move(app.floorplan_view, app.floorplan_view.mapFromScene(QPointF(*pivot)))
    assert drawing.rotation.angle == 45
    QTest.keyRelease(app, Qt.Key.Key_R)


def test_split_order_remains_geometric_for_nearly_vertical_rotated_segments():
    pieces = normalize_segments([line(300.00000000000006, 100, 300, 400), line(200, 250, 400, 250)])
    vertical = [piece for piece in pieces if abs(piece["x2"] - piece["x1"]) < 1e-9]
    assert len(vertical) == 2
    assert vertical[0]["y1"] == 100 and vertical[0]["y2"] == 250
    assert vertical[1]["y1"] == 250 and vertical[1]["y2"] == 400


@pytest.mark.parametrize("angle", [5, 35, 90, 175, 315])
def test_overlapping_rotated_rectangles_keep_all_three_real_closed_faces(angle):
    source = rectangle_segments(100, 100, 200, 200, "#123456") + rectangle_segments(200, 200, 200, 200, "#abcdef")
    rotated = rotate_degrees(source, angle)
    normalized = normalize_segments(rotated)
    assert len(normalized) == 12 and normalize_segments(normalized) == normalized
    regions = closed_plan_regions(normalized)
    assert len(regions.faces) == 3
    total = 0
    for face in regions.faces:
        total += abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(face, face[1:] + face[:1]))) / 2
    assert total == pytest.approx(70000, abs=1e-7)


def test_oblique_shape_does_not_snap_an_empty_bounding_box_corner():
    source = rotate_degrees(rectangle_segments(250, 200, 200, 100, "#123456"), 45)
    left, top, _, _ = segment_bounds(source)
    result = PlanSnapper([line(left, top, left + 1, top)]).snap_geometry(source, (0, 0, 900, 600), 10)
    assert result.x == result.y == 0 and not result.guides
