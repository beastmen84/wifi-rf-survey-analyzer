"""Physical closures may fade the grid without inventing editable reference joins."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath

from survey.curved_regions import closed_drawing_regions
from survey.plan_drawing import rectangle_segments
from survey.wall_geometry import enclosed_floor, ranked_wall_bodies
from tests.test_capture_adapter import window, qt_app
from tests.test_rectangle_design import editor


def walls(gap=5):
    lines = [dict(s,wall=dict(width=20,side=0,reference='axis'))
             for s in rectangle_segments(100,100,200,200,'#263238')]
    lines[2]['x2'] += gap
    return lines


def bodies(lines,curves=()):
    return [p for _rank,p in ranked_wall_bodies(lines,curves)]


@pytest.mark.parametrize('gap,closed', [(0,True),(5,True),(10.00001,False),(11,False)])
def test_only_real_physical_closures_fill_the_floor(gap,closed):
    lines = walls(gap)
    before = deepcopy(lines)
    floor = enclosed_floor(bodies(lines))
    assert floor.contains(QPointF(200,200)) == closed
    assert not floor.contains(QPointF(50,200))
    assert lines == before
    if gap:
        assert not closed_drawing_regions(lines).faces


def test_open_wall_chain_does_not_fill_its_bounding_box():
    assert enclosed_floor(bodies(walls()[:3])).isEmpty()


def test_curved_closure_through_thickness_preserves_open_reference_graph():
    lines = walls()[:2]+walls()[3:]
    curve = dict(kind='arc',x1=105,y1=300,x2=295,y2=300,height=95,color='#263238',
                 wall=dict(width=20,side=0,reference='axis'))
    assert not closed_drawing_regions(lines,[curve]).faces
    floor = enclosed_floor(bodies(lines,[curve]))
    assert floor.contains(QPointF(200,200)) and floor.contains(QPointF(200,350))
    assert not floor.contains(QPointF(200,450))


def test_nested_and_disconnected_physical_enclosures_keep_all_interiors():
    lines = walls(0)
    for x,y,width,height in ((150,150,50,50),(400,100,100,100)):
        lines.extend(dict(s,wall=dict(width=10,side=-1)) for s in rectangle_segments(x,y,width,height,'#445566'))
    floor = enclosed_floor(bodies(lines))
    assert all(floor.contains(QPointF(*p)) for p in ((125,125),(175,175),(450,150)))
    assert not floor.contains(QPointF(350,150))


def test_mask_reuses_equal_geometry_and_invalidates_for_changed_walls(editor):
    _owner,drawing = editor
    view = drawing.view
    group = bodies(walls())
    with patch('survey.wall_geometry.enclosed_floor',wraps=enclosed_floor) as build:
        view.set_grid_regions((),wall_groups=(group,))
        assert build.call_count == 1
        view.set_grid_regions((),wall_groups=([QPainterPath(p) for p in group],))
        assert build.call_count == 1
        view.set_grid_regions((),wall_groups=(bodies(walls(11)),))
        assert build.call_count == 2 and view.grid_interior_path.isEmpty()


def test_physical_grid_fade_updates_on_delete_undo_redo_without_editing_joins(editor):
    _owner,drawing = editor
    drawing.store(walls())
    before = deepcopy(drawing.snapshot())
    assert not drawing.regions.faces
    assert drawing.view.grid_interior_path.contains(QPointF(200,200))
    drawing.redraw()
    assert drawing.snapshot() == before
    assert drawing.apply_edit(drawing.segments()[:3])
    assert drawing.view.grid_interior_path.isEmpty()
    drawing.undo()
    assert drawing.view.grid_interior_path.contains(QPointF(200,200))
    drawing.redo()
    assert drawing.view.grid_interior_path.isEmpty()


def test_physical_closure_never_bridges_independent_or_hidden_layers(editor):
    owner,drawing = editor
    lines = walls()
    drawing.store(lines[:3])
    owner.layers_panel.add()
    drawing.store(lines[3:])
    assert drawing.view.grid_interior_path.isEmpty()
    drawing.store(lines)
    assert drawing.view.grid_interior_path.contains(QPointF(200,200))
    document = deepcopy(drawing.layer_document())
    document['layers'][1]['visible'] = False
    drawing.change_layers(document)
    assert drawing.view.grid_interior_path.isEmpty()


def test_overlapping_reference_and_physical_masks_preserve_all_interiors(editor):
    from tests.test_plan_regions import scene_image
    _owner,drawing = editor
    lines = walls(0)
    lines.extend(dict(s,wall=dict(width=10,side=-1))
                 for s in rectangle_segments(150,150,50,50,'#445566'))
    group = bodies(lines)
    physical = enclosed_floor(group)
    faces = (((100,100),(300,100),(300,300),(100,300)),
             ((150,150),(200,150),(200,200),(150,200)),
             ((250,100),(450,100),(450,250),(250,250)))
    drawing.view.set_grid_regions(faces)
    reference = QPainterPath(drawing.view.grid_interior_path)
    drawing.view.set_grid_regions(faces,wall_groups=(group,group))
    mask = drawing.view.grid_interior_path
    for x in range(50,501,10):
        for y in range(50,351,10):
            p = QPointF(x+.25,y+.25)
            assert mask.contains(p) == (reference.contains(p) or physical.contains(p))
    image = scene_image(drawing.view)
    inside = 255-image.pixelColor(150,175).red()
    outside = 255-image.pixelColor(150,75).red()
    assert 0 < inside < outside*.5


def test_limited_reference_topology_does_not_enable_physical_fallback(editor):
    from survey.plan_regions import PlanRegions
    _owner,drawing = editor
    drawing.store(walls())
    assert not drawing.view.grid_interior_path.isEmpty()
    with patch('qt_ui.qt_rectangle_design.closed_drawing_regions',return_value=PlanRegions(limited=True)):
        drawing.redraw()
        assert drawing.view.grid_interior_path.isEmpty()
    drawing.redraw()
    assert drawing.view.grid_interior_path.contains(QPointF(200,200))
