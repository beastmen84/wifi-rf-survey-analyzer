"""Automatic symbol tables and editable descriptions for drawn/imported plans."""
from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox,
    QHeaderView, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout,
    QStyledItemDelegate, QLineEdit, QAbstractItemDelegate)
from survey.plan_layers import read_layers
from survey.plan_mode import supports_plan_annotations
from survey.plan_symbols import legend_tables, symbols, sequences
from survey.plan_objects import NUMBERED_SYMBOLS
from survey.rack_inventory import rack_label


class DescriptionDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setMaxLength(2000)
        return editor


def finish_table_edit(table):
    editor = table.focusWidget()
    if isinstance(editor, QLineEdit):
        table.commitData(editor)
        table.closeEditor(editor, QAbstractItemDelegate.EndEditHint.NoHint)


def export_legend_tables(session):
    if session is None or not supports_plan_annotations(session.metadata):
        return []
    return legend_tables(read_layers(session.metadata), session.get_ap_groups(), visible_only=True)


class PlanLegendDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner, self.session = owner, owner.session
        self.token = deepcopy(self.session.metadata)
        self.document = deepcopy(read_layers(self.token))
        self.tables = []
        self.inventory = None
        self.setWindowTitle(owner.tr("plan_legend"))
        self.resize(owner.spx(780), owner.spx(600))
        layout = QVBoxLayout(self)
        hint = QLabel(owner.tr("legend_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.show_hidden = QCheckBox(owner.tr("legend_show_hidden"))
        self.show_hidden.toggled.connect(self.rebuild)
        layout.addWidget(self.show_hidden)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.empty = QLabel(owner.tr("legend_empty"))
        self.empty.setWordWrap(True)
        layout.addWidget(self.empty)
        self.number_existing = QPushButton(owner.tr("legend_number_existing"))
        self.number_existing.setObjectName("compactButton")
        self.number_existing.clicked.connect(self.number_unmarked)
        layout.addWidget(self.number_existing)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(owner.tr("save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(owner.tr("cancel"))
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.rebuild()

    def collect(self):
        if self.inventory is not None:
            self.inventory.finish_edit()
        for table, records in self.tables:
            finish_table_edit(table)
            for row, record in enumerate(records):
                layer = next(layer for layer in self.document["layers"] if layer["id"] == record["layer"])
                if layer["visible"] and not layer["locked"]:
                    item = next(a for a in layer["drawing"]["annotations"] if a["id"] == record["id"])
                    value = table.item(row, 1).text()[:2000]
                    if value or "description" in item:
                        item["description"] = value

    def rebuild(self, *_args):
        self.collect()
        self.tables = []
        while self.tabs.count():
            page = self.tabs.widget(0)
            self.tabs.removeTab(0)
            page.deleteLater()
        entries = legend_tables(self.document, self.session.get_ap_groups(), visible_only=not self.show_hidden.isChecked())
        inventory=[e for e in entries if e['kind']=='rack_ports']
        entries=[e for e in entries if e['kind']!='rack_ports']
        for index, entry in enumerate(entries, 1):
            table = QTableWidget(len(entry["rows"]), 2)
            table.setHorizontalHeaderLabels([self.owner.tr("legend_number" if entry["kind"] in NUMBERED_SYMBOLS else "annotation_symbol"),
                                              self.owner.tr("legend_description")])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(0, self.owner.spx(80 if entry["kind"] in NUMBERED_SYMBOLS else 220))
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.setItemDelegateForColumn(1, DescriptionDelegate(table))
            table.verticalHeader().hide()
            for row, record in enumerate(entry["rows"]):
                name = rack_label(record,self.owner.tr) if entry['kind']=='rack' else str(record["number"]) if record["number"] else record["ap"] or self.owner.tr("object_symbol_" + entry["kind"])
                reference = QTableWidgetItem(name)
                reference.setFlags(reference.flags() & ~Qt.ItemFlag.ItemIsEditable)
                reference.setToolTip(name + "\n" + record["layer_name"])
                table.setItem(row, 0, reference)
                description = QTableWidgetItem(record["description"])
                layer = next(layer for layer in self.document["layers"] if layer["id"] == record["layer"])
                if layer["locked"] or not layer["visible"]:
                    description.setFlags(description.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 1, description)
            table.resizeRowsToContents()
            title = self.owner.tr("legend_table").format(number=index, symbol=self.owner.tr("object_symbol_" + entry["kind"]))
            self.tabs.addTab(table, title)
            self.tables.append((table, entry["rows"]))
        self.inventory=None
        if inventory:
            from qt_ui.qt_rack_inventory import RackInventoryPanel
            self.inventory=RackInventoryPanel(self.owner,self.document,inventory)
            self.tabs.addTab(self.inventory,self.owner.tr('rack_inventory'))
        self.empty.setVisible(not (entries or inventory))
        self.number_existing.setEnabled(any(layer["visible"] and not layer["locked"] and item["variant"] in NUMBERED_SYMBOLS
                                           and "number" not in item for layer, item in symbols(self.document)))

    def number_unmarked(self):
        self.collect()
        candidate = deepcopy(self.document)
        try:
            counters = sequences(self.token, candidate)
            for layer, item in symbols(candidate):
                if layer["visible"] and not layer["locked"] and item["variant"] in NUMBERED_SYMBOLS and "number" not in item:
                    value = counters[item["variant"]]
                    if value > 999999:
                        raise ValueError("Symbol sequence exhausted")
                    item["number"] = value
                    counters[item["variant"]] += 1
            from survey.plan_layers import validate_document
            candidate = validate_document(candidate)
        except (ValueError, TypeError, KeyError) as error:
            QMessageBox.warning(self, self.owner.tr("plan_legend"), self.owner.tr(str(error)))
            return
        self.document = candidate
        self.rebuild()

    def save(self):
        if self.owner.session is not self.session or self.session.metadata != self.token or self.owner.scan_in_progress:
            QMessageBox.warning(self, self.owner.tr("plan_legend"), self.owner.tr("legend_stale"))
            return
        self.collect()
        try:
            self.owner.plan_tools.controller.change_layers(self.document)
            self.accept()
        except (ValueError, TypeError, KeyError) as error:
            QMessageBox.warning(self, self.owner.tr("plan_legend"), self.owner.tr(str(error)))


def open_plan_legend(owner):
    if owner.session is None or not supports_plan_annotations(owner.session.metadata) or owner.scan_in_progress:
        return False
    dialog = None
    try:
        dialog = PlanLegendDialog(owner)
        return dialog.exec() == QDialog.DialogCode.Accepted
    except (ValueError, TypeError, KeyError) as error:
        QMessageBox.warning(owner, owner.tr("plan_legend"), str(error))
        return False
    finally:
        if dialog is not None:
            dialog.deleteLater()
