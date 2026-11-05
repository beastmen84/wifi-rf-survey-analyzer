"""Editable cuts, line gestures and rigid selection transformations."""
import json
from copy import deepcopy
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtCore import QEvent, QLineF, QPoint, QPointF, QRectF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit

from qt_ui.qt_line_design import LineSizeDialog
from survey.plan_drawing import PLAN_DRAWING_KEY, drawing_segments, encode_drawing, rectangle_segments
from survey.plan_geometry import rotate_segments, segment_bounds, split_segments, translate_segments
from tests.test_rectangle_design import editor, move, drag
from tests.test_capture_adapter import window, qt_app


def line(x1, y1, x2, y2, color="#123456"):
    return dict(x1=x1, y1=y1, x2=x2, y2=y2, color=color)


def point(app, x, y):
    return app.floorplan_view.mapFromScene(QPointF(x, y))


def test_intersecting_rectangles_split_into_independently_editable_fragments():
    lines = rectangle_segments(100, 100, 200, 200, "#123456")
    lines += rectangle_segments(200, 200, 200, 200, "#abcdef")
    original = deepcopy(lines)
    result, sources = split_segments(lines, with_sources=True)
    assert len(result) == len(sources) == 12 and lines == original
    assert line(300, 100, 300, 200) in result and line(300, 200, 300, 300) in result
    assert split_segments(result) == result
    assert all(piece["color"] == lines[source]["color"] for piece, source in zip(result, sources))


@pytest.mark.parametrize("lines,expected", [
    ([line(100, 100, 300, 100), line(200, 50, 200, 150)], 4),
    ([line(100, 100, 300, 100), line(200, 100, 200, 150)], 3),
    ([line(300, 100, 100, 100), line(200, 150, 200, 50)], 4),
    ([line(100, 100, 300, 100), line(200, 100, 400, 100)], 4),
    ([line(100, 100, 300, 100), line(300, 100, 400, 100)], 2),
    ([line(100, 100, 300, 100), line(100, 100, 300, 100)], 2),
    ([line(100, 100, 300, 100), line(300.00001, 50, 300.00001, 150)], 2),
])
def test_finite_cross_t_collinear_endpoint_and_gap_semantics(lines, expected):
    result = split_segments(lines)
    assert len(result) == expected and split_segments(result) == result


def test_split_limits_fail_atomically_and_old_documents_get_cuts_without_mutation():
    lines = [line(100, 100, 300, 100), line(200, 50, 200, 150)]
    with pytest.raises(ValueError):
        split_segments(lines, limit=3)
    raw = json.dumps(dict(version=1, segments=lines))
    metadata = {"_generated_floorplan": "1", PLAN_DRAWING_KEY: raw}
    assert len(drawing_segments(metadata)) == 4 and metadata[PLAN_DRAWING_KEY] == raw
    assert len(json.loads(encode_drawing(lines))["segments"]) == 4


def test_quarter_turn_is_rigid_and_four_turns_restore_exact_source():
    lines = [line(100, 100, 300, 100), line(300, 100, 300, 200)]
    rotated = rotate_segments(lines)
    assert segment_bounds(rotated) == (150, 50, 250, 250)
    assert rotate_segments(lines, 4) == lines
    for original, changed in zip(lines, rotated):
        assert abs(original["x2"] - original["x1"]) + abs(original["y2"] - original["y1"]) == (
            abs(changed["x2"] - changed["x1"]) + abs(changed["y2"] - changed["y1"]))


def test_eraser_deletes_only_the_fragment_between_intersections_and_undo_restores(editor):
    app, drawing = editor
    drawing.commit(QRectF(100, 100, 200, 200))
    drawing.commit(QRectF(200, 200, 200, 200))
    original = drawing.segments()
    assert len(original) == 12
    app.plan_tools.eraser_button.click()
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=point(app, 300, 250))
    assert len(drawing.segments()) == 11
    assert line(300, 100, 300, 200, "#263238") in drawing.segments()
    assert line(300, 200, 300, 300, "#263238") not in drawing.segments()
    drawing.undo()
    assert drawing.segments() == original


@pytest.mark.parametrize("first,last,horizontal", [((100, 100), (350, 130), True),
    ((350, 100), (100, 130), True), ((100, 100), (130, 350), False), ((100, 350), (130, 100), False)])
def test_line_drag_locks_one_axis_and_never_captures_rf(editor, first, last, horizontal):
    app, drawing = editor
    app.plan_tools.line_button.click()
    captures = []
    app.floorplan_view.surveyPointRequested.connect(lambda *args: captures.append(args))
    drag(app.floorplan_view, point(app, *first), point(app, *last))
    lines = drawing.segments()
    assert len(lines) == 1 and not captures
    assert (lines[0]["y1"] == lines[0]["y2"]) == horizontal
    assert len(drawing.undo_stack) == 1


def test_line_click_prompts_only_for_length_and_r_rotates_all_four_preview_directions(editor):
    app, drawing = editor
    app.plan_tools.line_button.click()
    first = point(app, 200, 200)
    with (patch("qt_ui.qt_line_design.LineSizeDialog.exec", return_value=QDialog.DialogCode.Accepted) as prompt,
          patch("qt_ui.qt_line_design.LineSizeDialog.length", return_value=150)):
        QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=first)
        initial = drawing.line.preview.line()
        assert initial.dx() == 150 and initial.dy() == 0
        for expected in ((0, 150), (-150, 0), (0, -150), (150, 0)):
            QTest.keyClick(app, Qt.Key.Key_R)
            preview = drawing.line.preview.line()
            assert (preview.dx(), preview.dy()) == expected and preview.length() == 150
            assert not app.session.dirty and drawing.segments() is None
        QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=point(app, 400, 300))
        assert prompt.call_count == 1
    assert len(drawing.segments()) == 1 and drawing.line.pending_length is None


def test_line_numeric_imperial_length_and_rotation_fit_constraints(editor):
    app, drawing = editor
    app.measurement_system = "imperial"
    dialog = LineSizeDialog(app, QRectF(0, 0, 900, 600), 50)
    dialog.length_spin.setValue(10)
    assert dialog.length() == pytest.approx(152.4)
    dialog.deleteLater()
    app.plan_tools.line_button.click()
    drawing.line.begin_placement(800, QPointF(100, 100))
    assert drawing.line.preview.line().length() == 800
    before = drawing.line.turns
    QTest.keyClick(app, Qt.Key.Key_R)
    assert drawing.line.turns == before and not app.session.dirty
    assert app.status.currentMessage() == app.tr("design_rotation_outside")


def test_rectangle_preview_r_swaps_measurements_without_dirty_or_history(editor):
    app, drawing = editor
    drawing.begin_placement(250, 100, QPointF(400, 300))
    QTest.keyClick(app, Qt.Key.Key_R, Qt.KeyboardModifier.ShiftModifier)
    assert drawing.pending_size == (100, 250)
    assert drawing.preview.rect().size().width() == 100 and drawing.preview.rect().height() == 250
    assert not app.session.dirty and not drawing.undo_stack
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=point(app, 400, 300))
    left, top, right, bottom = segment_bounds(drawing.segments())
    assert (left, top) == pytest.approx((400, 300), abs=1)
    assert (right - left, bottom - top) == (100, 250)


@pytest.fixture
def selection_editor(editor):
    app, drawing = editor
    drawing.commit(QRectF(100, 100, 200, 100))
    drawing.undo_stack.clear()
    drawing.redo_stack.clear()
    app.session.dirty = False
    app.plan_tools.select_button.click()
    drag(app.floorplan_view, point(app, 90, 90), point(app, 310, 210))
    assert drawing.selection.selected == (0, 1, 2, 3)
    return app, drawing, drawing.selection


def test_select_click_one_fragment_and_marquee_many_does_not_dirty(selection_editor):
    app, drawing, selection = selection_editor
    assert not app.session.dirty and not drawing.undo_stack
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=point(app, 200, 100))
    assert selection.selected == (0,)
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=point(app, 500, 400))
    assert not selection.selected and not app.session.dirty


def test_selected_rotation_is_one_undo_action_and_preserves_selection(selection_editor):
    app, drawing, selection = selection_editor
    original = drawing.segments()
    QTest.keyClick(app, Qt.Key.Key_R)
    assert drawing.segments() == rotate_segments(original)
    assert len(selection.selected) == 4 and len(drawing.undo_stack) == 1
    drawing.undo()
    assert drawing.segments() == original and not selection.selected
    drawing.redo()
    assert segment_bounds(drawing.segments()) == (150, 50, 250, 250)


def test_move_follows_cursor_then_right_press_places_rigid_group_once(selection_editor):
    app, drawing, selection = selection_editor
    original = drawing.segments()
    move(app.floorplan_view, point(app, 200, 150))
    QTest.keyClick(app, Qt.Key.Key_M)
    assert selection.moving and not app.session.dirty
    target = point(app, 450, 350)
    move(app.floorplan_view, target)
    expected = deepcopy(selection.move_preview)
    assert drawing.segments() == original
    assert segment_bounds(expected) == pytest.approx((350, 300, 550, 400), abs=1)
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=target)
    assert drawing.segments() == expected and not selection.moving
    assert len(selection.selected) == 4 and len(drawing.undo_stack) == 1
    drawing.undo()
    assert drawing.segments() == original


@pytest.mark.parametrize("cancel", ["escape", "tool", "close", "deactivate", "undo"])
def test_provisional_move_cancel_keeps_original_model_and_restores_opacity(selection_editor, cancel):
    app, drawing, selection = selection_editor
    original = drawing.segments()
    QTest.keyClick(app, Qt.Key.Key_M)
    move(app.floorplan_view, point(app, 500, 350))
    if cancel == "escape":
        QTest.keyClick(app, Qt.Key.Key_Escape)
        assert app.plan_tools.open
    elif cancel == "tool":
        app.plan_tools.line_button.click()
    elif cancel == "close":
        app.plan_tools.set_open(False)
    elif cancel == "deactivate":
        QApplication.sendEvent(app, QEvent(QEvent.Type.WindowDeactivate))
    else:
        drawing.undo_stack.append(original)
        drawing.undo()
        app.session.dirty = False
    assert not selection.moving and drawing.segments() == original and not app.session.dirty
    assert all(item.opacity() == 1 for item in drawing.items)


def test_rotation_during_move_is_provisional_and_stays_inside_sheet(selection_editor):
    app, drawing, selection = selection_editor
    original = drawing.segments()
    QTest.keyClick(app, Qt.Key.Key_M)
    QTest.keyClick(app, Qt.Key.Key_R)
    move(app.floorplan_view, point(app, 890, 590))
    left, top, right, bottom = segment_bounds(selection.move_preview)
    assert (right - left, bottom - top) == (100, 200)
    assert right <= 900 and bottom <= 600 and drawing.segments() == original
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=point(app, 890, 590))
    assert not selection.moving and len(drawing.undo_stack) == 1


def test_zero_move_preserves_history_and_redo(selection_editor):
    app, drawing, selection = selection_editor
    original = drawing.segments()
    drawing.redo_stack.append(original)
    move(app.floorplan_view, point(app, 200, 150))
    QTest.keyClick(app, Qt.Key.Key_M)
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=point(app, 200, 150))
    assert not app.session.dirty and not drawing.undo_stack and drawing.redo_stack
    assert not selection.moving


def test_shortcuts_leave_text_fields_and_modifiers_alone(selection_editor, qt_app):
    app, drawing, selection = selection_editor
    original = drawing.segments()
    QTest.keyClick(app, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
    assert drawing.segments() == original
    text = QLineEdit(app)
    text.show()
    text.setFocus()
    qt_app.processEvents()
    QTest.keyClicks(text, "rMmR")
    assert text.text() == "rMmR" and drawing.segments() == original and not selection.moving
    text.deleteLater()


def test_move_creates_new_cuts_and_fragment_selection_survives_save_reopen(editor, tmp_path):
    app, drawing = editor
    drawing.apply_edit([line(100, 200, 500, 200), line(300, 300, 300, 400)])
    app.plan_tools.select_button.click()
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=point(app, 300, 350))
    selection = drawing.selection
    move(app.floorplan_view, point(app, 300, 350))
    QTest.keyClick(app, Qt.Key.Key_M)
    target = point(app, 300, 200)
    move(app.floorplan_view, target)
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=target)
    assert len(drawing.segments()) == 4 and len(selection.selected) == 2
    assert len(drawing.regions.faces) == 0
    original = drawing.segments()
    app.plan_tools.set_open(False)
    app.session.csv_file = str(tmp_path / "edited.csv")
    assert app.save_survey() and app.open_survey(str(tmp_path / "edited.csv"))
    assert drawing.segments() == original
    with Image.open(tmp_path / "edited.png") as image:
        assert image.getpixel((300, 175)) != (255, 255, 255)


def test_legacy_split_model_is_persisted_on_save_and_failed_save_rolls_back(editor, tmp_path):
    app, drawing = editor
    lines = [line(100, 100, 300, 100), line(200, 50, 200, 150)]
    raw = json.dumps(dict(version=1, segments=lines))
    app.session.metadata[PLAN_DRAWING_KEY] = raw
    app.refresh_session_labels()
    assert len(drawing.segments()) == 4 and app.session.metadata[PLAN_DRAWING_KEY] == raw
    app.plan_tools.set_open(False)
    app.session.csv_file = str(tmp_path / "legacy.csv")
    with (patch.object(app.session, "save", side_effect=OSError("disk full")),
          patch("qt_ui.qt_session_workflow.QMessageBox.warning")):
        assert not app.save_survey()
    assert app.session.metadata[PLAN_DRAWING_KEY] == raw
    assert app.save_survey()
    assert len(json.loads(app.session.metadata[PLAN_DRAWING_KEY])["segments"]) == 4
    assert app.open_survey(str(tmp_path / "legacy.csv")) and len(drawing.segments()) == 4


def test_line_drag_endpoint_snaps_without_changing_fixed_axis(editor):
    app, drawing = editor
    drawing.apply_edit([line(300, 50, 300, 250)])
    app.plan_tools.line_button.click()
    drag(app.floorplan_view, point(app, 100, 150), point(app, 304, 160))
    last = drawing.segments()[-1]
    assert last["x2"] == 300 and last["y1"] == last["y2"]


def test_rotating_selected_fragment_outside_sheet_is_rejected_atomically(editor):
    app, drawing = editor
    drawing.apply_edit([line(100, 0, 300, 0)])
    app.plan_tools.select_button.click()
    drawing.selection.set_selected([0])
    original = drawing.segments()
    app.session.dirty = False
    count = len(drawing.undo_stack)
    QTest.keyClick(app, Qt.Key.Key_R)
    assert drawing.segments() == original and not app.session.dirty
    assert len(drawing.undo_stack) == count and drawing.selection.selected == (0,)


def test_moving_selection_snaps_to_unselected_geometry_and_alt_bypasses(editor):
    app, drawing = editor
    drawing.apply_edit([line(100, 100, 200, 100), line(400, 300, 500, 300)])
    app.plan_tools.select_button.click()
    selection = drawing.selection
    selection.set_selected([0])
    move(app.floorplan_view, point(app, 100, 100))
    QTest.keyClick(app, Qt.Key.Key_M)
    move(app.floorplan_view, point(app, 404, 304))
    assert segment_bounds(selection.move_preview) == (400, 300, 500, 300)
    assert drawing.snap_guides
    QTest.keyPress(app, Qt.Key.Key_Alt)
    assert not drawing.snap_guides
    assert segment_bounds(selection.move_preview) != (400, 300, 500, 300)
    QTest.keyRelease(app, Qt.Key.Key_Alt)
    assert segment_bounds(selection.move_preview) == (400, 300, 500, 300)


def test_rotation_during_a_new_selection_gesture_does_not_transform_old_selection(selection_editor):
    app, drawing, selection = selection_editor
    original = drawing.segments()
    start, end = point(app, 150, 90), point(app, 250, 110)
    QTest.mousePress(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=start)
    move(app.floorplan_view, end, Qt.MouseButton.RightButton)
    QTest.keyClick(app, Qt.Key.Key_R)
    assert drawing.segments() == original and selection.origin is not None
    QTest.mouseRelease(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=end)
    assert selection.selected == (0,) and not app.session.dirty


@pytest.mark.parametrize("geometry", [QLineF(float("nan"), 10, 30, 30), QLineF(-10, 10, 30, 10),
                                     QLineF(10, 10, 10000, 10)])
def test_invalid_line_commit_does_not_mutate_model_or_history(editor, geometry):
    app, drawing = editor
    with pytest.raises(ValueError):
        drawing.line.commit(geometry)
    assert drawing.segments() is None and not app.session.dirty and not drawing.undo_stack
