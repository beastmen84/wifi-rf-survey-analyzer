"""Viewport overlays must not be translated by QGraphicsView scrolling."""
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tests.test_rectangle_design import editor, move
from tests.test_capture_adapter import window, qt_app


@pytest.mark.parametrize("tool", ["rectangle", "annotation_select", "pending_rectangle"])
def test_design_palette_button_and_huds_stay_fixed_during_zoom_and_pan(editor, qt_app, tool):
    app, drawing = editor
    view, tools = app.floorplan_view, app.plan_tools
    tools.select_tool("rectangle" if tool == "pending_rectangle" else tool)
    view.set_zoom(2)
    qt_app.processEvents()
    if tool == "pending_rectangle":
        drawing.begin_placement(150, 100)
    drawing.show_measurement("Viewport HUD", QPointF())
    drawing.dimensions.badge.setText("Viewport dimensions")
    drawing.dimensions.position()
    drawing.dimensions.badge.show()
    tools.position_controls()
    viewport_size = view.viewport().size()
    widgets = (tools, tools.toggle_button, drawing.measurement, drawing.dimensions.badge)
    positions = [widget.pos() for widget in widgets]
    hud_corner = drawing.measurement.geometry().topRight()
    badge_right = drawing.dimensions.badge.geometry().right()

    def anchored():
        assert view.viewport().size() == viewport_size
        assert [widget.pos() for widget in widgets[:2]] == positions[:2]
        # Preview text can change width/height while panning. Its top-right
        # anchor, rather than its content-dependent left edge, must stay fixed.
        assert drawing.measurement.geometry().topRight() == hud_corner
        assert drawing.dimensions.badge.geometry().right() == badge_right
        if drawing.measurement.isVisible() and drawing.dimensions.badge.isVisible():
            assert drawing.dimensions.badge.y() == drawing.measurement.geometry().bottom() + app.spx(8)
        assert tools.isVisible() and tools.toggle_button.isVisible()

    before = view.mapToScene(view.viewport().rect().center())
    view.horizontalScrollBar().setValue(view.horizontalScrollBar().value() + 37)
    view.verticalScrollBar().setValue(view.verticalScrollBar().value() - 29)
    assert view.mapToScene(view.viewport().rect().center()) != before
    anchored()  # Already fixed synchronously, before the next event-loop tick.
    view.set_zoom(view.zoom_level * 1.25)
    qt_app.processEvents()
    anchored()
    start = view.viewport().rect().center()
    for modifiers in (Qt.KeyboardModifier.ShiftModifier, Qt.KeyboardModifier.NoModifier,
                      Qt.KeyboardModifier.ControlModifier):
        event = QWheelEvent(QPointF(start), QPointF(view.viewport().mapToGlobal(start)), QPoint(), QPoint(0, -120),
                            Qt.MouseButton.NoButton, modifiers, Qt.ScrollPhase.ScrollUpdate, False)
        QApplication.sendEvent(view.viewport(), event)
        anchored()
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    move(view, start + QPoint(45, 30), Qt.MouseButton.LeftButton)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=start + QPoint(45, 30))
    qt_app.processEvents()
    anchored()
    if tool == "pending_rectangle":
        assert drawing.pending_size == (150, 100)
    assert not app.session.dirty and not drawing.undo_stack
