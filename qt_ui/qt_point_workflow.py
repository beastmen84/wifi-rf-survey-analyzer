"""Qt dialogs and worker used while adding a measured survey point."""

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QMessageBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app_core.logging import log_event, log_exception
from qt_ui.scaling import widget_px
from wifi.scanner import scan_wifi


class PointCaptureMixin:
    def create_point_from_floorplan(self, x, y):
        if self.session is None:
            self.new_survey()
            if self.session is None:
                return

        if not self.floorplan_view.has_floorplan():
            QMessageBox.warning(self, self.tr("warning"), self.tr("load_plan_first"))
            return

        if self.scan_in_progress:
            return

        self.pending_rescan_point = None
        self.start_wifi_scan(x, y)

    def start_wifi_scan(self, x, y):
        self.pending_scan_point = (int(x), int(y))
        self.set_scan_busy(True, self.tr("scanning", x=int(x), y=int(y)))
        log_event(f"qt point scan start x={int(x)} y={int(y)}", logger_name="main")

        thread = QThread(self)
        worker = WifiScanWorker("auto")
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self.finish_wifi_scan)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(self.fail_wifi_scan)
        worker.failed.connect(thread.quit)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(self.cleanup_wifi_scan_thread)
        thread.finished.connect(thread.deleteLater)
        self.scan_thread = thread
        self.scan_worker = worker
        thread.start()

    def finish_wifi_scan(self, networks, backend_used):
        try:
            x, y = self.pending_scan_point or (None, None)
            self.set_scan_busy(False)
            self.last_scan_backend_used = backend_used
            log_event(f"qt point scan finished backend={backend_used} networks={len(networks or [])}", logger_name="main")

            if x is None or y is None:
                return

            if not networks:
                self.pending_scan_point = None
                self.pending_rescan_point = None
                QMessageBox.critical(self, self.tr("error"), self.tr("no_networks_found"))
                return

            action = self.validate_relevant_networks(networks)
            log_event(f"qt point relevant validation action={action}", logger_name="main")
            if action == "retry":
                self.start_wifi_scan(x, y)
                return
            if action == "cancel":
                self.pending_scan_point = None
                self.pending_rescan_point = None
                self.status.showMessage(self.tr("cancelled"))
                return

            rescan_point = self.pending_rescan_point
            self.pending_scan_point = None
            self.pending_rescan_point = None
            removed_rows = 0
            if rescan_point:
                removed_rows = self.delete_point(rescan_point, refresh=False)
            self.save_survey_point(
                x,
                y,
                networks,
                status_message=self.tr(
                    "point_rescanned" if rescan_point else "point_saved",
                    x=x,
                    y=y,
                    count=len(networks),
                    rows=removed_rows,
                ),
            )
        except Exception as exc:
            log_exception("finish_wifi_scan failed", exc, logger_name="main")
            self.pending_scan_point = None
            self.pending_rescan_point = None
            self.set_scan_busy(False)
            QMessageBox.critical(self, self.tr("error"), str(exc))

    def fail_wifi_scan(self, message):
        log_event(f"qt point scan failed message={message}", logger_name="main")
        self.set_scan_busy(False)
        self.pending_scan_point = None
        self.pending_rescan_point = None
        QMessageBox.critical(self, self.tr("error"), message)

    def cleanup_wifi_scan_thread(self):
        finished_thread = self.sender()
        if finished_thread is self.scan_thread:
            self.scan_thread = None
            self.scan_worker = None
        log_event("qt point scan thread cleaned up", logger_name="main")

    def set_scan_busy(self, is_busy, message=None):
        self.scan_in_progress = is_busy
        if is_busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            if QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()

        if message:
            self.status.showMessage(message)
        self.refresh_session_labels()

    def validate_relevant_networks(self, networks):
        detected_ssids = self.get_detected_ssids(networks)
        if not detected_ssids:
            return "keep"

        connected_ssid = self.get_connected_ssid_from_scan(networks)
        if not self.relevant_ssids and not self.known_ssids:
            dialog = RelevantNetworksDialog(
                self,
                detected_ssids,
                self.tr("relevant_networks_title"),
                self.tr("relevant_networks_first_message"),
                connected_ssid=connected_ssid,
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return "cancel"

            self.set_relevant_ssids(dialog.selected_ssids())
            self.known_ssids |= detected_ssids
            self.save_known_ssids()
            return "keep"

        missing_ssids = sorted(self.relevant_ssids - detected_ssids, key=str.casefold)
        if self.relevant_ssids and missing_ssids:
            dialog = MissingRelevantNetworksDialog(self, missing_ssids)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return "cancel"
            return dialog.action

        new_ssids = sorted(detected_ssids - self.known_ssids, key=str.casefold)
        if new_ssids:
            dialog = RelevantNetworksDialog(
                self,
                new_ssids,
                self.tr("new_relevant_networks_title"),
                self.tr("new_relevant_networks_message"),
                connected_ssid=connected_ssid,
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return "cancel"

            selected = dialog.selected_ssids()
            if selected:
                self.set_relevant_ssids(self.relevant_ssids | selected)
            self.known_ssids |= detected_ssids
            self.save_known_ssids()

        return "keep"

    def get_detected_ssids(self, networks):
        return {
            str(network.get("ssid", "")).strip()
            for network in networks or []
            if str(network.get("ssid", "")).strip()
        }

    def get_connected_ssid_from_scan(self, networks):
        connected_ssids = sorted({
            str(network.get("ssid", "")).strip()
            for network in networks or []
            if network.get("is_connected") and str(network.get("ssid", "")).strip()
        }, key=str.casefold)
        return connected_ssids[0] if connected_ssids else ""

    def save_survey_point(self, x, y, networks, status_message=None):
        if self.session is None:
            return

        if not networks:
            QMessageBox.critical(self, self.tr("error"), self.tr("no_networks_found"))
            return

        log_event(f"qt save point start x={x} y={y} networks={len(networks or [])}", logger_name="main")
        timestamp = self.session.add_points(
            x,
            y,
            networks,
            raw_networks=networks,
            relevant_ssids=self.relevant_ssids,
        )
        self.refresh_session_labels()
        self.refresh_points_table()
        self.status.showMessage(status_message or self.tr("point_saved", x=x, y=y, count=len(networks)))
        self.points_table.selectRow(0)
        self.maybe_update_live_preview()
        log_event(f"qt save point done timestamp={timestamp}", logger_name="main")


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
    def __init__(self, app, ssids, title, message, connected_ssid=None, selected_ssids=None):
        super().__init__(app)
        self.app = app
        self.ssids = sorted({str(ssid).strip() for ssid in ssids if str(ssid).strip()}, key=str.casefold)
        self.connected_ssid = str(connected_ssid or "").strip()
        self.initial_selected_ssids = {
            str(ssid).strip().lower()
            for ssid in (selected_ssids or [])
            if str(ssid).strip()
        } if selected_ssids is not None else None
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
            checkbox.setChecked(
                ssid.lower() in self.initial_selected_ssids
                if self.initial_selected_ssids is not None
                else is_connected
            )
            self.checkboxes[ssid] = checkbox
            choices_layout.addWidget(checkbox)

        choices_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save_button = QPushButton(self.app.tr("save"))
        cancel_button = QPushButton(self.app.tr("cancel"))
        prepare_dialog_action_button(self, save_button)
        prepare_dialog_action_button(self, cancel_button)
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
        for button in (keep_button, retry_button, cancel_button):
            prepare_dialog_action_button(self, button)
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


def prepare_dialog_action_button(dialog, button):
    button.setObjectName("compactButton")
    button.setMinimumHeight(widget_px(dialog, 30))
    button.setMinimumWidth(max(widget_px(dialog, 112), button.sizeHint().width()))
