"""Every actual vertex may anchor a rigid grid snap, regardless of rotation/order."""
import math

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest

from survey.plan_drawing import rectangle_segments
from survey.plan_geometry import rotate_degrees, segment_bounds, translate_segments
from survey.plan_snapping import PlanSnapper
from tests.test_rectangle_design import editor, move
from tests.test_capture_adapter import window, qt_app

BOUNDS = (0, 0, 900, 600)


def vertices(lines):
    return {(line[x], line[y]) for line in lines for x, y in (("x1", "y1"), ("x2", "y2"))}


def pose(vertex, angle=45, target=(400.8, 299.4), dimensions=(117.3, 63.2)):
    source = rotate_degrees(rectangle_segments(200, 200, *dimensions, "#123456"), angle)
    chosen = source[vertex]
    return translate_segments(source, target[0] - chosen["x1"], target[1] - chosen["y1"])


@pytest.mark.parametrize("angle", [0, 35, 45, 90, 135, 180, 225, 315])
@pytest.mark.parametrize("vertex", range(4))
@pytest.mark.parametrize("reverse", [False, True])
def test_every_rectangle_vertex_can_snap_to_the_grid(angle, vertex, reverse):
    source = pose(vertex, angle)
    if reverse:
        source = [dict(line, x1=line["x2"], y1=line["y2"], x2=line["x1"], y2=line["y1"])
                  for line in reversed(source)]
    result = PlanSnapper().snap_geometry(source, BOUNDS, 10, grid=50)
    assert (result.x, result.y) == pytest.approx((-.8, .6), abs=1e-9)
    assert result.guides[0].point == pytest.approx((400, 300))
    snapped = translate_segments(source, result.x, result.y)
    assert min(math.dist(point, (400, 300)) for point in vertices(snapped)) < 1e-9
    for original, moved in zip(source, snapped):
        assert math.dist((original["x1"], original["y1"]), (original["x2"], original["y2"])) == pytest.approx(
            math.dist((moved["x1"], moved["y1"]), (moved["x2"], moved["y2"])))


@pytest.mark.parametrize("endpoint", [0, 1])
def test_either_rotated_line_endpoint_can_anchor_grid(endpoint):
    source = rotate_degrees([dict(x1=200, y1=200, x2=317.3, y2=200, color="#123456")], 35)
    x, y = (source[0]["x1"], source[0]["y1"]) if endpoint == 0 else (source[0]["x2"], source[0]["y2"])
    source = translate_segments(source, 400.8 - x, 299.4 - y)
    result = PlanSnapper().snap_geometry(source, BOUNDS, 10, grid=50)
    assert (result.x, result.y) == pytest.approx((-.8, .6))
    assert result.guides[0].point == pytest.approx((400, 300))


def test_axis_aligned_group_uses_real_vertices_not_empty_box_corner():
    points = [(98.6, 83.2), (216.2, 83.2), (216.2, 147.1)]
    result = PlanSnapper().snap(98.6, 83.2, 117.6, 63.9, BOUNDS, 10, 50, source_vertices=points)
    assert (result.x, result.y) == pytest.approx((82.4, 86.1))
    assert result.guides[0].point == (200, 150)
    assert any(math.dist((x + result.x - 98.6, y + result.y - 83.2), (200, 150)) < 1e-9 for x, y in points)


@pytest.mark.parametrize("vertex", range(4))
def test_real_corner_keeps_priority_over_nearer_grid(vertex):
    source = pose(vertex)
    target = dict(x1=402, y1=301, x2=442, y2=301, color="#654321")
    result = PlanSnapper([target]).snap_geometry(source, BOUNDS, 10, grid=50)
    assert result.guides[0].kind == "corner"
    assert result.guides[0].point == (402, 301)


@pytest.mark.parametrize("location", [(0, 0), (1, 1), (770, 0), (0, 470), (770, 470)])
def test_any_vertex_grid_snap_respects_sheet_limits(location):
    source = pose(0)
    left, top, _, _ = segment_bounds(source)
    source = translate_segments(source, location[0] - left, location[1] - top)
    result = PlanSnapper().snap_geometry(source, BOUNDS, 10, grid=50)
    snapped = translate_segments(source, result.x, result.y)
    left, top, right, bottom = segment_bounds(snapped)
    assert left >= -1e-9 and top >= -1e-9 and right <= 900 + 1e-9 and bottom <= 600 + 1e-9
    assert result.guides
    assert min(math.dist(point, result.guides[0].point) for point in vertices(snapped)) < 1e-9


def test_no_grid_point_that_can_fit_means_no_false_grid_marker():
    source = rectangle_segments(.1, .1, 100, 100, "#123456")
    result = PlanSnapper().snap_geometry(source, (.1, .1, 100.1, 100.1), 10, grid=50)
    assert result.x == result.y == 0 and not result.guides


@pytest.mark.parametrize("vertex", range(4))
def test_dragging_rotated_selection_snaps_each_corner_and_keeps_model_provisional(editor, vertex):
    app, drawing = editor
    step = app.floorplan_view.grid_spacing_pixels()
    target = (8 * step, 6 * step)
    source = pose(vertex, target=(target[0] + .8, target[1] - .6), dimensions=(117.3, 117.3))
    drawing.store(source)
    original = drawing.segments()
    app.plan_tools.select_tool("select")
    app.plan_tools.snap_button.setChecked(True)
    drawing.selection.set_selected(range(4))
    drawing.selection.begin_move()
    guide = drawing.snap_guides[0]
    assert guide.kind == "grid" and guide.point == pytest.approx(target)
    assert min(math.dist(point, guide.point) for point in vertices(drawing.selection.move_preview)) < 1e-7
    assert drawing.snap_items and drawing.segments() == original
    position = drawing.selection.last_pointer.toPoint()
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=position)
    assert min(math.dist(point, target) for point in vertices(drawing.segments())) < 1e-7
    drawing.undo()
    assert drawing.segments() == original


@pytest.mark.parametrize("vertex", range(4))
def test_rotated_numeric_preview_can_snap_from_every_corner(editor, vertex):
    app, drawing = editor
    source = pose(vertex)
    left, top, _, _ = segment_bounds(source)
    app.plan_tools.snap_button.setChecked(True)
    drawing.pending_size = (117.3, 63.2)
    drawing.pending_angle = 45
    position = app.floorplan_view.mapFromScene(QPointF(left, top))
    rect = drawing.pointer_rect(app.floorplan_view.mapToScene(position))
    drawing.show_preview(rect, position)
    geometry = drawing.rectangle_geometry(rect)
    guide = drawing.snap_guides[0]
    assert guide.kind == "grid" and guide.point == pytest.approx((400, 300))
    assert min(math.dist(point, guide.point) for point in vertices(geometry)) < 1e-7
    assert drawing.pending_size == (117.3, 63.2) and drawing.pending_angle == 45
    assert drawing.snap_items and not app.session.dirty


def test_rotated_text_preview_marks_the_actual_snapped_corner(editor):
    from survey.plan_label_rendering import build_label
    from survey.plan_labels import label_geometry
    from tests.test_plan_text_fill import style
    app, drawing = editor
    app.plan_tools.select_tool("text")
    app.plan_tools.snap_button.setChecked(True)
    label = build_label(style(text="Room Z", outline_width=0))
    label.update(x=300, y=220, angle=45)
    corner = label_geometry(label)[2]
    label["x"] += 400.8 - corner["x1"]
    label["y"] += 299.4 - corner["y1"]
    drawing.text.begin_placement(label, app.floorplan_view.mapFromScene(QPointF(label["x"], label["y"])))
    guide = drawing.snap_guides[0]
    assert guide.kind == "grid" and guide.point == pytest.approx((400, 300))
    assert min(math.dist(point, guide.point) for point in vertices(label_geometry(drawing.text.pending))) < 1e-7
    assert drawing.snap_items and not drawing.labels() and not app.session.dirty
