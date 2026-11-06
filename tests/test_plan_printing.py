"""Print the clean, current sheet through an isolated PDF printer, never hardware."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from PIL import Image, ImageChops
from PySide6.QtCore import QMarginsF, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter, QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPageSetupDialog
from PySide6.QtWidgets import QDialog

from qt_ui.qt_plan_printing import PlanPrintPreviewDialog, clean_plan_image, paint_plan_page
from survey.plan_drawing import PLAN_DRAWING_KEY, rectangle_segments
from tests.test_blank_plan import create_survey
from tests.test_capture_adapter import window, qt_app
from tests.test_plan_annotations import aperture, marker
from tests.test_plan_text_fill import label
from tests.test_rectangle_design import editor


def pillow(image):
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    rgba = Image.frombytes("RGBA", (image.width(), image.height()), bytes(image.constBits()),
                           "raw", "RGBA", image.bytesPerLine())
    paper = Image.new("RGB", rgba.size, "white")
    paper.paste(rgba, mask=rgba.getchannel("A"))
    return paper


def test_print_button_is_right_of_project_heading_and_tracks_map_and_scan_state(window, qt_app):
    assert not window.print_plan_button.isEnabled() and not window.print_plan()
    create_survey(window)
    window.resize(1600, 1000)
    window.show()
    qt_app.processEvents()
    button = window.print_plan_button
    assert button.isEnabled() and button.parentWidget() is window.project_section_label.parentWidget()
    assert button.x() > window.project_section_label.geometry().right()
    assert button.height() == window.delete_scale_button.height()
    for tab in (0, 1, 2):
        window.tabs.setCurrentIndex(tab)
        window.refresh_session_labels()
        assert button.isEnabled()
    window.scan_in_progress = True
    window.refresh_session_labels()
    assert not button.isEnabled() and not window.print_plan()
    window.scan_in_progress = False
    window.floorplan_view.clear_floorplan()
    window.refresh_session_labels()
    assert not button.isEnabled() and not window.print_plan()
    window.session.dirty = False


def test_clean_snapshot_has_current_unsaved_drawing_but_no_grid_points_masks_or_previews(editor):
    app, drawing = editor
    view = app.floorplan_view
    walls = rectangle_segments(100, 200, 500, 250, "#123456")
    curve = dict(kind="circle", cx=700, cy=350, radius=50, phase=0, color="#aa0000")
    assert drawing.apply_edit(walls, [dict(label(), x=350, y=350)], [curve],
                              [aperture(variant="frame"), marker()])
    # A previously saved raster can contain stale ink; current vectors win.
    stale = QImage(view.pixmap_item.pixmap().size(), QImage.Format.Format_RGB888)
    stale.fill(Qt.GlobalColor.white)
    painter = QPainter(stale)
    painter.fillRect(50, 50, 30, 10, QColor("#ff0000"))
    painter.end()
    view.pixmap_item.setPixmap(QPixmap.fromImage(stale))
    view.set_points([dict(point_id="p1", x=700, y=150, best_signal_dbm=-50)])
    view.set_ap_groups([dict(group_id="a", position=dict(x=750, y=150))])
    view.set_boundaries_edit_mode(True)
    view.apply_boundaries_brush(50, 100)
    drawing.begin_placement(80, 50, QPointF(700, 500))
    before, history, dirty = deepcopy(app.session.metadata), len(drawing.undo_stack), app.session.dirty
    first = pillow(clean_plan_image(view, app.session.metadata))
    assert first.size == (stale.width(), stale.height())
    assert first.getpixel((100, 250)) == (18, 52, 86)  # Current structural wall.
    assert first.getpixel((275, 200)) == (255, 255, 255)  # Clear frame opening.
    assert first.getpixel((250, 200)) == (51, 65, 85)  # Frame jamb retained.
    assert first.getpixel((155, 150)) == (217, 119, 6)  # Painted dash retained.
    assert first.getpixel((750, 350)) != (255, 255, 255)  # Committed curve.
    for point in ((60, 55), (50, 100), (700, 150), (750, 150), (700, 500)):
        assert first.getpixel(point) == (255, 255, 255)
    assert any(color == (216, 67, 21) for _count, color in first.getcolors(first.width * first.height))
    view.set_zoom(2)
    view.centerOn(700, 500)
    assert pillow(clean_plan_image(view, app.session.metadata)).tobytes() == first.tobytes()
    assert app.session.metadata == before and len(drawing.undo_stack) == history and app.session.dirty == dirty


def test_imported_plan_prints_loaded_pixels_without_reopening_source(window, tmp_path):
    create_survey(window)
    path = tmp_path / "imported.png"
    Image.new("RGB", (450, 900), "#abcdef").save(path)
    window.load_plan_file(str(path), save_metadata=True)
    path.unlink()
    image = clean_plan_image(window.floorplan_view, window.session.metadata)
    assert image.size() == QSize(450, 900) and image.pixelColor(200, 200).name() == "#abcdef"
    window.session.dirty = False


@pytest.mark.parametrize("size", [(800, 400), (300, 900)])
def test_real_pdf_print_is_one_centered_page_without_distortion_or_double_margins(qt_app, tmp_path, size):
    image = QImage(*size, QImage.Format.Format_RGB888)
    image.fill(QColor("#123456"))
    output = tmp_path / "printed.pdf"
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(output))
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Landscape if size[0] > size[1] else QPageLayout.Orientation.Portrait)
    printer.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)
    printer.setFullPage(False)
    paint_plan_page(printer, image)
    document = QPdfDocument()
    try:
        assert document.load(str(output)) == QPdfDocument.Error.None_
        assert document.pageCount() == 1
        page = document.pagePointSize(0)
        assert (page.width() > page.height()) == (size[0] > size[1])
        rendered = pillow(document.render(0, QSize(900, round(900 * page.height() / page.width()))))
        box = ImageChops.difference(rendered, Image.new("RGB", rendered.size, "white")).getbbox()
        left, top, right, bottom = box
        assert (right - left) / (bottom - top) == pytest.approx(size[0] / size[1], abs=.02)
        assert abs(left - (rendered.width - right)) <= 3
        assert abs(top - (rendered.height - bottom)) <= 3
        assert min(left, top, rendered.width - right, rendered.height - bottom) >= 20
    finally:
        document.close()


@pytest.mark.parametrize("mode", ["preview", "cancel", "failure"])
def test_button_preview_uses_snapshot_and_never_requires_saving(editor, tmp_path, mode):
    app, drawing = editor
    assert drawing.apply_edit(rectangle_segments(100, 200, 500, 250, "#123456"))
    before, history, dirty = deepcopy(app.session.metadata), len(drawing.undo_stack), app.session.dirty
    output = tmp_path / "preview.pdf"

    class PdfPrinter(QPrinter):
        def __init__(self, *args):
            super().__init__(*args)
            self.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            self.setOutputFileName(str(output))

    def preview(dialog):
        assert dialog.windowTitle() == app.tr("print_plan")
        if mode != "cancel":
            dialog.preview.paintRequested.emit(dialog.device)
        return QDialog.DialogCode.Rejected

    with (patch("qt_ui.qt_plan_printing.QPrinter", PdfPrinter),
          patch.object(PlanPrintPreviewDialog, "exec", preview), patch.object(app, "save_survey") as save,
          patch("qt_ui.qt_plan_printing.QMessageBox.warning") as warning):
        if mode == "failure":
            with patch("qt_ui.qt_plan_printing.paint_plan_page", side_effect=RuntimeError("device unavailable")):
                assert not app.print_plan()
            assert warning.call_count == 1
        else:
            app.print_plan_button.click()
            assert not warning.called
            assert output.exists() == (mode == "preview")
        save.assert_not_called()
    assert app.session.metadata == before and len(drawing.undo_stack) == history and app.session.dirty == dirty


def test_invalid_drawing_is_reported_instead_of_printing_stale_raster(editor):
    app, drawing = editor
    app.session.metadata[PLAN_DRAWING_KEY] = "invalid JSON"
    with patch("qt_ui.qt_plan_printing.QMessageBox.warning") as warning, \
            patch("qt_ui.qt_plan_printing.PlanPrintPreviewDialog") as preview:
        assert not app.print_plan()
        assert warning.call_count == 1 and not preview.called


@pytest.mark.parametrize("accepted", [False, True])
def test_page_setup_and_printer_dialog_only_apply_confirmed_actions(editor, tmp_path, accepted):
    app, drawing = editor
    printer = QPrinter()
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(tmp_path / "unused.pdf"))
    dialog = PlanPrintPreviewDialog(printer, app)
    assert dialog.minimumSizeHint().width() <= app.spx(1000)
    result = QDialog.DialogCode.Accepted if accepted else QDialog.DialogCode.Rejected
    try:
        with (patch.object(QPageSetupDialog, "exec", return_value=result),
              patch.object(QPrintDialog, "exec", return_value=result),
              patch.object(dialog.preview, "updatePreview") as refresh,
              patch.object(dialog.preview, "print") as send):
            dialog.page_setup()
            assert refresh.call_count == int(accepted)
            dialog.print_button.click()
            assert send.call_count == int(accepted)
            assert refresh.call_count == 2 * int(accepted)
        assert not (tmp_path / "unused.pdf").exists()
    finally:
        dialog.deleteLater()
