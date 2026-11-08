"""Rectangle gestures must never start RF capture or lose persisted geometry."""
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

from app_core.units import meters_to_display_units
from qt_ui.qt_rectangle_design import RectangleSizeDialog
from survey.plan_drawing import (PLAN_DRAWING_KEY, drawing_segments, encode_drawing,
                                rectangle_segments, render_plan_drawing)
from tests.test_blank_plan import create_survey
from tests.test_capture_adapter import window, qt_app


@pytest.fixture
def editor(window, qt_app):
    create_survey(window, width=18, height=12)
    window.resize(1400, 950)
    window.show()
    qt_app.processEvents()
    window.plan_tools.set_open(True)
    window.plan_tools.select_tool('rectangle')
    yield window, window.plan_tools.controller
    window.session.dirty = False
    window.hide()


def move(view, position, buttons=Qt.MouseButton.NoButton):
    event = QMouseEvent(QEvent.Type.MouseMove, QPointF(position), QPointF(view.viewport().mapToGlobal(position)),
                        Qt.MouseButton.NoButton, buttons, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(view.viewport(), event)


def drag(view, start, end):
    QTest.mousePress(view.viewport(), Qt.MouseButton.RightButton, pos=start)
    move(view, end, Qt.MouseButton.RightButton)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.RightButton, pos=end)


@pytest.mark.parametrize("reverse", [False, True])
def test_right_drag_previews_measures_and_commits_four_independent_segments(editor, qt_app, reverse):
    window, controller = editor
    view = window.floorplan_view
    first, last = view.mapFromScene(QPointF(200, 150)), view.mapFromScene(QPointF(500, 350))
    if reverse:
        first, last = last, first
    captures = []
    view.surveyPointRequested.connect(lambda *args: captures.append(args))
    QTest.mousePress(view.viewport(), Qt.MouseButton.RightButton, pos=first)
    move(view, last, Qt.MouseButton.RightButton)
    assert controller.preview is not None and controller.measurement.isVisible()
    assert " m" in controller.measurement.text()
    assert not window.session.dirty and drawing_segments(window.session.metadata) is None
    expected = controller.preview.rect()
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.RightButton, pos=last)
    lines = drawing_segments(window.session.metadata)
    assert len(lines) == len(controller.items) == 4 and window.session.dirty
    assert lines[0]["x1"] == pytest.approx(expected.left())
    assert lines[1]["y2"] == pytest.approx(expected.bottom())
    assert not captures and controller.preview is None
    assert window.plan_tools.undo_button.isEnabled()


def test_click_asks_for_size_once_and_next_press_places_without_reopening(editor, qt_app):
    window, controller = editor
    view = window.floorplan_view
    point = view.mapFromScene(QPointF(250, 200))
    with (patch("qt_ui.qt_rectangle_design.RectangleSizeDialog.exec", return_value=QDialog.DialogCode.Accepted) as prompt,
          patch("qt_ui.qt_rectangle_design.RectangleSizeDialog.dimensions", return_value=(150, 100))):
        QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=point)
        assert controller.pending_size == (150, 100)
        assert drawing_segments(window.session.metadata) is None
        target = view.mapFromScene(QPointF(500, 300))
        move(view, target)
        QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=target)
        assert prompt.call_count == 1
    assert len(drawing_segments(window.session.metadata)) == 4
    assert controller.pending_size is None


def test_esc_cancels_draft_first_then_exits_and_restores_point_capture(editor, qt_app):
    window, controller = editor
    controller.begin_placement(150, 100)
    QTest.keyClick(window, Qt.Key.Key_Escape)
    assert controller.pending_size is None and window.plan_tools.open
    assert window.plan_tools.active_tool is None
    assert drawing_segments(window.session.metadata) is None and not window.session.dirty
    QTest.keyClick(window, Qt.Key.Key_Escape)
    assert not window.floorplan_view.design_mode_active
    view = window.floorplan_view
    view.surveyPointRequested.disconnect(window.create_point_from_floorplan)
    captures = []
    view.surveyPointRequested.connect(lambda *args: captures.append(args))
    QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=QPoint(400, 100))
    assert len(captures) == 1


def test_cancelled_numeric_prompt_and_zero_height_drag_do_not_dirty_survey(editor, qt_app):
    window, controller = editor
    view = window.floorplan_view
    start = view.mapFromScene(QPointF(200, 200))
    with patch("qt_ui.qt_rectangle_design.RectangleSizeDialog.exec", return_value=QDialog.DialogCode.Rejected):
        QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=start)
    drag(view, start, start + QPoint(100, 0))
    assert drawing_segments(window.session.metadata) is None and not window.session.dirty


@pytest.mark.parametrize("system", ["metric", "imperial"])
def test_numeric_dimensions_convert_display_units_and_fit_canvas(editor, qt_app, system):
    window, controller = editor
    window.measurement_system = system
    density = window.get_px_per_meter()
    dialog = RectangleSizeDialog(window, window.floorplan_view.scene.sceneRect(), density)
    dialog.width_spin.setValue(5)
    dialog.height_spin.setValue(3)
    width, height = dialog.dimensions()
    assert meters_to_display_units(width / density, system) == pytest.approx(5)
    assert meters_to_display_units(height / density, system) == pytest.approx(3)
    controller.begin_placement(width, height, anchor=QPointF(100000, 100000))
    assert window.floorplan_view.scene.sceneRect().contains(controller.preview.rect())
    assert controller.preview.rect().width() == pytest.approx(width)
    assert ("ft" if system == "imperial" else "m") in controller.measurement.text()
    dialog.deleteLater()


def test_undo_redo_preserves_color_and_clears_stale_baked_pixels(editor, qt_app):
    window, controller = editor
    window.plan_tools.stroke_color = QColor("#d84315")
    controller.commit(QRectF(100, 100, 200, 150))
    lines = drawing_segments(window.session.metadata)
    assert {line["color"] for line in lines} == {"#d84315"}
    image = render_plan_drawing(Image.new("RGB", (900, 600), "white"), lines)
    assert image.getpixel((150, 100)) == (216, 67, 21)
    window.plan_tools.undo_button.click()
    assert drawing_segments(window.session.metadata) == []
    assert render_plan_drawing(image, []).getpixel((150, 100)) == (255, 255, 255)
    window.plan_tools.redo_button.click()
    assert drawing_segments(window.session.metadata) == lines


def test_shapes_survive_multiple_saves_reopen_and_are_removed_on_import(editor, qt_app, tmp_path):
    window, controller = editor
    controller.commit(QRectF(100, 100, 200, 150))
    original = drawing_segments(window.session.metadata)
    assert not window.is_empty_generated_survey()
    window.plan_tools.set_open(False)
    csv = tmp_path / "drawing.csv"
    window.session.csv_file = str(csv)
    assert window.save_survey()
    with Image.open(tmp_path / "drawing.png") as image:
        assert image.getpixel((150, 100)) != (255, 255, 255)
    assert window.open_survey(str(csv))
    assert drawing_segments(window.session.metadata) == original
    assert len(controller.items) == 4
    controller.commit(QRectF(400, 300, 150, 100))
    assert window.save_survey()
    assert window.open_survey(str(csv))
    assert len(drawing_segments(window.session.metadata)) == 8
    external = tmp_path / "external.png"
    Image.new("RGB", (600, 400), "white").save(external)
    window.load_plan_file(str(external), save_metadata=True)
    assert PLAN_DRAWING_KEY not in window.session.metadata
    assert not controller.items and not window.plan_tools.open


def test_shape_only_survey_requires_confirmation_and_save_failure_keeps_vectors(editor, qt_app, tmp_path):
    window, controller = editor
    controller.commit(QRectF(100, 100, 200, 150))
    original = drawing_segments(window.session.metadata)
    with patch.object(window, "choose_current_survey_close_action", return_value="cancel") as prompt:
        assert not window.confirm_new_survey_replaces_current()
        prompt.assert_called_once()
    window.session.csv_file = str(tmp_path / "failure.csv")
    with (patch.object(window.session, "save", side_effect=OSError("disk full")),
          patch("qt_ui.qt_session_workflow.QMessageBox.warning")):
        assert not window.save_survey()
    assert drawing_segments(window.session.metadata) == original and window.session.dirty
    assert not (tmp_path / "failure.png").exists()


@pytest.mark.parametrize("size", [(0, 10), (float("nan"), 10), (10000, 10)])
def test_invalid_numeric_sizes_never_create_geometry(editor, size):
    window, controller = editor
    with pytest.raises(ValueError):
        controller.begin_placement(*size)
    assert drawing_segments(window.session.metadata) is None


def test_vector_model_rejects_unverifiable_geometry():
    lines = rectangle_segments(1, 2, 3, 4, "#123456")
    assert len(lines) == 4
    lines[0]["x1"] = float("nan")
    with pytest.raises(ValueError):
        encode_drawing(lines)


def test_pending_rectangle_can_pan_without_registering_a_point(editor, qt_app):
    window, controller = editor
    view = window.floorplan_view
    controller.begin_placement(150, 100)
    captures = []
    view.surveyPointRequested.connect(lambda *args: captures.append(args))
    view.set_zoom(view.zoom_level * 2)
    start = QPoint(view.viewport().width() // 2, view.viewport().height() // 2)
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    move(view, start + QPoint(40, 25), Qt.MouseButton.LeftButton)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=start + QPoint(40, 25))
    assert controller.pending_size == (150, 100) and not captures
    assert controller.preview.rect().width() == 150


def test_esc_during_drag_cancels_without_opening_size_prompt(editor, qt_app):
    window, controller = editor
    view = window.floorplan_view
    point = view.mapFromScene(QPointF(200, 200))
    QTest.mousePress(view.viewport(), Qt.MouseButton.RightButton, pos=point)
    move(view, point + QPoint(100, 80), Qt.MouseButton.RightButton)
    QTest.keyClick(window, Qt.Key.Key_Escape)
    with patch("qt_ui.qt_rectangle_design.RectangleSizeDialog.exec") as prompt:
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.RightButton, pos=point + QPoint(100, 80))
        prompt.assert_not_called()
    assert not window.session.dirty and controller.preview is None


def test_exact_vector_fingerprint_prevents_stale_render_cache_for_small_changes():
    import pandas as pd
    from maps.config import MapConfig
    from maps.live_renderer import build_result_cache_key
    base = Image.new("RGB", (900, 600), "white")
    first = render_plan_drawing(base, rectangle_segments(100, 100, 200, 150, "#123456"))
    second = render_plan_drawing(base, rectangle_segments(100.01, 100, 200, 150, "#123456"))
    frame = pd.DataFrame([{"x": 100, "y": 100}])
    assert build_result_cache_key(frame, MapConfig(), first, {}) != build_result_cache_key(frame, MapConfig(), second, {})


def test_live_worker_uses_a_snapshot_of_the_editable_segments(tmp_path):
    from maps.config import MapConfig
    from qt_ui.qt_live_map import LiveMapRenderWorker
    path = tmp_path / "plan.png"
    Image.new("RGB", (900, 600), "white").save(path)
    lines = rectangle_segments(100, 100, 200, 150, "#d84315")
    worker = LiveMapRenderWorker([], str(path), MapConfig(), {}, plan_segments=lines)
    lines.clear()
    with patch("qt_ui.qt_live_map.render_live_map_payload", return_value={}) as render:
        worker.run()
    assert render.call_args.kwargs["bg_image"].getpixel((150, 100)) == (216, 67, 21)


def test_sheet_edge_strokes_remain_visible_in_exported_png():
    image = render_plan_drawing(Image.new("RGB", (900, 600), "white"),
                                rectangle_segments(0, 0, 900, 600, "#123456"))
    assert image.getpixel((899, 300)) == (18, 52, 86)
    assert image.getpixel((300, 599)) == (18, 52, 86)


def test_malformed_saved_drawing_stays_protected_on_repeated_refresh(editor, qt_app):
    window, controller = editor
    window.session.metadata[PLAN_DRAWING_KEY] = '{"version":1,"segments":[{}]}'
    original = window.session.metadata[PLAN_DRAWING_KEY]
    for _ in range(3):
        window.refresh_session_labels()
        assert window.plan_tools.drawing_error and not window.plan_tools.open
    assert window.session.metadata[PLAN_DRAWING_KEY] == original


def test_invalid_drawing_does_not_leave_live_worker_busy(editor, qt_app):
    window, controller = editor
    window.session.metadata[PLAN_DRAWING_KEY] = '{"version":1,"segments":[{}]}'
    with patch.object(window, "can_render_live_preview", return_value=True):
        window.update_live_preview()
    assert not window.live_rendering and window.live_thread is None
    assert window.live_status_label.text() == window.tr("rectangle_invalid_drawing")
