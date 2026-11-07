"""Reviewable wall layouts and existing-plan conversions with explicit area effects."""
from copy import deepcopy
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QTransform
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout)
from app_core.units import display_units_to_meters, meters_to_display_units, distance_unit_label, format_distance_meters
from survey.plan_layers import active_layer, validate_document
from survey.plan_mode import is_drawn_plan
from survey.wall_layout import plan_wall_layout
from survey.wall_conversion import convert_wall_reference, reference_regions
from qt_ui.qt_clean_plan import VectorPlanSource


def validate_survey_layout(owner, result):
    if not result.changed_positions:
        return
    if owner.session.get_points() or owner.floorplan_view.has_boundaries_mask():
        raise ValueError("wall_survey_lock")
    if any(g.get("position") and not g["position"].get("symbol_id") for g in owner.session.get_ap_groups()):
        raise ValueError("wall_convert_aps")


class WallPropertiesDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.session, self.pixmap = owner.session, owner.floorplan_view.pixmap_item
        self.token = deepcopy(self.session.metadata)
        drawing = owner.plan_tools.controller
        self.document = deepcopy(drawing.layer_document())
        self.state = active_layer(self.document)["drawing"]
        self.lines, self.curves = drawing.selection.selected, drawing.selection.selected_curves
        self.density = owner.get_px_per_meter()
        self.candidate = self.result = None
        self.error, self.problem_rooms = None, ()
        self.setWindowTitle(owner.tr("wall_title"))
        self.resize(owner.spx(980), owner.spx(640))
        layout = QVBoxLayout(self)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self.form = QFormLayout()
        self.mode = QComboBox()
        for key, value in (("wall_mode_rigid", "rigid"), ("wall_mode_axis", "axis"), ("wall_mode_face", "face"), ("wall_mode_keep", "keep")):
            self.mode.addItem(owner.tr(key), value)
        self.mode.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.mode.setMinimumContentsLength(24)
        self.mode.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.form.addRow(owner.tr("wall_method"), self.mode)
        self.thickness_spin = QDoubleSpinBox()
        self.thickness_spin.setDecimals(2)
        self.thickness_spin.setRange(0, meters_to_display_units(5, owner.measurement_system))
        self.thickness_spin.setSuffix(" "+distance_unit_label(owner.measurement_system))
        self.thickness_spin.setSingleStep(.01 if owner.measurement_system == "metric" else .1)
        self.thickness_spin.setKeyboardTracking(False)
        selected = [self.state["segments"][i] for i in self.lines] + [self.state["curves"][i] for i in self.curves]
        widths = {item.get("wall", {}).get("width", 0) for item in selected}
        initial = next(iter(widths)) if len(widths) == 1 and next(iter(widths)) > 0 else self.density*.2
        self.exact_initial_width = initial if len(widths) == 1 and initial in widths else None
        self.thickness_spin.setMaximum(meters_to_display_units(max(5, initial/self.density), owner.measurement_system))
        self.thickness_spin.setValue(meters_to_display_units(initial/self.density, owner.measurement_system))
        self.initial_display_width = self.thickness_spin.value()
        self.form.addRow(owner.tr("wall_depth"), self.thickness_spin)
        self.side = QComboBox()
        for key, side in (("wall_auto", 0), ("wall_left", 1), ("wall_right", -1)):
            self.side.addItem(owner.tr(key), side)
        self.form.addRow(owner.tr("wall_open_mode"), self.side)
        self.anchor = QComboBox()
        picker = reference_regions(self.state)
        self.reference_rooms = picker.records
        self.room_centers = picker.centers()
        for index, (path, room) in enumerate(picker.records):
            preferred = QPointF(self.room_centers[index][0], path.boundingRect().top()+path.boundingRect().height()*.2)
            if path.contains(preferred):
                self.room_centers[index] = (preferred.x(), preferred.y())
            self.anchor.addItem(owner.tr("wall_room").format(number=index+1)+" · "+self.area(room.area), index)
        self.anchor.setEnabled(self.anchor.count() > 1)
        self.anchor_label = QLabel()
        self.form.addRow(self.anchor_label, self.anchor)
        layout.addLayout(self.form)
        self.zero = QLabel()
        self.zero.setWordWrap(True)
        layout.addWidget(self.zero)
        body = QHBoxLayout()
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(owner.spx(440), owner.spx(240))
        body.addWidget(self.preview, 3)
        self.rooms = QTableWidget()
        self.rooms.setMinimumWidth(owner.spx(440))
        self.rooms.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rooms.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.rooms.verticalHeader().hide()
        self.rooms.cellClicked.connect(lambda row, _col: self.anchor.setCurrentIndex(row))
        body.addWidget(self.rooms, 2)
        layout.addLayout(body, 1)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel)
        self.apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        self.apply_button.setText(owner.tr("wall_apply"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(owner.tr("cancel"))
        self.apply_button.clicked.connect(self.try_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        if any(item.get("wall", {}).get("reference") for item in selected):
            self.mode.setCurrentIndex(self.mode.findData("keep"))
        self.mode.currentIndexChanged.connect(self.refresh)
        self.thickness_spin.valueChanged.connect(self.refresh)
        self.side.currentIndexChanged.connect(self.refresh)
        self.anchor.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def area(self, pixels, approximate=False):
        value = pixels/self.density**2*meters_to_display_units(1, self.owner.measurement_system)**2
        decimals = 4 if 0 < abs(value) < .01 else 2
        return ("≈ " if approximate else "")+self.locale().toString(value, "f", decimals)+" "+distance_unit_label(self.owner.measurement_system)+"²"

    def refresh(self, *_args):
        self.candidate = self.result = None
        self.error, self.problem_rooms = None, ()
        mode = self.mode.currentData()
        conversion = mode != "rigid"
        self.mode.setToolTip(self.mode.currentText())
        self.hint.setText(self.owner.tr("wall_convert_hint" if conversion else "wall_hint"))
        self.zero.setText(self.owner.tr("wall_convert_zero" if conversion else "wall_zero"))
        self.form.setRowVisible(self.side, not conversion)
        self.form.setRowVisible(self.anchor, mode in ("rigid", "face"))
        self.anchor_label.setText(self.owner.tr("wall_reference_room" if mode == "face" else "wall_anchor"))
        try:
            width = display_units_to_meters(self.thickness_spin.value(), self.owner.measurement_system)*self.density
            if self.exact_initial_width is not None and self.thickness_spin.value() == self.initial_display_width:
                width = self.exact_initial_width
            bounds = self.owner.floorplan_view.scene.sceneRect()
            if conversion:
                self.result = convert_wall_reference(self.state, self.lines, self.curves, width, bounds,
                    mode=mode, room_index=self.anchor.currentData() or 0)
            else:
                self.result = plan_wall_layout(self.state, self.lines, self.curves, width, bounds,
                    open_side=self.side.currentData(), anchor=self.anchor.currentData() or 0)
            validate_survey_layout(self.owner, self.result)
            candidate = deepcopy(self.document)
            active_layer(candidate)["drawing"] = self.result.state
            candidate = validate_document(candidate)
            source = VectorPlanSource.from_layers(self.pixmap.pixmap().size(), candidate["layers"])
            self.candidate = candidate
        except (ValueError, KeyError, TypeError, OverflowError) as error:
            self.error, self.problem_rooms = str(error), getattr(error, "rooms", ())
            source = VectorPlanSource.from_layers(self.pixmap.pixmap().size(), self.document["layers"])
        self.render_preview(source)
        headers = [self.owner.tr("wall_room").format(number="").strip()]
        headers += [self.owner.tr(key) for key in (("wall_reference_area", "wall_usable_area", "wall_area_delta") if conversion else ("wall_area", "wall_shift"))]
        self.rooms.setColumnCount(len(headers))
        self.rooms.setHorizontalHeaderLabels(headers)
        areas = self.result.areas if self.result and self.candidate else tuple(r.area for _p, r in self.reference_rooms)
        self.rooms.setRowCount(len(areas))
        if self.candidate:
            if conversion:
                lost = sum(area > 1e-6 and usable <= 1e-6 for area, usable in zip(areas, self.result.usable_areas))
                self.summary.setText(self.owner.tr("wall_conversion_ready")+(" "+self.owner.tr("wall_absorbed_count").format(count=lost) if lost else ""))
            else:
                count = sum(math.hypot(*move) > 1e-5 for move in self.result.moves)
                self.summary.setText(self.owner.tr("wall_moved").format(count=count) if count else self.owner.tr("wall_unchanged"))
            self.summary.setStyleSheet("")
        else:
            text = self.owner.tr(self.error) if self.error.startswith("wall_") else self.owner.tr("rectangle_invalid_drawing")
            if self.problem_rooms:
                text += " " + self.owner.tr("wall_conflict_rooms").format(rooms=", ".join(str(i+1) for i in self.problem_rooms))
            self.summary.setText(text)
            self.summary.setStyleSheet("color:#ef4444;")
        for row, area in enumerate(areas):
            values = [self.owner.tr("wall_room").format(number=row+1), self.area(area)]
            absorbed = False
            if conversion:
                usable = self.result.usable_areas[row] if self.candidate else None
                absorbed = usable is not None and area > 1e-6 and usable <= 1e-6
                values += [(self.owner.tr("wall_absorbed") if absorbed else self.area(usable, self.result.approximate_areas)) if usable is not None else "—",
                           self.area(usable-area, self.result.approximate_areas) if usable is not None else "—"]
            else:
                values.append(" / ".join(format_distance_meters(v/self.density, self.owner.measurement_system)
                    for v in self.result.moves[row]) if self.candidate else "—")
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if row in self.problem_rooms or absorbed:
                    item.setForeground(QColor("#ef4444"))
                item.setToolTip(value)
                self.rooms.setItem(row, col, item)
        self.rooms.resizeRowsToContents()
        self.apply_button.setEnabled(self.candidate is not None)

    def render_preview(self, source):
        from survey.plan_symbol_rendering import SymbolNumber, number_commands
        focus = QRectF()
        for path, _pen, _brush in source._commands:
            paths = [p for p, _n, _b in number_commands(path.item, 11)] if isinstance(path, SymbolNumber) else [path]
            for p in paths:
                focus = focus.united(p.boundingRect())
        focus = focus.adjusted(-20, -20, 20, 20).intersected(QRectF(0, 0, source.width(), source.height()))
        if focus.isEmpty():
            focus = QRectF(0, 0, source.width(), source.height())
        image = QImage(self.owner.spx(480), self.owner.spx(300), QImage.Format.Format_RGB32)
        image.fill(Qt.GlobalColor.white)
        painter = QPainter(image)
        try:
            factor = min((image.width()-12)/focus.width(), (image.height()-12)/focus.height())
            target = QRectF((image.width()-focus.width()*factor)/2-focus.left()*factor,
                            (image.height()-focus.height()*factor)/2-focus.top()*factor,
                            source.width()*factor, source.height()*factor)
            source.paint_plan(painter, target)
            transform = QTransform().translate(target.left(), target.top()).scale(factor, factor)
            for i in self.problem_rooms:
                if i in range(len(self.reference_rooms)):
                    painter.setPen(QPen(QColor("#ef4444"), 1.5))
                    painter.setBrush(QColor(239, 68, 68, 30))
                    painter.drawPath(transform.map(self.reference_rooms[i][0]))
            font = painter.font()
            font.setPixelSize(self.owner.spx(11))
            font.setBold(True)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            anchor = self.anchor.currentData() or 0
            for i, center in enumerate(self.room_centers):
                if len(self.room_centers) > 16 and i != anchor and i not in self.problem_rooms:
                    continue
                move = self.result.moves[i] if self.candidate and i < len(self.result.moves) else (0, 0)
                text = self.owner.tr("wall_room").format(number=i+1)
                x, y = target.left()+(center[0]+move[0])*factor, target.top()+(center[1]+move[1])*factor
                box = QRectF(x-(metrics.horizontalAdvance(text)+10)/2, y-metrics.height()/2-3,
                             metrics.horizontalAdvance(text)+10, metrics.height()+6)
                box.moveLeft(max(3, min(box.left(), image.width()-box.width()-3)))
                box.moveTop(max(3, min(box.top(), image.height()-box.height()-3)))
                painter.setPen(QPen(QColor("#ef4444" if i in self.problem_rooms else "#2563eb" if i == anchor else "#64748b"), 1))
                painter.setBrush(QColor("#dbeafe" if i == anchor else "#ffffff"))
                painter.drawRoundedRect(box, 3, 3)
                painter.setPen(QColor("#111827"))
                painter.drawText(box, Qt.AlignmentFlag.AlignCenter, text)
        finally:
            painter.end()
        self.preview.setPixmap(QPixmap.fromImage(image))

    def try_accept(self):
        self.refresh()
        if self.candidate is not None:
            self.accept()


def open_wall_properties(owner):
    drawing = owner.plan_tools.controller
    if (not drawing.editable() or owner.scan_in_progress or not is_drawn_plan(owner.session.metadata)
            or drawing.selection.moving or drawing.rotation.active
            or not (drawing.selection.selected or drawing.selection.selected_curves)):
        return False
    dialog = None
    drawing.wall_dialog_open = True
    try:
        dialog = WallPropertiesDialog(owner)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.candidate is None:
            return False
        if owner.session is not dialog.session or owner.floorplan_view.pixmap_item is not dialog.pixmap or owner.session.metadata != dialog.token or owner.scan_in_progress:
            QMessageBox.warning(owner, owner.tr("wall_title"), owner.tr("wall_stale"))
            return False
        validate_survey_layout(owner, dialog.result)
        return drawing.change_layers(dialog.candidate)
    except (ValueError, KeyError, TypeError, OverflowError) as error:
        key = str(error)
        QMessageBox.warning(owner, owner.tr("wall_title"), owner.tr(key) if key.startswith("wall_") else owner.tr("rectangle_invalid_drawing"))
        return False
    finally:
        drawing.wall_dialog_open = False
        if dialog is not None:
            dialog.deleteLater()
