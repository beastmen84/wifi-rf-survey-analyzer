"""Regressions for survey integrity, scanner evidence and asynchronous UI state."""

import json
import os
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest
from PIL import Image
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication

from app_core import file_io
from app_core.file_io import SurveyFileTransaction, atomic_write_text
from maps.config import MapConfig
from maps.heatmap import get_channel_map_points, get_dominant_ap_points, calculate_interference_points
from maps.live_renderer import build_result_cache_key
from maps.quality import evaluate_point_quality, QUALITY_MISSING_RELEVANT
from qt_ui.qt_app import WifiHeatmapQtApp
from qt_ui.qt_point_workflow import RelevantNetworksDialog
from survey import store
from survey.store import SurveySession, read_survey_rows, read_raw_scan_rows
from tests._common import build_row
from wifi import scanner


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("WIFI_HEATMAP_AP_MEMORY_FILE", str(tmp_path / "ap.memory"))
    monkeypatch.setenv("WIFI_HEATMAP_SETTINGS_FILE", str(tmp_path / "settings.json"))


@pytest.fixture
def window():
    app = QApplication.instance() or QApplication([])
    result = WifiHeatmapQtApp()
    yield result
    result.session = None
    result.deleteLater()
    app.processEvents()


def network(ssid="Office"):
    row = dict(ssid=ssid, bssid="02:00:00:00:00:01", signal_percent=80,
               signal_dbm=-60, channel="1", band="2.4", radio="802.11ax")
    return {**row, "raw_samples": [{**row, "scan_attempt": 1, "backend": "synthetic"}]}


def test_csv_multiline_hash_content_roundtrips(tmp_path):
    session = SurveySession()
    session.add_points(10, 10, [network('Office\n#not a comment\n"quoted",value')])
    path = str(tmp_path / "survey.csv")
    session.save(path)
    assert read_survey_rows(path)[0]["ssid"] == read_raw_scan_rows(path)[0]["ssid"]
    assert SurveySession(path).rows[0]["ssid"] == session.rows[0]["ssid"]


def test_staging_error_keeps_previous_files_and_session_state(tmp_path):
    session = SurveySession()
    session.add_points(10, 10, [network()])
    path = tmp_path / "survey.csv"
    session.save(str(path))
    raw = tmp_path / "survey_raw_data.scan"
    before = path.read_bytes(), raw.read_bytes()
    session.add_points(20, 20, [network()])
    with patch.object(store, "write_raw_scan_rows", side_effect=PermissionError("raw denied")):
        with pytest.raises(PermissionError):
            session.save()
    assert (path.read_bytes(), raw.read_bytes()) == before
    assert session.dirty
    assert len(SurveySession(str(path)).rows) == 1


@pytest.mark.parametrize("failure_index", [1, 2, 3])
def test_commit_error_rolls_back_all_survey_files(tmp_path, failure_index):
    csv = tmp_path / "survey.csv"
    raw = tmp_path / "survey_raw_data.scan"
    mask = tmp_path / "survey.boundaries.png"
    csv.write_bytes(b"old CSV")
    raw.write_bytes(b"old raw")
    real_replace = os.replace
    count = 0

    def fail_once(source, destination):
        nonlocal count
        if ".stage" in Path(source).name:
            count += 1
            if count == failure_index:
                raise PermissionError("simulated replace failure")
        real_replace(source, destination)

    with SurveyFileTransaction(csv) as transaction:
        for target in (csv, raw, mask):
            transaction.stage_file(target).write_bytes(b"new content")
        with patch.object(file_io.os, "replace", side_effect=fail_once):
            with pytest.raises(PermissionError):
                transaction.commit()
    assert csv.read_bytes() == b"old CSV"
    assert raw.read_bytes() == b"old raw"
    assert not mask.exists()
    assert not list(tmp_path.glob("*.save.json"))


@pytest.mark.parametrize("state,expected", [("prepared", b"old"), ("committed", b"new")])
def test_reopen_recovers_interrupted_transaction(tmp_path, state, expected):
    csv = tmp_path / "survey.csv"
    csv.write_bytes(b"old")
    transaction = SurveyFileTransaction(csv)
    stage = transaction.stage_file(csv)
    stage.write_bytes(b"new")
    entry = transaction.entries[0]
    (tmp_path / entry["backup"]).write_bytes(b"old")
    entry["old_sha256"] = file_io.file_digest(tmp_path / entry["backup"])
    entry["new_sha256"] = file_io.file_digest(stage)
    os.replace(stage, csv)
    transaction.journal.write_text(json.dumps(dict(version=1, token=transaction.token,
        state=state, files=transaction.entries)), encoding="utf-8")
    with SurveyFileTransaction(csv):
        pass
    assert csv.read_bytes() == expected
    assert not transaction.journal.exists()


def test_failed_rollback_keeps_backups_for_retry(tmp_path):
    csv = tmp_path / "survey.csv"
    csv.write_bytes(b"old")
    real_replace = os.replace

    def denied_replace(source, target):
        if ".stage" in Path(source).name or str(source).endswith(".restore"):
            raise PermissionError("denied")
        real_replace(source, target)

    with SurveyFileTransaction(csv) as transaction:
        stage = transaction.stage_file(csv)
        stage.write_bytes(b"new")
        with patch.object(file_io.os, "replace", side_effect=denied_replace):
            with pytest.raises(PermissionError):
                transaction.commit()
        assert transaction.journal.exists()
    with SurveyFileTransaction(csv):
        pass
    assert csv.read_bytes() == b"old"


def test_recovery_is_automatic_before_reading_survey_csv(tmp_path):
    session = SurveySession()
    session.add_points(10, 10, [network()])
    csv = tmp_path / "survey.csv"
    session.save(str(csv))
    raw = tmp_path / "survey_raw_data.scan"
    transaction = SurveyFileTransaction(csv)
    for path in (csv, raw):
        transaction.stage_file(path).write_bytes(b"interrupted content")
        entry = transaction.entries[-1]
        (tmp_path / entry["backup"]).write_bytes(path.read_bytes())
        entry["old_sha256"] = file_io.file_digest(tmp_path / entry["backup"])
        entry["new_sha256"] = file_io.file_digest(tmp_path / entry["stage"])
    first = transaction.entries[0]
    transaction.journal.write_text(json.dumps(dict(version=1, token=transaction.token,
        state="prepared", files=transaction.entries)), encoding="utf-8")
    os.replace(tmp_path / first["stage"], csv)
    loaded = SurveySession(str(csv))
    assert len(loaded.rows) == len(loaded.raw_scan_rows) == 1
    assert loaded.rows[0]["ssid"] == "Office"
    assert not transaction.journal.exists()


def test_commit_marker_error_restores_previous_set(tmp_path):
    csv = tmp_path / "survey.csv"
    csv.write_bytes(b"old")
    real_write = atomic_write_text

    def fail_marker(path, text):
        if json.loads(text)["state"] == "committed":
            raise OSError("full disk at commit marker")
        real_write(path, text)

    with SurveyFileTransaction(csv) as transaction:
        transaction.stage_file(csv).write_bytes(b"new")
        with patch.object(file_io, "atomic_write_text", side_effect=fail_marker):
            with pytest.raises(OSError):
                transaction.commit()
    assert csv.read_bytes() == b"old"


def test_transaction_rejects_duplicate_paths_and_concurrent_saves(tmp_path):
    csv = tmp_path / "survey.csv"
    with SurveyFileTransaction(csv) as transaction:
        transaction.stage_file(csv)
        with pytest.raises(ValueError):
            transaction.stage_file(csv)
        with pytest.raises(ValueError):
            transaction.stage_file(transaction.journal)
        with pytest.raises(OSError):
            with SurveyFileTransaction(csv):
                pass


def test_recovery_rejects_paths_outside_the_survey_directory(tmp_path):
    csv = tmp_path / "survey.csv"
    transaction = SurveyFileTransaction(csv)
    transaction.journal.write_text(json.dumps(dict(version=1, token=transaction.token,
        state="prepared", files=[dict(target="../victim.csv", stage="bad", backup="bad", existed=False)])),
        encoding="utf-8")
    with pytest.raises(ValueError):
        with SurveyFileTransaction(csv):
            pass
    assert transaction.journal.exists()


@pytest.mark.parametrize("damaged", ["target", "backup"])
def test_recovery_refuses_changed_files_or_corrupted_backups(tmp_path, damaged):
    csv = tmp_path / "survey.csv"
    csv.write_bytes(b"old")
    transaction = SurveyFileTransaction(csv)
    stage = transaction.stage_file(csv)
    stage.write_bytes(b"new")
    entry = transaction.entries[0]
    backup = tmp_path / entry["backup"]
    backup.write_bytes(b"old")
    entry["old_sha256"] = file_io.file_digest(backup)
    entry["new_sha256"] = file_io.file_digest(stage)
    transaction.journal.write_text(json.dumps(dict(version=1, token=transaction.token,
        state="prepared", files=transaction.entries)), encoding="utf-8")
    changed = csv if damaged == "target" else backup
    changed.write_bytes(b"unrelated newer data")
    with pytest.raises(OSError):
        with SurveyFileTransaction(csv):
            pass
    assert changed.read_bytes() == b"unrelated newer data"
    assert transaction.journal.exists()


def test_save_as_failure_keeps_original_path_and_metadata(tmp_path):
    session = SurveySession()
    session.dirty = True
    metadata = session.metadata.copy()
    with patch.object(store, "write_raw_scan_rows", side_effect=OSError("full disk")):
        with pytest.raises(OSError):
            session.save(str(tmp_path / "new.csv"))
    assert session.csv_file is None
    assert session.metadata == metadata
    assert session.dirty
    assert not (tmp_path / "new.csv").exists()


def test_saving_a_copy_does_not_overwrite_the_original_raw_data(tmp_path):
    session = SurveySession()
    session.add_points(10, 10, [network()])
    original = tmp_path / "original.csv"
    session.save(str(original))
    session.add_points(20, 20, [network()])
    copied = tmp_path / "copy.csv"
    session.save(str(copied))
    assert len(SurveySession(str(original)).raw_scan_rows) == 1
    assert len(SurveySession(str(copied)).raw_scan_rows) == 2
    assert session.metadata["raw_data_file"] == "copy_raw_data.scan"


def test_atomic_json_write_preserves_previous_file_on_error(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"theme":"dark"}', encoding="utf-8")
    with patch.object(file_io.os, "replace", side_effect=PermissionError("denied")):
        with pytest.raises(PermissionError):
            atomic_write_text(path, '{"theme":"light"}')
    assert json.loads(path.read_text())["theme"] == "dark"


def test_ui_save_failure_rolls_back_generated_png_and_metadata(window, tmp_path):
    window.choose_new_survey_measurement_system = lambda: "metric"
    assert window.new_survey(from_start_page=True)
    previous_metadata = window.session.metadata.copy()
    csv = tmp_path / "survey.csv"
    with patch("qt_ui.qt_session_workflow.get_centered_save_file_name", return_value=(str(csv), "")), \
         patch.object(store, "write_raw_scan_rows", side_effect=OSError("full disk")), \
         patch("qt_ui.qt_session_workflow.QMessageBox.warning") as warning:
        assert not window.save_survey()
    assert warning.called
    assert window.session.csv_file is None
    assert window.session.metadata == previous_metadata
    assert not csv.exists()
    assert not csv.with_suffix(".png").exists()


def test_ui_failed_save_keeps_existing_boundaries_unchanged(window, tmp_path):
    window.choose_new_survey_measurement_system = lambda: "metric"
    window.new_survey(from_start_page=True)
    csv = tmp_path / "survey.csv"
    window.session.csv_file = str(csv)
    assert window.save_survey()
    mask = tmp_path / "survey.boundaries.png"
    mask.write_bytes(b"previous mask")
    window.session.metadata["boundaries_file"] = mask.name
    old_csv = csv.read_bytes()
    metadata = window.session.metadata.copy()

    def save_mask(path):
        Path(path).write_bytes(b"new mask")
        return True

    with patch.object(window.floorplan_view, "has_boundaries_mask", return_value=True), \
         patch.object(window.floorplan_view, "save_boundaries_mask", side_effect=save_mask), \
         patch.object(store, "write_raw_scan_rows", side_effect=PermissionError("raw denied")), \
         patch("qt_ui.qt_session_workflow.QMessageBox.warning"):
        assert not window.save_survey()
    assert mask.read_bytes() == b"previous mask"
    assert csv.read_bytes() == old_csv
    assert window.session.metadata == metadata


def case_rows():
    first = build_row("p1", "Office", "02:00:00:00:00:01", -70, 1)
    second = build_row("p1", "office", "02:00:00:00:00:02", -40, 6)
    return [first, second]


def test_all_rf_maps_keep_case_distinct_ssids_separate():
    df = pd.DataFrame(case_rows())
    channels = get_channel_map_points(df, "Office", "2.4")
    assert channels.iloc[0]["ssid"] == "Office"
    assert int(channels.iloc[0]["channel"]) == 1
    dominant = get_dominant_ap_points(df, "Office", "2.4")
    assert dominant.iloc[0]["dominant_signal_dbm"] == -70
    interference = calculate_interference_points(df, "Office", "2.4", include_details=True)
    assert interference.iloc[0]["serving_signal_dbm"] == -70


def test_quality_flags_case_distinct_missing_network():
    quality = evaluate_point_quality(case_rows()[:1], relevant_ssids={"office"})
    assert quality["p1"]["status"] == QUALITY_MISSING_RELEVANT
    assert quality["p1"]["missing_relevant"] == ["office"]


def test_ssid_ui_choices_and_relevance_keep_case(window):
    window.session = SurveySession()
    window.session.rows = case_rows()
    window.set_relevant_ssids({"Office"})
    assert [row["is_relevant"] for row in window.session.rows] == ["1", "0"]
    assert window.preferred_live_ssid(["Office", "office"], "Office") == "Office"
    dialog = RelevantNetworksDialog(window, ["Office", "office"], "Networks", "Choose",
        connected_ssid="Office", selected_ssids={"Office"})
    assert dialog.checkboxes["Office"].isChecked()
    assert not dialog.checkboxes["office"].isChecked()
    dialog.deleteLater()


def test_capture_relevance_keeps_case_distinct_ssids():
    session = SurveySession()
    session.add_points(10, 10, [network("Office"), network("office")], relevant_ssids={"Office"})
    assert [row["is_relevant"] for row in session.rows] == ["1", "0"]


def test_reopening_legacy_row_flags_reconciles_explicit_ssid_selection(window):
    window.session = SurveySession()
    window.session.rows = case_rows()
    window.session.metadata["relevant_ssids"] = json.dumps(["Office"])
    for row in window.session.rows:
        row["is_relevant"] = "1"
    window.session.dirty = False
    window.load_session_ssid_state()
    assert [row["is_relevant"] for row in window.session.rows] == ["1", "0"]
    assert window.session.dirty


@pytest.mark.parametrize("signal,channel,radio,band", [
    ("Signal", "Channel", "Radio type", "Band"),
    ("Segnale", "Canale", "Tipo frequenza radio", "Banda"),
    ("Signal", "Canal", "Type de radio", "Bande"),
    ("Señal", "Canal", "Tipo de radio", "Banda"),
])
def test_localized_netsh_preserves_explicit_6ghz_band(signal, channel, radio, band):
    output = f"""SSID 1 : Office
    BSSID 1 : 02:00:00:00:00:01
      {signal} : 80%
      {channel} : 5
      {radio} : 802.11ax
      {band} : 6 GHz
    BSSID 2 : 02:00:00:00:00:02
      {signal} : 70%
      {channel} : 6
"""
    networks = scanner.parse_netsh_output(output)
    assert len(networks) == 2
    assert networks[0]["band"] == "6"
    assert networks[1]["band"] == "2.4"  # no leaked state from the previous BSSID


@pytest.mark.parametrize("name,state,value,signal,channel", [
    ("Name", "State", "connected", "Signal", "Channel"),
    ("Nome", "Stato", "connesso", "Segnale", "Canale"),
    ("Nom", "État", "connecté", "Signal", "Canal"),
    ("Nombre", "Estado", "conectado", "Señal", "Canal"),
])
def test_localized_netsh_connected_interface(name, state, value, signal, channel):
    output = f"""{name} : Wi-Fi
{state} : {value}
SSID : Office
AP BSSID : 02:00:00:00:00:01
{signal} : 80%
{channel} : 5
"""
    assert scanner.parse_netsh_interfaces_output(output)["ssid"] == "Office"


def test_netsh_keeps_connected_adapter_when_later_one_is_disconnected():
    output = "Name : Wi-Fi\nState : connected\nSSID : Office\nBSSID : 02:00:00:00:00:01\nName : Other\nState : disconnected\n"
    assert scanner.parse_netsh_interfaces_output(output)["ssid"] == "Office"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "cp850"])
def test_netsh_decodes_localized_bytes_without_dropping_field_accents(encoding):
    output = "SSID 1 : Office\nBSSID 1 : 02:00:00:00:00:01\nSeñal : 80%\nCanal : 5\nBanda : 6 GHz\n"
    assert scanner.parse_netsh_output(output.encode(encoding))[0]["band"] == "6"


def test_netsh_timeout_and_nonzero_exit_are_not_empty_successes():
    with patch.object(scanner.subprocess, "run", side_effect=subprocess.TimeoutExpired("netsh", 15)) as run:
        with pytest.raises(scanner.WifiScanError, match="wifi_scan_timeout"):
            scanner.scan_wifi_netsh(show_errors=False)
        assert run.call_args.kwargs["timeout"] == scanner.NETSH_SCAN_TIMEOUT_SECONDS
    with patch.object(scanner.subprocess, "run", return_value=SimpleNamespace(returncode=1, stdout="")):
        with pytest.raises(scanner.WifiScanError, match="wifi_scan_failed"):
            scanner.scan_wifi_netsh(show_errors=False)


def test_missing_saved_plan_clears_previous_canvas(window, tmp_path):
    plan = tmp_path / "old.png"
    Image.new("RGB", (50, 50), "white").save(plan)
    window.floorplan_view.load_floorplan(str(plan))
    assert window.floorplan_view.has_floorplan()
    window.session = SurveySession()
    window.session.metadata["map_file"] = str(tmp_path / "missing.png")
    with patch("qt_ui.qt_floorplan_workflow.QMessageBox.warning"):
        window.load_saved_plan()
    assert not window.floorplan_view.has_floorplan()
    assert not window.floorplan_view.grid_visible


def test_stale_live_success_and_error_are_both_discarded(window):
    old_session = SurveySession()
    window.session = old_session
    request = (old_session, window.live_generation)
    window.invalidate_live_preview()
    window.session = SurveySession()
    with patch.object(window.live_view, "set_payload") as accept, \
         patch.object(window.live_status_label, "setText") as status:
        window.finish_live_preview({"scale_payload": None}, request)
        window.fail_live_preview("old failure", request)
    assert not accept.called
    assert not status.called


def test_live_worker_thread_finishes_before_becoming_idle(window):
    """Exercise queued cross-thread completion, including invalidation mid-flight."""
    class Worker(QObject):
        finished = Signal(object, object)

        @Slot()
        def run(self):
            time.sleep(0.03)
            self.finished.emit({"scale_payload": None}, request)

    old_session = SurveySession()
    window.session = old_session
    request = (old_session, window.live_generation)
    thread = QThread(window)
    worker = Worker()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(window.finish_live_preview)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(window.cleanup_live_render_thread)
    window.live_thread, window.live_worker = thread, worker
    window.live_rendering = True
    thread.start()
    window.invalidate_live_preview()
    window.session = SurveySession()
    window.live_auto_check.setChecked(False)
    deadline = time.monotonic() + 5
    try:
        with patch.object(window.live_view, "set_payload") as accept:
            while window.live_thread is not None and time.monotonic() < deadline:
                QApplication.processEvents()
                time.sleep(0.005)
            assert window.live_thread is None
            assert not window.live_rendering
            assert not accept.called
    finally:
        thread.quit()
        thread.wait(5000)
        thread.deleteLater()


def test_live_cache_tracks_ssid_case_and_connected_evidence():
    df = pd.DataFrame(case_rows())
    image = Image.new("RGB", (10, 10), "white")
    first = build_result_cache_key(df, MapConfig(ssid="Office"), image, {})
    assert first != build_result_cache_key(df, MapConfig(ssid="office"), image, {})
    df["is_connected"] = ["1", "0"]
    connected = build_result_cache_key(df, MapConfig(ssid="Office"), image, {})
    df["is_connected"] = ["0", "1"]
    assert connected != build_result_cache_key(df, MapConfig(ssid="Office"), image, {})


def test_real_live_render_delivers_payload_and_cleans_up_thread(window, tmp_path):
    image = tmp_path / "plan.png"
    Image.new("RGB", (100, 100), "white").save(image)
    window.live_auto_check.setChecked(False)
    window.session = SurveySession()
    window.session.rows = case_rows()[:1]
    window.session.metadata["map_file"] = str(image)
    window.live_map_type_combo.setCurrentIndex(window.live_map_type_combo.findData("channel"))
    window.tabs.setCurrentIndex(1)
    window.refresh_live_controls()
    window.update_live_preview()
    assert window.live_thread is not None
    thread = window.live_thread
    deadline = time.monotonic() + 10
    try:
        while window.live_thread is not None and time.monotonic() < deadline:
            QApplication.processEvents()
            time.sleep(0.005)
        assert window.live_thread is None
        assert not window.live_rendering
        assert window.live_view.pixmap_item is not None
    finally:
        if window.live_thread is not None:
            thread.quit()
            thread.wait(10000)
