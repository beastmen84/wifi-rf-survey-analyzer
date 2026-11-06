"""Clean floor-plan snapshots and a single-page native print preview."""
from PIL import Image
from PySide6.QtCore import QMarginsF, QRectF
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPainter
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewWidget, QPrintDialog, QPageSetupDialog
from PySide6.QtWidgets import QDialog, QHBoxLayout, QMessageBox, QPushButton, QVBoxLayout

from app_core.logging import log_exception
from survey.plan_drawing import drawing_geometry, render_plan_drawing
from survey.plan_labels import drawing_labels
from survey.plan_annotations import drawing_annotations


def clean_plan_image(view, metadata):
    # Read the loaded source, never the viewport/scene containing survey overlays.
    image = view.pixmap_item.pixmap().toImage()
    lines, curves = drawing_geometry(metadata)
    labels, annotations = drawing_labels(metadata), drawing_annotations(metadata)
    if lines is None and not (curves or labels or annotations):
        return image
    native = image.convertToFormat(QImage.Format.Format_RGBA8888)
    source = Image.frombytes("RGBA", (native.width(), native.height()), bytes(native.constBits()),
                             "raw", "RGBA", native.bytesPerLine()).convert("RGB")
    rendered = render_plan_drawing(source, lines, labels, curves, annotations)
    return QImage(rendered.tobytes("raw", "RGB"), rendered.width, rendered.height,
                  rendered.width * 3, QImage.Format.Format_RGB888).copy()


def paint_plan_page(printer, image):
    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError("Cannot start the print device")
    try:
        # With fullPage=False, the device origin is the printable area's corner.
        # Using its width/height avoids applying paper margins twice.
        width, height = printer.width(), printer.height()
        if image.isNull() or width <= 0 or height <= 0:
            raise ValueError("The plan or printable page is empty")
        factor = min(width / image.width(), height / image.height())
        target = QRectF((width - image.width() * factor) / 2,
                        (height - image.height() * factor) / 2,
                        image.width() * factor, image.height() * factor)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(target, image)
    finally:
        if not painter.end():
            raise RuntimeError("Cannot finish the print page")


class PlanPrintPreviewDialog(QDialog):
    def __init__(self, printer, owner):
        super().__init__(owner)
        self.device = printer
        self.setWindowTitle(owner.tr("print_plan"))
        available = owner.screen().availableGeometry()
        self.resize(min(owner.spx(1000), available.width()), min(owner.spx(760), available.height()))
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        layout.addLayout(controls)
        self.preview = QPrintPreviewWidget(printer, self)
        for text, callback in ((owner.tr("print_plan_setup"), self.page_setup),
                               ("−", self.preview.zoomOut), ("+", self.preview.zoomIn),
                               (owner.tr("fit"), lambda: self.preview.setZoomMode(QPrintPreviewWidget.ZoomMode.FitInView))):
            button = QPushButton(text)
            button.setObjectName("compactButton")
            button.setAutoDefault(False)
            button.clicked.connect(lambda _checked=False, action=callback: action())
            controls.addWidget(button)
        controls.addStretch()
        self.print_button = QPushButton(owner.tr("print_plan_send"))
        self.print_button.setObjectName("compactButton")
        self.print_button.setAutoDefault(False)
        self.print_button.clicked.connect(self.choose_printer)
        controls.addWidget(self.print_button)
        close = QPushButton(owner.tr("close"))
        close.setObjectName("compactButton")
        close.setAutoDefault(False)
        close.clicked.connect(self.reject)
        controls.addWidget(close)
        layout.addWidget(self.preview, 1)

    def page_setup(self):
        dialog = QPageSetupDialog(self.device, self)
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.preview.updatePreview()
        finally:
            dialog.deleteLater()

    def choose_printer(self):
        dialog = QPrintDialog(self.device, self)
        # A clean plan is exactly one page; unsupported range/selection modes
        # must not imply that parts of the drawing will be printed separately.
        dialog.setMinMax(1, 1)
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.preview.print()
                self.preview.updatePreview()
        finally:
            dialog.deleteLater()


class PlanPrintingMixin:
    def print_plan(self):
        if self.session is None or self.scan_in_progress or not self.floorplan_view.has_floorplan():
            return False
        dialog = None
        try:
            image = clean_plan_image(self.floorplan_view, dict(self.session.metadata))
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setDocName(self.session_display_name())
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            printer.setPageOrientation(QPageLayout.Orientation.Landscape if image.width() > image.height()
                                       else QPageLayout.Orientation.Portrait)
            printer.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)
            printer.setFullPage(False)
            dialog = PlanPrintPreviewDialog(printer, self)
            errors = []

            def paint(device):
                try:
                    paint_plan_page(device, image)
                except Exception as error:
                    errors.append(error)
                    dialog.reject()

            dialog.preview.paintRequested.connect(paint)
            dialog.exec()
            if errors:
                raise errors[0]
            return True  # Preview closed; this does not assert a physical print.
        except Exception as error:
            log_exception("qt clean plan print failed", error, logger_name="main")
            QMessageBox.warning(self, self.tr("print_plan"), self.tr("print_plan_error", error=str(error)))
            return False
        finally:
            if dialog is not None:
                dialog.deleteLater()
