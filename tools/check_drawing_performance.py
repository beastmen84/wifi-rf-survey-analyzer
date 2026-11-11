"""Measure native drawing interactions on a temporary copy of a saved Draw plan.

The JSON contains counts and timings only. No RF scan, save, screenshot or
original-project write is performed. Timings are diagnostic, not CI thresholds.
"""
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
from statistics import median
import sys
import tempfile
from time import perf_counter
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_project(project, folder):
    from survey.store import read_survey_metadata
    metadata = read_survey_metadata(project)
    sources = {project}
    replacements = {}
    for key in ('map_file', 'raw_data_file', 'boundaries_file'):
        value = metadata.get(key)
        if not value:
            continue
        adjacent = project.parent / Path(value).name
        source = adjacent if adjacent.is_file() else Path(value)
        if source.is_file():
            sources.add(source)
            replacements[key] = str(folder / source.name)
        elif key == 'map_file':
            raise FileNotFoundError('The saved floorplan image is missing')
    hashes = {source: digest(source) for source in sources}
    for source in sources:
        shutil.copy2(source, folder / source.name)
    copied = folder / project.name
    rows = copied.read_text(encoding='utf-8-sig').splitlines()
    for key, value in replacements.items():
        rows = ['# '+key+'='+value if row.startswith('# '+key+'=') else row for row in rows]
    copied.write_text('\n'.join(rows)+'\n', encoding='utf-8')
    return copied, hashes


def benchmark(project, folder, repeats, rectangle=None):
    from PySide6.QtCore import QPoint, QRectF, Qt
    from PySide6.QtWidgets import QApplication, QDialog
    from qt_ui.qt_app import WifiHeatmapQtApp
    from qt_ui.qt_wall_sides import WallSidesDialog
    from tests.test_floorplan_pan import hand_drag
    from tests.test_rectangle_design import move
    from tools.canvas_probe import PaintCounter
    from PySide6.QtTest import QTest

    os.environ['WIFI_HEATMAP_SETTINGS_FILE'] = str(folder / 'settings.json')
    os.environ['WIFI_HEATMAP_AP_MEMORY_FILE'] = str(folder / 'ap-memory.json')
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    owner = WifiHeatmapQtApp()
    owner.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    owner.resize(1440, 980)
    owner.show()
    assert QTest.qWaitForWindowExposed(owner,3000)
    samples = []
    counts = None
    counter = None
    try:
        for _ in range(repeats):
            if owner.session:
                owner.session.dirty = False
            start = perf_counter()
            assert owner.open_survey(str(project))
            result = {'open': perf_counter()-start}
            drawing = owner.plan_tools.controller
            assert drawing.tools.structure_available() and drawing.editable(), 'An editable Draw plan is required'
            view = drawing.view
            owner.plan_tools.set_open(True)
            view.set_zoom(2.5)
            sheet = view.scene.sceneRect()
            view.centerOn(sheet.center())
            app.processEvents()
            if counter is None:
                counter = PaintCounter(view)
            counts = dict(segments=len(drawing.segments() or []), curves=len(drawing.curves()),
                          labels=len(drawing.labels()), annotations=len(drawing.annotations()))
            if rectangle is None:
                rect = QRectF(sheet.right()-140, sheet.bottom()-120, 100, 80)
            else:
                rect = QRectF(*rectangle)
            for name in ('reads', 'hover', 'pan', 'pending', 'placement_cancel', 'placement_apply'):
                owner.plan_tools.select_tool(None if name == 'pan' else 'rectangle')
                if name == 'pending':
                    drawing.begin_placement(200, 150)
                app.processEvents()
                start = perf_counter()
                frames_before = counter.frames
                if name == 'reads':
                    for _i in range(5):
                        drawing.segments(), drawing.curves(), drawing.labels(), drawing.annotations()
                elif name == 'pan':
                    for i in range(8):
                        hand_drag(view, QPoint(800, 200), QPoint(23 if i % 2 else -31, 17))
                        app.processEvents()
                elif name.startswith('placement'):
                    # WallSidesDialog uses `result` for the proposed wall layout,
                    # so retrieve the native modal result through the base class.
                    def modal_result(dialog):
                        if name == 'placement_cancel':
                            return QDialog.DialogCode.Rejected
                        dialog.confirm_shared.setChecked(True)
                        dialog.try_accept()
                        return QDialog.result(dialog)
                    with patch.object(WallSidesDialog, 'exec', modal_result):
                        changed = drawing.commit(rect)
                    assert changed == (name == 'placement_apply'), 'Choose a free --rectangle inside the sheet'
                else:
                    for i in range(8):
                        move(view, QPoint(820+i*3, 300+i*2))
                        app.processEvents()
                app.processEvents()
                result[name] = perf_counter()-start
                if name == 'pan':
                    result['pan_paint_events'] = counter.frames-frames_before
                    assert result['pan_paint_events'] >= 8, 'Benchmark did not paint the requested pan frames'
                elif name == 'pending':
                    result['pending_paint_events'] = counter.frames-frames_before
                    assert result['pending_paint_events'] > 0, 'Benchmark did not paint the moving preview'
                drawing.cancel()
            drawing.undo()
            samples.append(result)
        return dict(counts=counts, repeats=repeats, dpr=owner.devicePixelRatioF(), zoom=2.5,
                    graphics_backend=owner.floorplan_view.graphics_backend,
                    gesture_count=8, read_bundle_count=5, samples_seconds=samples,
                    median_seconds={key: median(s[key] for s in samples) for key in samples[0] if not key.endswith('_paint_events')},
                    median_pan_paint_events=median(s['pan_paint_events'] for s in samples),
                    median_pending_paint_events=median(s['pending_paint_events'] for s in samples))
    finally:
        if owner.session:
            owner.session.dirty = False
        owner.analysis_view.timer.stop()
        owner.close()
        owner.deleteLater()
        app.processEvents()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--rectangle', type=float, nargs=4, metavar=('X', 'Y', 'WIDTH', 'HEIGHT'))
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    logging.disable(logging.CRITICAL)
    with tempfile.TemporaryDirectory(prefix='drawing-performance-') as temp:
        folder = Path(temp)
        project, hashes = copy_project(args.project.resolve(), folder)
        if args.output.resolve() in hashes:
            parser.error('--output must differ from the original project files')
        try:
            result = benchmark(project, folder, args.repeats, args.rectangle)
        finally:
            assert all(digest(source) == before for source, before in hashes.items()), 'Original project changed'
    result.update(native_qt=True, original_files_unchanged=True, rf_scanning=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result['median_seconds'], indent=2), flush=True)


if __name__ == '__main__':
    main()
