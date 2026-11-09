"""Independent checks for imported-source integrity and complete AP interactions."""
from copy import deepcopy
from unittest.mock import patch

from PIL import Image
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPdfWriter, QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox

from qt_ui.pdf_floorplan import render_pdf_page_to_qimage, render_pdf_page_to_pil_image
from qt_ui.qt_plan_jpeg import PlanJpegDialog
from survey.plan_symbols import bind_ap
from survey.plan_layers import active_layer
from tests.test_loaded_plan_annotations import imported
from tests.test_capture_adapter import window, qt_app
from tests.test_network_plan_symbols import ap, symbol
from tests.test_plan_annotations import at
from tests.test_plan_legend_export import jpeg_options


def bound_ap(owner, drawing):
    owner.session.set_ap_groups([ap()], update_memory=False)
    assert drawing.apply_edit([], annotations=[symbol("wifi_ap", cx=750, cy=300)])
    assert drawing.change_layers(bind_ap(drawing.layer_document(), "s1", "ap-a"))


def test_direct_ap_pick_leaves_annotation_mode_and_accepts_the_real_click(imported, qt_app):
    owner, drawing, _source = imported
    owner.session.set_ap_groups([ap()], update_memory=False)
    assert owner.plan_tools.open
    assert owner.start_ap_positioning("ap-a")
    assert not owner.plan_tools.open and not drawing.view.design_mode_active
    point = at(owner, 820, 400)
    expected = drawing.view.mapToScene(point)
    QTest.mouseClick(drawing.view.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert owner.session.get_ap_groups()[0]["position"] == dict(x=round(expected.x()), y=round(expected.y()))


def test_direct_position_of_bound_ap_moves_its_symbol_and_has_one_history_step(imported):
    owner, drawing, _source = imported
    bound_ap(owner, drawing)
    previous = deepcopy(owner.session.get_ap_groups()[0]["position"])
    count = len(drawing.undo_stack)
    owner.save_ap_position("ap-a", 810, 410)
    assert owner.session.get_ap_groups()[0]["position"] == dict(x=810, y=410, symbol_id="s1")
    assert (drawing.annotations()[0]["cx"], drawing.annotations()[0]["cy"]) == (810, 410)
    assert len(drawing.undo_stack) == count + 1
    drawing.undo()
    assert owner.session.get_ap_groups()[0]["position"] == previous
    drawing.redo()
    assert owner.session.get_ap_groups()[0]["position"] == dict(x=810, y=410, symbol_id="s1")


@pytest.mark.parametrize("bound", (False, True))
def test_ap_position_actions_cannot_mutate_a_busy_survey(imported, bound):
    owner, drawing, _source = imported
    if bound:
        bound_ap(owner, drawing)
    else:
        owner.session.set_ap_groups([ap()], update_memory=False)
    before, history = deepcopy(owner.session.metadata), len(drawing.undo_stack)
    owner.scan_in_progress = True
    try:
        assert not owner.start_ap_positioning("ap-a")
        owner.save_ap_position("ap-a", 810, 410)
        assert owner.session.metadata == before and len(drawing.undo_stack) == history
    finally:
        owner.scan_in_progress = False


@pytest.mark.parametrize("readonly", ("locked", "hidden"))
def test_direct_bound_ap_position_respects_readonly_annotation_layers(imported, readonly):
    owner, drawing, _source = imported
    bound_ap(owner, drawing)
    document = deepcopy(drawing.layer_document())
    if readonly == "locked":
        active_layer(document)["locked"] = True
    else:
        from survey.plan_layers import add_layer
        document = add_layer(document, "AP layer")
        document["layers"][1]["drawing"]["annotations"] = document["layers"][0]["drawing"]["annotations"]
        document["layers"][0]["drawing"]["annotations"] = []
        document["layers"][1]["visible"] = False
    drawing.change_layers(document)
    original, history = deepcopy(owner.session.metadata), len(drawing.undo_stack)
    with patch("qt_ui.qt_ap_symbol_binding.QMessageBox.warning") as warning:
        owner.save_ap_position("ap-a", 810, 410)
    assert warning.called
    assert owner.session.metadata == original and len(drawing.undo_stack) == history


@pytest.mark.parametrize("collision", ("plan", "legend"))
def test_jpeg_export_cannot_overwrite_imported_source_even_as_a_legend_page(imported, tmp_path, collision):
    owner, drawing, _old_source = imported
    target = tmp_path / "export.jpg"
    source = target if collision == "plan" else tmp_path / "export-legend-01.jpg"
    Image.new("RGB", (1000, 700), "#abcdef").save(source)
    owner.load_plan_file(str(source), save_metadata=True)
    owner.session.metadata["px_per_meter"] = "50"
    owner.refresh_session_labels()
    if collision == "legend":
        drawing.apply_edit([], annotations=[symbol(number=1)])
    original = source.read_bytes()
    with (patch.object(PlanJpegDialog, "exec", jpeg_options),
          patch("qt_ui.qt_plan_jpeg.get_centered_save_file_name", return_value=(str(target), "")),
          patch("qt_ui.qt_plan_jpeg.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes),
          patch("qt_ui.qt_plan_jpeg.QMessageBox.warning") as warning):
        assert not owner.save_plan_jpeg()
    assert warning.called and source.read_bytes() == original
    if collision == "legend":
        assert not target.exists()


def test_unpainted_pdf_page_margins_are_white_in_both_import_paths(tmp_path, qt_app):
    source = tmp_path / "partially-painted.pdf"
    writer = QPdfWriter(str(source))
    writer.setResolution(72)
    painter = QPainter(writer)
    painter.fillRect(80, 80, 120, 100, QColor("#abcdef"))
    painter.end()
    del writer
    native = render_pdf_page_to_qimage(source)
    raster = render_pdf_page_to_pil_image(source)
    assert native.pixelColor(5, 5).name() == "#ffffff"
    assert raster.getpixel((5, 5)) == (255, 255, 255)
    assert native.pixelColor(230, 230).name() == "#abcdef"
