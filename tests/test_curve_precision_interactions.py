"""Precision and cursor-following regressions with the visible grid enabled."""
from copy import deepcopy
import math
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog

from qt_ui.qt_curve_design import CurveSizeDialog
from survey.plan_drawing import rectangle_segments
from survey.plan_curves import project_curve, arc_height_through_point, point_at, transform_curves
from survey.plan_geometry import rotate_degrees
from tests.test_capture_adapter import window, qt_app
from tests.test_rectangle_design import editor, move, drag
from tests.test_plan_curve_ui import at, click


@pytest.mark.parametrize("kind,dimensions", [("circle", (70,)), ("arc", (160, 45))])
def test_numeric_preview_follows_slow_cursor_motion_with_grid_enabled(editor, kind, dimensions):
    app, d = editor
    app.plan_tools.select_tool(kind)
    app.plan_tools.snap_button.setChecked(True)
    dialog = Mock()
    dialog.exec.return_value = QDialog.DialogCode.Accepted
    dialog.dimensions.return_value = dimensions
    with patch("qt_ui.qt_curve_design.CurveSizeDialog", return_value=dialog):
        click(app, 300, 250)
    initial = deepcopy(d.curve.pending)
    state = deepcopy(d.snapshot())
    first, last = at(app, 300, 250), at(app, 450, 250)
    for x in range(first.x() + 1, last.x() + 1):
        move(d.view, QPoint(x, first.y()))
    slow = deepcopy(d.curve.pending)
    key = "cx" if kind == "circle" else "x1"
    assert slow[key] > initial[key] + 100
    assert d.snapshot() == state  # Following the cursor is still provisional.
    d.curve.begin_placement(kind, dimensions, QPointF(300, 250))
    move(d.view, last)
    assert d.curve.pending == slow  # Same final pointer, independent of events.
    click(app, 450, 250)
    assert d.curves() == [slow]


@pytest.mark.parametrize("kind", ["circle", "arc"])
def test_radius_and_chord_size_are_continuous_even_with_grid_enabled(editor, kind):
    app, d = editor
    app.plan_tools.select_tool(kind)
    app.plan_tools.snap_button.setChecked(True)
    start, end = at(app, 300, 250), at(app, 373, 287)
    QTest.mousePress(d.view.viewport(), Qt.MouseButton.RightButton, pos=start)
    origin = QPointF(d.curve.origin)
    move(d.view, end, Qt.MouseButton.RightButton)
    raw = d.view.mapToScene(end)
    if kind == "circle":
        assert d.curve.current["radius"] == pytest.approx(math.hypot(raw.x() - origin.x(), raw.y() - origin.y()))
    QTest.mouseRelease(d.view.viewport(), Qt.MouseButton.RightButton, pos=end)
    if kind == "arc":
        assert (d.curve.chord["x2"], d.curve.chord["y2"]) == pytest.approx((raw.x(), raw.y()))


def test_sagitta_pull_is_continuous_instead_of_grid_square_steps(editor):
    app, d = editor
    app.plan_tools.select_tool("arc")
    app.plan_tools.snap_button.setChecked(True)
    drag(d.view, at(app, 200, 250), at(app, 400, 250))
    target = at(app, 300, 287)
    move(d.view, target)
    assert d.curve.current["height"] == pytest.approx(37, abs=1)


@pytest.mark.parametrize("angle", [0, 35])
def test_pull_snaps_arc_itself_through_the_rectangle_corner_without_moving_chord(editor, angle):
    app, d = editor
    lines = rotate_degrees(rectangle_segments(150, 150, 220, 160, "#123456"), angle)
    d.store(lines)
    a = QPointF(lines[0]["x1"], lines[0]["y1"])
    target = (lines[0]["x2"], lines[0]["y2"])
    b = QPointF(lines[1]["x2"], lines[1]["y2"])
    app.plan_tools.select_tool("arc")
    app.plan_tools.snap_button.setChecked(True)
    drag(d.view, d.view.mapFromScene(a), d.view.mapFromScene(b))
    chord = deepcopy(d.curve.chord)
    cursor = d.view.mapFromScene(QPointF(*target)) + QPoint(2, 1)
    move(d.view, cursor)
    assert math.dist(project_curve(d.curve.current, target), target) < 1e-7
    assert any(guide.kind == "corner" and guide.point == target for guide in d.snap_guides)
    assert d.snap_items and d.curve.chord == chord
    QTest.keyPress(d.view, Qt.Key.Key_Alt)
    assert not d.snap_guides
    QTest.keyRelease(d.view, Qt.Key.Key_Alt)
    assert math.dist(project_curve(d.curve.current, target), target) < 1e-7
    with patch.object(app, "start_wifi_scan") as scan:
        QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=cursor)
        scan.assert_not_called()
    assert any(math.dist((curve[x], curve[y]), target) < 1e-7 for curve in d.curves()
               for x, y in (("x1", "y1"), ("x2", "y2")))


@pytest.mark.parametrize("system", ["metric", "imperial"])
@pytest.mark.parametrize("kind", ["circle", "arc"])
def test_numeric_curve_buttons_adjust_by_hundredths(editor, system, kind):
    app, d = editor
    app.measurement_system = system
    dialog = CurveSizeDialog(app, kind, d.view.scene.sceneRect(), app.get_px_per_meter())
    for spin in dialog.spins:
        spin.setValue(2)
        spin.stepUp()
        assert spin.value() == pytest.approx(2.01)
    dialog.deleteLater()


@pytest.mark.parametrize("height", [30, -30, 200, -200])
@pytest.mark.parametrize("fraction", [.2, .75])
@pytest.mark.parametrize("angle", [0, 35])
def test_third_point_recovers_the_same_minor_or_major_arc(height, fraction, angle):
    original = dict(kind="arc", x1=200, y1=250, x2=400, y2=250, height=height, color="#123456")
    curve = transform_curves([original], angle, (300, 250))[0]
    target = point_at(curve, fraction)
    assert arc_height_through_point(curve, target) == pytest.approx(height, abs=1e-8)


def test_fixed_endpoints_and_collinear_points_cannot_force_a_bend():
    chord = dict(x1=100, y1=100, x2=300, y2=100)
    for target in ((100, 100), (200, 100), (300, 100), (400, 100)):
        assert arc_height_through_point(chord, target) is None
