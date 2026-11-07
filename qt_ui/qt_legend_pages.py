"""Resolution-independent legend pagination and painting in typographic points."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPen, QTextLayout, QTextOption
from survey.plan_objects import object_default, NUMBERED_SYMBOLS
from survey.plan_annotation_rendering import annotation_parts


def font(size=10, bold=False):
    result = QFont("Segoe UI")
    result.setPixelSize(size)
    result.setBold(bold)
    return result


def wrap(text, width, size=10):
    lines = []
    for paragraph in str(text).split("\n"):
        layout = QTextLayout(paragraph or " ", font(size))
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        layout.setTextOption(option)
        layout.beginLayout()
        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(max(1, width))
            encoded = paragraph.encode("utf-16-le")
            lines.append(encoded[line.textStart()*2:(line.textStart()+line.textLength())*2].decode("utf-16-le"))
        layout.endLayout()
    return lines or [""]


def legend_pages(tables, width, height, tr):
    """width/height are printable body points, excluding the paper margins."""
    if not tables:
        return []
    if width < 120 or height < 150:
        raise ValueError("The legend page is too small")
    pages, blocks, y = [], [], 43.0
    line_height = QFontMetricsF(font()).height() + 2
    for index, table in enumerate(tables, 1):
        kind = table["kind"]
        reference_width = 60 if kind in NUMBERED_SYMBOLS else min(155, width * .35)
        def header():
            nonlocal y
            blocks.append(dict(type="header", y=y, kind=kind, index=index, reference_width=reference_width))
            y += 47
        if y + 70 > height - 22:
            pages.append(blocks)
            blocks, y = [], 43.0
        header()
        for row in table["rows"]:
            reference = str(row["number"]) if row["number"] else row["ap"] or tr("object_symbol_" + kind)
            references = wrap(reference, reference_width - 14)
            descriptions = wrap(row["description"] or "—", width - reference_width - 14)
            lines = max(len(references), len(descriptions))
            start = 0
            while start < lines:
                room = int((height - 22 - y - 12) / line_height)
                if room < 1:
                    pages.append(blocks)
                    blocks, y = [], 43.0
                    header()
                    room = int((height - 22 - y - 12) / line_height)
                count = min(room, lines - start)
                blocks.append(dict(type="row", y=y, height=count*line_height+12,
                    reference_width=reference_width, reference=references[start:start+count],
                    description=descriptions[start:start+count], line_height=line_height,
                    continued=start > 0, number=reference))
                y += count*line_height+12
                start += count
        y += 15
    if blocks:
        pages.append(blocks)
    return pages


def paint_legend_page(painter, blocks, width, height, dpi, page_index, page_count, tr):
    painter.save()
    try:
        painter.scale(dpi/72, dpi/72)
        painter.setPen(QColor("#111827"))
        painter.setFont(font(18, True))
        painter.drawText(QPointF(0, 20), tr("plan_legend"))
        painter.setFont(font(9))
        painter.setPen(QColor("#475569"))
        painter.drawText(QPointF(0, 35), tr("legend_visible_export"))
        for block in blocks:
            y, first = block["y"], block["reference_width"]
            if block["type"] == "header":
                painter.setPen(QColor("#111827"))
                painter.setFont(font(11, True))
                title = tr("legend_table").format(number=block["index"], symbol=tr("object_symbol_" + block["kind"]))
                painter.drawText(QPointF(24, y + 15), title)
                item = object_default("symbol", 20, block["kind"])
                item.update(cx=9, cy=y+10, width=14, height=14)
                painter.setPen(QPen(QColor("#334155"), 1))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                for path, _dashed in annotation_parts(item):
                    painter.drawPath(path)
                painter.fillRect(QRectF(0, y+23, width, 24), QColor("#e2e8f0"))
                painter.setFont(font(10, True))
                painter.drawText(QPointF(7, y+39), tr("legend_number" if block["kind"] in NUMBERED_SYMBOLS else "annotation_symbol"))
                painter.drawText(QPointF(first+7, y+39), tr("legend_description"))
            else:
                painter.setPen(QPen(QColor("#cbd5e1"), .5))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(QRectF(0, y, width, block["height"]))
                painter.drawLine(QPointF(first, y), QPointF(first, y+block["height"]))
                painter.setPen(QColor("#111827"))
                painter.setFont(font())
                references = block["reference"] or ([block["number"] + " ↳"] if block["continued"] else [])
                for x, lines in ((7, references), (first+7, block["description"])):
                    for row, text in enumerate(lines):
                        painter.drawText(QPointF(x, y+6+(row+1)*block["line_height"]-2), text)
        painter.setFont(font(9))
        painter.setPen(QColor("#475569"))
        painter.drawText(QPointF(0, height-3), f"{page_index} / {page_count}")
    finally:
        painter.restore()
