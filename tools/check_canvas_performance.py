"""Native large vector sheets with grid, patterned walls and free objects."""
import argparse
import json
import math
import os
from pathlib import Path
from statistics import median,quantiles
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',choices=('auto','software','opengl'),default='auto')
    parser.add_argument('--rooms',type=int,nargs='+',default=[25,100,400])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--overview',action='store_true',help='Fit the whole sheet so most objects are visible')
    args = parser.parse_args()
    os.environ['WIFI_HEATMAP_RENDERER'] = args.backend
    from PySide6.QtCore import Qt,QSize
    from PySide6.QtGui import QPixmap,QColor
    from PySide6.QtWidgets import QApplication,QGraphicsPixmapItem
    from qt_ui.qt_floorplan import FloorplanView
    from qt_ui.qt_clean_plan import VectorPlanSource
    from survey.plan_drawing import rectangle_segments
    from survey.wall_rendering import wall_item
    from survey.plan_objects import object_default
    from tools.canvas_probe import PaintCounter
    from PySide6.QtTest import QTest
    app = QApplication([])
    cases = []
    for count in args.rooms:
        if not 1 <= count <= 500:
            parser.error('--rooms must be between 1 and 500')
        side = math.ceil(math.sqrt(count))
        extent = 300+side*400
        lines,objects,faces = [],[],[]
        for i in range(count):
            x,y = 150+(i%side)*400,150+(i//side)*400
            lines.extend(dict(s,wall=dict(width=20,side=-1,material=('brick','reinforced_concrete','drywall')[i%3]))
                         for s in rectangle_segments(x,y,300,300,'#263238'))
            objects.extend(dict(object_default('desk',50),id=f'desk-{i}-{j}',cx=x+70+j*140,cy=y+150) for j in range(2))
            faces.append(((x,y),(x+300,y),(x+300,y+300),(x,y+300)))
        view = FloorplanView()
        view.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        view.resize(1440,980)
        view.setBackgroundBrush(QColor('white'))
        white = QPixmap(1,1)
        white.fill(Qt.GlobalColor.white)
        view.pixmap_item = QGraphicsPixmapItem(white)
        view.scene.addItem(view.pixmap_item)
        view.scene.setSceneRect(0,0,extent,extent)
        start = perf_counter()
        source = VectorPlanSource(QSize(extent,extent),lines,[],[],objects)
        for path,pen,brush in source._commands:
            view.scene.addItem(wall_item(path,pen,brush))
        source_ms = (perf_counter()-start)*1000
        view.set_grid(True,50,interval_m=1)
        view.set_grid_regions(faces)
        prepare = perf_counter()-start
        view.show()
        assert QTest.qWaitForWindowExposed(view,3000)
        if args.overview:
            view.fit_to_view()
        else:
            view.set_zoom(1.25)
        view.centerOn(extent/2,extent/2)
        app.processEvents()
        assert view.graphics_backend['backend'] != 'opengl' or view.viewport().isValid(), 'OpenGL viewport initialization failed'
        times = []
        counter = PaintCounter(view)
        for i in range(45):
            start = perf_counter()
            view.horizontalScrollBar().setValue(view.horizontalScrollBar().value()+(31 if i%2 else -23))
            view.verticalScrollBar().setValue(view.verticalScrollBar().value()+17)
            app.processEvents()
            if i >= 5:
                times.append((perf_counter()-start)*1000)
        cases.append(dict(rooms=count,wall_segments=len(lines),objects=len(objects),sheet_units=extent,
                          zoom=view.zoom_level,overview=args.overview,source_ms=source_ms,
                          paint_events=counter.frames,
                          dpr=view.devicePixelRatioF(),graphics_backend=view.graphics_backend,
                          prepare_ms=prepare*1000,pan_median_ms=median(times),pan_p95_ms=quantiles(times,n=20)[18]))
        print(json.dumps(cases[-1]),flush=True)
        assert counter.frames >= 40, 'Benchmark did not paint the requested pan frames'
        view.close()
        view.deleteLater()
        app.processEvents()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(dict(native_qt=True,cases=cases),indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
