"""Reproducible source-only plan benchmarks with isolated settings and no RF scans."""
import argparse
import gc
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def measure(action, repeats):
    action()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        action()
        samples.append((time.perf_counter() - start) * 1000)
    ordered = sorted(samples)
    return dict(median_ms=statistics.median(samples), p95_ms=ordered[min(len(ordered) - 1, int(len(ordered) * .95))],
                max_ms=max(samples), samples=len(samples))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="wifi-plan-bench-") as temporary:
        os.environ["WIFI_HEATMAP_SETTINGS_FILE"] = str(Path(temporary) / "settings.json")
        os.environ["WIFI_HEATMAP_AP_MEMORY_FILE"] = str(Path(temporary) / "memory.json")
        from PySide6.QtCore import QCoreApplication, QEvent, QPointF, Qt
        from PySide6.QtWidgets import QApplication, QDialog
        from qt_ui.qt_app import WifiHeatmapQtApp
        from qt_ui.qt_text_editor import PlanTextDialog
        from survey.store import SurveySession
        from survey.plan_objects import object_default
        from survey.plan_curve_geometry import normalize_plan
        from survey.plan_clearances import ClearanceIndex
        from survey.plan_drawing import rectangle_segments
        from survey.plan_layers import read_layers, add_layer, active_layer
        from survey.plan_symbols import legend_tables
        from qt_ui.qt_legend_pages import legend_pages
        from tests.test_rectangle_design import move

        app = QApplication.instance() or QApplication([])
        window = WifiHeatmapQtApp()
        window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        window.session = SurveySession()
        window.measurement_system = "metric"
        window.load_default_floorplan(width_m=40, height_m=30)
        window.stack.setCurrentWidget(window.workspace_page)
        window.resize(1500, 1000)
        window.show()
        window.analysis_view.timer.stop()
        app.processEvents()
        window.plan_tools.set_open(True)
        drawing, view, tools = window.plan_tools.controller, window.floorplan_view, window.plan_tools
        results = dict(python=platform.python_version(), platform=platform.platform(), cases={})
        for count in (40, 200, 600):
            walls = [dict(x1=100, y1=20 + i * 1400 / count, x2=1900,
                          y2=20 + i * 1400 / count, color="#263238") for i in range(count)]
            objects = [dict(object_default("desk", 50), id=f"d{i}", cx=400 + i % 20 * 60,
                            cy=100 + i // 20 * 40, width=40, height=20) for i in range(count)]
            drawing.store(walls, annotations=objects)
            with patch.object(drawing.annotation, "configure", return_value=True):
                tools.select_tool("desk")
            drawing.annotation.templates["desk"] = object_default("desk", 50)
            positions = [view.mapFromScene(QPointF(650 + i % 8, 700 + i // 8)) for i in range(30)]
            cursor = iter(positions)
            def hover():
                nonlocal cursor
                try:
                    point = next(cursor)
                except StopIteration:
                    cursor = iter(positions)
                    point = next(cursor)
                move(view, point)
            case = {"desk_hover": measure(hover, 25),
                    "annotation_no_hit": measure(lambda: drawing.annotation.pick((20, 20)), 10)}
            template = dict(id="door", kind="door", variant="single", color="#334155", stroke=2, side=1, hinge=0)
            case["door_off_wall"] = measure(lambda: drawing.annotation.hosted((20, 750), 45, template), 3)
            case["normalize_orthogonal"] = measure(lambda: normalize_plan(walls, []), 3)
            room = rectangle_segments(100, 100, 600, 400, "#000000")
            distant = [dict(x1=1000 + i, y1=0, x2=1000 + i, y2=1400, color="#000000") for i in range(count - 4)]
            index = ClearanceIndex(room + distant)
            pose = dict(object_default("desk", 50), cx=350, cy=300)
            def clearances():
                pose["cx"] += .01  # Avoid the last-pose cache for this measurement.
                quotes = index.query(pose)
                assert len(quotes) == 2 and not any(q.overlap for q in quotes)
            case["clearance_open_room"] = measure(clearances, 25)
            results["cases"][str(count)] = case
            print(f"{count}: " + json.dumps(case), flush=True)
        results["layer_cases"] = {}
        for count in (40, 200, 600):
            document = read_layers({"_generated_floorplan": "1"})
            for number in range(1, 4):
                document = add_layer(document, f"Benchmark {number}")
            for number, layer in enumerate(document["layers"]):
                layer["drawing"]["segments"] = [dict(x1=100, y1=20 + i * 1400 / count,
                    x2=1900, y2=20 + i * 1400 / count, color="#263238") for i in range(number, count, 4)]
                layer["drawing"]["annotations"] = [dict(object_default("desk", 50), id=f"d{i}",
                    cx=400 + i % 20 * 60, cy=100 + i // 20 * 40, width=40, height=20)
                    for i in range(number, count, 4)]
            drawing.change_layers(document)
            with patch.object(drawing.annotation, "configure", return_value=True):
                tools.select_tool("desk")
            drawing.annotation.templates["desk"] = object_default("desk", 50)
            positions = [view.mapFromScene(QPointF(650 + i % 8, 700 + i // 8)) for i in range(30)]
            cursor = iter(positions)
            case = {"desk_hover": measure(hover, 25),
                    "cached_document_read": measure(drawing.layer_document, 100),
                    "four_layer_redraw": measure(drawing.redraw, 3)}
            assert len(drawing.layer_document()["layers"]) == 4
            assert active_layer(drawing.layer_document())["id"] == document["active"]
            results["layer_cases"][str(count)] = case
            print(f"4 layers/{count}: " + json.dumps(case), flush=True)
        results["numbered_symbol_cases"] = {}
        for count in (40, 200, 600):
            document = read_layers({"_generated_floorplan": "1"})
            for number in range(1, 4):
                document = add_layer(document, f"Symbols {number}")
            for number, layer in enumerate(document["layers"]):
                layer["drawing"]["annotations"] = [dict(object_default("symbol", 50, "square"),
                    id=f"s{i}", number=i+1, cx=250+i % 20*60, cy=100+i//20*40,
                    description=f"Network outlet {i+1}") for i in range(number, count, 4)]
            drawing.change_layers(document)
            with patch.object(drawing.annotation, "configure", return_value=True):
                tools.select_tool("symbol")
            drawing.annotation.templates["symbol"] = object_default("symbol", 50, "square")
            positions = [view.mapFromScene(QPointF(650+i % 8, 700+i//8)) for i in range(30)]
            cursor = iter(positions)
            factor = abs(view.transform().m11())
            def zoom_labels():
                view.scale(1.01, 1.01)
                drawing.update_symbol_numbers()
            tables = legend_tables(drawing.layer_document())
            case = {"symbol_hover": measure(hover, 25),
                    "zoom_number_labels": measure(zoom_labels, 10),
                    "legend_pagination": measure(lambda: legend_pages(tables, 780, 540, window.tr), 5)}
            view.scale(factor/abs(view.transform().m11()), factor/abs(view.transform().m11()))
            drawing.update_symbol_numbers()
            assert sum(len(table["rows"]) for table in tables) == count
            results["numbered_symbol_cases"][str(count)] = case
            print(f"Numbered/{count}: " + json.dumps(case), flush=True)
        before = len(window.findChildren(PlanTextDialog))
        with patch.object(PlanTextDialog, "exec", return_value=QDialog.DialogCode.Rejected):
            for _ in range(6):
                drawing.text.read_editor()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
        gc.collect()
        results["retained_text_dialogs_after_6_cancels"] = len(window.findChildren(PlanTextDialog)) - before
        results["settings_isolated"] = True
        results["physical_mouse_or_printer"] = False
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
        window.session = None
        window.close()
        window.deleteLater()
        app.processEvents()
        print("RESULT " + str(options.output), flush=True)


if __name__ == "__main__":
    main()
