"""Survey units and explicit receiver selection, with asynchronous discovery."""

import math

from PySide6.QtCore import QThread, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QPushButton, QVBoxLayout, QDoubleSpinBox, QWidget,
)

from app_core.units import (MEASUREMENT_SYSTEM_IMPERIAL, MEASUREMENT_SYSTEM_METRIC,
    meters_to_display_units, display_units_to_meters, distance_unit_label)
from qt_ui.default_floorplan import (default_blank_dimensions_m, BLANK_PLAN_MIN_METERS, BLANK_PLAN_MAX_METERS)
from qt_ui.scaling import widget_px
from wifi.adapters import adapter_identity, adapter_name, list_wifi_adapters


class AdapterDiscoveryThread(QThread):
    result_ready = Signal(object, str)

    def run(self):
        try:
            self.result_ready.emit(list_wifi_adapters(), "")
        except Exception:
            self.result_ready.emit([], "capture_adapter_discovery_failed")


class SurveySetupDialog(QDialog):
    def __init__(self, app, *, adapter_only=False, preferred_id=""):
        super().__init__(app)
        self.setFont(app.font())
        self.app = app
        self.adapter_only = adapter_only
        self.preferred_id = preferred_id
        self.thread = None
        self.pending_result = None
        self.setWindowTitle(app.tr("capture_adapter_choose" if adapter_only else "survey_setup_title"))
        self.setMinimumWidth(widget_px(app, 560))
        self.setMaximumWidth(widget_px(app, 800))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(widget_px(app, 24) for _ in range(4)))
        layout.setSpacing(widget_px(app, 16))
        intro = QLabel(app.tr("capture_adapter_legacy_hint" if adapter_only else "survey_setup_hint"))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        form.setHorizontalSpacing(widget_px(app, 16))
        self.units_combo = QComboBox()
        for system in (MEASUREMENT_SYSTEM_METRIC, MEASUREMENT_SYSTEM_IMPERIAL):
            self.units_combo.addItem(app.tr("measurement_system_" + system), system)
        self.units_combo.setCurrentIndex(max(0, self.units_combo.findData(app.measurement_system)))
        if not adapter_only:
            form.addRow(app.tr("measurement_system"), self.units_combo)
        else:
            self.units_combo.hide()

        row = QHBoxLayout()
        self.adapter_combo = QComboBox()
        self.adapter_combo.setMinimumContentsLength(32)
        self.adapter_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.adapter_combo.currentIndexChanged.connect(self.update_selection)
        row.addWidget(self.adapter_combo, 1)
        self.refresh_button = QPushButton(app.tr("capture_adapter_refresh"))
        self.refresh_button.setObjectName("compactButton")
        self.refresh_button.setMinimumHeight(widget_px(app, 32))
        self.refresh_button.setAutoDefault(False)
        self.refresh_button.clicked.connect(self.refresh_adapters)
        row.addWidget(self.refresh_button)
        form.addRow(app.tr("capture_adapter_label"), row)
        layout.addLayout(form)

        self.details_label = QLabel()
        self.details_label.setTextFormat(Qt.TextFormat.PlainText)
        self.details_label.setWordWrap(True)
        self.details_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.details_label)
        hint = QLabel(app.tr("capture_adapter_fixed_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.blank_plan_group = QWidget()
        self.blank_plan_group.setObjectName("blankPlanGroup")
        blank_layout = QVBoxLayout(self.blank_plan_group)
        blank_layout.setContentsMargins(0, 0, 0, 0)
        blank_layout.setSpacing(widget_px(app, 10))
        self.blank_title = QLabel(app.tr("blank_plan_size"))
        blank_layout.addWidget(self.blank_title)
        blank_fields = QFormLayout()
        blank_fields.setContentsMargins(0, 0, 0, 0)
        blank_fields.setHorizontalSpacing(widget_px(app, 16))
        self.blank_width_spin = QDoubleSpinBox()
        self.blank_height_spin = QDoubleSpinBox()
        self.blank_units = self.units_combo.currentData()
        self.blank_dimensions_custom = False
        for spin in (self.blank_width_spin, self.blank_height_spin):
            spin.setObjectName("blankPlanDimension")
            spin.setDecimals(2)
            spin.setKeyboardTracking(False)
            spin.setMinimumWidth(widget_px(app, 130))
            spin.setMinimumHeight(widget_px(app, 36))
        self.set_blank_dimensions(*default_blank_dimensions_m(self.blank_units))
        self.blank_width_spin.valueChanged.connect(lambda value: self.remember_blank_dimension(0, value))
        self.blank_height_spin.valueChanged.connect(lambda value: self.remember_blank_dimension(1, value))
        blank_fields.addRow(app.tr("blank_plan_width"), self.blank_width_spin)
        blank_fields.addRow(app.tr("blank_plan_height"), self.blank_height_spin)
        label_width = max(form.labelForField(self.units_combo).sizeHint().width() if not adapter_only else 0,
                          form.labelForField(row).sizeHint().width())
        for spin in (self.blank_width_spin, self.blank_height_spin):
            blank_fields.labelForField(spin).setMinimumWidth(label_width)
        blank_layout.addLayout(blank_fields)
        self.blank_hint = QLabel(app.tr("blank_plan_size_hint"))
        self.blank_hint.setWordWrap(True)
        self.blank_hint.setMinimumHeight(self.blank_hint.fontMetrics().lineSpacing() * 3)
        blank_layout.addWidget(self.blank_hint)
        self.units_combo.currentIndexChanged.connect(self.change_blank_units)
        self.blank_plan_group.setVisible(not adapter_only)
        layout.addWidget(self.blank_plan_group)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText(app.tr("capture_adapter_use" if adapter_only else "survey_setup_create"))
        self.ok_button.setDefault(True)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(app.tr("cancel"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.ok_button.setEnabled(False)
        QTimer.singleShot(0, self.refresh_adapters)

    def refresh_adapters(self):
        if self.thread is not None:
            return
        current = self.selected_adapter()
        if current:
            self.preferred_id = current["id"]
        self.adapter_combo.clear()
        self.adapter_combo.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.ok_button.setEnabled(False)
        self.details_label.setText(self.app.tr("capture_adapter_loading"))
        self.thread = AdapterDiscoveryThread(self)
        self.thread.result_ready.connect(self.populate_adapters)
        self.thread.finished.connect(self.discovery_finished)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    @Slot(object, str)
    def populate_adapters(self, adapters, error):
        preferred_index = 0
        for index, adapter in enumerate(adapters):
            state = "not_ready" if not adapter["ready"] else "connected" if adapter["connected"] else "disconnected"
            text = f"{adapter_name(adapter)} — {self.app.tr('capture_adapter_' + state)}"
            self.adapter_combo.addItem(text, adapter)
            # The GUID also distinguishes two receivers with identical names.
            self.adapter_combo.setItemData(index, text + "\n" + adapter["id"], Qt.ItemDataRole.ToolTipRole)
            if adapter_identity(adapter["id"]) == adapter_identity(self.preferred_id):
                preferred_index = index
        self.adapter_combo.setCurrentIndex(preferred_index)
        self.adapter_combo.setEnabled(bool(adapters))
        self.update_selection()
        if not adapters:
            self.details_label.setText(self.app.tr(error or "capture_adapter_none"))

    def update_selection(self):
        adapter = self.selected_adapter()
        if not hasattr(self, "ok_button"):
            return
        self.ok_button.setEnabled(bool(adapter and adapter["ready"]))
        if adapter:
            state = "not_ready" if not adapter["ready"] else "connected" if adapter["connected"] else "disconnected"
            self.details_label.setText(adapter_name(adapter) + " — " + self.app.tr("capture_adapter_" + state)
                                       + "\n" + self.app.tr("capture_adapter_identity", id=adapter["id"]))

    def selected_adapter(self):
        return self.adapter_combo.currentData()

    def set_blank_dimensions(self, width_m, height_m):
        self.blank_dimensions_m = (width_m, height_m)
        for spin, meters in ((self.blank_width_spin, width_m), (self.blank_height_spin, height_m)):
            spin.blockSignals(True)
            spin.setRange(math.ceil(meters_to_display_units(BLANK_PLAN_MIN_METERS, self.blank_units) * 100) / 100,
                          math.floor(meters_to_display_units(BLANK_PLAN_MAX_METERS, self.blank_units) * 100) / 100)
            spin.setSuffix(" " + distance_unit_label(self.blank_units))
            spin.setValue(meters_to_display_units(meters, self.blank_units))
            spin.blockSignals(False)

    def remember_blank_dimension(self, index, value):
        self.blank_dimensions_custom = True
        dimensions = list(self.blank_dimensions_m)
        dimensions[index] = display_units_to_meters(value, self.blank_units)
        self.blank_dimensions_m = tuple(dimensions)

    def change_blank_units(self):
        self.blank_units = self.units_combo.currentData()
        self.set_blank_dimensions(*(self.blank_dimensions_m if self.blank_dimensions_custom
                                    else default_blank_dimensions_m(self.blank_units)))

    def options(self):
        adapter = self.selected_adapter() or {}
        result = {"measurement_system": self.units_combo.currentData(),
                  "adapter": {key: adapter.get(key, "") for key in ("id", "name", "description")}}
        if not self.adapter_only:
            result["blank_plan"] = {
                "width_m": self.blank_dimensions_m[0], "height_m": self.blank_dimensions_m[1]}
        return result

    def accept(self):
        adapter = self.selected_adapter()
        if adapter and adapter["ready"]:
            self.done(QDialog.DialogCode.Accepted)

    def reject(self):
        self.done(QDialog.DialogCode.Rejected)

    def done(self, result):
        # Keep the owner alive until native enumeration has released its thread.
        if self.thread is not None:
            self.pending_result = result
            self.buttons.setEnabled(False)
            return
        super().done(result)

    @Slot()
    def discovery_finished(self):
        self.thread = None
        self.refresh_button.setEnabled(True)
        if self.pending_result is not None:
            self.done(self.pending_result)
