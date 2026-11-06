"""Annotation isolation, geometric hosts, persistence, ink masking and UI tools."""
from copy import deepcopy
import json
import math
from unittest.mock import patch

from PIL import Image
import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog

from survey.plan_annotations import (PLAN_ANNOTATIONS_KEY, annotation_points, drawing_annotations,
    encode_annotations, follow_hosts, overlaps, place_aperture, supported, transform_annotations,
    validate_annotations, visible_wall_segments)
from survey.plan_annotation_rendering import annotation_path
from survey.plan_drawing import rectangle_segments, render_plan_drawing
from survey.plan_geometry import normalize_segments, rotate_degrees, translate_segments
from qt_ui.qt_plan_annotations import AnnotationDialog
from tests.test_rectangle_design import editor, move, drag
from tests.test_capture_adapter import window, qt_app
from tests.test_plan_text_fill import label


def line(x1=100, y1=200, x2=600, y2=200):
    return dict(x1=x1, y1=y1, x2=x2, y2=y2, color="#123456")


def aperture(kind="door", **updates):
    return dict(dict(id="door1", kind=kind, x1=250, y1=200, x2=300, y2=200,
                     color="#334155", stroke=2, side=1, hinge=0, variant="single"), **updates)


def marker(**updates):
    return dict(dict(id="marker1", kind="marker", points=[[150, 150], [400, 150]], stroke=3, color="#d97706"), **updates)


def at(app, x, y):
    return app.floorplan_view.mapFromScene(QPointF(x, y))


def choose(app, tool, item=None):
    with patch.object(app.plan_tools.controller.annotation, "configure", return_value=True):
        app.plan_tools.select_tool(tool)
    if item:
        app.plan_tools.controller.annotation.templates[tool] = item


@pytest.mark.parametrize("item", [marker(), aperture(), aperture("window"), aperture(variant="double"), aperture(variant="sliding")])
def test_annotation_roundtrip_preserves_originals_and_legacy_absence(item):
    original = deepcopy(item)
    metadata = {"_generated_floorplan": "1", PLAN_ANNOTATIONS_KEY: encode_annotations([item])}
    assert drawing_annotations(metadata) == [item] and item == original
    assert not drawing_annotations({}) and not drawing_annotations({PLAN_ANNOTATIONS_KEY: metadata[PLAN_ANNOTATIONS_KEY]})
    assert json.loads(metadata[PLAN_ANNOTATIONS_KEY])["version"] == 1


@pytest.mark.parametrize("item", [marker(stroke=0), marker(color="red"), marker(points=[[0, 0], [float("nan"), 1]]),
    marker(points=[[0, 0]]), marker(points=[[1, 1], [1, 1]]), aperture(side=0), aperture(variant="bad"), aperture(x2=250)])
def test_invalid_annotation_models_are_rejected(item):
    with pytest.raises(ValueError):
        validate_annotations([item])


def test_duplicate_ids_version_and_complexity_are_rejected():
    with pytest.raises(ValueError):
        validate_annotations([marker(), marker()])
    with pytest.raises(ValueError):
        validate_annotations([marker(id=str(i)) for i in range(1001)])
    with pytest.raises(ValueError):
        drawing_annotations({"_generated_floorplan": "1", PLAN_ANNOTATIONS_KEY: '{"version":9,"items":[]}'})


@pytest.mark.parametrize("angle", [0, 5, 35, 90, 175, 270, 315])
def test_hosting_masking_and_rigid_following_use_true_oblique_geometry(angle):
    walls = rotate_degrees([line()], angle, (350, 300))
    item = transform_annotations([aperture()], angle, (350, 300))[0]
    assert supported(item, walls)
    visible = visible_wall_segments(walls, [item])
    assert len(visible) == 2
    assert sum(math.dist((s["x1"], s["y1"]), (s["x2"], s["y2"])) for s in visible) == pytest.approx(450)
    moved = translate_segments(walls, 50, 100)
    following = follow_hosts([item, marker()], walls, moved)
    assert following[0] == transform_annotations([item], dx=50, dy=100)[0]
    assert following[1] == marker()
    point = tuple(sum(p[i] for p in annotation_points(item)) / 2 for i in (0, 1))
    placed = place_aperture(point, 50, walls, 10, item)
    assert placed is not None and supported(placed, walls)


def test_host_survives_real_t_cut_and_fusion_but_never_bridges_a_gap():
    item = aperture()
    cut = normalize_segments([line(), line(275, 100, 275, 300)])
    assert supported(item, cut) and supported(item, normalize_segments([line(), line(270, 200, 280, 200)]))
    assert not supported(item, [line(100, 200, 270, 200), line(280, 200, 600, 200)])
    assert overlaps(item, [aperture(id="other", x1=275, x2=350)])
    assert not overlaps(item, [aperture(id="other", x1=300, x2=350)])
    assert not overlaps(item, [aperture(id="other", y1=300, y2=300)])
    assert not place_aperture((102, 200), 50, [line()], 10, item)


def test_mask_only_hides_host_ink_and_export_fingerprint_tracks_annotations(qt_app):
    walls = [line(), line(275, 100, 275, 300)]
    base = Image.new("RGB", (900, 600), "white")
    item = aperture()
    image = render_plan_drawing(base, walls, annotations=[item])
    assert image.getpixel((265, 200)) == (255, 255, 255)
    assert image.getpixel((275, 200)) == (18, 52, 86)  # A crossing wall is not erased.
    assert image.getpixel((200, 200)) == (18, 52, 86)
    assert walls == [line(), line(275, 100, 275, 300)]
    colored = render_plan_drawing(base, walls, annotations=[dict(item, color="#ff0000")])
    assert image.info["plan_drawing_fingerprint"] != colored.info["plan_drawing_fingerprint"]
    restored = render_plan_drawing(image, walls, annotations=[])
    assert restored.getpixel((265, 200)) == (18, 52, 86)


def test_marker_and_apertures_leave_room_topology_and_area_untouched(editor):
    app, d = editor
    walls = rectangle_segments(100, 200, 500, 250, "#123456")
    assert d.apply_edit(walls)
    before = deepcopy(d.regions)
    assert d.apply_edit(d.segments(), annotations=[aperture(), marker()])
    assert d.segments() == walls and d.regions.faces == before.faces
    assert d.selection.regions().pick(QPointF(350, 325)).area == 125000
    assert (275, 200) not in d.snapper.vertices
    assert len(d.items) == 4 and len(d.annotation.items) == 2


def test_structure_and_annotation_selections_and_deletions_are_isolated(editor):
    app, d = editor
    d.store([line()], [label()], annotations=[aperture(), marker()])
    before = deepcopy(d.segments())
    choose(app, "annotation_select")
    captures = []
    app.floorplan_view.surveyPointRequested.connect(lambda *args: captures.append(args))
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 250, 225))
    assert d.annotation.selected == (0,) and not d.selection.selected
    QTest.keyClick(app, Qt.Key.Key_Delete)
    assert d.segments() == before and len(d.annotations()) == 1 and len(d.labels()) == 1
    d.undo()
    choose(app, "select")
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 200, 150))
    assert not d.selection.has_selection() and not d.annotation.selected
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 300, 220))
    assert not d.selection.selected_labels
    QTest.keyClick(app, Qt.Key.Key_Delete)
    assert d.segments() == before and len(d.annotations()) == 2
    choose(app, "annotation_select")
    drag(app.floorplan_view, at(app, 80, 110), at(app, 650, 300))
    assert len(d.annotation.selected) == 2 and d.annotation.selected_labels == (0,)
    QTest.keyClick(app, Qt.Key.Key_Delete)
    assert d.segments() == before and not d.annotations() and not d.labels() and not captures
    d.undo()
    assert len(d.annotations()) == 2 and len(d.labels()) == 1


@pytest.mark.parametrize("grid", [False, True])
def test_marker_gesture_stays_above_structure_and_preserves_it(editor, grid):
    app, d = editor
    d.store([line()])
    choose(app, "marker", marker())
    d.annotation.marker_grid = grid
    drag(app.floorplan_view, at(app, 150, 150), at(app, 400, 350))
    assert d.segments() == [line()] and len(d.annotations()) == 1
    item = d.annotations()[0]
    assert item["kind"] == "marker" and d.annotation.items[0].zValue() > d.items[0].zValue()
    if grid:
        points = item["points"]
        step = app.floorplan_view.grid_spacing_pixels()
        assert all(v / step == pytest.approx(round(v / step)) for p in points for v in p)
        assert all(a[0] == b[0] or a[1] == b[1] for a, b in zip(points, points[1:]))
    d.undo()
    assert not d.annotations() and d.segments() == [line()]


@pytest.mark.parametrize("kind,variant,hinge,side", [("window", "single", 0, 1), ("door", "single", 0, 1),
    ("door", "single", 1, -1), ("door", "double", 0, 1), ("door", "sliding", 0, 1)])
def test_aperture_cursor_preview_place_reject_overlap_and_properties(editor, kind, variant, hinge, side):
    app, d = editor
    d.store([line()])
    template = aperture(kind, variant=variant, hinge=hinge, side=side)
    choose(app, kind, template)
    target = at(app, 350, 200)
    move(app.floorplan_view, target)
    assert d.annotation.pending and d.annotation.preview
    assert not d.annotations()
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=target)
    assert len(d.annotations()) == 1 and d.segments() == [line()]
    count = len(d.undo_stack)
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=target)
    assert len(d.annotations()) == 1 and len(d.undo_stack) == count
    choose(app, "annotation_select")
    d.annotation.select((0,))
    changed = dict(d.annotations()[0], color="#00aa00")
    with patch.object(d.annotation, "dialog", return_value=changed):
        assert d.annotation.edit()
    assert d.annotations()[0]["color"] == "#00aa00" and d.segments() == [line()]
    assert len(d.undo_stack) == count + 1


def test_host_move_rotation_and_deletion_are_one_shared_undo_step(editor):
    app, d = editor
    d.store([line()], annotations=[aperture(), marker()])
    original = d.snapshot()
    choose(app, "select")
    d.selection.set_selected([0])
    moved = translate_segments([line()], 0, 100)
    assert d.selection.apply_transformed(moved)
    assert d.annotations()[0]["y1"] == 300 and d.annotations()[1] == marker()
    d.undo()
    assert d.snapshot() == original
    d.selection.set_selected([0])
    assert d.selection.apply_rotation(90, (350, 300))
    assert supported(d.annotations()[0], d.segments())
    d.undo()
    assert d.snapshot() == original
    d.selection.set_selected([0])
    assert d.selection.delete_selected()
    assert not d.segments() and d.annotations() == [marker()]
    d.undo()
    assert d.snapshot() == original


def test_annotation_move_rotation_and_cancel_never_edit_the_wall(editor):
    app, d = editor
    d.store([line()], annotations=[aperture(), marker()])
    choose(app, "annotation_select")
    d.annotation.select((1,))
    before = d.snapshot()
    d.annotation.last_pointer = QPointF(at(app, 150, 150))
    QTest.keyClick(app, Qt.Key.Key_M)
    move(app.floorplan_view, at(app, 250, 250))
    assert d.snapshot() == before and d.annotation.moving
    QTest.keyClick(app, Qt.Key.Key_Escape)
    assert d.snapshot() == before and not d.annotation.moving
    d.annotation.select((1,))
    QTest.keyClick(app, Qt.Key.Key_R)
    assert d.annotations()[1]["points"] != marker()["points"] and d.segments() == [line()]
    d.undo()
    d.annotation.select((0,))
    QTest.keyClick(app, Qt.Key.Key_R)
    assert d.annotations()[0]["side"] == -1
    d.annotation.last_pointer = QPointF(at(app, 275, 200))
    QTest.keyClick(app, Qt.Key.Key_M)
    target = at(app, 450, 200)
    move(app.floorplan_view, target)
    QTest.mouseClick(app.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=target)
    assert d.segments() == [line()] and d.annotations()[0]["x1"] > 350


@pytest.mark.parametrize("system", ["metric", "imperial"])
def test_properties_units_and_pose_preservation(editor, system):
    app, d = editor
    app.measurement_system = system
    original = aperture()
    dialog = AnnotationDialog(d.annotation, original)
    try:
        dialog.width.setValue(3)
        dialog.variant.setCurrentIndex(dialog.variant.findData("double"))
        result = dialog.properties()
        meters = 3 if system == "metric" else .9144
        assert math.dist(*annotation_points(result)) == pytest.approx(meters * app.get_px_per_meter())
        assert (result["x1"] + result["x2"]) / 2 == 275 and result["variant"] == "double"
    finally:
        dialog.deleteLater()


def test_annotations_survive_save_png_reopen_and_clear_on_external_import(editor, tmp_path):
    app, d = editor
    d.store([line()], annotations=[aperture(), marker()])
    app.plan_tools.set_open(False)
    path = tmp_path / "annotations.csv"
    app.session.csv_file = str(path)
    with patch("qt_ui.qt_session_workflow.QMessageBox.warning") as error:
        assert app.save_survey(), error.call_args
    assert app.open_survey(str(path))
    assert d.annotations() == [aperture(), marker()] and d.segments() == [line()]
    with Image.open(path.with_suffix(".png")) as image:
        assert image.convert("RGB").getpixel((275, 200)) == (255, 255, 255)
    external = tmp_path / "external.png"
    Image.new("RGB", (900, 600), "white").save(external)
    app.load_plan_file(str(external), save_metadata=True)
    assert PLAN_ANNOTATIONS_KEY not in app.session.metadata and not d.annotation.items


def test_live_worker_copies_annotation_paths_and_masks_old_baked_ink(qt_app, tmp_path):
    from maps.config import MapConfig
    from qt_ui.qt_live_map import LiveMapRenderWorker
    path = tmp_path / "plan.png"
    render_plan_drawing(Image.new("RGB", (900, 600), "white"), [line()]).save(path)
    annotations = [aperture(), marker()]
    worker = LiveMapRenderWorker([], str(path), MapConfig(), {}, plan_segments=[line()], plan_annotations=annotations)
    annotations[1]["points"].clear()
    with patch("qt_ui.qt_live_map.render_live_map_payload", return_value={}) as render:
        worker.run()
    image = render.call_args.kwargs["bg_image"]
    assert image.getpixel((275, 200)) == (255, 255, 255)
    assert any(color == (217, 119, 6) for _count, color in image.getcolors(900 * 600))


def test_failed_save_preserves_annotation_metadata_and_previous_files(editor, tmp_path):
    app, d = editor
    d.store([line()], annotations=[aperture(), marker()])
    app.plan_tools.set_open(False)
    path = tmp_path / "rollback.csv"
    app.session.csv_file = str(path)
    metadata = deepcopy(app.session.metadata)
    with patch.object(app.session, "save", side_effect=OSError("disk full")), patch("qt_ui.qt_session_workflow.QMessageBox.warning"):
        assert not app.save_survey()
    assert app.session.metadata == metadata and not path.exists() and not path.with_suffix(".png").exists()


def test_marker_marquee_ignores_empty_space_inside_its_bounding_box(editor):
    app, d = editor
    d.store([line()], annotations=[marker(points=[[100, 100], [100, 400], [400, 400]])])
    choose(app, "annotation_select")
    drag(app.floorplan_view, at(app, 250, 200), at(app, 300, 250))
    assert not d.annotation.selected and d.segments() == [line()]
