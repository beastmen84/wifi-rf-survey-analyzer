"""Pointer motion must not repeatedly rebuild unchanged guides or HUD layout."""
from copy import deepcopy
from unittest.mock import patch

from PySide6.QtCore import QPoint,QRectF

from survey.plan_snapping import SnapGuide
from tests.test_rectangle_design import editor
from tests.test_capture_adapter import window,qt_app


def test_unchanged_measurement_reuses_layout_but_font_and_text_changes_refresh_it(editor,qt_app):
    _owner,drawing = editor
    before = deepcopy(drawing.snapshot())
    drawing.show_measurement('4.00 × 3.00 m',QPoint(200,200))
    with patch.object(drawing.measurement,'adjustSize',wraps=drawing.measurement.adjustSize) as layout:
        for i in range(8):
            drawing.show_measurement('4.00 × 3.00 m',QPoint(200+i,200))
        assert layout.call_count == 0
        drawing.measurement.setStyleSheet(drawing.measurement.styleSheet()+'font-size:20pt;')
        qt_app.processEvents()
        drawing.position_measurement()
        assert layout.call_count == 1
        drawing.show_measurement('4.00 × 3.00 m\nAdditional alignment',QPoint(200,200))
        assert layout.call_count == 2
    assert drawing.view.viewport().rect().contains(drawing.measurement.geometry())
    assert drawing.snapshot() == before


def test_identical_snap_guides_keep_items_but_zoom_and_clear_invalidate_them(editor):
    _owner,drawing = editor
    guides = (SnapGuide('edge',(200,200),'x',(100,500)),)
    rect = QRectF(200,200,100,100)
    drawing.snap_guides = guides
    drawing.show_snap_guides(rect)
    previous = list(drawing.snap_items)
    for _ in range(8):
        drawing.snap_guides = guides
        drawing.show_snap_guides(rect)
        assert drawing.snap_items == previous
    drawing.view.set_zoom(2)
    drawing.snap_guides = guides
    drawing.show_snap_guides(rect)
    assert drawing.snap_items != previous
    drawing.clear_snap_guides()
    assert not drawing.snap_items and not drawing.snap_guides
