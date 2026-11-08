"""Actual rendered bounds verify centering and fitting, independent of the view."""
from copy import deepcopy

from PIL import Image, ImageChops
import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QColor
from qt_ui.qt_clean_plan import VectorPlanSource
from qt_ui.qt_plan_jpeg import render_plan_page, page_pixels, PlanJpegDialog
from survey.plan_drawing import rectangle_segments
from tests.test_network_plan_symbols import symbol
from tests.test_rectangle_design import editor as editor
from tests.test_capture_adapter import window as window, qt_app as qt_app


def red_bounds(image):
    rgb = image.convertToFormat(QImage.Format.Format_RGB888)
    pil = Image.frombytes('RGB', (rgb.width(), rgb.height()), bytes(rgb.constBits()), 'raw', 'RGB', rgb.bytesPerLine())
    red = pil.getchannel('R').point(lambda v: 255 if v>200 else 0)
    green = pil.getchannel('G').point(lambda v: 255 if v<80 else 0)
    blue = pil.getchannel('B').point(lambda v: 255 if v<80 else 0)
    return ImageChops.multiply(ImageChops.multiply(red, green), blue).getbbox()


@pytest.mark.parametrize('paper,landscape', [('A5', False), ('A4', True), ('A3', False), ('A2', True),
                                          ('A1', False), ('A0', True), ('Letter', True), ('Legal', False)])
@pytest.mark.parametrize('size', [(100, 500), (500, 100), (250, 250)])
def test_jpeg_centers_and_maximally_fits_every_paper_and_aspect(qt_app, paper, landscape, size):
    source = QImage(*size, QImage.Format.Format_RGB32)
    source.fill(QColor('red'))
    page = render_plan_page(source, paper, landscape, 50)
    left, top, right, bottom = red_bounds(page)
    assert (left+right)/2 == pytest.approx(page.width()/2, abs=1)
    assert (top+bottom)/2 == pytest.approx(page.height()/2, abs=1)
    factor = min((page.width()-20*50/25.4)/size[0], (page.height()-54*50/25.4)/size[1])
    assert right-left == pytest.approx(size[0]*factor, abs=2)
    assert bottom-top == pytest.approx(size[1]*factor, abs=2)


def test_generated_plan_fits_visible_ink_without_changing_geometry_or_calibration(editor):
    app, d = editor
    d.store(rectangle_segments(50, 60, 120, 70, '#ff0000'))
    before = deepcopy(app.session.metadata)
    from qt_ui.qt_plan_printing import clean_plan_source
    source = clean_plan_source(d.view, before)
    fitted = source.fitted_content()
    assert fitted.width() < 140 and fitted.height() < 90
    assert source.width() == 900 and source.height() == 600
    page = render_plan_page(source, 'A4', True, 150, app.get_px_per_meter())
    bounds = red_bounds(page)
    assert (bounds[0]+bounds[2])/2 == pytest.approx(page.width()/2, abs=1)
    assert (bounds[1]+bounds[3])/2 == pytest.approx(page.height()/2, abs=1)
    assert bounds[2]-bounds[0] > page.width()*.75
    dialog = PlanJpegDialog(app, source, app.get_px_per_meter(), 'metric')
    try:
        assert dialog.image._viewport == fitted._viewport
        assert dialog.orientation.currentData() is True
    finally:
        dialog.deleteLater()
    assert app.session.metadata == before


def test_loaded_background_empty_plan_and_hidden_layers_keep_correct_extents(qt_app):
    source = VectorPlanSource(QSize(900, 600), [], [], [], [])
    assert source.fitted_content() is source
    image = QImage(900, 600, QImage.Format.Format_RGB32)
    image.fill(QColor('#aabbcc'))
    layers = [dict(visible=True, drawing=dict(segments=rectangle_segments(100, 100, 100, 50, '#ff0000'),
        curves=[], labels=[], annotations=[])), dict(visible=False, drawing=dict(segments=[], curves=[], labels=[],
        annotations=[symbol('rack', cx=800)]))]
    generated = VectorPlanSource.from_layers(image.size(), layers)
    assert generated.fitted_content().width() < 120
    loaded = VectorPlanSource.from_layers(image.size(), layers, image)
    assert loaded.fitted_content() is loaded and loaded.width() == 900
    output = render_plan_page(loaded, 'A4', False, 75)
    assert not output.isNull() and output.size() == page_pixels('A4', False, 75)


@pytest.mark.parametrize('line', [dict(x1=100,y1=100,x2=300,y2=100,color='#ff0000'),
                                dict(x1=100,y1=100,x2=100,y2=300,color='#ff0000'),
                                dict(x1=0,y1=0,x2=100,y2=0,color='#ff0000')])
def test_single_axis_lines_fit_as_ink_instead_of_disappearing(qt_app, line):
    source = VectorPlanSource(QSize(900,600), [line], [], [], [])
    output = render_plan_page(source, 'A4', False, 75)
    left, top, right, bottom = red_bounds(output)
    assert (left+right)/2 == pytest.approx(output.width()/2,abs=1)
    assert (top+bottom)/2 == pytest.approx(output.height()/2,abs=1)
