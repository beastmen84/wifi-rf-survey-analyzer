"""Eraser geometry and native Qt gestures preserve whole independent segments."""
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from survey.plan_drawing import drawing_segments, rectangle_segments
from survey.plan_erasing import intersecting_segments, nearest_segment
from tests.test_rectangle_design import editor, move, drag
from tests.test_capture_adapter import window, qt_app


@pytest.mark.parametrize("point,expected", [((200, 100), 0), ((300, 150), 1),
    ((200, 200), 2), ((100, 150), 3), ((200, 107), 0), ((200, 108), None),
    ((310, 150), None), ((90, 90), None), ((300, 100), 1)])
def test_click_picks_nearest_finite_segment(point, expected):
    lines = rectangle_segments(100, 100, 200, 100, "#123456")
    assert nearest_segment(lines, *point, 7) == expected


def test_overlapping_segments_pick_only_topmost_even_with_different_colors():
    lines = rectangle_segments(100, 100, 200, 100, "#123456")
    lines += rectangle_segments(100, 100, 200, 100, "#abcdef")
    assert nearest_segment(lines, 200, 100, 7) == 4
    assert intersecting_segments(lines, 150, 99, 250, 101) == (0, 4)


@pytest.mark.parametrize("box,expected", [((90, 90, 310, 210), (0, 1, 2, 3)),
    ((310, 210, 90, 90), (0, 1, 2, 3)), ((150, 90, 250, 110), (0,)),
    ((150, 120, 250, 180), ()), ((150, 100, 250, 100), (0,)),
    ((200, 90, 200, 210), (0, 2)), ((0, 0, 99, 99), ()),
    ((300, 200, 310, 210), (1, 2))])
def test_area_selects_whole_segments_on_actual_finite_intersection(box, expected):
    lines = rectangle_segments(100, 100, 200, 100, "#123456")
    assert intersecting_segments(lines, *box) == expected


@pytest.fixture
def eraser_editor(editor):
    app, drawing = editor
    drawing.commit(QRectF(100, 100, 200, 100))
    drawing.undo_stack.clear()
    drawing.redo_stack.clear()
    app.session.dirty = False
    app.plan_tools.eraser_button.click()
    return app, drawing, drawing.eraser


def scene_point(app, x, y):
    return app.floorplan_view.mapFromScene(QPointF(x, y))


def test_hover_then_click_erases_one_side_only_on_release_and_never_captures(eraser_editor):
    app, drawing, eraser = eraser_editor
    view = app.floorplan_view
    point = scene_point(app, 200, 100)
    captures = []
    view.surveyPointRequested.connect(lambda *args: captures.append(args))
    with patch("qt_ui.qt_rectangle_design.RectangleSizeDialog.exec") as prompt:
        move(view, point)
        assert eraser.targets == (0,) and len(eraser.highlights) == 2
        assert drawing.measurement.isVisible() and not app.session.dirty
        QTest.mousePress(view.viewport(), Qt.MouseButton.RightButton, pos=point)
        assert len(drawing.segments()) == 4 and not app.session.dirty
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.RightButton, pos=point)
        prompt.assert_not_called()
    assert len(drawing.segments()) == 3 and app.session.dirty and not captures
    assert not eraser.highlights and eraser.area is None
    assert len(drawing.undo_stack) == 1
    assert app.plan_tools.eraser_button.isChecked() and not app.plan_tools.rectangle_button.isChecked()


@pytest.mark.parametrize("reverse", [False, True])
def test_drag_previews_count_then_erases_all_touched_sides_in_one_undo_action(eraser_editor, reverse):
    app, drawing, eraser = eraser_editor
    view = app.floorplan_view
    first, last = scene_point(app, 90, 90), scene_point(app, 310, 210)
    if reverse:
        first, last = last, first
    original = drawing.segments()
    QTest.mousePress(view.viewport(), Qt.MouseButton.RightButton, pos=first)
    move(view, last, Qt.MouseButton.RightButton)
    assert len(eraser.targets) == 4 and eraser.area.isVisible()
    assert drawing.measurement.text().startswith("4 ")
    assert drawing.segments() == original and not app.session.dirty
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.RightButton, pos=last)
    assert drawing.segments() == [] and len(drawing.undo_stack) == 1
    app.plan_tools.undo_button.click()
    assert drawing.segments() == original
    app.plan_tools.redo_button.click()
    assert drawing.segments() == []


def test_partial_area_removes_whole_crossed_segment_and_keeps_other_sides(eraser_editor):
    app, drawing, eraser = eraser_editor
    original = drawing.segments()
    drag(app.floorplan_view, scene_point(app, 150, 90), scene_point(app, 250, 110))
    assert drawing.segments() == original[1:]


@pytest.mark.parametrize("gesture", ["click", "inside", "empty", "pan"])
def test_no_hit_or_left_pan_never_changes_document_or_history(eraser_editor, gesture):
    app, drawing, eraser = eraser_editor
    view = app.floorplan_view
    original = drawing.segments()
    if gesture == "click":
        QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=scene_point(app, 200, 150))
    elif gesture in {"inside", "empty"}:
        first, last = ((150, 120), (250, 180)) if gesture == "inside" else ((350, 250), (450, 350))
        drag(view, scene_point(app, *first), scene_point(app, *last))
    else:
        move(view, scene_point(app, 200, 100))
        assert eraser.highlights
        view.set_zoom(view.zoom_level * 2)
        start = QPoint(view.viewport().width() // 2, view.viewport().height() // 2)
        before = view.mapToScene(start)
        QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
        move(view, start + QPoint(60, 40), Qt.MouseButton.LeftButton)
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=start + QPoint(60, 40))
        assert view.mapToScene(start) != before
    assert drawing.segments() == original and not app.session.dirty
    assert not drawing.undo_stack and not drawing.redo_stack


@pytest.mark.parametrize("reason", ["escape", "switch", "close", "deactivate", "undo"])
def test_cancelled_erase_does_not_commit_after_late_release(eraser_editor, reason):
    app, drawing, eraser = eraser_editor
    view = app.floorplan_view
    first, last = scene_point(app, 90, 90), scene_point(app, 310, 210)
    original = drawing.segments()
    QTest.mousePress(view.viewport(), Qt.MouseButton.RightButton, pos=first)
    move(view, last, Qt.MouseButton.RightButton)
    assert eraser.area is not None
    if reason == "escape":
        QTest.keyClick(app, Qt.Key.Key_Escape)
        assert app.plan_tools.open
    elif reason == "switch":
        app.plan_tools.rectangle_button.click()
    elif reason == "close":
        app.plan_tools.set_open(False)
    elif reason == "deactivate":
        QApplication.sendEvent(app, QEvent(QEvent.Type.WindowDeactivate))
    else:
        # A real undo operation cancels the provisional selection before redraw.
        drawing.undo_stack.append(dict(segments=original, labels=[]))
        drawing.undo()
        app.session.dirty = False
    assert eraser.origin is None and not eraser.highlights and eraser.area is None
    with patch("qt_ui.qt_rectangle_design.RectangleSizeDialog.exec") as prompt:
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.RightButton, pos=last)
        prompt.assert_not_called()
    assert drawing.segments() == original and not app.session.dirty


def test_tool_switch_cancels_numeric_preview_and_preserves_snap_preferences(eraser_editor):
    app, drawing, eraser = eraser_editor
    tools = app.plan_tools
    assert not tools.snap_button.isEnabled() and not tools.color_button.isEnabled()
    tools.rectangle_button.click()
    tools.snap_button.click()
    drawing.begin_placement(150, 100)
    tools.eraser_button.click()
    assert drawing.pending_size is None and drawing.preview is None and not drawing.snap_items
    assert tools.snap_button.isChecked() and not tools.snap_button.isEnabled()
    tools.eraser_button.click()  # The active tool remains selected.
    assert tools.eraser_button.isChecked()
    tools.rectangle_button.click()
    assert tools.snap_button.isChecked() and tools.snap_button.isEnabled() and tools.color_button.isEnabled()


@pytest.mark.parametrize("zoom", [1, 2, 4])
def test_pick_tolerance_tracks_screen_pixels_instead_of_scene_zoom(eraser_editor, zoom):
    app, drawing, eraser = eraser_editor
    view = app.floorplan_view
    view.resetTransform()
    view.scale(zoom, zoom)
    assert eraser.pick(QPointF(200, 100 + (app.spx(6) - 1) / zoom)) == (0,)
    assert eraser.pick(QPointF(200, 100 + (app.spx(6) + 2) / zoom + 1)) == ()


def test_single_duplicate_click_erases_one_segment_and_area_erases_all_duplicates(eraser_editor):
    app, drawing, eraser = eraser_editor
    original = drawing.segments()
    drawing.store(original + rectangle_segments(100, 100, 200, 100, "#abcdef"))
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=scene_point(app, 200, 100))
    assert len(drawing.segments()) == 7 and drawing.segments()[:4] == original
    drag(app.floorplan_view, scene_point(app, 150, 90), scene_point(app, 250, 110))
    assert len(drawing.segments()) == 6 and original[0] not in drawing.segments()


def test_erased_targets_leave_snap_index_and_undo_restores_them(eraser_editor):
    app, drawing, eraser = eraser_editor
    drag(app.floorplan_view, scene_point(app, 90, 90), scene_point(app, 310, 210))
    assert not drawing.snapper.snap(100, 100, 0, 0, (0, 0, 900, 600), 10).guides
    drawing.undo()
    assert drawing.snapper.snap(100, 100, 0, 0, (0, 0, 900, 600), 10).guides
    drawing.redo()
    assert not drawing.snapper.snap(100, 100, 0, 0, (0, 0, 900, 600), 10).guides


def test_hover_hide_and_scene_replacement_clear_transient_items_safely(eraser_editor, qt_app):
    app, drawing, eraser = eraser_editor
    view = app.floorplan_view
    point = scene_point(app, 200, 100)
    baseline = len(view.scene.items())
    for _ in range(8):
        move(view, point)
    assert len(view.scene.items()) == baseline + 2
    drawing.hide_preview()
    assert not any(item.isVisible() for item in eraser.highlights)
    move(view, point)
    assert all(item.isVisible() for item in eraser.highlights)
    with patch.object(app, "choose_current_survey_close_action", return_value="discard"):
        from tests.test_blank_plan import create_survey
        create_survey(app, width=20, height=15)
    qt_app.processEvents()
    assert not eraser.highlights and eraser.area is None and eraser.origin is None
    assert not drawing.undo_stack and drawing.segments() is None


def test_erase_to_empty_survives_save_reopen_and_removes_baked_pixels(eraser_editor, tmp_path):
    app, drawing, eraser = eraser_editor
    app.plan_tools.set_open(False)
    app.session.csv_file = str(tmp_path / "erase.csv")
    assert app.save_survey()
    with Image.open(tmp_path / "erase.png") as image:
        assert image.getpixel((200, 100)) != (255, 255, 255)
    app.plan_tools.set_open(True)
    drag(app.floorplan_view, scene_point(app, 90, 90), scene_point(app, 310, 210))
    app.plan_tools.set_open(False)
    assert app.save_survey()
    assert app.open_survey(str(tmp_path / "erase.csv"))
    assert drawing_segments(app.session.metadata) == [] and not drawing.items
    with Image.open(tmp_path / "erase.png") as image:
        assert image.getpixel((200, 100)) == (255, 255, 255)


def test_empty_erase_does_not_discard_redo_or_mark_a_new_sheet_dirty(editor):
    app, drawing = editor
    drawing.commit(QRectF(100, 100, 200, 100))
    drawing.undo()
    app.session.dirty = False
    app.plan_tools.eraser_button.click()
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=scene_point(app, 200, 100))
    assert not app.session.dirty and len(drawing.redo_stack) == 1
    drawing.redo()
    assert len(drawing.segments()) == 4


def test_release_without_move_still_selects_area_and_history_branches(eraser_editor):
    app, drawing, eraser = eraser_editor
    view = app.floorplan_view
    original = drawing.segments()
    QTest.mousePress(view.viewport(), Qt.MouseButton.RightButton, pos=scene_point(app, 90, 90))
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.RightButton, pos=scene_point(app, 310, 210))
    assert drawing.segments() == []
    drawing.undo()
    assert drawing.redo_stack
    QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=scene_point(app, 200, 100))
    assert drawing.segments() == original[1:] and not drawing.redo_stack
    drawing.undo()
    assert drawing.segments() == original


def test_erase_save_failure_restores_old_files_and_keeps_unsaved_vector_edit(eraser_editor, tmp_path):
    app, drawing, eraser = eraser_editor
    app.plan_tools.set_open(False)
    app.session.csv_file = str(tmp_path / "failure.csv")
    assert app.save_survey()
    old_csv = (tmp_path / "failure.csv").read_bytes()
    old_png = (tmp_path / "failure.png").read_bytes()
    app.plan_tools.set_open(True)
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=scene_point(app, 200, 100))
    erased = drawing.segments()
    assert len(erased) == 3
    app.plan_tools.set_open(False)
    with (patch.object(app.session, "save", side_effect=OSError("disk full")),
          patch("qt_ui.qt_session_workflow.QMessageBox.warning")):
        assert not app.save_survey()
    assert (tmp_path / "failure.csv").read_bytes() == old_csv
    assert (tmp_path / "failure.png").read_bytes() == old_png
    assert drawing.segments() == erased and app.session.dirty
    drawing.undo()
    assert len(drawing.segments()) == 4


def test_area_outside_sheet_is_clamped_and_can_erase_edge_segments(editor):
    app, drawing = editor
    bounds = app.floorplan_view.scene.sceneRect()
    drawing.commit(QRectF(bounds.width() - 80, 100, 80, 100))
    app.plan_tools.eraser_button.click()
    first = scene_point(app, bounds.width() - 40, 90)
    last = scene_point(app, bounds.width() + 40, 210)
    view = app.floorplan_view
    QTest.mousePress(view.viewport(), Qt.MouseButton.RightButton, pos=first)
    move(view, last, Qt.MouseButton.RightButton)
    assert drawing.eraser.area.rect().right() == bounds.right()
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.RightButton, pos=last)
    assert len(drawing.segments()) == 1
