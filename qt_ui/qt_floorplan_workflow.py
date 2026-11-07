"""Floorplan loading, viewport zoom, and scale calibration workflow."""

import os

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QInputDialog, QMessageBox, QMenu
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from app_core.constants import (
    BOUNDARIES_FILE_METADATA_KEY,
    DEFAULT_FLOORPLAN_METADATA_KEY,
    GENERATED_FLOORPLAN_METADATA_KEY,
    MEASUREMENT_SYSTEM_METADATA_KEY,
)
from app_core.units import display_units_to_meters, format_scale_density, meters_to_display_units, distance_unit_label
from app_core.survey_grid import GRID_SPACING_KEY, survey_grid_spacing, grid_input_decimals, normalize_grid_spacing
from qt_ui.default_floorplan import (
    default_floorplan_save_path,
    ensure_default_floorplan,
    write_default_floorplan,
    blank_floorplan_geometry, BLANK_PLAN_WIDTH_KEY, BLANK_PLAN_HEIGHT_KEY,
)
from qt_ui.qt_floorplan import (
    BOUNDARIES_BRUSH_SIZE_MAX_PX,
    BOUNDARIES_BRUSH_SIZE_MIN_PX,
    BOUNDARIES_BRUSH_SIZE_STEP_PX,
    format_grid_interval,
)
from qt_ui.qt_theme import QT_THEMES
from survey.store import build_boundaries_file_path
from survey.plan_drawing import PLAN_DRAWING_KEY, encode_drawing, drawing_geometry
from survey.plan_labels import PLAN_LABELS_KEY, drawing_labels, encode_labels
from survey.plan_annotations import PLAN_ANNOTATIONS_KEY, drawing_annotations, encode_annotations
from survey.plan_curves import PLAN_CURVES_KEY, encode_curves
from survey.plan_layers import PLAN_LAYERS_KEY, visible_layers, read_layers, write_layers
from survey.plan_mode import PLAN_MODE_KEY, DRAW_PLAN, LOAD_PLAN


class FloorplanWorkflowMixin:
    def load_default_floorplan(self, width_m=None, height_m=None, *, prepared=None):
        if self.session is None:
            return False

        try:
            width_px, height_px, density = blank_floorplan_geometry(self.measurement_system, width_m, height_m)
            if prepared is None:
                file_path = ensure_default_floorplan(width_px, height_px)
                self.floorplan_view.load_floorplan(str(file_path))
            else:
                file_path, pixmap = prepared
                self.floorplan_view.load_floorplan(str(file_path), pixmap=pixmap)
        except Exception as exc:
            QMessageBox.warning(
                self,
                self.tr("warning"),
                str(exc),
            )
            return False

        was_dirty = self.session.dirty
        self.session.metadata["map_file"] = os.path.abspath(file_path)
        self.session.metadata[MEASUREMENT_SYSTEM_METADATA_KEY] = self.measurement_system
        self.session.metadata[DEFAULT_FLOORPLAN_METADATA_KEY] = "1"
        self.session.metadata[PLAN_MODE_KEY] = DRAW_PLAN
        self.session.metadata["px_per_meter"] = f"{density:.12g}"
        self.session.metadata[BLANK_PLAN_WIDTH_KEY] = f"{width_m if width_m is not None else width_px / density:.12g}"
        self.session.metadata[BLANK_PLAN_HEIGHT_KEY] = f"{height_m if height_m is not None else height_px / density:.12g}"
        self.session.dirty = was_dirty
        self.floorplan_view.set_points(self.session.get_point_summaries())
        self.floorplan_view.set_ap_groups(self.session.get_ap_groups())
        self.set_floorplan_grid_enabled(True, show_status=False)
        QTimer.singleShot(0, self.floorplan_view.fit_to_view)
        return True

    def materialize_default_floorplan(self, csv_file, transaction=None):
        if self.session is None:
            return True

        is_default = self.session.metadata.get(DEFAULT_FLOORPLAN_METADATA_KEY) == "1"
        segments, curves = drawing_geometry(self.session.metadata)
        labels = drawing_labels(self.session.metadata)
        annotations = drawing_annotations(self.session.metadata)
        layered_generated = PLAN_LAYERS_KEY in self.session.metadata and (
            is_default or self.session.metadata.get(GENERATED_FLOORPLAN_METADATA_KEY) == "1")
        has_drawing = segments is not None or bool(labels) or bool(curves) or bool(annotations) or layered_generated
        if not is_default and not has_drawing:
            return True

        image_file = default_floorplan_save_path(csv_file)
        current_file = self.session.metadata.get("map_file", "")
        if image_file.exists() and (is_default or os.path.abspath(image_file) != os.path.abspath(current_file)):
            response = QMessageBox.question(
                self,
                self.tr("replace_default_floorplan_title"),
                self.tr("replace_default_floorplan", path=str(image_file)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if response != QMessageBox.StandardButton.Yes:
                return False

        pixmap = self.floorplan_view.pixmap_item.pixmap()
        write_default_floorplan(transaction.stage_file(image_file) if transaction else image_file,
                                pixmap.width(), pixmap.height(), segments=segments, labels=labels, curves=curves, annotations=annotations,
                                layers=visible_layers(self.session.metadata))
        if layered_generated:
            write_layers(self.session.metadata, read_layers(self.session.metadata))
        else:
            if has_drawing:
                self.session.metadata[PLAN_DRAWING_KEY] = encode_drawing(segments or [], curves)
            if labels or PLAN_LABELS_KEY in self.session.metadata:
                self.session.metadata[PLAN_LABELS_KEY] = encode_labels(labels or [])
            if curves or PLAN_CURVES_KEY in self.session.metadata:
                self.session.metadata[PLAN_CURVES_KEY] = encode_curves(curves)
            if annotations or PLAN_ANNOTATIONS_KEY in self.session.metadata:
                self.session.metadata[PLAN_ANNOTATIONS_KEY] = encode_annotations(annotations)
        self.session.metadata["map_file"] = os.path.abspath(image_file)
        self.session.metadata.pop(DEFAULT_FLOORPLAN_METADATA_KEY, None)
        self.session.metadata[GENERATED_FLOORPLAN_METADATA_KEY] = "1"
        return True

    def load_saved_plan(self):
        if self.session is None:
            return

        self.floorplan_view.clear_floorplan()
        self.live_view.clear()
        map_file = self.session.metadata.get("map_file", "")
        if not map_file:
            return

        if os.path.exists(map_file):
            self.load_plan_file(map_file, save_metadata=False)
            return

        QMessageBox.warning(
            self,
            self.tr("map_not_found_title"),
            self.tr("map_not_found", path=map_file),
        )

    def load_plan_file(self, file_path, save_metadata=False, *, prepared_pixmap=None):
        if self.session is None:
            return

        self.set_boundaries_mode_enabled(False, show_status=False)
        previous_generated_floorplan = self.current_generated_floorplan_file()
        force_grid_off = False
        try:
            self.floorplan_view.load_floorplan(file_path, pixmap=prepared_pixmap)
        except Exception as exc:
            QMessageBox.warning(
                self,
                self.tr("warning"),
                str(exc),
            )
            return

        if save_metadata:
            self.clear_saved_boundaries_metadata(mark_dirty=False)
            self.session.metadata.pop(BLANK_PLAN_WIDTH_KEY, None)
            self.session.metadata.pop(BLANK_PLAN_HEIGHT_KEY, None)
            self.session.metadata.pop(PLAN_DRAWING_KEY, None)
            self.session.metadata.pop(PLAN_LABELS_KEY, None)
            self.session.metadata.pop(PLAN_CURVES_KEY, None)
            self.session.metadata.pop(PLAN_ANNOTATIONS_KEY, None)
            self.session.metadata.pop(PLAN_LAYERS_KEY, None)
            was_default_floorplan = (
                self.session.metadata.pop(DEFAULT_FLOORPLAN_METADATA_KEY, None) is not None
            )
            was_generated_floorplan = (
                was_default_floorplan
                or self.session.metadata.pop(GENERATED_FLOORPLAN_METADATA_KEY, None) is not None
            )
            self.session.update_metadata({"map_file": os.path.abspath(file_path)})
            self.session.metadata[PLAN_MODE_KEY] = LOAD_PLAN
            if was_generated_floorplan:
                self.session.metadata.pop("px_per_meter", None)
                self.session.dirty = True
                force_grid_off = True
                if previous_generated_floorplan:
                    self.mark_generated_floorplan_for_delete(previous_generated_floorplan)
            self.session.refresh_ap_groups_from_rows(update_memory=False)

        self.floorplan_view.set_points(self.session.get_point_summaries())
        self.floorplan_view.set_ap_groups(self.session.get_ap_groups())
        if not save_metadata:
            self.load_saved_boundaries_mask()
        QTimer.singleShot(0, self.floorplan_view.fit_to_view)
        self.refresh_session_labels()
        point_count = len(self.session.get_point_summaries())
        if point_count:
            self.status.showMessage(
                self.tr("map_loaded_points", count=point_count, name=self.session_display_name())
            )
        else:
            self.status.showMessage(self.tr("map_loaded", name=self.session_display_name()))
        if force_grid_off:
            self.set_floorplan_grid_enabled(False, show_status=False)
        else:
            self.sync_floorplan_grid_for_session()
        self.maybe_update_live_preview()

    def current_boundaries_file(self):
        if self.session is None or not self.session.csv_file:
            return ""

        boundaries_file = str(self.session.metadata.get(BOUNDARIES_FILE_METADATA_KEY, "")).strip()
        if not boundaries_file:
            return ""

        return os.path.abspath(build_boundaries_file_path(self.session.csv_file, self.session.metadata))

    def load_saved_boundaries_mask(self):
        if self.session is None:
            return False

        boundaries_file = self.current_boundaries_file()
        if not boundaries_file or not os.path.exists(boundaries_file):
            self.floorplan_view.reset_boundaries_mask(emit_signal=False)
            return False

        loaded = self.floorplan_view.load_boundaries_mask(boundaries_file, emit_signal=False)
        self.update_boundaries_controls_state()
        self.refresh_live_controls()
        return loaded

    def has_manual_boundaries_mask(self):
        return bool(
            self.floorplan_view.has_floorplan()
            and self.floorplan_view.has_boundaries_mask()
        )

    def persist_boundaries_mask(self, csv_file, transaction=None):
        if self.session is None:
            return True

        previous_file = self.current_boundaries_file()
        if self.floorplan_view.has_boundaries_mask():
            boundaries_file = build_boundaries_file_path(csv_file)
            output_file = transaction.stage_file(boundaries_file) if transaction else boundaries_file
            if not self.floorplan_view.save_boundaries_mask(str(output_file)):
                raise ValueError(self.tr("boundaries_save_failed", path=boundaries_file))
            self.session.metadata[BOUNDARIES_FILE_METADATA_KEY] = os.path.basename(boundaries_file)
            if previous_file and os.path.abspath(previous_file) != os.path.abspath(boundaries_file):
                self.mark_boundaries_file_for_delete(previous_file)
            return True

        self.clear_saved_boundaries_metadata(mark_dirty=False)
        if previous_file:
            self.mark_boundaries_file_for_delete(previous_file)
        return True

    def clear_saved_boundaries_metadata(self, mark_dirty=True):
        if self.session is None:
            return

        previous_file = self.current_boundaries_file()
        removed = self.session.metadata.pop(BOUNDARIES_FILE_METADATA_KEY, None) is not None
        if previous_file:
            self.mark_boundaries_file_for_delete(previous_file)
        if removed and mark_dirty:
            self.session.dirty = True

    def mark_boundaries_file_for_delete(self, file_path):
        if not self.is_deletable_boundaries_file(file_path):
            return

        pending = getattr(self, "boundaries_files_pending_delete", set())
        pending.add(os.path.abspath(file_path))
        self.boundaries_files_pending_delete = pending

    def is_deletable_boundaries_file(self, file_path):
        path = os.path.abspath(file_path)
        return path.lower().endswith(".boundaries.png")

    def cleanup_removed_boundaries_files(self):
        pending = set(getattr(self, "boundaries_files_pending_delete", set()))
        if not pending or self.session is None:
            return

        current_file = self.current_boundaries_file()
        current_file = os.path.abspath(current_file) if current_file else ""
        kept = set()
        failed = []
        for file_path in pending:
            if not file_path or file_path == current_file:
                continue
            if not self.is_deletable_boundaries_file(file_path):
                continue

            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                kept.add(file_path)
                failed.append(file_path)

        self.boundaries_files_pending_delete = kept
        if failed:
            self.status.showMessage(self.tr("boundaries_cleanup_failed", path=failed[0]))

    def current_generated_floorplan_file(self):
        if self.session is None:
            return ""

        if self.session.metadata.get(GENERATED_FLOORPLAN_METADATA_KEY) != "1":
            return ""

        map_file = self.session.metadata.get("map_file", "")
        if not map_file:
            return ""

        return os.path.abspath(map_file)

    def mark_generated_floorplan_for_delete(self, file_path):
        path = os.path.abspath(file_path)
        if not self.is_deletable_generated_floorplan(path):
            return

        pending = getattr(self, "generated_floorplans_pending_delete", set())
        pending.add(path)
        self.generated_floorplans_pending_delete = pending

    def is_deletable_generated_floorplan(self, file_path):
        if self.session is None or not self.session.csv_file:
            return False

        expected_path = os.path.abspath(default_floorplan_save_path(self.session.csv_file))
        return os.path.abspath(file_path) == expected_path

    def cleanup_replaced_generated_floorplans(self):
        pending = set(getattr(self, "generated_floorplans_pending_delete", set()))
        if not pending or self.session is None:
            return

        current_map_file = os.path.abspath(self.session.metadata.get("map_file", ""))
        kept = set()
        failed = []
        for file_path in pending:
            if not file_path or file_path == current_map_file:
                continue
            if not self.is_deletable_generated_floorplan(file_path):
                continue

            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                kept.add(file_path)
                failed.append(file_path)

        self.generated_floorplans_pending_delete = kept
        if failed:
            self.status.showMessage(self.tr("generated_floorplan_cleanup_failed", path=failed[0]))

    def floorplan_grid_color(self):
        return QT_THEMES.get(self.theme, QT_THEMES["light"])["metric_info"]

    def toggle_floorplan_grid(self):
        if self.session is None or not self.has_calibrated_scale():
            return

        self.set_boundaries_mode_enabled(False, show_status=False)
        self.set_floorplan_grid_enabled(
            not self.floorplan_view.grid_visible,
            show_status=True,
        )

    def set_floorplan_grid_enabled(self, enabled, show_status=True):
        px_per_meter = self.get_px_per_meter()
        enabled = bool(enabled and px_per_meter and self.floorplan_view.has_floorplan())
        try:
            interval = survey_grid_spacing(self.session.metadata) if self.session else None
        except (ValueError, TypeError):
            interval = None
            self.status.showMessage(self.tr("grid_invalid_spacing"))
        self.floorplan_view.set_grid(
            enabled,
            px_per_meter,
            self.measurement_system,
            self.floorplan_grid_color(),
            self.tr("grid_scale_label", interval=format_grid_interval(px_per_meter, self.measurement_system, interval))
            if enabled
            else "",
            self.ui_scale,
            interval_m=interval,
        )
        self.update_floorplan_grid_button_state()
        if hasattr(self, "plan_tools"):
            if not enabled:
                self.plan_tools.snap_button.setChecked(False)
            self.plan_tools.controller.refresh_snap()
        if show_status:
            self.status.showMessage(
                self.tr("grid_enabled") if enabled else self.tr("grid_disabled")
            )

    def sync_floorplan_grid_for_session(self):
        if self.session is None:
            self.set_floorplan_grid_enabled(False, show_status=False)
            return

        default_grid = (
            self.session.metadata.get(DEFAULT_FLOORPLAN_METADATA_KEY) == "1"
            or self.session.metadata.get(GENERATED_FLOORPLAN_METADATA_KEY) == "1"
        )
        current_visible = self.floorplan_view.grid_visible
        self.set_floorplan_grid_enabled(default_grid or current_visible, show_status=False)

    def update_floorplan_grid_button_state(self):
        if not hasattr(self, "grid_button"):
            return

        can_show_grid = (
            self.session is not None
            and self.floorplan_view.has_floorplan()
            and self.has_calibrated_scale()
            and self.tabs.currentIndex() == 0
            and not self.scan_in_progress
        )
        self.grid_button.setEnabled(can_show_grid)
        self.grid_button.setToolTip(self.tr("grid_options_hint"))
        self.grid_button.blockSignals(True)
        self.grid_button.setChecked(bool(can_show_grid and self.floorplan_view.grid_visible))
        self.grid_button.blockSignals(False)

    def show_grid_options(self, position):
        if not self.grid_button.isEnabled():
            return
        menu = QMenu(self)
        menu.setObjectName("gridOptionsMenu")
        palette = QT_THEMES[self.theme]
        menu.setStyleSheet(f"""
            QMenu#gridOptionsMenu {{
                background: {palette['panel']}; color: {palette['text']};
                border: 1px solid {palette['border']}; border-radius: {self.spx(5)}px;
                padding: {self.spx(4)}px;
            }}
            QMenu#gridOptionsMenu::item {{
                padding: {self.spx(7)}px {self.spx(12)}px;
                border-radius: {self.spx(3)}px;
            }}
            QMenu#gridOptionsMenu::item:selected {{
                background: {palette['button_hover']};
            }}
        """)
        action = menu.addAction(self.tr("grid_size_action"))
        action.triggered.connect(self.choose_grid_size)
        menu.exec(self.grid_button.mapToGlobal(position))
        menu.deleteLater()

    def choose_grid_size(self):
        if self.session is None or not self.grid_button.isEnabled():
            return False
        session = self.session
        pixmap = self.floorplan_view.pixmap_item
        current = self.floorplan_view.grid_interval_m
        if current is None:
            from qt_ui.qt_floorplan import choose_grid_interval_meters
            current = choose_grid_interval_meters(self.get_px_per_meter(), self.measurement_system)
        decimals = grid_input_decimals(self.measurement_system)
        self.grid_dialog_open = True
        try:
            value, accepted = QInputDialog.getDouble(self, self.tr("grid_size_action"), self.tr("grid_size_prompt", unit=distance_unit_label(self.measurement_system)),
                meters_to_display_units(current, self.measurement_system), 1 if decimals == 0 else .1,
                10000, decimals, step=1 if decimals == 0 else .1)
        finally:
            self.grid_dialog_open = False
        if not accepted or self.session is not session or self.floorplan_view.pixmap_item is not pixmap:
            return False
        spacing = normalize_grid_spacing(display_units_to_meters(value, self.measurement_system), self.measurement_system)
        encoded = f"{spacing:.12g}"
        if self.session.metadata.get(GRID_SPACING_KEY) == encoded:
            return False
        self.session.metadata[GRID_SPACING_KEY] = encoded
        self.session.dirty = True
        self.set_floorplan_grid_enabled(self.floorplan_view.grid_visible, show_status=False)
        self.refresh_session_labels()
        return True

    def can_use_boundaries_mode(self):
        return (
            self.session is not None
            and self.tabs.currentIndex() == 0
            and self.floorplan_view.has_floorplan()
            and not self.scan_in_progress
        )

    def toggle_boundaries_mode(self):
        self.set_boundaries_mode_enabled(self.boundaries_button.isChecked())

    def set_boundaries_mode_enabled(self, enabled, show_status=True):
        if not hasattr(self, "boundaries_button"):
            return

        enabled = bool(enabled and self.can_use_boundaries_mode())
        if enabled:
            self.plan_tools.set_open(False)
        if enabled and self.floorplan_view.grid_visible:
            self.set_floorplan_grid_enabled(False, show_status=False)

        toolbar = self.ensure_boundaries_toolbar() if enabled else getattr(self, "boundaries_toolbar", None)
        self.floorplan_view.set_boundaries_edit_mode(enabled)
        self.floorplan_view.set_boundaries_tool_state(self.boundaries_tool, self.boundaries_shape)
        if toolbar is not None:
            toolbar.setVisible(enabled)
        self.position_boundaries_toolbar()
        self.update_floorplan_grid_button_state()
        self.update_boundaries_button_state()
        self.update_boundaries_controls_state()
        if show_status:
            self.status.showMessage(
                self.tr("boundaries_enabled") if enabled else self.tr("boundaries_disabled")
            )

    def set_boundaries_tool(self, tool):
        if tool == "fill" and not self.plan_tools.available():
            return
        self.boundaries_tool = tool if tool in ("eraser", "fill") else "draw"
        self.floorplan_view.set_boundaries_tool_state(self.boundaries_tool, self.boundaries_shape)
        self.update_boundaries_controls_state()

    def set_boundaries_shape(self, shape):
        self.boundaries_shape = "square" if shape == "square" else "circle"
        self.floorplan_view.set_boundaries_tool_state(self.boundaries_tool, self.boundaries_shape)
        self.update_boundaries_controls_state()

    def adjust_boundaries_brush_size(self, direction):
        step = BOUNDARIES_BRUSH_SIZE_STEP_PX if direction > 0 else -BOUNDARIES_BRUSH_SIZE_STEP_PX
        if self.floorplan_view.adjust_boundaries_brush_size_px(step):
            self.update_boundaries_controls_state()

    def on_boundaries_mask_changed(self, _has_mask):
        self.update_boundaries_controls_state()
        self.refresh_live_controls()

    def on_boundaries_mask_edited(self):
        if self.session is None:
            return

        was_dirty = self.session.dirty
        self.session.dirty = True
        self.update_boundaries_controls_state()
        if not was_dirty:
            self.refresh_session_labels()

    def clear_boundaries_mask(self):
        if not self.floorplan_view.has_boundaries_mask():
            return

        answer = QMessageBox.question(
            self,
            self.tr("boundaries_clear_title"),
            self.tr("boundaries_clear_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.floorplan_view.clear_boundaries_mask()
        self.update_boundaries_controls_state()
        self.status.showMessage(self.tr("boundaries_cleared"))

    def update_boundaries_button_state(self):
        if not hasattr(self, "boundaries_button"):
            return

        can_edit = self.can_use_boundaries_mode()
        active = bool(
            can_edit
            and getattr(self.floorplan_view, "boundaries_edit_active", False)
        )
        if not can_edit and getattr(self.floorplan_view, "boundaries_edit_active", False):
            self.floorplan_view.set_boundaries_edit_mode(False)
            toolbar = getattr(self, "boundaries_toolbar", None)
            if toolbar is not None:
                toolbar.setVisible(False)
            active = False

        self.boundaries_button.setEnabled(can_edit)
        self.boundaries_button.blockSignals(True)
        self.boundaries_button.setChecked(active)
        self.boundaries_button.blockSignals(False)

    def update_boundaries_controls_state(self):
        if getattr(self, "boundaries_toolbar", None) is None:
            return

        active = bool(getattr(self.floorplan_view, "boundaries_edit_active", False))
        fill_available = bool(getattr(self, "plan_tools", None) and self.plan_tools.available())
        if not fill_available and self.boundaries_tool == "fill":
            self.boundaries_tool = "draw"
            self.floorplan_view.set_boundaries_tool_state("draw", self.boundaries_shape)
        for button, key in ((self.boundaries_fill_button, "fill"), (self.boundaries_auto_fill_button, "auto_fill")):
            button.setVisible(fill_available)
            button.setEnabled(active and fill_available)
            button.setToolTip(self.tr("boundaries_" + key))
            button.setAccessibleName(self.tr("boundaries_" + key))
        self.boundaries_fill_button.setChecked(active and self.boundaries_tool == "fill")
        from qt_ui.qt_plan_icons import update_fill_icons
        update_fill_icons(self)
        self.boundaries_draw_button.setEnabled(active)
        self.boundaries_eraser_button.setEnabled(active)
        brush_active = active and self.boundaries_tool != "fill"
        self.boundaries_circle_button.setEnabled(brush_active)
        self.boundaries_square_button.setEnabled(brush_active)
        self.boundaries_clear_button.setEnabled(
            active and self.floorplan_view.has_boundaries_mask()
        )
        self.boundaries_size_increase_button.setEnabled(
            brush_active and self.floorplan_view.boundaries_brush_size_px < BOUNDARIES_BRUSH_SIZE_MAX_PX
        )
        self.boundaries_size_decrease_button.setEnabled(
            brush_active and self.floorplan_view.boundaries_brush_size_px > BOUNDARIES_BRUSH_SIZE_MIN_PX
        )
        self.boundaries_size_label.setEnabled(brush_active)

        self.boundaries_draw_button.setChecked(active and self.boundaries_tool == "draw")
        self.boundaries_eraser_button.setChecked(active and self.boundaries_tool == "eraser")
        self.boundaries_circle_button.setChecked(active and self.boundaries_shape == "circle")
        self.boundaries_square_button.setChecked(active and self.boundaries_shape == "square")
        self.boundaries_size_label.setText(str(int(round(self.floorplan_view.boundaries_brush_size_px))))
        self.boundaries_size_label.setToolTip(
            self.tr(
                "boundaries_brush_size_value_tooltip",
                size=int(round(self.floorplan_view.boundaries_brush_size_px)),
                minimum=BOUNDARIES_BRUSH_SIZE_MIN_PX,
                maximum=BOUNDARIES_BRUSH_SIZE_MAX_PX,
                step=BOUNDARIES_BRUSH_SIZE_STEP_PX,
            )
        )

    def position_boundaries_toolbar(self):
        toolbar = getattr(self, "boundaries_toolbar", None)
        if toolbar is None or toolbar.isHidden():
            return

        container_width = self.floorplan_container.width()
        container_height = self.floorplan_container.height()
        if container_width <= 0 or container_height <= 0:
            return

        margin = self.spx(12)
        width = toolbar.sizeHint().width()
        height = toolbar.sizeHint().height()
        x = margin
        y = max(margin, (container_height - height) // 2)
        toolbar.setGeometry(x, y, width, height)
        toolbar.raise_()

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
        if self.tabs.currentIndex() == 2:
            return None
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

        display_distance, accepted = QInputDialog.getDouble(
            self,
            self.tr("calibrate_scale_title"),
            self.tr("calibrate_scale_distance_prompt", unit=self.tr(f"measurement_unit_{self.measurement_system}")),
            meters_to_display_units(1.0, self.measurement_system),
            meters_to_display_units(0.01, self.measurement_system),
            meters_to_display_units(10000.0, self.measurement_system),
            2,
        )
        self.floorplan_view.clear_scale_calibration_overlay()
        meters = display_units_to_meters(display_distance, self.measurement_system) if accepted else 0
        if not accepted or meters <= 0:
            self.status.showMessage(self.tr("calibrate_scale_invalid"))
            return

        px_per_meter = float(pixel_distance) / float(meters)
        self.session.update_metadata({"px_per_meter": f"{px_per_meter:.6f}"})
        self.refresh_session_labels()
        self.update_floorplan_grid_button_state()
        self.status.showMessage(
            self.tr("calibrate_scale_saved", scale=format_scale_density(px_per_meter, self.measurement_system))
        )
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
        self.set_floorplan_grid_enabled(False, show_status=False)
        self.refresh_session_labels()
        self.status.showMessage(self.tr("delete_scale_done"))
        self.maybe_update_live_preview()
