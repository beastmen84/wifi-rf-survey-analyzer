"""Standalone HTML and selectable-text PDF reports from the same analysis result."""

from base64 import b64encode
from io import BytesIO
import os
from pathlib import Path
import re
import tempfile

from PIL import Image, ImageDraw, ImageFont
from PySide6.QtCore import QMarginsF, QRectF, Qt
from PySide6.QtGui import QPageLayout, QPageSize, QTextDocument, QPdfWriter, QPainter, QFont
from PySide6.QtPdf import QPdfDocument

from advisor.presentation import report_html
from app_core.file_io import atomic_write_text


def _print_html(html, path, title):
    """Paginate our generated HTML, keeping ordinary evidence rows together.

    QTextDocument's automatic printing can split a table cell across pages.
    Render fitting table chunks instead, repeating the measured-evidence header.
    QPdfWriter also avoids initializing Windows' native printer drivers.
    """
    writer = QPdfWriter(str(path))
    writer.setResolution(96)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(14, 16, 14, 16), QPageLayout.Unit.Millimeter)
    writer.setTitle(title)
    painter = QPainter(writer)
    if not painter.isActive():
        raise OSError("PDF generation failed")
    width, height = writer.width(), writer.height() - 28
    y, page = 0, 1
    head, _, body = html.partition("<body>")
    body = body.removesuffix("</body></html>")

    def background():
        full = writer.pageLayout().fullRectPixels(96)
        paint = writer.pageLayout().paintRectPixels(96)
        painter.fillRect(QRectF(-paint.x(), -paint.y(), full.width(), full.height()), Qt.GlobalColor.white)

    background()

    def document(fragment):
        doc = QTextDocument()
        doc.setDocumentMargin(0)
        doc.setHtml(head + "<body>" + fragment + "</body></html>")
        doc.setTextWidth(width)
        return doc

    def footer():
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(QRectF(0, height + 8, width, 20), Qt.AlignmentFlag.AlignRight, str(page))

    def next_page():
        nonlocal y, page
        footer()
        if not writer.newPage():
            raise OSError("PDF page generation failed")
        y, page = 0, page + 1
        background()

    def draw(doc):
        nonlocal y
        total = doc.size().height()
        if y and total > height - y:
            next_page()
        start = 0
        while start < total:
            end = min(total, start + height - y)
            if end < total:
                # An exceptionally long paragraph/row can exceed a whole page.
                # Keep its text lines intact even in that case.
                boundaries = []
                block = doc.begin()
                while block.isValid():
                    rect = doc.documentLayout().blockBoundingRect(block)
                    layout = block.layout()
                    boundaries.extend(rect.y() + layout.lineAt(i).y() + layout.lineAt(i).height()
                                      for i in range(layout.lineCount()))
                    block = block.next()
                end = max((v for v in boundaries if start < v <= end), default=end)
            painter.save()
            painter.setClipRect(QRectF(0, y, width, end - start))
            painter.translate(0, y - start)
            doc.drawContents(painter, QRectF(0, start, width, end - start))
            painter.restore()
            y += end - start
            start = end
            if start < total:
                next_page()
        y += 8

    try:
        # These are the top-level elements emitted by advisor.presentation,
        # whose user-provided values are always HTML-escaped.
        fragments = [m.group(0) for m in re.finditer(
            r"<(h[1-3]|p|table|ul)\b[^>]*>.*?</\1>|<hr\s*/?>", body, re.S)]
        for index, fragment in enumerate(fragments):
            if not fragment.startswith("<table"):
                doc = document(fragment)
                if fragment.startswith(("<h1", "<h2", "<h3")) and index + 1 < len(fragments):
                    following = min(100, document(fragments[index + 1]).size().height())
                    if y and doc.size().height() + 8 + following > height - y:
                        next_page()
                draw(doc)
                continue
            opening = fragment[:fragment.index(">") + 1]
            header_match = re.search(r"<thead>.*?</thead>", fragment, re.S)
            header = header_match.group(0) if header_match else ""
            rows = re.findall(r"<tr>.*?</tr>", fragment.replace(header, "", 1), re.S)
            while rows:
                def chunk(count):
                    return document(opening + header + "".join(rows[:count]) + "</table>")
                if y and chunk(1).size().height() > height - y:
                    next_page()
                low, high = 1, len(rows)
                while low < high:
                    middle = (low + high + 1) // 2
                    if chunk(middle).size().height() <= height - y:
                        low = middle
                    else:
                        high = middle - 1
                draw(chunk(low))
                rows = rows[low:]
                if rows:
                    next_page()
        footer()
    finally:
        painter.end()
        # Finish the file before validation/replacement on Windows.
        writer = None


def overview_data(image, report):
    if image is None:
        return ""
    original = image.size
    image = image.copy()
    image.thumbnail((620, 400))
    image = Image.alpha_composite(Image.new("RGBA", image.size, "white"), image.convert("RGBA")).convert("RGB")
    sx, sy = image.width / original[0], image.height / original[1]
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=14)
    for index, point in enumerate(report.points, 1):
        x, y = point.x * sx, point.y * sy
        if not (0 <= x < image.width and 0 <= y < image.height):
            continue
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#3A6EA5", outline="white", width=2)
        draw.text((x + 7, y - 8), str(index), font=font, fill="#25313D", stroke_width=2, stroke_fill="white")
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return "data:image/png;base64," + b64encode(buffer.getvalue()).decode("ascii")


def export_analysis_report(report, output_file, language="en", floorplan_image=None):
    path = Path(output_file)
    html = report_html(report, language, overview_data(floorplan_image, report), browser=path.suffix.lower() == ".html")
    if path.suffix.lower() == ".html":
        atomic_write_text(path, html)
        return str(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError("Choose PDF or HTML")
    descriptor, temporary = tempfile.mkstemp(prefix=".analysis-", suffix=".pdf", dir=path.parent)
    os.close(descriptor)
    try:
        _print_html(html, temporary, report.survey_name)
        validation = QPdfDocument(None)
        try:
            error = validation.load(temporary)
            if error != QPdfDocument.Error.None_ or validation.pageCount() < 1:
                raise OSError("PDF generation failed")
        finally:
            validation.close()
            del validation
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return str(path)
