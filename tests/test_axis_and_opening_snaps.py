"""Live orthogonal constraints and center/jamb intent on short opening hosts."""
import math

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from survey.plan_annotations import annotation_points, supported
from tests.test_rectangle_design import editor, move
from tests.test_plan_annotations import aperture, choose, at
from tests.test_capture_adapter import window, qt_app

SHIFT = Qt.KeyboardModifier.ShiftModifier
ALT = Qt.KeyboardModifier.AltModifier


def mouse_move(view, position, modifiers):
    event = QMouseEvent(QEvent.Type.MouseMove, QPointF(position), QPointF(view.viewport().mapToGlobal(position)),
                       Qt.MouseButton.NoButton, Qt.MouseButton.RightButton, modifiers)
    QApplication.sendEvent(view.viewport(), event)


def preview_endpoints(drawing, tool):
    if tool == "line":
        line = drawing.line.preview.line()
        return (line.x1(), line.y1(), line.x2(), line.y2())
    path = drawing.curve.preview.path()
    return (path.elementAt(0).x, path.elementAt(0).y, path.elementAt(1).x, path.elementAt(1).y)


@pytest.mark.parametrize("tool", ["line", "arc"])
@pytest.mark.parametrize("end,horizontal", [((480, 280), True), ((320, 450), False),
                                          ((130, 220), True), ((330, 70), False)])
@pytest.mark.parametrize("grid", [False, True])
@pytest.mark.parametrize("modifiers", [SHIFT, SHIFT | ALT])
def test_shift_drag_and_release_keep_the_same_axis_and_origin(editor, tool, end, horizontal, grid, modifiers):
    app, d = editor
    app.plan_tools.select_tool(tool)
    app.plan_tools.snap_button.setChecked(grid)
    start, finish = at(app, 300, 250), at(app, *end)
    QTest.mousePress(d.view.viewport(), Qt.MouseButton.RightButton, modifiers, pos=start)
    origin = QPointF(d.line.origin if tool == "line" else d.curve.origin)
    mouse_move(d.view, finish, modifiers)
    draft = preview_endpoints(d, tool)
    assert draft[:2] == (origin.x(), origin.y())
    assert draft[3 if horizontal else 2] == (origin.y() if horizontal else origin.x())
    if modifiers & ALT:
        assert not d.snap_guides
    QTest.mouseRelease(d.view.viewport(), Qt.MouseButton.RightButton, modifiers, pos=finish)
    result = d.segments()[0] if tool == "line" else d.curve.chord
    assert tuple(result[key] for key in ("x1", "y1", "x2", "y2")) == draft
    assert not app.session.rows
    if tool == "line":
        d.undo()
        assert not d.segments()
    else:
        # The perpendicular bending stage keeps its frozen chord even with Shift.
        frozen = dict(d.curve.chord)
        mouse_move(d.view, at(app, 410, 350), modifiers)
        assert d.curve.chord == frozen
        d.cancel()
        assert not d.curves()


@pytest.mark.parametrize("tool", ["line", "arc"])
def test_shift_press_release_refreshes_a_stationary_drag_preview(editor, tool):
    app, d = editor
    app.plan_tools.select_tool(tool)
    app.plan_tools.snap_button.setChecked(False)
    start, finish = at(app, 300, 250), at(app, 470, 330)
    QTest.mousePress(d.view.viewport(), Qt.MouseButton.RightButton, pos=start)
    mouse_move(d.view, finish, Qt.KeyboardModifier.NoModifier)
    original = preview_endpoints(d, tool)
    assert original[1] != original[3]
    QTest.keyPress(app, Qt.Key.Key_Shift)
    locked = preview_endpoints(d, tool)
    assert locked[1] == locked[3] and locked[2] == original[2]
    QTest.keyRelease(app, Qt.Key.Key_Shift)
    assert preview_endpoints(d, tool) == original
    QTest.mouseRelease(d.view.viewport(), Qt.MouseButton.RightButton, pos=finish)
    d.cancel()


def test_axis_constraint_keeps_on_axis_magnets_and_ignores_off_axis_corners(editor):
    app, d = editor
    d.store([dict(x1=493.3, y1=250, x2=493.3, y2=450, color="#334455"),
             dict(x1=500, y1=257, x2=700, y2=257, color="#334455")])
    d.axis_lock = True
    result = d.snap_endpoint(QPointF(500, 265), QPointF(300, 250))
    assert (result.x, result.y) == (493.3, 250) and result.guides[0].kind == "corner"
    result = d.snap_endpoint(QPointF(500, 265), QPointF(300, 250), bypass=True)
    assert (result.x, result.y) == (500, 250) and not result.guides


def test_shift_preserves_circle_radius_and_exact_rotated_line_placement(editor):
    app, d = editor
    app.plan_tools.select_tool("circle")
    d.curve.origin = QPointF(300, 250)
    d.axis_lock = True
    circle = d.curve.drag_geometry(QPointF(at(app, 360, 330)), bypass=True)
    point = d.view.mapToScene(at(app, 360, 330))
    assert circle["radius"] == pytest.approx(math.hypot(point.x() - 300, point.y() - 250))
    app.plan_tools.select_tool("line")
    d.line.angle = 35
    d.line.begin_placement(150, QPointF(300, 250))
    point = QPointF(400, 300)
    before = d.line.geometry(point, bypass=True)
    d.axis_lock = True
    after = d.line.geometry(point, bypass=True)
    assert after == before and after.length() == pytest.approx(150)


@pytest.mark.parametrize("kind", ["door", "window"])
@pytest.mark.parametrize("angle", [0, 90, 35])
@pytest.mark.parametrize("offset", [0, 2, 4])
def test_short_host_offers_center_and_jamb_snaps_without_changing_opening_width(editor, kind, angle, offset):
    app, d = editor
    ux, uy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    center = (450, 300)
    a, b = [(center[0] + sign * 55 * ux, center[1] + sign * 55 * uy) for sign in (-1, 1)]
    wall = dict(x1=a[0], y1=a[1], x2=b[0], y2=b[1], color="#334455")
    d.store([wall])
    choose(app, kind, aperture(kind, x1=200, x2=300))
    app.plan_tools.snap_button.setChecked(False)
    move(d.view, at(app, center[0] + offset * ux, center[1] + offset * uy))
    item = d.annotation.pending
    assert item is not None and supported(item, [wall])
    p, q = annotation_points(item)
    assert [(p[i] + q[i]) / 2 for i in (0, 1)] == pytest.approx(center)
    assert math.dist(p, q) == pytest.approx(100)
    assert d.snap_guides[0].kind == "midpoint"
    # Explicitly approach a jamb: it must still anchor to the real wall corner.
    point = (a[0] + 2 * ux, a[1] + 2 * uy)
    item = d.annotation.hosted(point, 100, aperture(kind, x1=200, x2=300))
    assert item and min(math.dist(a, p) for p in annotation_points(item)) < 1e-5
    assert d.snap_guides[0].kind == "corner"
    # Alt releases both magnets while retaining the supporting wall and width.
    d.snap_bypass = True
    point = (center[0] + 2 * ux, center[1] + 2 * uy)
    item = d.annotation.hosted(point, 100, aperture(kind, x1=200, x2=300))
    p, q = annotation_points(item)
    assert [(p[i] + q[i]) / 2 for i in (0, 1)] == pytest.approx(point)
    assert not d.snap_guides and d.segments() == [wall]
