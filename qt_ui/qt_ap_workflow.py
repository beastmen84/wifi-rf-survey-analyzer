"""AP group actions and AP position workflow for the Qt workspace."""

try:
    from PySide6.QtWidgets import QMessageBox
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from qt_ui.qt_ap_groups import open_qt_ap_group_manager
from qt_ui.qt_tooltips import build_html_tooltip


class ApWorkflowMixin:
    def open_ap_group_manager(self):
        if self.session is None:
            return

        if open_qt_ap_group_manager(self):
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
                group["position"] = {"x": int(x), "y": int(y)}
                group["locked"] = True
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
        return build_html_tooltip(
            self.tr("ap_group_position_tooltip_title"),
            [
                (self.tr("ap_alias_group"), group.get("group_id", "-")),
                (self.tr("ap_alias_value"), label),
                ("x/y", f"{x}, {y}"),
                (self.tr("ap_alias_bssids"), ", ".join(group.get("bssids", [])) or "-"),
            ],
            "#0d6efd",
        )

    def channel_sort_key(self, channel):
        try:
            return int(str(channel).strip())
        except (TypeError, ValueError):
            return 9999
