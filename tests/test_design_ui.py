"""Drawing palette reachability, cancellation and display-density regressions."""
from copy import deepcopy

import pytest
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtTest import QTest

from qt_ui.qt_plan_icons import plan_tool_icon
from qt_ui.qt_theme import QT_THEMES
from tests.test_rectangle_design import editor
from tests.test_capture_adapter import window, qt_app


def test_close_palette_cancels_pending_shape_without_changing_the_plan(editor, qt_app):
    app, drawing = editor
    tools = app.plan_tools
    original = deepcopy(app.session.metadata)
    tools.select_tool("rectangle")
    drawing.begin_placement(150, 100)
    QTest.mouseClick(tools.close_button, Qt.MouseButton.LeftButton)
    assert not tools.open and tools.active_tool is None
    assert drawing.pending_size is None
    assert not app.floorplan_view.design_mode_active
    assert app.session.metadata == original and not app.session.dirty
    assert not drawing.undo_stack


def test_short_viewport_keeps_close_and_tools_reachable_with_stable_geometry(editor, qt_app):
    app, _drawing = editor
    tools = app.plan_tools
    # Exercise the overlay's small-screen behavior independently of the
    # workspace's minimum size, which is governed by its other panels.
    app.floorplan_view.viewport().setFixedHeight(app.spx(290))
    tools.select_tool("select")
    for _ in range(4):
        tools.position_controls()
        qt_app.processEvents()
    initial = tools.geometry()
    assert tools.parentWidget().rect().contains(initial)
    assert tools.geometry().bottom() < tools.toggle_button.y()
    assert tools.close_button.isVisible()
    assert tools.scroll.verticalScrollBar().maximum() > 0
    for button in (tools.rectangle_button, tools.annotation_buttons["annotation_select"], tools.edit_text_button):
        tools.scroll.ensureWidgetVisible(button)
        qt_app.processEvents()
        center = button.mapTo(tools.scroll.viewport(), button.rect().center())
        assert tools.scroll.viewport().rect().contains(center)
    tools.position_controls()
    assert tools.geometry() == initial


def test_language_and_theme_changes_keep_active_tool_and_accessible_scope(editor, qt_app):
    app, _drawing = editor
    tools = app.plan_tools
    tools.select_tool("select")
    for language in ("en", "it", "fr", "es"):
        app.change_language(language)
        for theme in QT_THEMES:
            app.change_theme(theme)
            qt_app.processEvents()
            assert tools.active_tool == "select" and tools.select_button.isChecked()
            assert app.tr("design_caption_select") in tools.active_label.text()
            assert tools.select_button.accessibleName() == app.tr("selection_shared")
            assert tools.snap_button.accessibleName() == app.tr("blank_tool_snap")
            assert tools.annotation_buttons["annotation_select"].accessibleName() != tools.select_button.accessibleName()


def test_toolbar_wraps_without_truncating_view_controls(window, qt_app):
    from app_core.settings import save_ui_scale
    from qt_ui.qt_app import WifiHeatmapQtApp
    # A larger UI scale stresses the narrow-window layout.
    save_ui_scale("175")
    app = WifiHeatmapQtApp()
    try:
        app.change_language("it")
        app.resize(1440, 900)
        app.show_workspace_page()
        app.show()
        qt_app.processEvents()
        bar = app.app_bar
        assert bar.layout().hasHeightForWidth()
        project_section = app.project_section_label.parentWidget()
        analysis_section = app.analysis_section_label.parentWidget()
        assert analysis_section.y() > project_section.y()
        for button in (app.fit_view_button, app.calibrate_button, app.grid_button,
                       app.boundaries_button, app.settings_menu_button):
            assert button.fontMetrics().horizontalAdvance(button.text()) <= button.width() - app.spx(8)
            assert bar.rect().contains(button.mapTo(bar, button.rect().center()))
        app.resize(3000, 1100)
        qt_app.processEvents()
        assert not bar.layout()._wraps(bar.width())
        assert analysis_section.y() == project_section.y()
    finally:
        app.analysis_view.timer.stop()
        app.close()
        app.deleteLater()


@pytest.mark.parametrize("theme", QT_THEMES)
@pytest.mark.parametrize("ratio", (1.0, 1.5, 2.0))
def test_vector_icons_keep_density_and_distinct_interaction_states(qt_app, theme, ratio):
    icon = plan_tool_icon("rectangle", theme, 22, ratio)
    normal = icon.pixmap(QSize(22, 22), ratio, QIcon.Mode.Normal, QIcon.State.Off)
    checked = icon.pixmap(QSize(22, 22), ratio, QIcon.Mode.Normal, QIcon.State.On)
    disabled = icon.pixmap(QSize(22, 22), ratio, QIcon.Mode.Disabled, QIcon.State.Off)
    assert normal.width() >= 22 * ratio
    assert normal.devicePixelRatio() == pytest.approx(ratio)
    assert normal.toImage() != checked.toImage()
    assert normal.toImage() != disabled.toImage()


@pytest.mark.parametrize("theme", QT_THEMES)
def test_selected_caption_contrast_at_least_four_and_a_half(theme):
    def linear(value):
        value = value / 255
        return value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4
    color = QT_THEMES[theme]["action_bg"].lstrip("#")
    r, g, b = (linear(int(color[index:index + 2], 16)) for index in (0, 2, 4))
    luminance = .2126 * r + .7152 * g + .0722 * b
    assert 1.05 / (luminance + .05) >= 4.5
