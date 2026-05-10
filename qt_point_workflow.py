from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui_scaling import widget_px
from wifi_scanner import scan_wifi


class WifiScanWorker(QObject):
    finished = Signal(list, str)
    failed = Signal(str)

    def __init__(self, backend="auto"):
        super().__init__()
        self.backend = backend

    @Slot()
    def run(self):
        try:
            networks, backend_used = scan_wifi(self.backend, show_errors=False)
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        self.finished.emit(networks, backend_used)


class RelevantNetworksDialog(QDialog):
    def __init__(self, app, ssids, title, message, connected_ssid=None):
        super().__init__(app)
        self.app = app
        self.ssids = sorted({str(ssid).strip() for ssid in ssids if str(ssid).strip()}, key=str.casefold)
        self.connected_ssid = str(connected_ssid or "").strip()
        self.checkboxes = {}

        self.setWindowTitle(title)
        self.resize(widget_px(self, 560), widget_px(self, 520))
        self.setMinimumSize(widget_px(self, 460), widget_px(self, 360))
        self.build_ui(title, message)

    def build_ui(self, title, message):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(widget_px(self, 14), widget_px(self, 14), widget_px(self, 14), widget_px(self, 14))
        layout.setSpacing(widget_px(self, 10))

        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)

        body = QLabel(message)
        body.setWordWrap(True)
        layout.addWidget(body)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        choices_layout = QVBoxLayout(content)
        choices_layout.setContentsMargins(widget_px(self, 6), widget_px(self, 6), widget_px(self, 6), widget_px(self, 6))
        choices_layout.setSpacing(widget_px(self, 6))

        ordered_ssids = sorted(
            self.ssids,
            key=lambda value: (
                not bool(self.connected_ssid and value.lower() == self.connected_ssid.lower()),
                value.casefold(),
            ),
        )
        for ssid in ordered_ssids:
            is_connected = bool(self.connected_ssid and ssid.lower() == self.connected_ssid.lower())
            label = self.app.tr("connected_ssid_option", ssid=ssid) if is_connected else ssid
            checkbox = QCheckBox(label)
            checkbox.setObjectName("relevantNetworkCheckbox")
            checkbox.setChecked(is_connected)
            self.checkboxes[ssid] = checkbox
            choices_layout.addWidget(checkbox)

        choices_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save_button = QPushButton(self.app.tr("save"))
        cancel_button = QPushButton(self.app.tr("cancel"))
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

    def selected_ssids(self):
        return {
            ssid
            for ssid, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        }


class MissingRelevantNetworksDialog(QDialog):
    def __init__(self, app, missing_ssids):
        super().__init__(app)
        self.app = app
        self.missing_ssids = missing_ssids
        self.action = "cancel"

        self.setWindowTitle(app.tr("missing_relevant_networks_title"))
        self.resize(widget_px(self, 560), widget_px(self, 280))
        self.setMinimumSize(widget_px(self, 460), widget_px(self, 240))
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(widget_px(self, 16), widget_px(self, 16), widget_px(self, 16), widget_px(self, 16))
        layout.setSpacing(widget_px(self, 12))

        heading = QLabel(self.app.tr("missing_relevant_networks_title"))
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)

        body = QLabel(self.app.tr("missing_relevant_networks_message", ssids=", ".join(self.missing_ssids)))
        body.setWordWrap(True)
        layout.addWidget(body, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        keep_button = QPushButton(self.app.tr("keep_scan"))
        retry_button = QPushButton(self.app.tr("retry_scan"))
        cancel_button = QPushButton(self.app.tr("cancel_point"))
        keep_button.clicked.connect(lambda: self.choose("keep"))
        retry_button.clicked.connect(lambda: self.choose("retry"))
        cancel_button.clicked.connect(lambda: self.choose("cancel"))
        buttons.addWidget(keep_button)
        buttons.addWidget(retry_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

    def choose(self, action):
        self.action = action
        self.accept()
