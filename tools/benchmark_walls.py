"""Source-only physical-wall workloads; no files, RF scans or device print jobs."""
import argparse
import json
from pathlib import Path
import sys
import time
import statistics

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def measure(function, repeats=3):
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        function()
        times.append((time.perf_counter()-start)*1000)
    return dict(median_ms=statistics.median(times), maximum_ms=max(times))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QRectF
    from survey.plan_drawing import rectangle_segments
    from survey.plan_curve_geometry import normalize_plan
    from survey.wall_layout import plan_wall_layout
    from survey.wall_geometry import wall_commands
    from survey.plan_clearances import ClearanceIndex
    from survey.plan_objects import object_default
    app = QApplication.instance() or QApplication([])
    results = {}
    for side in (1, 2, 4, 7, 10):
        lines = [line for y in range(side) for x in range(side)
                 for line in rectangle_segments(100+x*200, 100+y*200, 200, 200, "#263238")]
        lines, curves = normalize_plan(lines, [])
        state = dict(segments=lines, curves=curves, labels=[], annotations=[])
        bounds = QRectF(0, 0, 10000, 10000)
        def build():
            return plan_wall_layout(state, range(len(lines)), (), 10, bounds)
        result = build()
        thick = result.state["segments"]
        index = ClearanceIndex(thick)
        item = dict(object_default("desk", 50), cx=200, cy=200)
        def hover():
            item["cx"] += .01
            return index.query(item)
        case = dict(layout=measure(build), resize=measure(lambda: plan_wall_layout(result.state, range(len(thick)), (), 15, bounds)),
                    render_paths=measure(lambda: wall_commands(thick)), clearance_hover=measure(hover, 20))
        results[str(side*side)] = case
        print(side*side, json.dumps(case), flush=True)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(results, indent=2), encoding="utf8")
    app.processEvents()


if __name__ == "__main__":
    main()
