"""Survey hover should remain predictable at low zoom and after map changes."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF
from PySide6.QtGui import QHelpEvent, QPixmap
from PySide6.QtWidgets import QApplication

from qt_ui.qt_floorplan import FloorplanView, format_point_tooltip
from tests.test_advisor import qt_app
from translations.i18n import translate


def point(identity="one", x=800, y=400):
    return dict(point_id=identity, x=x, y=y, best_signal_dbm=-78,
        timestamp="2026-11-04T15:00:00", row_count=20,
        ssids=[f"Network {index:02d} <test>" for index in range(20)],
        measurement_summary="Acquisition reliability: Verified\nSignal stability: Stable in this capture\nObserved coverage: Weak signal observed")


@pytest.fixture
def view(qt_app):
    view = FloorplanView()
    view.resize(700, 500)
    pixmap = QPixmap(2000, 1000)
    pixmap.fill()
    view.pixmap_item = view.scene.addPixmap(pixmap)
    view.scene.setSceneRect(pixmap.rect())
    view.point_tooltip_formatter = lambda row: format_point_tooltip(row, compact=True)
    view.show()
    qt_app.processEvents()
    view.set_zoom(.2)
    view.centerOn(800, 400)
    yield view
    view.hide_point_tooltip()
    view.hide()
    view.deleteLater()
    qt_app.processEvents()


@pytest.mark.parametrize("language", ["en", "it", "fr", "es"])
def test_compact_hover_bounds_network_list_without_changing_evidence(language):
    value = point()
    before = deepcopy(value)
    tr = lambda key, **kw: translate(language, key, **kw)
    html = format_point_tooltip(value, tr, compact=True)
    assert "Network 03 &lt;test&gt;" in html and "Network 04" not in html
    assert tr("measurement_hover_more", count=16) in html
    assert "Verified" in html and "-78 dBm" in html and "width='360'" in html
    assert value == before


def test_zoomed_out_point_has_a_small_screen_pixel_hover_margin(view):
    value = point()
    view.set_points([value])
    position = view.mapFromScene(QPointF(800, 400)) + QPoint(6, 0)
    item = view.marker_items[0]
    assert not view.mapFromScene(item.sceneBoundingRect()).boundingRect().contains(position)
    assert view.point_for_hover(position) is item


def test_hover_selects_nearest_point_even_when_another_marker_is_selected(view):
    first, second = point(), point("two", x=820)
    view.set_points([first, second])
    view.select_point(first)
    position = view.mapFromScene(QPointF(820, 400))
    assert view.point_for_hover(position).data(0)["point_id"] == "two"


def test_ap_marker_tooltip_keeps_priority_over_a_survey_hover_margin(view):
    view.set_points([point()])
    ap = view.create_ap_marker(800, 400, {"group_id": "ap"}, "AP")
    view.scene.addItem(ap)
    position = view.mapFromScene(QPointF(800, 400))
    assert ap.toolTip()
    assert view.point_for_hover(position) is None


def test_tooltip_event_uses_point_area_and_closes_on_zoom_or_refresh(view):
    value = point()
    view.set_points([value])
    position = view.mapFromScene(QPointF(800, 400))
    event = QHelpEvent(QEvent.Type.ToolTip, position, view.viewport().mapToGlobal(position))
    with patch("qt_ui.qt_floorplan.QToolTip.showText") as show, patch("qt_ui.qt_floorplan.QToolTip.hideText") as hide:
        QApplication.sendEvent(view.viewport(), event)
        assert view.hover_point_key == ("id", "one")
        assert show.call_args.args[2] is view.viewport()
        assert show.call_args.args[3].contains(position)
        view.set_zoom(.3)
        assert view.hover_point_key is None
        hide.assert_called_once()
        view.hover_point_key = ("id", "one")
        view.set_points([point("replacement")])
        assert view.hover_point_key is None
        assert hide.call_count == 2


@pytest.mark.parametrize("change", ["leave", "scroll", "drawing"])
def test_hover_does_not_stay_on_screen_when_view_context_changes(view, change):
    view.set_points([point()])
    if change == "scroll":
        view.set_zoom(1)
        view.centerOn(800, 400)
    view.hover_point_key = ("id", "one")
    with patch("qt_ui.qt_floorplan.QToolTip.hideText") as hide:
        if change == "leave":
            QApplication.sendEvent(view.viewport(), QEvent(QEvent.Type.Leave))
        elif change == "scroll":
            view.horizontalScrollBar().setValue(view.horizontalScrollBar().value() + 1)
        else:
            view.boundaries_edit_active = True
            position = view.mapFromScene(QPointF(800, 400))
            event = QHelpEvent(QEvent.Type.ToolTip, position, view.viewport().mapToGlobal(position))
            with patch("qt_ui.qt_floorplan.QToolTip.showText") as show:
                QApplication.sendEvent(view.viewport(), event)
            show.assert_not_called()
        assert view.hover_point_key is None
        hide.assert_called_once()
