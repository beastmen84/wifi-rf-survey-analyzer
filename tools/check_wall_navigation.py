"""Native pixel comparisons across display densities and fixed-wall placement UI."""
import argparse
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def pan_worker(output, density):
    os.environ['QT_SCREEN_SCALE_FACTORS'] = density
    os.environ['QT_SCALE_FACTOR'] = '1'
    from PySide6.QtWidgets import QApplication, QGraphicsItem
    from tests.test_wall_pan_rendering import material_view, fresh_difference
    app = QApplication([])
    cases = []
    baseline = None
    for geometry in ('rooms','rotated','curve'):
        for pattern in ('cross','dots','brick'):
            for zoom in (1,1.25,2.75):
                view, scene, items, center = material_view(pattern,geometry)
                view.show()
                view.scale(zoom,zoom)
                view.centerOn(*center)
                app.processEvents()
                view.viewport().grab()
                for dx,dy in ((111,-83),(-57,139),(243,175),(-333,-241),(47,33)):
                    view.horizontalScrollBar().setValue(view.horizontalScrollBar().value()+dx)
                    view.verticalScrollBar().setValue(view.verticalScrollBar().value()+dy)
                    app.processEvents()
                    view.viewport().grab()
                difference,before,after = fresh_difference(view,items,app)
                assert difference == 0, (density,geometry,pattern,zoom,difference)
                cases.append(dict(dpr=view.devicePixelRatioF(),geometry=geometry,pattern=pattern,zoom=zoom,different_components=difference))
                if geometry == 'rooms' and pattern == 'cross' and zoom == 1.25:
                    for item in items:
                        item.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
                    view.viewport().grab()
                    for dx,dy in ((111,-83),(-57,139),(243,175)):
                        view.horizontalScrollBar().setValue(view.horizontalScrollBar().value()+dx)
                        view.verticalScrollBar().setValue(view.verticalScrollBar().value()+dy)
                        app.processEvents()
                        view.viewport().grab()
                    baseline,before,after = fresh_difference(view,items,app)
                    if density == '1.5':
                        before.save(str(output/'cached-pan.png'))
                        after.save(str(output/'vector-pan.png'))
                view.close()
                view.deleteLater()
                app.processEvents()
    result = dict(requested_dpr=density,cases=cases,old_cache_different_components=baseline)
    (output/'pan-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def placement_ui(output):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtWidgets import QApplication
    from app_core.settings import save_ui_scale
    from qt_ui.qt_app import WifiHeatmapQtApp
    from qt_ui.qt_wall_sides import WallSidesDialog
    from survey.wall_sides import stage_structure
    from tests.test_blank_plan import create_survey
    from tests.test_fixed_wall_placement import host
    from tests.test_wall_thickness import state,rectangle
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    cases = []
    for scale in (100,125,175):
        save_ui_scale(str(scale))
        owner = WifiHeatmapQtApp()
        owner.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        create_survey(owner,width=18,height=12)
        owner.resize(1440,980)
        owner.show()
        drawing = owner.plan_tools.controller
        original = state([host(width=5,y=200)])
        drawing.store(original['segments'])
        before = drawing.snapshot()
        staged,sides,anchor = stage_structure(original,rectangle(250,200,200,200))
        for language in ('en','it','fr','es'):
            owner.change_language(language)
            for theme in ('light','soft','dark','contrast'):
                owner.change_theme(theme)
                dialog = WallSidesDialog(owner,staged,sides,anchor,placing=True,fixed_state=original)
                dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
                dialog.show()
                app.processEvents()
                row = next(i for i,s in enumerate(sides) if s.shared)
                dialog.table.selectRow(row)
                assert dialog.preview_shape(sides[row])['y1'] == 205
                dialog.spins[row].setValue(10/owner.get_px_per_meter())
                assert abs(dialog.preview_shape(sides[row])['y1']-210) < 1e-6
                assert dialog.candidate is not None and not dialog.apply_button.isEnabled()
                dialog.confirm_shared.setChecked(True)
                app.processEvents()
                assert dialog.apply_button.isEnabled() and drawing.snapshot() == before
                assert dialog.rect().contains(dialog.apply_button.mapTo(dialog,QPoint(0,0)))
                assert not dialog.table.horizontalScrollBar().isVisible()
                available = dialog.screen().availableGeometry()
                assert dialog.width() <= available.width() and dialog.height() <= available.height()
                if language == 'it' and theme in ('light','dark') and scale in (100,175):
                    dialog.grab().save(str(output/f'fixed-wall-{theme}-{scale}.png'))
                cases.append(dict(language=language,theme=theme,ui_scale=scale,new_reference_y=210,old_reference_y=200,status='passed'))
                dialog.reject()
                dialog.deleteLater()
                app.processEvents()
        owner.session.dirty = False
        owner.analysis_view.timer.stop()
        owner.close()
        owner.deleteLater()
        app.processEvents()
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--worker-dpr')
    parser.add_argument('--ui-only',action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    logging.disable(logging.CRITICAL)
    if args.worker_dpr:
        pan_worker(output,args.worker_dpr)
        return
    workers = []
    for density in (() if args.ui_only else ('1','1.25','1.5','2')):
        folder = output/f'dpr-{density}'
        subprocess.run([sys.executable,__file__,'--output',str(folder),'--worker-dpr',density],check=True)
        workers.append(json.loads((folder/'pan-results.json').read_text(encoding='utf-8')))
        print('PASS pan requested scale',density,'effective DPR',workers[-1]['cases'][0]['dpr'],flush=True)
    with tempfile.TemporaryDirectory(prefix='fixed-wall-ui-') as temp:
        os.environ['WIFI_HEATMAP_SETTINGS_FILE'] = str(Path(temp)/'settings.json')
        os.environ['WIFI_HEATMAP_AP_MEMORY_FILE'] = str(Path(temp)/'memory.json')
        cases = placement_ui(output)
    (output/'results.json').write_text(json.dumps(dict(pan=workers,placement_ui=cases,native_qt=True,rf_scanning=False),indent=2),encoding='utf-8')
    print('PASS',sum(len(w['cases']) for w in workers),'pan cases and',len(cases),'placement UI configurations')


if __name__ == '__main__':
    main()
