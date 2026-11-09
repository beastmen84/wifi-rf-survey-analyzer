"""Imported backgrounds retain independent editable overlays and symbol legends."""
from copy import deepcopy
from unittest.mock import patch

from PIL import Image, ImageDraw
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPageSize, QPdfWriter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog

from app_core.constants import GENERATED_FLOORPLAN_METADATA_KEY
from qt_ui.qt_plan_legend import PlanLegendDialog, export_legend_tables
from qt_ui.qt_plan_printing import clean_plan_image, clean_plan_source, paint_plan_page
from qt_ui.qt_plan_jpeg import render_plan_page, write_plan_jpeg
from survey.plan_annotations import transform_annotations, encode_annotations
from survey.plan_drawing import rectangle_segments, render_plan_drawing, drawing_geometry
from survey.plan_labels import drawing_labels, encode_labels
from survey.plan_layers import (PLAN_LAYERS_KEY, write_layers, active_layer,
                                add_layer, move_selection, visible_layers)
from survey.plan_mode import PLAN_MODE_KEY, is_drawn_plan
from tests.test_capture_adapter import window, qt_app
from tests.test_plan_source import load_options
from tests.test_plan_objects import obj
from tests.test_network_plan_symbols import symbol, ap
from tests.test_plan_text_fill import label
from tests.test_plan_annotations import choose, at, marker, aperture
from tests.test_rectangle_design import move


@pytest.fixture
def imported(window, qt_app, tmp_path):
    source = tmp_path / "source.png"
    image = Image.new("RGB", (1000, 700), "#d6e6f0")
    pen = ImageDraw.Draw(image)
    pen.rectangle((70, 60, 900, 620), outline="#314159", width=4)
    pen.line((600, 60, 600, 620), fill="#314159", width=4)
    image.save(source)
    with patch.object(window, "choose_new_survey_options", return_value=load_options(source)):
        assert window.new_survey(from_start_page=True)
    window.session.metadata["px_per_meter"] = "50"
    window.refresh_session_labels()
    window.resize(1440, 1000)
    window.show()
    window.plan_tools.set_open(True)
    qt_app.processEvents()
    yield window, window.plan_tools.controller, source
    window.session.dirty = False
    window.hide()


def test_loaded_palette_excludes_structure_and_hosted_openings(imported):
    owner, drawing, source = imported
    tools = owner.plan_tools
    assert tools.open and tools.available() and not tools.structure_available()
    assert tools.toggle_button.text() == owner.tr("annotation_group")
    assert not tools.structure_heading.isVisible()
    assert not owner.resize_plan_button.isVisible()
    before = deepcopy(owner.session.metadata), list(drawing.undo_stack), source.read_bytes()
    with patch.object(drawing.annotation, "configure") as configure:
        for tool in ("rectangle", "line", "circle", "arc", "eraser", "select", "wall", "door", "window"):
            tools.select_tool(tool)
            assert tools.active_tool is None
        configure.assert_not_called()
    for button in (tools.rectangle_button, tools.line_button, tools.circle_button, tools.arc_button,
                   tools.eraser_button, tools.select_button, tools.wall_button, tools.color_button,
                   tools.annotation_buttons["door"], tools.annotation_buttons["window"]):
        assert not button.isVisible()
    assert before == (owner.session.metadata, drawing.undo_stack, source.read_bytes())
    captures = []
    drawing.view.surveyPointRequested.connect(lambda *args: captures.append(args))
    QTest.mouseClick(drawing.view.viewport(), Qt.MouseButton.RightButton, pos=at(owner, 800, 400))
    assert not captures and not drawing.annotations()


def test_free_symbol_placement_move_delete_and_history_do_not_touch_background(imported, qt_app):
    owner, drawing, source = imported
    original = source.read_bytes()
    choose(owner, "symbol", symbol("square", width=40, height=40))
    QTest.mouseClick(drawing.view.viewport(), Qt.MouseButton.RightButton, pos=at(owner, 750, 350))
    assert len(drawing.annotations()) == 1
    assert drawing.annotations()[0]["number"] == 1
    assert PLAN_LAYERS_KEY in owner.session.metadata
    assert not is_drawn_plan(owner.session.metadata)
    choose(owner, "annotation_select")
    drawing.annotation.select((0,))
    QTest.keyClick(drawing.view, Qt.Key.Key_M)
    assert drawing.annotation.moving
    move(drawing.view, at(owner, 820, 390))
    QTest.mouseClick(drawing.view.viewport(), Qt.MouseButton.RightButton, pos=at(owner, 820, 390))
    moved = deepcopy(drawing.annotations())
    QTest.keyClick(drawing.view, Qt.Key.Key_Delete)
    assert not drawing.annotations()
    drawing.undo()
    assert drawing.annotations() == moved
    drawing.redo()
    assert not drawing.annotations()
    assert drawing.view.pixmap_item.pixmap().toImage().pixelColor(10, 10).name() == "#d6e6f0"
    assert clean_plan_image(drawing.view, owner.session.metadata).pixelColor(10, 10).name() == "#d6e6f0"
    assert source.read_bytes() == original


@pytest.mark.parametrize("mode", ("explicit", "legacy", "stale_generated_flag"))
def test_save_reopen_keeps_source_pixels_layers_text_racks_and_legend(imported, tmp_path, mode):
    owner, drawing, source = imported
    original = source.read_bytes()
    if mode == "legacy":
        owner.session.metadata.pop(PLAN_MODE_KEY)
    elif mode == "stale_generated_flag":
        owner.session.metadata[GENERATED_FLOORPLAN_METADATA_KEY] = "1"
    furniture = obj(cx=350, cy=300, width=120, height=70)
    rack = symbol("rack", identity="rack", cx=750, cy=300,
                  rack=dict(name="Rack A", switches=[dict(ports=["Uplink", "", "", ""])]))
    assert drawing.apply_edit([], labels=[dict(label(), x=300, y=160)], annotations=[furniture, rack])
    document = add_layer(drawing.layer_document(), "Hidden signs")
    active_layer(document)["drawing"]["annotations"] = [symbol(identity="hidden", number=7, cx=800)]
    active_layer(document).update(visible=False, locked=True)
    assert drawing.change_layers(document)
    expected = deepcopy(drawing.layer_document())
    path = tmp_path / "survey.csv"
    owner.session.csv_file = str(path)
    assert owner.save_survey()
    assert owner.open_survey(str(path))
    assert drawing.layer_document() == expected
    assert owner.session.metadata["map_file"] == str(source)
    assert not path.with_suffix(".png").exists()
    assert source.read_bytes() == original
    assert not is_drawn_plan(owner.session.metadata)
    assert owner.session.metadata["px_per_meter"] == "50"
    assert drawing.view.pixmap_item.pixmap().toImage().pixelColor(10, 10).name() == "#d6e6f0"
    assert {entry["kind"] for entry in export_legend_tables(owner.session)} == {"rack", "rack_ports"}
    assert not owner.layers_panel.isHidden() and not owner.legend_button.isHidden()


def test_layer_transfer_lock_visibility_and_legend_description_history(imported):
    owner, drawing, source = imported
    original = source.read_bytes()
    assert drawing.apply_edit([], annotations=[symbol(number=1, cx=750)])
    doc = add_layer(drawing.layer_document(), "Network")
    target = doc["active"]
    doc["active"] = "0"
    doc = move_selection(doc, target, dict(annotations=(0,)))
    assert drawing.change_layers(doc)
    dialog = PlanLegendDialog(owner)
    try:
        table, _rows = dialog.tables[0]
        table.item(0, 1).setText("Uplink desk")
        dialog.save()
        assert drawing.annotations()[0]["description"] == "Uplink desk"
        drawing.undo()
        assert not drawing.annotations()[0].get("description")
        drawing.redo()
        assert drawing.annotations()[0]["description"] == "Uplink desk"
    finally:
        dialog.deleteLater()
    doc = deepcopy(drawing.layer_document())
    active_layer(doc).update(visible=False, locked=True)
    drawing.change_layers(doc)
    assert not export_legend_tables(owner.session)
    assert not drawing.editable()
    before = deepcopy(owner.session.metadata)
    assert not drawing.apply_edit([], annotations=[])
    assert owner.session.metadata == before and source.read_bytes() == original
    drawing.undo()
    assert drawing.editable() and export_legend_tables(owner.session)


@pytest.mark.parametrize("invalid", ("line", "curve", "door", "window", "hidden_structure"))
def test_model_rejects_imported_structure_atomically(imported, invalid):
    owner, drawing, _source = imported
    doc = deepcopy(drawing.layer_document())
    state = active_layer(doc)["drawing"]
    if invalid in ("line", "door", "window", "hidden_structure"):
        state["segments"] = [dict(x1=100, y1=200, x2=600, y2=200, color="#123456")]
    if invalid in ("door", "window"):
        state["annotations"] = [aperture(invalid)]
    if invalid == "curve":
        state["curves"] = [dict(kind="circle", cx=300, cy=300, radius=80, color="#123456")]
    if invalid == "hidden_structure":
        active_layer(doc).update(id="other", visible=False)
        doc["active"] = "other"
        doc["layers"].insert(0, dict(id="0", name="Base", visible=True, locked=False,
                                    drawing=dict(segments=[], curves=[], labels=[], annotations=[])))
    before = deepcopy(owner.session.metadata), list(drawing.undo_stack)
    with pytest.raises(ValueError):
        drawing.change_layers(doc)
    assert before == (owner.session.metadata, drawing.undo_stack)
    with pytest.raises(ValueError):
        write_layers(owner.session.metadata, doc)
    assert before == (owner.session.metadata, drawing.undo_stack)
    assert not drawing.apply_edit(rectangle_segments(100, 100, 100, 100, "#123456"))
    assert before == (owner.session.metadata, drawing.undo_stack)


def test_legacy_imported_annotations_render_on_pixels_without_layer_metadata(imported):
    owner, drawing, _source = imported
    meta = dict(owner.session.metadata)
    meta["plan_annotations"] = encode_annotations([marker()])
    meta["plan_labels"] = encode_labels([label()])
    assert PLAN_LAYERS_KEY not in meta
    lines, curves = drawing_geometry(meta)
    with Image.open(meta["map_file"]) as image:
        rendered = render_plan_drawing(image, lines, drawing_labels(meta), curves, layers=visible_layers(meta))
    assert rendered.getpixel((10, 10)) == (214, 230, 240)
    assert rendered.getpixel((150, 150)) != (214, 230, 240)


def test_loaded_clean_jpeg_and_print_keep_full_background_and_legend(imported, tmp_path):
    owner, drawing, _source = imported
    assert drawing.apply_edit([], annotations=[symbol(number=1, cx=750, description="Socket A")])
    source = clean_plan_source(drawing.view, owner.session.metadata)
    assert (source.fitted_content().width(), source.fitted_content().height()) == (1000, 700)
    image = render_plan_page(source, "A5", True, 150, 50, "metric", owner.tr)
    assert not image.isNull()
    assert sum(image.pixelColor(x, y).name() == "#d6e6f0"
               for x in range(0, image.width(), 20) for y in range(0, image.height(), 20)) > 100
    jpeg = tmp_path / "plan.jpg"
    write_plan_jpeg(jpeg, image)
    assert jpeg.stat().st_size > 1000
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    pdf_path = tmp_path / "plan.pdf"
    printer.setOutputFileName(str(pdf_path))
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    paint_plan_page(printer, source, 50, "metric", owner.tr, legend=export_legend_tables(owner.session))
    pdf = QPdfDocument()
    assert pdf.load(str(pdf_path)) == QPdfDocument.Error.None_
    assert pdf.pageCount() >= 2
    pdf.close()


def test_loaded_ap_binding_moves_with_annotations_and_preserves_free_picking(imported):
    owner, drawing, _source = imported
    owner.session.set_ap_groups([ap()], update_memory=False)
    assert drawing.apply_edit([], annotations=[symbol("wifi_ap", cx=750)])
    from qt_ui.qt_ap_symbol_binding import assign_ap_symbol
    def bind(dialog):
        dialog.selected_id = "s1"
        return QDialog.DialogCode.Accepted
    with patch("qt_ui.qt_ap_symbol_binding.ApSymbolDialog.exec", bind):
        assert assign_ap_symbol(owner, "ap-a")
    old = deepcopy(owner.session.get_ap_groups()[0]["position"])
    assert old["symbol_id"] == "s1"
    assert drawing.apply_edit([], annotations=transform_annotations(drawing.annotations(), dx=10.25))
    assert owner.session.get_ap_groups()[0]["position"]["x"] == old["x"] + 10.25
    drawing.undo()
    assert owner.session.get_ap_groups()[0]["position"] == old
    with patch.object(owner.floorplan_view, "start_ap_position_pick", return_value=True) as pick:
        assert owner.start_ap_positioning("ap-a")
        pick.assert_called_once()


def test_loaded_ap_manager_exposes_both_position_actions(imported):
    owner, _drawing, _source = imported
    from qt_ui.qt_ap_groups import APGroupManagerDialog
    owner.session.set_ap_groups([ap()], update_memory=False)
    dialog = APGroupManagerDialog(owner)
    try:
        dialog.table.selectRow(0)
        menu = dialog.position_button.menu()
        assert menu is not None and len(menu.actions()) == 2
        assert dialog.assign_symbol_action.isEnabled()
        with patch.object(owner, "start_ap_positioning", return_value=True) as pick:
            menu.actions()[0].trigger()
            pick.assert_called_once_with("ap-a")
        with patch.object(dialog, "start_positioning_for_selected_group") as start:
            dialog.assign_symbol_action.trigger()
            start.assert_called_once_with(use_symbol=True)
    finally:
        dialog.deleteLater()


def test_loaded_pdf_overlays_survive_save_reopen_without_materializing_a_png(imported, tmp_path):
    owner, drawing, _source = imported
    path = tmp_path / "source.pdf"
    writer = QPdfWriter(str(path))
    writer.setResolution(72)
    painter = QPainter(writer)
    painter.fillRect(0, 0, writer.width(), writer.height(), QColor("#d6e6f0"))
    painter.end()
    del writer
    owner.load_plan_file(str(path), save_metadata=True)
    owner.session.metadata["px_per_meter"] = "50"
    owner.refresh_session_labels()
    original = path.read_bytes()
    assert drawing.apply_edit([], annotations=[symbol(number=1)])
    document = deepcopy(drawing.layer_document())
    csv = tmp_path / "pdf-survey.csv"
    owner.session.csv_file = str(csv)
    assert owner.save_survey() and owner.open_survey(str(csv))
    assert drawing.layer_document() == document
    assert owner.session.metadata["map_file"] == str(path)
    assert not csv.with_suffix(".png").exists() and path.read_bytes() == original
    assert clean_plan_image(drawing.view, owner.session.metadata).pixelColor(100, 100).name() == "#d6e6f0"


def test_loaded_live_worker_uses_an_independent_visible_overlay_snapshot(imported):
    owner, drawing, source = imported
    from maps.config import MapConfig
    from qt_ui.qt_live_map import LiveMapRenderWorker
    drawing.apply_edit([], annotations=[obj(cx=750, cy=300, fill="#ff0000", color="#ff0000")])
    payload = visible_layers(owner.session.metadata)
    assert not payload["generated"]
    worker = LiveMapRenderWorker([], str(source), MapConfig(), {}, plan_layers=payload)
    payload["layers"].clear()
    failed = []
    worker.failed.connect(lambda *args: failed.append(args))
    with patch("qt_ui.qt_live_map.render_live_map_payload", return_value={}) as render:
        worker.run()
    assert not failed
    image = render.call_args.kwargs["bg_image"]
    assert image.getpixel((10, 10)) == (214, 230, 240)
    assert image.getpixel((750, 300)) == (255, 0, 0)


def test_loaded_html_contains_the_composited_plan(imported, tmp_path):
    import base64
    from io import BytesIO
    import re
    import pandas as pd
    from exporting.live_html import generate_live_html_export
    from maps.config import MapConfig
    from tests.test_advisor import fixture_survey
    owner, drawing, source = imported
    drawing.apply_edit([], annotations=[obj(cx=750, cy=300, fill="#ff0000", color="#ff0000")])
    with Image.open(source) as image:
        composed = render_plan_drawing(image, None, layers=visible_layers(owner.session.metadata))
    context = fixture_survey()
    output = tmp_path / "live.html"
    generate_live_html_export(pd.DataFrame(context["rows"]), composed, str(tmp_path / "survey.csv"),
        MapConfig(ssid="Office", band="2.4", map_type="channel"), owner.tr,
        owner.build_live_renderer_translations(), language="en", output_file=output)
    data = re.search(r'<image href="data:image/png;base64,([^"]+)"', output.read_text(encoding="utf-8"))
    assert data is not None
    with Image.open(BytesIO(base64.b64decode(data.group(1)))) as embedded:
        assert embedded.convert("RGB").getpixel((10, 10)) == (214, 230, 240)
        assert embedded.convert("RGB").getpixel((750, 300)) == (255, 0, 0)
