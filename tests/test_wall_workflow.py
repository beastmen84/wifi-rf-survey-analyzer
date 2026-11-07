"""Wall UI, annotations, history, permissions, exports and saved-plan regression."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog

from qt_ui.qt_wall_properties import WallPropertiesDialog, open_wall_properties
from qt_ui.qt_plan_printing import clean_plan_image, clean_plan_source
from survey.plan_layers import active_layer, add_layer, move_selection, visible_layers
from survey.plan_annotations import visible_wall_segments
from survey.plan_clearances import ClearanceIndex
from survey.plan_faces import RegionPicker
from survey.plan_geometry import translate_segments
from survey.plan_erasing import nearest_segment, intersecting_segments
from survey.wall_geometry import wall_solids
from survey.wall_layout import plan_wall_layout
from tests.test_wall_thickness import rectangle, state, BOUNDS
from tests.test_network_plan_symbols import symbol, ap
from tests.test_plan_annotations import aperture, at
from tests.test_rectangle_design import editor
from tests.test_capture_adapter import window, qt_app


def select_all(app, d):
    app.plan_tools.select_tool("select")
    d.selection.set_selected(range(len(d.segments() or [])), (), range(len(d.curves())))


@pytest.mark.parametrize("action", ["apply", "cancel", "stale"])
def test_wall_dialog_is_transactional_and_history_restores_original(editor, action):
    app, d = editor
    d.store(rectangle()+rectangle(x=300))
    select_all(app, d)
    before, history = deepcopy(app.session.metadata), len(d.undo_stack)
    assert app.plan_tools.wall_button.isEnabled()
    def edit(dialog):
        assert dialog.candidate is not None
        assert dialog.result.changed_positions
        if action == "stale":
            app.session.metadata["notes"] = "changed during dialog"
        return QDialog.DialogCode.Rejected if action == "cancel" else QDialog.DialogCode.Accepted
    with patch.object(WallPropertiesDialog, "exec", edit), patch("qt_ui.qt_wall_properties.QMessageBox.warning"):
        assert open_wall_properties(app) == (action == "apply")
    if action == "apply":
        assert len(d.undo_stack) == history+1
        assert all(l.get("wall") for l in d.segments())
        d.undo()
        assert not any(l.get("wall") for l in d.segments())
        assert len(d.segments()) == 7
        d.redo()
        assert len(d.segments()) == 8
    elif action == "cancel":
        assert app.session.metadata == before and len(d.undo_stack) == history
    else:
        assert app.session.metadata["notes"] == "changed during dialog"
        assert not any(l.get("wall") for l in d.segments()) and len(d.undo_stack) == history
    assert not d.wall_dialog_open


@pytest.mark.parametrize("protection", ["measurements", "mask", "legacy_ap"])
def test_room_separation_protects_existing_spatial_data(editor, protection):
    app, d = editor
    d.store(rectangle()+rectangle(x=300))
    select_all(app, d)
    if protection == "legacy_ap":
        app.session.set_ap_groups([ap(position=dict(x=400, y=200))], update_memory=False)
    before = deepcopy(app.session.metadata)
    with (patch.object(app.session, "get_points", return_value=[{}] if protection == "measurements" else []),
          patch.object(app.floorplan_view, "has_boundaries_mask", return_value=protection == "mask")):
        dialog = WallPropertiesDialog(app)
        assert dialog.candidate is None and not dialog.apply_button.isEnabled()
        assert dialog.error == ("wall_convert_aps" if protection == "legacy_ap" else "wall_survey_lock")
        dialog.reject()
        dialog.deleteLater()
    assert app.session.metadata == before


def test_external_offsets_are_allowed_after_capture_because_coordinates_stay_fixed(editor):
    app, d = editor
    d.store(rectangle())
    select_all(app, d)
    with patch.object(app.session, "get_points", return_value=[{}]):
        dialog = WallPropertiesDialog(app)
        assert dialog.candidate and not dialog.result.changed_positions
        dialog.deleteLater()


def test_bound_ap_symbols_and_apertures_follow_room_without_losing_identity(editor):
    app, d = editor
    app.session.set_ap_groups([ap()], update_memory=False)
    objects = [symbol("wifi_ap", "AP", cx=400, cy=200, ap_group="ap-a"),
               symbol(identity="point", cx=400, cy=240, number=3),
               aperture("door", x1=300, y1=170, x2=300, y2=220, side=-1)]
    d.store(rectangle()+rectangle(x=300), annotations=objects)
    select_all(app, d)
    old = app.session.get_ap_groups()[0]["position"]
    with patch.object(WallPropertiesDialog, "exec", return_value=QDialog.DialogCode.Accepted):
        assert open_wall_properties(app)
    shift = .2*app.get_px_per_meter()
    assert next(a for a in d.annotations() if a["id"] == "AP")["cx"] == pytest.approx(400+shift)
    assert app.session.get_ap_groups()[0]["position"]["x"] == pytest.approx(old["x"]+shift)
    assert next(a for a in d.annotations() if a["id"] == "point")["number"] == 3
    assert next(a for a in d.annotations() if a["kind"] == "door")["x1"] == pytest.approx(300+shift)
    d.undo()
    assert app.session.get_ap_groups()[0]["position"] == old


@pytest.mark.parametrize("kind,variant", [("door", "single"), ("door", "double"), ("door", "sliding"), ("door", "frame"), ("window", "single")])
@pytest.mark.parametrize("angle", [0, 35, 90])
def test_openings_cut_entire_depth_and_opposite_face(qt_app, kind, variant, angle):
    from survey.plan_annotations import transform_annotations
    from survey.plan_geometry import rotate_degrees
    base = state(rectangle()+rectangle(x=300), annotations=[aperture(kind, variant=variant, x1=300, y1=170, x2=300, y2=220, side=-1)])
    result = plan_wall_layout(base, range(len(base["segments"])), (), 20, BOUNDS)
    lines = translate_segments(rotate_degrees(result.state["segments"], angle, (300, 200)), 200, 200)
    opening = transform_annotations(result.state["annotations"], angle, (300, 200), 200, 200)
    cut = wall_solids(lines, [], opening)
    point = transform_annotations([symbol(cx=310, cy=195)], angle, (300, 200), 200, 200)[0]
    assert not any(p.contains(QPointF(point["cx"], point["cy"])) for _c, p in cut)
    visible = visible_wall_segments(lines, opening)
    from survey.planar_geometry import point_projection
    for a in opening:
        center = ((a["x1"]+a["x2"])/2, (a["y1"]+a["y2"])/2)
        assert all(sum((center[i]-point_projection(center, (l["x1"], l["y1"]), (l["x2"], l["y2"]))[i])**2 for i in (0, 1)) > 1e-7 for l in visible)


def test_walls_render_save_reopen_and_hidden_layers_export_consistently(editor, tmp_path):
    app, d = editor
    built = plan_wall_layout(state(rectangle()), range(4), (), 20, BOUNDS).state
    d.store(built["segments"])
    assert clean_plan_image(d.view, app.session.metadata).pixelColor(90, 200).name() == "#d1d5db"
    select_all(app, d)
    d.selection.apply_rotation(90)
    assert all(s["wall"]["width"] == 20 for s in d.segments())
    doc = add_layer(d.layer_document(), "Walls")
    doc["active"] = "0"
    target = doc["layers"][-1]["id"]
    doc = move_selection(doc, target, dict(segments=range(4), curves=(), annotations=(), labels=()))
    d.change_layers(doc)
    assert clean_plan_image(d.view, app.session.metadata).pixelColor(90, 200).name() == "#d1d5db"
    doc["layers"][-1]["visible"] = False
    d.change_layers(doc)
    assert clean_plan_image(d.view, app.session.metadata).pixelColor(90, 200).name() == "#ffffff"
    path = tmp_path/"walls.csv"
    app.session.csv_file = str(path)
    assert app.save_survey() and app.open_survey(str(path))
    hidden = d.layer_document()["layers"][-1]
    assert not hidden["visible"] and all(l["wall"]["width"] == 20 for l in hidden["drawing"]["segments"])
    assert not visible_layers(app.session.metadata)["layers"][-1]["drawing"]["segments"]


def test_thick_body_is_pickable_and_reports_outer_clearance_and_overlap(qt_app):
    l = dict(x1=100, y1=100, x2=500, y2=100, color="#263238", wall=dict(width=20, side=1))
    assert nearest_segment([l], 200, 115, 1) == 0
    assert intersecting_segments([l], 190, 110, 210, 116) == (0,)
    index = ClearanceIndex([l])
    assert index.query(symbol(cx=200, cy=150, width=20, height=20))[0].distance == pytest.approx(20)
    assert index.query(symbol(cx=200, cy=110, width=2, height=2))[0].overlap


def test_failed_move_outside_physical_extent_leaves_history_and_model_unchanged(editor):
    app, d = editor
    built = plan_wall_layout(state(rectangle()), range(4), (), 20, BOUNDS).state
    d.store(built["segments"])
    select_all(app, d)
    before, history = d.segments(), len(d.undo_stack)
    assert not d.selection.apply_transformed(translate_segments(before, -95, 0))
    assert d.segments() == before and len(d.undo_stack) == history
    assert app.status.currentMessage() == app.tr("wall_outside")


def test_selecting_physical_body_and_deleting_keeps_annotation_selection_separate(editor):
    app, d = editor
    built = plan_wall_layout(state(rectangle()), range(4), (), 20, BOUNDS).state
    d.store(built["segments"], annotations=[symbol(cx=200, cy=200)])
    app.plan_tools.select_tool("select")
    QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 90, 180))
    assert len(d.selection.selected) == 1
    QTest.keyClick(app, Qt.Key.Key_Delete)
    assert len(d.segments()) == 3 and len(d.annotations()) == 1
    d.undo()
    assert len(d.segments()) == 4


def test_load_plan_and_locked_layer_cannot_open_wall_editor(editor):
    app, d = editor
    d.store(rectangle())
    select_all(app, d)
    app.session.metadata["plan_mode"] = "load"
    assert not open_wall_properties(app)
    app.session.metadata["plan_mode"] = "draw"
    doc = d.layer_document()
    active_layer(doc)["locked"] = True
    d.change_layers(doc)
    assert not open_wall_properties(app)


def test_shared_wall_delete_removes_both_faces_and_closes_the_outer_perimeter(editor):
    app, d = editor
    built = plan_wall_layout(state(rectangle()+rectangle(x=300)), range(7), (), 20, BOUNDS).state
    d.store(built["segments"])
    app.plan_tools.select_tool("select")
    QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 310, 200))
    assert len(d.selection.selected) == 2
    QTest.keyClick(app, Qt.Key.Key_Delete)
    rooms = RegionPicker(d.segments(), []).records
    assert len(rooms) == 1 and rooms[0][1].area == pytest.approx(84000)
    assert all(line.get("wall") for line in d.segments())
    d.undo()
    assert len(RegionPicker(d.segments(), []).records) == 2


def test_t_shared_faces_are_split_on_both_sides_and_can_be_deleted_independently(qt_app):
    from survey.wall_editing import paired_lines, remove_wall_faces
    source = state(rectangle(w=400)+rectangle(y=300)+rectangle(x=300, y=300))
    result = plan_wall_layout(source, range(len(source["segments"])), (), 20, BOUNDS)
    lines = result.state["segments"]
    index = nearest_segment(lines, 200, 310, 1)
    assert len(paired_lines(lines, index)) == 2
    remaining = remove_wall_faces(lines, (index,))
    rooms = RegionPicker(remaining, []).records
    assert len(rooms) == 2
    assert sorted(r.area for _p, r in rooms) == pytest.approx([40000, 123800])


def test_changing_one_shared_piece_retains_other_wall_depths_and_room_areas(qt_app):
    source = state(rectangle(w=400)+rectangle(y=300)+rectangle(x=300, y=300))
    result = plan_wall_layout(source, range(len(source["segments"])), (), 20, BOUNDS)
    lines = result.state["segments"]
    index = nearest_segment(lines, 200, 310, 1)
    changed = plan_wall_layout(result.state, (index,), (), 25, BOUNDS)
    assert {s["wall"]["width"] for s in changed.state["segments"]} == {20, 25}
    assert sorted(r.area for _p, r in RegionPicker(changed.state["segments"], []).records) == pytest.approx([40000, 40000, 80000])


def test_imperial_property_review_preserves_exact_existing_depth(editor):
    app, d = editor
    built = plan_wall_layout(state(rectangle()+rectangle(x=300)), range(7), (), 13.123456, BOUNDS).state
    d.store(built["segments"])
    select_all(app, d)
    app.measurement_system = "imperial"
    dialog = WallPropertiesDialog(app)
    assert not dialog.result.changed_positions
    assert {s["wall"]["width"] for s in dialog.result.state["segments"]} == {13.123456}
    dialog.thickness_spin.setValue(dialog.thickness_spin.value()+.1)
    assert dialog.result.changed_positions
    dialog.deleteLater()
