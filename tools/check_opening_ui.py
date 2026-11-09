"""Synthetic native Qt previews for physical openings and endpoint quotes."""
import argparse
import json
import logging
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    OUT=parser.parse_args().output.resolve()
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='opening-ui-') as temp:
        os.environ['WIFI_HEATMAP_SETTINGS_FILE']=str(Path(temp)/'settings.json')
        os.environ['WIFI_HEATMAP_AP_MEMORY_FILE']=str(Path(temp)/'memory.json')
        from pytest import approx
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        from app_core.settings import save_ui_scale
        from qt_ui.qt_app import WifiHeatmapQtApp
        from survey.wall_layout import plan_wall_layout
        from survey.plan_annotations import place_aperture
        from tests.test_wall_thickness import rectangle,state,BOUNDS
        from tests.test_blank_plan import create_survey
        from tests.test_plan_annotations import aperture,at,choose
        from tests.test_rectangle_design import move
        app=QApplication([])
        app.setQuitOnLastWindowClosed(False)
        cases=[]
        for scale in (100,125,175):
            save_ui_scale(str(scale))
            owner=WifiHeatmapQtApp()
            owner.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
            create_survey(owner,width=18,height=12)
            owner.resize(1440,980)
            owner.show()
            d=owner.plan_tools.controller
            original=state(rectangle(150,150,300,300)+rectangle(450,150,300,300))
            lines=plan_wall_layout(original,range(len(original['segments'])),(),20,BOUNDS).state['segments']
            for line in lines:
                line['wall']['material']='reinforced_concrete'
            door=place_aperture((460,300),50,lines,2,aperture(variant='frame'))
            assert door
            d.store(lines,annotations=[door])
            owner.plan_tools.set_open(True)
            owner.floorplan_view.fit_to_view()
            for language in ('en','it','fr','es'):
                owner.change_language(language)
                for theme in ('light','soft','dark','contrast'):
                    owner.change_theme(theme)
                    for kind in ('door','window'):
                        choose(owner,kind,aperture(kind,variant='frame',x1=0,y1=0,x2=50,y2=0))
                        d.snap_bypass=True
                        app.processEvents()
                        move(d.view,at(owner,140,185))
                        values=d.dimensions.values
                        assert d.annotation.pending and values and values['kind']=='aperture'
                        assert min(values['before_m'],values['after_m'])==approx(.2,abs=.025),values
                        assert owner.tr('segment_before') not in d.dimensions.badge.text()
                        assert owner.tr('segment_after') not in d.dimensions.badge.text()
                        assert d.dimensions.badge.text().count('<br>')==2
                        box=d.annotation.preview[0].path().boundingRect()
                        assert abs(box.width()-20)<1e-5 and abs(box.center().x()-140)<1e-5
                        assert d.view.viewport().rect().contains(d.dimensions.badge.geometry())
                        if language=='it' and theme in ('light','dark') and scale in (125,175):
                            owner.grab().save(str(OUT/f'{kind}-{theme}-{scale}.png'))
                        if language=='it' and theme=='light' and scale==125 and kind=='door':
                            from PySide6.QtCore import QPointF
                            d.view.set_zoom(3)
                            app.processEvents()
                            vp=d.view.viewport()
                            d.view.centerOn(QPointF(140-(vp.width()*.72-vp.width()/2)/3,185))
                            app.processEvents()
                            move(d.view,at(owner,140,185))
                            assert min(d.dimensions.values['before_m'],d.dimensions.values['after_m'])==approx(.2,abs=.005)
                            owner.grab().save(str(OUT/'corner-20cm.png'))
                            owner.plan_tools.select_tool(None)
                            d.view.centerOn(QPointF(460-(vp.width()*.72-vp.width()/2)/3,300))
                            app.processEvents()
                            owner.grab().save(str(OUT/'shared-frame.png'))
                            owner.floorplan_view.fit_to_view()
                        cases.append(dict(language=language,theme=theme,scale=scale,kind=kind,
                            nearest_gap_m=min(values['before_m'],values['after_m']),status='passed'))
            owner.session.dirty=False
            owner.analysis_view.timer.stop()
            owner.close()
            owner.deleteLater()
            app.processEvents()
        (OUT/'results.json').write_text(json.dumps(dict(cases=cases,native_qt=True,rf_scanning=False),indent=2),encoding='utf-8')
        print('PASS',len(cases),'opening UI configurations')


if __name__ == '__main__':
    main()
