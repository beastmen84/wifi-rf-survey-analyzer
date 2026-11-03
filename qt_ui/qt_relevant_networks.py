"""Relevant network state and dialogs for the Qt workspace."""

import json

try:
    from PySide6.QtWidgets import QDialog, QMessageBox
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from qt_ui.qt_point_workflow import RelevantNetworksDialog
from wifi.scanner import get_connected_ssid


RELEVANT_SSIDS_METADATA_KEY = "relevant_ssids"
KNOWN_SSIDS_METADATA_KEY = "known_ssids"


class RelevantNetworksMixin:
    def load_session_ssid_state(self):
        self.relevant_ssids = self.load_relevant_ssids()
        self.known_ssids = self.load_known_ssids()
        if self.session is not None and RELEVANT_SSIDS_METADATA_KEY in self.session.metadata:
            self.update_relevant_row_flags()

    def load_relevant_ssids(self):
        if self.session is None:
            return set()

        return load_json_string_set(self.session.metadata.get(RELEVANT_SSIDS_METADATA_KEY))

    def load_known_ssids(self):
        if self.session is None:
            return set(self.relevant_ssids)

        known = load_json_string_set(self.session.metadata.get(KNOWN_SSIDS_METADATA_KEY))
        return known or set(self.relevant_ssids)

    def save_known_ssids(self):
        if self.session is None:
            return

        serialized = json.dumps(sorted(self.known_ssids), ensure_ascii=False)
        self.session.update_metadata({KNOWN_SSIDS_METADATA_KEY: serialized})

    def set_relevant_ssids(self, ssids):
        if self.session is None:
            return

        self.relevant_ssids = {
            str(ssid).strip()
            for ssid in ssids
            if str(ssid).strip()
        }
        serialized = json.dumps(sorted(self.relevant_ssids), ensure_ascii=False)
        self.session.update_metadata({RELEVANT_SSIDS_METADATA_KEY: serialized})
        self.known_ssids |= self.relevant_ssids
        self.update_relevant_row_flags()
        self.refresh_session_labels()

    def update_relevant_row_flags(self):
        if self.session is None:
            return

        relevant = set(self.relevant_ssids)
        changed = False
        for row in self.session.rows:
            is_relevant = "1" if str(row.get("ssid", "")).strip() in relevant else "0"
            if row.get("is_relevant") != is_relevant:
                row["is_relevant"] = is_relevant
                changed = True

        if changed:
            self.session.dirty = True

    def available_relevant_ssids(self):
        if self.session is None:
            return set()

        return {
            str(ssid).strip()
            for ssid in (self.known_ssids | self.relevant_ssids | set(self.session.get_ssids()))
            if str(ssid).strip()
        }

    def manage_relevant_ssids(self):
        if self.session is None:
            return

        available_ssids = self.available_relevant_ssids()
        if not available_ssids:
            QMessageBox.warning(self, self.tr("warning"), self.tr("no_relevant_networks_to_manage"))
            return

        dialog = RelevantNetworksDialog(
            self,
            available_ssids,
            self.tr("manage_relevant_networks_title"),
            self.tr("manage_relevant_networks_message"),
            connected_ssid=get_connected_ssid(),
            selected_ssids=self.relevant_ssids,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.known_ssids |= available_ssids
        self.set_relevant_ssids(dialog.selected_ssids())
        self.save_known_ssids()
        self.refresh_points_table()
        self.status.showMessage(self.tr("relevant_networks_updated"))
        self.maybe_update_live_preview()

    def clear_relevant_ssids(self):
        if self.session is None:
            return

        changed = bool(self.relevant_ssids or self.known_ssids)
        for key in (RELEVANT_SSIDS_METADATA_KEY, KNOWN_SSIDS_METADATA_KEY):
            if key in self.session.metadata:
                self.session.metadata.pop(key, None)
                changed = True

        self.relevant_ssids = set()
        self.known_ssids = set()
        self.update_relevant_row_flags()
        self.refresh_session_labels()
        self.refresh_points_table()

        if changed:
            self.session.dirty = True
            self.refresh_session_labels()
            self.status.showMessage(self.tr("relevant_networks_cleared"))


def load_json_string_set(value):
    if not value:
        return set()

    try:
        values = json.loads(value)
    except json.JSONDecodeError:
        return set()

    if not isinstance(values, list):
        return set()

    return {
        str(item).strip()
        for item in values
        if str(item).strip()
    }
