"""Measure layer commands on a disposable project copy; output counts/times only.

No scan, save, screenshot or original-project write. Timings include Qt event
processing after each command, not dialog wait time or physical input latency.
"""
import argparse
from copy import deepcopy
import json
import logging
import os
from pathlib import Path
from statistics import median
import sys
import tempfile
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from tools.check_drawing_performance import copy_project, digest  # noqa: E402


def benchmark(project,folder,repeats):
    from PySide6.QtCore import Qt, qVersion
    from PySide6.QtWidgets import QApplication
    from qt_ui.qt_app import WifiHeatmapQtApp
    from survey.plan_layers import add_layer, active_layer, empty_state, move_selection

    os.environ['WIFI_HEATMAP_SETTINGS_FILE'] = str(folder/'settings.json')
    os.environ['WIFI_HEATMAP_AP_MEMORY_FILE'] = str(folder/'ap-memory.json')
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    owner = WifiHeatmapQtApp()
    owner.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    owner.resize(1440,980)
    owner.show()
    try:
        assert owner.open_survey(str(project))
        drawing = owner.plan_tools.controller
        assert drawing.tools.structure_available(), 'A Draw plan is required'
        doc = deepcopy(drawing.layer_document())
        counts = {k:sum(len(layer['drawing'][k] or []) for layer in doc['layers'])
                  for k in ('segments','curves','labels','annotations')}
        if len(doc['layers']) == 1:
            original = deepcopy(active_layer(doc)['drawing'])
            doc['layers'][0]['drawing'] = empty_state()
            doc = add_layer(doc,'Benchmark structure')
            active_layer(doc)['drawing'] = original
        main = max(doc['layers'],key=lambda layer:sum(len(v or []) for v in layer['drawing'].values()))['id']
        names = {layer['name'].casefold() for layer in doc['layers']}
        number = 1
        name = 'Benchmark text 1'
        while name.casefold() in names or (name+' A').casefold() in names:
            number += 1
            name = f'Benchmark text {number}'
        doc = add_layer(doc,name)
        notes = doc['active']
        doc['active'] = main
        source = active_layer(doc)['drawing']
        active_layer(doc).update(visible=True,locked=False)
        assert source['labels'], 'At least one text label is required'
        doc = move_selection(doc,notes,dict(labels=range(len(source['labels']))))
        assert drawing.change_layers(doc)
        owner.layers_panel.set_open(True,save=False)
        app.processEvents()
        results = {}
        for action in ('activate','visibility','lock','rename','transfer'):
            times = []
            for _ in range(repeats):
                for flag in (True,False):
                    candidate = deepcopy(drawing.layer_document())
                    main_layer = next(layer for layer in candidate['layers'] if layer['id'] == main)
                    notes_layer = next(layer for layer in candidate['layers'] if layer['id'] == notes)
                    if action == 'activate':
                        candidate['active'] = main if flag else notes
                    elif action == 'visibility':
                        main_layer['visible'] = not flag
                    elif action == 'lock':
                        main_layer['locked'] = flag
                    elif action == 'rename':
                        notes_layer['name'] = name+' A' if flag else name
                    else:
                        source = notes_layer if flag else main_layer
                        candidate['active'] = source['id']
                        candidate = move_selection(candidate,main if flag else notes,
                                                   dict(labels=range(len(source['drawing']['labels']))))
                    start = perf_counter()
                    assert drawing.change_layers(candidate,history=action != 'activate')
                    app.processEvents()
                    times.append((perf_counter()-start)*1000)
            results[action] = dict(median_ms=median(times),samples_ms=times)
        return dict(counts=counts,repeats=repeats,python=sys.version.split()[0],qt=qVersion(),
                    dpr=owner.devicePixelRatioF(),actions=results)
    finally:
        owner.layers_panel.refresh_timer.stop()
        owner.analysis_view.timer.stop()
        if owner.session:
            owner.session.dirty = False
        owner.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--repeats',type=int,default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('repeats must be positive')
    logging.disable(logging.CRITICAL)
    with tempfile.TemporaryDirectory(prefix='wifi-layers-') as temp:
        folder = Path(temp)
        project,hashes = copy_project(args.project.resolve(),folder)
        try:
            result = benchmark(project,folder,args.repeats)
        finally:
            assert all(digest(path) == value for path,value in hashes.items()), 'Original project changed'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({a:round(t['median_ms'],1) for a,t in result['actions'].items()},indent=2))


if __name__ == '__main__':
    main()
