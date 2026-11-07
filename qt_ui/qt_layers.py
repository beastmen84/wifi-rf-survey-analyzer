"""Survey layer column, independent of Design Mode and RF overlays."""
from copy import deepcopy
from PySide6.QtCore import Qt, Signal, QSignalBlocker, QTimer, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QInputDialog,
    QLabel, QMessageBox, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout)
from app_core.settings import load_app_settings, save_app_settings
from survey.plan_layers import PLAN_LAYERS_KEY, MAX_LAYERS, active_layer, add_layer, move_selection
from qt_ui.qt_theme import QT_THEMES


class LayerTree(QTreeWidget):
    reorderRequested = Signal(str, str, bool)

    def dropEvent(self, event):
        selected = self.selectedItems()
        target = self.itemAt(event.position().toPoint())
        if event.source() is self and selected:
            source_id = selected[0].data(2, Qt.ItemDataRole.UserRole)
            target_id = target.data(2, Qt.ItemDataRole.UserRole) if target else ""
            before = bool(target and event.position().y() < self.visualItemRect(target).center().y())
            self.reorderRequested.emit(source_id, target_id, before)
            event.acceptProposedAction()
        else:
            event.ignore()


class LayersPanel(QFrame):
    def __init__(self, owner):
        super().__init__()
        self.owner, self.last = owner, object()
        self.in_tree_signal = False
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.sync)
        self.open = bool(load_app_settings().get("plan_layers_panel_open", False))
        self.setObjectName("summaryPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(owner.spx(6), owner.spx(6), owner.spx(6), owner.spx(6))
        header = QHBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("sectionTitle")
        header.addWidget(self.title)
        self.history_buttons = {}
        for action in ("undo", "redo"):
            button = QPushButton()
            button.setObjectName("compactButton")
            button.setStyleSheet("padding: 2px;")
            button.setFixedSize(owner.spx(30), owner.spx(30))
            button.clicked.connect(lambda _checked=False, name=action: getattr(self.drawing, name)())
            self.history_buttons[action] = button
            header.addWidget(button)
        self.toggle = QPushButton()
        self.toggle.setObjectName("compactButton")
        self.toggle.setStyleSheet("padding: 2px;")
        self.toggle.setFixedSize(owner.spx(30), owner.spx(30))
        self.toggle.clicked.connect(lambda: self.set_open(not self.open))
        header.addWidget(self.toggle)
        layout.addLayout(header)
        self.body = QFrame()
        body = QVBoxLayout(self.body)
        body.setContentsMargins(0, 0, 0, 0)
        self.tree = LayerTree()
        self.tree.setColumnCount(3)
        self.tree.setRootIsDecorated(False)
        self.tree.setItemsExpandable(False)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tree.setColumnWidth(0, owner.spx(46))
        self.tree.setColumnWidth(1, owner.spx(56))
        self.tree.setMinimumHeight(owner.spx(130))
        self.tree.currentItemChanged.connect(self.activate_item)
        self.tree.itemChanged.connect(self.check_changed)
        self.tree.itemDoubleClicked.connect(lambda *_args: self.rename(defer=True))
        self.tree.reorderRequested.connect(self.reorder)
        body.addWidget(self.tree, 1)
        self.buttons = {}
        for actions in (("add", "rename"), ("up", "down", "delete")):
            row = QHBoxLayout()
            for action in actions:
                button = QPushButton()
                button.setObjectName("compactButton")
                button.clicked.connect(lambda _checked=False, name=action: getattr(self, name)())
                self.buttons[action] = button
                row.addWidget(button)
            body.addLayout(row)
        self.move_button = QPushButton()
        self.move_button.setObjectName("compactButton")
        self.move_button.clicked.connect(self.move_selected)
        body.addWidget(self.move_button)
        self.note = QLabel()
        self.note.setWordWrap(True)
        body.addWidget(self.note)
        layout.addWidget(self.body, 1)
        layout.addStretch(0)
        self.set_open(self.open, save=False)

    @property
    def drawing(self):
        return self.owner.plan_tools.controller

    def set_open(self, opened, save=True):
        self.open = bool(opened)
        self.title.setVisible(self.open)
        for button in self.history_buttons.values():
            button.setVisible(self.open)
        self.body.setVisible(self.open)
        self.setFixedWidth(self.owner.spx(290 if self.open else 44))
        if save:
            settings = load_app_settings()
            settings["plan_layers_panel_open"] = self.open
            save_app_settings(settings)
        self.retranslate()

    def retranslate(self):
        tr = self.owner.tr
        self.title.setText(tr("layers_title"))
        self.toggle.setToolTip(tr("layers_title"))
        self.toggle.setAccessibleName(tr("layers_title"))
        self.tree.setHeaderLabels([tr("layer_visible"), tr("layer_locked"), tr("layer_name")])
        for action, button in self.buttons.items():
            button.setText(tr("layer_" + action))
        self.move_button.setText(tr("layer_move_selection"))
        self.note.setText(tr("layer_order_hint"))
        size = self.owner.spx(20)
        self.owner.plan_tools.update_history_icons()
        for action, button in self.history_buttons.items():
            button.setIcon(getattr(self.owner.plan_tools, action + "_button").icon())
            button.setIconSize(QSize(size, size))
            button.setToolTip(tr("blank_tool_" + action))
            button.setAccessibleName(tr("blank_tool_" + action))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.scale(size / 24, size / 24)
        painter.setPen(QPen(QColor(QT_THEMES[self.owner.theme]["text"]), 1.5))
        for y in (7, 12, 17):
            painter.drawLine(3, y, 12, y - 4)
            painter.drawLine(12, y - 4, 21, y)
            painter.drawLine(3, y, 12, y + 4)
            painter.drawLine(12, y + 4, 21, y)
        painter.end()
        self.toggle.setIcon(QIcon(pixmap))
        self.toggle.setIconSize(QSize(size, size))

    def sync(self):
        if self.in_tree_signal:
            # Never delete QTreeWidgetItems inside their native change/drop signal.
            self.refresh_timer.start(0)
            return
        enabled = self.owner.session is not None and not self.owner.scan_in_progress
        self.body.setEnabled(enabled)
        for action, button in self.history_buttons.items():
            button.setEnabled(enabled and bool(getattr(self.drawing, action + "_stack")))
        self.toggle.setEnabled(self.owner.session is not None)
        if not self.owner.session:
            self.tree.clear()
            self.last = object()
            return
        try:
            document = self.drawing.layer_document()
        except (ValueError, TypeError, KeyError):
            self.body.setEnabled(False)
            return
        value = (self.owner.session, self.owner.session.metadata.get(PLAN_LAYERS_KEY))
        if value != self.last:
            self.last = value
            blocker = QSignalBlocker(self.tree)
            self.tree.clear()
            for layer in reversed(document["layers"]):
                item = QTreeWidgetItem(["", "", layer["name"]])
                item.setData(2, Qt.ItemDataRole.UserRole, layer["id"])
                item.setToolTip(2, layer["name"])
                item.setFlags((item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled)
                              & ~Qt.ItemFlag.ItemIsDropEnabled)
                item.setCheckState(0, Qt.CheckState.Checked if layer["visible"] else Qt.CheckState.Unchecked)
                item.setCheckState(1, Qt.CheckState.Checked if layer["locked"] else Qt.CheckState.Unchecked)
                item.setToolTip(0, self.owner.tr("layer_base_hint") if layer["id"] == "0" else self.owner.tr("layer_visible"))
                font = item.font(2)
                font.setBold(layer["id"] == document["active"])
                item.setFont(2, font)
                self.tree.addTopLevelItem(item)
                if layer["id"] == document["active"]:
                    self.tree.setCurrentItem(item)
            del blocker
        current = active_layer(document)
        self.buttons["delete"].setEnabled(enabled and current["id"] != "0" and not current["locked"])
        self.buttons["add"].setEnabled(enabled and len(document["layers"]) < MAX_LAYERS)
        self.buttons["up"].setEnabled(enabled and current is not document["layers"][-1])
        self.buttons["down"].setEnabled(enabled and current is not document["layers"][0])
        self.update_selection()

    def update_selection(self):
        d = self.drawing
        has_selection = bool(d.selection.selected or d.selection.selected_curves or d.annotation.selected or d.annotation.selected_labels)
        self.move_button.setEnabled(self.owner.session is not None and not self.owner.scan_in_progress
            and has_selection and d.editable() and len(d.layer_document()["layers"]) > 1)

    def commit(self, document, history=True, defer=False):
        if self.owner.session is None or self.owner.scan_in_progress:
            return False
        self.in_tree_signal = defer
        try:
            return self.drawing.change_layers(document, history=history)
        except (ValueError, TypeError, KeyError, StopIteration):
            self.owner.status.showMessage(self.owner.tr("layer_invalid"))
            self.last = object()
            self.sync()
            return False
        finally:
            self.in_tree_signal = False

    def modal_context(self):
        # Nested Qt event loops may load another survey or change the drawing.
        return (self.owner.session, self.drawing.view.pixmap_item,
                deepcopy(self.owner.session.metadata))

    def context_matches(self, context):
        return (context[0] is self.owner.session and context[1] is self.drawing.view.pixmap_item
                and self.owner.session.metadata == context[2] and not self.owner.scan_in_progress)

    def activate_item(self, item, _previous):
        if item is not None and self.owner.session:
            document = deepcopy(self.drawing.layer_document())
            document["active"] = item.data(2, Qt.ItemDataRole.UserRole)
            self.commit(document, history=False, defer=True)

    def check_changed(self, item, column):
        if column not in (0, 1):
            return
        document = deepcopy(self.drawing.layer_document())
        layer = next(layer for layer in document["layers"] if layer["id"] == item.data(2, Qt.ItemDataRole.UserRole))
        layer["visible" if column == 0 else "locked"] = item.checkState(column) == Qt.CheckState.Checked
        self.commit(document, defer=True)

    def add(self):
        document = self.drawing.layer_document()
        names = {layer["name"].casefold() for layer in document["layers"]}
        number = 1
        while ("Layer " + str(number)).casefold() in names:
            number += 1
        self.commit(add_layer(document, "Layer " + str(number)))

    def rename(self, defer=False):
        document = deepcopy(self.drawing.layer_document())
        layer = active_layer(document)
        context = self.modal_context()
        name, accepted = QInputDialog.getText(self.owner, self.owner.tr("layer_rename"),
                                             self.owner.tr("layer_name"), text=layer["name"])
        if accepted and self.context_matches(context):
            layer["name"] = name
            self.commit(document, defer=defer)

    def delete(self):
        document = deepcopy(self.drawing.layer_document())
        layer = active_layer(document)
        if layer["id"] == "0" or layer["locked"]:
            return
        context = self.modal_context()
        if any(layer["drawing"][key] for key in ("segments", "curves", "labels", "annotations")):
            if QMessageBox.question(self.owner, self.owner.tr("layer_delete"), self.owner.tr("layer_delete_confirm"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
        if not self.context_matches(context):
            return
        document["layers"].remove(layer)
        document["active"] = "0"
        self.commit(document, defer=True)

    def reorder(self, source_id, target_id, before):
        document = deepcopy(self.drawing.layer_document())
        order = list(reversed(document["layers"]))
        source = next(layer for layer in order if layer["id"] == source_id)
        if source_id == target_id:
            return
        order.remove(source)
        index = next((i + int(not before) for i, layer in enumerate(order) if layer["id"] == target_id), len(order))
        order.insert(index, source)
        document["layers"] = list(reversed(order))
        self.commit(document, defer=True)

    def up(self):
        self.shift(1)

    def down(self):
        self.shift(-1)

    def shift(self, step):
        document = deepcopy(self.drawing.layer_document())
        index = document["layers"].index(active_layer(document))
        other = index + step
        if 0 <= other < len(document["layers"]):
            document["layers"][index], document["layers"][other] = document["layers"][other], document["layers"][index]
            self.commit(document)

    def move_selected(self):
        document = self.drawing.layer_document()
        targets = [layer for layer in document["layers"] if layer["id"] != document["active"]
                   and layer["visible"] and not layer["locked"]]
        selected = deepcopy(dict(segments=self.drawing.selection.selected, curves=self.drawing.selection.selected_curves,
                        labels=self.drawing.annotation.selected_labels, annotations=self.drawing.annotation.selected))
        if not targets or not any(selected.values()):
            self.owner.status.showMessage(self.owner.tr("layer_select_first"))
            return
        context = self.modal_context()
        name, accepted = QInputDialog.getItem(self.owner, self.owner.tr("layer_move_selection"),
            self.owner.tr("layer_name"), [layer["name"] for layer in targets], 0, False)
        current = dict(segments=self.drawing.selection.selected, curves=self.drawing.selection.selected_curves,
                       labels=self.drawing.annotation.selected_labels, annotations=self.drawing.annotation.selected)
        if accepted and self.context_matches(context) and current == selected:
            try:
                result = move_selection(document, next(layer["id"] for layer in targets if layer["name"] == name), selected)
                self.commit(result)
            except (ValueError, KeyError):
                self.owner.status.showMessage(self.owner.tr("layer_invalid"))
