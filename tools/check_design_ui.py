"""Render the native drawing UI across languages, themes and UI scales.

Uses isolated settings and a synthetic drawing, without Wi-Fi scans or user files.
"""
import argparse
import json
import logging
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    logging.disable(logging.CRITICAL)
    with tempfile.TemporaryDirectory(prefix="wifi-design-ui-") as temporary:
        os.environ["WIFI_HEATMAP_SETTINGS_FILE"] = str(Path(temporary) / "settings.json")
        os.environ["WIFI_HEATMAP_AP_MEMORY_FILE"] = str(Path(temporary) / "memory.json")
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication, QToolButton
        from app_core.settings import save_ui_scale
        from qt_ui.qt_app import WifiHeatmapQtApp
        from qt_ui.qt_theme import QT_THEMES
        from survey.plan_drawing import rectangle_segments
        from survey.plan_objects import object_default
        from survey.plan_label_rendering import build_label
        from tests.test_blank_plan import create_survey
        app = QApplication([])
        app.setQuitOnLastWindowClosed(False)
        cases = []
        for scale in (100, 125, 175):
            save_ui_scale(str(scale))
            window = WifiHeatmapQtApp()
            window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
            window.resize(1440, 900)
            create_survey(window)
            window.show()
            app.processEvents()
            tools = window.plan_tools
            tools.controller.store(
                rectangle_segments(100, 100, 400, 350, "#25313d")
                + rectangle_segments(500, 100, 300, 350, "#25313d"),
                labels=[build_label(dict(text="Ufficio", x=300, y=200, size=22,
                                         family="Segoe UI", color="#25313d",
                                         outline_color="#ffffff", outline_width=0))],
                annotations=[dict(object_default("desk", 50), id="desk1", cx=300,
                                  cy=320, width=120, height=60)])
            for language in ("en", "it", "fr", "es"):
                window.change_language(language)
                for theme in QT_THEMES:
                    window.change_theme(theme)
                    tools.set_open(True)
                    assert tools.available() and tools.open
                    for button in (window.fit_view_button, window.calibrate_button,
                                   window.grid_button, window.boundaries_button,
                                   window.settings_menu_button):
                        assert button.fontMetrics().horizontalAdvance(button.text()) <= button.width() - window.spx(8), (language, theme, scale, button.text())
                    for tool in (None, "rectangle", "line", "circle", "arc", "text",
                                 "eraser", "select", "annotation_eraser", "annotation_select"):
                        tools.select_tool(tool)
                        assert tools.active_tool == tool
                        app.processEvents()
                        tools.position_controls()
                        app.processEvents()
                        assert tools.parentWidget().rect().contains(tools.geometry()), (scale, language, theme, tool)
                        assert tools.geometry().bottom() < tools.toggle_button.y()
                        assert tools.note.height() >= tools.note.heightForWidth(tools.note.width())
                        for button in tools.findChildren(QToolButton):
                            assert not button.icon().isNull()
                            if button.text():
                                assert button.fontMetrics().horizontalAdvance(button.text()) <= button.width() - window.spx(8), (language, theme, scale, tool, button.text(), button.width())
                                assert button.accessibleName()
                    key = f"{language}-{theme}-{scale}"
                    cases.append(dict(language=language, theme=theme, scale=scale,
                                      effective_scale=window.ui_scale, status="passed",
                                      viewport=[tools.parentWidget().width(), tools.parentWidget().height()],
                                      palette=[tools.width(), tools.height()],
                                      scrollable=tools.scroll.verticalScrollBar().maximum() > 0))
                    if language == "it" and theme in ("light", "dark") and scale in (125, 175):
                        tools.select_tool("rectangle")
                        tools.scroll.verticalScrollBar().setValue(0)
                        app.processEvents()
                        tools.grab().save(str(out / f"palette-{key}.png"))
                        window.grab().save(str(out / f"workspace-{key}.png"))
                    print("PASS " + key, flush=True)
            # Also inspect the two downstream workspace screens in the default size.
            if scale == 125:
                window.change_language("it")
                window.change_theme("light")
                for index, name in ((1, "live-map"), (2, "recommendations")):
                    window.tabs.setCurrentIndex(index)
                    app.processEvents()
                    window.grab().save(str(out / f"{name}.png"))
            window.session = None
            window.analysis_view.timer.stop()
            window.close()
            window.deleteLater()
            app.processEvents()
        (out / "ui-results.json").write_text(json.dumps(dict(cases=cases,
            native_qt=True, physical_mouse=False, rf_scanning=False), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
