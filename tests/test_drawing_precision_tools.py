"""Door symbols, isolated erasers, center magnets and transient wall dimensions."""
import math
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtTest import QTest

from qt_ui.qt_plan_annotations import AnnotationDialog, DOOR_CHOICES
from qt_ui.qt_plan_region_selection import RegionPicker
from survey.plan_annotation_rendering import annotation_parts, annotation_item
from survey.plan_annotations import annotation_points
from survey.plan_drawing import rectangle_segments, render_plan_drawing
from survey.plan_snapping import PlanSnapper
from tests.test_plan_annotations import aperture, marker, line, at, choose
from tests.test_plan_text_fill import label
from tests.test_rectangle_design import editor, move, drag
from tests.test_capture_adapter import window, qt_app

BOUNDS = (0, 0, 900, 600)


@pytest.mark.parametrize("variant", ["single", "double", "sliding"])
def test_only_door_swing_arcs_are_dashed_in_shared_scene_and_export(qt_app, variant):
    item = aperture(variant=variant, x1=200, x2=300, stroke=2)
    parts = annotation_parts(item)
    assert [dashed for _path, dashed in parts] == ([False] if variant == "sliding" else [False, True])
    native = annotation_item(item)
    assert sorted(child.pen().style().value for child in native.childItems()) == sorted(
        (Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine).value for _path, dashed in parts)
    image = render_plan_drawing(Image.new("RGB", (900, 600), "white"), [line()], annotations=[item])
    if variant == "single":
        assert all(image.getpixel((200, y)) != (255, 255, 255) for y in range(205, 295))
        samples = [image.getpixel((round(200 + 100 * math.cos(a * math.pi / 180)),
                                  round(200 + 100 * math.sin(a * math.pi / 180)))) for a in range(5, 85)]
        assert any(p == (255, 255, 255) for p in samples) and any(p != (255, 255, 255) for p in samples)


@pytest.mark.parametrize("choice", DOOR_CHOICES)
def test_door_icon_row_selects_exact_configuration_without_flip_options(editor, choice):
    app, d = editor
    dialog = AnnotationDialog(d.annotation, aperture())
    try:
        assert len(dialog.door_buttons) == 7
        button = dialog.door_buttons[choice]
        button.click()
        value = dialog.properties()
        assert (value["variant"], value["hinge"], value["side"]) == choice
        assert sum(b.isChecked() for b in dialog.door_buttons.values()) == 1
        assert not button.icon().isNull() and button.accessibleName()
        assert not hasattr(dialog, "hinge") and not hasattr(dialog, "side")
    finally:
        dialog.deleteLater()


def test_two_erasers_are_distinct_and_annotation_click_drag_never_erases_walls(editor):
    app, d = editor
    walls = [line(), line(100, 400, 600, 400)]
    d.store(walls, [label()], annotations=[aperture(), marker()])
    choose(app, "annotation_eraser")
    assert app.plan_tools.annotation_buttons["annotation_eraser"].isChecked()
    move(app.floorplan_view, at(app, 200, 150))
    assert d.annotation.selected == (1,)
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 200, 150))
    assert d.segments() == walls and d.annotations() == [aperture()] and len(d.labels()) == 1
    d.undo()
    drag(app.floorplan_view, at(app, 80, 100), at(app, 650, 300))
    assert d.segments() == walls and not d.annotations() and not d.labels()
    d.undo()
    choose(app, "eraser")
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 200, 400))
    assert d.annotations() == [aperture(), marker()] and len(d.labels()) == 1
    assert d.segments() == [line()]


def test_midpoint_and_room_center_are_distinct_from_corners_and_work_without_grid():
    snapper = PlanSnapper([line()], region_centers=[(350, 350)])
    midpoint = snapper.snap(354, 203, 0, 0, BOUNDS, 10)
    center = snapper.snap(353, 354, 0, 0, BOUNDS, 10)
    assert (midpoint.x, midpoint.y, midpoint.guides[0].kind) == (350, 200, "midpoint")
    assert (center.x, center.y, center.guides[0].kind) == (350, 350, "area_center")
    assert snapper.snap(103, 202, 0, 0, BOUNDS, 10).guides[0].kind == "corner"
    assert snapper.vertices == [(100, 200), (600, 200)]  # Magnets do not split the wall.


def test_rigid_shapes_can_snap_from_their_center_without_changing_dimensions():
    snapper = PlanSnapper([line()])
    source = rectangle_segments(330, 193, 50, 20, "#123456")
    result = snapper.snap_geometry(source, BOUNDS, 10)
    assert (result.x, result.y) == (-5, -3) and result.guides[0].kind == "midpoint"
    assert source == rectangle_segments(330, 193, 50, 20, "#123456")


def test_room_centers_remain_inside_concave_and_holed_areas(qt_app):
    outer = rectangle_segments(100, 100, 500, 400, "#123456")
    inner = rectangle_segments(250, 200, 200, 200, "#123456")
    picker = RegionPicker(outer + inner, [])
    centers = picker.centers()
    assert len(centers) == 2
    assert all(path.contains(QPointF(*center)) for (path, _region), center in zip(picker.records, centers))
    rectangle = RegionPicker(outer, [])
    assert rectangle.centers() == [(350, 300)]


@pytest.mark.parametrize("kind", ["door", "window"])
def test_aperture_center_is_the_opening_center_and_alt_disables_magnets(editor, kind):
    app, d = editor
    d.store([line()])
    choose(app, kind, aperture(kind, x2=330))
    app.plan_tools.snap_button.setChecked(False)
    target = at(app, 354, 200)
    move(app.floorplan_view, target)
    a, b = annotation_points(d.annotation.pending)
    assert ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) == (350, 200)
    assert d.snap_guides[0].kind == "midpoint"
    if kind == "door":
        assert d.annotation.preview[0].boundingRect().center().y() != 200
    QTest.keyPress(app, Qt.Key.Key_Alt)
    raw = app.floorplan_view.mapToScene(target)
    a, b = annotation_points(d.annotation.pending)
    assert (a[0] + b[0]) / 2 == pytest.approx(raw.x()) and not d.snap_guides
    QTest.keyRelease(app, Qt.Key.Key_Alt)
    assert d.snap_guides[0].kind == "midpoint"
    assert d.segments() == [line()]


def test_opening_can_anchor_either_jamb_to_a_wall_corner(editor):
    app, d = editor
    d.store([line()])
    choose(app, "door", aperture(x2=330))
    move(app.floorplan_view, at(app, 103, 200))
    assert d.annotation.pending and min(p[0] for p in annotation_points(d.annotation.pending)) == 100
    assert d.snap_guides[0].kind == "corner"
    assert d.dimensions.values["before"] < 10  # Actual cursor stays near the jamb.
    assert d.dimensions.values["clearance_before"] == pytest.approx(0)


def test_text_creation_and_annotation_move_snap_the_label_center_to_room_center(editor):
    app, d = editor
    d.store(rectangle_segments(100, 100, 500, 400, "#123456"))
    choose(app, "text")
    app.plan_tools.snap_button.setChecked(False)
    assert d.text.begin_placement(label(), at(app, 354, 304))
    assert (d.text.pending["x"], d.text.pending["y"]) == pytest.approx((350, 300))
    assert d.snap_guides[0].kind == "area_center"
    d.cancel()
    d.store(d.segments(), [label()])
    choose(app, "annotation_select")
    d.annotation.select((), (0,))
    d.annotation.last_pointer = QPointF(at(app, 300, 220))
    QTest.keyClick(app, Qt.Key.Key_M)
    move(app.floorplan_view, at(app, 354, 304))
    assert (d.annotation.draft_labels[0]["x"], d.annotation.draft_labels[0]["y"]) == pytest.approx((350, 300))
    QTest.keyPress(app, Qt.Key.Key_Alt)
    assert (d.annotation.draft_labels[0]["x"], d.annotation.draft_labels[0]["y"]) != pytest.approx((350, 300))
    QTest.keyRelease(app, Qt.Key.Key_Alt)


def test_grid_off_keeps_marker_corner_snapping_and_alt_disables_it(editor):
    app, d = editor
    d.store([line()])
    choose(app, "marker", marker())
    app.plan_tools.snap_button.setChecked(False)
    position = QPointF(at(app, 103, 202))
    assert d.annotation.point(position, False, True) == [100, 200]
    QTest.keyPress(app, Qt.Key.Key_Alt)
    assert d.annotation.point(position, False, True) != [100, 200]
    QTest.keyRelease(app, Qt.Key.Key_Alt)


@pytest.mark.parametrize("system", ["metric", "imperial"])
def test_overlay_reports_cursor_splits_and_separate_opening_clearance(editor, system):
    app, d = editor
    app.measurement_system = system
    d.store([line()])
    choose(app, "door", aperture(x1=145, x2=195))
    move(app.floorplan_view, at(app, 170, 200))
    values = d.dimensions.values
    assert values and values["before"] + values["after"] == pytest.approx(500)
    assert values["clearance_before"] / app.get_px_per_meter() == pytest.approx(.9, abs=.02)
    assert values["before_m"] == pytest.approx(1.4, abs=.02)
    assert ("ft" if system == "imperial" else "m") in d.dimensions.badge.text()
    assert d.dimensions.badge.y() > d.measurement.geometry().bottom()
    assert len(d.dimensions.items) == 2 and d.segments() == [line()]
    move(app.floorplan_view, at(app, 700, 500))
    assert d.dimensions.values is None and not d.dimensions.badge.isVisible()


def test_dimensions_do_not_dirty_the_survey_and_disappear_when_mode_closes(editor):
    app, d = editor
    d.store([line()])
    choose(app, "line")
    app.session.dirty = False
    before = d.snapshot()
    move(app.floorplan_view, at(app, 190, 200))
    assert d.dimensions.values and not app.session.dirty and d.snapshot() == before
    app.plan_tools.set_open(False)
    assert not d.dimensions.badge.isVisible() and not d.dimensions.values
