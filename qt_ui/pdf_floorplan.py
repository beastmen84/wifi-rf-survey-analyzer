"""PDF floor-plan rasterization helpers backed by QtPdf."""

from io import BytesIO

from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtPdf import QPdfDocument


PDF_RENDER_SCALE = 2.0


def render_pdf_page_to_qimage(file_path, page_index=0, scale=PDF_RENDER_SCALE):
    document = QPdfDocument(None)
    try:
        error = document.load(str(file_path))
        if error != QPdfDocument.Error.None_:
            raise ValueError(f"Unable to load PDF floor plan: {file_path}")
        if page_index < 0 or page_index >= document.pageCount():
            raise ValueError(f"PDF floor plan page {page_index + 1} is not available: {file_path}")

        page_size = document.pagePointSize(page_index)
        target_size = QSize(
            max(1, int(round(page_size.width() * scale))),
            max(1, int(round(page_size.height() * scale))),
        )
        image = document.render(page_index, target_size)
        if image.isNull():
            raise ValueError(f"Unable to render PDF floor plan: {file_path}")
        # QtPdf leaves unpainted areas transparent. Dropping their alpha would
        # turn paper margins black in both the editor and Live/HTML exports.
        paper = QImage(image.size(), QImage.Format.Format_RGB888)
        paper.fill(Qt.GlobalColor.white)
        painter = QPainter(paper)
        try:
            painter.drawImage(0, 0, image)
        finally:
            painter.end()
        return paper
    finally:
        document.close()


def render_pdf_page_to_pil_image(file_path, page_index=0, scale=PDF_RENDER_SCALE):
    image = render_pdf_page_to_qimage(file_path, page_index=page_index, scale=scale)
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    try:
        if not image.save(buffer, "PNG"):
            raise ValueError(f"Unable to convert PDF floor plan image: {file_path}")
        return Image.open(BytesIO(bytes(buffer.data()))).convert("RGB")
    finally:
        buffer.close()
