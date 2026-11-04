"""Survey hover should remain predictable at low zoom and after map changes."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QSize, Qt
from PySide6.QtGui import QHelpEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication

from qt_ui.qt_floorplan import FloorplanView, format_point_tooltip
from qt_ui.qt_point_hover import SurveyPointHover
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


@pytest.mark.parametrize("zoom", [.2, 1, 2.5])
def test_painted_black_border_is_included_without_an_early_activation_halo(view, zoom):
    value = point()
    view.set_points([value])
    view.select_point(value)
    view.set_zoom(zoom)
    view.centerOn(800, 400)
    item = view.marker_items[0]
    center = view.viewportTransform().map(QPointF(800, 400))
    radius = zoom * (7 + item.pen().widthF() / 2)
    assert view.point_for_hover(center + QPointF(radius - .1, 0)) is item
    assert view.point_for_hover(center + QPointF(radius + 1, 0)) is None


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
    with patch("qt_ui.qt_floorplan.QToolTip.showText") as native:
        QApplication.sendEvent(view.viewport(), event)
        assert view.hover_point_key == ("id", "one")
        popup = view.point_hover_popup
        assert popup.isVisible() and "Verified" in popup.label.text()
        assert popup.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        assert popup.windowFlags() & Qt.WindowType.WindowTransparentForInput
        native.assert_not_called()
        view.set_zoom(.3)
        assert view.hover_point_key is None and not popup.isVisible()
        view.hover_point_key = ("id", "one")
        view.set_points([point("replacement")])
        assert view.hover_point_key is None


def move_mouse(view, position):
    event = QMouseEvent(QEvent.Type.MouseMove, position,
        QPointF(view.viewport().mapToGlobal(position.toPoint())), Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(view.viewport(), event)


def test_slow_edge_crossing_shows_immediately_and_does_not_restart_or_expire(view, qt_app):
    value = point()
    view.set_points([value])
    view.select_point(value)
    view.set_zoom(1)
    view.centerOn(800, 400)
    center = view.viewportTransform().map(QPointF(800, 400))
    move_mouse(view, center + QPointF(-8.5, 0))
    popup = view.point_hover_popup
    assert popup is not None and popup.isVisible() and view.hover_point_key == ("id", "one")
    geometry = popup.geometry()
    with patch.object(popup, "present", wraps=popup.present) as present:
        for quarter in range(-33, 35):
            position = center + QPointF(quarter / 4, 0)
            move_mouse(view, position)
            qt_app.processEvents()
            assert popup.isVisible() and view.hover_point_key == ("id", "one")
            assert popup.geometry() == geometry
        # Qt's delayed tooltip event must not introduce a second popup/timer.
        event = QHelpEvent(QEvent.Type.ToolTip, center.toPoint(), view.viewport().mapToGlobal(center.toPoint()))
        QApplication.sendEvent(view.viewport(), event)
        present.assert_not_called()
    move_mouse(view, center + QPointF(10, 0))
    assert not popup.isVisible() and view.hover_point_key is None


def test_overlapping_points_keep_current_popup_until_its_outline_is_left(view):
    view.set_zoom(1)
    view.centerOn(800, 400)
    view.set_points([point(), point("two", x=812)])
    center = view.viewportTransform().map(QPointF(800, 400))
    move_mouse(view, center)
    popup = view.point_hover_popup
    move_mouse(view, center + QPointF(7, 0))
    assert view.hover_point_key == ("id", "one")
    move_mouse(view, center + QPointF(10, 0))
    assert view.hover_point_key == ("id", "two") and popup.isVisible()
    assert view.point_hover_popup is popup


@pytest.mark.parametrize("position", [QPoint(-1270, 10), QPoint(-20, 10), QPoint(-1270, 690), QPoint(-20, 690)])
def test_popup_placement_stays_on_its_monitor_and_clear_of_marker(position):
    screen = QRect(-1280, 0, 1280, 720)
    marker = QRect(position, QSize(12, 12))
    popup_size = QSize(385, 424)
    result = QRect(SurveyPointHover.position_for(marker, popup_size, screen), popup_size)
    assert screen.contains(result) and not result.intersects(marker)


@pytest.mark.parametrize("change", ["leave", "scroll", "drawing"])
def test_hover_does_not_stay_on_screen_when_view_context_changes(view, change):
    view.set_points([point()])
    if change == "scroll":
        view.set_zoom(1)
        view.centerOn(800, 400)
    view.hover_point_key = ("id", "one")
    with patch.object(view, "hide_point_tooltip", wraps=view.hide_point_tooltip) as hide:
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
