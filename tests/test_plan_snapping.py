"""Snap targets must be real, deterministic and preserve numeric dimensions."""
import math

import pytest
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtTest import QTest

from survey.plan_drawing import rectangle_segments, drawing_segments
from survey.plan_geometry import segment_bounds
from survey.plan_snapping import PlanSnapper
from qt_ui.scaling import widget_px
from tests.test_rectangle_design import editor, move
from tests.test_capture_adapter import window, qt_app

BOUNDS = (0, 0, 900, 600)


def line(x1, y1, x2, y2):
    return dict(x1=x1, y1=y1, x2=x2, y2=y2, color="#123456")


def kinds(result):
    return {guide.kind for guide in result.guides}


@pytest.mark.parametrize("origin,pointer,expected", [
    ((300, 100), (500, 204), (500, 200)),
    ((300, 200), (500, 96), (500, 100)),
    ((100, 100), (46, 204), (46, 200)),
    ((100, 200), (46, 96), (46, 100)),
    ((100, 200), (304, 400), (300, 400)),
    ((300, 200), (96, 400), (100, 400)),
])
def test_drag_aligns_full_moving_side_beyond_target_segment(origin, pointer, expected):
    snapper = PlanSnapper(rectangle_segments(100, 100, 200, 100, "#123456"))
    direct = snapper.snap(*pointer, 0, 0, BOUNDS, 10)
    assert (direct.x, direct.y) == pointer
    result = snapper.snap_drag(*pointer, origin, BOUNDS, 10)
    assert (result.x, result.y) == expected and "alignment" in kinds(result)


def test_drag_alignment_requires_real_overlap_with_draft_span_and_is_deterministic():
    lines = [line(100, 200, 300, 200), line(100, 210, 300, 210)]
    for segments in (lines, lines[::-1], lines * 2):
        result = PlanSnapper(segments).snap_drag(500, 205, (300, 100), BOUNDS, 10, grid=50)
        assert (result.x, result.y) == (500, 200)
        assert "alignment" in kinds(result)
    result = PlanSnapper(lines).snap_drag(500, 204, (350, 100), BOUNDS, 10)
    assert (result.x, result.y) == (500, 204) and not result.guides


def test_drag_supports_two_side_alignment_and_real_corner_priority():
    lines = [line(400, 100, 400, 200), line(100, 300, 200, 300)]
    result = PlanSnapper(lines).snap_drag(404, 304, (100, 100), BOUNDS, 10)
    assert (result.x, result.y) == (400, 300) and len(result.guides) == 2
    snapper = PlanSnapper(rectangle_segments(100, 100, 200, 100, "#123456"))
    result = snapper.snap_drag(304, 204, (500, 350), BOUNDS, 10, grid=50)
    assert (result.x, result.y) == (300, 200) and kinds(result) == {"corner"}


@pytest.mark.parametrize("origin", [(float("nan"), 100), (-1, 100), (1000, 100)])
def test_drag_rejects_invalid_fixed_origin_even_when_pointer_nears_a_corner(origin):
    snapper = PlanSnapper(rectangle_segments(100, 100, 200, 100, "#123456"))
    with pytest.raises(ValueError):
        snapper.snap_drag(300, 200, origin, BOUNDS, 10)


def test_drag_preview_aligns_height_and_commit_keeps_start_corner_fixed(editor, qt_app):
    window, controller = editor
    controller.commit(QRectF(100, 100, 200, 100))
    view = window.floorplan_view
    first, last = view.mapFromScene(QPointF(300, 100)), view.mapFromScene(QPointF(500, 204))
    captures = []
    view.surveyPointRequested.connect(lambda *args: captures.append(args))
    QTest.mousePress(view.viewport(), Qt.MouseButton.RightButton, pos=first)
    move(view, last, Qt.MouseButton.RightButton)
    assert controller.origin == QPointF(300, 100)
    assert controller.preview.rect().bottom() == 200
    assert "alignment" in {guide.kind for guide in controller.snap_guides}
    assert window.tr("design_snap_alignment") in controller.measurement.text()
    QTest.keyPress(window, Qt.Key.Key_Alt)
    assert controller.preview.rect().bottom() != 200
    QTest.keyRelease(window, Qt.Key.Key_Alt)
    assert controller.preview.rect().bottom() == 200
    expected = controller.preview.rect()
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.RightButton, pos=last)
    lines = drawing_segments(window.session.metadata)[4:]
    assert lines[0]["x1"] == expected.left() == 300 and lines[0]["y1"] == 100
    assert lines[1]["y2"] == 200 and not captures


def test_corner_has_priority_over_grid_and_projected_edges():
    snapper = PlanSnapper(rectangle_segments(103, 107, 200, 120, "#123456"))
    result = snapper.snap(105, 105, 0, 0, BOUNDS, 10, grid=50)
    assert (result.x, result.y) == (103, 107)
    assert kinds(result) == {"corner"}


def test_edge_snap_does_not_extend_beyond_a_real_segment():
    snapper = PlanSnapper([line(100, 100, 100, 200)])
    result = snapper.snap(104, 150, 0, 0, BOUNDS, 10)
    assert (result.x, result.y) == (100, 150) and kinds(result) == {"edge"}
    result = snapper.snap(104, 250, 0, 0, BOUNDS, 10)
    assert (result.x, result.y) == (104, 250) and not result.guides


def test_edge_has_priority_over_grid_with_independent_other_axis():
    result = PlanSnapper([line(103, 0, 103, 500)]).snap(106, 171, 0, 0, BOUNDS, 10, 50)
    assert (result.x, result.y) == (103, 150)
    assert kinds(result) == {"edge", "grid"}


def test_equal_distance_targets_are_stable_when_segment_order_changes():
    lines = [line(100, 100, 100, 300), line(110, 100, 110, 300)]
    for sequence in (lines, list(reversed(lines)), lines * 3):
        result = PlanSnapper(sequence).snap(105, 170, 0, 0, BOUNDS, 10)
        assert (result.x, result.y) == (100, 170)


def test_numeric_rectangle_snaps_opposite_corner_without_resizing():
    snapper = PlanSnapper(rectangle_segments(100, 100, 200, 100, "#123456"))
    result = snapper.snap(183, 132, 117.3, 68.9, BOUNDS, 10)
    assert result.x + 117.3 == pytest.approx(300)
    assert result.y + 68.9 == pytest.approx(200)
    assert result.guides[0].point == (300, 200)


def test_numeric_rectangle_snaps_overlapping_edges_without_near_corners():
    result = PlanSnapper([line(100, 200, 100, 220)]).snap(104, 150, 80, 130, BOUNDS, 10)
    assert (result.x, result.y) == (100, 150)
    assert result.guides[0].point == (100, 210)


def test_numeric_rectangle_can_align_different_edges_on_both_axes():
    lines = [line(100, 150, 100, 300), line(140, 270, 200, 270)]
    result = PlanSnapper(lines).snap(104, 207, 80, 60, BOUNDS, 10)
    assert (result.x, result.y) == (100, 210)
    assert len(result.guides) == 2


@pytest.mark.parametrize("grid,expected", [(None, (63.1, 76.6)), (50, (50, 100))])
def test_grid_is_optional(grid, expected):
    result = PlanSnapper().snap(63.1, 76.6, 0, 0, BOUNDS, 10, grid)
    assert (result.x, result.y) == expected


def test_grid_ties_and_sheet_bounds_are_deterministic():
    result = PlanSnapper().snap(25, 114, 0, 0, (0, 0, 115, 115), 10, 50)
    assert (result.x, result.y) == (50, 100)


def test_floating_grid_boundary_does_not_lose_the_last_visible_line():
    result = PlanSnapper().snap(4096, 4096, 0, 0, (0, 0, 4096, 4096), 10, 40.96)
    assert (result.x, result.y) == (4096, 4096)


def test_grid_translates_the_nearest_numeric_corner_without_resizing():
    result = PlanSnapper().snap(81, 85, 117.3, 63.2, BOUNDS, 10, 50)
    assert (result.x, result.y) == pytest.approx((82.7, 86.8))
    assert result.x + 117.3 == pytest.approx(200)
    assert result.y + 63.2 == pytest.approx(150)
    assert result.guides[0].point == (200, 150)


def test_bounds_hold_for_all_numeric_corner_targets():
    snapper = PlanSnapper(rectangle_segments(0, 0, 900, 600, "#123456"))
    for x, y in ((-50, -20), (895, 599), (14, 14), (450, 590)):
        result = snapper.snap(x, y, 117.3, 68.9, BOUNDS, 10, 50)
        assert 0 <= result.x <= 900 - 117.3
        assert 0 <= result.y <= 600 - 68.9


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_invalid_pointer_coordinates_cannot_produce_geometry(value):
    with pytest.raises(ValueError):
        PlanSnapper().snap(value, 10, 20, 30, BOUNDS, 10)


@pytest.mark.parametrize("zoom", [1, 2, 4])
def test_geometry_acquisition_distance_is_in_viewport_pixels(editor, qt_app, zoom):
    window, controller = editor
    controller.commit(QRectF(100, 100, 200, 150))
    view = window.floorplan_view
    view.set_zoom(zoom)
    scale = math.hypot(view.transform().m11(), view.transform().m12())
    close = controller.snap_position(QPointF(100 + widget_px(window, 8) / scale, 100))
    far = controller.snap_position(QPointF(100 + widget_px(window, 14) / scale, 100))
    assert (close.x, close.y) == (100, 100)
    assert "corner" in kinds(close) and "corner" not in kinds(far)


def test_grid_toggle_updates_preview_without_changing_numeric_size(editor, qt_app):
    window, controller = editor
    controller.begin_placement(117.3, 63.2, anchor=QPointF(167, 197))
    window.plan_tools.snap_button.click()
    rect = controller.preview.rect()
    step = window.floorplan_view.grid_spacing_pixels()
    assert any(corner.x() / step == pytest.approx(round(corner.x() / step))
               and corner.y() / step == pytest.approx(round(corner.y() / step))
               for corner in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()))
    assert rect.width() == pytest.approx(117.3) and rect.height() == pytest.approx(63.2)
    assert controller.snap_items and window.tr("design_snap_grid") in controller.measurement.text()
    assert not window.session.dirty
    window.set_floorplan_grid_enabled(False, show_status=False)
    assert not window.plan_tools.snap_button.isChecked()
    assert not controller.snap_guides


def test_grid_snap_uses_the_displayed_imperial_interval(editor, qt_app):
    window, controller = editor
    window.measurement_system = "imperial"
    window.plan_tools.snap_button.click()
    step = window.floorplan_view.grid_spacing_pixels()
    assert step == pytest.approx(.9144 * window.get_px_per_meter())
    result = controller.snap_position(QPointF(68, 83))
    assert result.x / step == pytest.approx(round(result.x / step))
    assert result.y / step == pytest.approx(round(result.y / step))


def test_alt_temporarily_bypasses_geometry_and_grid_without_resizing(editor, qt_app):
    window, controller = editor
    controller.commit(QRectF(100, 100, 200, 100))
    controller.begin_placement(117.3, 68.9, anchor=QPointF(183, 132))
    assert controller.snap_guides
    QTest.keyPress(window, Qt.Key.Key_Alt)
    assert not controller.snap_guides
    assert controller.preview.rect().width() == pytest.approx(117.3)
    QTest.keyRelease(window, Qt.Key.Key_Alt)
    assert controller.snap_guides
    controller.cancel()
    window.plan_tools.snap_button.click()
    result = controller.snap_position(QPointF(166.7, 197.2), 117.3, 68.9, bypass=True)
    assert (result.x, result.y) == (166.7, 197.2) and not result.guides


def test_guides_do_not_accumulate_and_are_removed_on_cancel(editor, qt_app):
    window, controller = editor
    controller.commit(QRectF(100, 100, 200, 100))
    controller.begin_placement(117.3, 68.9, anchor=QPointF(183, 132))
    count = len(window.floorplan_view.scene.items())
    for _ in range(30):
        controller.refresh_snap()
    assert len(window.floorplan_view.scene.items()) == count
    controller.cancel()
    assert not controller.snap_items and not controller.snap_guides


def test_snap_targets_refresh_after_undo_redo_and_reopen(editor, qt_app, tmp_path):
    window, controller = editor
    controller.commit(QRectF(100, 100, 200, 100))
    assert "corner" in kinds(controller.snap_position(QPointF(103, 103)))
    controller.undo()
    assert not controller.snap_position(QPointF(103, 103)).guides
    controller.redo()
    original = drawing_segments(window.session.metadata)
    window.plan_tools.set_open(False)
    csv = tmp_path / "snapping.csv"
    window.session.csv_file = str(csv)
    assert window.save_survey() and window.open_survey(str(csv))
    assert drawing_segments(window.session.metadata) == original
    assert "corner" in kinds(controller.snap_position(QPointF(103, 103)))


def test_numeric_commit_uses_the_previewed_snap_and_consumes_release(editor, qt_app):
    window, controller = editor
    view = window.floorplan_view
    controller.commit(QRectF(100, 100, 200, 100))
    from PySide6.QtGui import QColor
    window.plan_tools.stroke_color = QColor("#d84315")
    controller.begin_placement(117.3, 68.9)
    point = view.mapFromScene(QPointF(183, 132))
    move(view, point)
    expected = controller.preview.rect()
    captures = []
    view.surveyPointRequested.connect(lambda *args: captures.append(args))
    QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=point)
    lines = [line for line in drawing_segments(window.session.metadata) if line["color"] == "#d84315"]
    left, top, right, bottom = segment_bounds(lines)
    assert (left, top) == pytest.approx((expected.x(), expected.y()))
    assert (right - left, bottom - top) == pytest.approx((117.3, 68.9))
    assert not captures and controller.pending_size is None
