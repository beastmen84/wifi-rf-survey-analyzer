"""AP group actions and AP position workflow for the Qt workspace."""

try:
    from PySide6.QtWidgets import QMessageBox
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from qt_ui.qt_ap_groups import open_qt_ap_group_manager
from qt_ui.qt_floorplan import format_ap_tooltip
from ap.memory import clear_group_memory_flag
from ap.groups import invalidate_ap_group_confirmation
from survey.plan_mode import is_drawn_plan


class ApWorkflowMixin:
    def open_ap_group_manager(self, focus_group_id=None, open_metadata=False):
        if self.session is None:
            return

        if open_qt_ap_group_manager(self, focus_group_id=focus_group_id, open_metadata=open_metadata):
            self.refresh_session_labels()
            self.refresh_points_table()
            if not self.floorplan_view.pending_ap_position_group_id:
                self.status.showMessage(self.tr("ap_groups_saved"))
            self.maybe_update_live_preview()

    def start_ap_positioning(self, group_id):
        if self.session is None:
            return False

        if not self.floorplan_view.has_floorplan():
            QMessageBox.warning(self, self.tr("warning"), self.tr("load_plan_first"))
            return False

        label = self.get_ap_group_display_name(group_id)
        if is_drawn_plan(self.session.metadata):
            if not self.get_px_per_meter():
                QMessageBox.warning(self, self.tr("warning"), self.tr("ap_position_no_scale"))
                return False
            from qt_ui.qt_ap_symbol_binding import assign_ap_symbol
            self.tabs.setCurrentIndex(0)
            return assign_ap_symbol(self, str(group_id))
        started = self.floorplan_view.start_ap_position_pick(group_id, label)
        if started:
            self.tabs.setCurrentIndex(0)
            self.status.showMessage(self.tr("ap_position_pick", group=label))
        return started

    def save_ap_position(self, group_id, x, y):
        if self.session is None:
            return

        groups = self.session.get_ap_groups()
        updated = False
        for group in groups:
            if str(group.get("group_id", "")) == str(group_id):
                if group.get("position") != {"x": int(x), "y": int(y)}:
                    invalidate_ap_group_confirmation(group)
                group["position"] = {"x": int(x), "y": int(y)}
                group["locked"] = True
                clear_group_memory_flag(group)
                updated = True
                break

        if not updated:
            QMessageBox.warning(self, self.tr("warning"), self.tr("ap_group_not_found"))
            return

        self.session.set_ap_groups(groups)
        self.refresh_session_labels()
        self.refresh_points_table()
        self.status.showMessage(
            self.tr("ap_position_saved", group=self.get_ap_group_display_name(group_id), x=x, y=y)
        )
        self.maybe_update_live_preview()

    def cancel_ap_positioning(self):
        self.status.showMessage(self.tr("ap_position_cancelled"))

    def get_ap_group_display_name(self, group_id):
        if self.session is None:
            return str(group_id)

        group_id = str(group_id)
        for group in self.session.get_ap_groups():
            if str(group.get("group_id", "")) == group_id:
                alias = str(group.get("alias", "")).strip()
                return alias or group_id

        return group_id

    def format_ap_position_tooltip(self, group, label, x, y):
        return format_ap_tooltip(group, label, x, y, self.tr)

    def channel_sort_key(self, channel):
        try:
            return int(str(channel).strip())
        except (TypeError, ValueError):
            return 9999
