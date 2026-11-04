"""Live map offline HTML export workflow for the Qt workspace."""

from pathlib import Path

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QMessageBox
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from app_core.logging import log_exception
from exporting.live_html import MapExportError, build_live_html_output_path, generate_live_html_export
from qt_ui.qt_live_map import load_floorplan_image
from qt_ui.qt_windowing import get_centered_save_file_name


class LiveReportExportMixin:
    def ensure_saved_for_map_export(self):
        if self.session is None:
            return False

        if not self.session.csv_file:
            QMessageBox.information(
                self,
                self.tr("save_required_title"),
                self.tr("report_save_required"),
            )

        if self.session.dirty or not self.session.csv_file:
            saved = self.save_survey()
            if not saved:
                self.status.showMessage(self.tr("save_failed"))
            return saved

        return True

    def export_live_report(self):
        if self.session is None or self.scan_in_progress or self.live_rendering:
            return False

        if not self.can_render_live_preview():
            QMessageBox.warning(self, self.tr("warning"), self.tr("live_preview_empty"))
            return False

        if not self.ensure_saved_for_map_export():
            return False

        map_file = self.session.metadata.get("map_file", "")
        config = self.build_live_map_config()
        export_session, export_generation = self.session, self.live_generation
        output_file = self.choose_live_report_output_file(config)
        if not output_file:
            return False
        # The modal file dialog can process pending survey/options events.
        if (self.session is not export_session or self.live_generation != export_generation
                or self.build_live_map_config() != config):
            self.status.showMessage(self.tr("advisor_stale"))
            return False

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        result = None
        map_error = None
        unexpected_error = None
        try:
            bg_image = load_floorplan_image(map_file)
            result = generate_live_html_export(
                self.session.to_dataframe(),
                bg_image,
                self.session.csv_file,
                config,
                self.tr,
                translations=self.build_live_renderer_translations(),
                language=self.language,
                aliases=self.session.get_ap_aliases(),
                ap_groups=self.session.get_ap_groups(),
                px_per_meter=self.get_px_per_meter(),
                measurement_system=self.measurement_system,
                output_file=output_file,
                boundary_mask_image=self.current_boundary_mask_image(),
            )
        except MapExportError as exc:
            map_error = exc
        except Exception as exc:
            unexpected_error = exc
        finally:
            QApplication.restoreOverrideCursor()

        if map_error is not None:
            QMessageBox.warning(self, map_error.title, map_error.message)
            return False
        if unexpected_error is not None:
            log_exception("qt live HTML export failed", unexpected_error, logger_name="main")
            QMessageBox.critical(self, self.tr("error"), str(unexpected_error))
            return False

        QMessageBox.information(
            self,
            self.tr("report_exported"),
            self.format_map_export_files_message(result),
        )
        self.status.showMessage(self.tr("report_exported"))
        return True

    def choose_live_report_output_file(self, config):
        if self.session is None or not self.session.csv_file:
            return ""

        default_path = build_live_html_output_path(self.session.csv_file, config)
        output_file, _selected_filter = get_centered_save_file_name(
            self,
            self.tr("report_save_live"),
            default_path,
            self.tr("report_html_filter"),
        )
        if not output_file:
            return ""
        if Path(output_file).suffix.lower() != ".html":
            output_file = f"{output_file}.html"
        return output_file

    def format_map_export_files_message(self, result):
        return (
            self.tr("files_created", paths="\n".join(result.files))
            if len(result.files) > 1
            else self.tr("file_created", path=result.output_file)
        )
