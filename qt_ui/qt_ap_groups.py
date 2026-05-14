"""Qt AP Group Manager dialog and related editing workflows."""

import math

from PySide6.QtCore import Qt, QTimer
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
    normalize_channel,
    parse_expected_bands,
    parse_expected_channels,
    sort_bands,
    sort_channels,
)
from ap.groups import (
    AP_ANALYSIS_CHANNEL_OVERRIDE_FIELDS,
    AP_MEMORY_APPLIED_KEY,
    AP_ROLE_CHOICES,
    AP_ROLE_INTERNAL,
    build_default_manual_groups,
    build_detected_ap_groups,
    build_manual_ap_group,
    build_unique_group_id,
    get_ap_analysis_channel_override_field,
    merge_new_bssids_into_manual_groups,
    normalize_ap_analysis_channel_override,
    normalize_ap_metadata,
    normalize_ap_role,
    normalize_bssid,
)
from ap.memory import (
    apply_group_memory_update,
    clear_group_memory_flag,
    get_group_memory_update_fields,
    group_has_memory_flag,
    load_ap_memory,
)
from qt_ui.qt_theme import QT_THEMES, build_scrollbar_stylesheet
from qt_ui.scaling import widget_font, widget_px
from wifi.band import get_row_band


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


def open_qt_ap_group_manager(parent, focus_group_id=None, open_metadata=False):
    dialog = APGroupManagerDialog(parent)
    if focus_group_id:
        dialog.focus_group_by_id(focus_group_id)
    if open_metadata:
        QTimer.singleShot(0, dialog.open_metadata_dialog_for_selected_group)
    return dialog.exec() == QDialog.DialogCode.Accepted


def make_dialog_label(text):
    label = QLabel(text)
    label.setObjectName("apDialogLabel")
    return label


def add_filter_pair(layout, owner, label_text, control, min_width=None):
    if min_width is not None:
        control.setMinimumWidth(widget_px(owner, min_width))
    control.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    container = QWidget()
    container.setObjectName("apFilterPair")
    pair_layout = QHBoxLayout(container)
    pair_layout.setContentsMargins(0, 0, 0, 0)
    pair_layout.setSpacing(widget_px(owner, 6))
    pair_layout.addWidget(make_dialog_label(label_text))
    pair_layout.addWidget(control)
    layout.addWidget(container)


class APGroupManagerDialog(QDialog):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.session = app.session
        self.groups = []
        self.detected_by_bssid = {}
        self.memory_records = []
        self.group_conflicts_by_id = {}
        self.visible_group_ids = []
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

    def make_filter_label(self, key):
        return make_dialog_label(self.tr(key))

    def build_state(self):
        if hasattr(self.session, "refresh_ap_groups_from_rows"):
            self.session.refresh_ap_groups_from_rows(update_memory=False)
        self.memory_records = load_ap_memory().get("groups", [])
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
        search_label = self.make_filter_label("ap_alias_search")
        search_row.addWidget(search_label)
        self.search_edit = QLineEdit()
        self.search_edit.setMinimumHeight(widget_px(self, 34))
        self.search_edit.textChanged.connect(self.render_rows)
        search_row.addWidget(self.search_edit, 1)
        self.conflict_label = QLabel()
        self.conflict_label.setObjectName("apConflictLabel")
        search_row.addWidget(self.conflict_label)
        layout.addLayout(search_row)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(widget_px(self, 14))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItem(self.tr("ap_group_filter_status_all"), "all")
        self.status_filter_combo.addItem(self.tr("ap_group_filter_status_warning"), "warning")
        self.status_filter_combo.addItem(self.tr("ap_group_filter_status_ok"), "ok")
        self.status_filter_combo.currentIndexChanged.connect(self.render_rows)
        add_filter_pair(filter_row, self, self.tr("ap_group_filter_status"), self.status_filter_combo, 146)

        self.role_filter_combo = QComboBox()
        self.role_filter_combo.addItem(self.tr("ap_group_filter_role_all"), "all")
        for role in AP_ROLE_CHOICES:
            self.role_filter_combo.addItem(self.tr(f"ap_group_role_{role}"), role)
        self.role_filter_combo.currentIndexChanged.connect(self.render_rows)
        add_filter_pair(filter_row, self, self.tr("ap_group_filter_role"), self.role_filter_combo, 146)

        self.band_filter_combo = QComboBox()
        self.band_filter_combo.addItem(self.tr("ap_group_filter_band_all"), "all")
        for band in self.available_filter_bands():
            self.band_filter_combo.addItem(format_band_label(band), band)
        self.band_filter_combo.currentIndexChanged.connect(self.render_rows)
        add_filter_pair(filter_row, self, self.tr("ap_group_filter_band"), self.band_filter_combo, 132)

        self.state_filter_combo = QComboBox()
        self.state_filter_combo.addItem(self.tr("ap_group_filter_state_all"), "all")
        self.state_filter_combo.addItem(self.tr("ap_group_state_manual"), "manual")
        self.state_filter_combo.addItem(self.tr("ap_group_state_auto"), "auto")
        self.state_filter_combo.addItem(self.tr("ap_group_state_memory"), "memory")
        self.state_filter_combo.addItem(self.tr("ap_group_state_memory_update"), "memory_update")
        self.state_filter_combo.currentIndexChanged.connect(self.render_rows)
        add_filter_pair(filter_row, self, self.tr("ap_group_filter_state"), self.state_filter_combo, 132)

        self.clear_filters_button = QPushButton(self.tr("ap_group_clear_filters"))
        self.clear_filters_button.clicked.connect(self.clear_filters)
        self.prepare_action_button(self.clear_filters_button)
        filter_row.addWidget(self.clear_filters_button)
        filter_row.addStretch(1)
        self.visible_count_label = QLabel()
        self.visible_count_label.setObjectName("apDialogLabel")
        filter_row.addWidget(self.visible_count_label)
        layout.addLayout(filter_row)

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
        self.bssid_management_button = QPushButton(self.tr("ap_group_bssid_management"))
        self.conflict_button = QPushButton(self.tr("ap_group_conflict_details"))
        self.confirm_memory_button = QPushButton(self.tr("ap_group_confirm_memory"))
        self.update_memory_button = QPushButton(self.tr("ap_group_update_from_memory"))
        self.alias_button = QPushButton(self.tr("ap_group_set_alias"))
        self.delete_alias_button = QPushButton(self.tr("ap_group_delete_alias"))
        self.role_button = QPushButton(self.tr("ap_group_set_role"))
        self.metadata_button = QPushButton(self.tr("ap_group_metadata"))
        self.position_button = QPushButton(self.tr("ap_group_set_position"))
        self.save_button = QPushButton(self.tr("save"))
        self.cancel_button = QPushButton(self.tr("cancel"))

        self.reset_button.clicked.connect(self.reset_groups_to_auto)
        self.bssid_management_button.clicked.connect(self.open_bssid_group_dialog_for_selected_group)
        self.conflict_button.clicked.connect(self.open_conflict_dialog_for_selected_group)
        self.confirm_memory_button.clicked.connect(self.confirm_memory_for_selected_group)
        self.update_memory_button.clicked.connect(self.update_from_memory_for_selected_group)
        self.alias_button.clicked.connect(self.prompt_alias_for_selected_group)
        self.delete_alias_button.clicked.connect(self.delete_alias_for_selected_group)
        self.role_button.clicked.connect(self.prompt_role_for_selected_group)
        self.metadata_button.clicked.connect(self.open_metadata_dialog_for_selected_group)
        self.position_button.clicked.connect(self.start_positioning_for_selected_group)
        self.save_button.clicked.connect(self.save_groups)
        self.cancel_button.clicked.connect(self.reject)

        for button in (
            self.reset_button,
            self.bssid_management_button,
            self.conflict_button,
            self.confirm_memory_button,
            self.update_memory_button,
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
            QWidget#apFilterPair {{
                background: transparent;
            }}
            QLineEdit, QComboBox {{
                background: {palette["panel"]};
                color: {palette["text"]};
                border: 1px solid {palette["border"]};
                border-radius: {s(5)}px;
                padding: {s(6)}px {s(8)}px;
            }}
            QComboBox::drop-down {{
                width: {s(24)}px;
                border: 0;
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
            {build_scrollbar_stylesheet(palette, s)}
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
            0: (42, 56),
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
        seen_bands = set()
        display_groups = set()
        for bssid in group.get("bssids", []):
            detected_group = self.detected_by_bssid.get(bssid)
            if not detected_group:
                continue
            seen_ssids.update(detected_group["ssids"])
            seen_channels.update(detected_group["channels"])
            seen_bands.update(detected_group.get("bands", []))
            display_groups.update(detected_group["display_groups"])

        group["ssids"] = sorted(seen_ssids)
        group["channels"] = sorted(seen_channels, key=self.app.channel_sort_key)
        group["bands"] = sort_bands(seen_bands)
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
        status_filter = self.current_combo_value(self.status_filter_combo)
        role_filter = self.current_combo_value(self.role_filter_combo)
        band_filter = self.current_combo_value(self.band_filter_combo)
        state_filter = self.current_combo_value(self.state_filter_combo)
        visible_groups = [
            group
            for group in self.groups
            if self.group_matches_filters(group, query, status_filter, role_filter, band_filter, state_filter)
        ]
        visible_groups.sort(key=lambda group: self.sort_value(group, self.sort_column), reverse=self.sort_reverse)
        self.visible_group_ids = [group["group_id"] for group in visible_groups]

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
                    item.setToolTip(self.format_group_status_tooltip(group))
                    if self.group_has_memory_update(group):
                        font = item.font()
                        font.setStrikeOut(True)
                        item.setFont(font)
                self.table.setItem(row, column, item)
            if group["group_id"] == selected_group_id:
                self.table.selectRow(row)
            self.table.setRowHeight(row, self.row_height_for_values(values))

        self.apply_table_column_widths()
        self.update_visible_count_label()
        self.update_action_state()

    def get_group_display_values(self, group):
        role = normalize_ap_role(group.get("role"))
        position = group.get("position") or {}
        position_label = f"{position.get('x')}, {position.get('y')}" if position else "-"
        return (
            self.format_group_status(group),
            format_multiline_list(group["display_groups"]),
            group.get("alias", ""),
            self.tr(f"ap_group_role_{role}"),
            position_label,
            format_metadata_preview(group.get("metadata")),
            format_multiline_list(group["bssids"]),
            format_multiline_list(group["ssids"]),
            ", ".join(group["channels"]),
            self.format_group_management_state(group),
        )

    def format_group_management_state(self, group):
        if group_has_memory_flag(group):
            return self.tr("ap_group_state_memory")
        if self.group_has_memory_update(group):
            return self.tr("ap_group_state_memory_update")
        return self.tr("ap_group_state_manual") if group.get("locked") else self.tr("ap_group_state_auto")

    def format_group_status(self, group):
        status = []
        if self.group_conflicts_by_id.get(group["group_id"]):
            status.append("!")
        if group_has_memory_flag(group):
            status.append("M")
        elif self.group_has_memory_update(group):
            status.append("M")
        return " ".join(status)

    def format_group_status_tooltip(self, group):
        lines = []
        if self.group_conflicts_by_id.get(group["group_id"]):
            lines.append(self.tr("ap_group_status_warning_tooltip"))
        if group_has_memory_flag(group):
            lines.append(self.tr("ap_group_status_memory_tooltip"))
        elif self.group_has_memory_update(group):
            fields = ", ".join(self.memory_update_fields(group))
            lines.append(self.tr("ap_group_status_memory_update_tooltip", fields=fields))
        return "\n".join(lines)

    def memory_update_fields(self, group):
        return get_group_memory_update_fields(
            group,
            self.session.metadata.get("map_file", ""),
            records=self.memory_records,
        )

    def group_has_memory_update(self, group):
        return bool(self.memory_update_fields(group))

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
            self.tr("ap_group_state_memory") if group_has_memory_flag(group) else "",
            self.tr("ap_group_state_memory_update") if self.group_has_memory_update(group) else "",
        ]).lower()
        return query in haystack

    def group_matches_filters(self, group, query, status_filter, role_filter, band_filter, state_filter):
        if not self.group_matches_search(group, query):
            return False

        has_warning = bool(self.group_conflicts_by_id.get(group["group_id"]))
        if status_filter == "warning" and not has_warning:
            return False
        if status_filter == "ok" and has_warning:
            return False
        if role_filter != "all" and normalize_ap_role(group.get("role")) != role_filter:
            return False
        if band_filter != "all" and band_filter not in group.get("bands", []):
            return False
        has_memory = group_has_memory_flag(group)
        has_memory_update = self.group_has_memory_update(group)
        if state_filter == "manual" and (not group.get("locked") or has_memory or has_memory_update):
            return False
        if state_filter == "auto" and group.get("locked"):
            return False
        if state_filter == "memory" and not has_memory:
            return False
        if state_filter == "memory_update" and not has_memory_update:
            return False
        return True

    def current_combo_value(self, combo):
        return combo.currentData() if combo.currentIndex() >= 0 else "all"

    def available_filter_bands(self):
        bands = set()
        for detected_group in self.detected_by_bssid.values():
            bands.update(detected_group.get("bands", []))
        return sort_bands(bands)

    def clear_filters(self):
        self.search_edit.clear()
        for combo in (
            self.status_filter_combo,
            self.role_filter_combo,
            self.band_filter_combo,
            self.state_filter_combo,
        ):
            combo.setCurrentIndex(0)
        self.render_rows()

    def update_visible_count_label(self):
        self.visible_count_label.setText(
            self.tr("ap_group_visible_count", visible=len(self.visible_group_ids), total=len(self.groups))
        )

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
            if group_has_memory_flag(group):
                return 0
            if self.group_has_memory_update(group):
                return 1
            return 2 if group.get("locked") else 3
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
        self.bssid_management_button.setEnabled(has_group)
        self.alias_button.setEnabled(has_group)
        self.role_button.setEnabled(has_group)
        self.metadata_button.setEnabled(has_group)
        self.position_button.setEnabled(has_group)
        self.delete_alias_button.setEnabled(bool(group and group.get("alias")))
        self.conflict_button.setEnabled(bool(group and self.group_conflicts_by_id.get(group["group_id"])))
        self.confirm_memory_button.setEnabled(bool(group and group_has_memory_flag(group)))
        self.update_memory_button.setEnabled(bool(group and self.group_has_memory_update(group)))

    def set_alias(self, group, value):
        group["alias"] = value.strip()
        group["locked"] = True
        clear_group_memory_flag(group)
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
        clear_group_memory_flag(group)
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
        clear_group_memory_flag(group)
        self.refresh_all_group_details()
        self.render_rows()

    def confirm_memory_for_selected_group(self):
        group = self.require_selected_group()
        if group is None:
            return

        clear_group_memory_flag(group)
        group["locked"] = True
        self.refresh_all_group_details()
        self.render_rows()

    def update_from_memory_for_selected_group(self):
        group = self.require_selected_group()
        if group is None:
            return

        if apply_group_memory_update(
            group,
            self.session.metadata.get("map_file", ""),
            records=self.memory_records,
        ):
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
                AP_MEMORY_APPLIED_KEY: group.get(AP_MEMORY_APPLIED_KEY),
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
            if saved_state.get(AP_MEMORY_APPLIED_KEY):
                group[AP_MEMORY_APPLIED_KEY] = True
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
        previous_bssids_by_group = {
            other_group["group_id"]: set(other_group.get("bssids", []))
            for other_group in self.groups
        }
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
        self.clear_memory_flags_for_changed_membership(previous_bssids_by_group)
        self.refresh_all_group_details()
        self.render_rows()

    def split_bssids_to_new_group(self, source_group_id, bssids):
        selected_bssids = self.normalize_bssid_list(bssids)
        if not selected_bssids:
            QMessageBox.warning(self, self.tr("ap_groups_title"), self.tr("ap_group_bssid_select_rows_required"))
            return False

        source_group = self.get_group_by_id(source_group_id)
        if source_group:
            remaining_source_bssids = [
                bssid for bssid in source_group.get("bssids", []) if normalize_bssid(bssid) not in selected_bssids
            ]
            if not remaining_source_bssids:
                QMessageBox.warning(self, self.tr("ap_groups_title"), self.tr("ap_group_split_source_empty"))
                return False

        new_group_id = build_unique_group_id(
            self.suggest_split_group_id(source_group_id, selected_bssids),
            {str(group.get("group_id", "")) for group in self.groups if str(group.get("group_id", ""))},
        )
        role = normalize_ap_role(source_group.get("role")) if source_group else AP_ROLE_INTERNAL
        previous_bssids_by_group = {
            group["group_id"]: set(group.get("bssids", []))
            for group in self.groups
        }
        self.remove_bssids_from_groups(selected_bssids)
        self.groups.append(build_manual_ap_group(new_group_id, selected_bssids, locked=True, role=role))
        self.clear_memory_flags_for_changed_membership(previous_bssids_by_group)
        self.finish_group_membership_change(new_group_id)
        return True

    def move_bssids_to_group(self, target_group_id, bssids):
        target_group = self.get_group_by_id(target_group_id)
        selected_bssids = self.normalize_bssid_list(bssids)
        if target_group is None or not selected_bssids:
            return False

        previous_bssids_by_group = {
            group["group_id"]: set(group.get("bssids", []))
            for group in self.groups
        }
        self.remove_bssids_from_groups(selected_bssids)
        target_group["bssids"] = sorted(set(target_group.get("bssids", [])) | set(selected_bssids))
        target_group["locked"] = True
        self.clear_memory_flags_for_changed_membership(previous_bssids_by_group)
        self.finish_group_membership_change(target_group_id)
        return True

    def prompt_move_bssids_to_existing_group(self, source_group_id, bssids):
        selected_bssids = self.normalize_bssid_list(bssids)
        if not selected_bssids:
            QMessageBox.warning(self, self.tr("ap_groups_title"), self.tr("ap_group_bssid_select_rows_required"))
            return False

        targets = [
            group
            for group in self.groups
            if group.get("group_id") != source_group_id
        ]
        if not targets:
            QMessageBox.warning(self, self.tr("ap_groups_title"), self.tr("ap_group_move_no_target"))
            return False

        labels_by_group_id = {
            group["group_id"]: self.format_group_choice_label(group)
            for group in targets
        }
        labels = [labels_by_group_id[group["group_id"]] for group in targets]
        label, ok = QInputDialog.getItem(
            self,
            self.tr("ap_group_move_target_title"),
            self.tr("ap_group_move_target_prompt"),
            labels,
            0,
            False,
        )
        if not ok:
            return False

        target_group_id = next(
            group_id
            for group_id, group_label in labels_by_group_id.items()
            if group_label == label
        )
        return self.move_bssids_to_group(target_group_id, selected_bssids)

    def normalize_bssid_list(self, bssids):
        return sorted({
            normalize_bssid(bssid)
            for bssid in bssids
            if normalize_bssid(bssid)
        })

    def remove_bssids_from_groups(self, bssids):
        bssid_set = set(bssids)
        for group in self.groups:
            group["bssids"] = [
                bssid for bssid in group.get("bssids", []) if normalize_bssid(bssid) not in bssid_set
            ]

    def clear_memory_flags_for_changed_membership(self, previous_bssids_by_group):
        for group in self.groups:
            group_id = group.get("group_id")
            previous_bssids = previous_bssids_by_group.get(group_id)
            current_bssids = set(group.get("bssids", []))
            if previous_bssids is None or previous_bssids != current_bssids:
                clear_group_memory_flag(group)

    def finish_group_membership_change(self, selected_group_id=None):
        self.groups = [item for item in self.groups if item.get("bssids")]
        self.groups = merge_new_bssids_into_manual_groups(self.groups, self.session.rows)
        self.refresh_all_group_details()
        self.render_rows()
        if selected_group_id:
            self.select_group_by_id(selected_group_id)

    def suggest_split_group_id(self, source_group_id, selected_bssids):
        detected_group_ids = {
            self.detected_by_bssid.get(bssid, {}).get("ap_group")
            for bssid in selected_bssids
            if self.detected_by_bssid.get(bssid, {}).get("ap_group")
        }
        if len(detected_group_ids) == 1:
            return next(iter(detected_group_ids))
        return f"{source_group_id}-split"

    def format_group_choice_label(self, group):
        alias = str(group.get("alias", "")).strip()
        group_id = str(group.get("group_id", "")).strip()
        bssid_count = len(group.get("bssids", []))
        if alias:
            return self.tr("ap_group_move_target_with_alias", alias=alias, group=group_id, count=bssid_count)
        return self.tr("ap_group_move_target_without_alias", group=group_id, count=bssid_count)

    def select_group_by_id(self, group_id):
        self.table.clearSelection()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == group_id:
                self.table.selectRow(row)
                self.table.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                return True
        return False

    def focus_group_by_id(self, group_id):
        group_id = str(group_id or "")
        if not group_id:
            return False

        self.clear_filters()
        return self.select_group_by_id(group_id)

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

        dialog = ConflictDialog(self, group, conflicts)
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
        groups_changed = self.session.set_ap_groups(self.groups, force_memory_update=True)
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
        self.analysis_channel_combos = {}
        self.observed_channels_by_band = self.build_observed_channels_by_band()
        self.selected_channels_by_band = self.initial_selected_channels_by_band()

        self.setWindowTitle(manager.tr("ap_group_metadata_title"))
        self.resize(widget_px(self, 980), widget_px(self, 560))
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

    def build_observed_channels_by_band(self):
        observed = {band: set() for band, _label in EXPECTED_BAND_OPTIONS}
        bssids = {
            normalize_bssid(bssid)
            for bssid in self.group.get("bssids", [])
            if normalize_bssid(bssid)
        }
        if not bssids:
            return observed

        for row in self.manager.session.rows:
            if normalize_bssid(row.get("bssid", "")) not in bssids:
                continue

            band = get_row_band(row)
            channel = normalize_channel(row.get("channel"))
            if band in observed and channel:
                observed[band].add(channel)

        return {
            band: set(sort_channels(channels, self.manager.app.channel_sort_key))
            for band, channels in observed.items()
        }

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
        analysis_header = self.header_label("ap_group_metadata_analysis_channel")
        analysis_header.setToolTip(self.manager.tr("ap_group_metadata_analysis_channel_hint"))
        section_layout.addWidget(analysis_header, 0, 3)
        section_layout.setColumnStretch(2, 1)
        section_layout.setColumnStretch(3, 0)

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

            combo = QComboBox()
            combo.setToolTip(self.manager.tr("ap_group_metadata_analysis_channel_hint"))
            combo.setMinimumWidth(widget_px(self, 136))
            observed_channels = sort_channels(
                self.observed_channels_by_band.get(band_value, set()),
                self.manager.app.channel_sort_key,
            )
            if observed_channels:
                combo.addItem(self.manager.tr("ap_group_metadata_analysis_channel_auto"), "")
            else:
                combo.addItem(self.manager.tr("ap_group_metadata_analysis_channel_not_observed"), "")
                combo.setEnabled(False)
            for channel in observed_channels:
                combo.addItem(f"CH {channel}", channel)

            field = get_ap_analysis_channel_override_field(band_value)
            current_channel = normalize_ap_analysis_channel_override(self.metadata.get(field, ""))
            if current_channel and current_channel in observed_channels:
                current_index = combo.findData(current_channel)
                if current_index >= 0:
                    combo.setCurrentIndex(current_index)
            self.analysis_channel_combos[band_value] = combo
            section_layout.addWidget(combo, row, 3)

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
        for band, combo in self.analysis_channel_combos.items():
            field = get_ap_analysis_channel_override_field(band)
            if field:
                values[field] = combo.currentData() or ""
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
        self.current_bssids = {normalize_bssid(bssid) for bssid in self.group.get("bssids", [])}
        self.visible_bssids = []

        self.setWindowTitle(manager.tr("ap_group_bssid_title"))
        self.resize(widget_px(self, 1180), widget_px(self, 720))
        self.setMinimumSize(widget_px(self, 980), widget_px(self, 580))
        self.setStyleSheet(manager.styleSheet())
        self.build_ui()
        self.render_items()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(widget_px(self, 14), widget_px(self, 14), widget_px(self, 14), widget_px(self, 14))
        layout.setSpacing(widget_px(self, 10))
        hint = QLabel(self.manager.tr("ap_group_bssid_hint"))
        hint.setObjectName("apDialogHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        if self.focus_bssids:
            focus_hint = QLabel(self.manager.tr("ap_group_bssid_warning_focus_hint"))
            focus_hint.setObjectName("apDialogHint")
            focus_hint.setWordWrap(True)
            layout.addWidget(focus_hint)

        search_row = QHBoxLayout()
        search_row.setSpacing(widget_px(self, 8))
        search_row.addWidget(make_dialog_label(self.manager.tr("ap_alias_search")))
        self.search_edit = QLineEdit()
        self.search_edit.setMinimumHeight(widget_px(self, 34))
        self.search_edit.textChanged.connect(self.render_items)
        search_row.addWidget(self.search_edit, 1)
        layout.addLayout(search_row)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(widget_px(self, 14))
        self.scope_combo = QComboBox()
        self.scope_combo.addItem(self.manager.tr("ap_group_bssid_scope_all"), "all")
        self.scope_combo.addItem(self.manager.tr("ap_group_bssid_scope_current"), "current")
        self.scope_combo.addItem(self.manager.tr("ap_group_bssid_scope_other"), "other")
        self.scope_combo.addItem(self.manager.tr("ap_group_bssid_scope_unassigned"), "unassigned")
        self.scope_combo.addItem(self.manager.tr("ap_group_bssid_scope_checked"), "checked")
        if self.focus_bssids:
            self.scope_combo.addItem(self.manager.tr("ap_group_bssid_scope_warning"), "focus")
        self.scope_combo.currentIndexChanged.connect(self.render_items)
        add_filter_pair(filter_row, self, self.manager.tr("ap_group_bssid_scope"), self.scope_combo, 178)

        self.band_combo = QComboBox()
        self.band_combo.addItem(self.manager.tr("ap_group_bssid_filter_all"), "")
        for band in self.available_bands():
            self.band_combo.addItem(format_band_label(band), band)
        self.band_combo.currentIndexChanged.connect(self.render_items)
        add_filter_pair(filter_row, self, self.manager.tr("band"), self.band_combo, 118)

        self.channel_combo = QComboBox()
        self.channel_combo.addItem(self.manager.tr("ap_group_bssid_filter_all"), "")
        for channel in self.available_channels():
            self.channel_combo.addItem(channel, channel)
        self.channel_combo.currentIndexChanged.connect(self.render_items)
        add_filter_pair(filter_row, self, self.manager.tr("ap_alias_channels"), self.channel_combo, 118)

        self.count_label = QLabel()
        self.count_label.setObjectName("apDialogLabel")
        filter_row.addStretch(1)
        filter_row.addWidget(self.count_label)
        layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(widget_px(self, 8))
        action_row.setContentsMargins(0, widget_px(self, 2), 0, widget_px(self, 2))
        self.select_visible_button = QPushButton(self.manager.tr("ap_group_bssid_select_visible"))
        self.clear_visible_button = QPushButton(self.manager.tr("ap_group_bssid_clear_visible"))
        self.invert_visible_button = QPushButton(self.manager.tr("ap_group_bssid_invert_visible"))
        self.new_group_button = QPushButton(self.manager.tr("ap_group_bssid_new_group_from_rows"))
        self.move_rows_button = QPushButton(self.manager.tr("ap_group_bssid_move_rows"))
        for button in (
            self.select_visible_button,
            self.clear_visible_button,
            self.invert_visible_button,
            self.new_group_button,
            self.move_rows_button,
        ):
            self.manager.prepare_action_button(button)
            action_row.addWidget(button)
        self.select_visible_button.clicked.connect(lambda _checked=False: self.set_visible_checked(True))
        self.clear_visible_button.clicked.connect(lambda _checked=False: self.set_visible_checked(False))
        self.invert_visible_button.clicked.connect(self.invert_visible_checked)
        self.new_group_button.clicked.connect(self.split_selected_rows_to_new_group)
        self.move_rows_button.clicked.connect(self.move_selected_rows_to_existing_group)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.table = QTableWidget(0, 6)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(True)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.update_filter_action_state)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalHeaderLabels([
            "",
            self.manager.tr("ap_alias_bssids"),
            self.manager.tr("ap_alias_ssids"),
            self.manager.tr("band"),
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
        save_button.setObjectName("apDialogPrimaryButton")
        cancel_button.setObjectName("apDialogActionButton")
        self.manager.prepare_action_button(save_button)
        self.manager.prepare_action_button(cancel_button)
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        for bssid in self.detected_by_bssid:
            clean_bssid = normalize_bssid(bssid)
            self.checked_by_bssid[clean_bssid] = clean_bssid in self.current_bssids

    def render_items(self):
        query = self.search_edit.text().strip().lower()
        scope = self.current_combo_value(self.scope_combo)
        band_filter = self.current_combo_value(self.band_combo)
        channel_filter = self.current_combo_value(self.channel_combo)
        self.table.setRowCount(0)
        all_bssids = sorted(
            self.detected_by_bssid.keys(),
            key=lambda bssid: (0 if normalize_bssid(bssid) in self.focus_bssids else 1, bssid),
        )
        self.visible_bssids = []

        for bssid in all_bssids:
            row_data = self.build_bssid_row_data(bssid)
            clean_bssid = normalize_bssid(bssid)
            if not self.bssid_matches_filters(clean_bssid, row_data, query, scope, band_filter, channel_filter):
                continue
            self.visible_bssids.append(clean_bssid)
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
                row_data["bands"],
                row_data["channels"],
                row_data["other_group"],
            ]
            for offset, value in enumerate(values, start=1):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                item.setData(Qt.ItemDataRole.UserRole, clean_bssid)
                if offset in {1, 3, 4, 5}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, offset, item)
            self.table.setRowHeight(row, widget_px(self, 38))

        self.apply_table_column_widths()
        self.update_filter_action_state()

    def set_bssid_checked(self, bssid, checked):
        self.checked_by_bssid[bssid] = bool(checked)

    def set_visible_checked(self, checked):
        for bssid in self.visible_bssids:
            self.checked_by_bssid[bssid] = bool(checked)
        self.render_items()

    def invert_visible_checked(self):
        for bssid in self.visible_bssids:
            self.checked_by_bssid[bssid] = not self.checked_by_bssid.get(bssid, False)
        self.render_items()

    def selected_row_bssids(self):
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        bssids = []
        for row in rows:
            item = self.table.item(row, 1)
            if item:
                bssids.append(item.data(Qt.ItemDataRole.UserRole))
        return sorted({
            normalize_bssid(bssid)
            for bssid in bssids
            if normalize_bssid(bssid)
        })

    def split_selected_rows_to_new_group(self):
        if self.manager.split_bssids_to_new_group(self.group.get("group_id"), self.selected_row_bssids()):
            self.accept()

    def move_selected_rows_to_existing_group(self):
        if self.manager.prompt_move_bssids_to_existing_group(self.group.get("group_id"), self.selected_row_bssids()):
            self.accept()

    def build_bssid_row_data(self, bssid):
        detected_group = self.detected_by_bssid.get(bssid, {})
        ssids = ", ".join(detected_group.get("ssids", [])) or "-"
        bands = ", ".join(format_band_label(band) for band in detected_group.get("bands", [])) or "-"
        channels = ", ".join(detected_group.get("channels", [])) or "-"
        other_group = self.format_other_group_label(bssid)
        return {
            "bssid": bssid,
            "ssids": ssids,
            "bands": bands,
            "channels": channels,
            "other_group": other_group or "-",
            "focus": "!" if normalize_bssid(bssid) in self.focus_bssids else "",
            "_bands": set(detected_group.get("bands", [])),
            "_channels": set(str(channel) for channel in detected_group.get("channels", [])),
        }

    def bssid_matches_filters(self, clean_bssid, row_data, query, scope, band_filter, channel_filter):
        if query:
            haystack = " ".join(
                str(value)
                for key, value in row_data.items()
                if not key.startswith("_")
            ).lower()
            if query not in haystack:
                return False

        if scope == "current" and clean_bssid not in self.current_bssids:
            return False
        if scope == "other" and row_data["other_group"] == "-":
            return False
        if scope == "unassigned" and (clean_bssid in self.current_bssids or row_data["other_group"] != "-"):
            return False
        if scope == "checked" and not self.checked_by_bssid.get(clean_bssid, False):
            return False
        if scope == "focus" and clean_bssid not in self.focus_bssids:
            return False
        if band_filter and band_filter not in row_data["_bands"]:
            return False
        if channel_filter and channel_filter not in row_data["_channels"]:
            return False
        return True

    def current_combo_value(self, combo):
        return combo.currentData() if combo.currentIndex() >= 0 else ""

    def available_bands(self):
        bands = set()
        for detected_group in self.detected_by_bssid.values():
            bands.update(detected_group.get("bands", []))
        return sorted(bands)

    def available_channels(self):
        channels = {
            str(channel)
            for detected_group in self.detected_by_bssid.values()
            for channel in detected_group.get("channels", [])
            if str(channel)
        }
        return sorted(channels, key=self.manager.app.channel_sort_key)

    def update_filter_action_state(self):
        visible_count = len(self.visible_bssids)
        total_count = len(self.detected_by_bssid)
        self.count_label.setText(
            self.manager.tr("ap_group_bssid_visible_count", visible=visible_count, total=total_count)
        )
        enabled = bool(self.visible_bssids)
        self.select_visible_button.setEnabled(enabled)
        self.clear_visible_button.setEnabled(enabled)
        self.invert_visible_button.setEnabled(enabled)
        has_row_selection = bool(self.selected_row_bssids()) if hasattr(self, "table") else False
        self.new_group_button.setEnabled(has_row_selection)
        self.move_rows_button.setEnabled(has_row_selection)

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
            3: max(widget_px(self, 80), min(self.table.columnWidth(3) + widget_px(self, 18), widget_px(self, 130))),
            4: max(widget_px(self, 92), min(self.table.columnWidth(4) + widget_px(self, 18), widget_px(self, 130))),
            5: max(widget_px(self, 150), min(self.table.columnWidth(5) + widget_px(self, 18), widget_px(self, 260))),
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
    def __init__(self, manager, group, conflicts):
        super().__init__(manager)
        self.manager = manager
        self.group = group
        self.group_id = group.get("group_id", "")
        self.conflicts = conflicts

        self.setWindowTitle(manager.tr("ap_group_conflict_title"))
        self.resize(widget_px(self, 860), widget_px(self, 600))
        self.setStyleSheet(manager.styleSheet())
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        hint = QLabel(self.manager.tr("ap_group_conflict_hint"))
        hint.setObjectName("apDialogHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(self.format_conflicts())
        layout.addWidget(text, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        fix_button = QPushButton(self.manager.tr("ap_group_fix_from_warning"))
        close_button = QPushButton(self.manager.tr("close"))
        fix_button.setObjectName("apDialogPrimaryButton")
        close_button.setObjectName("apDialogActionButton")
        self.manager.prepare_action_button(fix_button)
        self.manager.prepare_action_button(close_button)
        fix_button.clicked.connect(self.accept)
        close_button.clicked.connect(self.reject)
        buttons.addWidget(fix_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def format_conflicts(self):
        lines = [
            self.manager.tr("ap_group_conflict_group", group=self.format_group_label()),
            "",
            self.manager.tr("ap_group_conflict_diagnosis_title"),
            self.manager.tr("ap_group_conflict_diagnosis_body"),
            "",
            self.manager.tr("ap_group_conflict_recommendation_title"),
            self.manager.tr("ap_group_conflict_recommendation_body"),
            "",
            self.manager.tr("ap_group_conflict_details_title"),
        ]
        for conflict in self.conflicts:
            lines.append(self.format_conflict_summary(conflict))
            for channel in conflict.get("channels", []):
                bssids = ", ".join(conflict.get("bssids_by_channel", {}).get(channel, []))
                lines.append(self.manager.tr("ap_group_conflict_channel_row", channel=channel, bssids=bssids))
            lines.append("")
        return "\n".join(lines).strip()

    def format_group_label(self):
        alias = str(self.group.get("alias", "")).strip()
        group_id = str(self.group_id).strip()
        if alias and group_id:
            return f"{alias} ({group_id})"
        return alias or group_id or "-"

    def format_conflict_summary(self, conflict):
        channels = conflict.get("channels", [])
        bssids = {
            bssid
            for channel_bssids in conflict.get("bssids_by_channel", {}).values()
            for bssid in channel_bssids
        }
        return self.manager.tr(
            "ap_group_conflict_band_summary",
            band=format_band_label(conflict.get("band", "")),
            channel_count=len(channels),
            bssid_count=len(bssids),
            channels=", ".join(channels),
        )


def format_multiline_list(values):
    clean_values = [str(value) for value in values if str(value)]
    return "\n".join(clean_values) if clean_values else "-"


def format_metadata_preview(metadata):
    metadata = normalize_ap_metadata(metadata)
    vendor_model = " ".join(value for value in (metadata.get("vendor"), metadata.get("model")) if value)
    if vendor_model:
        return vendor_model
    for field in ("mounting", "expected_bands", "expected_channels"):
        if metadata.get(field):
            return metadata[field]
    for band, field in AP_ANALYSIS_CHANNEL_OVERRIDE_FIELDS:
        if metadata.get(field):
            return f"{format_band_label(band)} CH {metadata[field]}"
    if metadata.get("notes"):
        return metadata["notes"]
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
