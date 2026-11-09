"""Plan origin is chosen once, safely, and survives old/new survey reopening."""
from copy import deepcopy
from unittest.mock import patch

from PIL import Image
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPdfWriter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QPushButton, QFileDialog

from app_core.constants import DEFAULT_FLOORPLAN_METADATA_KEY, GENERATED_FLOORPLAN_METADATA_KEY
from qt_ui.qt_floorplan import load_floorplan_pixmap
from qt_ui.qt_survey_setup import SurveySetupDialog
from survey.plan_mode import PLAN_MODE_KEY, is_drawn_plan
from tests.test_blank_plan import create_survey
from tests.test_capture_adapter import RECEIVER, qt_app, window, wait_until


def load_options(path, system="metric"):
    return dict(measurement_system=system, adapter=RECEIVER, plan_mode="load", plan_file=str(path))


def test_setup_switches_fields_and_requires_file_without_losing_draw_settings(window, qt_app, tmp_path):
    with patch("qt_ui.qt_survey_setup.list_wifi_adapters", return_value=[dict(RECEIVER, ready=True, connected=True)]):
        dialog = SurveySetupDialog(window)
        dialog.show()
        wait_until(qt_app, lambda: dialog.thread is None)
        assert dialog.options()["plan_mode"] == "draw" and dialog.ok_button.isEnabled()
        dialog.blank_width_spin.setValue(20)
        QTest.mouseClick(dialog.load_plan_button, Qt.MouseButton.LeftButton)
        assert dialog.blank_plan_group.isHidden() and dialog.plan_file_group.isVisible()
        assert not dialog.ok_button.isEnabled()
        dialog.accept()
        assert dialog.result() != QDialog.DialogCode.Accepted
        with patch("qt_ui.qt_survey_setup.get_centered_open_file_name", return_value=("", "")):
            dialog.browse_plan()
        assert not dialog.ok_button.isEnabled()
        path = tmp_path / "source.png"
        Image.new("RGB", (400, 300), "#abcdef").save(path)
        with patch("qt_ui.qt_survey_setup.get_centered_open_file_name", return_value=(str(path), "")):
            dialog.browse_plan()
        assert dialog.options() == load_options(path) and dialog.ok_button.isEnabled()
        QTest.mouseClick(dialog.draw_plan_button, Qt.MouseButton.LeftButton)
        assert dialog.options()["blank_plan"]["width_m"] == 20
        assert "plan_file" not in dialog.options()
        QTest.mouseClick(dialog.load_plan_button, Qt.MouseButton.LeftButton)
        assert dialog.plan_file_edit.text() == str(path)
        dialog.reject()
        dialog.deleteLater()


def test_legacy_receiver_selection_does_not_change_plan_origin(window, qt_app):
    with patch("qt_ui.qt_survey_setup.list_wifi_adapters", return_value=[dict(RECEIVER, ready=True, connected=True)]):
        dialog = SurveySetupDialog(window, adapter_only=True)
        wait_until(qt_app, lambda: dialog.thread is None)
        assert dialog.plan_source_group.isHidden() and dialog.blank_plan_group.isHidden()
        assert set(dialog.options()) == {"measurement_system", "adapter"}
        dialog.reject()
        dialog.deleteLater()


def test_nested_plan_picker_keeps_theme_and_cancel_keeps_selection(window, qt_app, tmp_path):
    from qt_ui.qt_theme import QT_THEMES
    window.change_theme("dark")
    with patch("qt_ui.qt_survey_setup.list_wifi_adapters", return_value=[dict(RECEIVER, ready=True, connected=True)]):
        dialog = SurveySetupDialog(window)
        wait_until(qt_app, lambda: dialog.thread is None)
        dialog.plan_file_edit.setText(str(tmp_path / "selected.png"))
        with patch("qt_ui.qt_windowing.QFileDialog.exec", return_value=QDialog.DialogCode.Rejected):
            dialog.browse_plan()
        picker = dialog.findChildren(QFileDialog)[0]
        assert QT_THEMES["dark"]["panel"] in picker.styleSheet()
        assert dialog.plan_file_edit.text() == str(tmp_path / "selected.png")
        qt_app.processEvents()
        dialog.reject()
        dialog.deleteLater()


@pytest.mark.parametrize("source", ["png", "pdf"])
def test_load_plan_initial_creation_needs_annotation_scale_and_keeps_manual_boundaries(window, tmp_path, source):
    path = tmp_path / ("source." + source)
    if source == "png":
        Image.new("RGB", (400, 300), "#abcdef").save(path)
    else:
        writer = QPdfWriter(str(path))
        writer.setResolution(72)
        painter = QPainter(writer)
        painter.fillRect(0, 0, writer.width(), writer.height(), QColor("#abcdef"))
        painter.end()
        del writer
    with (patch.object(window, "choose_new_survey_options", return_value=load_options(path)),
          patch("qt_ui.qt_session_workflow.load_floorplan_pixmap", wraps=load_floorplan_pixmap) as decode):
        assert window.new_survey(from_start_page=True)
    assert decode.call_count == 1
    assert window.session.metadata[PLAN_MODE_KEY] == "load"
    assert window.session.metadata["map_file"] == str(path)
    assert "px_per_meter" not in window.session.metadata and not window.session.dirty
    assert window.session.capture_adapter() == RECEIVER
    assert window.floorplan_view.has_floorplan()
    assert not window.plan_tools.toggle_button.isHidden() and not window.layers_panel.isHidden()
    assert not window.plan_tools.toggle_button.isEnabled()
    assert window.plan_tools.toggle_button.toolTip() == window.tr("loaded_plan_scale_hint")
    assert not window.legend_button.isHidden()
    assert not window.plan_tools.controller.editable()
    before = deepcopy(window.session.metadata)
    window.plan_tools.set_open(True)
    assert not window.plan_tools.open and window.session.metadata == before
    window.set_boundaries_mode_enabled(True, show_status=False)
    assert window.floorplan_view.boundaries_edit_active
    assert window.boundaries_fill_button.isHidden() and window.boundaries_auto_fill_button.isHidden()
    assert window.calibrate_button.isEnabled()
    assert window.print_plan_button.isEnabled() and window.save_plan_jpeg_button.isEnabled()
    assert not hasattr(window, "load_plan_button")
    assert not hasattr(window, "load_plan")
    assert not any(button.text() == window.tr("load_plan") for button in window.workspace_page.findChildren(QPushButton))


@pytest.mark.parametrize("failure", ["missing", "corrupt", "empty", "bad_draw_size"])
def test_plan_setup_failure_preserves_existing_survey_view_units_and_history(window, tmp_path, failure):
    create_survey(window)
    window.plan_tools.set_open(True)
    drawing = window.plan_tools.controller
    drawing.apply_edit([dict(x1=100, y1=100, x2=200, y2=100, color="#123456")])
    previous, pixmap = window.session, window.floorplan_view.pixmap_item
    before = deepcopy((previous.metadata, drawing.undo_stack)), window.measurement_system
    path = tmp_path / "broken.png"
    if failure == "corrupt":
        path.write_text("not an image", encoding="utf-8")
    options = load_options("" if failure == "empty" else path, "imperial")
    if failure == "bad_draw_size":
        options.update(plan_mode="draw", blank_plan=dict(width_m=0, height_m=20))
    with (patch.object(window, "confirm_new_survey_replaces_current", return_value=True),
          patch.object(window, "choose_new_survey_options", return_value=options),
          patch("qt_ui.qt_session_workflow.QMessageBox.warning") as warning,
          patch.object(window, "set_new_survey_measurement_system") as set_units):
        assert not window.new_survey()
    assert warning.call_count == 1
    set_units.assert_not_called()
    assert window.session is previous and window.floorplan_view.pixmap_item is pixmap
    assert (previous.metadata, drawing.undo_stack) == before[0]
    assert window.measurement_system == before[1] and window.plan_tools.open


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("mode", ["draw", "load"])
def test_source_and_calibration_survive_save_reopen_without_prompting(window, tmp_path, mode, legacy):
    if mode == "draw":
        create_survey(window)
    else:
        path = tmp_path / "original.png"
        Image.new("RGB", (400, 300), "#abcdef").save(path)
        with patch.object(window, "choose_new_survey_options", return_value=load_options(path)):
            assert window.new_survey(from_start_page=True)
        window.session.metadata["px_per_meter"] = "50"
    assert is_drawn_plan(window.session.metadata) == (mode == "draw")
    scale = window.session.metadata["px_per_meter"]
    if legacy:
        window.session.metadata.pop(PLAN_MODE_KEY)
    path = tmp_path / "roundtrip.csv"
    window.session.csv_file = str(path)
    assert window.save_survey()
    with patch.object(window, "choose_new_survey_options") as choose:
        assert window.open_survey(str(path))
    choose.assert_not_called()
    assert window.session.metadata["px_per_meter"] == scale
    assert is_drawn_plan(window.session.metadata) == (mode == "draw")
    assert not window.layers_panel.isHidden()
    assert not window.plan_tools.toggle_button.isHidden()
    if mode == "load":
        assert window.plan_tools.toggle_button.text() == window.tr("annotation_group")
        assert not path.with_suffix(".png").exists()
        assert window.floorplan_view.pixmap_item.pixmap().toImage().pixelColor(100, 100).name() == "#abcdef"


def test_explicit_load_origin_does_not_enable_editing_with_stale_generated_flags():
    assert not is_drawn_plan({PLAN_MODE_KEY: "load", GENERATED_FLOORPLAN_METADATA_KEY: "1"})
    assert is_drawn_plan({DEFAULT_FLOORPLAN_METADATA_KEY: "1"})


def test_failed_unit_preference_save_preserves_current_plan(window, tmp_path):
    create_survey(window)
    previous, pixmap = window.session, window.floorplan_view.pixmap_item
    before = deepcopy(previous.metadata)
    path = tmp_path / "valid.png"
    Image.new("RGB", (400, 300), "white").save(path)
    with (patch.object(window, "confirm_new_survey_replaces_current", return_value=True),
          patch.object(window, "choose_new_survey_options", return_value=load_options(path, "imperial")),
          patch("qt_ui.qt_session_workflow.save_measurement_system", return_value=False),
          patch("qt_ui.qt_session_workflow.QMessageBox.warning")):
        assert not window.new_survey()
    assert window.session is previous and previous.metadata == before
    assert window.floorplan_view.pixmap_item is pixmap and window.measurement_system == "metric"
