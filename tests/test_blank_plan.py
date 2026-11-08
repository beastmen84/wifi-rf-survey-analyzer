"""Canvas dimensions, physical scale and availability of the blank-plan tools."""
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest

from qt_ui.default_floorplan import (
    blank_floorplan_geometry, BLANK_PLAN_WIDTH_KEY, BLANK_PLAN_HEIGHT_KEY,
    BLANK_PLAN_MAX_PIXELS,
)
from qt_ui.qt_survey_setup import SurveySetupDialog
from tests.test_capture_adapter import window, qt_app, RECEIVER, wait_until


def create_survey(window, system="metric", width=18, height=12):
    options = {"measurement_system": system, "adapter": RECEIVER,
               "blank_plan": {"width_m": width, "height_m": height}}
    with (patch.object(window, "choose_new_survey_options", return_value=options),
          patch("qt_ui.qt_session_workflow.save_measurement_system", return_value=True)):
        assert window.new_survey(from_start_page=True)


@pytest.mark.parametrize("system,width,height", [
    ("metric", 10, 7.5), ("imperial", 30.48, 15.24),
    ("metric", 500, 320), ("imperial", 1, 500),
])
def test_geometry_has_one_physical_scale_and_bounded_raster(system, width, height):
    pixels_x, pixels_y, density = blank_floorplan_geometry(system, width, height)
    assert max(pixels_x, pixels_y) <= BLANK_PLAN_MAX_PIXELS
    assert abs(pixels_x - width * density) <= .5
    assert abs(pixels_y - height * density) <= .5


@pytest.mark.parametrize("width,height", [(0, 12), (float("nan"), 12),
    (12, float("inf")), (501, 12), (12, None), ("invalid", 12)])
def test_bad_dimensions_cannot_allocate_an_image(width, height):
    with pytest.raises(ValueError):
        blank_floorplan_geometry("metric", width, height)


def test_setup_converts_units_without_drift_or_changing_the_other_dimension(window, qt_app):
    with patch("qt_ui.qt_survey_setup.list_wifi_adapters", return_value=[dict(RECEIVER, ready=True, connected=True)]):
        dialog = SurveySetupDialog(window)
        wait_until(qt_app, lambda: dialog.thread is None)
        dialog.blank_width_spin.setValue(13.47)
        dialog.blank_height_spin.setValue(9.23)
        original = dialog.options()["blank_plan"]
        for _ in range(10):
            dialog.units_combo.setCurrentIndex(dialog.units_combo.findData("imperial"))
            assert dialog.blank_width_spin.suffix() == " ft"
            dialog.units_combo.setCurrentIndex(dialog.units_combo.findData("metric"))
        assert dialog.options()["blank_plan"] == original
        dialog.units_combo.setCurrentIndex(dialog.units_combo.findData("imperial"))
        dialog.blank_width_spin.setValue(50)
        dimensions = dialog.options()["blank_plan"]
        assert dimensions["width_m"] == pytest.approx(15.24)
        assert dimensions["height_m"] == original["height_m"]
        dialog.blank_width_spin.setValue(dialog.blank_width_spin.minimum())
        blank_floorplan_geometry("imperial", **dialog.options()["blank_plan"])
        dialog.reject()
        dialog.deleteLater()


def test_legacy_adapter_dialog_does_not_ask_for_a_new_canvas(window, qt_app):
    with patch("qt_ui.qt_survey_setup.list_wifi_adapters", return_value=[]):
        dialog = SurveySetupDialog(window, adapter_only=True)
        wait_until(qt_app, lambda: dialog.thread is None)
        assert dialog.blank_plan_group.isHidden()
        assert "blank_plan" not in dialog.options()
        dialog.reject()
        dialog.deleteLater()


@pytest.mark.parametrize("system,width,height", [("metric", 18, 12), ("imperial", 30.48, 15.24)])
def test_custom_sheet_survives_save_reopen_and_plan_replacement(window, qt_app, tmp_path, system, width, height):
    create_survey(window, system, width, height)
    density = float(window.session.metadata["px_per_meter"])
    size = window.floorplan_view.pixmap_item.pixmap().size()
    assert abs(size.width() - width * density) <= .5
    assert abs(size.height() - height * density) <= .5
    assert not window.session.dirty
    assert not window.plan_tools.toggle_button.isHidden()
    csv_file = tmp_path / "survey.csv"
    window.session.csv_file = str(csv_file)
    assert window.save_survey()
    with Image.open(tmp_path / "survey.png") as saved:
        assert saved.size == (size.width(), size.height())
    assert window.open_survey(str(csv_file))
    assert float(window.session.metadata[BLANK_PLAN_WIDTH_KEY]) == width
    assert float(window.session.metadata[BLANK_PLAN_HEIGHT_KEY]) == height
    assert float(window.session.metadata["px_per_meter"]) == density
    assert window.floorplan_view.pixmap_item.pixmap().size() == size
    assert not window.plan_tools.toggle_button.isHidden()
    window.plan_tools.set_open(True)
    external = tmp_path / "external.png"
    Image.new("RGB", (400, 300), "white").save(external)
    window.load_plan_file(str(external), save_metadata=True)
    assert window.plan_tools.toggle_button.isHidden() and not window.plan_tools.open
    assert BLANK_PLAN_WIDTH_KEY not in window.session.metadata
    assert BLANK_PLAN_HEIGHT_KEY not in window.session.metadata


def test_toolbar_states_color_cancel_and_boundaries_exclusion(window, qt_app):
    create_survey(window)
    tools = window.plan_tools
    tools.set_open(True)
    assert tools.open
    assert tools.rectangle_button.isEnabled()
    assert tools.eraser_button.isEnabled()
    assert all(not button.isEnabled() for button in
               (tools.undo_button, tools.redo_button))
    tools.snap_button.click()
    assert tools.snap_button.isChecked() and window.floorplan_view.grid_visible
    tools.select_tool('rectangle')
    with patch("qt_ui.qt_plan_colors.QColorDialog.getColor", return_value=QColor("#d84315")):
        tools.color_button.click()
    assert tools.stroke_color.name() == "#d84315"
    with patch("qt_ui.qt_plan_colors.QColorDialog.getColor", return_value=QColor()):
        tools.color_button.click()
    assert tools.stroke_color.name() == "#d84315"
    window.set_boundaries_mode_enabled(True, show_status=False)
    assert not tools.open
    tools.set_open(True)
    assert not window.floorplan_view.boundaries_edit_active
    window.scan_in_progress = True
    window.refresh_session_labels()
    assert not tools.open and not tools.toggle_button.isEnabled()
    window.scan_in_progress = False
    window.refresh_session_labels()
    assert tools.toggle_button.isEnabled()


def test_design_mode_blocks_survey_clicks_and_restores_capture_on_exit(window, qt_app):
    create_survey(window)
    window.resize(1400, 950)
    window.show()
    qt_app.processEvents()
    tools = window.plan_tools
    tools.set_open(True)
    qt_app.processEvents()
    assert tools.parentWidget().rect().contains(tools.geometry())
    assert tools.parentWidget().rect().contains(tools.toggle_button.geometry())
    view = window.floorplan_view
    view.surveyPointRequested.disconnect(window.create_point_from_floorplan)
    captures = []
    view.surveyPointRequested.connect(lambda x, y: captures.append((x, y)))
    with patch("qt_ui.qt_rectangle_design.RectangleSizeDialog.exec", return_value=0):
        QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=QPoint(view.viewport().width() // 2, 70))
    assert len(captures) == 0
    QTest.mouseClick(tools.note, Qt.MouseButton.RightButton)
    assert len(captures) == 0  # Toolbar background must not leak clicks to the map.
    assert tools.note.height() >= tools.note.heightForWidth(tools.note.width())
    size_before = tools.size()
    for _ in range(30):
        tools.position_controls()
    assert tools.size() == size_before
    tools.set_open(False)
    QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=QPoint(view.viewport().width() // 2, 70))
    assert len(captures) == 1
    tools.set_open(True)
    QTest.keyClick(window, Qt.Key.Key_Escape)
    assert not tools.open and not view.design_mode_active
    QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=QPoint(view.viewport().width() // 2, 70))
    assert len(captures) == 2
    tools.set_open(True)
    window.toggle_points_panel()
    qt_app.processEvents()
    points_top = tools.parentWidget().mapFromGlobal(window.points_overlay.mapToGlobal(QPoint())).y()
    assert tools.toggle_button.geometry().bottom() < points_top
    QTest.keyClick(window, Qt.Key.Key_Escape)
    assert not tools.open
    assert not view.design_mode_active
    window.hide()
