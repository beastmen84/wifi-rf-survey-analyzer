"""Synthetic Qt checks for wall priority, scaled controls and shared-corner caps."""
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
    parser.add_argument('--output', type=Path, required=True)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    logging.disable(logging.CRITICAL)
    with tempfile.TemporaryDirectory(prefix='wall-priority-') as temp:
        os.environ['WIFI_HEATMAP_SETTINGS_FILE'] = str(Path(temp)/'settings.json')
        os.environ['WIFI_HEATMAP_AP_MEMORY_FILE'] = str(Path(temp)/'memory.json')
        from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtWidgets import QApplication
        from app_core.settings import save_ui_scale
        from qt_ui.qt_app import WifiHeatmapQtApp
        from qt_ui.qt_wall_sides import WallSidesDialog
        from survey.wall_sides import wall_sides
        from survey.wall_layout import plan_wall_layout
        from tests.test_blank_plan import create_survey
        from tests.test_wall_thickness import rectangle, state, BOUNDS
        from tests.test_wall_corner_caps import attached
        from survey.plan_faces import RegionPicker
        app = QApplication([])
        app.setQuitOnLastWindowClosed(False)
        cases = []
        for scale in (100,125,175):
            save_ui_scale(str(scale))
            owner = WifiHeatmapQtApp()
            owner.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
            create_survey(owner, width=18, height=12)
            owner.resize(1440,980)
            owner.show()
            drawing = owner.plan_tools.controller
            built = plan_wall_layout(state(rectangle(150,150,300,250)), range(4), (), 20, BOUNDS).state
            for line in built['segments']:
                line['wall'].update(material='reinforced_concrete', pattern='solid')
            built['segments'][1]['wall']['priority'] = True
            built['segments'][2]['wall'].update(width=5, material='drywall')
            drawing.store(built['segments'])
            before = drawing.snapshot()
            for language in ('en','it','fr','es'):
                owner.change_language(language)
                for theme in ('light','soft','dark','contrast'):
                    owner.change_theme(theme)
                    dialog = WallSidesDialog(owner, built, wall_sides(built, range(4)))
                    dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
                    dialog.show()
                    app.processEvents()
                    assert dialog.table.columnCount() == 4
                    assert dialog.table.horizontalHeaderItem(3).text() == owner.tr('wall_priority')
                    assert dialog.priority_checks[1].isChecked()
                    dialog.priority_checks[1].click()
                    dialog.priority_checks[2].click()
                    assert dialog.priorities[2] and not dialog.priorities[1]
                    assert dialog.candidate is not None and dialog.apply_button.isEnabled()
                    assert drawing.snapshot() == before
                    assert not dialog.table.horizontalScrollBar().isVisible()
                    for check in dialog.priority_checks:
                        point = check.mapTo(dialog, QPoint(0,0))
                        assert dialog.rect().contains(point) and dialog.rect().contains(point+QPoint(check.width()-1, check.height()-1))
                    assert dialog.rect().contains(dialog.apply_button.mapTo(dialog,QPoint(0,0)))
                    image = QImage(500,500,QImage.Format.Format_RGB32)
                    image.fill(0xffffffff)
                    painter = QPainter(image)
                    dialog.preview.scene().render(painter,QRectF(0,0,500,500),QRectF(0,0,500,500))
                    painter.end()
                    assert image.pixelColor(460,402).name() == '#e6e9f2'
                    if language == 'it' and theme in ('light','dark') and scale in (100,175):
                        dialog.grab().save(str(output/f'priority-{theme}-{scale}.png'))
                    available = dialog.screen().availableGeometry()
                    cases.append(dict(language=language,theme=theme,scale=scale,
                                      dialog_size=[dialog.width(),dialog.height()],
                                      available_size=[available.width(),available.height()],status='passed'))
                    dialog.reject()
                    dialog.deleteLater()
                    app.processEvents()
            drawing.store(attached())
            owner.plan_tools.set_open(True)
            owner.plan_tools.select_tool('select')
            app.processEvents()
            selected, curves = drawing.selection.pick_stroke(QPointF(390,410))
            assert len(drawing.segments()) == 8 and len(selected) == 2 and not curves
            assert len(RegionPicker(drawing.segments(),[]).records) == 2
            if scale == 125:
                owner.floorplan_view.set_zoom(2)
                owner.floorplan_view.centerOn(QPointF(390,400))
                app.processEvents()
                owner.grab().save(str(output/'joined-corner.png'))
            owner.session.dirty = False
            owner.analysis_view.timer.stop()
            owner.close()
            owner.deleteLater()
            app.processEvents()
        (output/'results.json').write_text(json.dumps(dict(cases=cases,native_qt=True,rf_scanning=False),indent=2),encoding='utf-8')
        print('PASS', len(cases), 'wall priority UI configurations')


if __name__ == '__main__':
    main()
