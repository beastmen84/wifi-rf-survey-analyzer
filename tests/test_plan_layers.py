"""Layer topology isolation, edit permissions, stack rendering and persistence."""
from copy import deepcopy
from unittest.mock import patch

from PIL import Image
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtTest import QTest

from survey.plan_layers import (PLAN_LAYERS_KEY, read_layers, add_layer, active_layer, write_layers,
    validate_document, move_selection, visible_layers)
from survey.plan_drawing import PLAN_DRAWING_KEY, rectangle_segments, render_plan_drawing, encode_drawing
from qt_ui.qt_plan_printing import clean_plan_image, clean_plan_source
from qt_ui.qt_plan_jpeg import render_plan_page
from tests.test_plan_objects import obj
from tests.test_plan_annotations import aperture, line, choose, at
from tests.test_rectangle_design import editor, move
from tests.test_capture_adapter import window, qt_app


def test_legacy_base_migration_does_not_change_input_or_join_other_layers():
    metadata = {"_generated_floorplan": "1", PLAN_DRAWING_KEY: encode_drawing([line()])}
    before = deepcopy(metadata)
    document = read_layers(metadata)
    assert document["active"] == "0" and document["layers"][0]["drawing"]["segments"] == [line()]
    document = add_layer(document, "Crossing")
    active_layer(document)["drawing"]["segments"] = [line(300, 100, 300, 400)]
    document = validate_document(document)
    assert all(len(layer["drawing"]["segments"]) == 1 for layer in document["layers"])
    assert metadata == before
    write_layers(metadata, document)
    assert read_layers(metadata) == document


@pytest.mark.parametrize("bad", ["hidden_base", "missing_base", "duplicate_id", "duplicate_name", "missing_active",
    "empty_name", "invalid_bool", "invalid_segments", "unsupported_opening", "version"])
def test_invalid_layer_documents_are_rejected_without_modifying_metadata(bad):
    document = add_layer(read_layers({"_generated_floorplan": "1"}), "Second")
    if bad == "hidden_base":
        document["layers"][0]["visible"] = False
    elif bad == "missing_base":
        document["layers"].pop(0)
    elif bad == "duplicate_id":
        document["layers"][1]["id"] = "0"
    elif bad == "duplicate_name":
        document["layers"][1]["name"] = "layer 0"
    elif bad == "missing_active":
        document["active"] = "no-such-layer"
    elif bad == "empty_name":
        document["layers"][1]["name"] = " "
    elif bad == "invalid_bool":
        document["layers"][1]["locked"] = "false"
    elif bad == "invalid_segments":
        document["layers"][1]["drawing"]["segments"] = ""
    elif bad == "unsupported_opening":
        document["layers"][1]["drawing"]["annotations"] = [aperture()]
    else:
        document["version"] = 3  # v2 protects physical wall properties from older readers.
    metadata = {"keep": "value"}
    with pytest.raises((ValueError, KeyError, TypeError)):
        write_layers(metadata, document)
    assert metadata == {"keep": "value"}


def test_transfer_moves_supported_openings_and_rejects_stranded_ones():
    document = add_layer(read_layers({"_generated_floorplan": "1"}), "Destination")
    target = document["active"]
    document["active"] = "0"
    state = active_layer(document)["drawing"]
    state.update(segments=[line()], annotations=[aperture()])
    document = validate_document(document)
    result = move_selection(document, target, dict(segments=[0]))
    assert active_layer(result)["drawing"]["annotations"] == document["layers"][0]["drawing"]["annotations"]
    assert not result["layers"][0]["drawing"]["segments"] and not result["layers"][0]["drawing"]["annotations"]
    with pytest.raises(ValueError):
        move_selection(document, target, dict(annotations=[0]))
    assert len(document["layers"][0]["drawing"]["segments"]) == 1


def test_layer_edits_history_and_structural_intersections_stay_local(editor):
    app, d = editor
    d.store([line()])
    assert d.change_layers(add_layer(d.layer_document(), "Overlay"))
    overlay_id = d.layer_document()["active"]
    assert d.segments() == []
    assert d.apply_edit([line(300, 100, 300, 400)])
    assert len(d.segments()) == 1
    assert len(d.layer_document()["layers"][0]["drawing"]["segments"]) == 1
    state = deepcopy(d.layer_document())
    d.undo()
    assert d.segments() == [] and d.layer_document()["active"] == overlay_id
    d.undo()
    assert PLAN_LAYERS_KEY not in app.session.metadata and d.segments() == [line()]
    d.redo()
    d.redo()
    assert d.layer_document() == state
    document = deepcopy(state)
    document["active"] = "0"
    d.change_layers(document, history=False)
    assert d.segments() == [line()]


@pytest.mark.parametrize("property_name", ["locked", "visible"])
def test_readonly_active_layer_never_edits_or_captures_rf_points(editor, property_name):
    app, d = editor
    d.change_layers(add_layer(d.layer_document(), "Readonly"))
    document = deepcopy(d.layer_document())
    active_layer(document)[property_name] = property_name == "locked"
    d.change_layers(document)
    assert app.plan_tools.open and not d.editable() and not app.plan_tools.line_button.isEnabled()
    before = deepcopy(app.session.metadata)
    captures = []
    d.view.surveyPointRequested.connect(lambda *args: captures.append(args))
    QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 450, 300))
    QTest.keyClick(app, Qt.Key.Key_Delete)
    assert not d.apply_edit([line()])
    assert app.session.metadata == before and not captures


def test_visibility_order_and_vector_raster_outputs_agree(editor):
    app, d = editor
    d.store([], annotations=[obj(cx=400, cy=300, width=200, height=100, fill="#ff0000", color="#ff0000")])
    d.change_layers(add_layer(d.layer_document(), "Upper"))
    d.store([], annotations=[obj(cx=400, cy=300, width=120, height=80, fill="#0000ff", color="#0000ff")])
    image = clean_plan_image(d.view, app.session.metadata)
    assert image.pixelColor(400, 300).name() == "#0000ff"
    canvas = QImage(900, 600, QImage.Format.Format_RGB32)
    painter = QPainter(canvas)
    d.view.scene.render(painter, source=d.view.scene.sceneRect())
    painter.end()
    assert canvas.pixelColor(400, 300).name() == "#0000ff"
    doc = deepcopy(d.layer_document())
    doc["layers"].reverse()
    d.change_layers(doc)
    assert clean_plan_image(d.view, app.session.metadata).pixelColor(400, 300).name() == "#ff0000"
    doc = deepcopy(d.layer_document())
    active_layer(doc)["visible"] = False
    d.change_layers(doc)
    assert clean_plan_image(d.view, app.session.metadata).pixelColor(400, 300).name() == "#ff0000"
    # Every renderer receives an independent visible-layer snapshot.
    payload = visible_layers(app.session.metadata)
    result = render_plan_drawing(Image.new("RGB", (900, 600), "white"), [], layers=payload)
    assert result.getpixel((400, 300)) == (255, 0, 0)
    assert len(payload["layers"]) == 1
    page = render_plan_page(clean_plan_source(d.view, app.session.metadata), "A4", True, 150, 50)
    assert not page.isNull()


def test_furniture_references_visible_base_walls_but_structure_does_not(editor):
    app, d = editor
    d.store(rectangle_segments(100, 100, 600, 400, "#334455"))
    d.change_layers(add_layer(d.layer_document(), "Furniture"))
    assert not d.snapper.segments and d.reference_snapper.segments
    choose(app, "desk", obj(cx=400, cy=300, width=100, height=50))
    move(d.view, at(app, 180, 200))
    assert d.dimensions.values["kind"] == "object"
    assert len(d.dimensions.values["quotes"]) == 2
    # A passive base wall is outside structure picking/erasing.
    before = deepcopy(app.session.metadata)
    choose(app, "eraser")
    QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 100, 250))
    assert app.session.metadata == before
    assert d.selection.lines == []


def test_panel_outside_design_mode_and_visible_hidden_layers_survive_real_save(editor, tmp_path):
    app, d = editor
    d.store([line()])
    app.layers_panel.add()
    d.store([], annotations=[obj()])
    doc = deepcopy(d.layer_document())
    active_layer(doc).update(name="Arredi", visible=False, locked=True)
    d.change_layers(doc)
    app.plan_tools.set_open(False)
    app.layers_panel.set_open(True, save=False)
    assert app.layers_panel.body.isVisible()
    path = tmp_path / "layered.csv"
    app.session.csv_file = str(path)
    with patch("qt_ui.qt_session_workflow.QMessageBox.warning") as warning:
        assert app.save_survey(), warning.call_args
    assert app.open_survey(str(path))
    assert d.layer_document() == doc
    assert len(active_layer(d.layer_document())["drawing"]["annotations"]) == 1
    assert not active_layer(d.layer_document())["visible"]
    with Image.open(path.with_suffix(".png")) as png:
        assert png.convert("RGB").getpixel((450, 320)) == (255, 255, 255)


def test_layer_presentation_does_not_change_rf_analysis_fingerprint(editor):
    app, d = editor
    d.change_layers(add_layer(d.layer_document(), "Furniture"))
    before = app.analysis_view.fingerprint(app.analysis_view.context())
    doc = deepcopy(d.layer_document())
    active_layer(doc).update(name="Other name", visible=False, locked=True)
    doc["layers"].reverse()
    doc["active"] = "0"
    d.change_layers(doc)
    assert app.analysis_view.fingerprint(app.analysis_view.context()) == before


def test_real_tree_activation_checkboxes_rename_and_order_are_safe(editor, qt_app):
    app, d = editor
    panel = app.layers_panel
    panel.set_open(True, save=False)
    panel.add()
    other = d.layer_document()["active"]
    base = panel.tree.topLevelItem(1)
    panel.tree.setCurrentItem(base)
    qt_app.processEvents()
    assert d.layer_document()["active"] == "0"
    # Base visibility is invariant, including keyboard/programmatic checkbox edits.
    base = panel.tree.topLevelItem(1)
    base.setCheckState(0, Qt.CheckState.Unchecked)
    qt_app.processEvents()
    assert d.layer_document()["layers"][0]["visible"]
    assert panel.tree.topLevelItem(1).checkState(0) == Qt.CheckState.Checked
    item = panel.tree.topLevelItem(0)
    panel.tree.setCurrentItem(item)
    qt_app.processEvents()
    assert d.layer_document()["active"] == other
    item = panel.tree.topLevelItem(0)
    item.setCheckState(1, Qt.CheckState.Checked)
    qt_app.processEvents()
    assert active_layer(d.layer_document())["locked"] and not panel.buttons["delete"].isEnabled()
    panel.tree.topLevelItem(0).setCheckState(1, Qt.CheckState.Unchecked)
    qt_app.processEvents()
    with patch("qt_ui.qt_layers.QInputDialog.getText", return_value=("Furniture", True)):
        panel.rename()
    assert active_layer(d.layer_document())["name"] == "Furniture"
    panel.down()
    assert d.layer_document()["layers"][0]["id"] == other
    panel.reorder(other, "0", True)
    qt_app.processEvents()
    assert d.layer_document()["layers"][-1]["id"] == other


def test_move_selection_button_transfers_free_objects_in_one_undoable_edit(editor):
    app, d = editor
    d.store([], annotations=[obj()])
    doc = add_layer(d.layer_document(), "Furniture")
    destination = doc["active"]
    doc["active"] = "0"
    d.change_layers(doc)
    choose(app, "annotation_select")
    d.annotation.select((0,))
    assert app.layers_panel.move_button.isEnabled()
    with patch("qt_ui.qt_layers.QInputDialog.getItem", return_value=("Furniture", True)):
        app.layers_panel.move_selected()
    assert d.layer_document()["active"] == destination and len(d.annotations()) == 1
    assert not d.layer_document()["layers"][0]["drawing"]["annotations"]
    d.undo()
    assert d.layer_document()["active"] == "0" and len(d.annotations()) == 1


def test_imported_bitmap_survives_layer_changes_save_and_reopen(editor, tmp_path):
    app, d = editor
    original = tmp_path / "imported.png"
    Image.new("RGB", (600, 400), "#abcdef").save(original)
    app.load_plan_file(str(original), save_metadata=True)
    # Old imported projects can contain layer metadata; preserve it read-only.
    write_layers(app.session.metadata, add_layer(d.layer_document(), "Legacy overlay"))
    app.refresh_session_labels()
    before = deepcopy(app.session.metadata)
    app.layers_panel.add()
    assert app.session.metadata == before and app.layers_panel.isHidden()
    assert d.view.pixmap_item.pixmap().toImage().pixelColor(100, 100).name() == "#abcdef"
    assert clean_plan_image(d.view, app.session.metadata).pixelColor(100, 100).name() == "#abcdef"
    csv = tmp_path / "bitmap-layers.csv"
    app.session.csv_file = str(csv)
    assert app.save_survey()
    assert not csv.with_suffix(".png").exists()
    assert app.open_survey(str(csv))
    assert app.session.metadata["map_file"] == str(original)
    assert clean_plan_image(d.view, app.session.metadata).pixelColor(100, 100).name() == "#abcdef"


@pytest.mark.parametrize("action", ["rename", "delete", "move_selected"])
def test_layer_dialogs_discard_results_after_the_drawing_changes(editor, action):
    app, d = editor
    app.layers_panel.add()
    d.store([], annotations=[obj()])
    choose(app, "annotation_select")
    d.annotation.select((0,))
    expected = []

    def changed(*_args, **_kwargs):
        document = deepcopy(d.layer_document())
        active_layer(document)["name"] = "Changed while dialog open"
        d.change_layers(document)
        expected.append(deepcopy(app.session.metadata))
        if action == "rename":
            return "Stale rename", True
        if action == "move_selected":
            return "Layer 0", True
        from PySide6.QtWidgets import QMessageBox
        return QMessageBox.StandardButton.Yes

    target = {"rename": "QInputDialog.getText", "delete": "QMessageBox.question",
              "move_selected": "QInputDialog.getItem"}[action]
    with patch("qt_ui.qt_layers." + target, side_effect=changed):
        getattr(app.layers_panel, action)()
    assert expected and app.session.metadata == expected[-1]


def test_layer_bounds_failure_preserves_metadata_history_and_selection(editor):
    app, d = editor
    app.layers_panel.add()
    d.store([line()])
    choose(app, "select")
    d.selection.set_selected((0,))
    before = deepcopy(app.session.metadata), deepcopy(d.undo_stack)
    document = deepcopy(d.layer_document())
    active_layer(document)["drawing"]["segments"] = [line(100, 100, 950, 100)]
    with pytest.raises(ValueError):
        d.change_layers(document)
    assert (app.session.metadata, d.undo_stack) == before
    assert d.selection.selected == (0,)
    assert not d.apply_edit([line(100, 100, 950, 100)])
    assert (app.session.metadata, d.undo_stack) == before


def test_global_annotation_limit_rejects_edit_before_changing_history(editor):
    app, d = editor
    d.store([], annotations=[obj(id=f"base-{i}") for i in range(600)])
    app.layers_panel.add()
    d.store([], annotations=[obj(id=f"upper-{i}") for i in range(400)])
    before = deepcopy(app.session.metadata), deepcopy(d.undo_stack), deepcopy(d.redo_stack)
    assert not d.apply_edit([], annotations=d.annotations() + [obj(id="overflow")])
    assert (app.session.metadata, d.undo_stack, d.redo_stack) == before


def test_live_worker_uses_visible_layer_snapshot_without_stale_baked_content(editor, tmp_path):
    from maps.config import MapConfig
    from qt_ui.qt_live_map import LiveMapRenderWorker

    app, d = editor
    d.store([], annotations=[obj(cx=400, cy=300, fill="#ff0000", color="#ff0000")])
    app.layers_panel.add()
    d.store([], annotations=[obj(cx=400, cy=300, fill="#0000ff", color="#0000ff")])
    doc = deepcopy(d.layer_document())
    active_layer(doc)["visible"] = False
    d.change_layers(doc)
    path = tmp_path / "stale.png"
    Image.new("RGB", (900, 600), "#00ff00").save(path)
    payload = visible_layers(app.session.metadata)
    worker = LiveMapRenderWorker([], str(path), MapConfig(), {}, plan_layers=payload)
    payload["layers"].clear()
    finished, failed = [], []
    worker.finished.connect(lambda *args: finished.append(args))
    worker.failed.connect(lambda *args: failed.append(args))
    with patch("qt_ui.qt_live_map.render_live_map_payload", return_value={}) as render:
        worker.run()
    assert finished and not failed
    image = render.call_args.kwargs["bg_image"]
    assert image.getpixel((400, 300)) == (255, 0, 0)
    assert image.getpixel((20, 20)) == (255, 255, 255)


def test_empty_base_layer_does_not_retain_other_layers_baked_into_saved_png(editor, tmp_path):
    app, d = editor
    app.layers_panel.add()
    d.store([], annotations=[obj(cx=400, cy=300, fill="#0000ff", color="#0000ff")])
    doc = deepcopy(d.layer_document())
    doc["active"] = "0"
    d.change_layers(doc)
    assert d.segments() is None
    path = tmp_path / "empty-base.csv"
    app.session.csv_file = str(path)
    assert app.save_survey() and app.open_survey(str(path))
    assert PLAN_DRAWING_KEY not in app.session.metadata
    with Image.open(path.with_suffix(".png")) as png:
        assert png.convert("RGB").getpixel((400, 300)) == (0, 0, 255)
    assert d.view.pixmap_item.pixmap().toImage().pixelColor(400, 300).name() == "#ffffff"
    doc = deepcopy(d.layer_document())
    doc["layers"][1]["visible"] = False
    d.change_layers(doc)
    canvas = QImage(900, 600, QImage.Format.Format_RGB32)
    painter = QPainter(canvas)
    d.view.scene.render(painter, source=d.view.scene.sceneRect())
    painter.end()
    assert canvas.pixelColor(400, 300).name() != "#0000ff"


def test_room_closure_grid_and_fill_do_not_join_visible_layers(editor):
    app, d = editor
    walls = rectangle_segments(100, 100, 500, 300, "#334455")
    d.store(walls[:3])
    app.layers_panel.add()
    d.store(walls[3:])
    assert not d.regions.faces
    assert d.view.grid_interior_path.isEmpty()
    assert not d.reference_snapper.region_centers()
    # Closing a room on the active layer does not consume the passive pieces.
    assert d.apply_edit(walls)
    assert len(d.regions.faces) == 1
    assert len(d.layer_document()["layers"][0]["drawing"]["segments"]) == 3


def test_layer_panel_history_works_with_design_mode_closed(editor, qt_app):
    app, d = editor
    panel = app.layers_panel
    panel.set_open(True, save=False)
    panel.add()
    document = deepcopy(d.layer_document())
    app.plan_tools.set_open(False)
    assert panel.history_buttons["undo"].isEnabled()
    QTest.mouseClick(panel.history_buttons["undo"], Qt.MouseButton.LeftButton)
    qt_app.processEvents()
    assert PLAN_LAYERS_KEY not in app.session.metadata
    assert panel.history_buttons["redo"].isEnabled()
    QTest.mouseClick(panel.history_buttons["redo"], Qt.MouseButton.LeftButton)
    qt_app.processEvents()
    assert d.layer_document() == document and not app.plan_tools.open
