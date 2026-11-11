"""Unreadable live hatches can be omitted without losing vector export detail."""
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage,QPainter,QPainterPath,QPen,QColor

from survey.wall_rendering import MaterialPath,MaterialItem,paint_material
from tests.test_capture_adapter import qt_app


def rgb_pixels(image):
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    pixels = np.frombuffer(image.constBits(),np.uint8).reshape(image.height(),image.bytesPerLine())
    pixels = pixels[:,:image.width()*4].reshape(image.height(),image.width(),4)
    return pixels[:,:,:3].copy()


def test_live_overview_omits_subpixel_hatches_but_export_keeps_vectors(qt_app):
    shape = QPainterPath()
    shape.addRect(100,100,300,20)
    material = MaterialPath(shape,'brick','cross')
    elements = material.hatch.elementCount()
    item = MaterialItem(material,QPen(QColor('#263238'),1))
    overview = QImage(512,256,QImage.Format.Format_RGB32)
    overview.fill(Qt.GlobalColor.white)
    painter = QPainter(overview)
    painter.scale(.2,.2)
    item.paint(painter,None)
    painter.end()
    fill = (material.fill.red(),material.fill.green(),material.fill.blue())
    assert np.all(rgb_pixels(overview)[21:23,25:75] == fill)
    export = QImage(512,256,QImage.Format.Format_RGB32)
    export.fill(Qt.GlobalColor.white)
    painter = QPainter(export)
    paint_material(painter,material,item.pen())
    painter.end()
    assert np.any(rgb_pixels(export)[102:118,102:398] != fill)
    assert material.hatch.elementCount() == elements > 0
