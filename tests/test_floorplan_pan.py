"""A fitted sheet must remain movable so floating tools cannot block its corners."""
from copy import deepcopy

import pytest
from PIL import Image
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtTest import QTest

from qt_ui.qt_floorplan import FloorplanView
from survey.plan_drawing import drawing_segments
from tests.test_rectangle_design import editor, move, drag
from tests.test_capture_adapter import window, qt_app


def hand_drag(view, start, delta):
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    move(view, start + delta, Qt.MouseButton.LeftButton)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=start + delta)


@pytest.mark.parametrize("tool", ["rectangle", "line", "annotation_select", "pending_rectangle"])
def test_fitted_design_can_reveal_and_draw_in_corner_behind_palette(editor, qt_app, tool):
    app, drawing = editor
    view, tools = app.floorplan_view, app.plan_tools
    tools.select_tool("rectangle" if tool == "pending_rectangle" else tool)
    view.fit_to_view()
    qt_app.processEvents()
    sheet = QRectF(view.scene.sceneRect())
    fitted_zoom = view.zoom_level
    assert view.viewport().rect().adjusted(-2, -2, 2, 2).contains(view.mapFromScene(sheet).boundingRect())
    if tool == "pending_rectangle":
        drawing.begin_placement(150, 100)
    metadata = deepcopy(app.session.metadata)
    positions = tools.pos(), tools.toggle_button.pos()
    captures = []
    view.surveyPointRequested.connect(lambda *args: captures.append(args))
    covered = tools.geometry().intersected(view.mapFromScene(sheet).boundingRect())
    assert not covered.isEmpty()
    before = QPoint(covered.left() + 20, covered.bottom() - 20)
    corner = view.mapToScene(before)
    assert tools.geometry().contains(before)
    delta = QPoint(tools.geometry().right() + 70 - before.x(), -130)
    start = QPoint(view.viewport().width() // 2, view.viewport().height() // 3)
    hand_drag(view, start, delta)
    qt_app.processEvents()
    assert view.mapFromScene(corner) == before + delta
    assert not tools.geometry().contains(view.mapFromScene(corner))
    assert (tools.pos(), tools.toggle_button.pos()) == positions
    assert view.scene.sceneRect() == sheet
    assert app.session.metadata == metadata and not app.session.dirty
    assert not captures and not drawing.undo_stack
    if tool == "pending_rectangle":
        assert drawing.pending_size == (150, 100)

    tools.select_tool("line")
    drag(view, view.mapFromScene(corner), view.mapFromScene(corner + QPointF(100, -50)))
    lines = drawing_segments(app.session.metadata)
    assert len(lines) == 1 and len(drawing.undo_stack) == 1
    assert sheet.contains(QPointF(lines[0]["x1"], lines[0]["y1"]))
    assert sheet.contains(QPointF(lines[0]["x2"], lines[0]["y2"]))
    assert not captures
    view.fit_to_view()
    qt_app.processEvents()
    assert view.zoom_level == pytest.approx(fitted_zoom)
    assert view.viewport().rect().adjusted(-2, -2, 2, 2).contains(view.mapFromScene(sheet).boundingRect())
    center = view.mapFromScene(sheet.center())
    assert (center - view.viewport().rect().center()).manhattanLength() <= 2


@pytest.mark.parametrize("size", [(1200, 800), (150, 300), (1000, 50)])
@pytest.mark.parametrize("zoom_fraction", [1, 0.35])
def test_fit_zoom_and_resize_allow_pan_on_both_axes_without_changing_sheet(qt_app, tmp_path, size, zoom_fraction):
    image = tmp_path / "plan.png"
    Image.new("RGB", size, "white").save(image)
    view = FloorplanView()
    try:
        view.resize(800, 600)
        view.show()
        view.load_floorplan(str(image))
        qt_app.processEvents()
        view.set_zoom(view.zoom_level * zoom_fraction)
        for width, height in ((800, 600), (1100, 750), (500, 400)):
            view.resize(width, height)
            qt_app.processEvents()
            sheet = QRectF(0, 0, *size)
            assert view.scene.sceneRect() == sheet
            before = view.mapFromScene(sheet.center())
            start = view.viewport().rect().center()
            for delta in (QPoint(80, -60), QPoint(-160, 120)):
                hand_drag(view, start, delta)
                before += delta
                assert view.mapFromScene(sheet.center()) == before
            for _ in range(5):
                view.set_zoom(view.zoom_level)
                assert view.mapFromScene(sheet.center()) == before
            assert not view.is_point_inside_floorplan(QPointF(-1, size[1] / 2))
            assert view.is_point_inside_floorplan(sheet.center())
        view.fit_to_view()
        qt_app.processEvents()
        assert view.viewport().rect().adjusted(-2, -2, 2, 2).contains(view.mapFromScene(sheet).boundingRect())
    finally:
        view.close()
        view.deleteLater()
        qt_app.processEvents()


@pytest.mark.parametrize("mode", ["survey", "ap", "calibration", "boundaries"])
def test_navigation_margin_cannot_store_points_or_start_boundary_strokes(qt_app, tmp_path, mode):
    image = tmp_path / "plan.png"
    Image.new("RGB", (400, 300), "white").save(image)
    view = FloorplanView()
    try:
        view.resize(800, 600)
        view.show()
        view.load_floorplan(str(image))
        qt_app.processEvents()
        requested, positioned = [], []
        view.surveyPointRequested.connect(lambda *args: requested.append(args))
        view.apPositionPicked.connect(lambda *args: positioned.append(args))
        if mode == "ap":
            view.start_ap_position_pick("test", "Test AP")
        elif mode == "calibration":
            view.start_scale_calibration_pick()
        elif mode == "boundaries":
            view.set_boundaries_edit_mode(True)
        view.centerOn(0, 150)
        outside = view.mapFromScene(QPointF(-50, 150))
        assert view.viewport().rect().contains(outside)
        if mode == "survey":
            delta = QPoint(40, 20)
            hand_drag(view, outside, delta)
            assert view.mapFromScene(QPointF(-50, 150)) == outside + delta
            outside += delta
        button = Qt.MouseButton.LeftButton if mode in ("ap", "calibration") else Qt.MouseButton.RightButton
        QTest.mouseClick(view.viewport(), button, pos=outside)
        assert not requested and not positioned and not view.scale_calibration_points
        assert not view.boundaries_drawing_active and not view.has_boundaries_mask()
        if mode == "ap":
            assert view.pending_ap_position_group_id == "test"
        inside = view.mapFromScene(QPointF(50, 150))
        QTest.mouseClick(view.viewport(), button, pos=inside)
        if mode == "survey":
            assert len(requested) == 1
        elif mode == "ap":
            assert len(positioned) == 1 and not view.pending_ap_position_group_id
        elif mode == "calibration":
            assert len(view.scale_calibration_points) == 1
        else:
            assert view.has_boundaries_mask()
        view.clear_floorplan()
        assert not view.has_floorplan() and view.sceneRect().isEmpty()
        view.load_floorplan(str(image))
        assert view.scene.sceneRect() == QRectF(0, 0, 400, 300)
    finally:
        view.close()
        view.deleteLater()
        qt_app.processEvents()
