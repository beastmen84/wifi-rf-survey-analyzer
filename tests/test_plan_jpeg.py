"""Paper dimensions, clean snapshot exports, atomic failures and benign cancellation."""
from copy import deepcopy
from unittest.mock import patch

from PIL import Image
import pytest
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QDialog, QMessageBox

from qt_ui.qt_plan_jpeg import PlanJpegDialog, page_pixels, render_plan_page, write_plan_jpeg
from qt_ui.qt_plan_printing import PlanPrintPreviewDialog, PrintDeviceNotStarted, clean_plan_source, clean_plan_image
from survey.plan_drawing import rectangle_segments
from tests.test_blank_plan import create_survey
from tests.test_rectangle_design import editor
from tests.test_capture_adapter import window, qt_app


@pytest.mark.parametrize("paper,mm", [("A5", (148, 210)), ("A4", (210, 297)), ("A3", (297, 420)),
    ("A2", (420, 594)), ("A1", (594, 841)), ("A0", (841, 1189)),
    ("Letter", (215.9, 279.4)), ("Legal", (215.9, 355.6))])
@pytest.mark.parametrize("dpi", [150, 300, 600])
@pytest.mark.parametrize("landscape", [False, True])
def test_paper_pixels_match_physical_dimensions(paper, mm, dpi, landscape):
    size = page_pixels(paper, landscape, dpi)
    width, height = reversed(mm) if landscape else mm
    assert (size.width(), size.height()) == (round(width / 25.4 * dpi), round(height / 25.4 * dpi))


def test_jpeg_button_beside_print_and_has_same_availability(window, qt_app):
    assert not window.save_plan_jpeg_button.isEnabled() and not window.save_plan_jpeg()
    create_survey(window)
    window.resize(1600, 1000)
    window.show()
    qt_app.processEvents()
    button = window.save_plan_jpeg_button
    assert button.parentWidget() is window.print_plan_button.parentWidget()
    assert button.x() > window.print_plan_button.geometry().right()
    assert button.height() == window.print_plan_button.height()
    for tab in (0, 1, 2):
        window.tabs.setCurrentIndex(tab)
        window.refresh_session_labels()
        assert button.isEnabled()
    window.scan_in_progress = True
    window.refresh_session_labels()
    assert not button.isEnabled() and not window.save_plan_jpeg()
    window.scan_in_progress = False
    window.floorplan_view.clear_floorplan()
    window.refresh_session_labels()
    assert not button.isEnabled()


@pytest.mark.parametrize("paper,landscape,dpi,units", [("A4", True, 300, "metric"), ("A3", False, 150, "imperial")])
def test_actual_jpeg_includes_clean_plan_scale_and_print_resolution(editor, tmp_path, paper, landscape, dpi, units):
    app, d = editor
    app.measurement_system = units
    d.store(rectangle_segments(100, 100, 650, 400, "#123456"))
    before, history, dirty = deepcopy(app.session.metadata), len(d.undo_stack), app.session.dirty
    target = tmp_path / "Pianta è già pronta.jpeg"
    def options(dialog):
        dialog.paper.setCurrentIndex(dialog.paper.findData(paper))
        dialog.orientation.setCurrentIndex(int(landscape))
        dialog.resolution.setCurrentIndex(dialog.resolution.findData(dpi))
        assert not dialog.preview.pixmap().isNull()
        return QDialog.DialogCode.Accepted
    with (patch.object(PlanJpegDialog, "exec", options),
          patch("qt_ui.qt_plan_jpeg.get_centered_save_file_name", return_value=(str(target), "JPEG")),
          patch.object(app, "save_survey") as save,
          patch("qt_ui.qt_plan_jpeg.QMessageBox.warning") as warning):
        assert app.save_plan_jpeg(), warning.call_args
        assert not warning.called and not save.called
    with Image.open(target) as image:
        size = page_pixels(paper, landscape, dpi)
        assert image.format == "JPEG" and image.size == (size.width(), size.height())
        assert image.info["dpi"] == pytest.approx((dpi, dpi), abs=1)
        assert image.getpixel((0, 0)) == (255, 255, 255)
        # The footer has a real reference, not an empty page or viewport capture.
        crop = image.crop((0, image.height - round(27 * dpi / 25.4), image.width, image.height))
        assert crop.convert("L").getextrema()[0] < 100
        # The unique structural color survives lossy JPEG compression nearby.
        assert any(abs(r - 18) + abs(g - 52) + abs(b - 86) < 15
                   for _n, (r, g, b) in image.getcolors(image.width * image.height))
    assert app.session.metadata == before and len(d.undo_stack) == history and app.session.dirty == dirty


@pytest.mark.parametrize("stage", ["options", "filename", "normalized_overwrite"])
def test_cancel_never_writes_or_shows_error(editor, tmp_path, stage):
    app, d = editor
    target = tmp_path / "plan.jpg"
    target.write_bytes(b"existing")
    result = QDialog.DialogCode.Rejected if stage == "options" else QDialog.DialogCode.Accepted
    name = str(target.with_suffix("")) if stage == "normalized_overwrite" else ""
    before = deepcopy(app.session.metadata)
    with (patch.object(PlanJpegDialog, "exec", return_value=result),
          patch("qt_ui.qt_plan_jpeg.get_centered_save_file_name", return_value=(name, "")) as choose,
          patch("qt_ui.qt_plan_jpeg.QMessageBox.question", return_value=QMessageBox.StandardButton.No),
          patch("qt_ui.qt_plan_jpeg.write_plan_jpeg") as write,
          patch("qt_ui.qt_plan_jpeg.QMessageBox.warning") as warning):
        assert not app.save_plan_jpeg()
        assert choose.called == (stage != "options")
        assert not write.called and not warning.called
    assert target.read_bytes() == b"existing" and app.session.metadata == before


def test_failed_encoder_preserves_existing_file_atomically(qt_app, tmp_path):
    target = tmp_path / "existing.jpg"
    target.write_bytes(b"previous complete file")
    image = QImage(30, 30, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    with patch("qt_ui.qt_plan_jpeg.QImageWriter.write", return_value=False):
        with pytest.raises(OSError):
            write_plan_jpeg(target, image)
    assert target.read_bytes() == b"previous complete file"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("extension", ["", ".JPG", ".JPEG", ".png"])
def test_filename_suffix_is_an_actual_jpeg(editor, tmp_path, extension):
    app, d = editor
    target = tmp_path / ("map" + extension)
    with (patch.object(PlanJpegDialog, "exec", return_value=QDialog.DialogCode.Accepted),
          patch("qt_ui.qt_plan_jpeg.get_centered_save_file_name", return_value=(str(target), "")),
          patch("qt_ui.qt_plan_jpeg.render_plan_page", return_value=QImage(10, 10, QImage.Format.Format_RGB32)),
          patch("qt_ui.qt_plan_jpeg.write_plan_jpeg") as write):
        assert app.save_plan_jpeg()
    assert write.call_args.args[0].name == (target.name if extension in (".JPG", ".JPEG") else target.name + ".jpg")


@pytest.mark.parametrize("native_accepted", [False, True])
def test_print_cancellation_in_native_or_driver_file_prompt_is_not_an_error(editor, native_accepted):
    app, d = editor
    def preview(dialog):
        def print_page(device, *_args):
            if dialog.printing:
                # This is the user's logged failure after Windows file-prompt Cancel.
                raise PrintDeviceNotStarted("Cannot start the print device")
            return True
        def send():
            assert dialog.printing
            dialog.preview.paintRequested.emit(dialog.device)
        with (patch("qt_ui.qt_plan_printing.QPrintDialog.exec", return_value=(QDialog.DialogCode.Accepted
                    if native_accepted else QDialog.DialogCode.Rejected)),
              patch("qt_ui.qt_plan_printing.paint_plan_page", side_effect=print_page),
              patch.object(dialog.preview, "print", side_effect=send) as print_job,
              patch.object(dialog.preview, "updatePreview") as refresh):
            dialog.choose_printer()
            assert print_job.call_count == int(native_accepted)
            assert refresh.call_count == int(native_accepted)
            assert not dialog.printing
        return QDialog.DialogCode.Rejected
    with (patch.object(PlanPrintPreviewDialog, "exec", preview),
          patch("qt_ui.qt_plan_printing.QMessageBox.warning") as warning):
        assert app.print_plan()
        assert not warning.called


def test_genuine_preview_failure_is_still_reported(editor):
    app, d = editor
    def preview(dialog):
        dialog.preview.paintRequested.emit(dialog.device)
        return QDialog.DialogCode.Rejected
    with (patch.object(PlanPrintPreviewDialog, "exec", preview),
          patch("qt_ui.qt_plan_printing.paint_plan_page", side_effect=PrintDeviceNotStarted("device unavailable")),
          patch("qt_ui.qt_plan_printing.QMessageBox.warning") as warning):
        assert not app.print_plan()
        assert warning.call_count == 1


def test_drawn_paths_render_directly_and_remain_an_immutable_snapshot(editor):
    from tests.test_plan_text_fill import label
    from tests.test_plan_objects import obj
    from tests.test_plan_annotations import aperture, marker
    app, d = editor
    d.store(rectangle_segments(100, 200, 500, 250, "#123456"), labels=[label()],
            curves=[dict(kind="circle", cx=720, cy=300, radius=50, color="#ff0000")],
            annotations=[aperture(), marker(), obj(fill="#abcdef")])
    source = clean_plan_source(d.view, app.session.metadata)
    before = deepcopy(app.session.metadata)
    with patch.object(QPainter, "drawImage") as raster:
        first = render_plan_page(source, "A4", True, 150, app.get_px_per_meter())
        raster.assert_not_called()  # Paths, not an enlarged low-resolution plan.
    d.store([])
    second = render_plan_page(source, "A4", True, 150, app.get_px_per_meter())
    assert first == second and app.session.metadata != before
    imported = QImage(200, 100, QImage.Format.Format_RGB32)
    imported.fill(QColor("#123456"))
    with patch.object(QPainter, "drawImage") as raster:
        render_plan_page(imported, "A4", True, 150)
        assert raster.call_count == 1  # Imported bitmap detail cannot be invented.


def test_a3_600dpi_has_actual_fine_edges_and_correct_jpeg_density(editor, tmp_path):
    app, d = editor
    d.store([dict(x1=123.37, y1=100, x2=123.37, y2=500, color="#000000")])
    density = app.get_px_per_meter()
    size = page_pixels("A3", False, 600)
    margin, footer = 10 * 600 / 25.4, 17 * 600 / 25.4
    factor = min((size.width() - 2 * margin) / 900, (size.height() - 2 * margin - footer) / 600)
    x = round(margin + 123.37 * factor)
    y = round(margin + (size.height() - 2 * margin - footer - 600 * factor) / 2 + 300 * factor)
    def partial_edges(page):
        return sum(15 < page.pixelColor(i, y).red() < 240 for i in range(x - 30, x + 31))
    old = render_plan_page(clean_plan_image(d.view, app.session.metadata), "A3", False, 600, density)
    blurred = partial_edges(old)
    del old
    page = render_plan_page(clean_plan_source(d.view, app.session.metadata), "A3", False, 600, density)
    assert partial_edges(page) <= 4 and blurred > partial_edges(page) + 4
    output = tmp_path / "a3-600.jpg"
    write_plan_jpeg(output, page)
    with Image.open(output) as image:
        assert image.size == (7016, 9921) and image.info["dpi"] == pytest.approx((600, 600), abs=1)
        assert image.crop((x - 30, y - 2, x + 31, y + 3)).convert("L").getextrema()[0] < 20


@pytest.mark.parametrize("paper", ["A1", "A0"])
def test_extreme_page_limit_is_visible_and_checked_before_allocation(editor, paper):
    app, d = editor
    source = clean_plan_source(d.view, app.session.metadata)
    dialog = PlanJpegDialog(app, source, app.get_px_per_meter(), "metric")
    try:
        dialog.paper.setCurrentIndex(dialog.paper.findData(paper))
        dialog.resolution.setCurrentIndex(dialog.resolution.findData(600))
        assert not dialog.save_button.isEnabled() and not dialog.size_limit.isHidden()
        with patch("qt_ui.qt_plan_jpeg.QImage") as allocate:
            with pytest.raises(ValueError, match="size limit"):
                render_plan_page(source, paper, False, 600)
            allocate.assert_not_called()
        dialog.resolution.setCurrentIndex(dialog.resolution.findData(300))
        assert dialog.save_button.isEnabled() and dialog.size_limit.isHidden()
    finally:
        dialog.deleteLater()
