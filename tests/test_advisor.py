"""Evidence and safety tests for the local RF analysis and report workflow."""

from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import string
import time
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtCore import QUrl, QSize
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtPdf import QPdfDocument

from advisor.engine import analyze_survey
from advisor.models import AnalysisProfile
from advisor.presentation import report_html
from exporting.analysis_report import export_analysis_report
from qt_ui.qt_app import WifiHeatmapQtApp
from survey.store import SurveySession
from translations.i18n import TRANSLATIONS


def fixture_survey(point_count=4, band="2.4", channel=1, width=20):
    groups = [dict(group_id="a", alias="Corridoio", bssids=["02:00:00:00:00:10"], role="internal",
                   position={"x": 0, "y": 0}),
              dict(group_id="b", alias="Ufficio", bssids=["02:00:00:00:00:20"], role="internal",
                   position={"x": 300, "y": 100}),
              dict(group_id="neighbor", alias="Vicino", bssids=["02:00:00:00:00:30"], role="external")]
    rows, raw = [], []
    for index in range(point_count):
        for ap_index, group in enumerate(groups):
            row = dict(point_id=f"p{index}", timestamp=f"2026-11-03T10:00:{index:02d}",
                x=80 + index * 60, y=100, ssid="Office" if ap_index < 2 else "Neighbor",
                bssid=group["bssids"][0], band=band, channel=channel, channel_width_mhz=width,
                signal_dbm=-55 + ap_index * 3, samples_seen=5, samples_total=5,
                scan_confidence=1.0, backend="lswifi", frequency_mhz=2412 if band == "2.4" else 5180,
                adapter_id="receiver-one", freshness="fresh", signal_kind="direct",
                scan_started_at=100000 + index * 100, scan_completed_at=100010 + index * 100,
                observed_at=100020 + index * 100, host_timestamp=100001 + index * 100)
            rows.append(row)
            raw.extend({**row, "scan_attempt": attempt, "host_timestamp": 100000 + index * 100 + attempt} for attempt in range(1, 6))
    return dict(rows=rows, raw_rows=raw, groups=groups, relevant_ssids={"Office"}, px_per_meter=10,
                survey_name="Test survey")


def findings(report, rule):
    return [f for f in report.findings if f.rule == rule]


def test_channel_proposals_form_one_improved_plan_without_external_changes():
    context = fixture_survey()
    report = analyze_survey(**context)
    proposals = findings(report, "channel_change")
    assert proposals
    assignment = {"a": 1, "b": 1, "neighbor": 1}
    for proposal in proposals:
        assert proposal.confidence != "high"
        assert proposal.group_ids[0] != "neighbor"
        assert proposal.metrics["modeled_after"] < proposal.metrics["modeled_before"]
        assert len(proposal.point_ids) >= 3
        assignment[proposal.group_ids[0]] = proposal.metrics["new_channel"]
    assert len(set(assignment.values())) == 3
    assert context == fixture_survey()
    json.dumps(report.to_dict(), allow_nan=False)


def test_recommendations_are_deterministic_and_do_not_mutate_input():
    context = fixture_survey()
    before = deepcopy(context)
    first, second = analyze_survey(**context), analyze_survey(**context)
    assert first.fingerprint == second.fingerprint
    assert first.findings == second.findings
    assert context == before


@pytest.mark.parametrize("change", ["confidence", "width", "channel", "sparse"])
def test_specific_channel_proposals_require_stable_sufficient_evidence(change):
    context = fixture_survey(point_count=1 if change == "sparse" else 4)
    for row in context["rows"]:
        if change == "confidence":
            row["scan_confidence"] = 0.1
        elif change == "width":
            row["channel_width_mhz"] = ""
        elif change == "channel":
            row["channel"] = 6 if row["point_id"] == "p0" else 1
    assert not findings(analyze_survey(**context), "channel_change")


def test_radio_with_manual_override_is_never_a_change_target():
    context = fixture_survey()
    context["groups"][0]["metadata"] = {"analysis_channel_override_24": "6"}
    report = analyze_survey(**context)
    assert findings(report, "model_override")
    assert all(f.group_ids != ("a",) for f in findings(report, "channel_change"))


def test_conflicting_expected_metadata_is_reported_before_changing_target():
    context = fixture_survey()
    context["groups"][0]["metadata"] = {"expected_channels": "11", "expected_bands": "5"}
    report = analyze_survey(**context)
    mismatch = findings(report, "metadata_mismatch")[0]
    assert mismatch.metrics["expected_channels"] == "11"
    assert mismatch.metrics["observed_channels"] == "1"
    assert all(f.group_ids != ("a",) for f in findings(report, "channel_change"))


def test_low_confidence_external_neighbor_prevents_false_precise_proposals():
    context = fixture_survey()
    for row in context["rows"]:
        if row["ssid"] == "Neighbor":
            row["scan_confidence"] = 0.1
    report = analyze_survey(**context)
    assert findings(report, "channel_evidence")
    assert not findings(report, "channel_change")


def test_6ghz_missing_frequency_does_not_allow_specific_channel_advice():
    context = fixture_survey(band="6", channel=5)
    context["profile"] = AnalysisProfile(channels_6=(1, 5, 9))
    report = analyze_survey(**context)
    assert findings(report, "scanner_limits")
    assert not findings(report, "channel_change")


def test_unknown_neighbor_band_blocks_precise_channel_plan():
    context = fixture_survey()
    for row in context["rows"]:
        if row["ssid"] == "Neighbor":
            row.update(band="", channel="", frequency_mhz="")
    report = analyze_survey(**context)
    assert findings(report, "channel_evidence")
    assert not findings(report, "channel_change")


def test_missing_scale_is_explicit_and_disables_distance_conclusions():
    context = fixture_survey()
    context["px_per_meter"] = None
    report = analyze_survey(**context)
    assert findings(report, "scale_required")
    assert not findings(report, "dominance")


def test_same_physical_ap_multiple_ssids_is_not_its_own_interferer():
    context = fixture_survey()
    context["rows"] = [r for r in context["rows"] if r["bssid"].endswith(":10")]
    context["groups"] = context["groups"][:1]
    for row in list(context["rows"]):
        context["rows"].append({**row, "ssid": "Guest"})
    report = analyze_survey(**context)
    assert not findings(report, "channel_overlap")
    assert not findings(report, "channel_change")


def test_test_role_is_excluded_and_ssid_case_is_preserved():
    context = fixture_survey()
    context["groups"][1]["role"] = "test"
    context["relevant_ssids"] = {"office"}
    report = analyze_survey(**context)
    assert findings(report, "missing_network")[0].ssid == "office"
    assert not findings(report, "channel_change")
    assert all(r.group_id != "b" for r in report.readings)


def test_5ghz_channel_proposal_requires_candidate_policy():
    context = fixture_survey(band="5", channel=36)
    assert not findings(analyze_survey(**context), "channel_change")
    context["profile"] = AnalysisProfile(channels_5=(36, 40, 44))
    assert findings(analyze_survey(**context), "channel_change")


def test_local_scope_is_shared_with_quality_and_does_not_expect_whole_site_coverage():
    context = fixture_survey()
    local = context["groups"][1]
    local["metadata"] = {"coverage_scope": "local", "coverage_radius_m": "12"}
    for row in context["rows"]:
        if row["bssid"].endswith(":20"):
            row["ssid"] = "Zone"
    # Zone is present at p0 only. p1 is within the AP radius; p3 is outside it.
    local["position"] = {"x": 80, "y": 100}
    context["rows"] = [r for r in context["rows"] if r["ssid"] != "Zone" or r["point_id"] == "p0"]
    context["relevant_ssids"] = {"Office", "Zone"}
    report = analyze_survey(**context)
    missing = next(f for f in findings(report, "missing_network") if f.ssid == "Zone")
    assert "p1" in missing.point_ids
    assert "p3" not in missing.point_ids


def test_power_trial_requires_repetition_alternative_coverage_and_positions():
    context = fixture_survey()
    for row in context["rows"]:
        row["x"] = 600 + int(row["point_id"][1:]) * 30
        row["signal_dbm"] = -40 if row["bssid"].endswith(":10") else -65
    for row in context["raw_rows"]:
        row["x"] = 600 + int(row["point_id"][1:]) * 30
        row["signal_dbm"] = -40 if row["bssid"].endswith(":10") else -65
    context["groups"][1]["position"] = {"x": 600, "y": 100}
    report = analyze_survey(**context)
    power = next(f for f in findings(report, "dominance") if f.action == "power_trial")
    assert "b" in power.metrics["neighbor_ids"]
    assert power.metrics["distance_min_m"] >= 60
    context["rows"] = [r for r in context["rows"] if not r["bssid"].endswith(":20")]
    report = analyze_survey(**context)
    assert not any(f.action == "power_trial" for f in report.findings)


def test_weak_coverage_is_counted_at_points_not_interpolated_area():
    context = fixture_survey()
    for row in context["rows"] + context["raw_rows"]:
        row["signal_dbm"] = -80
    report = analyze_survey(**context)
    result = findings(report, "weak_coverage")[0]
    assert result.metrics["points"] == result.metrics["total"] == 4
    assert "measured_points_only" in result.limitations
    assert not any(f.action == "power_trial" for f in report.findings)


def test_roaming_is_observation_and_string_zero_is_not_connected():
    context = fixture_survey()
    for row in context["rows"]:
        row["signal_dbm"] = -65 if row["bssid"].endswith(":10") else -50
        row["is_connected"] = "0"
    for row in context["raw_rows"]:
        row["signal_dbm"] = -65 if row["bssid"].endswith(":10") else -50
    assert not findings(analyze_survey(**context), "roaming")
    for row in context["rows"]:
        if row["bssid"].endswith(":10"):
            row["is_connected"] = "1"
    observation = findings(analyze_survey(**context), "roaming")[0]
    assert "client_decides" in observation.limitations
    assert observation.metrics["neighbor_ids"] == ("b",)


def test_invalid_measurements_do_not_make_nan_scores_or_false_green_results():
    context = fixture_survey()
    context["rows"][0]["x"] = float("nan")
    report = analyze_survey(**context)
    assert findings(report, "invalid_data")
    json.dumps(report.to_dict(), allow_nan=False)


@pytest.mark.parametrize("language", ["en", "it", "fr", "es"])
def test_localized_report_escapes_network_and_ap_names(language):
    context = fixture_survey()
    context["groups"][0]["alias"] = '<img src="https://invalid.example/track"> & AP'
    report = analyze_survey(**context)
    html = report_html(report, language)
    assert '<img src="https://invalid.example' not in html
    assert "&lt;img" in html
    assert "advisor_" not in html
    assert report.fingerprint[:16] in html


@pytest.mark.parametrize("field,value", [("coverage_dbm", float("nan")), ("minimum_confidence", 2),
    ("channels_24", (200,)), ("channels_5", (999,)), ("minimum_points", 1)])
def test_invalid_profiles_are_rejected(field, value):
    with pytest.raises(ValueError):
        replace(AnalysisProfile(), **{field: value})


@pytest.fixture
def qt_app():
    app = QApplication.instance() or QApplication([])
    # The Windows offscreen platform does not enumerate OS fonts. Register
    # the same font used by the app so PDF glyphs/layout are actually tested.
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen" and os.name == "nt":
        for name in ("segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf"):
            font = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / name
            if font.exists():
                QFontDatabase.addApplicationFont(str(font))
    return app


@pytest.mark.parametrize("language", ["en", "it", "fr", "es"])
def test_pdf_and_html_export_same_snapshot(tmp_path, qt_app, language):
    report = analyze_survey(**fixture_survey())
    image = Image.new("RGB", (400, 300), "white")
    pdf = tmp_path / f"report-{language}.pdf"
    html = pdf.with_suffix(".html")
    export_analysis_report(report, pdf, language, image)
    export_analysis_report(report, html, language, image)
    document = QPdfDocument(None)
    try:
        assert document.load(str(pdf)) == QPdfDocument.Error.None_
        assert document.pageCount() > 0
        assert not document.render(0, QSize(600, 800)).isNull()
        text = " ".join(document.getAllText(i).text() for i in range(document.pageCount()))
        assert report.fingerprint[:16] in text
        assert "Corridoio" in text
        assert document.render(0, QSize(600, 800)).pixelColor(0, 0).name() == "#ffffff"
        for page in range(document.pageCount()):
            lines = document.getAllText(page).text().splitlines()
            ap_rows = sum(line in {"Corridoio", "Ufficio", "Vicino"} for line in lines)
            ssid_rows = sum(line in {"Office · 2.4 GHz", "Neighbor · 2.4 GHz"} for line in lines)
            assert ap_rows == ssid_rows  # No evidence row split between pages.
    finally:
        document.close()
    assert "data:image/png;base64," in html.read_text(encoding="utf-8")
    assert report.fingerprint[:16] in html.read_text(encoding="utf-8")


def test_failed_pdf_export_preserves_existing_report(tmp_path, qt_app):
    path = tmp_path / "report.pdf"
    path.write_bytes(b"previous report")
    with patch("exporting.analysis_report._print_html", side_effect=OSError("disk full")):
        with pytest.raises(OSError, match="disk full"):
            export_analysis_report(analyze_survey(**fixture_survey()), path)
    assert path.read_bytes() == b"previous report"
    assert list(tmp_path.iterdir()) == [path]


def wait_for_analysis(view):
    deadline = time.monotonic() + 10
    while (view.busy or view.timer.isActive()) and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.01)
    assert not view.busy
    assert view.report is not None


@pytest.fixture
def analysis_window(qt_app, tmp_path, monkeypatch):
    monkeypatch.setenv("WIFI_HEATMAP_AP_MEMORY_FILE", str(tmp_path / "ap.memory"))
    monkeypatch.setenv("WIFI_HEATMAP_SETTINGS_FILE", str(tmp_path / "settings.json"))
    context = fixture_survey()
    window = WifiHeatmapQtApp()
    window.session = SurveySession()
    window.session.rows = context["rows"]
    window.session.raw_scan_rows = context["raw_rows"]
    window.session.metadata["ap_groups"] = json.dumps(context["groups"])
    window.relevant_ssids = {"Office"}
    window.show_workspace_page()
    window.tabs.setCurrentIndex(2)
    wait_for_analysis(window.analysis_view)
    yield window
    window.analysis_view.timer.stop()
    if window.analysis_view.thread:
        wait_for_analysis(window.analysis_view)
    window.deleteLater()
    qt_app.processEvents()


def test_analysis_tab_is_independent_of_live_filters_and_read_only(analysis_window):
    window = analysis_window
    view = window.analysis_view
    assert window.tabs.count() == 3
    assert view.findings.count() > 0
    assert not window.zoom_in_button.isEnabled()
    before = deepcopy(window.session.metadata)
    fingerprint = view.report.fingerprint
    window.live_ssid_combo.setCurrentText("Neighbor")
    view.update_analysis()
    assert view.report.fingerprint == fingerprint
    assert window.session.metadata == before


def test_changed_objectives_and_stale_snapshot_are_detected(analysis_window):
    view = analysis_window.analysis_view
    previous = view.report
    view.target.setValue(-65)
    assert not view.export_button.isEnabled()
    wait_for_analysis(view)
    assert previous.fingerprint != view.report.fingerprint
    analysis_window.session.rows[0]["signal_dbm"] = -90
    assert not view.report_is_current()
    with patch("qt_ui.qt_analysis.get_centered_save_file_name") as choose:
        assert not view.export_report()
    assert not choose.called
    wait_for_analysis(view)


def test_result_from_old_survey_is_rejected_and_invalid_profile_cannot_export(analysis_window):
    view = analysis_window.analysis_view
    previous = view.report
    analysis_window.session.rows[0]["signal_dbm"] = -80
    view.accept_report(previous)
    assert view.pending
    assert not view.report_is_current()
    view.update_analysis()
    wait_for_analysis(view)
    assert view.report.fingerprint != previous.fingerprint
    view.channel_edits["5"].setText("not a channel")
    view.update_analysis()
    assert not view.export_button.isEnabled()
    assert not view.report_is_current()


def test_evidence_links_focus_the_survey_point(analysis_window, tmp_path):
    window = analysis_window
    plan = tmp_path / "plan.png"
    Image.new("RGB", (400, 300), "white").save(plan)
    window.floorplan_view.load_floorplan(str(plan))
    window.analysis_view.focus_evidence(QUrl("point:0"))
    assert window.tabs.currentIndex() == 0
    assert window.current_selected_point()["point_id"] == "p0"


def test_all_rule_strings_have_translation_and_matching_placeholders():
    english = TRANSLATIONS["en"]
    keys = [key for key in english if key.startswith("advisor_")]
    for language in ("it", "fr", "es"):
        for key in keys:
            expected = {f for _, f, _, _ in string.Formatter().parse(english[key]) if f}
            actual = {f for _, f, _, _ in string.Formatter().parse(TRANSLATIONS[language][key]) if f}
            assert expected == actual, (language, key)
