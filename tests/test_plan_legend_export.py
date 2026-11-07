"""Paginated, unicode-safe legends and recoverable multi-image clean exports."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import pytest
from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QPageLayout, QPageSize
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QDialog, QMessageBox

from qt_ui.qt_legend_pages import wrap, legend_pages
from qt_ui.qt_plan_jpeg import PlanJpegDialog, legend_page_layout, render_legend_image
from qt_ui.qt_plan_printing import clean_plan_source, paint_plan_page
from qt_ui.qt_plan_legend import export_legend_tables
from tests.test_network_plan_symbols import symbol
from tests.test_rectangle_design import editor
from tests.test_capture_adapter import window, qt_app


def populate(drawing, count=25):
    drawing.store([], annotations=[symbol(identity=f"s{i}", number=i, cx=100+(i%10)*60, cy=150+(i//10)*70,
        description=f"Position {i}: Ethernet / PoE — αβγ 🛜 " + "Long description "*6) for i in range(1, count+1)])


def test_unicode_wrap_preserves_all_characters_and_pagination_repeats_headers(qt_app):
    text = "Porta 🚪 punto rete 🛜 connettore αβγ "*20
    lines = wrap(text, 80)
    assert "".join(lines) == text
    table = [dict(kind="square", rows=[dict(number=12, ap="", description=text*2)])]
    tr = lambda key: dict(plan_legend="Legenda", legend_visible_export="Visible", legend_table="Table {number} {symbol}",
        object_symbol_square="Square", legend_number="Number", legend_description="Description").get(key, key)
    pages = legend_pages(table, 220, 250, tr)
    assert len(pages) > 1
    assert all(page[0]["type"] == "header" for page in pages)
    actual = "".join(line for page in pages for block in page if block["type"] == "row" for line in block["description"])
    assert actual == text*2
    assert all(block["y"] + block.get("height", 0) <= 228 for page in pages for block in page)


def test_real_print_document_contains_plan_plus_every_legend_page_and_respects_range(editor, tmp_path):
    app, d = editor
    populate(d)
    tables = export_legend_tables(app.session)
    image = clean_plan_source(d.view, app.session.metadata)
    for selected in (False, True):
        output = tmp_path / ("selected.pdf" if selected else "all.pdf")
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setResolution(150)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(output))
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A5))
        printer.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)
        printer.setFullPage(False)
        pages = legend_pages(tables, printer.width()*72/150, printer.height()*72/150, app.tr)
        assert len(pages) >= 2
        if selected:
            printer.setPrintRange(QPrinter.PrintRange.PageRange)
            printer.setFromTo(2, 2)
        assert paint_plan_page(printer, image, app.get_px_per_meter(), "metric", app.tr, legend=tables)
        document = QPdfDocument()
        try:
            assert document.load(str(output)) == QPdfDocument.Error.None_
            assert document.pageCount() == (1 if selected else len(pages)+1)
            rendered = document.render(0 if selected else 1, image_size())
            assert not rendered.isNull()
        finally:
            document.close()


def image_size():
    from PySide6.QtCore import QSize
    return QSize(500, 700)


def jpeg_options(dialog):
    dialog.paper.setCurrentIndex(dialog.paper.findData("A5"))
    dialog.orientation.setCurrentIndex(0)
    dialog.resolution.setCurrentIndex(dialog.resolution.findData(150))
    return QDialog.DialogCode.Accepted


def test_jpeg_outputs_matching_paper_density_all_legend_rows_and_preview_pages(editor, tmp_path):
    app, d = editor
    populate(d)
    before = deepcopy(app.session.metadata), len(d.undo_stack)
    target = tmp_path / "network.jpg"
    with (patch.object(PlanJpegDialog, "exec", jpeg_options),
          patch("qt_ui.qt_plan_jpeg.get_centered_save_file_name", return_value=(str(target), ""))):
        assert app.save_plan_jpeg()
    pages = legend_page_layout(export_legend_tables(app.session), "A5", False, app.tr)
    files = sorted(tmp_path.glob("network-legend-*.jpg"))
    assert len(files) == len(pages) >= 2 and target.exists()
    for path in [target, *files]:
        with Image.open(path) as image:
            assert image.size == (874, 1240)
            assert image.info["dpi"] == pytest.approx((150, 150), abs=1)
            assert image.convert("L").getextrema()[0] < 100
    assert (app.session.metadata, len(d.undo_stack)) == before
    dialog = PlanJpegDialog(app, clean_plan_source(d.view, app.session.metadata), app.get_px_per_meter(), "metric")
    try:
        assert dialog.include_legend.isChecked() and dialog.page_choice.count() > 1
        dialog.page_choice.setCurrentIndex(1)
        assert not dialog.preview.pixmap().isNull()
        dialog.include_legend.setChecked(False)
        assert dialog.page_choice.count() == 1
    finally:
        dialog.deleteLater()


@pytest.mark.parametrize("failure", ["cancel_options", "cancel_file", "cancel_replace", "write_failure"])
def test_export_cancellation_and_failed_secondary_write_preserve_existing_set(editor, tmp_path, failure):
    app, d = editor
    populate(d, 2)
    target = tmp_path / "network.jpg"
    secondary = tmp_path / "network-legend-01.jpg"
    target.write_bytes(b"old plan")
    secondary.write_bytes(b"old legend")
    from qt_ui.qt_plan_jpeg import write_plan_jpeg as real_write
    writes = []
    def write(path, image):
        writes.append(Path(path))
        if failure == "write_failure" and len(writes) == 2:
            raise OSError("simulated image failure")
        return real_write(path, image)
    with (patch.object(PlanJpegDialog, "exec", return_value=QDialog.DialogCode.Rejected) if failure == "cancel_options"
          else patch.object(PlanJpegDialog, "exec", jpeg_options),
          patch("qt_ui.qt_plan_jpeg.get_centered_save_file_name", return_value=("" if failure == "cancel_file" else str(target), "")),
          patch("qt_ui.qt_plan_jpeg.QMessageBox.question", return_value=QMessageBox.StandardButton.Cancel
                if failure == "cancel_replace" else QMessageBox.StandardButton.Yes),
          patch("qt_ui.qt_plan_jpeg.QMessageBox.warning"),
          patch("qt_ui.qt_plan_jpeg.write_plan_jpeg", side_effect=write)):
        assert not app.save_plan_jpeg()
    assert target.read_bytes() == b"old plan" and secondary.read_bytes() == b"old legend"
    assert not list(tmp_path.glob("*.stage*"))


def test_rendered_legend_page_has_bounded_allocation_and_readable_text(editor):
    app, d = editor
    populate(d, 2)
    tables = export_legend_tables(app.session)
    pages = legend_page_layout(tables, "A4", False, app.tr)
    with pytest.raises(ValueError):
        render_legend_image(pages[0], "A0", False, 600, 1, 1, app.tr)
    image = render_legend_image(pages[0], "A4", False, 150, 1, 1, app.tr)
    assert not image.isNull()
