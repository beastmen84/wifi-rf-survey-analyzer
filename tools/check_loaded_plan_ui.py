"""Native PNG/PDF annotation UI checks with synthetic plans and isolated settings."""
import argparse
import json
import logging
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
    logging.disable(logging.CRITICAL)
    with tempfile.TemporaryDirectory(prefix="wifi-loaded-ui-") as temporary:
        temp = Path(temporary)
        os.environ["WIFI_HEATMAP_SETTINGS_FILE"] = str(temp / "settings.json")
        os.environ["WIFI_HEATMAP_AP_MEMORY_FILE"] = str(temp / "memory.json")
        from PySide6.QtCore import QMarginsF, QRect, QSizeF, Qt
        from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPageSize, QPdfWriter, QPen
        from PySide6.QtWidgets import QApplication, QToolButton
        from app_core.settings import save_ui_scale
        from qt_ui.qt_app import WifiHeatmapQtApp
        from qt_ui.qt_theme import QT_THEMES
        from qt_ui.qt_plan_legend import PlanLegendDialog, export_legend_tables
        from survey.plan_layers import add_layer
        from tests.test_plan_source import load_options
        from tests.test_plan_objects import obj
        from tests.test_network_plan_symbols import symbol
        from tests.test_plan_text_fill import label
        app = QApplication([])
        app.setQuitOnLastWindowClosed(False)
        image = QImage(1000, 700, QImage.Format.Format_RGB32)
        image.fill(QColor("#faf8f3"))
        painter = QPainter(image)
        painter.setPen(QPen(QColor("#68737b"), 4))
        painter.drawRect(70, 65, 850, 555)
        painter.drawLine(600, 65, 600, 620)
        painter.drawLine(70, 390, 600, 390)
        painter.setFont(QFont("Segoe UI", 16))
        painter.setPen(QColor("#92999d"))
        for rect, text in ((QRect(100, 90, 450, 60), "OFFICE 01"),
                           (QRect(640, 90, 240, 60), "MEETING ROOM"),
                           (QRect(100, 420, 450, 60), "RECEPTION")):
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        png, pdf = temp / "source.png", temp / "source.pdf"
        image.save(str(png))
        writer = QPdfWriter(str(pdf))
        writer.setResolution(72)
        writer.setPageSize(QPageSize(QSizeF(1000, 700), QPageSize.Unit.Point))
        writer.setPageMargins(QMarginsF(0, 0, 0, 0))
        painter = QPainter(writer)
        painter.drawImage(QRect(0, 0, writer.width(), writer.height()), image)
        painter.end()
        del writer
        cases = []
        for source in (png, pdf):
            original = source.read_bytes()
            for scale in (100, 125, 175):
                save_ui_scale(str(scale))
                owner = WifiHeatmapQtApp()
                owner.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
                owner.resize(1440, 1000)
                with patch.object(owner, "choose_new_survey_options", return_value=load_options(source)):
                    assert owner.new_survey(from_start_page=True)
                assert not owner.plan_tools.toggle_button.isEnabled()
                factor = owner.floorplan_view.pixmap_item.pixmap().width() / 1000
                owner.session.metadata["px_per_meter"] = str(50 * factor)
                owner.refresh_session_labels()
                owner.show()
                app.processEvents()
                drawing, tools = owner.plan_tools.controller, owner.plan_tools
                drawing.change_layers(add_layer(drawing.layer_document(), "Network"))
                drawing.store([], labels=[dict(label(), x=740 * factor, y=200 * factor)], annotations=[
                    obj(cx=350 * factor, cy=250 * factor, width=140 * factor, height=80 * factor),
                    symbol(identity="socket", number=1, description="Network outlet", cx=760 * factor,
                           cy=360 * factor, width=40 * factor, height=40 * factor),
                    symbol("rack", identity="rack", cx=220 * factor, cy=510 * factor,
                           rack=dict(name="Rack A", switches=[dict(ports=["Uplink", "Desk 1", "", ""])]))])
                owner.layers_panel.set_open(True, save=False)
                for language in ("en", "it", "fr", "es"):
                    owner.change_language(language)
                    for theme in QT_THEMES:
                        owner.change_theme(theme)
                        tools.set_open(True)
                        for tool in (None, "annotation_select", "annotation_eraser", "text"):
                            tools.select_tool(tool)
                            app.processEvents()
                            tools.position_controls()
                            app.processEvents()
                            assert tools.open and tools.active_tool == tool
                            assert tools.parentWidget().rect().contains(tools.geometry())
                            assert tools.geometry().bottom() < tools.toggle_button.y()
                            assert not tools.structure_heading.isVisible()
                            for forbidden in (tools.rectangle_button, tools.line_button, tools.circle_button,
                                              tools.arc_button, tools.wall_button, tools.eraser_button,
                                              tools.select_button, tools.annotation_buttons["door"],
                                              tools.annotation_buttons["window"]):
                                assert not forbidden.isVisible()
                            for button in tools.findChildren(QToolButton):
                                if button.isVisible() and button.text():
                                    assert button.accessibleName() and not button.icon().isNull()
                                    assert button.fontMetrics().horizontalAdvance(button.text()) <= button.width() - owner.spx(8)
                        assert len(export_legend_tables(owner.session)) == 3
                        assert source.read_bytes() == original
                        key = f"{source.suffix[1:]}-{language}-{theme}-{scale}"
                        if source == png and language == "it" and theme in ("light", "dark") and scale in (125, 175):
                            tools.select_tool(None)
                            app.processEvents()
                            owner.grab().save(str(out / f"workspace-{key}.png"))
                            tools.grab().save(str(out / f"palette-{key}.png"))
                            dialog = PlanLegendDialog(owner)
                            dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
                            dialog.show()
                            app.processEvents()
                            dialog.grab().save(str(out / f"legend-{key}.png"))
                            dialog.reject()
                            dialog.deleteLater()
                        cases.append(dict(source=source.suffix[1:], language=language, theme=theme,
                                          scale=scale, effective_scale=owner.ui_scale, status="passed"))
                        print("PASS " + key, flush=True)
                owner.session = None
                owner.analysis_view.timer.stop()
                owner.close()
                owner.deleteLater()
                app.processEvents()
        (out / "ui-results.json").write_text(json.dumps(dict(cases=cases, native_qt=True,
            physical_mouse=False, source_files_unchanged=True, rf_scanning=False), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
