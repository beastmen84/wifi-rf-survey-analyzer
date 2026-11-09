"""Physical-depth openings and jamb-to-host dimensions, without moving hosts."""
from copy import deepcopy
import math

import pytest
from PIL import Image
from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtTest import QTest

from survey.plan_annotations import (annotation_points, aperture_host_span, place_aperture,
                                     supported, transform_annotations)
from survey.plan_annotation_rendering import annotation_parts, annotation_path
from survey.plan_geometry import rotate_degrees
from survey.plan_drawing import render_plan_drawing
from qt_ui.qt_clean_plan import VectorPlanSource
from tests.test_plan_annotations import aperture, at, choose
from tests.test_rectangle_design import editor, move
from tests.test_capture_adapter import window, qt_app


def wall(side=1):
    return dict(x1=100, y1=300, x2=700, y2=300, color='#475569', wall=dict(width=40, side=side))


@pytest.mark.parametrize('kind,variant', [('door','frame'), ('door','sliding'), ('door','single'),
                                         ('door','double'), ('window','single')])
@pytest.mark.parametrize('side', [-1, 0, 1])
@pytest.mark.parametrize('angle', [0, 35, 90])
def test_frames_and_leaves_follow_full_physical_depth(kind, variant, side, angle):
    host = rotate_degrees([wall(side)], angle, (400, 400))
    item = transform_annotations([aperture(kind, variant=variant, x1=250, y1=300, x2=350, y2=300)],
                                 angle, (400, 400))[0]
    before = deepcopy(item)
    low, high = (-20,20) if side == 0 else (0,40) if side == 1 else (-40,0)
    center = (low+high)/2
    a,b = annotation_points(item)
    ux,uy = (b[0]-a[0])/100, (b[1]-a[1])/100
    def point(x,y):
        return QPointF(a[0]+ux*x-uy*y, a[1]+uy*x+ux*y)
    parts = annotation_parts(item, host)
    assert parts[0][0].contains(point(1, low+.5))
    assert parts[0][0].contains(point(1, high-.5))
    if variant in ('frame','sliding') or kind == 'window':
        offsets = [(p.x()-a[0])*-uy+(p.y()-a[1])*ux
                   for poly in parts[0][0].toSubpathPolygons() for p in poly]
        assert min(offsets) == pytest.approx(low, abs=1e-5)
        assert max(offsets) == pytest.approx(high, abs=1e-5)
    else:
        first = parts[1][0].elementAt(0)
        assert (first.x-a[0])*-uy+(first.y-a[1])*ux == pytest.approx(center)
    assert item == before and supported(item, host)


def test_opposite_faces_of_shared_wall_render_identical_frames():
    lines = [wall(), dict(wall(), x1=700, y1=340, x2=100, y2=340)]
    first = aperture(variant='frame', x1=250, y1=300, x2=350, y2=300)
    other = dict(first, x1=350, y1=340, x2=250, y2=340)
    a,b = annotation_path(first, lines), annotation_path(other, lines)
    assert a.boundingRect().center().y() == pytest.approx(320)
    assert a.subtracted(b).isEmpty() and b.subtracted(a).isEmpty()


@pytest.mark.parametrize('kind', ['door', 'window'])
def test_editor_accepts_wall_body_and_centers_preview_and_committed_opening(editor, kind):
    owner,drawing = editor
    lines = [wall()]
    drawing.store(lines)
    choose(owner, kind, aperture(kind, variant='frame'))
    move(drawing.view, at(owner, 400, 320))
    pending = drawing.annotation.pending
    assert pending is not None and supported(pending, lines)
    bounds = drawing.annotation.preview[0].path().boundingRect()
    assert (bounds.top(), bounds.bottom(), bounds.center().y()) == pytest.approx((300,340,320))
    assert drawing.dimensions.values['kind'] == 'aperture'
    QTest.mouseClick(drawing.view.viewport(), Qt.MouseButton.RightButton, pos=at(owner,400,320))
    assert len(drawing.annotations()) == 1
    assert drawing.annotation.items[0].path().boundingRect() == bounds
    assert drawing.segments() == lines


@pytest.mark.parametrize('kind', ['door','window'])
def test_vertical_twenty_centimeter_clearance_is_measured_at_opening_edges(editor, kind):
    owner,drawing = editor
    line = dict(wall(), x1=300, y1=100, x2=300, y2=550)
    drawing.store([line])
    choose(owner, kind, aperture(kind, variant='frame', x1=250, x2=290))
    QTest.keyPress(owner, Qt.Key.Key_Alt)
    try:
        move(drawing.view, at(owner,280,130))
        values = drawing.dimensions.values
        item = drawing.annotation.pending
        assert item and values and values['before_m'] == pytest.approx(.2, abs=.02)
        assert values['before'] + values['after'] + 40 == pytest.approx(450)
        assert owner.tr('segment_before') not in drawing.dimensions.badge.text()
        assert owner.tr('segment_after') not in drawing.dimensions.badge.text()
        assert drawing.dimensions.badge.text().count('<br>') == 2
        # The two dimension strokes stop at different jambs, leaving the opening unmeasured.
        for graphic, expected in zip(drawing.dimensions.items, (values['before'], values['after'])):
            path = graphic.path()
            assert math.hypot(path.elementAt(1).x-path.elementAt(0).x,
                              path.elementAt(1).y-path.elementAt(0).y) == pytest.approx(expected)
        move(drawing.view, at(owner,285,130))
        assert drawing.dimensions.values['before_m'] == values['before_m']
    finally:
        QTest.keyRelease(owner, Qt.Key.Key_Alt)


def test_fragmented_host_span_joins_only_contiguous_support():
    lines = [dict(wall(), x2=300), dict(wall(), x1=300, x2=500), dict(wall(), x1=550)]
    item = aperture(variant='frame', x1=280, y1=300, x2=330, y2=300)
    _index,a,b = aperture_host_span(item, lines)
    assert a == (100,300) and b == (500,300)
    assert place_aperture((525,320), 80, lines, 10, item) is None


def test_quotes_keep_the_containing_segment_ends_at_a_room_junction():
    lines = [dict(wall(), x2=300), dict(wall(), x1=300),
             dict(wall(), x1=300, x2=300, y1=300, y2=500)]
    item = aperture(variant='frame', x1=310, y1=300, x2=350, y2=300)
    _index,a,b = aperture_host_span(item, lines)
    assert a == (300,300) and b == (700,300)


def test_frame_depth_ignores_a_different_wall_touching_only_at_its_endpoint():
    lines = [dict(wall(), x2=300, wall=dict(width=80,side=1)),
             dict(wall(), x1=300, wall=dict(width=20,side=1))]
    item = aperture(variant='frame', x1=300, y1=300, x2=350, y2=300)
    assert annotation_path(item, lines).boundingRect().height() == pytest.approx(20)


def test_vector_and_raster_exports_show_jambs_through_shared_wall_depth(qt_app):
    lines = [wall(), dict(wall(), x1=700, y1=340, x2=100, y2=340)]
    item = aperture(variant='frame', x1=250, y1=300, x2=350, y2=300)
    source = VectorPlanSource(QSize(1000,700), lines, [], [], [item])
    assert source._commands[-1][0] == annotation_path(item, lines)
    output = render_plan_drawing(Image.new('RGB',(1000,700),'white'), lines, annotations=[item])
    assert output.getpixel((250,320)) != (255,255,255)
    assert output.getpixel((300,320)) == (255,255,255)


def test_existing_opening_adapts_to_wall_depth_without_rewriting_its_coordinates(editor, tmp_path):
    owner,drawing = editor
    item = aperture(variant='frame', x1=250, y1=300, x2=350, y2=300)
    drawing.store([wall()], annotations=[item])
    before, history = deepcopy(drawing.snapshot()), len(drawing.undo_stack)
    wider = dict(wall(), wall=dict(width=60, side=1))
    assert drawing.apply_edit([wider])
    assert drawing.annotation.items[0].path().boundingRect().height() == pytest.approx(60)
    assert drawing.annotations() == [item] and len(drawing.undo_stack) == history+1
    assert drawing.undo() and drawing.snapshot() == before
    assert drawing.redo()
    owner.session.csv_file = str(tmp_path/'thick-openings.csv')
    assert owner.save_survey() and owner.open_survey(owner.session.csv_file)
    assert drawing.annotations() == [item]
    assert drawing.annotation.items[0].path().boundingRect().height() == pytest.approx(60)
