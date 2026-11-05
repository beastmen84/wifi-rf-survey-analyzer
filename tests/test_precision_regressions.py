"""Behavioral regressions for all pre-1.1 RF precision audit findings."""

import math
from types import SimpleNamespace as NS
from unittest.mock import patch

import pandas as pd
import pytest

from advisor.engine import analyze_survey
from ap.groups import build_default_manual_groups, build_bssid_to_manual_group_map
from maps.heatmap import (channel_overlap_weight, calculate_interference_points,
    get_scan_confidence_values, normalize_confidence_array, get_channel_frequency_range)
from maps.quality import evaluate_point_quality, get_signal_ranges_by_key, QUALITY_UNSTABLE_SIGNAL
from survey.store import SurveySession, SurveyFormatError, write_survey_file
from tests.test_advisor import fixture_survey, findings
from wifi import scanner
from wifi.band import get_row_band
from wifi.evidence import scan_confidence
from wifi.native_scan import ssid_bytes_from_native, scan_and_wait


def test_native_ssid_explicit_length_overrides_ctypes_nul_truncation():
    from ctypes import addressof, memmove
    from lswifi.wlanapi import DOT11SSID
    data = DOT11SSID()
    original = b"A\0B\xff"
    data.SSIDLength = len(original)
    memmove(addressof(data) + DOT11SSID.SSID.offset, original, len(original))
    assert data.SSID == b"A"  # The upstream c_char convenience access loses data.
    assert ssid_bytes_from_native(data) == original


@pytest.mark.parametrize("event", ["complete", "failed", "timeout", "wrong_adapter", "request_error"])
def test_native_lifecycle_filters_notifications_and_closes_handle(event):
    import ctypes
    from lswifi import wlanapi as actual
    guid = actual.GUID("{00000000-0000-0000-0000-000000000001}")
    interface = NS(guid=guid)
    retained, closed = [], []

    def register(handle, source, ignore, callback, *_):
        assert source == 8 and not ignore
        retained.append(callback)
        return 0

    def request(_handle, request_guid):
        if event == "request_error":
            raise OSError("Scan failed")
        if event != "timeout":
            data = actual.WLANNotificationData()
            data.NotificationSource = 8
            data.NotificationCode = 8 if event == "failed" else 7
            data.InterfaceGuid = request_guid if event != "wrong_adapter" else actual.GUID("{00000000-0000-0000-0000-000000000002}")
            retained[0](ctypes.pointer(data), None)

    api = NS(WLAN=NS(open_handle=lambda: 7, close_handle=lambda h: closed.append(h), wlan_scan=request),
        WLAN_API=NS(WlanRegisterNotification=register), WLANNotificationData=actual.WLANNotificationData,
        HANDLE=actual.HANDLE, DWORD=actual.DWORD, BOOL=actual.BOOL)
    result = scan_and_wait(api, interface, timeout=.001)
    expected = {"complete": "complete", "failed": "failed", "request_error": "failed"}.get(event, "timeout")
    assert result["status"] == expected and closed == [7]


def test_radio_geometry_unknown_propagates_to_map_and_export_diagnosis():
    from exporting.reports import build_interference_summary, get_interference_problem_df
    from translations.i18n import translate
    context = fixture_survey()
    for row in context["rows"]:
        row["channel_width_mhz"] = 40
    risk = calculate_interference_points(pd.DataFrame(context["rows"]), "Office", "2.4", include_details=True)
    assert risk["risk"].isna().all() and not risk["geometry_complete"].any()
    tr = lambda key, **kw: translate("it", key, **kw)
    summary = build_interference_summary(risk, "", "", "2.4", tr, "it")
    assert summary["max_risk"] == "—" and "non determinabile" in summary["diagnosis"]
    assert len(get_interference_problem_df(risk)) == 4


def test_renaming_auto_group_does_not_confirm_physical_identity(tmp_path):
    from ap.groups import is_ap_group_confirmed, merge_new_bssids_into_manual_groups
    context = fixture_survey()
    groups = build_default_manual_groups(context["rows"])
    group = groups[0]
    group.update(locked=True, alias="Renamed")
    assert not is_ap_group_confirmed(group)
    session = SurveySession()
    session.rows = context["rows"]
    session.set_ap_groups(groups, update_memory=False)
    assert not is_ap_group_confirmed(session.get_ap_groups()[0])
    assert not is_ap_group_confirmed(merge_new_bssids_into_manual_groups(session.get_ap_groups(), context["rows"])[0])


def test_raw_provenance_and_adapter_survive_save_open(tmp_path):
    rows = scanner.merge_wifi_scans([fresh_sample(i, 100+i) for i in range(1, 6)], 5)
    session = SurveySession()
    session.add_points(40, 50, rows)
    path = str(tmp_path / "provenance.csv")
    session.save(path)
    loaded = SurveySession(path)
    assert loaded.rows[0]["adapter_id"] == "receiver"
    assert scan_confidence(loaded.rows[0]) == 1
    assert len({r["host_timestamp"] for r in loaded.raw_scan_rows}) == 5
    assert all(r["observed_at"] != r["timestamp"] for r in loaded.raw_scan_rows)


def bss(ssid="Office", signal=-55, stamp=110):
    return NS(ssid=NS(value=ssid), bssid="02:00:00:00:00:10", rssi=signal,
              channel_number=1, band="2.4", frequency_mhz=2412,
              channel_width=20, host_timestamp=stamp)


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("WIFI_HEATMAP_AP_MEMORY_FILE", str(tmp_path / "ap.memory"))
    monkeypatch.setenv("WIFI_HEATMAP_SETTINGS_FILE", str(tmp_path / "settings.json"))


@pytest.mark.parametrize("ssid", [" Office ", "unknown", "none", "--", "", " ", "A\x00B"])
def test_ssid_identity_and_hidden_bss_are_preserved(ssid):
    rows = scanner.parse_lswifi_bss_list([bss(ssid)])
    assert len(rows) == 1 and rows[0]["ssid"] == ssid
    assert rows[0]["bssid"]


def test_hidden_netsh_header_resets_identity_and_preserves_spaces():
    output = "SSID 1 :  Office \n BSSID 1 : 02:00:00:00:00:10\n Signal : 80%\n Channel : 1\nSSID 2 : \n BSSID 1 : 02:00:00:00:00:20\n Signal : 70%\n Channel : 6\n"
    assert [r["ssid"] for r in scanner.parse_netsh_output(output)] == [" Office ", ""]


def test_raw_ssid_bytes_are_lossless_including_nul_and_invalid_utf8():
    item = bss()
    item.ssid_bytes = b"A\0\xffB"
    row = scanner.parse_lswifi_bss_list([item])[0]
    assert row["ssid_hex"] == "4100ff42"
    assert row["ssid"].endswith("4100ff42>")


def test_distinct_whitespace_ssids_never_merge_or_roundtrip_as_same_name(tmp_path):
    rows = scanner.parse_lswifi_bss_list([bss("Office"), bss(" Office ")])
    merged = scanner.merge_wifi_scans(rows, 5)
    assert len(merged) == 2
    session = SurveySession()
    session.add_points(1, 2, merged, relevant_ssids={" Office "})
    path = str(tmp_path / "names.csv")
    session.save(path)
    loaded = SurveySession(path)
    assert {r["ssid"] for r in loaded.rows} == {"Office", " Office "}
    assert [r["ssid"] for r in loaded.rows if r["is_relevant"] == "1"] == [" Office "]


def fresh_sample(attempt=1, stamp=110, signal=-55, adapter="receiver"):
    return dict(scanner.parse_lswifi_bss_list([bss(signal=signal, stamp=stamp)])[0],
        scan_attempt=attempt, backend="lswifi", adapter_id=adapter, freshness="fresh", signal_kind="direct",
        scan_started_at=90, scan_completed_at=120, observed_at=130)


@pytest.mark.parametrize("case", ["attempt", "timestamp"])
def test_reused_observation_cannot_inflate_confidence(case):
    samples = [fresh_sample(i if case == "timestamp" else 1,
                            100 + i if case == "attempt" else 110) for i in range(1, 6)]
    row = scanner.merge_wifi_scans(samples, 5)[0]
    assert row["samples_seen"] == 1 and row["scan_confidence"] == .2


def test_equal_rssi_from_five_fresh_observations_is_valid_stability():
    row = scanner.merge_wifi_scans([fresh_sample(i, 100 + i) for i in range(1, 6)], 5)[0]
    assert row["samples_seen"] == 5 and row["scan_confidence"] == 1
    assert row["signal_max_dbm"] == row["signal_min_dbm"] == -55


def mock_native(outcome, bss_rows):
    from lswifi import wlanapi
    return (patch.object(wlanapi.WLAN, "get_wireless_interfaces", return_value={0: NS(guid="adapter")}),
        patch("wifi.scanner.scan_and_wait", side_effect=outcome if isinstance(outcome, list) else None,
            return_value=outcome), patch("wifi.scanner.read_bss_list", return_value=bss_rows),
        patch("wifi.scanner.get_lswifi_connected_network", return_value={}),
        patch("wifi.scanner.time.sleep"), patch("wifi.scanner.filetime_now", return_value=1000))


@pytest.mark.parametrize("status", ["failed", "timeout"])
def test_scan_failure_never_reads_or_promotes_cached_bss(status):
    from contextlib import ExitStack
    with ExitStack() as stack:
        handles = [stack.enter_context(p) for p in mock_native({"status": status, "started": 100, "completed": 0}, [bss()])]
        with pytest.raises(scanner.WifiScanError):
            scanner.scan_wifi_lswifi(False)
        handles[2].assert_not_called()


def test_completed_scan_still_excludes_old_host_timestamps():
    from contextlib import ExitStack
    with ExitStack() as stack:
        for p in mock_native({"status": "complete", "started": 200, "completed": 300}, [bss(stamp=110)]):
            stack.enter_context(p)
        with pytest.raises(scanner.WifiScanError):
            scanner.scan_wifi_lswifi(False)


def test_successful_empty_scan_is_not_fallback_or_fabricated_signal(tmp_path):
    from contextlib import ExitStack
    with ExitStack() as stack:
        for p in mock_native({"status": "complete", "started": 100, "completed": 200}, []):
            stack.enter_context(p)
        rows, backend = scanner.scan_wifi("auto", False)
    assert not rows and backend == "lswifi" and rows.capture["status"] == "complete"
    session = SurveySession()
    session.add_points(30, 40, rows)
    assert not session.rows and not session.raw_scan_rows
    path = str(tmp_path / "empty.csv")
    session.save(path)
    loaded = SurveySession(path)
    assert loaded.get_point_summaries()[0]["best_signal_dbm"] is None
    assert loaded.get_points()[0]["signal_dbm"] is None
    report = analyze_survey([], context_metadata=loaded.metadata, relevant_ssids={"Office"})
    assert len(report.points) == 1 and findings(report, "empty_measurement")
    point = loaded.get_point_summaries()[0]
    assert loaded.delete_point(point["timestamp"], 30, 40, point["point_id"]) == 1
    assert not loaded.get_points()


def test_unverified_empty_list_is_rejected_without_mutating_session():
    session = SurveySession()
    with pytest.raises(ValueError):
        session.add_points(30, 40, [])
    assert not session.rows and not session.dirty


def test_partial_raw_cannot_hide_aggregate_instability_or_authorize_changes():
    context = fixture_survey()
    for row in context["rows"]:
        row["signal_dbm"] = -50 if row["bssid"].endswith(":10") else -65
        row["signal_min_dbm"] = -90 if row["bssid"].endswith(":10") else -65
        row["signal_max_dbm"] = -40 if row["bssid"].endswith(":10") else -65
    context["raw_rows"] = [r for r in context["raw_rows"] if r["bssid"].endswith(":20")]
    ranges = get_signal_ranges_by_key(context["rows"], context["raw_rows"], {"Office"})
    assert max(ranges.values()) == 50
    quality = evaluate_point_quality(context["rows"], context["raw_rows"], {"Office"})
    assert all(r["status"] == QUALITY_UNSTABLE_SIGNAL for r in quality.values())
    assert not findings(analyze_survey(**context), "channel_change")


def test_partial_or_replayed_raw_cannot_authorize_operational_advice():
    context = fixture_survey()
    context["raw_rows"] = context["raw_rows"][:1] * 5
    assert not findings(analyze_survey(**context), "channel_change")


def test_ht40_unknown_offset_is_unknown_and_known_ht40_overlap_is_nonzero():
    assert math.isnan(channel_overlap_weight(1, 6, "2.4", 40, 20))
    assert channel_overlap_weight(1, 6, "2.4", 40, 20, 1, None) == .75


def test_discontiguous_80_plus_80_is_never_reinterpreted_as_contiguous_160():
    assert scanner.normalize_channel_width_mhz("80+80") == "80+80"
    assert math.isnan(channel_overlap_weight(36, 149, "5", "80+80", 20))
    assert get_channel_frequency_range(36, 320, "5") is None
    assert get_channel_frequency_range(33, 320, "6") is None


@pytest.mark.parametrize("row", [dict(channel=5), dict(channel=5.5, band="2.4"),
    dict(channel=5, band="2.4", frequency_mhz=5975),
    dict(channel=36, band="5", frequency_mhz=5200), dict(channel=float("inf"))])
def test_ambiguous_contradictory_and_fractional_band_evidence_is_unknown(row):
    assert get_row_band(row) == ""


def test_contradictory_band_blocks_specific_channel_advice():
    context = fixture_survey(channel=5)
    for row in context["rows"] + context["raw_rows"]:
        row["frequency_mhz"] = 5975
    report = analyze_survey(**context)
    assert findings(report, "scanner_limits")
    assert not findings(report, "channel_change")


def test_automatic_mac_group_does_not_suppress_independent_interferer():
    context = fixture_survey()
    context["rows"] = [r for r in context["rows"] if r["ssid"] == "Office"]
    context["raw_rows"] = [r for r in context["raw_rows"] if r["ssid"] == "Office"]
    for row in context["rows"] + context["raw_rows"]:
        row["bssid"] = "02:aa:bb:cc:dd:11" if row["bssid"].endswith(":10") else "06:aa:bb:cc:dd:12"
    context["groups"] = build_default_manual_groups(context["rows"])
    assert len(context["groups"]) == 1  # UI suggestion retained.
    report = analyze_survey(**context)
    assert findings(report, "channel_overlap") and findings(report, "unconfirmed_group")
    assert not findings(report, "channel_change")
    risk = calculate_interference_points(pd.DataFrame(context["rows"]), "Office", "2.4", include_details=True,
        ap_group_map=build_bssid_to_manual_group_map(context["groups"], confirmed_only=True))
    assert (risk["risk"] > 0).all() and not risk["same_physical_ap_ignored_count"].any()


def test_unconfirmed_group_retains_user_metadata_without_collapsing_rf_neighbors():
    from ap.groups import build_ap_group_role_map, build_ap_group_channel_override_map
    from ap.metadata import build_ap_metadata_warnings
    from maps.heatmap import add_ap_group_metadata, apply_ap_channel_analysis_overrides
    context = fixture_survey()
    bssids = sorted({r["bssid"] for r in context["rows"] if r["ssid"] == "Office"})
    group = dict(group_id="proposed", bssids=bssids, physical_confirmed=False, locked=True,
        role="external", metadata=dict(expected_channels="6", analysis_channel_override_24="11"))
    membership = build_bssid_to_manual_group_map([group])
    rf_map = build_bssid_to_manual_group_map([group], confirmed_only=True)
    assert {membership[bssid] for bssid in bssids} == {"proposed"}
    assert {rf_map[bssid] for bssid in bssids} == set(bssids)
    assert build_ap_metadata_warnings(context["rows"], [group])[0]["group_id"] == "proposed"
    mapped = add_ap_group_metadata(pd.DataFrame(context["rows"]), rf_map, build_ap_group_role_map([group]))
    assert set(mapped[mapped["bssid"].isin(bssids)]["ap_role"]) == {"external"}
    mapped, _ = apply_ap_channel_analysis_overrides(mapped, build_ap_group_channel_override_map([group]))
    assert set(mapped[mapped["bssid"].isin(bssids)]["channel"]) == {11}
    group["role"] = "test"
    risk = calculate_interference_points(pd.DataFrame(context["rows"]), "Office", "2.4",
        ap_group_map=rf_map, ap_group_roles=build_ap_group_role_map([group]))
    assert risk.empty


@pytest.mark.parametrize("signal", [float("nan"), float("inf"), -200, 1])
def test_invalid_bss_does_not_discard_other_valid_observations(signal):
    rows = scanner.parse_lswifi_bss_list([bss(signal=signal), bss("Good")])
    assert [r["ssid"] for r in rows] == ["Good"]


def test_invalid_coordinates_fail_before_persistence_or_mutation(tmp_path):
    session = SurveySession()
    with pytest.raises(ValueError):
        session.add_points(float("inf"), 1, [fresh_sample()])
    assert not session.rows and not session.dirty
    session.add_points(1, 2, scanner.merge_wifi_scans([fresh_sample()], 5))
    path = str(tmp_path / "invalid.csv")
    session.save(path)
    session.rows[0]["x"] = "inf"
    write_survey_file(path, session.metadata, session.rows)
    with pytest.raises(SurveyFormatError):
        SurveySession(path)


def test_adapter_identity_is_not_merged_and_denominator_is_per_receiver():
    samples = [fresh_sample(i, 100 + i, adapter=a) for a in ("one", "two") for i in range(1, 6)]
    rows = scanner.merge_wifi_scans(samples, 5)
    assert len(rows) == 2
    assert {r["adapter_id"] for r in rows} == {"one", "two"}
    assert all(r["scan_confidence"] == 1 and r["samples_total"] == 5 for r in rows)


def test_native_capture_uses_only_the_connected_receiver_and_its_attempt_count():
    from lswifi import wlanapi
    interfaces = {0: NS(guid="unconnected"), 1: NS(guid="connected")}
    outcomes = [dict(status="complete", started=100 + i*100, completed=120 + i*100) for i in range(5)]
    items = [[bss(stamp=110 + i*100)] for i in range(5)]
    def connected(_api, iface):
        return {"ssid": "Office"} if iface.guid == "connected" else {}
    with patch.object(wlanapi.WLAN, "get_wireless_interfaces", return_value=interfaces), \
            patch("wifi.scanner.get_lswifi_connected_network", side_effect=connected), \
            patch("wifi.scanner.scan_and_wait", side_effect=outcomes) as request, \
            patch("wifi.scanner.read_bss_list", side_effect=items), \
            patch("wifi.scanner.time.sleep"), patch("wifi.scanner.filetime_now", return_value=1000):
        rows = scanner.scan_wifi_lswifi(False)
    assert request.call_count == 5
    assert all(call.args[1].guid == "connected" for call in request.call_args_list)
    assert rows[0]["samples_seen"] == rows[0]["samples_total"] == 5
    assert rows[0]["adapter_id"] == "connected" and rows[0]["scan_confidence"] == 1


def test_qt_scan_worker_preserves_empty_capture_outcome():
    from qt_ui.qt_point_workflow import WifiScanWorker
    batch = scanner.ScanBatch([], dict(status="complete", freshness="fresh", backend="lswifi"))
    worker = WifiScanWorker()
    received = []
    worker.finished.connect(lambda rows, backend: received.append((rows, backend)))
    with patch("qt_ui.qt_point_workflow.scan_wifi", return_value=(batch, "lswifi")):
        worker.run()
    assert received[0][0] is batch and received[0][0].capture["status"] == "complete"


@pytest.fixture
def qt_runtime():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_empty_capture_is_visible_in_point_table_floorplan_and_dashboard(qt_runtime, tmp_path):
    from PIL import Image
    from qt_ui.qt_app import WifiHeatmapQtApp
    from qt_ui.qt_quality_dashboard import build_dashboard_rows
    window = WifiHeatmapQtApp()
    try:
        window.session = SurveySession()
        plan = tmp_path / "plan.png"
        Image.new("RGB", (200, 150), "white").save(plan)
        window.session.metadata["map_file"] = str(plan)
        window.load_saved_plan()
        window.pending_scan_point = (30, 40)
        from qt_ui.qt_capture_dialog import GuidedCaptureDialog
        window.capture_dialog = GuidedCaptureDialog(window, 30, 40)
        batch = scanner.ScanBatch([], dict(status="complete", freshness="fresh", backend="lswifi"))
        window.finish_wifi_scan(batch, "lswifi")
        assert not window.session.measurement_points()
        window.accept_wifi_capture()
        qt_runtime.processEvents()
        assert window.points_table.rowCount() == len(window.floorplan_view.marker_items) == 1
        assert window.points_table.item(0, 3).text() == "—"
        assert window.points_table.item(0, 4).text() == window.tr("measurement_collection_unverified")
        dashboard = build_dashboard_rows(window, window.session.get_point_summaries(), {})
        assert dashboard[0]["best"] == "—" and dashboard[0]["needs_review"]
        assert not window.session.rows and not window.session.raw_scan_rows
    finally:
        window.session = None
        window.deleteLater()
        qt_runtime.processEvents()


def test_group_confirmation_badge_persists_independently_of_alias(qt_runtime):
    from PySide6.QtCore import Qt
    from ap.groups import is_ap_group_confirmed
    from qt_ui.qt_app import WifiHeatmapQtApp
    from qt_ui.qt_ap_groups import APGroupManagerDialog
    window = WifiHeatmapQtApp()
    dialog = None
    try:
        window.session = SurveySession()
        window.session.rows = fixture_survey()["rows"]
        dialog = APGroupManagerDialog(window)
        dialog.table.selectRow(0)
        group = dialog.require_selected_group()
        assert not is_ap_group_confirmed(group)
        dialog.set_alias(group, "Office AP")
        assert not is_ap_group_confirmed(group)
        dialog.table.selectRow(0)
        group = dialog.require_selected_group()
        dialog.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        assert is_ap_group_confirmed(group)
        dialog.save_groups()
        assert next(g for g in window.session.get_ap_groups() if g["group_id"] == group["group_id"])["physical_confirmed"]
    finally:
        if dialog is not None:
            dialog.deleteLater()
        window.session = None
        window.deleteLater()
        qt_runtime.processEvents()


def test_live_and_export_configs_keep_unconfirmed_bssids_separate(qt_runtime):
    from qt_ui.qt_app import WifiHeatmapQtApp
    window = WifiHeatmapQtApp()
    try:
        window.session = SurveySession()
        window.session.rows = fixture_survey()["rows"]
        bssids = sorted({r["bssid"] for r in window.session.rows if r["ssid"] == "Office"})
        group = dict(group_id="proposed", bssids=bssids, physical_confirmed=False,
            locked=True, role="external", alias="Proposed AP")
        window.session.set_ap_groups([group], update_memory=False)
        window.live_ssid_combo.addItem("Office")
        window.live_ssid_combo.setCurrentText("Office")
        for config in (window.build_live_map_config(), window.build_export_default_config()):
            assert {dict(config.ap_group_map)[bssid] for bssid in bssids} == set(bssids)
            assert {dict(config.ap_group_roles)[bssid] for bssid in bssids} == {"external"}
        assert {key for key, label in window.live_ap_group_filter_items()} == set(bssids)
    finally:
        window.session = None
        window.deleteLater()
        qt_runtime.processEvents()


def test_mixed_receivers_in_survey_block_operational_comparisons():
    context = fixture_survey()
    for row in context["rows"] + context["raw_rows"]:
        if row["point_id"] == "p3":
            row["adapter_id"] = "different-receiver"
    report = analyze_survey(**context)
    assert findings(report, "mixed_receivers") and not findings(report, "channel_change")


def test_rescan_same_second_deletes_only_original_point_id():
    session = SurveySession()
    rows = scanner.merge_wifi_scans([fresh_sample()], 5)
    session.add_points(1, 2, rows)
    original = session.get_point_summaries()[0]
    session.add_points(1, 2, rows)
    assert len(session.get_point_summaries()) == 2
    session.delete_point(original["timestamp"], 1, 2, original["point_id"])
    assert len(session.get_point_summaries()) == 1
    assert session.get_point_summaries()[0]["point_id"] != original["point_id"]


@pytest.mark.parametrize("confidence", [None, "", "bad", float("nan"), float("inf"), 1])
def test_legacy_or_unknown_confidence_never_becomes_100_percent(confidence):
    row = {"scan_confidence": confidence}
    assert scan_confidence(row) == 0
    assert get_scan_confidence_values(pd.DataFrame([row]))[0] == 0
    assert normalize_confidence_array([float("nan")], 1)[0] == 0


def test_repeated_position_ids_do_not_authorize_power_reduction():
    context = fixture_survey()
    for row in context["rows"] + context["raw_rows"]:
        row["x"] = 600
        row["signal_dbm"] = -40 if row["bssid"].endswith(":10") else -65
    context["groups"][1]["position"] = {"x": 600, "y": 100}
    report = analyze_survey(**context)
    assert findings(report, "dominance")
    assert not any(f.action == "power_trial" for f in report.findings)
