"""Draw Plan AP assignment: choose existing apparatus, with source-plan preview."""
from copy import deepcopy
from uuid import uuid4

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPen, QColor, QPixmap
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QHeaderView, QAbstractItemView)
from app_core.units import format_distance_meters
from qt_ui.qt_plan_printing import clean_plan_source
from survey.plan_objects import object_default
from survey.plan_layers import active_layer
from survey.plan_symbols import symbols, bind_ap
from survey.plan_annotation_rendering import annotation_fits


class ApSymbolDialog(QDialog):
    def __init__(self, owner, group_id, document, groups):
        super().__init__(owner)
        self.owner, self.group_id, self.selected_id, self.action = owner, group_id, None, "bind"
        self.group = next(g for g in groups if str(g["group_id"]) == group_id)
        self.candidates = [(layer, item) for layer, item in symbols(document) if item["variant"] == "wifi_ap"
            and layer["visible"] and not layer["locked"] and item.get("ap_group") in (None, group_id)]
        self.setWindowTitle(owner.tr("ap_symbol_assign") + " · " + owner.get_ap_group_display_name(group_id))
        self.resize(owner.spx(720), owner.spx(620))
        layout = QVBoxLayout(self)
        hint = QLabel(owner.tr("ap_symbol_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.table = QTableWidget(len(self.candidates), 3)
        self.table.setHorizontalHeaderLabels([owner.tr("annotation_symbol"), owner.tr("layer_name"), owner.tr("symbol_position")])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        for row, (layer, item) in enumerate(self.candidates):
            values = (item.get("description") or owner.tr("object_symbol_wifi_ap"), layer["name"],
                " / ".join(format_distance_meters(item[key] / owner.get_px_per_meter(), owner.measurement_system) for key in ("cx", "cy")))
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        layout.addWidget(self.table, 1)
        self.preview = QLabel()
        self.preview.setMinimumHeight(owner.spx(180))
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview)
        self.source = clean_plan_source(owner.floorplan_view, owner.session.metadata)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(owner.tr("ap_symbol_assign"))
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(owner.tr("cancel"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        actions = QHBoxLayout()
        self.unassign = QPushButton(owner.tr("ap_symbol_unassign"))
        self.unassign.setObjectName("compactButton")
        self.unassign.setEnabled(any(item.get("ap_group") == group_id and not layer["locked"]
                                     for layer, item in symbols(document)))
        self.unassign.clicked.connect(lambda: self.finish("unbind"))
        actions.addWidget(self.unassign)
        self.convert = QPushButton(owner.tr("ap_symbol_convert"))
        self.convert.setObjectName("compactButton")
        self.convert.setEnabled(bool(self.group.get("position") and not self.group["position"].get("symbol_id")
                                    and any(layer["visible"] and not layer["locked"] for layer in document["layers"])))
        self.convert.clicked.connect(lambda: self.finish("convert"))
        actions.addWidget(self.convert)
        layout.addLayout(actions)
        layout.addWidget(self.buttons)
        self.table.currentCellChanged.connect(self.refresh)
        if self.candidates:
            self.table.selectRow(0)
        self.refresh()

    def refresh(self, *_args):
        row = self.table.currentRow()
        self.selected_id = self.candidates[row][1]["id"] if 0 <= row < len(self.candidates) else None
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(self.selected_id is not None)
        image = QImage(600, 220, QImage.Format.Format_RGB32)
        image.fill(Qt.GlobalColor.white)
        painter = QPainter(image)
        target = QRectF(4, 4, 592, 212)
        factor = min(target.width() / self.source.width(), target.height() / self.source.height())
        target = QRectF((600-self.source.width()*factor)/2, (220-self.source.height()*factor)/2,
                        self.source.width()*factor, self.source.height()*factor)
        if hasattr(self.source, "paint_plan"):
            self.source.paint_plan(painter, target)
        else:
            painter.drawImage(target, self.source)
        if self.selected_id:
            item = self.candidates[row][1]
            painter.setPen(QPen(QColor("#ef4444"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(target.left()+item["cx"]*factor-9, target.top()+item["cy"]*factor-9, 18, 18))
        painter.end()
        self.preview.setPixmap(QPixmap.fromImage(image))

    def finish(self, action):
        self.action = action
        self.accept()


def assign_ap_symbol(owner, group_id):
    from survey.plan_mode import is_drawn_plan
    if owner.session is None or not is_drawn_plan(owner.session.metadata) or owner.scan_in_progress:
        return False
    drawing = owner.plan_tools.controller
    dialog = None
    try:
        document, session, pixmap = deepcopy(drawing.layer_document()), owner.session, owner.floorplan_view.pixmap_item
        groups = session.get_ap_groups()
        if not any(str(g["group_id"]) == group_id for g in groups):
            return False
        token = deepcopy(session.metadata)
        dialog = ApSymbolDialog(owner, group_id, document, groups)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        if owner.session is not session or owner.floorplan_view.pixmap_item is not pixmap or session.metadata != token or owner.scan_in_progress:
            return False
        if dialog.action == "convert":
            position = next(g["position"] for g in groups if str(g["group_id"]) == group_id)
            layer = active_layer(document)
            if layer["locked"] or not layer["visible"]:
                layer = next(l for l in document["layers"] if l["visible"] and not l["locked"])
            item = object_default("symbol", owner.get_px_per_meter(), "wifi_ap")
            item.update(id=uuid4().hex, cx=float(position["x"]), cy=float(position["y"]), ap_group=group_id)
            if not annotation_fits(item, owner.floorplan_view.scene.sceneRect()):
                raise ValueError("The current AP position is too close to the sheet edge")
            layer["drawing"]["annotations"].append(item)
            document["active"] = layer["id"]
        elif dialog.action == "unbind":
            for layer, item in symbols(document):
                if item.get("ap_group") == group_id:
                    if layer["locked"]:
                        raise ValueError("The current symbol layer is locked")
                    item.pop("ap_group")
        else:
            document = bind_ap(document, dialog.selected_id, group_id)
        return drawing.change_layers(document)
    except (ValueError, TypeError, KeyError, StopIteration) as error:
        QMessageBox.warning(owner, owner.tr("ap_symbol_assign"), owner.tr("ap_symbol_error").format(error=str(error)))
        return False
    finally:
        if dialog is not None:
            dialog.deleteLater()
