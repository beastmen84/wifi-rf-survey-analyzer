"""Qt AP Group Manager dialog and related editing workflows."""

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QHeaderView,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ap.checks import build_ap_group_conflicts
from ap.metadata import (
    infer_band_from_channel,
    parse_expected_bands,
    parse_expected_channels,
    sort_bands,
    sort_channels,
)
from ap.groups import (
    AP_ROLE_CHOICES,
    AP_ROLE_INTERNAL,
    build_default_manual_groups,
    build_detected_ap_groups,
    merge_new_bssids_into_manual_groups,
    normalize_ap_metadata,
    normalize_ap_role,
    normalize_bssid,
)
from qt_ui.qt_theme import QT_THEMES
from qt_ui.scaling import widget_font, widget_px


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

EXPECTED_BAND_OPTIONS = (
    ("2.4", "2.4 GHz"),
    ("5", "5 GHz"),
    ("6", "6 GHz"),
)

EXPECTED_CHANNEL_GROUPS = (
    ("ap_group_metadata_channel_group_24", tuple(str(channel) for channel in range(1, 14))),
    ("ap_group_metadata_channel_group_5_low", ("36", "40", "44", "48", "52", "56", "60", "64")),
    ("ap_group_metadata_channel_group_5_dfs", (
        "100", "104", "108", "112", "116", "120", "124", "128", "132", "136", "140", "144"
    )),
    ("ap_group_metadata_channel_group_5_high", ("149", "153", "157", "161", "165")),
)
EXPECTED_6GHZ_CHANNELS = tuple(str(channel) for channel in sorted([2] + list(range(1, 234, 4))))

EXPECTED_CHANNEL_GROUPS_BY_BAND = {
    "2.4": EXPECTED_CHANNEL_GROUPS[:1],
    "5": EXPECTED_CHANNEL_GROUPS[1:],
    "6": (("ap_group_metadata_channel_group_6", EXPECTED_6GHZ_CHANNELS),),
}

EXPECTED_CHANNELS_BY_BAND = {
    band: tuple(channel for _title_key, channels in groups for channel in channels)
    for band, groups in EXPECTED_CHANNEL_GROUPS_BY_BAND.items()
}


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
        self.resize(widget_px(self, 1480), widget_px(self, 780))
        self.setMinimumSize(widget_px(self, 1120), widget_px(self, 640))

        self.build_state()
        self.build_ui()
        self.apply_styles()
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
        layout.setContentsMargins(widget_px(self, 14), widget_px(self, 14), widget_px(self, 14), widget_px(self, 14))
        layout.setSpacing(widget_px(self, 10))

        hint = QLabel(self.tr("ap_groups_hint"))
        hint.setObjectName("apDialogHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        search_row = QHBoxLayout()
        search_row.setSpacing(widget_px(self, 8))
        search_label = QLabel(self.tr("ap_alias_search"))
        search_label.setObjectName("apDialogLabel")
        search_row.addWidget(search_label)
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.render_rows)
        search_row.addWidget(self.search_edit, 1)
        self.conflict_label = QLabel()
        self.conflict_label.setObjectName("apConflictLabel")
        search_row.addWidget(self.conflict_label)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, len(AP_GROUP_COLUMNS))
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setVisible(False)
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
        self.configure_table_columns()
        self.table.horizontalHeader().sectionClicked.connect(self.sort_by_column_index)
        self.table.itemSelectionChanged.connect(self.update_action_state)
        layout.addWidget(self.table, 1)

        footer = QFrame()
        footer.setObjectName("apDialogFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(widget_px(self, 0), widget_px(self, 4), widget_px(self, 0), 0)
        footer_layout.setSpacing(widget_px(self, 8))

        action_row = QHBoxLayout()
        action_row.setSpacing(widget_px(self, 6))
        self.reset_button = QPushButton(self.tr("ap_groups_reset_auto"))
        self.split_button = QPushButton(self.tr("ap_group_split"))
        self.conflict_button = QPushButton(self.tr("ap_group_conflict_details"))
        self.alias_button = QPushButton(self.tr("ap_group_set_alias"))
        self.delete_alias_button = QPushButton(self.tr("ap_group_delete_alias"))
        self.role_button = QPushButton(self.tr("ap_group_set_role"))
        self.metadata_button = QPushButton(self.tr("ap_group_metadata"))
        self.position_button = QPushButton(self.tr("ap_group_set_position"))
        self.save_button = QPushButton(self.tr("save"))
        self.cancel_button = QPushButton(self.tr("cancel"))

        self.reset_button.clicked.connect(self.reset_groups_to_auto)
        self.split_button.clicked.connect(self.open_bssid_group_dialog_for_selected_group)
        self.conflict_button.clicked.connect(self.open_conflict_dialog_for_selected_group)
        self.alias_button.clicked.connect(self.prompt_alias_for_selected_group)
        self.delete_alias_button.clicked.connect(self.delete_alias_for_selected_group)
        self.role_button.clicked.connect(self.prompt_role_for_selected_group)
        self.metadata_button.clicked.connect(self.open_metadata_dialog_for_selected_group)
        self.position_button.clicked.connect(self.start_positioning_for_selected_group)
        self.save_button.clicked.connect(self.save_groups)
        self.cancel_button.clicked.connect(self.reject)

        for button in (
            self.reset_button,
            self.split_button,
            self.conflict_button,
            self.alias_button,
            self.delete_alias_button,
            self.role_button,
            self.metadata_button,
            self.position_button,
        ):
            self.prepare_action_button(button)
            action_row.addWidget(button)
        action_row.addStretch(1)
        footer_layout.addLayout(action_row)

        commit_row = QHBoxLayout()
        commit_row.setSpacing(widget_px(self, 8))
        self.save_button.setObjectName("apDialogPrimaryButton")
        self.cancel_button.setObjectName("apDialogActionButton")
        self.prepare_action_button(self.save_button)
        self.prepare_action_button(self.cancel_button)
        commit_row.addStretch(1)
        commit_row.addWidget(self.save_button)
        commit_row.addWidget(self.cancel_button)
        footer_layout.addLayout(commit_row)
        layout.addWidget(footer)

    def apply_styles(self):
        palette = QT_THEMES.get(getattr(self.app, "theme", "light"), QT_THEMES["light"])
        s = lambda value: widget_px(self, value)
        font = lambda value: widget_font(self, value)
        self.setStyleSheet(
            f"""
            QDialog, QWidget {{
                background: {palette["bg"]};
                color: {palette["text"]};
                font-family: "Segoe UI";
                font-size: {font(10)}pt;
            }}
            QLabel#apDialogHint {{
                color: {palette["text"]};
                font-size: {font(10)}pt;
            }}
            QLabel#apDialogLabel {{
                color: {palette["muted"]};
                font-weight: 700;
            }}
            QLabel#apConflictLabel {{
                color: {palette["metric_danger"]};
                font-weight: 700;
            }}
            QLineEdit {{
                background: {palette["panel"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(5)}px;
                padding: {s(6)}px {s(8)}px;
            }}
            QGroupBox {{
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(5)}px;
                margin-top: {s(9)}px;
                padding: {s(8)}px {s(8)}px {s(6)}px {s(8)}px;
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {s(8)}px;
                padding: 0 {s(4)}px;
                background: {palette["bg"]};
            }}
            QTextEdit {{
                background: {palette["panel"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(5)}px;
                padding: {s(6)}px;
            }}
            QCheckBox {{
                color: {palette["text"]};
                spacing: {s(9)}px;
                padding: {s(3)}px {s(2)}px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: {s(18)}px;
                height: {s(18)}px;
                border-radius: {s(4)}px;
                border: 1px solid {palette["border"]};
                background: {palette["panel"]};
            }}
            QCheckBox::indicator:hover {{
                border: 1px solid {palette["metric_info"]};
            }}
            QCheckBox::indicator:checked {{
                background: {palette["metric_info"]};
                border: 1px solid {palette["metric_info"]};
            }}
            QTableWidget {{
                background: {palette["panel"]};
                alternate-background-color: {palette["panel_alt"]};
                color: {palette["text"]};
                selection-background-color: {palette["metric_info"]};
                selection-color: #FFFFFF;
                border: 1px solid {palette["border"]};
                border-radius: {s(5)}px;
            }}
            QTableWidget::item {{
                border: 0;
                border-bottom: 1px solid {palette["border"]};
                padding: {s(5)}px {s(7)}px;
            }}
            QTableWidget::item:selected {{
                background: {palette["metric_info"]};
                color: #FFFFFF;
                border-bottom: 1px solid {palette["metric_info"]};
            }}
            QTableWidget::item:focus {{
                border: 0;
                border-bottom: 1px solid {palette["border"]};
            }}
            QWidget#apTableCheckboxContainer {{
                background: transparent;
            }}
            QHeaderView::section {{
                background: {palette["header"]};
                color: {palette["text"]};
                padding: {s(6)}px {s(7)}px;
                border: 0;
                border-right: 1px solid {palette["border"]};
                font-weight: 700;
            }}
            QFrame#apDialogFooter {{
                background: {palette["bg"]};
            }}
            QPushButton#apDialogActionButton, QPushButton#apDialogPrimaryButton {{
                min-width: 0;
                background: {palette["button_bg"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(5)}px;
                padding: {s(6)}px {s(10)}px;
                font-weight: 600;
            }}
            QPushButton#apDialogActionButton:hover {{
                background: {palette["button_hover"]};
            }}
            QPushButton#apDialogActionButton:disabled {{
                color: {palette["muted"]};
                background: {palette["panel_alt"]};
            }}
            QPushButton#apDialogPrimaryButton {{
                background: {palette["metric_info"]};
                color: #FFFFFF;
                border: 1px solid {palette["metric_info"]};
            }}
            QPushButton#apDialogPrimaryButton:hover {{
                background: {palette["metric_info"]};
            }}
            """
        )

    def prepare_action_button(self, button):
        if not button.objectName():
            button.setObjectName("apDialogActionButton")
        button.setMinimumWidth(0)
        button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def configure_table_columns(self):
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(widget_px(self, 34))
        for column in range(self.table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.apply_table_column_widths()

    def apply_table_column_widths(self):
        if self.table.columnCount() == 0:
            return

        self.table.resizeColumnsToContents()
        fixed_limits = {
            0: (34, 42),
            1: (150, 240),
            3: (84, 110),
            4: (86, 112),
            5: (92, 150),
            6: (180, 300),
            7: (190, 320),
            8: (82, 112),
            9: (116, 150),
        }
        widths = {}
        for column, (minimum, maximum) in fixed_limits.items():
            content_width = self.table.columnWidth(column) + widget_px(self, 12)
            widths[column] = max(widget_px(self, minimum), min(content_width, widget_px(self, maximum)))

        viewport_width = max(0, self.table.viewport().width() - widget_px(self, 4))
        reserved_width = sum(widths.values())
        alias_content_width = self.table.columnWidth(2) + widget_px(self, 20)
        alias_min_width = max(widget_px(self, 220), min(alias_content_width, widget_px(self, 360)))
        self.table.horizontalHeader().setMinimumSectionSize(widget_px(self, 34))

        for column, width in widths.items():
            self.table.setColumnWidth(column, width)
        self.table.setColumnWidth(2, max(alias_min_width, viewport_width - reserved_width))
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "table"):
            self.apply_table_column_widths()

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
                if column in {0, 3, 4, 5, 8, 9}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, group["group_id"])
                self.table.setItem(row, column, item)
            if group["group_id"] == selected_group_id:
                self.table.selectRow(row)
            self.table.setRowHeight(row, self.row_height_for_values(values))

        self.apply_table_column_widths()
        self.update_action_state()

    def get_group_display_values(self, group):
        role = normalize_ap_role(group.get("role"))
        position = group.get("position") or {}
        position_label = f"{position.get('x')}, {position.get('y')}" if position else "-"
        return (
            "!" if self.group_conflicts_by_id.get(group["group_id"]) else "",
            format_multiline_list(group["display_groups"]),
            group.get("alias", ""),
            self.tr(f"ap_group_role_{role}"),
            position_label,
            format_metadata_preview(group.get("metadata")),
            format_multiline_list(group["bssids"]),
            format_multiline_list(group["ssids"]),
            ", ".join(group["channels"]),
            self.tr("ap_group_state_manual") if group.get("locked") else self.tr("ap_group_state_auto"),
        )

    def row_height_for_values(self, values):
        multiline_columns = (1, 6, 7)
        line_count = max(str(values[column]).count("\n") + 1 for column in multiline_columns)
        line_height = self.table.fontMetrics().lineSpacing()
        return max(widget_px(self, 44), (line_height * line_count) + widget_px(self, 18))

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
        self.metadata_button.setEnabled(has_group)
        self.position_button.setEnabled(has_group)
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

    def open_metadata_dialog_for_selected_group(self):
        group = self.require_selected_group()
        if group is None:
            return

        dialog = MetadataDialog(self, group)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        group["metadata"] = dialog.metadata_values()
        group["locked"] = True
        self.refresh_all_group_details()
        self.render_rows()

    def start_positioning_for_selected_group(self):
        group = self.require_selected_group()
        if group is None:
            return

        if not self.app.floorplan_view.has_floorplan():
            QMessageBox.warning(self, self.tr("warning"), self.tr("load_plan_first"))
            return

        group_id = group["group_id"]
        self.persist_groups()
        self.accept()
        self.app.start_ap_positioning(group_id)

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

    def persist_groups(self):
        aliases = {
            group["group_id"]: group.get("alias", "")
            for group in self.groups
            if group.get("alias", "").strip()
        }
        aliases_changed = self.session.set_ap_aliases(aliases)
        groups_changed = self.session.set_ap_groups(self.groups)
        if aliases_changed or groups_changed:
            self.session.dirty = True
        return aliases_changed or groups_changed

    def save_groups(self):
        self.persist_groups()
        self.accept()

    def format_group_conflict_summary(self, conflict):
        return self.tr(
            "ap_group_conflict_band_row",
            band=format_band_label(conflict.get("band", "")),
            channels=", ".join(conflict.get("channels", [])),
        )


class MetadataDialog(QDialog):
    def __init__(self, manager, group):
        super().__init__(manager)
        self.manager = manager
        self.group = group
        self.metadata = normalize_ap_metadata(group.get("metadata"))
        self.field_edits = {}
        self.band_checks = {}
        self.channel_buttons = {}
        self.band_summary_labels = {}
        self.selected_channels_by_band = self.initial_selected_channels_by_band()

        self.setWindowTitle(manager.tr("ap_group_metadata_title"))
        self.resize(widget_px(self, 980), widget_px(self, 620))
        self.setMinimumSize(widget_px(self, 860), widget_px(self, 560))
        self.setStyleSheet(manager.styleSheet())
        self.build_ui()

    def initial_selected_channels_by_band(self):
        selected = {band: set() for band, _label in EXPECTED_BAND_OPTIONS}
        expected_bands = parse_expected_bands(self.metadata.get("expected_bands", ""))
        for channel in parse_expected_channels(self.metadata.get("expected_channels", "")):
            candidate_bands = infer_expected_channel_bands(channel, expected_bands)
            for band in candidate_bands:
                selected[band].add(channel)
        return selected

    def build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(widget_px(self, 12), widget_px(self, 12), widget_px(self, 12), widget_px(self, 12))
        outer.setSpacing(widget_px(self, 8))

        hint = QLabel(self.manager.tr("ap_group_metadata_hint"))
        hint.setObjectName("apDialogHint")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(widget_px(self, 2), widget_px(self, 2), widget_px(self, 2), widget_px(self, 2))
        content_layout.setSpacing(widget_px(self, 8))

        form = QGridLayout()
        form.setHorizontalSpacing(widget_px(self, 10))
        form.setVerticalSpacing(widget_px(self, 4))
        for column, field in enumerate(("vendor", "model", "mounting")):
            label = QLabel(self.manager.tr(f"ap_group_metadata_{field}"))
            label.setObjectName("apDialogLabel")
            edit = QLineEdit(self.metadata.get(field, ""))
            self.field_edits[field] = edit
            form.addWidget(label, 0, column)
            form.addWidget(edit, 1, column)
        content_layout.addLayout(form)

        self.build_band_channel_section(content_layout)

        content_layout.addWidget(QLabel(self.manager.tr("ap_group_metadata_notes")))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlainText(self.metadata.get("notes", ""))
        self.notes_edit.setMinimumHeight(widget_px(self, 104))
        content_layout.addWidget(self.notes_edit)
        outer.addLayout(content_layout, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save_button = QPushButton(self.manager.tr("save"))
        cancel_button = QPushButton(self.manager.tr("cancel"))
        save_button.setObjectName("apDialogPrimaryButton")
        cancel_button.setObjectName("apDialogActionButton")
        self.manager.prepare_action_button(save_button)
        self.manager.prepare_action_button(cancel_button)
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        outer.addLayout(buttons)

    def build_band_channel_section(self, parent_layout):
        selected_bands = parse_expected_bands(self.metadata.get("expected_bands", ""))
        selected_bands.update(
            band for band, channels in self.selected_channels_by_band.items() if channels
        )

        section = QGroupBox(self.manager.tr("ap_group_metadata_expected_bands"))
        section_layout = QGridLayout(section)
        section_layout.setContentsMargins(widget_px(self, 10), widget_px(self, 10), widget_px(self, 10), widget_px(self, 10))
        section_layout.setHorizontalSpacing(widget_px(self, 12))
        section_layout.setVerticalSpacing(widget_px(self, 8))
        section_layout.addWidget(self.header_label("ap_group_metadata_band"), 0, 0)
        section_layout.addWidget(self.header_label("ap_group_metadata_channels"), 0, 1)
        section_layout.addWidget(self.header_label("ap_group_metadata_selected_channels"), 0, 2)
        section_layout.setColumnStretch(2, 1)

        for row, (band_value, band_label) in enumerate(EXPECTED_BAND_OPTIONS, start=1):
            checkbox = QCheckBox(band_label)
            checkbox.setChecked(band_value in selected_bands)
            checkbox.stateChanged.connect(lambda _state, band=band_value: self.update_band_row_state(band))
            self.band_checks[band_value] = checkbox
            section_layout.addWidget(checkbox, row, 0)

            button = QPushButton(self.manager.tr("ap_group_metadata_edit_channels"))
            button.setObjectName("apDialogActionButton")
            self.manager.prepare_action_button(button)
            button.setMinimumWidth(widget_px(self, 120))
            button.clicked.connect(lambda _checked=False, band=band_value: self.open_channel_picker(band))
            self.channel_buttons[band_value] = button
            section_layout.addWidget(button, row, 1)

            summary = QLabel()
            summary.setObjectName("apDialogHint")
            summary.setWordWrap(True)
            self.band_summary_labels[band_value] = summary
            section_layout.addWidget(summary, row, 2)

        self.update_all_band_row_states()

        parent_layout.addWidget(section)

    def header_label(self, key):
        label = QLabel(self.manager.tr(key))
        label.setObjectName("apDialogLabel")
        return label

    def update_all_band_row_states(self):
        for band_value, _label in EXPECTED_BAND_OPTIONS:
            self.update_band_row_state(band_value)

    def update_band_row_state(self, band):
        is_checked = self.band_checks[band].isChecked()
        available_channels = EXPECTED_CHANNELS_BY_BAND.get(band, ())
        button = self.channel_buttons[band]
        button.setEnabled(is_checked and bool(available_channels))
        self.band_summary_labels[band].setText(self.channel_summary_text(band))

    def channel_summary_text(self, band):
        if not self.band_checks[band].isChecked():
            return self.manager.tr("ap_group_metadata_band_disabled")

        available_channels = EXPECTED_CHANNELS_BY_BAND.get(band, ())
        if not available_channels:
            return self.manager.tr("ap_group_metadata_channels_unavailable")

        channels = sort_channels(
            self.selected_channels_by_band.get(band, set()),
            self.manager.app.channel_sort_key,
        )
        if not channels:
            return self.manager.tr("ap_group_metadata_no_channels")

        return ", ".join(f"CH {channel}" for channel in channels)

    def open_channel_picker(self, band):
        if not self.band_checks[band].isChecked():
            return

        channels = EXPECTED_CHANNELS_BY_BAND.get(band, ())
        if not channels:
            return

        dialog = ChannelSelectionDialog(
            self,
            band,
            channels,
            self.selected_channels_by_band.get(band, set()),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.selected_channels_by_band[band] = set(dialog.selected_channels())
        self.update_band_row_state(band)

    def metadata_values(self):
        expected_channels = sort_channels(
            [
                channel
                for band, band_channels in self.selected_channels_by_band.items()
                if self.band_checks[band].isChecked()
                for channel in band_channels
            ],
            self.manager.app.channel_sort_key,
        )
        expected_bands = {
            band
            for band, checkbox in self.band_checks.items()
            if checkbox.isChecked()
        }
        for channel in expected_channels:
            for band in infer_expected_channel_bands(channel, expected_bands):
                expected_bands.add(band)

        values = {
            field: edit.text()
            for field, edit in self.field_edits.items()
        }
        values["expected_bands"] = ", ".join(sort_bands(expected_bands))
        values["expected_channels"] = ", ".join(expected_channels)
        values["notes"] = self.notes_edit.toPlainText().strip()
        return normalize_ap_metadata(values)


class ChannelSelectionDialog(QDialog):
    def __init__(self, metadata_dialog, band, channels, selected_channels):
        super().__init__(metadata_dialog)
        self.metadata_dialog = metadata_dialog
        self.manager = metadata_dialog.manager
        self.band = band
        self.channels = tuple(channels)
        self.channel_checks = {}
        self.setWindowTitle(
            self.manager.tr(
                "ap_group_metadata_channel_picker_title",
                band=format_band_label(band),
            )
        )
        width, height = self.dialog_size_for_channels()
        self.resize(width, height)
        self.setMinimumSize(width, height)
        self.setStyleSheet(self.manager.styleSheet())
        self.build_ui(set(selected_channels))

    def dialog_size_for_channels(self):
        rows = max(1, math.ceil(len(self.channels) / self.column_count()))
        width = max(widget_px(self, 360), (self.column_count() * widget_px(self, 96)) + widget_px(self, 54))
        height = widget_px(self, 152) + (rows * widget_px(self, 34))
        return width, max(widget_px(self, 250), height)

    def column_count(self):
        return min(4, max(2, math.ceil(len(self.channels) / 4)))

    def build_ui(self, selected_channels):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(widget_px(self, 12), widget_px(self, 12), widget_px(self, 12), widget_px(self, 12))
        layout.setSpacing(widget_px(self, 8))

        grid = QGridLayout()
        grid.setHorizontalSpacing(widget_px(self, 12))
        grid.setVerticalSpacing(widget_px(self, 6))
        columns = self.column_count()
        for index, channel in enumerate(self.channels):
            checkbox = QCheckBox(f"CH {channel}")
            checkbox.setChecked(channel in selected_channels)
            checkbox.setMinimumWidth(widget_px(self, 84))
            self.channel_checks[channel] = checkbox
            grid.addWidget(checkbox, index // columns, index % columns)
        layout.addLayout(grid, 1)

        action_row = QHBoxLayout()
        action_row.setSpacing(widget_px(self, 8))
        select_button = QPushButton(self.manager.tr("ap_group_metadata_select_all"))
        clear_button = QPushButton(self.manager.tr("ap_group_metadata_clear"))
        for button in (select_button, clear_button):
            button.setObjectName("apDialogActionButton")
            self.manager.prepare_action_button(button)
        select_button.clicked.connect(lambda _checked=False: self.set_all_channels(True))
        clear_button.clicked.connect(lambda _checked=False: self.set_all_channels(False))
        action_row.addWidget(select_button)
        action_row.addWidget(clear_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save_button = QPushButton(self.manager.tr("save"))
        cancel_button = QPushButton(self.manager.tr("cancel"))
        save_button.setObjectName("apDialogPrimaryButton")
        cancel_button.setObjectName("apDialogActionButton")
        self.manager.prepare_action_button(save_button)
        self.manager.prepare_action_button(cancel_button)
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

    def set_all_channels(self, enabled):
        for checkbox in self.channel_checks.values():
            checkbox.setChecked(enabled)

    def selected_channels(self):
        return [
            channel
            for channel, checkbox in self.channel_checks.items()
            if checkbox.isChecked()
        ]


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
        self.resize(widget_px(self, 1180), widget_px(self, 720))
        self.setMinimumSize(widget_px(self, 980), widget_px(self, 580))
        self.setStyleSheet(manager.styleSheet())
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

        self.table = QTableWidget(0, 5)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(True)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalHeaderLabels([
            "",
            self.manager.tr("ap_alias_bssids"),
            self.manager.tr("ap_alias_ssids"),
            self.manager.tr("ap_alias_channels"),
            self.manager.tr("ap_group_bssid_other_group"),
        ])
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        for column in range(self.table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

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
        self.table.setRowCount(0)
        all_bssids = sorted(
            self.detected_by_bssid.keys(),
            key=lambda bssid: (0 if normalize_bssid(bssid) in self.focus_bssids else 1, bssid),
        )

        for bssid in all_bssids:
            row_data = self.build_bssid_row_data(bssid)
            if query and query not in " ".join(row_data.values()).lower():
                continue
            clean_bssid = normalize_bssid(bssid)
            row = self.table.rowCount()
            self.table.insertRow(row)

            checkbox_container = QWidget()
            checkbox_container.setObjectName("apTableCheckboxContainer")
            checkbox_container.setAutoFillBackground(False)
            checkbox_layout = QHBoxLayout(checkbox_container)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox = QCheckBox()
            checkbox.setChecked(self.checked_by_bssid.get(clean_bssid, False))
            checkbox.toggled.connect(
                lambda checked, selected_bssid=clean_bssid: self.set_bssid_checked(selected_bssid, checked)
            )
            checkbox_layout.addWidget(checkbox)
            self.table.setCellWidget(row, 0, checkbox_container)

            values = [
                row_data["bssid"],
                row_data["ssids"],
                row_data["channels"],
                row_data["other_group"],
            ]
            for offset, value in enumerate(values, start=1):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                item.setData(Qt.ItemDataRole.UserRole, clean_bssid)
                if offset in {1, 3, 4}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, offset, item)
            self.table.setRowHeight(row, widget_px(self, 38))

        self.apply_table_column_widths()

    def set_bssid_checked(self, bssid, checked):
        self.checked_by_bssid[bssid] = bool(checked)

    def build_bssid_row_data(self, bssid):
        detected_group = self.detected_by_bssid.get(bssid, {})
        ssids = ", ".join(detected_group.get("ssids", [])) or "-"
        channels = ", ".join(detected_group.get("channels", [])) or "-"
        other_group = self.format_other_group_label(bssid)
        return {
            "bssid": bssid,
            "ssids": ssids,
            "channels": channels,
            "other_group": other_group or "-",
            "focus": "!" if normalize_bssid(bssid) in self.focus_bssids else "",
        }

    def format_other_group_label(self, bssid):
        clean_bssid = normalize_bssid(bssid)
        for group in self.groups:
            if clean_bssid not in {normalize_bssid(item) for item in group.get("bssids", [])}:
                continue
            if group.get("group_id") == self.group.get("group_id"):
                return ""
            return group.get("alias") or group.get("group_id") or "-"
        return ""

    def apply_table_column_widths(self):
        self.table.resizeColumnsToContents()
        viewport_width = max(0, self.table.viewport().width() - widget_px(self, 4))
        fixed_widths = {
            0: widget_px(self, 48),
            1: max(widget_px(self, 190), min(self.table.columnWidth(1) + widget_px(self, 16), widget_px(self, 240))),
            3: max(widget_px(self, 92), min(self.table.columnWidth(3) + widget_px(self, 18), widget_px(self, 130))),
            4: max(widget_px(self, 150), min(self.table.columnWidth(4) + widget_px(self, 18), widget_px(self, 260))),
        }
        reserved_width = sum(fixed_widths.values())
        ssid_width = max(widget_px(self, 260), viewport_width - reserved_width)
        for column, width in fixed_widths.items():
            self.table.setColumnWidth(column, width)
        self.table.setColumnWidth(2, ssid_width)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "table"):
            self.apply_table_column_widths()

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
        self.resize(widget_px(self, 760), widget_px(self, 520))
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


def format_multiline_list(values):
    clean_values = [str(value) for value in values if str(value)]
    return "\n".join(clean_values) if clean_values else "-"


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


def infer_expected_channel_bands(channel, preferred_bands=None):
    preferred_bands = set(preferred_bands or [])
    candidates = {
        band
        for band, channels in EXPECTED_CHANNELS_BY_BAND.items()
        if str(channel) in channels
    }
    if preferred_bands:
        preferred_candidates = candidates & preferred_bands
        if preferred_candidates:
            return sorted(preferred_candidates, key=lambda band: {"2.4": 0, "5": 1, "6": 2}.get(band, 99))

    inferred = infer_band_from_channel(channel)
    if inferred:
        return [inferred]

    return sorted(candidates, key=lambda band: {"2.4": 0, "5": 1, "6": 2}.get(band, 99))
