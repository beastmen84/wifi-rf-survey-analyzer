"""Guidance must never invent data, conflate weak Wi-Fi with bad capture, or lose points."""

from copy import deepcopy
from html import unescape
from threading import Event
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog

from advisor.engine import analyze_survey
from advisor.presentation import report_html
from qt_ui.qt_capture_dialog import GuidedCaptureDialog
from survey.measurement_quality import assess_measurement, assess_survey_measurements
from survey.measurement_presentation import measurement_cards
from survey.store import SurveySession
from tests.test_capture_adapter import RECEIVER, OTHER, window, qt_app, wait_until
from tests.test_precision_regressions import fresh_sample, mock_native, bss
from wifi import scanner


def measured(signals=(-80, -80, -80, -80, -80), *, complete=True, ssid="Office"):
    samples = [dict(fresh_sample(index, 100 + index, signal, RECEIVER["id"]), ssid=ssid)
               for index, signal in enumerate(signals, 1)]
    rows = scanner.merge_wifi_scans(samples, 5)
    count = 5 if complete else 3
    capture = dict(status="complete" if complete else "partial", freshness="fresh", backend="lswifi",
        adapter_id=RECEIVER["id"], expected_attempts=5, successful_reads=count,
        attempts=[dict(attempt=index, status="complete" if index <= count else "failed") for index in range(1, 6)])
    return scanner.ScanBatch(rows, capture)


def assessment(batch):
    return assess_measurement(batch, capture=batch.capture, relevant_ssids={"Office"}, expected_adapter_id=RECEIVER["id"])


def start_capture(window, qt_app):
    window.session = SurveySession()
    window.session.set_capture_adapter(RECEIVER)
    window.relevant_ssids = {"Office"}
    window.known_ssids = {"Office"}
    window.start_wifi_scan(10, 20)
    assert window.capture_dialog.phase == "prepare" and window.scan_thread is None
    window.capture_dialog.primary_action()
    wait_until(qt_app, lambda: window.scan_thread is None)


def test_weak_signal_can_be_fresh_reliable_and_stable():
    result = assessment(measured())
    assert result.collection == "verified" and result.stability == "stable" and result.coverage == "weak"
    assert result.fresh_samples == 5 and result.spread_db == 0 and result.weak_ssids == ["Office"]


def test_partial_capture_and_stability_are_independent():
    result = assessment(measured(complete=False))
    assert result.collection == "limited" and result.stability == "stable"
    assert result.completed == 3 and result.total == 5 and result.can_save


def test_duplicate_attempt_ledger_cannot_claim_a_complete_acquisition():
    batch = measured()
    batch.capture["attempts"][1]["attempt"] = 1
    assert assessment(batch).collection == "limited"


@pytest.mark.parametrize("signals,expected", [((-55, -55), "unknown"), ((-55, -55, -55), "stable"),
    ((-55, -67, -55), "variable"), ((-55, -66, -55), "stable")])
def test_stability_has_a_minimum_sample_count_and_explicit_12_db_boundary(signals, expected):
    result = assessment(measured(signals))
    assert result.stability == expected
    if len(signals) < 3:
        assert result.collection == "limited"


def test_completed_scans_do_not_invent_missing_ap_observations():
    result = assessment(measured((-55,)))
    assert result.completed == 5 and result.total == 5
    assert result.fresh_samples == result.minimum_samples == 1
    assert result.collection == "limited" and result.stability == "unknown"


def test_neighbor_strength_does_not_hide_weak_relevant_network():
    target, neighbor = measured(), measured((-35,) * 5, ssid="Neighbor")
    batch = scanner.ScanBatch(list(target) + list(neighbor), target.capture)
    result = assessment(batch)
    assert result.coverage == "weak" and result.weakest_ssid_dbm == -80


def test_different_bssids_are_never_compared_as_signal_variation():
    one, two = measured((-55,) * 5), measured((-59,) * 5)
    two[0]["bssid"] = "aa:bb:cc:dd:ee:ff"
    for sample in two[0]["raw_samples"]:
        sample["bssid"] = two[0]["bssid"]
    result = assessment(scanner.ScanBatch(list(one) + list(two), one.capture))
    assert result.spread_db == 0 and result.stability == "stable"


def test_unknown_and_estimated_data_are_not_upgraded_to_verified_or_stable():
    batch = measured()
    for row in batch:
        row["signal_kind"] = "estimated"
        for raw in row["raw_samples"]:
            raw["signal_kind"] = "estimated"
    result = assessment(batch)
    assert result.collection == "unverified" and result.stability == "unknown"
    assert measurement_cards(result, lambda key, **kw: key)[2]["tone"] != "good"


def test_reused_or_inconsistent_raw_evidence_cannot_authorize_stability():
    batch = measured()
    batch[0]["raw_samples"][1]["host_timestamp"] = batch[0]["raw_samples"][0]["host_timestamp"]
    result = assessment(batch)
    assert result.collection == "unverified" and result.stability == "unknown"


def test_no_scope_and_missing_scope_are_distinguished_from_coverage_failure():
    batch = measured()
    assert assess_measurement(batch, capture=batch.capture).coverage == "unknown"
    empty = scanner.ScanBatch([], batch.capture)
    result = assessment(empty)
    assert result.collection == "verified" and result.coverage == "missing" and result.can_save
    assert result.weakest_ssid_dbm is None and result.stability == "unknown"


def test_receiver_mismatch_blocks_save_before_review():
    batch = measured()
    batch[0]["raw_samples"][0]["adapter_id"] = OTHER["id"]
    result = assessment(batch)
    assert result.collection == "invalid" and not result.can_save


def test_saved_measurements_recompute_from_raw_and_ledger_without_changing_evidence(tmp_path):
    session = SurveySession()
    session.set_capture_adapter(RECEIVER)
    session.add_points(10, 20, measured(), relevant_ssids={"Office"})
    path = str(tmp_path / "quality.csv")
    session.save(path)
    reopened = SurveySession(path)
    before = deepcopy((reopened.rows, reopened.raw_scan_rows, reopened.metadata))
    result = next(iter(assess_survey_measurements(*before, {"Office"}).values()))
    assert result.collection == "verified" and result.coverage == "weak"
    assert (reopened.rows, reopened.raw_scan_rows, reopened.metadata) == before


def test_native_progress_counts_requests_and_unique_observations_separately():
    from contextlib import ExitStack
    progress = []
    with ExitStack() as stack:
        for p in mock_native(dict(status="complete", started=100, completed=200), [bss(stamp=110)]):
            stack.enter_context(p)
        result = scanner.scan_wifi_lswifi(False, progress=progress.append)
    assert len(progress) == 10
    assert progress[-1]["completed"] == progress[-1]["successful_reads"] == 5
    assert progress[-1]["fresh_samples"] == result[0]["samples_seen"] == 1


@pytest.mark.parametrize("when", ["before", "after_request", "between"])
def test_native_cancel_never_returns_partial_data_or_uses_fallback(when):
    from contextlib import ExitStack
    cancel = Event()
    if when == "before":
        cancel.set()
    def progress(info):
        if when == "between" and info.get("completed") == 1:
            cancel.set()
    def request(*_):
        if when == "after_request":
            cancel.set()
        return dict(status="complete", started=100, completed=200)
    with ExitStack() as stack:
        for p in mock_native(dict(status="complete", started=100, completed=200), [bss(stamp=110)]):
            stack.enter_context(p)
        stack.enter_context(patch.object(scanner, "scan_and_wait", side_effect=request))
        fallback = stack.enter_context(patch.object(scanner, "scan_wifi_netsh"))
        with pytest.raises(scanner.WifiScanCancelled):
            scanner.scan_wifi(show_errors=False, progress=progress, cancel_event=cancel)
    fallback.assert_not_called()


def test_capture_is_provisional_until_save_and_persisted_view_retains_three_axes(window, qt_app):
    with patch("qt_ui.qt_point_workflow.scan_wifi", return_value=(measured(), "lswifi")):
        start_capture(window, qt_app)
    assert window.capture_dialog.phase == "review" and not window.session.rows
    assert window.scan_in_progress
    window.capture_dialog.primary_action()
    assert window.capture_dialog is None and not window.scan_in_progress
    assert len(window.session.rows) == 1
    window.points_table.selectRow(0)
    assert window.tr("measurement_collection") in window.point_measurement_summary.text()
    assert window.tr("measurement_coverage_weak") in window.point_measurement_summary.text()
    assert window.tr("measurement_collection_verified") in window.points_table.item(0, 4).toolTip()


def test_cancel_during_preparation_does_not_start_receiver_or_change_points(window):
    window.session = SurveySession()
    window.session.set_capture_adapter(RECEIVER)
    with patch("qt_ui.qt_point_workflow.WifiScanWorker") as worker:
        window.start_wifi_scan(10, 20)
        window.capture_dialog.reject()
    worker.assert_not_called()
    assert window.capture_dialog is None and not window.scan_in_progress and not window.session.rows


def test_preparation_countdown_starts_once_and_retry_reenables_start(window):
    dialog = GuidedCaptureDialog(window, 1, 2, RECEIVER)
    started = []
    dialog.start_requested.connect(lambda: started.append(True))
    dialog.begin_preparation()
    dialog.prepare_tick()
    assert dialog.phase == "prepare" and not started
    dialog.prepare_tick()
    assert dialog.phase == "scanning" and started == [True]
    bad = assessment(measured())
    bad.can_save = False
    dialog.show_review(bad)
    assert not dialog.primary_button.isEnabled()
    dialog.begin_preparation()
    assert dialog.primary_button.isEnabled()
    dialog.finish()
    dialog.deleteLater()


def test_cancel_while_native_request_is_active_preserves_existing_point(window, qt_app):
    entered, release = Event(), Event()
    window.session = SurveySession()
    window.session.set_capture_adapter(RECEIVER)
    window.session.add_points(10, 20, measured())
    previous = deepcopy((window.session.rows, window.session.raw_scan_rows, window.session.metadata))
    def scan(*_, **kw):
        entered.set()
        release.wait(3)
        return measured(), "lswifi"
    with patch("qt_ui.qt_point_workflow.scan_wifi", side_effect=scan):
        window.pending_rescan_point = window.session.get_points()[0]
        window.start_wifi_scan(10, 20)
        window.capture_dialog.primary_action()
        wait_until(qt_app, entered.is_set)
        window.capture_dialog.reject()
        assert window.capture_dialog.phase == "cancelling" and window.scan_in_progress
        release.set()
        wait_until(qt_app, lambda: window.capture_dialog is None)
    assert (window.session.rows, window.session.raw_scan_rows, window.session.metadata) == previous
    assert not window.scan_in_progress


def test_failed_rescan_and_retry_keep_old_point_until_new_measurement_is_saved(window, qt_app):
    window.session = SurveySession()
    window.session.set_capture_adapter(RECEIVER)
    window.relevant_ssids = window.known_ssids = {"Office"}
    window.session.add_points(10, 20, measured())
    previous = deepcopy(window.session.rows)
    with patch("qt_ui.qt_point_workflow.scan_wifi", side_effect=scanner.WifiScanError("capture_adapter_unavailable")):
        window.pending_rescan_point = window.session.get_points()[0]
        window.start_wifi_scan(10, 20)
        window.capture_dialog.primary_action()
        wait_until(qt_app, lambda: window.scan_thread is None)
    assert window.capture_dialog.phase == "error" and window.session.rows == previous
    window.retry_wifi_capture()
    with patch("qt_ui.qt_point_workflow.scan_wifi", return_value=(measured((-60,) * 5), "lswifi")):
        window.capture_dialog.primary_action()
        wait_until(qt_app, lambda: window.scan_thread is None)
    assert window.session.rows == previous
    window.capture_dialog.primary_action()
    assert len(window.session.rows) == 1 and float(window.session.rows[0]["signal_dbm"]) == -60
    assert window.session.rows[0]["point_id"] != previous[0]["point_id"]


def test_saved_details_dialog_is_read_only(window):
    dialog = GuidedCaptureDialog(window, 1, 2, RECEIVER, read_only=True)
    dialog.show_review(assessment(measured()), {"Office"})
    assert dialog.primary_button.isHidden() and dialog.retry_button.isHidden()
    assert dialog.cards[2][2].text() == window.tr("measurement_coverage_weak")
    dialog.reject()
    dialog.deleteLater()


def test_keyboard_enter_activates_focused_repeat_instead_of_saving(window, qt_app):
    dialog = GuidedCaptureDialog(window, 1, 2, RECEIVER)
    events = []
    dialog.retry_requested.connect(lambda: events.append("retry"))
    dialog.save_requested.connect(lambda: events.append("save"))
    dialog.show_review(assessment(measured()))
    dialog.show()
    qt_app.processEvents()
    dialog.retry_button.setFocus()
    QTest.keyClick(dialog.retry_button, Qt.Key.Key_Return)
    assert events == ["retry"]
    dialog.finish()
    assert dialog.result() == QDialog.DialogCode.Rejected
    dialog.deleteLater()


def test_legacy_saved_details_do_not_invent_a_receiver(window):
    window.session = SurveySession()
    window.session.add_points(10, 20, [{"ssid": "Office", "bssid": "aa:bb:cc:dd:ee:ff", "signal_percent": 50,
        "signal_dbm": -70, "channel": "1", "radio": "802.11ax"}])
    window.session.set_capture_adapter(RECEIVER)
    window.refresh_points_table()
    window.points_table.selectRow(0)
    with patch("qt_ui.qt_survey_points.GuidedCaptureDialog") as dialog:
        window.show_selected_measurement_details()
    assert dialog.call_args.args[3] == {"description": window.tr("measurement_unknown_receiver")}


def test_measurement_summary_retranslates_and_preserves_selection(window):
    window.session = SurveySession()
    window.session.add_points(10, 20, measured())
    window.relevant_ssids = {"Office"}
    window.refresh_points_table()
    window.points_table.selectRow(0)
    selected_id = window.current_selected_point()["point_id"]
    window.change_language("it")
    assert window.current_selected_point()["point_id"] == selected_id
    assert window.tr("measurement_coverage_weak") in window.point_measurement_summary.text()


def test_store_failure_during_rescan_keeps_old_evidence_and_provisional_capture(window, qt_app):
    with patch("qt_ui.qt_point_workflow.scan_wifi", return_value=(measured(), "lswifi")):
        start_capture(window, qt_app)
    window.capture_dialog.primary_action()
    original = deepcopy((window.session.rows, window.session.raw_scan_rows, window.session.metadata))
    window.pending_rescan_point = window.session.get_points()[0]
    with patch("qt_ui.qt_point_workflow.scan_wifi", return_value=(measured((-60,) * 5), "lswifi")):
        window.start_wifi_scan(10, 20)
        window.capture_dialog.primary_action()
        wait_until(qt_app, lambda: window.scan_thread is None)
    with patch.object(window.session, "add_points", side_effect=ValueError("capture_adapter_mismatch")):
        window.capture_dialog.primary_action()
    assert (window.session.rows, window.session.raw_scan_rows, window.session.metadata) == original
    assert window.capture_dialog.phase == "error"
    window.capture_dialog.reject()


@pytest.mark.parametrize("language", ["en", "it", "fr", "es"])
def test_analysis_html_retains_separate_quality_axes_and_actual_analysis_reference(window, language):
    session = SurveySession()
    session.add_points(10, 20, measured(), relevant_ssids={"Office"})
    report = analyze_survey(session.rows, session.raw_scan_rows, relevant_ssids={"Office"}, context_metadata=session.metadata)
    html = report_html(report, language)
    window.language = language
    for key in ("measurement_collection", "measurement_stability", "measurement_coverage"):
        assert window.tr(key) in unescape(html)
    assert "-70" in html and report.measurements
