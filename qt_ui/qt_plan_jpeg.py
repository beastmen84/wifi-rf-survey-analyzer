"""Paper-sized JPEG exports of clean plans, sharing the calibrated print layout."""
import math
from pathlib import Path

from PySide6.QtCore import QIODevice, QSaveFile, QSize, Qt
from PySide6.QtGui import QImage, QImageWriter, QPageSize, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QLabel, QMessageBox, QVBoxLayout, QCheckBox)

from app_core.logging import log_exception
from app_core.settings import get_last_survey_directory
from qt_ui.qt_plan_printing import clean_plan_source, draw_plan_page
from qt_ui.qt_windowing import get_centered_save_file_name
from qt_ui.scaling import widget_px
from qt_ui.qt_plan_legend import export_legend_tables
from qt_ui.qt_legend_pages import legend_pages, paint_legend_page
from app_core.file_io import SurveyFileTransaction, file_digest

PAPER_SIZES = ("A5", "A4", "A3", "A2", "A1", "A0", "Letter", "Legal")
RESOLUTIONS = (150, 300, 600)
# One RGB32 output page, including the existing A0/300 preset, stays below 600MB.
MAX_PAGE_PIXELS = 150_000_000


def paper_mm(paper, landscape=False):
    if paper not in PAPER_SIZES:
        raise ValueError("Unsupported paper size")
    size = QPageSize(getattr(QPageSize.PageSizeId, paper)).size(QPageSize.Unit.Millimeter)
    return (size.height(), size.width()) if landscape else (size.width(), size.height())


def page_pixels(paper, landscape, dpi):
    if not math.isfinite(dpi) or dpi <= 0 or dpi > 600:
        raise ValueError("Unsupported resolution")
    return QSize(*(max(1, round(mm * dpi / 25.4)) for mm in paper_mm(paper, landscape)))


def render_plan_page(image, paper, landscape, dpi, density=None, units="metric", tr=None):
    size = page_pixels(paper, landscape, dpi)
    if size.width() * size.height() > MAX_PAGE_PIXELS:
        raise ValueError("The selected page exceeds the raster export size limit")
    canvas = QImage(size, QImage.Format.Format_RGB32)
    if canvas.isNull():
        raise MemoryError("Cannot allocate the JPEG page")
    canvas.setDotsPerMeterX(round(dpi / .0254))
    canvas.setDotsPerMeterY(round(dpi / .0254))
    canvas.fill(Qt.GlobalColor.white)
    painter = QPainter(canvas)
    try:
        margin = 10 * dpi / 25.4
        painter.translate(margin, margin)
        draw_plan_page(painter, image, size.width() - 2 * margin, size.height() - 2 * margin,
                       dpi, density, units, tr)
    finally:
        painter.end()
    return canvas


def write_plan_jpeg(path, image):
    """Commit a complete JPEG atomically, preserving an existing target on failure."""
    device = QSaveFile(str(path))
    if not device.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError(device.errorString())
    try:
        writer = QImageWriter(device, b"jpeg")
        writer.setQuality(95)
        if not writer.write(image):
            raise OSError(writer.errorString())
        if not device.commit():
            raise OSError(device.errorString())
    finally:
        if device.isOpen():
            device.cancelWriting()


def legend_page_layout(tables, paper, landscape, tr):
    width, height = paper_mm(paper, landscape)
    return legend_pages(tables, (width-20)*72/25.4, (height-20)*72/25.4, tr)


def render_legend_image(blocks, paper, landscape, dpi, index, total, tr):
    size = page_pixels(paper, landscape, dpi)
    if size.width()*size.height() > MAX_PAGE_PIXELS:
        raise ValueError("The selected page exceeds the raster export size limit")
    canvas = QImage(size, QImage.Format.Format_RGB32)
    if canvas.isNull():
        raise MemoryError("Cannot allocate the legend image")
    canvas.setDotsPerMeterX(round(dpi/.0254))
    canvas.setDotsPerMeterY(round(dpi/.0254))
    canvas.fill(Qt.GlobalColor.white)
    painter = QPainter(canvas)
    try:
        margin = 10*dpi/25.4
        painter.translate(margin, margin)
        width, height = paper_mm(paper, landscape)
        paint_legend_page(painter, blocks, (width-20)*72/25.4, (height-20)*72/25.4, dpi, index, total, tr)
    finally:
        painter.end()
    return canvas


class PlanJpegDialog(QDialog):
    def __init__(self, owner, image, density, units):
        super().__init__(owner)
        self.owner, self.image, self.density, self.units = owner, image, density, units
        self.setWindowTitle(owner.tr("save_plan_jpeg"))
        self.setMinimumWidth(widget_px(owner, 450))
        layout = QVBoxLayout(self)
        layout.setSpacing(widget_px(owner, 10))
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.paper = QComboBox()
        for name in PAPER_SIZES:
            width, height = paper_mm(name)
            self.paper.addItem(f"{name} · {width:g} × {height:g} mm", name)
        self.paper.setCurrentIndex(PAPER_SIZES.index("A4"))
        self.orientation = QComboBox()
        self.orientation.addItem(owner.tr("plan_jpeg_portrait"), False)
        self.orientation.addItem(owner.tr("plan_jpeg_landscape"), True)
        self.orientation.setCurrentIndex(int(image.width() > image.height()))
        self.resolution = QComboBox()
        for dpi, key in zip(RESOLUTIONS, ("plan_jpeg_draft", "plan_jpeg_quality", "plan_jpeg_detail")):
            self.resolution.addItem(str(dpi) + " DPI · " + owner.tr(key), dpi)
        self.resolution.setCurrentIndex(1)
        form.addRow(owner.tr("plan_jpeg_paper"), self.paper)
        form.addRow(owner.tr("plan_jpeg_orientation"), self.orientation)
        form.addRow(owner.tr("plan_jpeg_resolution"), self.resolution)
        layout.addLayout(form)
        self.legend_tables = export_legend_tables(owner.session)
        self.include_legend = QCheckBox(owner.tr("legend_include"))
        self.include_legend.setChecked(bool(self.legend_tables))
        self.include_legend.setVisible(bool(self.legend_tables))
        layout.addWidget(self.include_legend)
        self.page_choice = QComboBox()
        self.page_label = QLabel(owner.tr("legend_preview_page"))
        form.addRow(self.page_label, self.page_choice)
        self.page_choice.setVisible(bool(self.legend_tables))
        self.page_label.setVisible(bool(self.legend_tables))
        self.dimensions = QLabel()
        self.dimensions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.dimensions)
        self.size_limit = QLabel(owner.tr("plan_jpeg_size_limit"), self)
        self.size_limit.setWordWrap(True)
        self.size_limit.hide()
        layout.addWidget(self.size_limit)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setFixedSize(widget_px(owner, 420), widget_px(owner, 300))
        self.preview.setStyleSheet("background:#dce3eb;border:1px solid #94a3b8;border-radius:5px;")
        layout.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignCenter)
        self.note = QLabel(owner.tr("save_plan_jpeg_hint"), self)
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(owner.tr("save"))
        self.save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(owner.tr("cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        for combo in (self.paper, self.orientation, self.resolution):
            combo.currentIndexChanged.connect(self.refresh_preview)
        self.include_legend.toggled.connect(self.refresh_preview)
        self.page_choice.currentIndexChanged.connect(self.refresh_preview)
        self.refresh_preview()
        self.ensurePolished()
        self.note.setMinimumHeight(self.note.heightForWidth(widget_px(owner, 420)))
        # QDialog's automatic size can compress the aligned fixed preview below
        # its visual bounds when the description wraps at enlarged UI scales.
        self.setMinimumHeight(self.sizeHint().height())
        self.adjustSize()

    def options(self):
        return self.paper.currentData(), self.orientation.currentData(), self.resolution.currentData()

    def refresh_preview(self):
        paper, landscape, dpi = self.options()
        pixels = page_pixels(paper, landscape, dpi)
        self.dimensions.setText(f"{pixels.width():,} × {pixels.height():,} px · {dpi} DPI".replace(",", " "))
        too_large = pixels.width() * pixels.height() > MAX_PAGE_PIXELS
        self.save_button.setEnabled(not too_large)
        self.size_limit.setVisible(too_large)
        self.size_limit.setMinimumHeight(self.size_limit.heightForWidth(widget_px(self.owner, 420)))
        # Preview allocation stays bounded, even for A0 at full export resolution.
        ratio = self.preview.devicePixelRatioF()
        available = self.preview.size() - QSize(widget_px(self.owner, 12), widget_px(self.owner, 12))
        target = QSize(round(available.width() * ratio), round(available.height() * ratio))
        preview_dpi = min(300, max(target.width(), target.height()) * 25.4 / max(paper_mm(paper, landscape)))
        pages = legend_page_layout(self.legend_tables, paper, landscape, self.owner.tr) if self.include_legend.isChecked() else []
        selected = max(0, min(self.page_choice.currentIndex(), len(pages)))
        self.page_choice.blockSignals(True)
        self.page_choice.clear()
        self.page_choice.addItem(self.owner.tr("legend_plan_page"))
        for index in range(len(pages)):
            self.page_choice.addItem(self.owner.tr("legend_page_number").format(number=index+1))
        self.page_choice.setCurrentIndex(selected)
        self.page_choice.blockSignals(False)
        if selected:
            canvas = render_legend_image(pages[selected-1], paper, landscape, preview_dpi, selected, len(pages), self.owner.tr)
        else:
            canvas = render_plan_page(self.image, paper, landscape, preview_dpi, self.density, self.units, self.owner.tr)
        pixmap = QPixmap.fromImage(canvas).scaled(target,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        pixmap.setDevicePixelRatio(ratio)
        self.preview.setPixmap(pixmap)
        self.layout().activate()
        self.setMinimumHeight(self.sizeHint().height())
        self.adjustSize()


def export_plan_jpeg(owner):
    if owner.session is None or owner.scan_in_progress or not owner.floorplan_view.has_floorplan():
        return False
    dialog = None
    try:
        image = clean_plan_source(owner.floorplan_view, dict(owner.session.metadata))
        density, units = owner.get_px_per_meter(), owner.measurement_system
        survey_file = owner.session.csv_file
        dialog = PlanJpegDialog(owner, image, density, units)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        options = dialog.options()
        tables = dialog.legend_tables if getattr(dialog, "include_legend", None) and dialog.include_legend.isChecked() else []
        pages = legend_page_layout(tables, options[0], options[1], owner.tr)
        if survey_file:
            survey = Path(survey_file)
            initial = survey.with_name(survey.stem + "-plan.jpg")
        else:
            initial = Path(get_last_survey_directory()) / "plan.jpg"
        chosen, _filter = get_centered_save_file_name(owner, owner.tr("save_plan_jpeg"), str(initial), "JPEG (*.jpg *.jpeg)")
        if not chosen:
            return False
        target = Path(chosen)
        if target.suffix.lower() not in (".jpg", ".jpeg"):
            target = target.with_suffix(target.suffix + ".jpg")
            # The file dialog confirmed the typed name, not this normalized one.
            if target.exists() and QMessageBox.question(owner, owner.tr("save_plan_jpeg"),
                    owner.tr("plan_jpeg_replace").format(name=target.name),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return False
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if not pages:
                canvas = render_plan_page(image, *options, density, units, owner.tr)
                write_plan_jpeg(target, canvas)
            else:
                targets = [target] + [target.with_name(f"{target.stem}-legend-{i:02d}.jpg") for i in range(1, len(pages)+1)]
                with SurveyFileTransaction(target) as transaction:
                    # Recovery completes before choosing replacements or hashing.
                    existing = [path.name for path in targets[1:] if path.exists()]
                    if existing:
                        QApplication.restoreOverrideCursor()
                        try:
                            if QMessageBox.question(owner, owner.tr("save_plan_jpeg"),
                                    owner.tr("legend_replace_files").format(files="\n".join(existing)),
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                    QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Yes:
                                return False
                        finally:
                            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                    before = {path: file_digest(path) for path in targets}
                    stages = [transaction.stage_file(path) for path in targets]
                    write_plan_jpeg(stages[0], render_plan_page(image, *options, density, units, owner.tr))
                    for i, blocks in enumerate(pages, 1):
                        canvas = render_legend_image(blocks, *options, i, len(pages), owner.tr)
                        write_plan_jpeg(stages[i], canvas)
                    if any(file_digest(path) != digest for path, digest in before.items()):
                        raise OSError("An export target changed while pages were rendered")
                    transaction.commit()
        finally:
            QApplication.restoreOverrideCursor()
        owner.status.showMessage((owner.tr("legend_jpeg_saved").format(path=str(target), count=len(pages))
                                 if pages else owner.tr("plan_jpeg_saved").format(path=str(target))))
        return True
    except Exception as error:
        log_exception("qt clean plan JPEG export failed", error, logger_name="main")
        QMessageBox.warning(owner, owner.tr("save_plan_jpeg"), owner.tr("plan_jpeg_error").format(error=str(error)))
        return False
    finally:
        if dialog is not None:
            dialog.deleteLater()
