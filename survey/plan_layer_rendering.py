"""Render visible layer paths in stack order, without cross-layer topology."""
from hashlib import sha256
import json
from PIL import Image
from PySide6.QtCore import QRectF, QSize
from PySide6.QtGui import QImage, QPainter
from qt_ui.qt_clean_plan import VectorPlanSource


def source_for_layers(size, payload, background=None):
    return VectorPlanSource.from_layers(size, payload["layers"], None if payload["generated"] else background)


def render_layers(image, payload):
    rgb = image.convert("RGBA")
    background = QImage(rgb.tobytes(), rgb.width, rgb.height, rgb.width * 4, QImage.Format.Format_RGBA8888).copy()
    source = source_for_layers(QSize(image.width, image.height), payload, background)
    native = QImage(image.width, image.height, QImage.Format.Format_RGB32)
    native.fill(0xffffffff)
    painter = QPainter(native)
    try:
        source.paint_plan(painter, QRectF(0, 0, image.width, image.height))
    finally:
        painter.end()
    rgba = native.convertToFormat(QImage.Format.Format_RGBA8888)
    result = Image.frombytes("RGBA", image.size, bytes(rgba.constBits()), "raw", "RGBA", rgba.bytesPerLine()).convert("RGB")
    result.info["plan_drawing_fingerprint"] = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return result
