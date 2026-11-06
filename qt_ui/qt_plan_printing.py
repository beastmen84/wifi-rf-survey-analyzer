"""Clean floor-plan snapshots and a single-page native print preview."""
from PIL import Image
import math
from PySide6.QtCore import QLocale, QMarginsF, QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter, QPen
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewWidget, QPrintDialog, QPageSetupDialog
from PySide6.QtWidgets import QDialog, QHBoxLayout, QMessageBox, QPushButton, QVBoxLayout

from app_core.logging import log_exception
from survey.plan_drawing import drawing_geometry, render_plan_drawing
from survey.plan_labels import drawing_labels
from survey.plan_annotations import drawing_annotations
from app_core.units import meters_to_display_units, display_units_to_meters, distance_unit_label
from translations.i18n import translate


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


def print_scale_reference(image_width, px_per_meter, measurement_system="metric"):
    try:
        density = float(px_per_meter)
    except (ValueError, TypeError, OverflowError):
        return None
    if not math.isfinite(density) or density <= 0:
        return None
    target = meters_to_display_units(image_width / density * .22, measurement_system)
    if not math.isfinite(target) or target <= 0:
        return None
    power = 10.0 ** math.floor(math.log10(target))
    if not power:
        return None
    length = max(value for value in (1, 2, 5) if value * power <= target * (1 + 1e-12)) * power
    meters = display_units_to_meters(length, measurement_system)
    return dict(value=length, source_pixels=meters * density, unit=distance_unit_label(measurement_system))


class PrintDeviceNotStarted(RuntimeError):
    """A native job can fail to start when its print-to-file prompt is cancelled."""


def draw_plan_page(painter, image, width, height, dpi, px_per_meter=None, measurement_system="metric", tr=None):
    tr = tr or (lambda key: translate("en", key))
    painter.save()
    try:
        if image.isNull() or width <= 0 or height <= 0:
            raise ValueError("The plan or printable page is empty")
        millimeter = dpi / 25.4
        footer = 17 * millimeter
        body_height = height - footer
        if body_height <= 0:
            raise ValueError("The printable page is too small")
        factor = min(width / image.width(), body_height / image.height())
        target = QRectF((width - image.width() * factor) / 2,
                        (body_height - image.height() * factor) / 2,
                        image.width() * factor, image.height() * factor)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(target, image)
        font = painter.font()
        font.setPointSizeF(8.5)
        font.setBold(False)
        painter.setFont(font)
        reference = print_scale_reference(image.width(), px_per_meter, measurement_system)
        x, y = target.left(), height - 6 * millimeter
        if reference:
            length = reference["source_pixels"] * factor
            label = QLocale().toString(reference["value"], "g", 4) + " " + reference["unit"]
            pen = QPen(QColor("#111827"), max(1, .25 * millimeter))
            painter.setPen(pen)
            painter.drawText(QPointF(x, y - 4 * millimeter), tr("print_plan_scale"))
            painter.drawLine(QPointF(x, y), QPointF(x + length, y))
            for endpoint in (x, x + length):
                painter.drawLine(QPointF(endpoint, y - millimeter), QPointF(endpoint, y + millimeter))
            painter.drawText(QPointF(x, y + 4 * millimeter), "0")
            painter.drawText(QPointF(x + length - painter.fontMetrics().horizontalAdvance(label), y + 4 * millimeter), label)
        else:
            painter.setPen(QColor("#475569"))
            painter.drawText(QPointF(x, y), tr("print_plan_scale_missing"))
    finally:
        painter.restore()


def paint_plan_page(printer, image, px_per_meter=None, measurement_system="metric", tr=None):
    painter = QPainter()
    if not painter.begin(printer):
        raise PrintDeviceNotStarted("Cannot start the print device")
    try:
        # fullPage=False makes the printable area's corner the device origin.
        draw_plan_page(painter, image, printer.width(), printer.height(), printer.resolution(),
                       px_per_meter, measurement_system, tr)
    finally:
        if not painter.end() and printer.printerState() != QPrinter.PrinterState.Aborted:
            raise RuntimeError("Cannot finish the print page")
    return printer.printerState() != QPrinter.PrinterState.Aborted


class PlanPrintPreviewDialog(QDialog):
    def __init__(self, printer, owner):
        super().__init__(owner)
        self.device = printer
        self.printing = False
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
                self.printing = True
                try:
                    self.preview.print()
                finally:
                    self.printing = False
                self.preview.updatePreview()
        finally:
            dialog.deleteLater()


class PlanPrintingMixin:
    def save_plan_jpeg(self):
        from qt_ui.qt_plan_jpeg import export_plan_jpeg
        return export_plan_jpeg(self)

    def print_plan(self):
        if self.session is None or self.scan_in_progress or not self.floorplan_view.has_floorplan():
            return False
        dialog = None
        try:
            image = clean_plan_image(self.floorplan_view, dict(self.session.metadata))
            density, units = self.get_px_per_meter(), self.measurement_system
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
                    if not paint_plan_page(device, image, density, units, self.tr):
                        self.status.showMessage(self.tr("print_plan_not_started"))
                except PrintDeviceNotStarted as error:
                    if dialog.printing:
                        # Windows print-to-file cancellation can leave the engine
                        # Idle and return False from begin(), rather than Aborted.
                        self.status.showMessage(self.tr("print_plan_not_started"))
                    else:
                        errors.append(error)
                        dialog.reject()
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
