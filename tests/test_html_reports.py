"""Export behavior: useful summary, retained evidence and standalone files."""

from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest
from PIL import Image

from advisor.engine import analyze_survey
from advisor.presentation import report_html
from exporting.analysis_report import export_analysis_report
from exporting.live_html import generate_live_html_export
from maps.config import MapConfig
from qt_ui.qt_live_preview import LivePreviewMixin
from tests.test_advisor import fixture_survey, analysis_window, qt_app, wait_for_analysis
from translations.i18n import translate
from survey.plan_drawing import PLAN_DRAWING_KEY, encode_drawing, rectangle_segments


class ReportDOM(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.links, self.resources, self.details = [], [], [], []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag in {"img", "image", "link", "script", "iframe"}:
            self.resources.extend(attrs[key] for key in ("src", "href") if key in attrs)
        if tag == "details":
            self.details.append(attrs)


@pytest.mark.parametrize("language", ["en", "it", "fr", "es"])
def test_analysis_html_prioritizes_actions_preserves_evidence_and_has_no_external_resources(tmp_path, language):
    context = fixture_survey()
    report = analyze_survey(**context)
    before = deepcopy(report.to_dict())
    output = tmp_path / "report.html"
    export_analysis_report(report, output, language, Image.new("RGB", (400, 300), "white"))
    html = output.read_text(encoding="utf-8")
    dom = ReportDOM(html)
    assert html.index('id="actions"') < html.index('id="reviews"')
    assert dom.details and all("open" not in attrs for attrs in dom.details)
    assert len(dom.ids) == len(set(dom.ids))
    assert all(link[1:] in dom.ids for link in dom.links if link.startswith("#"))
    assert all(resource.startswith("data:image/png;base64,") for resource in dom.resources)
    assert "beforeprint" in html and "afterprint" in html
    assert "advisor_" not in html and "report_" not in html
    assert report.fingerprint[:16] in html and "receiver-one" in html
    for point in report.points:
        assert str(point.x) in html or f"{point.x:g}" in html
    assert report.to_dict() == before


def test_data_constraints_and_limits_are_outside_collapsed_measurements():
    context = fixture_survey()
    context["raw_rows"] = []
    report = analyze_survey(**context)
    html = report_html(report, "it")
    assert 'class="callout"' in html and 'class="card data"' in html
    assert "Le evidenze attuali non supportano" in html
    assert "Rischio" not in html or "throughput" in html
    assert translate("it", "advisor_general_limit") in html


@pytest.mark.parametrize("kind", ["signal", "interference", "channel", "dominant"])
@pytest.mark.parametrize("language", ["en", "it", "fr", "es"])
def test_live_html_all_maps_are_local_and_point_links_resolve(tmp_path, qt_app, kind, language):
    context = fixture_survey()
    tr = lambda key, **kw: translate(language, key, **kw)
    translations = LivePreviewMixin.build_live_renderer_translations(SimpleNamespace(tr=tr, measurement_system="metric"))
    output = tmp_path / f"{kind}-{language}.html"
    result = generate_live_html_export(pd.DataFrame(context["rows"]), Image.new("RGB", (400, 300), "white"),
        str(tmp_path / "survey.csv"), MapConfig(ssid="Office", band="2.4", map_type=kind, interpolation="linear"),
        tr, translations, language, ap_groups=context["groups"], px_per_meter=10, output_file=output)
    html = output.read_text(encoding="utf-8")
    dom = ReportDOM(html)
    assert result.files == [str(output)]
    assert "<svg" in html and 'href="#point-1"' in html
    assert all(link[1:] in dom.ids for link in dom.links if link.startswith("#"))
    assert len(dom.ids) == len(set(dom.ids))
    assert all(resource.startswith("data:image/png;base64,") for resource in dom.resources)
    assert "advisor_" not in html and "report_" not in html
    assert "receiver-one" in html
    assert not list(tmp_path.glob("*.pdf"))


def test_unknown_rf_risk_stays_visible_without_opening_point_details(tmp_path, qt_app):
    context = fixture_survey()
    for row in context["rows"]:
        row["channel_width_mhz"] = 40
    tr = lambda key, **kw: translate("it", key, **kw)
    translations = LivePreviewMixin.build_live_renderer_translations(SimpleNamespace(tr=tr, measurement_system="metric"))
    output = tmp_path / "unknown.html"
    generate_live_html_export(pd.DataFrame(context["rows"]), Image.new("RGB", (400, 300), "white"), "survey.csv",
        MapConfig(ssid="Office", band="2.4", map_type="interference"), tr, translations,
        language="it", output_file=output)
    html = output.read_text(encoding="utf-8")
    assert "Sovrapposizione RF non determinabile in 4 punti" in html
    assert "La geometria mancante non indica interferenza nulla" in html
    assert 'fill="#6b7280"' in html


def test_failed_html_replace_keeps_existing_report(tmp_path):
    path = tmp_path / "report.html"
    path.write_text("previous report", encoding="utf-8")
    with patch("app_core.file_io.os.replace", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            export_analysis_report(analyze_survey(**fixture_survey()), path)
    assert path.read_text(encoding="utf-8") == "previous report"


def test_analysis_advanced_controls_keep_values_summary_and_quality_guards(analysis_window):
    view = analysis_window.analysis_view
    before = view.report.fingerprint
    assert not view.settings_panel.isVisible()
    view.settings_button.setChecked(True)
    assert not view.settings_panel.isHidden()
    assert view.report.fingerprint == before
    view.confidence.setValue(75)
    assert "75%" in view.settings_summary.text()
    view.settings_button.setChecked(False)
    assert view.confidence.value() == 75 and view.settings_panel.isHidden()
    wait_for_analysis(view)
    assert view.report.fingerprint != before


def test_analysis_export_defaults_to_html_and_detects_changes_during_dialog(analysis_window, tmp_path):
    view = analysis_window.analysis_view
    output = str(tmp_path / "analysis")
    with patch("qt_ui.qt_analysis.get_centered_save_file_name", return_value=(output, "")) as choose:
        assert view.export_report()
        assert ".analysis.html" in choose.call_args.args[2]
        assert "*.html" in choose.call_args.args[3] and "*.pdf" not in choose.call_args.args[3]
    assert Path(output + ".html").is_file()
    def edited(*_):
        analysis_window.session.rows[0]["signal_dbm"] = -90
        return output, ""
    with patch("qt_ui.qt_analysis.get_centered_save_file_name", side_effect=edited), \
            patch("qt_ui.qt_analysis.export_analysis_report") as export:
        assert not view.export_report()
        export.assert_not_called()
    wait_for_analysis(view)


def test_live_ui_exports_html_and_rejects_changed_options_in_file_dialog(analysis_window, tmp_path):
    window = analysis_window
    image = tmp_path / "plan.png"
    Image.new("RGB", (400, 300), "white").save(image)
    window.session.metadata["map_file"] = str(image)
    window.session.csv_file = str(tmp_path / "survey.csv")
    window.live_ssid_combo.addItem("Office")
    window.live_ssid_combo.setCurrentText("Office")
    output = str(tmp_path / "live.html")
    with patch.object(window, "can_render_live_preview", return_value=True), \
            patch.object(window, "ensure_saved_for_map_export", return_value=True), \
            patch("qt_ui.qt_live_export.QMessageBox.information"), \
            patch("qt_ui.qt_live_export.get_centered_save_file_name", return_value=(output, "")):
        assert window.export_live_report()
    assert Path(output).is_file() and not list(tmp_path.glob("*.pdf"))
    def changed(*_):
        window.live_generation += 1
        return output, ""
    with patch.object(window, "can_render_live_preview", return_value=True), \
            patch.object(window, "ensure_saved_for_map_export", return_value=True), \
            patch("qt_ui.qt_live_export.get_centered_save_file_name", side_effect=changed), \
            patch("qt_ui.qt_live_export.generate_live_html_export") as export:
        assert not window.export_live_report()
        export.assert_not_called()


def test_live_export_escapes_names_and_passes_the_boundary_mask_to_shared_renderer(tmp_path, qt_app):
    from qt_ui.qt_live_map import render_live_map_payload
    context = fixture_survey()
    df = pd.DataFrame(context["rows"])
    malicious = '<img src="https://example.invalid/track">'
    df.loc[df.ssid == "Office", "ssid"] = malicious
    tr = lambda key, **kw: translate("en", key, **kw)
    translations = LivePreviewMixin.build_live_renderer_translations(SimpleNamespace(tr=tr, measurement_system="metric"))
    mask = Image.new("L", (400, 300), 255)
    before = df.copy(deep=True)
    output = tmp_path / "masked.html"
    with patch("exporting.live_html.render_live_map_payload", wraps=render_live_map_payload) as render:
        generate_live_html_export(df, Image.new("RGB", (400, 300), "white"), "survey.csv",
            MapConfig(ssid=malicious, band="2.4", map_type="signal"), tr, translations,
            output_file=output, boundary_mask_image=mask)
        assert render.call_args.args[-1] is mask
    pd.testing.assert_frame_equal(df, before)
    html = output.read_text(encoding="utf-8")
    assert '<img src="https://' not in html and "&lt;img" in html
    assert all(resource.startswith("data:") for resource in ReportDOM(html).resources)


@pytest.mark.parametrize("operation", ["draw", "erase", "move", "line"])
def test_both_workspace_html_exports_include_current_editable_shapes(analysis_window, tmp_path, operation):
    window = analysis_window
    image = tmp_path / "drawing.png"
    Image.new("RGB", (400, 300), "white").save(image)
    window.session.metadata.update(map_file=str(image), _generated_floorplan="1", px_per_meter="50")
    lines = rectangle_segments(100, 100, 120, 60, "#d84315")
    # Keep a stale baked top side to verify an erase also removes old raster ink.
    from survey.plan_drawing import render_plan_drawing
    render_plan_drawing(Image.new("RGB", (400, 300), "white"), lines).save(image)
    window.session.metadata[PLAN_DRAWING_KEY] = encode_drawing(lines)
    window.session.csv_file = str(tmp_path / "survey.csv")
    window.load_saved_plan()
    window.refresh_session_labels()
    if operation == "erase":
        window.plan_tools.set_open(True)
        window.plan_tools.eraser_button.click()
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtTest import QTest
        point = window.floorplan_view.mapFromScene(QPointF(150, 100))
        QTest.mouseClick(window.floorplan_view.viewport(), Qt.MouseButton.RightButton, pos=point)
        assert len(window.plan_tools.controller.segments()) == 3
        window.plan_tools.set_open(False)
    elif operation == "move":
        from survey.plan_geometry import translate_segments
        window.plan_tools.set_open(True)
        window.plan_tools.select_button.click()
        selection = window.plan_tools.controller.selection
        selection.set_selected(range(4))
        assert selection.apply_transformed(translate_segments(lines, 0, 80))
        window.plan_tools.set_open(False)
    elif operation == "line":
        from PySide6.QtCore import QLineF
        from PySide6.QtGui import QColor
        window.plan_tools.stroke_color = QColor("#d84315")
        window.plan_tools.controller.line.commit(QLineF(50, 180, 80, 180))
    expected = (255, 255, 255) if operation in ("erase", "move") else (216, 67, 21)
    bottom = (255, 255, 255) if operation == "move" else (216, 67, 21)
    wait_for_analysis(window.analysis_view)
    analysis = str(tmp_path / "drawing.analysis.html")
    with (patch("qt_ui.qt_analysis.get_centered_save_file_name", return_value=(analysis, "")),
          patch("qt_ui.qt_analysis.export_analysis_report", wraps=export_analysis_report) as export):
        assert window.analysis_view.export_report()
        assert export.call_args.args[3].getpixel((150, 100)) == expected
        assert export.call_args.args[3].getpixel((150, 160)) == bottom
        if operation == "move":
            assert export.call_args.args[3].getpixel((150, 180)) == (216, 67, 21)
        if operation == "line":
            assert export.call_args.args[3].getpixel((60, 180)) == (216, 67, 21)
    assert Path(analysis).is_file()
    window.live_ssid_combo.addItem("Office")
    window.live_ssid_combo.setCurrentText("Office")
    live = str(tmp_path / "drawing.live.html")
    with (patch.object(window, "can_render_live_preview", return_value=True),
          patch.object(window, "ensure_saved_for_map_export", return_value=True),
          patch("qt_ui.qt_live_export.QMessageBox.information"),
          patch("qt_ui.qt_live_export.get_centered_save_file_name", return_value=(live, "")),
          patch("qt_ui.qt_live_export.generate_live_html_export", wraps=generate_live_html_export) as export):
        assert window.export_live_report()
        assert export.call_args.args[1].getpixel((150, 100)) == expected
        assert export.call_args.args[1].getpixel((150, 160)) == bottom
        if operation == "move":
            assert export.call_args.args[1].getpixel((150, 180)) == (216, 67, 21)
        if operation == "line":
            assert export.call_args.args[1].getpixel((60, 180)) == (216, 67, 21)
    assert Path(live).is_file()
