from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from ap_group_checks import build_ap_group_conflicts
from ap_groups import (
    AP_ROLE_CHOICES,
    AP_ROLE_INTERNAL,
    build_default_manual_groups,
    build_detected_ap_groups,
    merge_new_bssids_into_manual_groups,
    normalize_ap_metadata,
    normalize_ap_role,
    normalize_bssid,
)


AP_GROUP_COLUMNS = (
    "status",
    "group",
    "alias",
    "role",
    "position",
    "metadata",
    "bssids",
    "ssids",
    "channels",
    "locked",
)


def open_qt_ap_group_manager(parent):
    dialog = APGroupManagerDialog(parent)
    return dialog.exec() == QDialog.DialogCode.Accepted


class APGroupManagerDialog(QDialog):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.session = app.session
        self.groups = []
        self.detected_by_bssid = {}
        self.group_conflicts_by_id = {}
        self.sort_column = "ssids"
        self.sort_reverse = False

        self.setWindowTitle(self.tr("ap_groups_title"))
        self.resize(1680, 820)
        self.setMinimumSize(1300, 700)

        self.build_state()
        self.build_ui()
        self.refresh_all_group_details()
        self.render_rows()
        self.update_action_state()

    def tr(self, key, **kwargs):
        return self.app.tr(key, **kwargs)

    def build_state(self):
        detected_groups = build_detected_ap_groups(self.session.rows, self.app.channel_sort_key)
        self.aliases = self.session.get_ap_aliases()
        saved_groups = self.session.get_ap_groups()
        self.groups = (
            merge_new_bssids_into_manual_groups(saved_groups, self.session.rows)
            if saved_groups
            else build_default_manual_groups(self.session.rows)
        )
        self.detected_by_bssid = {
            bssid: detected_group
            for detected_group in detected_groups
            for bssid in detected_group["bssids"]
        }

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        hint = QLabel(self.tr("ap_groups_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel(self.tr("ap_alias_search")))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.render_rows)
        search_row.addWidget(self.search_edit, 1)
        self.conflict_label = QLabel()
        search_row.addWidget(self.conflict_label)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, len(AP_GROUP_COLUMNS))
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setHorizontalHeaderLabels([
            "",
            self.tr("ap_alias_group"),
            self.tr("ap_alias_value"),
            self.tr("ap_group_role"),
            self.tr("ap_group_position"),
            self.tr("ap_group_metadata"),
            self.tr("ap_alias_bssids"),
            self.tr("ap_alias_ssids"),
            self.tr("ap_alias_channels"),
            self.tr("ap_group_management"),
        ])
        self.table.horizontalHeader().sectionClicked.connect(self.sort_by_column_index)
        self.table.itemSelectionChanged.connect(self.update_action_state)
        layout.addWidget(self.table, 1)

        button_row = QHBoxLayout()
        self.reset_button = QPushButton(self.tr("ap_groups_reset_auto"))
        self.split_button = QPushButton(self.tr("ap_group_split"))
        self.conflict_button = QPushButton(self.tr("ap_group_conflict_details"))
        self.alias_button = QPushButton(self.tr("ap_group_set_alias"))
        self.delete_alias_button = QPushButton(self.tr("ap_group_delete_alias"))
        self.role_button = QPushButton(self.tr("ap_group_set_role"))
        self.save_button = QPushButton(self.tr("save"))
        self.cancel_button = QPushButton(self.tr("cancel"))

        self.reset_button.clicked.connect(self.reset_groups_to_auto)
        self.split_button.clicked.connect(self.open_bssid_group_dialog_for_selected_group)
        self.conflict_button.clicked.connect(self.open_conflict_dialog_for_selected_group)
        self.alias_button.clicked.connect(self.prompt_alias_for_selected_group)
        self.delete_alias_button.clicked.connect(self.delete_alias_for_selected_group)
        self.role_button.clicked.connect(self.prompt_role_for_selected_group)
        self.save_button.clicked.connect(self.save_groups)
        self.cancel_button.clicked.connect(self.reject)

        for button in (
            self.reset_button,
            self.split_button,
            self.conflict_button,
            self.alias_button,
            self.delete_alias_button,
            self.role_button,
        ):
            button_row.addWidget(button)
        button_row.addStretch(1)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.cancel_button)
        layout.addLayout(button_row)

    def refresh_group_details(self, group):
        group["alias"] = group.get("alias") or self.aliases.get(group["group_id"], "")
        group["role"] = normalize_ap_role(group.get("role", AP_ROLE_INTERNAL))
        group["metadata"] = normalize_ap_metadata(group.get("metadata"))
        seen_ssids = set()
        seen_channels = set()
        display_groups = set()
        for bssid in group.get("bssids", []):
            detected_group = self.detected_by_bssid.get(bssid)
            if not detected_group:
                continue
            seen_ssids.update(detected_group["ssids"])
            seen_channels.update(detected_group["channels"])
            display_groups.update(detected_group["display_groups"])

        group["ssids"] = sorted(seen_ssids)
        group["channels"] = sorted(seen_channels, key=self.app.channel_sort_key)
        group["display_groups"] = sorted(display_groups) or [group["group_id"]]

    def refresh_group_checks(self):
        self.group_conflicts_by_id.clear()
        for conflict in build_ap_group_conflicts(self.session.rows, self.groups, self.app.channel_sort_key):
            self.group_conflicts_by_id.setdefault(conflict["group_id"], []).append(conflict)

    def refresh_all_group_details(self):
        for group in self.groups:
            self.refresh_group_details(group)
        self.refresh_group_checks()
        conflict_count = len(self.group_conflicts_by_id)
        self.conflict_label.setText(
            self.tr("ap_group_conflict_count", count=conflict_count)
            if conflict_count
            else ""
        )

    def render_rows(self):
        selected_group_id = self.current_group_id()
        query = self.search_edit.text().strip().lower()
        visible_groups = [group for group in self.groups if self.group_matches_search(group, query)]
        visible_groups.sort(key=lambda group: self.sort_value(group, self.sort_column), reverse=self.sort_reverse)

        self.table.setRowCount(0)
        for group in visible_groups:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = self.get_group_display_values(group)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, group["group_id"])
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, item)
            if group["group_id"] == selected_group_id:
                self.table.selectRow(row)

        self.table.resizeColumnsToContents()
        self.update_action_state()

    def get_group_display_values(self, group):
        role = normalize_ap_role(group.get("role"))
        position = group.get("position") or {}
        position_label = f"{position.get('x')}, {position.get('y')}" if position else "-"
        return (
            "!" if self.group_conflicts_by_id.get(group["group_id"]) else "",
            format_list_preview(group["display_groups"]),
            group.get("alias", ""),
            self.tr(f"ap_group_role_{role}"),
            position_label,
            format_metadata_preview(group.get("metadata")),
            format_list_preview(group["bssids"]),
            ", ".join(group["ssids"]),
            ", ".join(group["channels"]),
            self.tr("ap_group_state_manual") if group.get("locked") else self.tr("ap_group_state_auto"),
        )

    def group_matches_search(self, group, query):
        if not query:
            return True

        role = normalize_ap_role(group.get("role"))
        metadata = normalize_ap_metadata(group.get("metadata"))
        conflict_text = " ".join(
            self.format_group_conflict_summary(conflict)
            for conflict in self.group_conflicts_by_id.get(group["group_id"], [])
        )
        haystack = " ".join([
            group["group_id"],
            " ".join(group["display_groups"]),
            group.get("alias", ""),
            role,
            self.tr(f"ap_group_role_{role}"),
            " ".join(metadata.values()),
            conflict_text,
            " ".join(group["bssids"]),
            " ".join(group["ssids"]),
            " ".join(group["channels"]),
        ]).lower()
        return query in haystack

    def sort_value(self, group, column):
        if column == "status":
            return 0 if self.group_conflicts_by_id.get(group["group_id"]) else 1
        if column == "alias":
            return group.get("alias", "").lower()
        if column == "role":
            return self.tr(f"ap_group_role_{normalize_ap_role(group.get('role'))}").lower()
        if column == "position":
            position = group.get("position") or {}
            return (position.get("x", 999999), position.get("y", 999999))
        if column == "metadata":
            return format_metadata_preview(group.get("metadata")).lower()
        if column == "bssids":
            return " ".join(group["bssids"]).lower()
        if column == "ssids":
            return " ".join(group["ssids"]).lower()
        if column == "channels":
            return [self.app.channel_sort_key(channel) for channel in group["channels"]]
        if column == "locked":
            return 0 if group.get("locked") else 1
        return " ".join(group["display_groups"]).lower()

    def sort_by_column_index(self, index):
        column = AP_GROUP_COLUMNS[index]
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        self.render_rows()

    def current_group_id(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def selected_group(self):
        group_id = self.current_group_id()
        for group in self.groups:
            if group.get("group_id") == group_id:
                return group
        return None

    def require_selected_group(self):
        group = self.selected_group()
        if group is None:
            QMessageBox.warning(self, self.tr("ap_groups_title"), self.tr("ap_group_select_group"))
        return group

    def update_action_state(self):
        group = self.selected_group()
        has_group = group is not None
        self.split_button.setEnabled(has_group)
        self.alias_button.setEnabled(has_group)
        self.role_button.setEnabled(has_group)
        self.delete_alias_button.setEnabled(bool(group and group.get("alias")))
        self.conflict_button.setEnabled(bool(group and self.group_conflicts_by_id.get(group["group_id"])))

    def set_alias(self, group, value):
        group["alias"] = value.strip()
        group["locked"] = True
        self.render_rows()

    def prompt_alias_for_selected_group(self):
        group = self.require_selected_group()
        if group is None:
            return

        value, ok = QInputDialog.getText(
            self,
            self.tr("ap_group_alias_title"),
            self.tr("ap_group_alias_prompt"),
            text=group.get("alias", ""),
        )
        if ok:
            self.set_alias(group, value)

    def delete_alias_for_selected_group(self):
        group = self.require_selected_group()
        if group is None or not group.get("alias"):
            return

        response = QMessageBox.question(
            self,
            self.tr("ap_group_delete_alias_title"),
            self.tr("ap_group_delete_alias_confirm"),
        )
        if response == QMessageBox.StandardButton.Yes:
            self.set_alias(group, "")

    def prompt_role_for_selected_group(self):
        group = self.require_selected_group()
        if group is None:
            return

        role_labels = [self.tr(f"ap_group_role_{role}") for role in AP_ROLE_CHOICES]
        current_role = normalize_ap_role(group.get("role"))
        current_index = list(AP_ROLE_CHOICES).index(current_role)
        label, ok = QInputDialog.getItem(
            self,
            self.tr("ap_group_role_title"),
            self.tr("ap_group_role_prompt"),
            role_labels,
            current_index,
            False,
        )
        if not ok:
            return

        role = AP_ROLE_CHOICES[role_labels.index(label)]
        group["role"] = role
        group["locked"] = True
        self.refresh_all_group_details()
        self.render_rows()

    def reset_groups_to_auto(self):
        response = QMessageBox.question(
            self,
            self.tr("ap_groups_reset_title"),
            self.tr("ap_groups_reset_confirm"),
        )
        if response != QMessageBox.StandardButton.Yes:
            return

        state_by_group = {
            group["group_id"]: {
                "alias": group.get("alias", ""),
                "role": normalize_ap_role(group.get("role")),
                "position": group.get("position"),
                "metadata": normalize_ap_metadata(group.get("metadata")),
            }
            for group in self.groups
        }
        self.groups = build_default_manual_groups(self.session.rows)
        for group in self.groups:
            saved_state = state_by_group.get(group["group_id"], {})
            group["alias"] = saved_state.get("alias") or self.aliases.get(group["group_id"], "")
            group["role"] = saved_state.get("role", AP_ROLE_INTERNAL)
            if saved_state.get("position"):
                group["position"] = saved_state["position"]
            if saved_state.get("metadata"):
                group["metadata"] = saved_state["metadata"]
            group["locked"] = False

        self.refresh_all_group_details()
        self.render_rows()

    def open_bssid_group_dialog_for_selected_group(self):
        group = self.require_selected_group()
        if group is None:
            return
        self.open_bssid_group_dialog(group["group_id"])

    def open_bssid_group_dialog(self, group_id, focus_bssids=None):
        group = self.get_group_by_id(group_id)
        if group is None:
            return

        dialog = BssidSelectionDialog(self, group, self.groups, self.detected_by_bssid, focus_bssids or [])
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_bssids = dialog.selected_bssids()
        if not selected_bssids:
            QMessageBox.warning(self, self.tr("ap_groups_title"), self.tr("ap_group_empty_selection"))
            return

        selected_set = set(selected_bssids)
        for other_group in self.groups:
            if other_group["group_id"] == group_id:
                other_group["bssids"] = selected_bssids
                other_group["locked"] = True
            else:
                other_group["bssids"] = [
                    bssid for bssid in other_group.get("bssids", []) if bssid not in selected_set
                ]

        self.groups = [item for item in self.groups if item.get("bssids")]
        self.groups = merge_new_bssids_into_manual_groups(self.groups, self.session.rows)
        self.refresh_all_group_details()
        self.render_rows()

    def get_group_by_id(self, group_id):
        for group in self.groups:
            if group.get("group_id") == group_id:
                return group
        return None

    def collect_conflict_bssids(self, conflicts):
        bssids = set()
        for conflict in conflicts:
            for channel_bssids in conflict.get("bssids_by_channel", {}).values():
                bssids.update(normalize_bssid(bssid) for bssid in channel_bssids)
        return sorted(bssids)

    def open_conflict_dialog_for_selected_group(self):
        group = self.require_selected_group()
        if group is None:
            return

        conflicts = self.group_conflicts_by_id.get(group["group_id"], [])
        if not conflicts:
            QMessageBox.information(
                self,
                self.tr("ap_group_conflict_title"),
                self.tr("ap_group_conflict_none"),
            )
            return

        dialog = ConflictDialog(self, group["group_id"], conflicts)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.open_bssid_group_dialog(
                group["group_id"],
                focus_bssids=self.collect_conflict_bssids(conflicts),
            )

    def save_groups(self):
        aliases = {
            group["group_id"]: group.get("alias", "")
            for group in self.groups
            if group.get("alias", "").strip()
        }
        aliases_changed = self.session.set_ap_aliases(aliases)
        groups_changed = self.session.set_ap_groups(self.groups)
        if aliases_changed or groups_changed:
            self.session.dirty = True
        self.accept()

    def format_group_conflict_summary(self, conflict):
        return self.tr(
            "ap_group_conflict_band_row",
            band=format_band_label(conflict.get("band", "")),
            channels=", ".join(conflict.get("channels", [])),
        )


class BssidSelectionDialog(QDialog):
    def __init__(self, manager, group, groups, detected_by_bssid, focus_bssids):
        super().__init__(manager)
        self.manager = manager
        self.group = group
        self.groups = groups
        self.detected_by_bssid = detected_by_bssid
        self.focus_bssids = {normalize_bssid(bssid) for bssid in focus_bssids if normalize_bssid(bssid)}
        self.checked_by_bssid = {}

        self.setWindowTitle(manager.tr("ap_group_bssid_title"))
        self.resize(980, 700)
        self.setMinimumSize(850, 580)
        self.build_ui()
        self.render_items()

    def build_ui(self):
        layout = QVBoxLayout(self)
        hint = QLabel(self.manager.tr("ap_group_bssid_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        if self.focus_bssids:
            focus_hint = QLabel(self.manager.tr("ap_group_bssid_warning_focus_hint"))
            focus_hint.setWordWrap(True)
            layout.addWidget(focus_hint)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel(self.manager.tr("ap_alias_search")))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.render_items)
        search_row.addWidget(self.search_edit, 1)
        layout.addLayout(search_row)

        self.list_widget = QListWidget()
        self.list_widget.itemChanged.connect(self.update_checked_state)
        layout.addWidget(self.list_widget, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save_button = QPushButton(self.manager.tr("save"))
        cancel_button = QPushButton(self.manager.tr("cancel"))
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        current_bssids = {normalize_bssid(bssid) for bssid in self.group.get("bssids", [])}
        for bssid in self.detected_by_bssid:
            clean_bssid = normalize_bssid(bssid)
            self.checked_by_bssid[clean_bssid] = clean_bssid in current_bssids

    def render_items(self):
        query = self.search_edit.text().strip().lower()
        self.list_widget.clear()
        all_bssids = sorted(
            self.detected_by_bssid.keys(),
            key=lambda bssid: (0 if normalize_bssid(bssid) in self.focus_bssids else 1, bssid),
        )

        for bssid in all_bssids:
            label = self.build_bssid_label(bssid)
            if query and query not in label.lower():
                continue
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if self.checked_by_bssid.get(normalize_bssid(bssid), False)
                else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, normalize_bssid(bssid))
            self.list_widget.addItem(item)

    def update_checked_state(self, item):
        bssid = item.data(Qt.ItemDataRole.UserRole)
        self.checked_by_bssid[bssid] = item.checkState() == Qt.CheckState.Checked

    def build_bssid_label(self, bssid):
        detected_group = self.detected_by_bssid.get(bssid, {})
        ssids = ", ".join(detected_group.get("ssids", [])) or "-"
        channels = ", ".join(detected_group.get("channels", [])) or "-"
        assigned_label = self.format_assigned_label(bssid)
        if assigned_label:
            label = self.manager.tr(
                "ap_group_bssid_row_with_group",
                bssid=bssid,
                ssids=ssids,
                channels=channels,
                group=assigned_label,
            )
        else:
            label = self.manager.tr(
                "ap_group_bssid_row",
                bssid=bssid,
                ssids=ssids,
                channels=channels,
            )
        if normalize_bssid(bssid) in self.focus_bssids:
            label = self.manager.tr("ap_group_bssid_warning_row", row=label)
        return label

    def format_assigned_label(self, bssid):
        clean_bssid = normalize_bssid(bssid)
        for group in self.groups:
            if clean_bssid not in {normalize_bssid(item) for item in group.get("bssids", [])}:
                continue
            if group.get("group_id") == self.group.get("group_id"):
                return ""
            return group.get("alias") or group.get("group_id") or "-"
        return "-"

    def selected_bssids(self):
        return sorted([
            bssid
            for bssid, checked in self.checked_by_bssid.items()
            if checked
        ])


class ConflictDialog(QDialog):
    def __init__(self, manager, group_id, conflicts):
        super().__init__(manager)
        self.manager = manager
        self.group_id = group_id
        self.conflicts = conflicts

        self.setWindowTitle(manager.tr("ap_group_conflict_title"))
        self.resize(760, 520)
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        hint = QLabel(self.manager.tr("ap_group_conflict_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(self.format_conflicts())
        layout.addWidget(text, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        split_button = QPushButton(self.manager.tr("ap_group_split_from_warning"))
        close_button = QPushButton(self.manager.tr("close"))
        split_button.clicked.connect(self.accept)
        close_button.clicked.connect(self.reject)
        buttons.addWidget(split_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def format_conflicts(self):
        lines = []
        for conflict in self.conflicts:
            lines.append(self.manager.format_group_conflict_summary(conflict))
            for channel in conflict.get("channels", []):
                bssids = ", ".join(conflict.get("bssids_by_channel", {}).get(channel, []))
                lines.append(self.manager.tr("ap_group_conflict_channel_row", channel=channel, bssids=bssids))
            lines.append("")
        return "\n".join(lines).strip()


def format_list_preview(values, limit=2):
    clean_values = [str(value) for value in values if str(value)]
    if len(clean_values) <= limit:
        return ", ".join(clean_values)
    return f"{', '.join(clean_values[:limit])} (+{len(clean_values) - limit})"


def format_metadata_preview(metadata):
    metadata = normalize_ap_metadata(metadata)
    vendor_model = " ".join(value for value in (metadata.get("vendor"), metadata.get("model")) if value)
    if vendor_model:
        return vendor_model
    for field in ("mounting", "expected_bands", "expected_channels", "notes"):
        if metadata.get(field):
            return metadata[field]
    return "-"


def format_band_label(band):
    band = str(band)
    return f"{band} GHz" if band in {"2.4", "5", "6"} else band
