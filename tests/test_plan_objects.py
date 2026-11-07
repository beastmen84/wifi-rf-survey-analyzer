"""Free desk/symbol geometry, placement, styles and structural isolation."""
from copy import deepcopy
from unittest.mock import patch

from PIL import Image
import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest

from app_core.units import display_units_to_meters
from qt_ui.qt_plan_objects import ObjectAnnotationDialog
from survey.plan_objects import DESK_VARIANTS, SYMBOL_VARIANTS, object_default, object_is_round, object_vertices
from survey.plan_annotations import (PLAN_ANNOTATIONS_KEY, validate_annotations, encode_annotations, drawing_annotations,
    visible_wall_segments, supported, overlaps, follow_hosts, transform_annotations)
from survey.plan_annotation_rendering import annotation_path, annotation_item
from survey.plan_drawing import rectangle_segments, render_plan_drawing
from tests.test_capture_adapter import window, qt_app
from tests.test_rectangle_design import editor, move, drag
from tests.test_plan_annotations import aperture, marker, line, choose, at

VARIANTS = [("desk", v) for v in DESK_VARIANTS] + [("symbol", v) for v in SYMBOL_VARIANTS]


def obj(kind="desk", variant="rectangle", **changes):
    item = dict(object_default(kind, 100, variant), id="object1", cx=450, cy=320)
    item.update(changes)
    return validate_annotations([item])[0]


@pytest.mark.parametrize("kind,variant", VARIANTS)
def test_objects_roundtrip_render_fill_and_outline_without_hosts(qt_app, kind, variant):
    item = obj(kind, variant, color="#123456", fill="#abcdef")
    before = deepcopy(item)
    metadata = {"_generated_floorplan": "1", PLAN_ANNOTATIONS_KEY: encode_annotations([item])}
    assert drawing_annotations(metadata) == [item] and item == before
    assert supported(item, []) and not overlaps(item, [item, aperture()])
    assert visible_wall_segments([line()], [item]) == [line()]
    image = render_plan_drawing(Image.new("RGB", (900, 600), "white"), [], annotations=[item])
    colors = dict((color, count) for count, color in image.getcolors(900 * 600))
    assert colors.get((18, 52, 86), 0) > 1 and colors.get((171, 205, 239), 0) > 1
    native = annotation_item(item)
    assert native.childItems()[0].brush().color().name() == "#abcdef"
    assert native.childItems()[0].pen().color().name() == "#123456"
    empty = render_plan_drawing(Image.new("RGB", (900, 600), "white"), [], annotations=[dict(item, fill=None)])
    assert (171, 205, 239) not in [color for _count, color in empty.getcolors(900 * 600)]
    moved = transform_annotations([item], 90, (450, 320), 10, 20)[0]
    assert (moved["cx"], moved["cy"]) == (460, 340)
    assert moved["angle"] == (0 if object_is_round(item) else 90)
    assert item == before


@pytest.mark.parametrize("changes", [dict(width=0), dict(height=float("nan")), dict(angle=float("inf")),
    dict(cx=-1000), dict(width=100001), dict(fill="red"), dict(stroke=0), dict(variant="bad"),
    dict(variant="square", width=100, height=80), dict(variant="l", arm=0),
    dict(variant="l", arm=200), dict(variant="l_equal", width=100, height=80)])
def test_invalid_object_data_is_rejected(changes):
    item = dict(object_default("desk", 100), cx=450, cy=320)
    item.update(changes)
    with pytest.raises((ValueError, KeyError)):
        validate_annotations([item])


@pytest.mark.parametrize("kind,variant", VARIANTS)
@pytest.mark.parametrize("system", ["metric", "imperial"])
def test_object_dialog_variants_dimensions_and_independent_colors(editor, kind, variant, system):
    app, d = editor
    app.measurement_system = system
    dialog = ObjectAnnotationDialog(d.annotation, obj(kind, variant))
    try:
        assert len(dialog.variant_buttons) == (len(DESK_VARIANTS) if kind == "desk" else len(SYMBOL_VARIANTS))
        assert dialog.variant_buttons[variant].isChecked()
        assert all(not button.icon().isNull() and button.accessibleName() for button in dialog.variant_buttons.values())
        dialog.width_spin.setValue(2)
        if dialog.height_spin.isHidden() is False:
            dialog.height_spin.setValue(3)
        dialog.stroke.setValue(3.5)
        with patch("qt_ui.qt_plan_colors.QColorDialog.getColor", return_value=QColor("#123456")):
            dialog.outline.click()
        dialog.fill_enabled.setChecked(True)
        with patch("qt_ui.qt_plan_colors.QColorDialog.getColor", return_value=QColor("#abcdef")):
            dialog.fill.click()
        result = validate_annotations([dialog.properties()])[0]
        assert result["width"] == pytest.approx(display_units_to_meters(2, system) * app.get_px_per_meter())
        assert result["color"] == "#123456" and result["fill"] == "#abcdef" and result["stroke"] == 3.5
        assert result["variant"] == variant and result["cx"] == 450 and result["cy"] == 320
        if (kind == "symbol" and variant != "rack") or variant in ("square", "l_equal", "round"):
            assert result["height"] == result["width"]
        if variant in ("l", "l_equal"):
            assert 0 < result["arm"] < min(result["width"], result["height"])
        dialog.fill_enabled.setChecked(False)
        assert dialog.properties()["fill"] is None
    finally:
        dialog.deleteLater()


@pytest.mark.parametrize("kind,variant", VARIANTS)
def test_cursor_place_rotate_select_move_delete_and_history(editor, qt_app, kind, variant):
    app, d = editor
    item = obj(kind, variant)
    walls = rectangle_segments(100, 150, 600, 350, "#334455")
    d.store(walls)
    app.session.dirty = False
    choose(app, kind, item)
    captures = []
    app.floorplan_view.surveyPointRequested.connect(lambda *args: captures.append(args))
    target = at(app, 450, 320)
    move(app.floorplan_view, target)
    assert d.annotation.pending and not d.annotations() and not app.session.dirty
    before = deepcopy(d.annotation.pending)
    QTest.keyClick(app, Qt.Key.Key_R)
    assert d.annotation.pending["angle"] == (0 if object_is_round(item) else 90)
    assert (d.annotation.pending["width"], d.annotation.pending["height"]) == (item["width"], item["height"])
    assert not d.undo_stack and not captures
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=target)
    assert len(d.annotations()) == 1 and d.segments() == walls and len(d.undo_stack) == 1
    original = d.annotations()[0]
    assert original["id"] not in ("template", "preview") and original["fill"] == item["fill"]
    choose(app, "annotation_select")
    first = object_vertices(original)[0]
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, *first))
    assert d.annotation.selected == (0,) and not d.selection.has_selection()
    QTest.keyClick(app, Qt.Key.Key_R)
    assert len(d.undo_stack) == (1 if object_is_round(item) else 2)
    QTest.keyClick(app, Qt.Key.Key_M)
    assert d.annotation.moving
    move(app.floorplan_view, at(app, 620, 400))
    assert d.annotations()[0] != d.annotation.draft[0]
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 620, 400))
    assert d.segments() == walls and d.annotations()[0]["id"] == original["id"]
    assert not captures
    moved = d.snapshot()
    QTest.keyClick(app, Qt.Key.Key_Delete)
    assert not d.annotations() and d.segments() == walls
    d.undo()
    assert d.snapshot() == moved
    d.redo()
    assert not d.annotations()
    assert (before["cx"], before["cy"]) == pytest.approx((450, 320), abs=1)


def test_l_notch_and_open_marker_interior_are_empty_but_solid_object_can_be_marquee_picked(editor):
    app, d = editor
    item = obj("desk", "l", width=200, height=160, arm=60, cx=350, cy=300)
    d.store([], annotations=[item])
    assert d.annotation.pick((270, 330))[0] == (0,)
    assert d.annotation.pick((420, 350)) == ((), ())
    choose(app, "annotation_eraser")
    drag(app.floorplan_view, at(app, 270, 320), at(app, 280, 330))
    assert not d.annotations() and not d.segments()
    d.undo()
    assert d.annotations() == [item]
    image = render_plan_drawing(Image.new("RGB", (900, 600), "white"), [], annotations=[
        obj("desk", "square", cx=650, cy=250), marker(points=[[100, 100], [100, 400], [400, 400]])])
    assert image.getpixel((200, 300)) == (255, 255, 255)  # Fill must not leak into a later open path.


def test_objects_never_follow_or_mask_structural_hosts_or_change_room_area(editor):
    app, d = editor
    walls = rectangle_segments(100, 200, 500, 250, "#123456")
    items = [obj("desk", "l_equal"), obj("symbol", "x", id="symbol1", cx=200, cy=300)]
    assert d.apply_edit(walls, annotations=items)
    assert d.selection.regions().pick(QPointF(350, 325)).area == 125000
    assert visible_wall_segments(walls, items) == walls
    shifted = [dict(line(), y1=300, y2=300)]
    assert follow_hosts(items, [line()], shifted) == items
    assert d.apply_edit([], annotations=None)
    assert d.annotations() == items  # Removing structural hosts leaves free annotations.


@pytest.mark.parametrize("kind", ["desk", "symbol"])
def test_clicking_each_variant_and_editing_selected_object_keeps_identity_pose_and_structure(editor, kind):
    app, d = editor
    item = obj(kind, "l" if kind == "desk" else "arrow", angle=90)
    dialog = ObjectAnnotationDialog(d.annotation, item)
    try:
        for variant, button in dialog.variant_buttons.items():
            button.click()
            value = validate_annotations([dialog.properties()])[0]
            assert value["variant"] == variant
            assert sum(b.isChecked() for b in dialog.variant_buttons.values()) == 1
            assert (value["cx"], value["cy"]) == (item["cx"], item["cy"])
    finally:
        dialog.deleteLater()
    d.store([line()], annotations=[item])
    choose(app, "annotation_select")
    point = object_vertices(item)[0]
    changed = dict(item, fill="#aaeecc", color="#224488", stroke=4)
    with patch.object(ObjectAnnotationDialog, "exec", return_value=1), \
            patch.object(ObjectAnnotationDialog, "properties", return_value=changed):
        QTest.mouseDClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, *point))
    assert d.annotations() == [changed] and d.segments() == [line()]
    assert len(d.undo_stack) == 1
    d.undo()
    assert d.annotations() == [item]


@pytest.mark.parametrize("kind,variant", VARIANTS)
def test_creation_center_snap_alt_grid_and_sheet_edge_preserve_object_dimensions(editor, kind, variant):
    app, d = editor
    d.store(rectangle_segments(100, 100, 500, 400, "#123456"))
    item = obj(kind, variant)
    choose(app, kind, item)
    cursor = at(app, 349, 299)
    move(app.floorplan_view, cursor)
    assert (d.annotation.pending["cx"], d.annotation.pending["cy"]) == pytest.approx((350, 300))
    assert any(guide.kind == "area_center" for guide in d.snap_guides)
    QTest.keyPress(app, Qt.Key.Key_Alt)
    raw = app.floorplan_view.mapToScene(cursor)
    assert (d.annotation.pending["cx"], d.annotation.pending["cy"]) == pytest.approx((raw.x(), raw.y()))
    assert not d.snap_guides
    QTest.keyRelease(app, Qt.Key.Key_Alt)
    assert (d.annotation.pending["cx"], d.annotation.pending["cy"]) == pytest.approx((350, 300))
    for _ in range(4):
        move(app.floorplan_view, at(app, 2, 2))
        QTest.keyClick(app, Qt.Key.Key_R)
        assert d.annotation.valid([d.annotation.pending])
        assert (d.annotation.pending["width"], d.annotation.pending["height"]) == (item["width"], item["height"])
    app.plan_tools.snap_button.setChecked(True)
    move(app.floorplan_view, at(app, 448, 326))
    step = app.floorplan_view.grid_spacing_pixels()
    vertices = object_vertices(d.annotation.pending)
    center = (d.annotation.pending["cx"], d.annotation.pending["cy"])
    assert any(abs(x / step - round(x / step)) < 1e-7 and abs(y / step - round(y / step)) < 1e-7 for x, y in [*vertices, center])
    assert not d.annotations() and not d.undo_stack


@pytest.mark.parametrize("kind,variant", [("desk", "l_equal"), ("desk", "round"), ("symbol", "arrow")])
def test_objects_survive_real_save_png_and_reopen(editor, tmp_path, kind, variant):
    app, d = editor
    item = obj(kind, variant, fill="#abcdef")
    d.store([line()], annotations=[item])
    path = tmp_path / "objects.csv"
    app.session.csv_file = str(path)
    app.plan_tools.set_open(False)
    with patch("qt_ui.qt_session_workflow.QMessageBox.warning") as error:
        assert app.save_survey(), error.call_args
    assert app.open_survey(str(path))
    assert d.annotations() == [item] and d.segments() == [line()]
    with Image.open(path.with_suffix(".png")) as image:
        assert any(color == (171, 205, 239) for _count, color in image.convert("RGB").getcolors(image.width * image.height))
