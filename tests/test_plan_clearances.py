"""Independent analytic clearance checks and transient native gesture coverage."""
from copy import deepcopy
import math
import random
from unittest.mock import patch

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest

from survey.plan_clearances import ClearanceIndex, line_gaps, curve_gaps
from survey.plan_curves import project_curve, point_at
from survey.plan_drawing import rectangle_segments
from survey.plan_objects import object_vertices
from tests.test_plan_objects import obj
from tests.test_plan_annotations import choose, at
from tests.test_rectangle_design import editor, move
from tests.test_capture_adapter import window, qt_app


def wall(a, b):
    return dict(x1=a[0], y1=a[1], x2=b[0], y2=b[1], color="#000000")


def gap(item, line):
    pairs, overlap = line_gaps(item, object_vertices(item), line)
    return min(math.dist(a, b) for a, b in pairs), overlap


@pytest.mark.parametrize("kind,variant", [("desk", "rectangle"), ("desk", "round"), ("desk", "l"),
    ("symbol", "circle"), ("symbol", "square"), ("symbol", "star"), ("symbol", "x")])
def test_nearest_two_axes_are_from_footprint_not_center(kind, variant):
    item = obj(kind, variant, cx=300, cy=250, width=100, height=100, arm=30)
    walls = rectangle_segments(100, 100, 600, 400, "#000000")
    before = deepcopy((item, walls))
    index = ClearanceIndex(walls)
    quotes = index.query(item)
    assert len(quotes) == 2 and not any(q.overlap for q in quotes)
    for quote in quotes:
        if quote.direction == "left":
            assert quote.distance == pytest.approx(min(p[0] for p in object_vertices(item)) - 100)
        elif quote.direction == "above":
            assert quote.distance == pytest.approx(min(p[1] for p in object_vertices(item)) - 100)
        else:
            pytest.fail(str(quote))
    assert (item, walls) == before
    assert index.query(dict(item, stroke=19, fill=None)) is quotes
    assert index.query(dict(item, cx=310)) != quotes


@pytest.mark.parametrize("angle", [0, 5, 30, 45, 90, 155, 270])
def test_rotated_border_and_diagonal_wall_exact_projection(angle):
    item = obj(cx=300, cy=300, width=120, height=50, angle=angle)
    vertices = object_vertices(item)
    assert gap(item, wall((100, 0), (100, 800))) == pytest.approx((min(p[0] for p in vertices) - 100, False))
    # Wall x+y=100; all corners project inside the finite wall.
    distance, overlap = gap(item, wall((-500, 600), (600, -500)))
    assert not overlap
    assert distance == pytest.approx(min((x + y - 100) / math.sqrt(2) for x, y in vertices))


@pytest.mark.parametrize("variant", ["rectangle", "round", "l"])
def test_contact_zero_crossing_red_and_finite_wall_endpoints(variant):
    item = obj(variant=variant, cx=300, cy=300, width=100, height=100, arm=30)
    assert gap(item, wall((250, 0), (250, 600))) == pytest.approx((0, False))
    assert gap(item, wall((260, 0), (260, 600))) == pytest.approx((0, True))
    assert gap(item, wall((100, 100), (100, 150)))[0] > 150
    quotes = ClearanceIndex([wall((260, 0), (260, 600))]).query(item)
    assert len(quotes) == 1 and quotes[0].overlap
    # A short wall entirely inside the empty L notch is not a collision.
    if variant == "l":
        distance, overlap = gap(item, wall((310, 310), (330, 310)))
        assert distance == pytest.approx(30) and not overlap


def test_circle_arc_clearances_and_enclosed_or_tangent_structure():
    item = obj(variant="round", cx=300, cy=300, width=100, height=100)
    circle = dict(kind="circle", cx=300, cy=300, radius=200, color="#000000")
    quotes = ClearanceIndex(curves=[circle]).query(item)
    assert len(quotes) == 2 and all(q.distance == pytest.approx(150) and not q.overlap for q in quotes)
    arc = dict(kind="arc", x1=100, y1=100, x2=500, y2=100, height=100, color="#000000")
    assert min(q.distance for q in ClearanceIndex(curves=[arc]).query(item)) == pytest.approx(50)
    tangent = dict(circle, cy=50)
    assert all(not q.overlap and q.distance == pytest.approx(0) for q in ClearanceIndex(curves=[tangent]).query(item))
    assert ClearanceIndex(curves=[dict(circle, radius=30)]).query(item)[0].overlap
    square = obj(cx=300, cy=300, width=100, height=100)
    assert ClearanceIndex(curves=[dict(circle, radius=30)]).query(square)[0].overlap


def test_curve_polygon_minimum_matches_dense_independent_distance_oracle():
    rng = random.Random(61)
    for _ in range(24):
        item = obj(cx=500, cy=500, width=100, height=70, angle=rng.uniform(0, 360))
        curve = dict(kind="arc", x1=100, y1=80, x2=900, y2=130,
                     height=rng.uniform(-150, 150) or 1, color="#000000")
        pairs, collision = curve_gaps(item, object_vertices(item), curve)
        assert not collision
        # Sample curve, and compute point-to-finite-edge distance independently.
        def point_edge(p, a, b):
            dx, dy = b[0] - a[0], b[1] - a[1]
            t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
            return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)
        vertices = object_vertices(item)
        sampled = min(point_edge(point_at(curve, i / 1500), a, b) for i in range(1501)
                      for a, b in zip(vertices, vertices[1:] + vertices[:1]))
        exact = min(math.dist(a, b) for a, b in pairs)
        assert exact <= sampled + 1e-6 and sampled - exact < .01


@pytest.mark.parametrize("height", [.002, -.002, 5, -5, 1000, -1000])
def test_shallow_arc_projection_lies_on_stable_curve_and_has_normal_tangent(height):
    curve = dict(kind="arc", x1=0, y1=100, x2=100000, y2=100, height=height, color="#000000")
    for x in (25000, 50000, 75000):
        point = project_curve(curve, (x, 3000))
        assert point[0] == pytest.approx(x, abs=200)
        # Finite difference tangent must be perpendicular to the query vector.
        from survey.plan_curves import parameter_at
        t = parameter_at(curve, point)
        assert point == pytest.approx(point_at(curve, t), abs=.0002)
        a, b = point_at(curve, t - 1e-5), point_at(curve, t + 1e-5)
        residual = ((point[0] - x) * (b[0] - a[0]) + (point[1] - 3000) * (b[1] - a[1])) / math.dist(a, b)
        assert residual == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize("system", ["metric", "imperial"])
def test_clearance_overlay_placement_move_rotation_zoom_leave_and_history(editor, qt_app, system):
    app, d = editor
    app.measurement_system = system
    d.store(rectangle_segments(100, 100, 650, 400, "#334455"))
    app.session.dirty = False
    choose(app, "desk", obj(cx=350, cy=300))
    before, history = deepcopy(app.session.metadata), len(d.undo_stack)
    move(d.view, at(app, 350, 300))
    assert d.dimensions.values["kind"] == "object"
    assert len(d.dimensions.items) <= 2 and len(d.dimensions.text_items) <= 2
    assert (" ft" if system == "imperial" else " m") in d.dimensions.badge.text()
    for i in range(20):
        move(d.view, at(app, 350 + i, 300))
    assert len(d.dimensions.items) <= 2 and len(d.dimensions.text_items) <= 2
    assert app.session.metadata == before and len(d.undo_stack) == history and not app.session.dirty
    with patch.object(d, "move", wraps=d.move) as handler:
        move(d.view, at(app, 380, 300))
        assert handler.call_count == 1
    QTest.keyClick(app, Qt.Key.Key_R)
    assert d.dimensions.last_object == d.annotation.pending
    d.view.set_zoom(1.5)
    qt_app.processEvents()
    assert d.dimensions.badge.isVisible()
    from PySide6.QtWidgets import QApplication
    QApplication.sendEvent(d.view.viewport(), QEvent(QEvent.Type.Leave))
    assert not d.dimensions.badge.isVisible()
    assert all(not p.isVisible() for p in d.dimensions.items + d.dimensions.text_items)
    move(d.view, at(app, 380, 300))
    QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 380, 300))
    assert len(d.annotations()) == 1
    choose(app, "annotation_select")
    vertex = object_vertices(d.annotations()[0])[0]
    QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=at(app, *vertex))
    move(d.view, at(app, *vertex))
    assert d.dimensions.values["kind"] == "object"
    QTest.keyClick(app, Qt.Key.Key_R)
    assert d.dimensions.last_object == d.annotation.selected_items()[0]
    QTest.keyClick(app, Qt.Key.Key_M)
    move(d.view, at(app, 500, 350))
    assert d.dimensions.values["kind"] == "object"
    QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 500, 350))
    d.undo()
    assert len(d.annotations()) == 1
    d.store([])
    move(d.view, at(app, 500, 350))
    assert not d.dimensions.badge.isVisible()
