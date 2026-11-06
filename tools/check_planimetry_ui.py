"""Native source QA and exportable audit evidence; no RF or physical print job."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wifi-plan-ui-") as temporary:
        os.environ["WIFI_HEATMAP_SETTINGS_FILE"] = str(Path(temporary) / "settings.json")
        os.environ["WIFI_HEATMAP_AP_MEMORY_FILE"] = str(Path(temporary) / "memory.json")
        from PySide6.QtCore import Qt, QMarginsF, QSize
        from PySide6.QtGui import QPageSize, QImage, QPainter
        from PySide6.QtPrintSupport import QPrinter
        from PySide6.QtPdf import QPdfDocument
        from PySide6.QtWidgets import QApplication, QLabel
        from app_core.settings import save_ui_scale
        from qt_ui.qt_app import WifiHeatmapQtApp
        from qt_ui.qt_plan_objects import ObjectAnnotationDialog
        from qt_ui.qt_plan_printing import clean_plan_image, paint_plan_page
        from survey.plan_objects import object_default, DESK_VARIANTS, SYMBOL_VARIANTS
        from survey.plan_drawing import rectangle_segments
        from survey.plan_label_rendering import build_label
        from tests.test_blank_plan import create_survey
        from tests.test_rectangle_design import move
        from tests.test_plan_annotations import at

        app = QApplication([])
        app.setQuitOnLastWindowClosed(False)
        cases = []
        for language in ("en", "it", "fr", "es"):
            for theme in ("light", "dark"):
                for scale in (100, 125, 175):
                    save_ui_scale(str(scale))
                    window = WifiHeatmapQtApp()
                    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
                    window.change_language(language.upper())
                    window.change_theme(theme)
                    create_survey(window, width=18, height=12)
                    available = window.screen().availableGeometry()
                    window.resize(min(window.spx(1400), available.width()), min(window.spx(950), available.height()))
                    window.show()
                    app.processEvents()
                    d, tools = window.plan_tools.controller, window.plan_tools
                    item = dict(object_default("desk", 50), id="desk1", cx=380, cy=270, width=150, height=80)
                    text = build_label(dict(text="Ufficio", family="Segoe UI", size=24, color="#202938",
                                            outline_color="#ffffff", outline_width=0, alignment="center", x=550, y=150))
                    white = dict(build_label(dict(text="Testo chiaro", family="Segoe UI", size=18, color="#ffffff",
                                            outline_color="#000000", outline_width=0, alignment="center", x=550, y=400)), id="white")
                    d.store(rectangle_segments(160, 80, 540, 420, "#263238"), labels=[text, white])
                    tools.set_open(True)
                    d.annotation.templates["desk"] = item
                    with patch.object(d.annotation, "configure", return_value=True):
                        tools.select_tool("desk")
                    move(d.view, at(window, 380, 270))
                    app.processEvents()
                    assert d.dimensions.values["kind"] == "object"
                    assert d.dimensions.badge.isVisible()
                    assert d.view.viewport().rect().contains(d.dimensions.badge.geometry())
                    assert tools.width() < d.view.viewport().width()
                    assert tools.height() < d.view.viewport().height() - tools.toggle_button.height()
                    badge_position = d.dimensions.badge.pos()
                    d.view.horizontalScrollBar().setValue(d.view.horizontalScrollBar().value() + 20)
                    assert d.dimensions.badge.pos() == badge_position
                    # Every furniture/symbol property variant remains reachable.
                    for kind, variants in (("desk", DESK_VARIANTS), ("symbol", SYMBOL_VARIANTS)):
                        dialog = ObjectAnnotationDialog(d.annotation, object_default(kind, 50))
                        dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
                        dialog.show()
                        app.processEvents()
                        for variant in variants:
                            dialog.variant_buttons[variant].click()
                            app.processEvents()
                            assert dialog.properties()["variant"] == variant
                        for label in dialog.findChildren(QLabel):
                            if not label.isVisible():
                                continue
                            if label.wordWrap():
                                assert label.height() + 3 >= label.heightForWidth(label.width()), (language, theme, scale, kind, label.text())
                            elif label.text():
                                assert label.fontMetrics().horizontalAdvance(label.text()) <= label.width() + 3, (language, theme, scale, kind, label.text(), label.size())
                        assert dialog.width() <= available.width() and dialog.height() <= available.height()
                        dialog.reject()
                        dialog.deleteLater()
                    key = f"{language}-{theme}-{scale}"
                    if language == "it" and scale in (100, 175):
                        d.view.viewport().grab().save(str(out / f"clearances-{key}.png"))
                        with patch.object(d.annotation, "configure", return_value=True):
                            tools.select_tool("annotation_select")
                        d.annotation.select(labels=(0, 1))
                        app.processEvents()
                        d.view.viewport().grab().save(str(out / f"text-selection-{key}.png"))
                    if language == "it" and theme == "light" and scale == 100:
                        d.store(rectangle_segments(160, 80, 540, 420, "#263238"), labels=[text], annotations=[item])
                        image = clean_plan_image(d.view, window.session.metadata)
                        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                        printer.setOutputFileName(str(out / "clean-plan-scale.pdf"))
                        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
                        printer.setPageMargins(QMarginsF(10, 10, 10, 10))
                        paint_plan_page(printer, image, window.get_px_per_meter(), "metric", window.tr)
                        pdf = QPdfDocument()
                        assert pdf.load(str(out / "clean-plan-scale.pdf")) == QPdfDocument.Error.None_
                        rendered = pdf.render(0, QSize(850, 1202))
                        paper = QImage(rendered.size(), QImage.Format.Format_RGB888)
                        paper.fill(Qt.GlobalColor.white)
                        painter = QPainter(paper)
                        painter.drawImage(0, 0, rendered)
                        painter.end()
                        paper.save(str(out / "printed-scale.png"))
                        pdf.close()
                    cases.append(dict(language=language, theme=theme, scale=scale, status="passed"))
                    window.session = None
                    window.analysis_view.timer.stop()
                    window.close()
                    window.deleteLater()
                    app.processEvents()
                    print("PASS " + key, flush=True)
        (out / "ui-results.json").write_text(json.dumps(dict(cases=cases, native_qt=True,
            physical_mouse=False, physical_printer=False), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
