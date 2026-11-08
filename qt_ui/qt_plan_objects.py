"""Icon variants, dimensions and outline/fill controls for free annotations."""
from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QPlainTextEdit, QSpinBox)

from app_core.units import distance_unit_label, display_units_to_meters, meters_to_display_units
from qt_ui.qt_theme import QT_THEMES
from qt_ui.scaling import widget_px
from survey.plan_annotation_rendering import annotation_path
from survey.plan_objects import (DESK_VARIANTS, SYMBOL_VARIANTS, NUMBERED_SYMBOLS, NETWORK_SYMBOLS,
    GENERIC_SYMBOLS, object_default, object_is_round)
from qt_ui.qt_plan_colors import choose_plan_color


class ObjectAnnotationDialog(QDialog):
    def __init__(self, controller, item):
        super().__init__(controller.owner)
        self.controller, self.value = controller, deepcopy(item)
        self.owner, self.density = controller.owner, controller.owner.get_px_per_meter()
        self.kind, self.variant = item["kind"], item["variant"]
        self.setWindowTitle(self.owner.tr("annotation_" + self.kind))
        self.setMinimumWidth(widget_px(self.owner, 430))
        layout = QVBoxLayout(self)
        layout.setSpacing(widget_px(self.owner, 10))
        self.variant_group, self.variant_buttons = QButtonGroup(self), {}
        self.variants = DESK_VARIANTS if self.kind == "desk" else SYMBOL_VARIANTS
        rows = {}
        categories = (("annotation_type", DESK_VARIANTS),) if self.kind == "desk" else (
            ("symbol_numbered_group", NUMBERED_SYMBOLS), ("symbol_network_group", NETWORK_SYMBOLS),
            ("symbol_generic_group", GENERIC_SYMBOLS))
        for title, variants in categories:
            layout.addWidget(QLabel(self.owner.tr(title)))
            choices = QWidget()
            row = QHBoxLayout(choices)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(widget_px(self.owner, 4))
            for variant in variants:
                rows[variant] = row
            row.addStretch()
            layout.addWidget(choices)
        for index, variant in enumerate(self.variants):
            key = "object_" + self.kind + "_" + variant
            button = self.owner.create_boundaries_text_button("", key)
            button.setFixedSize(widget_px(self.owner, 46), widget_px(self.owner, 46))
            button.setCheckable(True)
            button.setToolTip(self.owner.tr(key))
            button.setAccessibleName(self.owner.tr(key))
            self.variant_group.addButton(button, index)
            self.variant_buttons[variant] = button
            rows[variant].insertWidget(rows[variant].count() - 1, button)
        self.form = QFormLayout()
        layout.addLayout(self.form)
        self.outline = self.color_button("color")
        self.form.addRow(self.owner.tr("object_outline_color"), self.outline)
        self.stroke = QDoubleSpinBox()
        self.stroke.setRange(.5, 20)
        self.stroke.setSingleStep(.5)
        self.stroke.setDecimals(1)
        self.stroke.setValue(item["stroke"])
        self.stroke.setSuffix(" px")
        self.form.addRow(self.owner.tr("object_outline_width"), self.stroke)
        fill_row = QWidget()
        fill_layout = QHBoxLayout(fill_row)
        fill_layout.setContentsMargins(0, 0, 0, 0)
        self.fill_enabled = QCheckBox(self.owner.tr("object_fill_enabled"))
        self.fill_enabled.setChecked(item.get("fill") is not None)
        if self.value.get("fill") is None:
            self.value["fill"] = "#ffffff"
        self.fill = self.color_button("fill")
        self.fill.setEnabled(self.fill_enabled.isChecked())
        self.fill_enabled.toggled.connect(self.fill.setEnabled)
        fill_layout.addWidget(self.fill_enabled)
        fill_layout.addWidget(self.fill, 1)
        self.form.addRow(self.owner.tr("object_fill_color"), fill_row)
        self.width_spin, self.height_spin, self.arm_spin = QDoubleSpinBox(), QDoubleSpinBox(), QDoubleSpinBox()
        maximum = max(controller.view.scene.sceneRect().width(), controller.view.scene.sceneRect().height()) / self.density
        for spin, key in ((self.width_spin, "width"), (self.height_spin, "height"), (self.arm_spin, "arm")):
            spin.setDecimals(2)
            spin.setRange(.01, max(.01, meters_to_display_units(maximum, self.owner.measurement_system)))
            spin.setSingleStep(.1 if self.owner.measurement_system == "metric" else 1)
            spin.setKeyboardTracking(False)
            spin.setSuffix(" " + distance_unit_label(self.owner.measurement_system))
            self.set_length(spin, item.get(key, min(item["width"], item["height"]) / 3))
        self.width_label, self.height_label = QLabel(), QLabel()
        self.arm_label = QLabel(self.owner.tr("object_arm_depth"))
        self.form.addRow(self.width_label, self.width_spin)
        self.form.addRow(self.height_label, self.height_spin)
        self.form.addRow(self.arm_label, self.arm_spin)
        self.numbered = QCheckBox(self.owner.tr("symbol_numbered"))
        self.numbered.setChecked(item.get("_numbered", "number" in item or item["id"] == "template"))
        self.form.addRow(self.numbered)
        self.description = QPlainTextEdit(item.get("description", ""))
        self.description.setMaximumHeight(widget_px(self.owner, 65))
        self.description.setPlaceholderText(self.owner.tr("legend_description"))
        self.description_label = QLabel(self.owner.tr("legend_description"))
        self.form.addRow(self.description_label, self.description)
        from survey.rack_inventory import MAX_SWITCHES
        self.rack_value=deepcopy(item.get('rack',{}))
        self.rack_label=QLabel(self.owner.tr('rack_switch_count'))
        self.rack_row=QWidget();rack_row=QHBoxLayout(self.rack_row);rack_row.setContentsMargins(0,0,0,0)
        self.rack_count=QSpinBox();self.rack_count.setRange(0,MAX_SWITCHES)
        self.rack_count.setMinimumWidth(widget_px(self.owner,130))
        self.rack_count.setValue(len(self.rack_value.get('switches',[])))
        self.rack_details=QPushButton(self.owner.tr('rack_configure'))
        self.rack_details.setObjectName('compactButton')
        self.rack_details.clicked.connect(self.configure_rack)
        rack_row.addWidget(self.rack_count);rack_row.addWidget(self.rack_details,1)
        self.form.addRow(self.rack_label,self.rack_row)
        self.width_spin.valueChanged.connect(self.update_dimensions)
        self.height_spin.valueChanged.connect(self.update_dimensions)
        self.variant_group.idClicked.connect(lambda index: self.choose_variant(self.variants[index]))
        hint = QLabel(self.owner.tr("object_properties_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(self.owner.tr("cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.choose_variant(self.variant)

    def color_button(self, key):
        button = QPushButton()
        button.setObjectName("compactButton")
        def update():
            button.setText(self.value[key])
            button.setStyleSheet("border:2px solid " + self.value[key] + ";padding:6px;")
        def choose():
            color = choose_plan_color(self.value[key], self)
            if color.isValid():
                self.value[key] = color.name()
                update()
        button.clicked.connect(choose)
        update()
        return button

    def set_length(self, spin, pixels):
        spin.setValue(meters_to_display_units(pixels / self.density, self.owner.measurement_system))

    def configure_rack(self):
        from survey.rack_inventory import resize_switches
        from qt_ui.qt_rack_inventory import RackConfigurationDialog
        dialog=RackConfigurationDialog(self.owner,resize_switches(self.rack_value,self.rack_count.value()))
        try:
            if dialog.exec()==QDialog.DialogCode.Accepted:
                self.rack_value=dialog.properties()
                self.rack_count.setValue(len(self.rack_value.get('switches',[])))
        finally:
            dialog.deleteLater()

    def choose_variant(self, variant):
        if variant != self.variant:
            defaults = object_default(self.kind, self.density, variant)
            for spin, key in ((self.width_spin, "width"), (self.height_spin, "height"), (self.arm_spin, "arm")):
                self.set_length(spin, defaults[key])
        self.variant = variant
        self.variant_buttons[variant].setChecked(True)
        self.update_dimensions()
        self.update_icons()

    def update_dimensions(self):
        square = (self.kind == "symbol" and self.variant != "rack") or self.variant in ("square", "l_equal", "round")
        elbow = self.kind == "desk" and self.variant in ("l", "l_equal")
        self.width_label.setText(self.owner.tr("blank_plan_width" if self.variant == "rack" else
                                              "object_diameter" if self.variant in ("circle", "round", "wifi_ap") else
                                              "object_symbol_size" if self.kind == "symbol" else
                                              "object_size" if square else "object_side_a" if elbow else "blank_plan_width"))
        self.height_label.setText(self.owner.tr("object_side_b" if elbow else "object_depth"))
        self.numbered.setVisible(self.kind == "symbol" and self.variant in NUMBERED_SYMBOLS)
        self.description.setVisible(self.kind == "symbol")
        self.description_label.setVisible(self.kind == "symbol")
        self.rack_label.setVisible(self.kind=='symbol' and self.variant=='rack')
        self.rack_row.setVisible(self.kind=='symbol' and self.variant=='rack')
        self.height_spin.setVisible(not square)
        self.height_label.setVisible(not square)
        self.arm_spin.setVisible(elbow)
        self.arm_label.setVisible(elbow)
        self.width_spin.setMinimum(.02 if elbow else .01)
        self.height_spin.setMinimum(.02 if elbow else .01)
        if elbow:
            limit = min(self.width_spin.value(), self.width_spin.value() if square else self.height_spin.value()) - .01
            self.arm_spin.setMaximum(max(.01, limit))

    def update_icons(self):
        size = widget_px(self.owner, 34)
        palette = QT_THEMES[self.owner.theme]
        for variant, button in self.variant_buttons.items():
            item = object_default(self.kind, 20, variant)
            path = annotation_path(item)
            bounds = path.boundingRect().adjusted(-2, -2, 2, 2)
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            scale = min(size / bounds.width(), size / bounds.height())
            painter.translate(size / 2, size / 2)
            painter.scale(scale, scale)
            painter.translate(-bounds.center().x(), -bounds.center().y())
            painter.setPen(QPen(QColor("#ffffff" if button.isChecked() else palette["text"]), 1.5 / scale))
            painter.setBrush(QColor(255, 255, 255, 45) if button.isChecked() else QColor(palette["panel_alt"]))
            painter.drawPath(path)
            painter.end()
            button.setIcon(QIcon(pixmap))
            button.setIconSize(pixmap.size())

    def properties(self):
        result = deepcopy(self.value)
        width = display_units_to_meters(self.width_spin.value(), self.owner.measurement_system) * self.density
        square = (self.kind == "symbol" and self.variant != "rack") or self.variant in ("square", "l_equal", "round")
        height = width if square else display_units_to_meters(self.height_spin.value(), self.owner.measurement_system) * self.density
        result.update(variant=self.variant, width=width, height=height, stroke=self.stroke.value(),
                      fill=self.value["fill"] if self.fill_enabled.isChecked() else None)
        if self.kind == "desk" and self.variant in ("l", "l_equal"):
            result["arm"] = display_units_to_meters(self.arm_spin.value(), self.owner.measurement_system) * self.density
        else:
            result.pop("arm", None)
        if object_is_round(result):
            result["angle"] = 0
        if self.kind == "symbol":
            result["_numbered"] = self.numbered.isChecked() and self.variant in NUMBERED_SYMBOLS
            result["description"] = self.description.toPlainText()[:2000]
        result.pop('rack',None)
        if self.kind=='symbol' and self.variant=='rack':
            from survey.rack_inventory import resize_switches,validate_rack
            rack=validate_rack(resize_switches(self.rack_value,self.rack_count.value()))
            if rack:
                result['rack']=rack
        return result
