"""Rack inventories survive real editor workflows and generate usable legends."""
from copy import deepcopy
import json
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLineEdit

from survey.rack_inventory import validate_rack, inventory_tables, validate_inventory_totals
from survey.plan_annotations import (validate_annotations, transform_annotations, encode_annotations,
    drawing_annotations, PLAN_ANNOTATIONS_KEY)
from survey.plan_layers import read_layers, active_layer, add_layer, validate_document
from qt_ui.qt_rack_inventory import RackConfigurationDialog
from qt_ui.qt_plan_objects import ObjectAnnotationDialog
from qt_ui.qt_plan_legend import PlanLegendDialog, export_legend_tables
from qt_ui.qt_legend_pages import legend_pages
from qt_ui.qt_plan_jpeg import render_legend_image
from tests.test_network_plan_symbols import symbol
from tests.test_rectangle_design import editor as editor
from tests.test_capture_adapter import window as window, qt_app as qt_app


def rack(identity='rack-a', **changes):
    return symbol('rack', identity, rack=dict(name='Main rack', switches=[dict(ports=['AP piano 1', 'αβ 🛜']),
                                                                          dict(ports=['Uplink'])]), **changes)


@pytest.mark.parametrize('value', [None, [], {'count': 1}, {'name': 3}, {'name': 'a\nb'},
    {'name': 'x'*81}, {'switches': {}}, {'switches': [{}]}, {'switches': [{'ports': 'x'}]},
    {'switches': [{'ports': [1]}]}, {'switches': [{'ports': ['a\0b']}]},
    {'switches': [{'ports': ['x'*2001]}]}, {'switches': [{'ports': ['']*513}]},
    {'switches': [{'ports': []}]*33}, {'switches': [{'ports': ['']*512}]*9}])
def test_invalid_inventory_is_rejected(value):
    with pytest.raises(ValueError):
        validate_rack(value)


def test_optional_inventory_is_canonical_and_never_aliases_input():
    assert validate_rack({}) == validate_rack({'name': ' ', 'switches': []}) == {}
    value = {'name': ' Rack A ', 'switches': [{'ports': ['  α\nβ  ', '']}, {'ports': []}]}
    original = deepcopy(value)
    validated = validate_rack(value)
    assert validated['name'] == 'Rack A'
    validated['switches'][0]['ports'][0] = 'changed'
    assert value == original
    item = rack()
    assert 'number' not in item
    assert json.loads(encode_annotations([item]))['version'] == 2
    metadata = {'_generated_floorplan': '1', PLAN_ANNOTATIONS_KEY: encode_annotations([item])}
    assert drawing_annotations(metadata) == [item]
    assert read_layers(metadata)['version'] == 3
    assert json.loads(encode_annotations([symbol('rack')]))['version'] == 1
    assert read_layers({})['version'] == 1
    for version in (1, 2, 3):
        assert validate_document(dict(read_layers({}), version=version))['version'] == 1
    with pytest.raises(ValueError, match='rack symbol'):
        validate_annotations([dict(symbol('square'), rack=value)])


@pytest.mark.parametrize('limit', ['switches', 'ports', 'text'])
def test_document_inventory_budgets_cover_multiple_racks(limit):
    items = [{'rack': {'switches': [{'ports': ['']*512}]*8}}]*5
    if limit == 'switches':
        items = [{'rack': {'switches': [{'ports': []}]*32}}]*17
    if limit == 'text':
        items = [{'rack': {'switches': [{'ports': ['x'*2000]*501}]}}]
    with pytest.raises(ValueError, match='rack_document_limit'):
        validate_inventory_totals(items)


def test_rack_configuration_retains_prefixes_until_accepted_and_cancels_without_mutation(editor):
    app, _d = editor
    original = rack()['rack']
    before = deepcopy(original)
    dialog = RackConfigurationDialog(app, original)
    try:
        dialog.spins[0].setValue(1)
        dialog.count.setValue(1)
        dialog.count.setValue(2)
        dialog.spins[0].setValue(3)
        assert dialog.properties()['switches'] == [{'ports': ['AP piano 1', 'αβ 🛜', '']}, {'ports': ['Uplink']}]
        dialog.count.setValue(0)
        assert dialog.properties() == {'name': 'Main rack', 'switches': []}
        dialog.name.clear()
        assert dialog.properties() == {}
        dialog.count.setValue(9)
        for spin in dialog.spins:
            spin.setValue(512)
        assert not dialog.ok.isEnabled()
        dialog.reject()
        assert original == before
    finally:
        dialog.deleteLater()


def test_object_properties_show_rack_fields_only_for_racks(editor):
    app, d = editor
    dialog = ObjectAnnotationDialog(d, rack())
    try:
        assert not dialog.rack_row.isHidden() and dialog.rack_count.value() == 2
        dialog.rack_count.setValue(1)
        assert dialog.properties()['rack']['switches'] == [{'ports': ['AP piano 1', 'αβ 🛜']}]
        dialog.choose_variant('circle')
        assert dialog.rack_row.isHidden() and 'rack' not in dialog.properties()
        dialog.choose_variant('rack')
        with patch.object(RackConfigurationDialog, 'exec', return_value=QDialog.DialogCode.Rejected):
            dialog.configure_rack()
        assert dialog.rack_value == rack()['rack']
    finally:
        dialog.deleteLater()


def test_inventory_follows_geometry_layers_history_and_real_survey_roundtrip(editor, tmp_path):
    app, d = editor
    item = rack()
    d.store([], annotations=[item])
    moved = transform_annotations([item], angle=35, pivot=(450, 300), dx=20, dy=30)
    assert moved[0]['rack'] == item['rack']
    assert d.apply_edit([], annotations=moved)
    doc = add_layer(d.layer_document(), 'Network equipment')
    doc['layers'][0]['drawing']['annotations'] = []
    active_layer(doc)['drawing']['annotations'] = moved
    assert d.change_layers(doc)
    assert d.layer_document()['version'] == 3
    before = deepcopy(d.layer_document())
    path = tmp_path / 'rack-network.csv'
    app.session.csv_file = str(path)
    assert app.save_survey() and app.open_survey(str(path))
    assert d.layer_document() == before
    assert d.annotations()[0]['rack'] == item['rack']


def test_inventory_legend_edit_cancel_save_undo_and_switch_change(editor, qt_app):
    app, d = editor
    d.store([], annotations=[rack()])
    before = deepcopy(app.session.metadata)
    before_document = deepcopy(d.layer_document())
    dialog = PlanLegendDialog(app)
    panel = dialog.inventory
    assert panel.tree.topLevelItemCount() == 1 and panel.table.rowCount() == 2
    assert not panel.table.item(0, 0).flags() & Qt.ItemFlag.ItemIsEditable
    panel.table.item(0, 1).setText('Cancelled')
    dialog.reject(); dialog.deleteLater()
    assert app.session.metadata == before
    dialog = PlanLegendDialog(app)
    dialog.show()
    dialog.tabs.setCurrentWidget(dialog.inventory)
    qt_app.processEvents()
    panel = dialog.inventory
    # Exercise an active delegate editor, not just programmatic item changes.
    cell = panel.table.item(0, 1)
    panel.table.setCurrentItem(cell); panel.table.editItem(cell)
    qt_app.processEvents()
    edit = panel.table.findChild(QLineEdit)
    assert edit is not None
    edit.setText('Camera <PoE> & uplink 🛜')
    panel.tree.setCurrentItem(panel.tree.topLevelItem(0).child(1))
    assert panel.table.rowCount() == 1 and panel.table.item(0, 0).text() == '1'
    panel.table.item(0, 1).setText('Core uplink')
    dialog.show_hidden.setChecked(True)
    dialog.save()
    assert dialog.result() == QDialog.DialogCode.Accepted
    dialog.deleteLater()
    saved = d.annotations()[0]['rack']['switches']
    assert saved == [{'ports': ['Camera <PoE> & uplink 🛜', 'αβ 🛜']}, {'ports': ['Core uplink']}]
    d.undo()
    assert d.layer_document() == before_document
    d.redo()
    assert d.annotations()[0]['rack']['switches'] == saved


def test_hidden_and_locked_racks_are_readonly_and_excluded_from_exports(editor):
    app, d = editor
    d.store([], annotations=[rack()])
    doc = add_layer(d.layer_document(), 'Hidden rack')
    active_layer(doc)['drawing']['annotations'] = [rack('rack-b', cx=600)]
    active_layer(doc).update(visible=False, locked=True)
    doc['layers'][0]['locked'] = True
    d.change_layers(doc)
    assert len([t for t in export_legend_tables(app.session) if t['kind'] == 'rack_ports']) == 2
    dialog = PlanLegendDialog(app)
    try:
        dialog.show_hidden.setChecked(True)
        panel = dialog.inventory
        assert panel.tree.topLevelItemCount() == 2
        for index in range(2):
            panel.tree.setCurrentItem(panel.tree.topLevelItem(index).child(0))
            assert not panel.table.item(0, 1).flags() & Qt.ItemFlag.ItemIsEditable
            panel.table.item(0, 1).setText('Must not save')
        dialog.save()
        assert all(a['rack']['switches'][0]['ports'][0] == 'AP piano 1'
                   for layer in d.layer_document()['layers'] for a in layer['drawing']['annotations'])
    finally:
        dialog.deleteLater()


def test_save_commits_active_port_editor_and_stale_edits_are_rejected(editor, qt_app):
    app, d = editor
    d.store([], annotations=[rack()])
    dialog = PlanLegendDialog(app)
    dialog.show(); dialog.tabs.setCurrentWidget(dialog.inventory); qt_app.processEvents()
    table = dialog.inventory.table
    table.setCurrentCell(1, 1); table.editItem(table.item(1, 1)); qt_app.processEvents()
    table.findChild(QLineEdit).setText('Direct save from editor')
    dialog.save(); dialog.deleteLater()
    assert d.annotations()[0]['rack']['switches'][0]['ports'][1] == 'Direct save from editor'
    dialog = PlanLegendDialog(app)
    dialog.inventory.table.item(0, 1).setText('Stale edit')
    app.session.metadata['notes'] = 'Concurrent change'
    before = deepcopy(app.session.metadata)
    with patch('qt_ui.qt_plan_legend.QMessageBox.warning') as warning:
        dialog.save()
    assert warning.called and app.session.metadata == before
    dialog.reject(); dialog.deleteLater()


def test_rack_ports_reach_actual_multipage_print_document(editor, tmp_path):
    from PySide6.QtCore import QMarginsF
    from PySide6.QtGui import QPageLayout, QPageSize
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPrintSupport import QPrinter
    from qt_ui.qt_plan_printing import clean_plan_source, paint_plan_page
    app, d = editor
    item = rack()
    item['rack']['switches'] = [{'ports': [f'Equipment {p} — αβ 🛜' for p in range(48)]}]
    d.store([], annotations=[item])
    output = tmp_path/'rack.pdf'
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setResolution(150); printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(output)); printer.setPageSize(QPageSize(QPageSize.PageSizeId.A5))
    printer.setPageMargins(QMarginsF(10,10,10,10), QPageLayout.Unit.Millimeter)
    tables = export_legend_tables(app.session)
    pages = legend_pages(tables,printer.width()*72/150,printer.height()*72/150,app.tr)
    assert len(pages)>1
    assert paint_plan_page(printer,clean_plan_source(d.view,app.session.metadata),app.get_px_per_meter(),tr=app.tr,legend=tables)
    document = QPdfDocument()
    try:
        assert document.load(str(output)) == QPdfDocument.Error.None_
        assert document.pageCount() == len(pages)+1
    finally:
        document.close()


def test_inventory_pagination_repeats_rack_switch_identity_and_keeps_all_ports(editor):
    app, d = editor
    item = rack()
    item['rack']['name'] = 'Rack di piano αβ ' * 4
    item['rack']['switches'] = [{'ports': [f'Port {p} — PoE 🔌 ' + 'desc '*20 for p in range(1, 49)]}, {'ports': []}]
    d.store([], annotations=[item])
    tables = inventory_tables(d.layer_document())
    assert len(tables) == 2 and [r['number'] for r in tables[0]['rows']] == list(range(1, 49))
    pages = legend_pages(tables, 340, 500, app.tr)
    rows = [b for page in pages for b in page if b['type'] == 'row']
    assert len(pages) > 2 and all(page[0]['type'] == 'header' for page in pages)
    assert all(b['y'] + b.get('height', 0) <= 478 for page in pages for b in page)
    actual = ''.join(''.join(b['description']) for b in rows)
    assert actual == ''.join(r['description'] for t in tables for r in t['rows']) + app.tr('rack_no_ports')
    assert not render_legend_image(pages[0], 'A4', False, 150, 1, len(pages), app.tr).isNull()
    # Tiny pages fail clearly instead of repeatedly generating empty pages.
    tiny = legend_pages(tables[:1], 120, 150, app.tr)
    assert tiny and all(any(b['type'] == 'row' for b in page) for page in tiny)
