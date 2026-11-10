"""Panned wall hatches must match a fresh vector paint at the same camera pose."""
from copy import deepcopy

import numpy as np
import pytest
from PySide6.QtCore import QPoint, Qt, QSize
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView

from qt_ui.qt_clean_plan import VectorPlanSource
from survey.plan_geometry import rotate_degrees, translate_segments
from survey.wall_rendering import MaterialPath, wall_item
from tests.test_capture_adapter import window, qt_app
from tests.test_rectangle_design import editor
from tests.test_floorplan_pan import hand_drag
from tests.test_wall_thickness import rectangle
from tests.test_plan_annotations import aperture


def pixels(image):
    image = image.convertToFormat(QImage.Format.Format_RGB32)
    return np.frombuffer(image.constBits(),np.uint8).reshape(image.height(),image.bytesPerLine())[:, :image.width()*4].copy()


def material_view(pattern='cross', geometry='rooms'):
    lines = [dict(line,wall=dict(width=20,side=-1,material='reinforced_concrete',pattern=pattern))
             for x,y,w,h in ((100,100,1000,700),(1400,200,700,900),(700,1100,1500,700))
             for line in rectangle(x,y,w,h)]
    curves = []
    if geometry == 'curve':
        curves = [dict(kind='circle',cx=600,cy=500,radius=300,phase=0,color='#263238',
                       wall=dict(width=20,side=-1,material='brick',pattern=pattern,priority=True))]
    center = (1000,800)
    objects = [aperture(variant='frame',x1=1100,y1=350,x2=1100,y2=450)]
    if geometry == 'rotated':
        from survey.plan_annotations import transform_annotations
        lines = translate_segments(rotate_degrees(lines,35,(1000,900)),600,600)
        objects = transform_annotations(objects,35,(1000,900),600,600)
        center = (1657,1418)
    source = VectorPlanSource(QSize(4000,3500),lines,curves,[],objects)
    scene = QGraphicsScene()
    scene.setSceneRect(0,0,4000,3500)
    materials = []
    for path,pen,brush in source._commands:
        item = wall_item(path,pen,brush)
        scene.addItem(item)
        if isinstance(path,MaterialPath):
            materials.append(item)
    view = QGraphicsView(scene)
    view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    view.setBackgroundBrush(QColor('white'))
    view.setRenderHints(QPainter.RenderHint.Antialiasing|QPainter.RenderHint.SmoothPixmapTransform)
    view.resize(900,650)
    return view, scene, materials, center


def fresh_difference(view, materials, app):
    before = view.viewport().grab().toImage()
    pose = view.viewportTransform()
    modes = [item.cacheMode() for item in materials]
    for item in materials:
        item.setCacheMode(QGraphicsItem.CacheMode.NoCache)
    view.viewport().update()
    app.processEvents()
    after = view.viewport().grab().toImage()
    assert view.viewportTransform() == pose
    difference = int(np.count_nonzero(pixels(before) != pixels(after)))
    for item,mode in zip(materials,modes):
        item.setCacheMode(mode)
    return difference, before, after


@pytest.mark.parametrize('geometry', ['rooms','rotated','curve'])
@pytest.mark.parametrize('pattern', ['cross','dots','brick'])
@pytest.mark.parametrize('zoom', [1,1.25,2.75])
def test_pan_and_reverse_pan_match_fresh_vector_pixels(qt_app, geometry, pattern, zoom):
    view, scene, materials, center = material_view(pattern,geometry)
    try:
        view.show()
        view.scale(zoom,zoom)
        view.centerOn(*center)
        qt_app.processEvents()
        view.viewport().grab()  # Warm any cache before revealing new item portions.
        for sequence in (((111,-83),(-57,139),(243,175)),((-333,-241),(47,33),(89,-67))):
            for dx,dy in sequence:
                view.horizontalScrollBar().setValue(view.horizontalScrollBar().value()+dx)
                view.verticalScrollBar().setValue(view.verticalScrollBar().value()+dy)
                qt_app.processEvents()
                view.viewport().grab()
            difference, _before, _after = fresh_difference(view,materials,qt_app)
            assert difference == 0, (geometry,pattern,zoom,difference)
    finally:
        view.close()
        view.deleteLater()
        qt_app.processEvents()


def test_hand_pan_preserves_the_editor_model_history_and_material_alignment(editor, qt_app):
    owner,drawing = editor
    lines = [dict(line,wall=dict(width=12,side=-1,material='reinforced_concrete')) for line in rectangle()]
    drawing.store(lines)
    owner.plan_tools.select_tool(None)
    drawing.view.set_zoom(2.75)
    drawing.view.centerOn(300,300)
    qt_app.processEvents()
    before, count = deepcopy(drawing.snapshot()), len(drawing.undo_stack)
    start = QPoint(drawing.view.viewport().width()*3//4,drawing.view.viewport().height()//3)
    for delta in (QPoint(73,-51),QPoint(-131,87),QPoint(45,31)):
        hand_drag(drawing.view,start,delta)
        qt_app.processEvents()
        difference, _before, _after = fresh_difference(drawing.view,drawing.wall_items,qt_app)
        assert difference == 0
    assert drawing.snapshot() == before and len(drawing.undo_stack) == count
