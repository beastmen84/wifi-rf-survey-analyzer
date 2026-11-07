"""Network symbol numbering, AP binding/history, legacy conversion and legend data."""
from copy import deepcopy
import json
from unittest.mock import patch

from PIL import Image
import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog

from ap.groups import build_manual_ap_group, normalize_ap_position, merge_new_bssids_into_manual_groups
from ap.positioning import build_ap_position_map
from survey.plan_objects import object_default, NUMBERED_SYMBOLS
from survey.plan_annotations import validate_annotations, transform_annotations
from survey.plan_layers import read_layers, add_layer, active_layer, validate_document
from survey.plan_symbols import bind_ap, next_number, SYMBOL_STATE_KEY
from qt_ui.qt_plan_legend import PlanLegendDialog, export_legend_tables, open_plan_legend
from qt_ui.qt_ap_symbol_binding import ApSymbolDialog
from qt_ui.qt_plan_printing import clean_plan_image
from survey.plan_symbol_rendering import number_commands, SymbolNumberItem
from qt_ui.qt_live_map import build_ap_position_marker_infos
from tests.test_rectangle_design import editor
from tests.test_plan_annotations import choose, at
from tests.test_capture_adapter import window, qt_app


def symbol(variant="square", identity="s1", **changes):
    item = dict(object_default("symbol", 50, variant), id=identity, cx=450, cy=300)
    item.update(changes)
    return validate_annotations([item])[0]


def ap(identity="ap-a", **changes):
    item = build_manual_ap_group(identity, ["00:11:22:33:44:55" if identity == "ap-a" else "00:11:22:33:44:66"], alias="Reception")
    item.update(changes)
    return item


def test_new_markers_count_per_shape_across_layers_without_reusing_deleted_numbers(editor):
    app, d = editor
    choose(app, "symbol", symbol())
    for x in (300, 400):
        QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=at(app, x, 250))
    assert [a["number"] for a in d.annotations()] == [1, 2]
    app.layers_panel.add()
    choose(app, "symbol", symbol())
    QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 450, 350))
    assert d.annotations()[0]["number"] == 3
    assert d.apply_edit([], annotations=[])
    assert next_number(app.session.metadata, d.layer_document(), "square") == 4
    d.undo()
    assert d.annotations()[0]["number"] == 3
    choose(app, "symbol", symbol("circle"))
    QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 550, 350))
    assert d.annotations()[-1]["number"] == 1
    assert json.loads(app.session.metadata[SYMBOL_STATE_KEY])["next"]["square"] == 4


def test_numbering_can_be_disabled_for_a_new_marker(editor):
    app, d = editor
    choose(app, "symbol", dict(symbol(), _numbered=False))
    QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=at(app, 450, 300))
    assert "number" not in d.annotations()[0]


def test_legend_numbering_exhaustion_is_atomic(editor):
    app, d = editor
    d.store([], annotations=[symbol(identity="first"), symbol(identity="second", cx=550)])
    app.session.metadata[SYMBOL_STATE_KEY] = json.dumps(dict(version=1, next=dict(square=999999)))
    dialog = PlanLegendDialog(app)
    before = deepcopy(dialog.document), deepcopy(app.session.metadata)
    with patch("qt_ui.qt_plan_legend.QMessageBox.warning") as warning:
        dialog.number_unmarked()
    assert warning.called
    assert (dialog.document, app.session.metadata) == before
    dialog.deleteLater()


def test_ap_symbol_entry_point_rejects_loaded_plans(window):
    from qt_ui.qt_ap_symbol_binding import assign_ap_symbol
    from survey.store import SurveySession
    window.session = SurveySession()
    window.session.metadata["plan_mode"] = "load"
    with patch("qt_ui.qt_ap_symbol_binding.ApSymbolDialog") as dialog:
        assert not assign_ap_symbol(window, "ap-a")
    dialog.assert_not_called()
    before = deepcopy(window.session.metadata)
    assert not window.plan_tools.controller.change_layers(add_layer(read_layers(before), "Disabled"))
    assert window.session.metadata == before


def test_duplicate_numbers_and_ap_bindings_are_rejected_across_layers(editor):
    app, d = editor
    d.store([], annotations=[symbol(number=1)])
    doc = add_layer(d.layer_document(), "Upper")
    active_layer(doc)["drawing"]["annotations"] = [symbol(identity="s2", number=1)]
    before = deepcopy(app.session.metadata), deepcopy(d.undo_stack)
    with pytest.raises(ValueError):
        d.change_layers(doc)
    assert (app.session.metadata, d.undo_stack) == before
    doc["layers"][0]["drawing"]["annotations"] = [symbol("wifi_ap", "a", ap_group="ap-a")]
    active_layer(doc)["drawing"]["annotations"] = [symbol("wifi_ap", "b", ap_group="ap-a")]
    with pytest.raises(ValueError):
        validate_document(doc)


def test_legend_legacy_numbering_description_cancel_save_and_undo(editor):
    app, d = editor
    d.store([], annotations=[symbol(), symbol("circle", "circle1", cx=550)])
    assert not export_legend_tables(app.session)
    before = deepcopy(app.session.metadata)
    dialog = PlanLegendDialog(app)
    dialog.number_unmarked()
    assert len(dialog.tables) == 2
    assert not dialog.tables[0][0].item(0, 0).flags() & Qt.ItemFlag.ItemIsEditable
    dialog.tables[0][0].item(0, 1).setText("Desk sockets <A> & B")
    dialog.reject()
    dialog.deleteLater()
    assert app.session.metadata == before
    dialog = PlanLegendDialog(app)
    dialog.number_unmarked()
    dialog.tables[0][0].item(0, 1).setText("Desk sockets <A> & B")
    dialog.save()
    assert dialog.result() == QDialog.DialogCode.Accepted
    dialog.deleteLater()
    records = export_legend_tables(app.session)
    assert records[0]["rows"][0]["description"] == "Desk sockets <A> & B"
    d.undo()
    assert "number" not in d.annotations()[0]
    d.redo()
    assert d.annotations()[1]["description"] == "Desk sockets <A> & B"  # Square table follows circle.


def test_legend_filters_visibility_and_protects_locked_rows_and_stale_modal(editor):
    app, d = editor
    d.store([], annotations=[symbol(number=1)])
    d.change_layers(add_layer(d.layer_document(), "Hidden"))
    d.store([], annotations=[symbol(identity="s2", number=2)])
    doc = deepcopy(d.layer_document())
    active_layer(doc).update(visible=False, locked=True)
    d.change_layers(doc)
    assert len(export_legend_tables(app.session)[0]["rows"]) == 1
    dialog = PlanLegendDialog(app)
    dialog.show_hidden.setChecked(True)
    table, rows = dialog.tables[0]
    hidden_row = next(i for i, row in enumerate(rows) if row["id"] == "s2")
    assert not table.item(hidden_row, 1).flags() & Qt.ItemFlag.ItemIsEditable
    app.session.metadata["notes"] = "Changed during dialog"
    before = deepcopy(app.session.metadata)
    with patch("qt_ui.qt_plan_legend.QMessageBox.warning") as warning:
        dialog.save()
    assert warning.called and app.session.metadata == before
    dialog.reject()
    dialog.deleteLater()


def test_bound_ap_moves_with_exact_symbol_center_and_history_preserves_other_ap_metadata(editor):
    app, d = editor
    app.session.set_ap_groups([ap()], update_memory=False)
    d.store([], annotations=[symbol("wifi_ap", cx=450.375, cy=300.625)])
    assert d.change_layers(bind_ap(d.layer_document(), "s1", "ap-a"))
    position = app.session.get_ap_groups()[0]["position"]
    assert position == dict(x=450.375, y=300.625, symbol_id="s1")
    assert build_ap_position_map(app.session.get_ap_groups())["ap-a"] == (450.375, 300.625)
    assert not d.view.ap_marker_items
    assert not build_ap_position_marker_infos(app.session.get_ap_groups(), {}, {})
    moved = transform_annotations(d.annotations(), dx=15.25, dy=-10.125)
    assert d.apply_edit([], annotations=moved)
    assert app.session.get_ap_groups()[0]["position"]["x"] == 465.625
    groups = app.session.get_ap_groups()
    groups[0]["alias"] = "Renamed after move"
    app.session.set_ap_groups(groups, update_memory=False)
    app.refresh_session_labels()
    d.undo()
    group = app.session.get_ap_groups()[0]
    assert group["position"] == position and group["alias"] == "Renamed after move"
    assert d.annotations()[0]["ap_label"] == "Renamed after move"
    d.redo()
    assert app.session.get_ap_groups()[0]["position"]["x"] == 465.625


def test_deleting_bound_symbol_clears_position_and_undo_restores_binding(editor):
    app, d = editor
    app.session.set_ap_groups([ap()], update_memory=False)
    d.store([], annotations=[symbol("wifi_ap")])
    d.change_layers(bind_ap(d.layer_document(), "s1", "ap-a"))
    d.apply_edit([], annotations=[])
    group = app.session.get_ap_groups()[0]
    assert not group.get("position") and group["position_cleared"]
    rebuilt = merge_new_bssids_into_manual_groups([group], [])
    assert rebuilt[0]["position_cleared"]
    d.undo()
    group = app.session.get_ap_groups()[0]
    assert group["position"]["symbol_id"] == "s1" and "position_cleared" not in group
    assert d.annotations()[0]["ap_group"] == "ap-a"


def test_binding_is_one_to_one_and_hidden_layers_keep_operational_positions(editor):
    app, d = editor
    app.session.set_ap_groups([ap(), ap("ap-b")], update_memory=False)
    d.store([], annotations=[symbol("wifi_ap", "s1"), symbol("wifi_ap", "s2", cx=550)])
    d.change_layers(bind_ap(d.layer_document(), "s1", "ap-a"))
    d.change_layers(bind_ap(d.layer_document(), "s2", "ap-b"))
    with pytest.raises(ValueError):
        bind_ap(d.layer_document(), "s2", "ap-a")
    doc = add_layer(d.layer_document(), "Unused upper")
    doc["layers"][0]["locked"] = True
    d.change_layers(doc)
    before = deepcopy(app.session.get_ap_groups())
    assert build_ap_position_map(before).keys() == {"ap-a", "ap-b"}
    assert not export_legend_tables(app.session)[0]["rows"][0]["number"]
    assert app.session.get_ap_groups() == before


def test_group_deletion_unbinds_symbol_without_deleting_its_geometry(editor):
    app, d = editor
    app.session.set_ap_groups([ap()], update_memory=False)
    d.store([], annotations=[symbol("wifi_ap")])
    d.change_layers(bind_ap(d.layer_document(), "s1", "ap-a"))
    app.session.set_ap_groups([], update_memory=False)
    app.refresh_session_labels()
    assert len(d.annotations()) == 1 and "ap_group" not in d.annotations()[0]
    assert "ap_label" not in d.annotations()[0]


@pytest.mark.parametrize("action", ["bind", "convert", "cancel", "stale"])
def test_draw_ap_action_uses_symbol_dialog_and_can_convert_old_coordinates(editor, action):
    app, d = editor
    app.session.set_ap_groups([ap(position=dict(x=400, y=300))], update_memory=False)
    if action != "convert":
        d.store([], annotations=[symbol("wifi_ap")])
    before = deepcopy(app.session.metadata)
    def choose_symbol(dialog):
        dialog.selected_id = "s1"
        dialog.action = "convert" if action == "convert" else "bind"
        if action == "stale":
            app.session.metadata["notes"] = "Changed"
        return QDialog.DialogCode.Rejected if action == "cancel" else QDialog.DialogCode.Accepted
    with patch.object(ApSymbolDialog, "exec", choose_symbol):
        result = app.start_ap_positioning("ap-a")
    if action in ("cancel", "stale"):
        assert not result and app.session.get_ap_groups()[0]["position"] == dict(x=400, y=300)
        if action == "cancel":
            assert app.session.metadata == before
    else:
        assert result and app.session.get_ap_groups()[0]["position"].get("symbol_id")
        if action == "convert":
            assert d.annotations()[0]["cx"] == 400
            d.undo()
            assert app.session.get_ap_groups()[0]["position"] == dict(x=400, y=300)


def test_load_plan_keeps_direct_ap_picking_and_has_no_legend(editor, tmp_path):
    app, d = editor
    source = tmp_path / "loaded.png"
    Image.new("RGB", (900, 600), "white").save(source)
    app.load_plan_file(str(source), save_metadata=True)
    app.session.set_ap_groups([ap()], update_memory=False)
    app.refresh_session_labels()
    assert app.legend_button.isHidden() and not open_plan_legend(app) and not export_legend_tables(app.session)
    with patch.object(app.floorplan_view, "start_ap_position_pick", return_value=True) as pick:
        assert app.start_ap_positioning("ap-a")
    pick.assert_called_once()
    assert normalize_ap_position(dict(x=10.4, y=11.6)) == dict(x=10, y=12)


@pytest.mark.parametrize("variant", NUMBERED_SYMBOLS)
def test_number_commands_fit_shape_and_small_badges_remain_readable(editor, variant):
    app, d = editor
    item = symbol(variant, number=123, width=100, height=100)
    commands = number_commands(item, 10, d.view.scene.sceneRect())
    assert len(commands) == 1
    assert commands[0][0].boundingRect().height() >= 10
    tiny = symbol(variant, number=999999, cx=2, cy=2, width=2, height=2)
    commands = number_commands(tiny, 11, d.view.scene.sceneRect())
    assert len(commands) == 3 and commands[-1][0].boundingRect().height() == pytest.approx(11)
    assert d.view.scene.sceneRect().contains(commands[-1][0].boundingRect())
    d.store([], annotations=[item])
    groups = [c for c in d.annotation.items[0].childItems() if isinstance(c, SymbolNumberItem)]
    assert len(groups) == 1
    image = clean_plan_image(d.view, app.session.metadata)
    assert not image.isNull()
    children = groups[0].childItems()
    for zoom in (.25, 1, 3):
        d.view.set_zoom(zoom)
        assert groups[0].last[0] > 0
        assert groups[0].childItems() == children
        assert all(groups[0].boundingRect().contains(child.boundingRect()) for child in children if child.isVisible())


def test_clicking_external_number_badge_selects_the_symbol_at_low_zoom(editor):
    app, d = editor
    d.store([], annotations=[symbol(number=12345, width=2, height=2)])
    choose(app, "annotation_select")
    d.view.set_zoom(.4)
    labels = [child for child in d.annotation.items[0].childItems() if isinstance(child, SymbolNumberItem)]
    label = labels[0]
    bubble = label.childItems()[1]
    point = label.deviceTransform(d.view.viewportTransform()).map(bubble.path().boundingRect().center())
    source = d.view.mapFromScene(QPointF(450, 300))
    assert 5 < (point-QPointF(source)).manhattanLength() < 150
    QTest.mouseClick(d.view.viewport(), Qt.MouseButton.RightButton, pos=point.toPoint())
    assert d.annotation.selected == (0,)


def test_hidden_ap_layer_keeps_position_and_save_roundtrip_keeps_numbers_links_and_description(editor, tmp_path):
    app, d = editor
    app.session.set_ap_groups([ap()], update_memory=False)
    d.change_layers(add_layer(d.layer_document(), "Equipment"))
    d.store([], annotations=[symbol(number=22, description="Ethernet 🔌"),
                              symbol("wifi_ap", "ap-symbol", cx=500.125, cy=350.875)])
    d.change_layers(bind_ap(d.layer_document(), "ap-symbol", "ap-a"))
    doc = deepcopy(d.layer_document())
    active_layer(doc)["visible"] = False
    d.change_layers(doc)
    assert not export_legend_tables(app.session)
    position = app.session.get_ap_groups()[0]["position"]
    assert build_ap_position_map(app.session.get_ap_groups())["ap-a"] == (500.125, 350.875)
    path = tmp_path / "network.csv"
    app.session.csv_file = str(path)
    assert app.save_survey() and app.open_survey(str(path))
    assert app.session.get_ap_groups()[0]["position"] == position
    assert d.annotations()[0]["description"] == "Ethernet 🔌" and d.annotations()[0]["number"] == 22
    assert next_number(app.session.metadata, d.layer_document(), "square") == 23
    assert not export_legend_tables(app.session)


def test_cleared_bound_position_is_not_resurrected_from_ap_memory(editor):
    from ap.memory import apply_memory_record_to_group, get_group_memory_update_fields
    app, d = editor
    group = ap(position_cleared=True)
    with patch("ap.memory.find_memory_position_for_map", return_value=dict(x=400, y=300)):
        apply_memory_record_to_group(group, dict(alias="Reception"), "plan.png")
        assert not group.get("position")
    bound = ap(position=dict(x=450.125, y=300.5, symbol_id="s1"))
    with patch("ap.memory.find_memory_position_for_map", return_value=dict(x=450, y=300)):
        fields = get_group_memory_update_fields(bound, records=[dict(bssids=bound["bssids"], alias="Reception")])
    assert "position" not in fields


def test_group_replacement_can_adopt_its_existing_symbol_without_duplicating_bindings(editor):
    app, d = editor
    app.session.set_ap_groups([ap()], update_memory=False)
    d.store([], annotations=[symbol("wifi_ap")])
    d.change_layers(bind_ap(d.layer_document(), "s1", "ap-a"))
    group = app.session.get_ap_groups()[0]
    group["group_id"] = "replacement"
    group["alias"] = "Renamed physical AP"
    app.session.set_ap_groups([group], update_memory=False)
    app.refresh_session_labels()
    assert d.annotations()[0]["ap_group"] == "replacement"
    assert d.annotations()[0]["ap_label"] == "Renamed physical AP"
    assert app.session.get_ap_groups()[0]["position"]["symbol_id"] == "s1"
