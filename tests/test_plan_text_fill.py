"""Portable text, shared selection edits and closed-room boundary masks."""
from copy import deepcopy
from unittest.mock import Mock, patch

import pytest
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit

from qt_ui.qt_plan_fill import closed_fill_paths, fill_closed_boundaries
from qt_ui.qt_text_editor import PlanTextDialog
from survey.plan_drawing import rectangle_segments, render_plan_drawing
from survey.plan_geometry import rotate_degrees, segment_bounds
from survey.plan_label_rendering import build_label
from survey.plan_labels import (PLAN_LABELS_KEY, drawing_labels, encode_labels,
                                label_geometry, transform_labels, validate_labels)
from tests.test_rectangle_design import editor, move
from tests.test_plan_rotation import orbit
from tests.test_capture_adapter import window, qt_app


def style(**values):
    return dict(dict(text="Sala riunioni\nÉtage 2", family="Segoe UI", size=24, bold=False, italic=False,
        color="#d84315", outline_color="#ffffff", outline_width=1, alignment="center"), **values)


def label(**values):
    result = build_label(style())
    result.update(x=300, y=220, **values)
    return result


def at(app, x, y):
    return app.floorplan_view.mapFromScene(QPointF(x, y))


def test_glyph_model_roundtrip_and_render_are_portable(qt_app):
    original = label()
    metadata = {"_generated_floorplan": "1", PLAN_LABELS_KEY: encode_labels([original])}
    assert drawing_labels(metadata) == [original]
    assert drawing_labels({PLAN_LABELS_KEY: metadata[PLAN_LABELS_KEY]}) is None
    image = render_plan_drawing(Image.new("RGB", (900, 600), "white"), [], [original])
    colors = image.getcolors(900 * 600)
    assert any(color == (216, 67, 21) and count > 20 for count, color in colors)
    before = image.info["plan_drawing_fingerprint"]
    changed = deepcopy(original)
    changed["x"] += .01
    assert render_plan_drawing(image, [], [changed]).info["plan_drawing_fingerprint"] != before
    assert render_plan_drawing(image, [], []).getbbox() == (0, 0, 900, 600)
    assert render_plan_drawing(image, [], []).getpixel((300, 220)) == (255, 255, 255)


def test_outline_is_behind_glyph_fill_and_does_not_erase_thin_letters(qt_app):
    plain = build_label(style(text="Thin letters", outline_width=0))
    outlined = build_label(style(text="Thin letters", outline_width=6))
    for text in (plain, outlined):
        text.update(x=300, y=220)
    source = Image.new("RGB", (900, 600), "white")
    assert render_plan_drawing(source, [], [plain]).tobytes() == render_plan_drawing(source, [], [outlined]).tobytes()


@pytest.mark.parametrize("field,value", [("size", 0), ("angle", float("nan")), ("color", "red"),
    ("outline_width", 20), ("text", " "), ("alignment", "unknown"), ("path", [["L", 0, 0]])])
def test_invalid_label_data_is_rejected(qt_app, field, value):
    source = label()
    source[field] = value
    with pytest.raises(ValueError):
        validate_labels([source])


def test_editor_validates_text_and_previews_style(qt_app, window):
    dialog = PlanTextDialog(window)
    try:
        dialog.show()
        qt_app.processEvents()
        assert not dialog.buttons.button(dialog.buttons.StandardButton.Ok).isEnabled()
        dialog.content.setPlainText("Ufficio\nReception")
        dialog.size.setValue(30)
        dialog.bold.setChecked(True)
        dialog.italic.setChecked(True)
        dialog.outline.setValue(2)
        assert dialog.preview_scene.items()
        assert dialog.values()["bold"] and dialog.values()["size"] == 30
        assert dialog.buttons.button(dialog.buttons.StandardButton.Ok).isEnabled()
        bounds = dialog.preview.mapFromScene(dialog.preview_scene.itemsBoundingRect()).boundingRect()
        assert dialog.preview.viewport().rect().adjusted(-2, -2, 2, 2).contains(bounds)
    finally:
        dialog.reject()
        dialog.deleteLater()


def test_right_click_prompt_preview_quarter_turn_placement_and_undo(editor, qt_app):
    app, drawing = editor
    app.plan_tools.select_tool("text")
    dialog = Mock()
    dialog.exec.return_value = QDialog.DialogCode.Accepted
    dialog.values.return_value = style()
    with patch("qt_ui.qt_text_design.PlanTextDialog", return_value=dialog), patch.object(app, "start_wifi_scan") as scan:
        QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 300, 220))
        assert drawing.text.pending and not drawing.labels() and not app.session.dirty
        assert drawing.text.preview is not None
        QTest.keyClick(app, Qt.Key.Key_R)
        assert drawing.text.pending["angle"] == 90
        move(app.floorplan_view, at(app, 400, 250))
        QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 400, 250))
        scan.assert_not_called()
    assert len(drawing.labels()) == 1 and drawing.labels()[0]["angle"] == 90
    assert len(drawing.undo_stack) == 1
    drawing.undo()
    assert not drawing.labels()
    drawing.redo()
    assert len(drawing.labels()) == 1


def test_text_hold_rotation_freezes_center_and_preserves_mouse_grip(editor):
    app, drawing = editor
    app.plan_tools.select_tool("text")
    drawing.text.begin_placement(label(), at(app, 320, 240))
    original = deepcopy(drawing.text.pending)
    QTest.keyPress(app, Qt.Key.Key_R)
    orbit(app, drawing, 0)
    pos = orbit(app, drawing, 45)
    assert drawing.rotation.angle == 45
    assert drawing.text.pending == original
    QTest.keyRelease(app, Qt.Key.Key_R)
    assert drawing.text.pending["angle"] == 45
    assert drawing.text.pending["x"] == pytest.approx(original["x"])
    assert drawing.text.pending["y"] == pytest.approx(original["y"])
    placed = deepcopy(drawing.text.pending)
    move(app.floorplan_view, pos)
    assert drawing.text.pending["x"] == pytest.approx(placed["x"])
    assert drawing.text.pending["y"] == pytest.approx(placed["y"])
    QTest.keyClick(app, Qt.Key.Key_Escape)
    assert not drawing.text.pending and not drawing.labels() and not app.session.dirty


def test_mixed_selection_move_rotate_delete_and_shared_history(editor):
    app, drawing = editor
    lines = rectangle_segments(100, 100, 120, 80, "#123456")
    labels = [label()]
    drawing.store(lines, labels)
    app.plan_tools.select_tool("select")
    selection = drawing.selection
    selection.set_selected(range(4), (0,))
    original = drawing.snapshot()
    selection.rotate()
    assert drawing.labels()[0]["angle"] == 90 and len(drawing.segments()) == 4
    assert len(drawing.undo_stack) == 1
    drawing.undo()
    assert drawing.snapshot() == original
    selection.set_selected(range(4), (0,))
    assert selection.begin_move()
    position = at(app, 550, 350)
    move(app.floorplan_view, position)
    assert drawing.snapshot() == original
    assert all(item.opacity() == .25 for item in drawing.text.items)
    QTest.keyPress(app, Qt.Key.Key_R)
    orbit(app, drawing, 0, radius=120)
    orbit(app, drawing, 35, radius=120)
    QTest.keyRelease(app, Qt.Key.Key_R)
    preview = deepcopy(selection.move_label_preview)
    assert preview[0]["angle"] == 35
    position = selection.last_pointer.toPoint()
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=position)
    assert drawing.labels() == preview
    assert selection.has_selection()
    QTest.keyClick(app, Qt.Key.Key_Delete)
    assert not drawing.labels() and not drawing.segments()
    drawing.undo()
    assert drawing.labels() == preview and len(drawing.segments()) == 4


def test_text_edit_keeps_identity_pose_and_cancel_is_non_destructive(editor):
    app, drawing = editor
    original = label(angle=25)
    drawing.store([], [original])
    app.plan_tools.select_tool("select")
    drawing.selection.set_selected((), (0,))
    dialog = Mock()
    dialog.exec.return_value = QDialog.DialogCode.Accepted
    dialog.values.return_value = style(text="Nuovo nome", size=32)
    with patch("qt_ui.qt_text_design.PlanTextDialog", return_value=dialog):
        assert drawing.text.edit(0)
    updated = drawing.labels()[0]
    assert updated["id"] == original["id"] and updated["angle"] == 25
    assert updated["x"] == original["x"] and updated["y"] == original["y"]
    assert updated["text"] == "Nuovo nome" and len(drawing.undo_stack) == 1
    dialog.exec.return_value = QDialog.DialogCode.Rejected
    with patch("qt_ui.qt_text_design.PlanTextDialog", return_value=dialog):
        drawing.text.edit(0)
    assert drawing.labels() == [updated] and len(drawing.undo_stack) == 1
    drawing.undo()
    assert drawing.labels() == [original]


def test_select_then_right_double_click_reopens_text_editor(editor):
    app, drawing = editor
    drawing.store([], [label()])
    app.plan_tools.select_tool("annotation_select")
    dialog = Mock()
    dialog.exec.return_value = QDialog.DialogCode.Accepted
    dialog.values.return_value = style(text="Edited by double click")
    with patch("qt_ui.qt_text_design.PlanTextDialog", return_value=dialog) as constructor:
        QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 300, 220))
        constructor.assert_not_called()
        assert drawing.annotation.selected_labels == (0,)
        QTest.mouseDClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 300, 220))
        QTest.mouseRelease(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 300, 220))
        constructor.assert_called_once()
    assert drawing.labels()[0]["text"] == "Edited by double click"
    assert drawing.annotation.selected_labels == (0,)


def test_delete_does_not_run_inside_an_editable_input(editor):
    app, drawing = editor
    drawing.store([], [label()])
    app.plan_tools.select_tool("select")
    drawing.selection.set_selected((), (0,))
    field = QLineEdit(app)
    field.show()
    field.setFocus()
    QApplication.processEvents()
    QTest.keyClick(field, Qt.Key.Key_Delete)
    assert len(drawing.labels()) == 1
    field.deleteLater()


def test_text_survives_png_save_reopen_and_external_import(editor, qt_app, tmp_path):
    app, drawing = editor
    original = label(angle=35)
    drawing.store([], [original])
    assert not app.is_empty_generated_survey()
    app.plan_tools.set_open(False)
    path = tmp_path / "labels.csv"
    app.session.csv_file = str(path)
    assert app.save_survey()
    with Image.open(path.with_suffix(".png")) as image:
        assert any(color == (216, 67, 21) for _count, color in image.convert("RGB").getcolors(900 * 600))
    assert app.open_survey(str(path))
    assert drawing.labels() == [original] and len(drawing.text.items) == 1
    external = tmp_path / "import.png"
    Image.new("RGB", (600, 400), "white").save(external)
    app.load_plan_file(str(external), save_metadata=True)
    assert PLAN_LABELS_KEY not in app.session.metadata and not drawing.text.items


def boundary_mode(app):
    app.plan_tools.set_open(False)
    app.set_boundaries_mode_enabled(True, show_status=False)
    assert app.floorplan_view.boundaries_edit_active


def test_fill_one_room_auto_fill_all_and_no_open_area_leaks(editor):
    app, drawing = editor
    first = rectangle_segments(100, 100, 150, 120, "#123456")
    second = rectangle_segments(400, 100, 150, 120, "#123456")
    drawing.store(first + second)
    boundary_mode(app)
    assert app.boundaries_fill_button.isVisible() and app.boundaries_auto_fill_button.isVisible()
    app.boundaries_fill_button.click()
    with patch.object(app, "start_wifi_scan") as scan:
        QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 150, 150))
        scan.assert_not_called()
    mask = app.floorplan_view.boundaries_mask_image
    assert mask.pixelColor(150, 150).alpha() == 255
    assert mask.pixelColor(450, 150).alpha() == 0
    assert mask.pixelColor(300, 150).alpha() == 0
    app.boundaries_auto_fill_button.click()
    assert app.floorplan_view.boundaries_mask_image.pixelColor(450, 150).alpha() == 255
    assert app.floorplan_view.boundaries_mask_image.pixelColor(300, 150).alpha() == 0
    app.session.dirty = False
    assert not fill_closed_boundaries(app)
    assert not app.session.dirty


def test_fill_respects_nested_rooms_and_oblique_edges(editor):
    app, drawing = editor
    outer = rectangle_segments(100, 100, 400, 300, "#123456")
    inner = rectangle_segments(200, 180, 100, 100, "#123456")
    drawing.store(outer + inner)
    boundary_mode(app)
    assert fill_closed_boundaries(app, QPointF(150, 150))
    mask = app.floorplan_view.boundaries_mask_image
    assert mask.pixelColor(150, 150).alpha() == 255 and mask.pixelColor(250, 220).alpha() == 0
    assert fill_closed_boundaries(app, QPointF(250, 220))
    assert mask.pixelColor(250, 220).alpha() == 255
    app.floorplan_view.clear_boundaries_mask()
    rotated = rotate_degrees(rectangle_segments(250, 200, 150, 100, "#123456"), 35)
    drawing.store(rotated)
    assert fill_closed_boundaries(app)
    assert app.floorplan_view.boundaries_mask_image.pixelColor(325, 250).alpha() == 255
    assert app.floorplan_view.boundaries_mask_image.pixelColor(240, 190).alpha() == 0


def test_open_contours_and_imported_plan_cannot_be_filled(editor, tmp_path):
    app, drawing = editor
    drawing.store(rectangle_segments(100, 100, 150, 120, "#123456")[:3])
    boundary_mode(app)
    app.session.dirty = False
    assert not fill_closed_boundaries(app) and not app.floorplan_view.has_boundaries_mask()
    assert not app.session.dirty
    external = tmp_path / "import.png"
    Image.new("RGB", (900, 600), "white").save(external)
    app.load_plan_file(str(external), save_metadata=True)
    boundary_mode(app)
    assert not app.boundaries_fill_button.isVisible() and not app.boundaries_auto_fill_button.isVisible()
    assert not fill_closed_boundaries(app)


def test_text_worker_takes_an_independent_glyph_snapshot(qt_app, tmp_path):
    from maps.config import MapConfig
    from qt_ui.qt_live_map import LiveMapRenderWorker
    path = tmp_path / "plan.png"
    Image.new("RGB", (900, 600), "white").save(path)
    labels = [label()]
    worker = LiveMapRenderWorker([], str(path), MapConfig(), {}, plan_segments=[], plan_labels=labels)
    labels[0]["path"].clear()
    with patch("qt_ui.qt_live_map.render_live_map_payload", return_value={}) as render:
        worker.run()
    image = render.call_args.kwargs["bg_image"]
    assert any(color == (216, 67, 21) for _count, color in image.getcolors(900 * 600))


def test_filled_boundary_mask_survives_save_and_reopen(editor, tmp_path):
    app, drawing = editor
    drawing.store(rectangle_segments(100, 100, 200, 150, "#123456"))
    boundary_mode(app)
    assert fill_closed_boundaries(app, QPointF(150, 150))
    path = tmp_path / "filled.csv"
    app.session.csv_file = str(path)
    assert app.save_survey()
    assert app.open_survey(str(path))
    mask = app.floorplan_view.get_boundaries_mask_image_copy()
    assert mask.pixelColor(150, 150).alpha() == 255
    assert mask.pixelColor(350, 150).alpha() == 0
