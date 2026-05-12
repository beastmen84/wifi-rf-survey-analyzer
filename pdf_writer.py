"""Inline image PDF writer used by map export workflows."""

from base64 import a85encode
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage


@dataclass(frozen=True)
class InlinePdfPageImage:
    jpeg_bytes: bytes
    width_px: int
    height_px: int
    width_pt: float
    height_pt: float


def write_figures_as_live_pdf(figures, output_file):
    write_figures_as_inline_image_pdf(figures, output_file)


def write_figures_as_inline_image_pdf(figures, output_file):
    pages = [render_figure_to_pdf_page(fig) for fig in figures]
    if not pages:
        return

    write_inline_image_pdf(pages, output_file)


def render_figure_to_pdf_page(fig):
    render_dpi = 150
    buffer = BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=render_dpi,
        facecolor="white",
        edgecolor="white",
        transparent=False,
    )
    buffer.seek(0)
    with PILImage.open(buffer) as image:
        rgb_image = image.convert("RGB")
        jpeg_buffer = BytesIO()
        rgb_image.save(jpeg_buffer, format="JPEG", quality=92, optimize=True)
        width_px, height_px = rgb_image.size
        return InlinePdfPageImage(
            jpeg_bytes=jpeg_buffer.getvalue(),
            width_px=width_px,
            height_px=height_px,
            width_pt=(width_px / render_dpi) * 72.0,
            height_pt=(height_px / render_dpi) * 72.0,
        )


def write_inline_image_pdf(pages, output_file):
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        build_inline_pdf_pages_object(len(pages)),
    ]
    for index, page in enumerate(pages):
        page_object_number = 3 + index * 2
        content_object_number = page_object_number + 1
        objects.append(build_inline_pdf_page_object(page, content_object_number))
        objects.append(build_inline_pdf_content_object(page))

    output = BytesIO()
    output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, payload in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{object_number} 0 obj\n".encode("ascii"))
        output.write(payload)
        output.write(b"\nendobj\n")

    xref_position = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_position}\n%%EOF\n"
        ).encode("ascii")
    )
    Path(output_file).write_bytes(output.getvalue())


def build_inline_pdf_pages_object(page_count):
    kids = " ".join(f"{3 + index * 2} 0 R" for index in range(page_count))
    return f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii")


def build_inline_pdf_page_object(page, content_object_number):
    return (
        f"<< /Type /Page /Parent 2 0 R "
        f"/MediaBox [0 0 {page.width_pt:.4f} {page.height_pt:.4f}] "
        f"/Resources << /ProcSet [/PDF /ImageC] >> "
        f"/Contents {content_object_number} 0 R >>"
    ).encode("ascii")


def build_inline_pdf_content_object(page):
    content = build_inline_pdf_image_content(page)
    return b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream"


def build_inline_pdf_image_content(page):
    encoded_image = a85encode(page.jpeg_bytes, adobe=False) + b"~>"
    header = (
        f"q\n{page.width_pt:.4f} 0 0 {page.height_pt:.4f} 0 0 cm\n"
        "BI\n"
        f"/W {page.width_px}\n"
        f"/H {page.height_px}\n"
        "/CS /RGB\n"
        "/BPC 8\n"
        "/F [/ASCII85Decode /DCTDecode]\n"
        "ID\n"
    ).encode("ascii")
    return header + encoded_image + b"\nEI\nQ\n"
