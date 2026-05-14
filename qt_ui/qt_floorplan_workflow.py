"""Floorplan loading, viewport zoom, and scale calibration workflow."""

import os

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QInputDialog, QMessageBox
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from qt_ui.qt_windowing import get_centered_open_file_name


class FloorplanWorkflowMixin:
    def load_plan(self):
        if self.session is None:
            self.new_survey()
            if self.session is None:
                return

        file_path, _selected_filter = get_centered_open_file_name(
            self,
            self.tr("select_plan_title"),
            "",
            self.tr("qt_plan_file_filter"),
        )
        if not file_path:
            return

        self.load_plan_file(file_path, save_metadata=True)

    def load_saved_plan(self):
        if self.session is None:
            return

        map_file = self.session.metadata.get("map_file", "")
        if not map_file:
            self.floorplan_view.clear_floorplan()
            self.live_view.clear()
            return

        if os.path.exists(map_file):
            self.load_plan_file(map_file, save_metadata=False)
            return

        QMessageBox.warning(
            self,
            self.tr("map_not_found_title"),
            self.tr("map_not_found", path=map_file),
        )

    def load_plan_file(self, file_path, save_metadata=False):
        if self.session is None:
            return

        try:
            self.floorplan_view.load_floorplan(file_path)
        except Exception as exc:
            QMessageBox.warning(
                self,
                self.tr("warning"),
                str(exc),
            )
            return

        if save_metadata:
            self.session.update_metadata({"map_file": os.path.abspath(file_path)})
            self.session.refresh_ap_groups_from_rows(update_memory=False)

        self.floorplan_view.set_points(self.session.get_point_summaries())
        self.floorplan_view.set_ap_groups(self.session.get_ap_groups())
        QTimer.singleShot(0, self.floorplan_view.fit_to_view)
        self.refresh_session_labels()
        point_count = len(self.session.get_point_summaries())
        if point_count:
            self.status.showMessage(
                self.tr("map_loaded_points", count=point_count, name=self.session_display_name())
            )
        else:
            self.status.showMessage(self.tr("map_loaded", name=self.session_display_name()))
        self.maybe_update_live_preview()

    def zoom_in(self):
        view = self.current_zoom_view()
        if view is None:
            return

        view.zoom_in()
        self.status.showMessage(self.tr("zoom", zoom=view.zoom_level))

    def zoom_out(self):
        view = self.current_zoom_view()
        if view is None:
            return

        view.zoom_out()
        self.status.showMessage(self.tr("zoom", zoom=view.zoom_level))

    def fit_floorplan(self):
        view = self.current_zoom_view()
        if view is None:
            return

        view.fit_to_view()
        self.status.showMessage(self.tr("zoom", zoom=view.zoom_level))

    def current_zoom_view(self):
        if self.tabs.currentIndex() == 1:
            return self.live_view if self.live_view.pixmap_item is not None else None

        return self.floorplan_view if self.floorplan_view.has_floorplan() else None

    def start_scale_calibration(self):
        if self.session is None:
            return

        if not self.floorplan_view.has_floorplan():
            QMessageBox.warning(self, self.tr("warning"), self.tr("load_plan_first"))
            return

        if self.has_calibrated_scale():
            self.status.showMessage(self.tr("calibrate_scale_already_set"))
            return

        if self.floorplan_view.start_scale_calibration_pick():
            self.tabs.setCurrentIndex(0)
            self.status.showMessage(self.tr("calibrate_scale_start"))

    def on_scale_calibration_first_point(self):
        self.status.showMessage(self.tr("calibrate_scale_second_point"))

    def finish_scale_calibration(self, pixel_distance):
        if self.session is None:
            self.floorplan_view.clear_scale_calibration_overlay()
            return

        if pixel_distance <= 0:
            self.floorplan_view.clear_scale_calibration_overlay()
            self.status.showMessage(self.tr("calibrate_scale_invalid"))
            return

        meters, accepted = QInputDialog.getDouble(
            self,
            self.tr("calibrate_scale_title"),
            self.tr("calibrate_scale_distance_prompt"),
            1.0,
            0.01,
            10000.0,
            2,
        )
        self.floorplan_view.clear_scale_calibration_overlay()
        if not accepted or meters <= 0:
            self.status.showMessage(self.tr("calibrate_scale_invalid"))
            return

        px_per_meter = float(pixel_distance) / float(meters)
        self.session.update_metadata({"px_per_meter": f"{px_per_meter:.6f}"})
        self.refresh_session_labels()
        self.status.showMessage(self.tr("calibrate_scale_saved", px_per_meter=px_per_meter))
        self.maybe_update_live_preview()

    def cancel_scale_calibration(self):
        self.status.showMessage(self.tr("calibrate_scale_cancelled"))

    def delete_scale_calibration(self):
        if self.session is None or not self.has_calibrated_scale():
            return

        response = QMessageBox.question(
            self,
            self.tr("delete_scale_title"),
            self.tr("delete_scale_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if response != QMessageBox.StandardButton.Yes:
            return

        self.session.metadata.pop("px_per_meter", None)
        self.session.dirty = True
        self.floorplan_view.clear_scale_calibration_overlay()
        self.refresh_session_labels()
        self.status.showMessage(self.tr("delete_scale_done"))
        self.maybe_update_live_preview()
