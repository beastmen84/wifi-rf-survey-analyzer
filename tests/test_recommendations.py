"""Recommendation organization and disclosure never change the RF decisions."""
from copy import deepcopy
from dataclasses import replace
from html.parser import HTMLParser
from html import unescape
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt, QUrl

from advisor.engine import analyze_survey
from advisor.models import Finding
from advisor.presentation import finding_html, report_html
from advisor.recommendations import sections, recommendation_kind, empty_recommendation_key
from tests.test_advisor import (fixture_survey, analysis_window as analysis_window,
                               qt_app as qt_app, wait_for_analysis)
from tests.test_html_reports import ReportDOM
from translations.i18n import translate


def finding(rule, category="channels", **kwargs):
    return Finding(rule, rule, category, "warning", "medium", action=rule, **kwargs)


def test_every_finding_is_retained_once_and_channel_plan_keeps_step_order():
    report = analyze_survey(**fixture_survey())
    items = (finding("weak_coverage", "coverage"), finding("channel_unstable"),
             finding("channel_change", metrics={"step": 2}),
             replace(finding("channel_change", metrics={"step": 1}), finding_id="first"),
             finding("low_quality", "data", point_ids=("p0", "p1")),
             finding("missing_network", "coverage", point_ids=("p1", "p2")),
             finding("empty_measurement", "coverage"), finding("missing_position", "position"),
             finding("model_override"), finding("dominance", "position"),
             replace(finding("dominance", "position"), action="power_trial", finding_id="trial"),
             finding("channel_width"), finding("roaming", "roaming"), finding("channel_overlap"),
             finding("future_rule", "new_category"))
    report = replace(report, findings=items)
    before = deepcopy(report.to_dict())
    grouped = sections(report)
    assert grouped.recommendations[:2] == (items[3], items[2])
    assert all(recommendation_kind(f) == "trial" for f in grouped.recommendations[2:4])
    combined = (*grouped.recommendations, *grouped.prerequisites, *grouped.observations)
    assert len(combined) == len(items) and {f.finding_id for f in combined} == {f.finding_id for f in items}
    assert grouped.affected_points == 3
    assert items[-1] in grouped.observations
    assert report.to_dict() == before


class VisibleText(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.depth = 0
        self.visible = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "details":
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == "details":
            self.depth -= 1

    def handle_data(self, text):
        if self.depth == 0:
            self.visible.append(text)


@pytest.mark.parametrize("language", ["en", "it", "fr", "es"])
def test_html_native_order_counts_all_recommendation_types_and_preserves_hidden_details(language):
    report = analyze_survey(**fixture_survey())
    report = replace(report, findings=report.findings + (
        finding("weak_coverage", "coverage", ssid="Office", point_ids=("p0",), metrics={"threshold": -70}),
        finding("channel_width", group_ids=("a",), point_ids=("p0",)),
        finding("missing_position", "position", group_ids=("a",), point_ids=("p0",))))
    before = deepcopy(report.to_dict())
    html = report_html(report, language)
    dom = ReportDOM(html)
    grouped = sections(report)
    assert html.count('class="card action"') == len(grouped.recommendations)
    assert len(dom.ids) == len(set(dom.ids))
    assert all(link[1:] in dom.ids for link in dom.links if link.startswith("#"))
    assert all("open" not in attrs for attrs in dom.details)
    visible = ''.join(VisibleText(html).visible)
    assert translate(language, "advisor_quality_summary", checks=len(grouped.prerequisites), points=grouped.affected_points) in visible
    assert translate(language, "advisor_general_limit") in visible
    assert translate(language, "advisor_rule_missing_position", ap="Corridoio") not in visible
    assert "receiver-one" not in visible and "receiver-one" in html
    assert html.index('id="actions"') < html.index('id="prerequisites"') < html.index('id="reviews"')
    assert report.to_dict() == before


def test_default_detail_is_short_but_keeps_safety_limits_and_context():
    report = analyze_survey(**fixture_survey())
    result = next(f for f in report.findings if f.rule == "channel_change")
    before = deepcopy(report.to_dict())
    compact = finding_html(result, report, "en", True, expanded=False, compact=True)
    expanded = finding_html(result, report, "en", True, expanded=True, compact=True)
    assert "receiver-one" not in compact and "receiver-one" in expanded
    assert "point:0" not in compact and "point:0" in expanded
    assert report.ap_labels[result.group_ids[0]] in compact
    assert translate("en", "advisor_action_channel_change") in unescape(compact)
    for limit in result.limitations:
        assert translate("en", "advisor_" + limit) in unescape(compact)
    assert report.to_dict() == before


def test_native_default_section_and_expansion_do_not_modify_report_or_survey(analysis_window):
    view = analysis_window.analysis_view
    before = deepcopy(view.report.to_dict()), deepcopy(analysis_window.session.metadata)
    grouped = sections(view.report)
    assert view.filter.currentData() == "recommendations"
    assert view.findings.count() == len(grouped.recommendations)
    actual = [view.findings.item(i).data(Qt.ItemDataRole.UserRole) for i in range(view.findings.count())]
    assert actual == list(grouped.recommendations)
    assert not view.evidence_button.isChecked() and "receiver-one" not in view.detail.toPlainText()
    view.evidence_button.setChecked(True)
    assert "receiver-one" in view.detail.toPlainText()
    view.filter.setCurrentIndex(view.filter.findData("everything"))
    assert view.findings.count() == len(view.report.findings)
    assert not view.evidence_button.isChecked()
    assert (view.report.to_dict(), analysis_window.session.metadata) == before


def test_quality_link_and_prerequisite_section_have_no_rf_side_effects(analysis_window):
    view = analysis_window.analysis_view
    analysis_window.session.raw_scan_rows = []
    view.update_analysis(); wait_for_analysis(view)
    grouped = sections(view.report)
    assert grouped.prerequisites and not grouped.recommendations
    assert view.findings.count() == 0
    assert view.text("none_limited") in view.detail.toPlainText()
    assert not view.prerequisites_button.isHidden()
    assert not view.evidence_button.isEnabled()
    before = deepcopy(view.report.to_dict()), deepcopy(analysis_window.session.metadata)
    view.prerequisites_button.click()
    assert view.filter.currentData() == "prerequisites"
    assert view.findings.count() == len(grouped.prerequisites)
    with patch("qt_ui.qt_app.open_qt_quality_dashboard") as show:
        view.quality_button.click()
        show.assert_called_once_with(analysis_window)
    assert (view.report.to_dict(), analysis_window.session.metadata) == before


def test_cached_report_reenables_controls_after_objectives_are_reverted(analysis_window):
    view = analysis_window.analysis_view
    original = view.target.value()
    fingerprint = view.report.fingerprint
    view.target.setValue(original+1)
    assert not view.findings.isEnabled() and not view.evidence_button.isEnabled()
    view.target.setValue(original)
    view.update_analysis()
    assert view.report.fingerprint == fingerprint
    assert view.findings.isEnabled() and view.evidence_button.isEnabled()


@pytest.mark.parametrize("url", ["point:-1", "point:9999", "point:bad", "https://example.invalid/"])
def test_invalid_or_external_evidence_link_is_ignored(analysis_window, url):
    view = analysis_window.analysis_view
    with patch.object(analysis_window.floorplan_view, "focus_on") as focus:
        view.focus_evidence(QUrl(url))
    focus.assert_not_called()
    assert analysis_window.tabs.currentIndex() == 2


def test_empty_report_never_certifies_full_coverage(analysis_window):
    view = analysis_window.analysis_view
    view.accept_report(replace(view.report, findings=()))
    assert view.findings.count() == 0 and not view.evidence_button.isEnabled()
    assert view.text("none") in view.detail.toPlainText()
    assert view.text("quality_ready") == view.quality_summary.text()


def test_collapsed_evidence_does_not_build_or_traverse_reading_tables():
    class UnusedReadings:
        def __iter__(self):
            raise AssertionError("Collapsed detail must not traverse readings")
    report = analyze_survey(**fixture_survey())
    result = next(f for f in report.findings if f.rule == "channel_change")
    report = replace(report, readings=UnusedReadings())
    assert finding_html(result, report, "en", compact=True, expanded=False)


def test_stale_section_does_not_present_an_old_no_action_conclusion(analysis_window):
    view = analysis_window.analysis_view
    analysis_window.session.rows[0]['signal_dbm'] = -90
    view.inputs_changed()
    view.filter.setCurrentIndex(view.filter.findData('observations'))
    assert not view.findings.isEnabled() and not view.evidence_button.isEnabled()
    assert view.text('stale') in view.detail.toPlainText()
    wait_for_analysis(view)


def test_scanning_disables_old_result_controls_and_point_links(analysis_window):
    view = analysis_window.analysis_view
    analysis_window.scan_in_progress = True
    try:
        view.sync_state()
        assert not view.findings.isEnabled() and not view.evidence_button.isEnabled()
        assert not view.quality_button.isEnabled() and not view.export_button.isEnabled()
        with patch.object(analysis_window.floorplan_view, 'focus_on') as focus:
            view.focus_evidence(QUrl('point:0'))
        focus.assert_not_called()
    finally:
        analysis_window.scan_in_progress = False


def test_review_only_channels_keep_overlap_visible_without_an_operational_proposal():
    report = analyze_survey(**fixture_survey(band='5', channel=36))
    grouped = sections(report)
    assert not grouped.recommendations and not grouped.prerequisites and grouped.observations
    assert empty_recommendation_key(grouped) == 'none_observations'
    html = report_html(report, 'it')
    assert translate('it', 'advisor_none_observations') in ''.join(VisibleText(html).visible)
    assert all('finding-'+f.finding_id in html for f in grouped.observations)
