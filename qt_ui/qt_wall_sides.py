"""Clickable per-side review before structural placement or room editing."""
from copy import deepcopy
from dataclasses import replace
import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPainterPathStroker, QPen, QPixmap, QIcon
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QGraphicsScene, QGraphicsView, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QFormLayout, QSizePolicy, QWidget,
    QStyle, QStyleOptionButton)
from app_core.units import distance_unit_label, display_units_to_meters, meters_to_display_units, format_distance_meters
from survey.plan_curves import curve_info, point_at, transform_curves
from survey.plan_faces import RegionPicker
from survey.plan_geometry import translate_segments
from survey.plan_curve_rendering import curve_path
from survey.plan_layers import active_layer, validate_document
from survey.wall_sides import stage_structure, wall_sides, apply_side_widths, same_wall_faces
from survey.wall_conversion import reference_regions
from survey.wall_geometry import solid, wall_commands
from survey.wall_editing import relation
from qt_ui.qt_clean_plan import VectorPlanSource
from qt_ui.qt_wall_properties import validate_survey_layout
from survey.wall_materials import MATERIALS, PATTERNS, appearance, validated_appearance
from survey.wall_rendering import MaterialPath, paint_material, wall_item, WallReferenceInk
from survey.wall_attachments import WallAttachmentIndex


def appearance_icon(owner, material, pattern='auto'):
    size = QSize(owner.spx(52),owner.spx(22))
    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        painter.scale(size.width()/52,size.height()/22)
        path = QPainterPath()
        path.addRect(QRectF(1,1,50,20))
        paint_material(painter,MaterialPath(path,material,pattern),QPen(QColor('#475569'),.8))
    finally:
        painter.end()
    return QIcon(pixmap)


def side_path(shape):
    if 'kind' in shape:
        return curve_path(shape)
    path = QPainterPath(QPointF(shape['x1'], shape['y1']))
    path.lineTo(shape['x2'], shape['y2'])
    return path


class PriorityCheckBox(QCheckBox):
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.isChecked():
            option = QStyleOptionButton()
            self.initStyleOption(option)
            box = self.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, self)
            path = QPainterPath(QPointF(box.left()+box.width()*.24, box.top()+box.height()*.52))
            path.lineTo(box.left()+box.width()*.43, box.top()+box.height()*.72)
            path.lineTo(box.left()+box.width()*.78, box.top()+box.height()*.28)
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor('white'), max(1.5,box.width()*.1))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setOpacity(1 if self.isEnabled() else .5)
            painter.drawPath(path)
            painter.end()


class SidePreview(QGraphicsView):
    def __init__(self, dialog):
        super().__init__(QGraphicsScene(dialog), dialog)
        self.dialog = dialog
        self.paths = []
        self.focus_rect = QRectF()
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QColor('white'))
        self.setMinimumSize(dialog.owner.spx(400), dialog.owner.spx(280))
        self.setAccessibleName(dialog.owner.tr('wall_sides_preview'))

    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            point = self.mapToScene(event.position().toPoint())
            stroke = QPainterPathStroker()
            stroke.setWidth(18/max(.001, abs(self.transform().m11())))
            hits = [i for i, path in enumerate(self.paths) if path.contains(point) or stroke.createStroke(path).contains(point)]
            if hits:
                self.dialog.table.selectRow(hits[0])
                event.accept()
                return
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit()

    def fit(self):
        if not self.focus_rect.isEmpty():
            self.fitInView(self.focus_rect, Qt.AspectRatioMode.KeepAspectRatio)


class WallSidesDialog(QDialog):
    def __init__(self, owner, state, sides, anchor=0, *, placing=False, form_indices=None, fixed_state=None, fixed_rooms=()):
        super().__init__(owner)
        self.owner, self.state, self.sides, self.anchor = owner, deepcopy(state), list(sides), anchor
        self.placing = placing
        self.fixed_state = deepcopy(fixed_state)
        self.fixed_rooms = tuple(fixed_rooms)
        self.converted = any(s.get('wall', {}).get('reference') for s in [*(state['segments'] or []), *state['curves']])
        self.result = self.candidate = None
        self._preview_state = None
        self.error = None
        self.density, self.system = owner.get_px_per_meter(), owner.measurement_system
        self.values = {s.index:s.shape.get('wall', {}).get('width', 0.0) for s in sides}
        self.original_values = dict(self.values)
        self.priorities = {s.index:s.shape.get('wall', {}).get('priority', False) for s in sides}
        self.original_priorities = dict(self.priorities)
        self.priority_checks = []
        self.appearances = {s.index:validated_appearance({k:v for k,v in s.shape.get('wall',{}).items() if k in ('material','pattern')}) for s in sides}
        self.original_appearances = deepcopy(self.appearances)
        selected = {side.index for side in self.sides}
        line_count = len(state['segments'] or [])
        preview_rooms = RegionPicker(state['segments'] or [], state['curves']).records
        boundaries = [set(room.lines) | {line_count+i for i in room.curves} for _path,room in preview_rooms]
        def score(i):
            return len(boundaries[i] & selected), -len(boundaries[i]-selected)
        self.preview_owners = {side.index:max((i for i,boundary in enumerate(boundaries) if side.index in boundary),
                                            key=score, default=None) for side in self.sides}
        if placing or form_indices is not None:
            self.material_forms = [selected if placing else set(form_indices) & selected]
        else:
            line_count = len(state['segments'] or [])
            boundaries = [set(region.lines) | {line_count+i for i in region.curves}
                          for _path, region in reference_regions(state).records]
            self.material_forms = [boundary for boundary in boundaries if boundary <= selected]
        self.shared_signature = ()
        self.spins, self.initial_display = [], []
        attachment_lengths = WallAttachmentIndex([state])
        self.setWindowTitle(owner.tr('wall_sides_place' if placing else 'wall_sides_edit'))
        self.resize(owner.spx(1040), owner.spx(660))
        layout = QVBoxLayout(self)
        hint = QLabel(owner.tr('wall_sides_hint')+(' '+owner.tr('wall_sides_existing_references') if self.converted else ''))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        if placing:
            cancel_hint = QLabel(owner.tr('wall_sides_cancel')+(' '+owner.tr('wall_sides_fixed') if not self.converted else ''))
            cancel_hint.setWordWrap(True)
            layout.addWidget(cancel_hint)
        body = QHBoxLayout()
        self.preview = SidePreview(self)
        body.addWidget(self.preview, 3)
        panel = QVBoxLayout()
        if any(s.shared for s in sides):
            legend = QLabel(owner.tr('wall_sides_shared_legend'))
            legend.setWordWrap(True)
            panel.addWidget(legend)
        self.table = QTableWidget(len(sides), 4)
        self.table.setMinimumWidth(owner.spx(440))
        self.table.setHorizontalHeaderLabels([owner.tr('wall_side'), owner.tr('wall_side_length'), owner.tr('wall_side_depth'), owner.tr('wall_priority')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeaderItem(3).setToolTip(owner.tr('wall_priority_hint'))
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for row, side in enumerate(sides):
            name = str(row+1)+(' ↔' if side.shared else '')
            cell = QTableWidgetItem(name)
            cell.setToolTip(owner.tr('wall_side_shared_hint') if side.shared else name)
            if side.shared:
                cell.setForeground(QColor('#c07412'))
            self.table.setItem(row, 0, cell)
            shape = side.shape
            length = abs(curve_info(shape)[2]*curve_info(shape)[4]) if 'kind' in shape else attachment_lengths.clear_length(
                (shape['x1'],shape['y1']),(shape['x2'],shape['y2']))
            self.table.setItem(row, 1, QTableWidgetItem(format_distance_meters(length/self.density, self.system)))
            spin = QDoubleSpinBox()
            spin.setDecimals(2)
            spin.setRange(0, meters_to_display_units(max(5, self.values[side.index]/self.density), self.system))
            spin.setSuffix(' '+distance_unit_label(self.system))
            spin.setSingleStep(.01 if self.system == 'metric' else .1)
            spin.setKeyboardTracking(False)
            spin.setMinimumHeight(max(owner.spx(34), spin.sizeHint().height()))
            spin.setValue(meters_to_display_units(self.values[side.index]/self.density, self.system))
            spin.valueChanged.connect(lambda _v, r=row:self.change_width(r))
            self.initial_display.append(spin.value())
            self.spins.append(spin)
            self.table.setCellWidget(row, 2, spin)
            check = PriorityCheckBox()
            check.setAccessibleName(owner.tr('wall_priority')+' '+str(row+1))
            check.setToolTip(owner.tr('wall_priority_hint'))
            check.setChecked(self.priorities[side.index])
            check.setEnabled(self.values[side.index] > 0)
            check.toggled.connect(lambda value, r=row:self.change_priority(r, value))
            self.priority_checks.append(check)
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(4, 2, 4, 2)
            cell_layout.addWidget(check, 0, Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 3, cell)
        self.table.resizeRowsToContents()
        for row, spin in enumerate(self.spins):
            self.table.setRowHeight(row, max(self.table.rowHeight(row), spin.minimumHeight()+owner.spx(8)))
        panel.addWidget(self.table, 1)
        properties = QFormLayout()
        self.material = QComboBox()
        self.pattern = QComboBox()
        for key in MATERIALS:
            self.material.addItem(appearance_icon(owner,key),owner.tr('wall_material_'+key),key)
        for key in PATTERNS:
            self.pattern.addItem(owner.tr('wall_pattern_'+key),key)
        for combo in (self.material,self.pattern):
            combo.setIconSize(QSize(owner.spx(52),owner.spx(22)))
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(16)
            combo.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
            combo.setMinimumHeight(owner.spx(34))
        self.material.setAccessibleName(owner.tr('wall_material'))
        self.pattern.setAccessibleName(owner.tr('wall_pattern'))
        properties.addRow(owner.tr('wall_material'),self.material)
        self.apply_all_material_button = QPushButton(owner.tr('wall_material_apply_all'))
        self.apply_all_material_button.setObjectName('compactButton')
        self.apply_all_material_button.setAutoDefault(False)
        self.apply_all_material_button.setMinimumHeight(owner.spx(34))
        self.apply_all_material_button.setAccessibleName(owner.tr('wall_material_apply_all'))
        self.apply_all_material_button.clicked.connect(self.apply_material_to_form)
        properties.addRow(self.apply_all_material_button)
        properties.addRow(owner.tr('wall_pattern'),self.pattern)
        self.material.currentIndexChanged.connect(self.change_appearance)
        self.pattern.currentIndexChanged.connect(self.change_appearance)
        panel.addLayout(properties)
        material_hint = QLabel(owner.tr('wall_material_hint'))
        material_hint.setWordWrap(True)
        panel.addWidget(material_hint)
        priority_hint = QLabel(owner.tr('wall_priority_hint'))
        priority_hint.setWordWrap(True)
        panel.addWidget(priority_hint)
        self.direction = QComboBox()
        self.direction.addItem(owner.tr('wall_side_left'), 1)
        self.direction.addItem(owner.tr('wall_side_right'), -1)
        self.direction.currentIndexChanged.connect(self.change_direction)
        panel.addWidget(self.direction)
        body.addLayout(panel, 2)
        layout.addLayout(body, 1)
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        self.confirm_shared = QCheckBox(owner.tr('wall_shared_confirm'))
        self.confirm_shared.toggled.connect(self.update_apply)
        layout.addWidget(self.confirm_shared)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel)
        self.apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        self.apply_button.setText(owner.tr('wall_sides_place' if placing else 'wall_sides_apply'))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(owner.tr('cancel'))
        self.apply_button.clicked.connect(self.try_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.table.selectRow(0)
        self.table.itemSelectionChanged.connect(self.select_side)
        self.refresh()

    def change_width(self, row):
        side = self.sides[row]
        display = self.spins[row].value()
        value = self.original_values[side.index] if display == self.initial_display[row] else display_units_to_meters(display, self.system)*self.density
        self.values[side.index] = value
        # If both faces of a divider are in this selection, keep the fields aligned.
        for other, target in enumerate(self.sides):
            if other != row and 'kind' not in side.shape and 'kind' not in target.shape and relation(side.shape, target.shape):
                self.values[target.index] = value
                self.spins[other].blockSignals(True)
                self.spins[other].setValue(meters_to_display_units(value/self.density, self.system))
                self.spins[other].blockSignals(False)
        self.refresh()

    def change_priority(self, row, value):
        side = self.sides[row]
        self.priorities[side.index] = value
        for other in self.sides:
            if same_wall_faces(side.shape, other.shape):
                self.priorities[other.index] = value
        self.table.selectRow(row)
        self.refresh()

    def select_side(self):
        row = self.table.currentRow()
        if row < 0:
            return
        side = self.sides[row]
        material,pattern = appearance(self.appearances[side.index])
        for combo,value in ((self.material,material),(self.pattern,pattern)):
            combo.blockSignals(True)
            combo.setCurrentIndex(combo.findData(value))
            combo.setEnabled(self.values[side.index] > 0)
            combo.blockSignals(False)
        for i,key in enumerate(PATTERNS):
            self.pattern.setItemIcon(i,appearance_icon(self.owner,material,key))
        for i,s in enumerate(self.sides):
            m,p = appearance(self.appearances[s.index])
            self.table.item(i,1).setToolTip(self.owner.tr('wall_material_'+m)+' · '+self.owner.tr('wall_pattern_'+p))
        targets = self.material_targets()
        self.apply_all_material_button.setEnabled(len(targets) > 1)
        self.apply_all_material_button.setToolTip(self.owner.tr(
            'wall_material_apply_all_hint' if targets else 'wall_material_apply_all_scope'))
        self.direction.blockSignals(True)
        self.direction.setCurrentIndex(self.direction.findData(side.side))
        self.direction.blockSignals(False)
        self.direction.setVisible(side.open and side.shape.get('wall', {}).get('reference') != 'axis')
        self.draw_preview()

    def change_appearance(self):
        row = self.table.currentRow()
        if row < 0:
            return
        side = self.sides[row]
        value = validated_appearance(dict(material=self.material.currentData(),pattern=self.pattern.currentData()))
        self.appearances[side.index] = value
        for other in self.sides:
            if same_wall_faces(side.shape,other.shape):
                self.appearances[other.index] = dict(value)
        self.refresh()

    def material_targets(self):
        row = self.table.currentRow()
        if row < 0 or self.values[self.sides[row].index] <= 0:
            return []
        forms = [indices for indices in self.material_forms if self.sides[row].index in indices]
        # A shared side alone cannot choose between two selected shapes.
        if len(forms) != 1:
            return []
        return [side for side in self.sides if side.index in forms[0] and self.values[side.index] > 0]

    def apply_material_to_form(self):
        targets = self.material_targets()
        if len(targets) < 2:
            return
        material = self.material.currentData()
        for side in targets:
            _previous, pattern = appearance(self.appearances[side.index])
            value = validated_appearance(dict(material=material, pattern=pattern))
            self.appearances[side.index] = value
            for other in self.sides:
                if same_wall_faces(side.shape, other.shape):
                    self.appearances[other.index] = dict(value)
        self.refresh()

    def change_direction(self):
        row = self.table.currentRow()
        if row >= 0:
            self.sides[row] = replace(self.sides[row], side=self.direction.currentData())
            self.refresh()

    def refresh(self):
        self.result = self.candidate = None
        self.error = None
        try:
            self.result = apply_side_widths(self.state, self.sides, self.values, self.owner.floorplan_view.scene.sceneRect(), anchor=self.anchor, appearances=self.appearances, priorities=self.priorities, fixed_state=self.fixed_state, fixed_rooms=self.fixed_rooms)
            validate_survey_layout(self.owner, self.result)
            document = deepcopy(self.owner.plan_tools.controller.layer_document())
            active_layer(document)['drawing'] = self.result.state
            self.candidate = validate_document(document)
            VectorPlanSource.from_layers(self.owner.floorplan_view.pixmap_item.pixmap().size(), self.candidate['layers'])
            count = sum(math.hypot(*m) > 1e-5 for m in self.result.moves)
            self.status.setText(self.owner.tr('wall_conversion_ready') if self.converted else self.owner.tr('wall_side_one_moved') if count == 1 else self.owner.tr('wall_moved').format(count=count) if count else self.owner.tr('wall_sides_ready'))
            self.status.setStyleSheet('')
        except (ValueError, KeyError, TypeError, OverflowError) as error:
            self.error = str(error)
            self.candidate = None
            key = ('wall_fixed_fit' if (self.fixed_state is not None or self.fixed_rooms) and self.error in ('wall_constraints_conflict','wall_room_collision')
                   else self.error if self.error.startswith('wall_') else 'rectangle_invalid_drawing')
            self.status.setText(self.owner.tr(key))
            self.status.setStyleSheet('color:#ef4444')
        for i, side in enumerate(self.sides):
            check = self.priority_checks[i]
            check.blockSignals(True)
            check.setChecked(self.priorities[side.index])
            check.setEnabled(self.values[side.index] > 0)
            check.blockSignals(False)
        signature = tuple((s.index, self.values[s.index], appearance(self.appearances[s.index]), self.priorities[s.index]) for s in self.sides
                          if s.shared and (self.values[s.index] != self.original_values[s.index] or self.appearances[s.index] != self.original_appearances[s.index] or self.priorities[s.index] != self.original_priorities[s.index]))
        if signature != self.shared_signature:
            self.confirm_shared.setChecked(False)
        self.shared_signature = signature
        self.confirm_shared.setVisible(bool(signature))
        notice_key = ('wall_shared_fixed_changed' if self.fixed_rooms else
                      'wall_shared_placement_changed' if self.placing and not self.converted else 'wall_shared_changed')
        self.notice.setText(self.owner.tr(notice_key) if signature else '')
        self.notice.setVisible(bool(signature))
        self.select_side()
        self.update_apply()

    def update_apply(self):
        self.apply_button.setEnabled(self.candidate is not None and (not self.shared_signature or self.confirm_shared.isChecked()))

    def try_accept(self):
        self.refresh()
        if self.apply_button.isEnabled():
            self.accept()

    def preview_shape(self, side):
        owner = self.preview_owners[side.index]
        move = self.result.moves[owner] if self.result is not None and owner is not None and owner < len(self.result.moves) else (0,0)
        shape = (transform_curves([side.shape], dx=move[0], dy=move[1]) if 'kind' in side.shape
                 else translate_segments([side.shape], *move))[0]
        if not self.values[side.index]:
            shape.pop('wall', None)
            return shape
        directed = shape['wall']['side'] if shape.get('wall', {}).get('reference') else side.side
        profile = dict(shape.get('wall', {}), width=self.values[side.index], side=directed)
        for key in ('material','pattern','priority'):
            profile.pop(key, None)
        profile.update(self.appearances[side.index])
        if self.priorities[side.index]:
            profile['priority'] = True
        shape['wall'] = profile
        return shape

    def draw_preview(self):
        scene = self.preview.scene()
        scene.clear()
        self.preview.paths = []
        focus = QRectF()
        row = self.table.currentRow()
        display = self.result.state if self.result is not None else self.state
        if display is not self._preview_state:
            preview_lines, preview_curves = display['segments'] or [], display['curves']
            try:
                self._preview_commands = list(wall_commands(preview_lines, preview_curves, display['annotations']))
            except ValueError:
                self._preview_commands = []  # refresh reports invalid geometry.
            try:
                self._preview_ink = WallReferenceInk(preview_lines, preview_curves)
            except ValueError:
                self._preview_ink = WallReferenceInk()
            self._preview_state = display
        for path, pen, brush in self._preview_commands:
            scene.addItem(wall_item(path, pen, brush))
        ink = self._preview_ink
        for i, side in enumerate(self.sides):
            shape = self.preview_shape(side)
            path = side_path(shape)
            self.preview.paths.append(path)
            box = path.boundingRect()
            focus = focus.united(box.adjusted(-1,-1,1,1))
            width = self.values[side.index]
            if width:
                try:
                    body = solid(shape)
                    focus = focus.united(body.boundingRect())
                    hit = QPainterPath(path)
                    hit.addPath(body)
                    self.preview.paths[-1] = hit
                except ValueError:
                    pass  # Invalid radius is reported and Apply is disabled.
            color = '#2563eb' if i == row else '#c07412' if side.shared else '#374151'
            pen = QPen(QColor(color), 4 if i == row else 2)
            pen.setCosmetic(True)
            visible, line_pen, brush = (path, pen, None) if i == row else ink.command(shape, path, pen)
            item = scene.addPath(visible, line_pen)
            if brush is not None:
                item.setBrush(brush)
            middle = point_at(shape, .5) if 'kind' in shape else ((shape['x1']+shape['x2'])/2, (shape['y1']+shape['y2'])/2)
            text = scene.addSimpleText(str(i+1))
            text.setBrush(QColor(color))
            text.setFlag(text.GraphicsItemFlag.ItemIgnoresTransformations)
            text.setPos(*middle)
        margin = max(20, max(focus.width(), focus.height())*.12)
        self.preview.focus_rect = focus.adjusted(-margin,-margin,margin,margin)
        scene.setSceneRect(self.preview.focus_rect)
        self.preview.fit()


def _review(owner, state, sides, anchor=0, *, placing=False, form_indices=None, fixed_state=None, fixed_rooms=()):
    drawing = owner.plan_tools.controller
    if not sides or not drawing.tools.structure_available() or not drawing.editable() or owner.scan_in_progress or drawing.wall_dialog_open:
        return False
    token, session, pixmap = deepcopy(owner.session.metadata), owner.session, owner.floorplan_view.pixmap_item
    drawing.wall_dialog_open = True
    dialog = None
    try:
        drawing.cancel()
        dialog = WallSidesDialog(owner, state, sides, anchor, placing=placing, form_indices=form_indices, fixed_state=fixed_state, fixed_rooms=fixed_rooms)
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.apply_button.isEnabled():
            return False
        if owner.session is not session or owner.floorplan_view.pixmap_item is not pixmap or owner.session.metadata != token or owner.scan_in_progress:
            owner.status.showMessage(owner.tr('wall_stale'))
            return False
        validate_survey_layout(owner, dialog.result)
        return drawing.apply_edit(**dialog.result.state)
    except (ValueError, KeyError, TypeError, OverflowError) as error:
        key = str(error)
        owner.status.showMessage(owner.tr(key if key.startswith('wall_') else 'rectangle_invalid_drawing'))
        return False
    finally:
        drawing.wall_dialog_open = False
        if dialog is not None:
            dialog.deleteLater()


def place_structure(drawing, lines=(), curves=()):
    try:
        state = active_layer(drawing.layer_document())['drawing']
        staged, sides, anchor = stage_structure(state, lines, curves)
        return _review(drawing.owner, staged, sides, anchor, placing=True, fixed_state=state)
    except (ValueError, KeyError, TypeError, OverflowError) as error:
        key = str(error)
        if key in ('wall_constraints_conflict','wall_room_collision'):
            key = 'wall_fixed_fit'
        drawing.owner.status.showMessage(drawing.owner.tr(key if key.startswith('wall_') else 'rectangle_invalid_drawing'))
        return False


def edit_wall_sides(owner, region=None):
    drawing = owner.plan_tools.controller
    if not drawing.tools.structure_available() or not drawing.editable() or drawing.selection.moving or drawing.rotation.active:
        return False
    state = active_layer(drawing.layer_document())['drawing']
    lines = region.lines if region else drawing.selection.selected
    curves = region.curves if region else drawing.selection.selected_curves
    indices = [*lines, *(len(state['segments'] or [])+i for i in curves)]
    rooms = reference_regions(state).records
    selected_room = next((i for i,(_p,r) in enumerate(rooms) if set(r.lines) == set(lines) and set(r.curves) == set(curves)), None)
    anchor = selected_room if selected_room is not None else 0
    fixed_rooms = tuple(i for i in range(len(rooms)) if i != selected_room) if selected_room is not None else ()
    return _review(owner, state, wall_sides(state, indices), anchor,
                   form_indices=indices if region is not None else None, fixed_rooms=fixed_rooms)
