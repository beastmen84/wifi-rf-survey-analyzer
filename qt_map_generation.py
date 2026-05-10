from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QVBoxLayout,
)

from constants import HEATMAP_MAX_DISTANCE_PX, HEATMAP_SMOOTHING_SIGMA
from map_config import MapConfig


class MapGenerationDialog(QDialog):
    def __init__(self, parent, ssids, tr, current_config=None, px_per_meter=None):
        super().__init__(parent)
        self.tr = tr
        self.px_per_meter = px_per_meter
        self.setWindowTitle(tr("generate_heatmap"))
        self.setModal(True)
        self.resize(760, 520)

        current_config = current_config or MapConfig()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        layout.addLayout(grid)

        self.ssid_combo = QComboBox()
        self.ssid_combo.setMinimumWidth(260)
        self.ssid_combo.addItems(ssids)
        if current_config.ssid in ssids:
            self.ssid_combo.setCurrentText(current_config.ssid)
        elif ssids:
            self.ssid_combo.setCurrentIndex(0)

        self.band_combo = QComboBox()
        self.map_type_combo = QComboBox()
        self.interpolation_combo = QComboBox()
        self.aggregation_combo = QComboBox()
        self.color_scale_combo = QComboBox()
        self.interference_mode_combo = QComboBox()
        self.point_labels_combo = QComboBox()
        self.usable_check = QCheckBox(tr("usable_only"))
        self.smoothing_spin = QDoubleSpinBox()
        self.distance_spin = QDoubleSpinBox()

        self.set_combo_items(
            self.band_combo,
            [
                ("all", tr("all_bands_option")),
                ("2.4", "2.4 GHz"),
                ("5", "5 GHz"),
            ],
        )
        self.set_combo_items(
            self.map_type_combo,
            [
                ("signal", tr("map_type_signal")),
                ("interference", tr("map_type_interference")),
                ("channel", tr("map_type_channel")),
                ("dominant", tr("map_type_dominant")),
            ],
        )
        self.set_combo_items(
            self.interpolation_combo,
            [
                ("rbf", tr("interpolation_rbf")),
                ("linear", tr("interpolation_linear")),
            ],
        )
        self.set_combo_items(
            self.aggregation_combo,
            [
                ("max", tr("aggregation_max")),
                ("median", tr("aggregation_median")),
                ("mean", tr("aggregation_mean")),
            ],
        )
        self.set_combo_items(
            self.color_scale_combo,
            [
                ("fixed", tr("color_scale_fixed")),
                ("auto", tr("color_scale_auto")),
            ],
        )
        self.set_combo_items(
            self.interference_mode_combo,
            [
                ("intra_ssid", tr("interference_mode_intra_ssid")),
                ("all", tr("interference_mode_all")),
            ],
        )
        self.set_combo_items(
            self.point_labels_combo,
            [
                ("auto", tr("point_labels_auto")),
                ("critical", tr("point_labels_critical")),
                ("all", tr("point_labels_all")),
                ("none", tr("point_labels_none")),
            ],
        )

        self.smoothing_spin.setRange(0.0, 12.0)
        self.smoothing_spin.setSingleStep(0.5)
        self.smoothing_spin.setDecimals(1)
        self.smoothing_spin.setValue(float(current_config.smoothing_sigma or HEATMAP_SMOOTHING_SIGMA))

        if self.px_per_meter:
            self.distance_spin.setRange(1.0, 50.0)
            self.distance_spin.setSingleStep(0.5)
            self.distance_spin.setDecimals(1)
            self.distance_spin.setSuffix(" m")
            self.distance_spin.setValue(max(1.0, current_config.max_distance_px / self.px_per_meter))
            distance_label = tr("max_distance_m")
        else:
            self.distance_spin.setRange(40.0, 1000.0)
            self.distance_spin.setSingleStep(20.0)
            self.distance_spin.setDecimals(0)
            self.distance_spin.setSuffix(" px")
            self.distance_spin.setValue(float(current_config.max_distance_px or HEATMAP_MAX_DISTANCE_PX))
            distance_label = tr("max_distance_px")

        self.set_combo_value(self.band_combo, current_config.band)
        self.set_combo_value(self.map_type_combo, current_config.map_type)
        self.set_combo_value(self.interpolation_combo, current_config.interpolation)
        self.set_combo_value(self.aggregation_combo, current_config.aggregation)
        self.set_combo_value(self.color_scale_combo, current_config.color_scale)
        self.set_combo_value(self.interference_mode_combo, current_config.interference_mode)
        self.set_combo_value(self.point_labels_combo, current_config.point_label_mode)
        self.usable_check.setChecked(bool(current_config.usable_only))

        rows = [
            ("SSID", self.ssid_combo),
            (tr("band"), self.band_combo),
            (tr("map_type"), self.map_type_combo),
            (tr("interpolation"), self.interpolation_combo),
            (tr("aggregation"), self.aggregation_combo),
            (tr("color_scale"), self.color_scale_combo),
            (tr("interference_mode"), self.interference_mode_combo),
            (tr("point_labels"), self.point_labels_combo),
            (tr("smoothing") if tr("smoothing") != "smoothing" else "Smoothing", self.smoothing_spin),
            (distance_label, self.distance_spin),
        ]
        for row_index, (label, widget) in enumerate(rows):
            label_widget = QLabel(label)
            label_widget.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(label_widget, row_index, 0)
            grid.addWidget(widget, row_index, 1)

        grid.addWidget(self.usable_check, len(rows), 1)
        grid.setColumnStretch(1, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("generate"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.map_type_combo.currentIndexChanged.connect(self.update_state)
        self.band_combo.currentIndexChanged.connect(self.update_state)
        self.update_state()

    def set_combo_items(self, combo, items):
        combo.clear()
        for value, label in items:
            combo.addItem(label, value)

    def set_combo_value(self, combo, value):
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def current_combo_value(self, combo, default=""):
        value = combo.currentData()
        return default if value is None else str(value)

    def update_state(self):
        map_type = self.current_combo_value(self.map_type_combo, "signal")
        is_signal = map_type == "signal"
        is_interference = map_type == "interference"
        is_discrete = map_type in {"channel", "dominant"}

        if is_interference and self.current_combo_value(self.band_combo) == "all":
            index = self.band_combo.findData("2.4")
            if index >= 0:
                self.band_combo.blockSignals(True)
                self.band_combo.setCurrentIndex(index)
                self.band_combo.blockSignals(False)

        self.interpolation_combo.setEnabled(is_signal or is_interference)
        self.smoothing_spin.setEnabled(is_signal or is_interference)
        self.distance_spin.setEnabled(is_signal or is_interference)
        self.aggregation_combo.setEnabled(is_signal)
        self.color_scale_combo.setEnabled(is_signal)
        self.usable_check.setEnabled(is_signal)
        self.interference_mode_combo.setEnabled(is_interference)
        self.point_labels_combo.setEnabled(is_interference or is_discrete)

    def get_config(self, ap_group_map=(), ap_group_roles=()):
        if self.px_per_meter:
            max_distance_px = max(1, int(round(self.distance_spin.value() * self.px_per_meter)))
        else:
            max_distance_px = max(1, int(round(self.distance_spin.value())))

        return MapConfig(
            ssid=self.ssid_combo.currentText().strip(),
            band=self.current_combo_value(self.band_combo, "all"),
            map_type=self.current_combo_value(self.map_type_combo, "signal"),
            interference_mode=self.current_combo_value(self.interference_mode_combo, "intra_ssid"),
            interpolation=self.current_combo_value(self.interpolation_combo, "rbf"),
            aggregation=self.current_combo_value(self.aggregation_combo, "max"),
            color_scale=self.current_combo_value(self.color_scale_combo, "fixed"),
            point_label_mode=self.current_combo_value(self.point_labels_combo, "auto"),
            usable_only=self.usable_check.isChecked(),
            smoothing_sigma=float(self.smoothing_spin.value()),
            max_distance_px=max_distance_px,
            ap_group_map=ap_group_map,
            ap_group_roles=ap_group_roles,
        ).normalized()
