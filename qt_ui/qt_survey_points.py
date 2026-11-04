"""Survey point table and selection helpers for the Qt workspace."""

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox, QTableWidgetItem
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from maps.quality import (
    QUALITY_GOOD,
    QUALITY_LOW_CONFIDENCE,
    QUALITY_MISSING_RELEVANT,
    QUALITY_SPARSE_DATA,
    QUALITY_UNSTABLE_SIGNAL,
    QUALITY_EMPTY_SCAN,
    evaluate_point_quality,
)
from qt_ui.qt_floorplan import format_point_tooltip
from qt_ui.qt_capture_dialog import GuidedCaptureDialog
from survey.measurement_quality import assess_survey_measurements
from survey.measurement_presentation import measurement_text
from wifi.adapters import adapter_identity


class SurveyPointTableMixin:
    def current_selected_point(self):
        selected = self.points_table.selectedItems()
        if not selected:
            return None

        row = selected[0].row()
        item = self.points_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def select_point_in_table(self, point):
        point_id = str(point.get("point_id", ""))
        timestamp = point.get("timestamp")
        x = point.get("x")
        y = point.get("y")

        for row_index in range(self.points_table.rowCount()):
            item = self.points_table.item(row_index, 0)
            row_point = item.data(Qt.ItemDataRole.UserRole) if item else None
            if not row_point:
                continue

            same_point_id = point_id and str(row_point.get("point_id", "")) == point_id
            same_position = (
                row_point.get("timestamp") == timestamp
                and row_point.get("x") == x
                and row_point.get("y") == y
            )
            if same_point_id or same_position:
                self.points_table.selectRow(row_index)
                self.points_table.scrollToItem(item)
                return True

        return False

    def clear_point_selection(self):
        self.points_table.clearSelection()
        self.floorplan_view.clear_selected_point()
        self.update_point_action_state()

    def on_points_table_selection_changed(self):
        point = self.current_selected_point()
        if point:
            self.floorplan_view.select_point(point)
        else:
            self.floorplan_view.clear_selected_point()
        self.update_point_action_state()

    def update_point_action_state(self):
        has_point = bool(self.current_selected_point())
        has_any_point = bool(self.session and self.session.get_point_summaries())
        self.focus_point_button.setEnabled(has_point)
        self.rescan_point_button.setEnabled(has_point and not self.scan_in_progress)
        self.delete_selected_button.setEnabled(has_point)
        self.delete_last_button.setEnabled(has_any_point)
        self.measurement_detail_button.setEnabled(has_point and not self.scan_in_progress)
        point = self.current_selected_point()
        assessment = getattr(self, "measurements_by_point", {}).get(str(point.get("point_id", ""))) if point else None
        self.point_measurement_summary.setText(measurement_text(assessment, self.tr).replace("\n", "  ·  ") if assessment else "")
        self.point_measurement_summary.setVisible(assessment is not None)

    def show_selected_measurement_details(self):
        point = self.current_selected_point()
        if point is None or self.scan_in_progress:
            return
        assessment = self.measurements_by_point.get(str(point.get("point_id", "")))
        if assessment is None:
            return
        capture = next((entry.get("capture", {}) for entry in self.session.measurement_points()
                        if entry["point_id"] == point["point_id"]), {})
        adapter = self.session.capture_adapter()
        observed_ids = {str(row["adapter_id"]) for row in self.session.rows + self.session.raw_scan_rows
                        if str(row.get("point_id", "")) == str(point["point_id"]) and row.get("adapter_id")}
        actual_id = capture.get("adapter_id") or (next(iter(observed_ids)) if len(observed_ids) == 1 else "")
        if not actual_id:
            adapter = {"description": self.tr("measurement_unknown_receiver")}
        elif adapter_identity(actual_id) != adapter_identity(adapter.get("id")):
            adapter = {"id": actual_id}
        dialog = GuidedCaptureDialog(self, point["x"], point["y"], adapter, read_only=True)
        dialog.show_review(assessment, self.relevant_ssids)
        dialog.exec()
        dialog.deleteLater()

    def focus_selected_point(self):
        point = self.current_selected_point()
        if not point:
            QMessageBox.warning(self, self.tr("warning"), self.tr("select_point"))
            return

        self.floorplan_view.focus_on(point["x"], point["y"])

    def rescan_selected_point(self):
        if self.session is None:
            return

        point = self.current_selected_point()
        if not point:
            QMessageBox.warning(self, self.tr("warning"), self.tr("select_point"))
            return
        if self.scan_in_progress:
            return

        self.pending_rescan_point = dict(point)
        self.start_wifi_scan(point["x"], point["y"])

    def delete_selected_point(self):
        point = self.current_selected_point()
        if not point:
            QMessageBox.warning(self, self.tr("warning"), self.tr("select_point"))
            return

        self.delete_point(point)

    def delete_last_point(self):
        if self.session is None:
            return

        points = self.session.get_point_summaries()
        if not points:
            QMessageBox.warning(self, self.tr("warning"), self.tr("no_point_to_delete"))
            return

        point = points[-1]
        removed_rows = self.delete_point(point, refresh=False)
        self.refresh_session_labels()
        self.refresh_points_table()
        self.status.showMessage(
            self.tr("last_point_deleted", x=point["x"], y=point["y"], rows=removed_rows)
        )
        self.maybe_update_live_preview()

    def delete_point(self, point, refresh=True):
        if self.session is None:
            return 0

        removed_rows = self.session.delete_point(point["timestamp"], int(point["x"]), int(point["y"]), point.get("point_id"))
        if refresh:
            self.refresh_session_labels()
            self.refresh_points_table()
            self.status.showMessage(
                self.tr("point_deleted", x=point["x"], y=point["y"], rows=removed_rows)
            )
            self.maybe_update_live_preview()
        return removed_rows

    def refresh_points_table(self):
        self.points_table.setRowCount(0)
        if self.session is None:
            self.update_point_action_state()
            return

        summaries = list(reversed(self.session.get_point_summaries()))
        self.measurements_by_point = assess_survey_measurements(self.session.rows, self.session.raw_scan_rows,
            self.session.metadata, self.relevant_ssids)
        quality_by_point_id = evaluate_point_quality(
            self.session.rows,
            self.session.raw_scan_rows,
            relevant_ssids=self.relevant_ssids,
        )
        for point in summaries:
            quality = quality_by_point_id.get(point.get("point_id", ""), {})
            if point.get("status") == "empty":
                quality = {"status": QUALITY_EMPTY_SCAN}
                quality_by_point_id[point["point_id"]] = quality
            point["quality_label"] = self.format_point_quality(quality.get("status"))
            assessment = self.measurements_by_point.get(str(point.get("point_id", "")))
            point["measurement_summary"] = measurement_text(assessment, self.tr) if assessment else ""
        self.floorplan_view.set_points(summaries)
        self.floorplan_view.set_ap_groups(self.session.get_ap_groups())
        self.points_table.setRowCount(len(summaries))
        for row_index, point in enumerate(summaries):
            quality = quality_by_point_id.get(point.get("point_id", ""), {})
            assessment = self.measurements_by_point.get(str(point.get("point_id", "")))
            values = [
                str(len(summaries) - row_index),
                str(point.get("x", "")),
                str(point.get("y", "")),
                "—" if point.get("best_signal_dbm") is None else str(point["best_signal_dbm"]),
                self.tr("measurement_collection_" + assessment.collection) if assessment else "—",
                ", ".join(point.get("ssids", [])),
                str(point.get("row_count", "")),
                str(point.get("timestamp", "")),
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                if column_index == 5:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    item.setToolTip(value)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, point)
                if column_index == 4:
                    item.setToolTip(point.get("measurement_summary", ""))
                self.points_table.setItem(row_index, column_index, item)
        self.resize_points_table_columns()
        self.update_point_action_state()

    def format_point_quality(self, status):
        return {
            QUALITY_GOOD: self.tr("quality_good"),
            QUALITY_MISSING_RELEVANT: self.tr("quality_missing_relevant"),
            QUALITY_LOW_CONFIDENCE: self.tr("quality_low_confidence"),
            QUALITY_UNSTABLE_SIGNAL: self.tr("quality_unstable_signal"),
            QUALITY_SPARSE_DATA: self.tr("quality_sparse_data"),
            QUALITY_EMPTY_SCAN: self.tr("advisor_empty_scan_label"),
        }.get(status, "-")

    def format_survey_point_tooltip(self, point):
        return format_point_tooltip(point, self.tr, compact=True)

    def should_show_quality_tooltip(self, quality):
        breakdown = quality.get("breakdown", []) if quality else []
        if len(breakdown) > 1:
            return True
        if not breakdown:
            return False

        return breakdown[0].get("status") in {QUALITY_LOW_CONFIDENCE, QUALITY_UNSTABLE_SIGNAL}

    def build_quality_tooltip_text(self, quality):
        lines = [self.tr("quality_breakdown_title")]
        lines.append(f"{self.tr('quality')}: {self.format_point_quality(quality.get('status'))}")
        for item in quality.get("breakdown", []):
            lines.append(f"{item.get('ssid', '-')}: {self.format_quality_breakdown_item(item)}")
        return "\n".join(lines)

    def format_quality_breakdown_item(self, item):
        status = item.get("status")
        if status == QUALITY_GOOD:
            return self.tr("quality_good")
        if status == QUALITY_MISSING_RELEVANT:
            return self.tr("quality_missing_relevant")
        if status == QUALITY_LOW_CONFIDENCE:
            confidence = item.get("min_confidence")
            suffix = f" ({confidence:.2f})" if isinstance(confidence, float) else ""
            return f"{self.tr('quality_low_confidence')}{suffix}"
        if status == QUALITY_UNSTABLE_SIGNAL:
            range_db = item.get("range_db")
            suffix = f" ({range_db:.1f} dB)" if isinstance(range_db, float) else ""
            return f"{self.tr('quality_unstable_signal')}{suffix}"
        return self.format_point_quality(status)
