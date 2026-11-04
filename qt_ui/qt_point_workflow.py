"""Qt dialogs and worker used while adding a measured survey point."""

from threading import Event

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
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
from qt_ui.qt_survey_setup import SurveySetupDialog
from qt_ui.qt_capture_dialog import GuidedCaptureDialog
from survey.measurement_quality import assess_measurement
from survey.measurement_presentation import measurement_cards
from wifi.scanner import scan_wifi, WifiScanError, WifiScanCancelled


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
        if self.scan_in_progress or self.session is None:
            return
        adapter = self.session.capture_adapter()
        if not adapter:
            # Legacy files retain unknown provenance. Choosing a receiver only
            # binds future points, without relabelling any existing evidence.
            ids = {str(row.get("adapter_id")) for row in self.session.rows if row.get("adapter_id")}
            dialog = SurveySetupDialog(self, adapter_only=True, preferred_id=next(iter(ids)) if len(ids) == 1 else "")
            try:
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    self.pending_rescan_point = None
                    return
                adapter = dialog.options()["adapter"]
                self.session.set_capture_adapter(adapter)
            finally:
                dialog.deleteLater()
        self.pending_scan_point = (int(x), int(y))
        self.set_scan_busy(True, self.tr("scanning", x=int(x), y=int(y)))
        self.capture_result = None
        self.capture_error = None
        self.capture_cancel_requested = False
        self.capture_dialog = GuidedCaptureDialog(self, int(x), int(y), adapter)
        self.capture_dialog.start_requested.connect(self.start_prepared_wifi_scan)
        self.capture_dialog.save_requested.connect(self.accept_wifi_capture)
        self.capture_dialog.retry_requested.connect(self.retry_wifi_capture)
        self.capture_dialog.discard_requested.connect(self.discard_wifi_capture)
        self.capture_dialog.show()
        self.capture_dialog.begin_preparation()

    def start_prepared_wifi_scan(self):
        if self.scan_thread is not None or self.capture_cancel_requested or not self.pending_scan_point:
            return
        x, y = self.pending_scan_point
        adapter = self.session.capture_adapter()
        self.capture_result = None
        self.capture_error = None
        log_event(f"qt point scan start x={int(x)} y={int(y)}", logger_name="main")

        thread = QThread(self)
        worker = WifiScanWorker("auto", adapter_id=adapter["id"])
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self.finish_wifi_scan)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.progress.connect(self.capture_dialog.update_progress)
        worker.failed.connect(self.fail_wifi_scan)
        worker.failed.connect(thread.quit)
        worker.failed.connect(worker.deleteLater)
        worker.cancelled.connect(thread.quit)
        worker.cancelled.connect(worker.deleteLater)
        worker.cancelled.connect(self.finish_cancelled_wifi_scan)
        thread.finished.connect(self.cleanup_wifi_scan_thread)
        thread.finished.connect(thread.deleteLater)
        self.scan_thread = thread
        self.scan_worker = worker
        thread.start()

    def finish_wifi_scan(self, networks, backend_used):
        self.capture_result = (networks, backend_used)
        if self.scan_thread is None:
            self.present_wifi_capture()

    def present_wifi_capture(self):
        if self.capture_cancel_requested or not self.capture_result or self.capture_dialog is None:
            return
        networks, backend_used = self.capture_result
        self.last_scan_backend_used = backend_used
        if not networks and getattr(networks, "capture", {}).get("status") != "complete":
            self.capture_error = "no_networks_found"
            self.capture_dialog.show_error(self.tr(self.capture_error))
            return
        assessment = self.assess_pending_capture()
        self.capture_dialog.show_review(assessment, self.relevant_ssids)

    def assess_pending_capture(self):
        networks = self.capture_result[0]
        return assess_measurement(networks, capture=getattr(networks, "capture", {}),
            relevant_ssids=self.relevant_ssids, expected_adapter_id=self.session.capture_adapter().get("id", ""))

    def accept_wifi_capture(self):
        if self.scan_thread is not None or not self.capture_result or self.capture_cancel_requested:
            return
        try:
            networks, _backend = self.capture_result
            x, y = self.pending_scan_point
            if not self.assess_pending_capture().can_save:
                return
            previous_scope = set(self.relevant_ssids)
            action = self.validate_relevant_networks(networks)
            if action == "retry":
                self.retry_wifi_capture()
                return
            if action == "cancel":
                self.discard_wifi_capture()
                return
            if previous_scope != set(self.relevant_ssids):
                self.present_wifi_capture()
                return
            rescan_point = self.pending_rescan_point
            assessment = self.assess_pending_capture()
            self.save_survey_point(x, y, networks)
            if rescan_point:
                self.delete_point(rescan_point, refresh=False)
                self.refresh_points_table()
                self.maybe_update_live_preview()
            cards = measurement_cards(assessment, self.tr)
            self.close_wifi_capture(saved=True)
            self.status.showMessage(self.tr("measurement_saved", **{card["key"]: card["value"] for card in cards}))
        except Exception as exc:
            log_exception("accept_wifi_capture failed", exc, logger_name="main")
            self.capture_dialog.show_error(self.tr(str(exc)))

    def fail_wifi_scan(self, message):
        log_event(f"qt point scan failed message={message}", logger_name="main")
        self.capture_error = message

    def finish_cancelled_wifi_scan(self):
        self.capture_cancel_requested = True

    def cleanup_wifi_scan_thread(self):
        finished_thread = self.sender()
        if finished_thread is self.scan_thread:
            self.scan_thread = None
            self.scan_worker = None
            if self.capture_cancel_requested:
                self.close_wifi_capture()
            elif self.capture_error:
                self.capture_dialog.show_error(self.tr(self.capture_error))
            else:
                self.present_wifi_capture()
        log_event("qt point scan thread cleaned up", logger_name="main")

    def retry_wifi_capture(self):
        if self.scan_thread is not None:
            return
        self.capture_result = None
        self.capture_error = None
        self.capture_dialog.begin_preparation()

    def discard_wifi_capture(self):
        self.capture_cancel_requested = True
        self.capture_dialog.timer.stop()
        if self.scan_worker is not None:
            self.scan_worker.cancel()
            self.capture_dialog.show_cancelling()
        else:
            self.close_wifi_capture()
        self.status.showMessage(self.tr("cancelled"))

    def close_wifi_capture(self, saved=False):
        dialog, self.capture_dialog = self.capture_dialog, None
        if dialog is not None:
            dialog.finish(saved=saved)
            dialog.deleteLater()
        self.pending_scan_point = None
        self.pending_rescan_point = None
        self.capture_result = None
        self.capture_error = None
        self.set_scan_busy(False)

    def set_scan_busy(self, is_busy, message=None):
        self.scan_in_progress = is_busy
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
            str(network.get("ssid", ""))
            for network in networks or []
            if str(network.get("ssid", ""))
        }

    def get_connected_ssid_from_scan(self, networks):
        connected_ssids = sorted({
            str(network.get("ssid", ""))
            for network in networks or []
            if network.get("is_connected") and str(network.get("ssid", ""))
        }, key=str.casefold)
        return connected_ssids[0] if connected_ssids else ""

    def save_survey_point(self, x, y, networks, status_message=None):
        if self.session is None:
            return

        if not networks and getattr(networks, "capture", {}).get("status") != "complete":
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
    finished = Signal(object, str)
    failed = Signal(str)
    progress = Signal(object)
    cancelled = Signal()

    def __init__(self, backend="auto", adapter_id=None):
        super().__init__()
        self.backend = backend
        self.adapter_id = adapter_id
        self.cancel_event = Event()

    def cancel(self):
        self.cancel_event.set()

    @Slot()
    def run(self):
        try:
            networks, backend_used = scan_wifi(self.backend, show_errors=False, adapter_id=self.adapter_id,
                progress=self.progress.emit, cancel_event=self.cancel_event)
            if self.cancel_event.is_set():
                raise WifiScanCancelled()
        except WifiScanCancelled:
            self.cancelled.emit()
            return
        except WifiScanError as exc:
            self.failed.emit(exc.message_key)
            return
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        self.finished.emit(networks, backend_used)


class RelevantNetworksDialog(QDialog):
    def __init__(self, app, ssids, title, message, connected_ssid=None, selected_ssids=None):
        super().__init__(app)
        self.app = app
        self.ssids = sorted({str(ssid) for ssid in ssids if str(ssid)}, key=str.casefold)
        self.connected_ssid = str(connected_ssid or "")
        self.initial_selected_ssids = {
            str(ssid)
            for ssid in (selected_ssids or [])
            if str(ssid)
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
                not bool(self.connected_ssid and value == self.connected_ssid),
                value.casefold(),
            ),
        )
        for ssid in ordered_ssids:
            is_connected = bool(self.connected_ssid and ssid == self.connected_ssid)
            label = self.app.tr("connected_ssid_option", ssid=ssid) if is_connected else ssid
            checkbox = QCheckBox(label)
            checkbox.setObjectName("relevantNetworkCheckbox")
            checkbox.setChecked(
                ssid in self.initial_selected_ssids
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

        button_spacing = buttons.spacing() if buttons.spacing() >= 0 else layout.spacing()
        required_width = (
            sum(button.minimumWidth() for button in (keep_button, retry_button, cancel_button))
            + button_spacing * 2
            + widget_px(self, 40)
        )
        self.setMinimumWidth(max(self.minimumWidth(), required_width))

    def choose(self, action):
        self.action = action
        self.accept()


def prepare_dialog_action_button(dialog, button):
    button.setObjectName("compactButton")
    button.setMinimumHeight(widget_px(dialog, 30))
    button.setMinimumWidth(max(widget_px(dialog, 112), button.sizeHint().width()))
