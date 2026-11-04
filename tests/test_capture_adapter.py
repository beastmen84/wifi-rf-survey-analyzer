"""Receiver choice must survive save/reopen and constrain every new capture."""

from copy import deepcopy
from html import unescape
from threading import Event
from types import SimpleNamespace as NS
from unittest.mock import ANY, patch

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QMessageBox

from qt_ui.qt_app import WifiHeatmapQtApp
from qt_ui.qt_point_workflow import WifiScanWorker
from qt_ui.qt_survey_setup import SurveySetupDialog
from survey.store import SurveySession
from tests.test_advisor import qt_app
from tests.test_precision_regressions import fresh_sample
from translations.i18n import translate
from wifi.adapters import CAPTURE_ADAPTER_KEY, adapter_identity, list_wifi_adapters
from wifi import scanner

RECEIVER = {"id": "{00000000-0000-0000-0000-000000000001}", "name": "Wi-Fi", "description": "Test receiver"}
OTHER = {"id": "{00000000-0000-0000-0000-000000000002}", "name": "Wi-Fi 2", "description": "Test receiver"}


def interface(adapter, state="disconnected"):
    return NS(guid=adapter["id"], connection_name=adapter["name"], description=adapter["description"], state_string=state)


def wait_until(qt_app, predicate):
    for _ in range(500):
        qt_app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("Qt worker did not finish")


@pytest.fixture
def window(qt_app, tmp_path, monkeypatch):
    monkeypatch.setenv("WIFI_HEATMAP_SETTINGS_FILE", str(tmp_path / "settings.json"))
    monkeypatch.setenv("WIFI_HEATMAP_AP_MEMORY_FILE", str(tmp_path / "memory.json"))
    app = WifiHeatmapQtApp()
    yield app
    app.analysis_view.timer.stop()
    app.deleteLater()
    qt_app.processEvents()


def batch(adapter_id=RECEIVER["id"], empty=False):
    rows = [] if empty else scanner.merge_wifi_scans([fresh_sample(adapter=adapter_id)], 5)
    return scanner.ScanBatch(rows, {"adapter_id": adapter_id, "backend": "lswifi", "status": "complete", "freshness": "fresh"})


def test_discovery_prefers_connected_and_keeps_unassociated_receivers():
    from lswifi import wlanapi
    with patch.object(wlanapi.WLAN, "get_wireless_interfaces", return_value={
        0: interface(RECEIVER), 1: interface(OTHER, "connected")
    }):
        adapters = list_wifi_adapters()
    assert [row["id"] for row in adapters] == [OTHER["id"], RECEIVER["id"]]
    assert adapters[1]["ready"] and not adapters[1]["connected"]


@pytest.mark.parametrize("state", ["connected", "disconnected"])
def test_pinned_scan_uses_requested_receiver_even_if_another_is_connected(state):
    from lswifi import wlanapi
    requested = interface(RECEIVER, state)
    with (patch.object(wlanapi.WLAN, "get_wireless_interfaces", return_value={
        0: interface(OTHER, "connected"), 1: requested
    }), patch.object(scanner, "scan_and_wait", return_value={"status": "complete", "started": 100, "completed": 200}) as scan,
          patch.object(scanner, "read_bss_list", return_value=[]),
          patch.object(scanner, "get_lswifi_connected_network", return_value={}),
          patch.object(scanner.time, "sleep"), patch.object(scanner, "scan_wifi_netsh") as fallback):
        rows, backend = scanner.scan_wifi(adapter_id=adapter_identity(RECEIVER["id"]).upper(), show_errors=False)
    assert backend == "lswifi" and rows.capture["adapter_id"] == RECEIVER["id"]
    assert len(scan.call_args_list) == 5
    assert all(call.args[1] is requested for call in scan.call_args_list)
    fallback.assert_not_called()


@pytest.mark.parametrize("case", ["missing", "not_ready", "failed", "enumeration_error"])
def test_pinned_receiver_failure_never_falls_back_or_scans_another_adapter(case):
    from lswifi import wlanapi
    adapters = {0: interface(OTHER, "connected")}
    if case != "missing":
        adapters[1] = interface(RECEIVER, "not_ready" if case == "not_ready" else "disconnected")
    with (patch.object(wlanapi.WLAN, "get_wireless_interfaces", return_value=adapters,
                       side_effect=OSError() if case == "enumeration_error" else None),
          patch.object(scanner, "scan_and_wait", return_value={"status": "failed", "started": 100, "completed": 0}) as scan,
          patch.object(scanner.time, "sleep"), patch.object(scanner, "scan_wifi_netsh") as fallback):
        with pytest.raises(scanner.WifiScanError, match="capture_adapter_"):
            scanner.scan_wifi(adapter_id=RECEIVER["id"], show_errors=False)
    fallback.assert_not_called()
    if case in {"missing", "not_ready", "enumeration_error"}:
        scan.assert_not_called()


def test_pinned_receiver_rejects_netsh_backend():
    with patch.object(scanner, "scan_wifi_netsh") as fallback:
        with pytest.raises(scanner.WifiScanError, match="capture_adapter_native_required"):
            scanner.scan_wifi("netsh", adapter_id=RECEIVER["id"])
    fallback.assert_not_called()


@pytest.mark.parametrize("empty", [False, True])
def test_receiver_metadata_and_capture_provenance_roundtrip(tmp_path, empty):
    session = SurveySession()
    session.set_capture_adapter(RECEIVER, mark_dirty=False)
    assert not session.dirty
    session.add_points(10, 20, batch(empty=empty))
    path = str(tmp_path / "survey.csv")
    session.save(path)
    reopened = SurveySession(path)
    assert reopened.capture_adapter() == RECEIVER
    assert reopened.measurement_points()[0]["capture"]["adapter_id"] == RECEIVER["id"]
    if not empty:
        assert {row["adapter_id"] for row in reopened.raw_scan_rows + reopened.rows} == {RECEIVER["id"]}


@pytest.mark.parametrize("source", ["capture", "row", "raw", "sidecar", "unknown", "empty"])
def test_mismatched_capture_cannot_replace_or_append_to_existing_measurements(source):
    session = SurveySession()
    session.set_capture_adapter(RECEIVER)
    session.add_points(10, 20, batch())
    before = deepcopy((session.rows, session.raw_scan_rows, session.metadata))
    capture = batch(empty=source == "empty")
    sidecar = None
    if source in {"capture", "empty"}:
        capture.capture["adapter_id"] = OTHER["id"]
    elif source in {"row", "unknown"}:
        capture[0]["adapter_id"] = OTHER["id"] if source == "row" else ""
    elif source == "raw":
        capture[0]["raw_samples"][0]["adapter_id"] = OTHER["id"]
    else:
        sidecar = batch(OTHER["id"])
    with pytest.raises(ValueError, match="capture_adapter_mismatch"):
        session.add_points(30, 40, capture, raw_networks=sidecar)
    assert (session.rows, session.raw_scan_rows, session.metadata) == before


def test_fixed_receiver_cannot_be_changed_and_legacy_selection_does_not_relabel_rows():
    session = SurveySession()
    session.add_points(10, 20, batch(OTHER["id"]))
    before = deepcopy((session.rows, session.raw_scan_rows))
    assert not session.capture_adapter() and CAPTURE_ADAPTER_KEY not in session.metadata
    session.set_capture_adapter(RECEIVER)
    assert (session.rows, session.raw_scan_rows) == before
    with pytest.raises(ValueError, match="capture_adapter_mismatch"):
        session.set_capture_adapter(OTHER)


def test_new_survey_stores_choice_and_shows_it_after_reopen(window, tmp_path):
    options = {"measurement_system": "imperial", "adapter": RECEIVER}
    with patch.object(window, "choose_new_survey_options", return_value=options):
        assert window.new_survey(from_start_page=True)
    assert window.session.capture_adapter() == RECEIVER
    assert not window.session.dirty
    assert window.measurement_system == "imperial"
    path = str(tmp_path / "chosen.csv")
    window.session.csv_file = path
    assert window.save_survey()
    with patch.object(window, "choose_new_survey_options") as choose:
        assert window.open_survey(path)
    choose.assert_not_called()
    assert window.session.capture_adapter() == RECEIVER
    assert RECEIVER["description"] in window.capture_adapter_label.text()
    assert RECEIVER["id"] in window.capture_adapter_label.toolTip()


def test_setup_cancel_preserves_current_survey_and_units(window):
    window.session = SurveySession()
    previous = window.session
    units = window.measurement_system
    with (patch.object(window, "confirm_new_survey_replaces_current", return_value=True),
          patch.object(window, "choose_new_survey_options", return_value=None)):
        assert not window.new_survey()
    assert window.session is previous and window.measurement_system == units


@pytest.mark.parametrize("adapters,error", [([], ""), ([], "capture_adapter_discovery_failed"),
    ([dict(RECEIVER, ready=False, connected=False)], "")])
def test_setup_blocks_create_with_no_usable_receiver(window, qt_app, adapters, error):
    with patch("qt_ui.qt_survey_setup.list_wifi_adapters", side_effect=RuntimeError() if error else None, return_value=adapters):
        dialog = SurveySetupDialog(window)
        wait_until(qt_app, lambda: dialog.thread is None and dialog.refresh_button.isEnabled() and bool(dialog.details_label.text()))
        assert not dialog.ok_button.isEnabled()
        dialog.accept()
        assert dialog.result() != QDialog.DialogCode.Accepted
        dialog.reject()
        dialog.deleteLater()


def test_setup_selects_receiver_refreshes_and_returns_units(window, qt_app):
    adapters = [dict(OTHER, ready=True, connected=True), dict(RECEIVER, ready=True, connected=False)]
    with patch("qt_ui.qt_survey_setup.list_wifi_adapters", return_value=adapters):
        dialog = SurveySetupDialog(window)
        wait_until(qt_app, lambda: dialog.thread is None and dialog.adapter_combo.count() == 2)
        assert dialog.selected_adapter()["id"] == OTHER["id"]
        dialog.adapter_combo.setCurrentIndex(1)
        dialog.units_combo.setCurrentIndex(dialog.units_combo.findData("imperial"))
        dialog.refresh_adapters()
        wait_until(qt_app, lambda: dialog.thread is None)
        assert dialog.options() == {"measurement_system": "imperial", "adapter": RECEIVER}
        assert dialog.ok_button.isEnabled()
        dialog.reject()
        dialog.deleteLater()


def test_setup_cancel_waits_for_discovery_thread_to_release_resources(window, qt_app):
    entered, release = Event(), Event()

    def discover():
        entered.set()
        release.wait(3)
        return []

    with patch("qt_ui.qt_survey_setup.list_wifi_adapters", side_effect=discover):
        dialog = SurveySetupDialog(window)
        wait_until(qt_app, entered.is_set)
        dialog.reject()
        assert dialog.thread is not None
        release.set()
        wait_until(qt_app, lambda: dialog.thread is None)
        assert dialog.result() == QDialog.DialogCode.Rejected
        dialog.deleteLater()


def test_scan_worker_passes_receiver_and_preserves_capture_metadata(qt_app):
    worker = WifiScanWorker(adapter_id=RECEIVER["id"])
    captured = []
    worker.finished.connect(lambda data, backend: captured.append(data))
    result = batch()
    with patch("qt_ui.qt_point_workflow.scan_wifi", return_value=(result, "lswifi")) as scan:
        worker.run()
    scan.assert_called_once_with("auto", show_errors=False, adapter_id=RECEIVER["id"], progress=ANY, cancel_event=ANY)
    assert captured == [result] and captured[0] is result


def test_workspace_captures_with_pinned_receiver_and_keeps_points_on_failure(window, qt_app):
    window.session = SurveySession()
    window.session.set_capture_adapter(RECEIVER)
    with (patch("qt_ui.qt_point_workflow.scan_wifi", return_value=(batch(), "lswifi")) as scan,
          patch.object(window, "validate_relevant_networks", return_value="keep")):
        window.start_wifi_scan(10, 20)
        window.capture_dialog.primary_action()
        wait_until(qt_app, lambda: window.scan_thread is None)
        window.capture_dialog.primary_action()
    scan.assert_called_once_with("auto", show_errors=False, adapter_id=RECEIVER["id"], progress=ANY, cancel_event=ANY)
    before = deepcopy((window.session.rows, window.session.raw_scan_rows, window.session.metadata))
    with (patch("qt_ui.qt_point_workflow.scan_wifi", side_effect=scanner.WifiScanError("capture_adapter_unavailable")),
          patch.object(QMessageBox, "critical") as error):
        window.pending_rescan_point = window.session.get_points()[0]
        window.start_wifi_scan(10, 20)
        window.capture_dialog.primary_action()
        wait_until(qt_app, lambda: window.scan_thread is None)
    assert window.capture_dialog.phase == "error"
    assert window.capture_dialog.progress_detail.text() == window.tr("capture_adapter_unavailable")
    window.capture_dialog.reject()
    assert (window.session.rows, window.session.raw_scan_rows, window.session.metadata) == before
    assert not window.scan_in_progress and window.pending_rescan_point is None
    error.assert_not_called()


def test_legacy_capture_requires_explicit_selection_and_cancel_does_not_start_scan(window):
    window.session = SurveySession()
    with (patch("qt_ui.qt_point_workflow.SurveySetupDialog") as dialog,
          patch("qt_ui.qt_point_workflow.WifiScanWorker") as scan):
        dialog.return_value.exec.return_value = QDialog.DialogCode.Rejected
        window.start_wifi_scan(10, 20)
    scan.assert_not_called()
    assert not window.session.capture_adapter() and not window.scan_in_progress


def test_legacy_capture_choice_pins_future_points_without_relabelling_old_data(window, qt_app):
    window.session = SurveySession()
    window.session.add_points(5, 6, batch(OTHER["id"]))
    previous = deepcopy(window.session.rows)
    with (patch("qt_ui.qt_point_workflow.SurveySetupDialog") as dialog,
          patch("qt_ui.qt_point_workflow.scan_wifi", return_value=(batch(), "lswifi")) as scan,
          patch.object(window, "validate_relevant_networks", return_value="keep")):
        dialog.return_value.exec.return_value = QDialog.DialogCode.Accepted
        dialog.return_value.options.return_value = {"adapter": RECEIVER}
        window.start_wifi_scan(10, 20)
        window.capture_dialog.primary_action()
        wait_until(qt_app, lambda: window.scan_thread is None)
        window.capture_dialog.primary_action()
    assert window.session.capture_adapter() == RECEIVER
    assert window.session.rows[:len(previous)] == previous
    assert window.session.rows[-1]["adapter_id"] == RECEIVER["id"]
    scan.assert_called_once_with("auto", show_errors=False, adapter_id=RECEIVER["id"], progress=ANY, cancel_event=ANY)


@pytest.mark.parametrize("language", ["en", "it", "fr", "es"])
def test_receiver_help_is_available_in_all_languages(window, language):
    from qt_ui.qt_help_dialog import build_help_sections
    window.language = language
    survey_help = next(section.body_html for section in build_help_sections(window, window.tr) if section.key == "survey")
    assert translate(language, "capture_adapter_help") in unescape(survey_help)
    assert translate(language, "capture_adapter_label") != "capture_adapter_label"
