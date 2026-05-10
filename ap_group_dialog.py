import tkinter as tk
from tkinter import messagebox, simpledialog

import ttkbootstrap as ttk
from ttkbootstrap.constants import DANGER, INFO, PRIMARY, SECONDARY, WARNING

from ap_groups import (
    build_default_manual_groups,
    build_detected_ap_groups,
    merge_new_bssids_into_manual_groups,
)


AP_GROUP_COLUMNS = ("status", "group", "alias", "position", "bssids", "ssids", "channels", "locked")


def open_ap_group_manager(app):
    dialog = app.create_modal_dialog(app.tr("ap_groups_title"))
    dialog.geometry("1560x780")
    dialog.minsize(1320, 700)

    frame = ttk.Frame(dialog, padding=12)
    frame.pack(fill=tk.BOTH, expand=True)
    ttk.Label(
        frame,
        text=app.tr("ap_groups_hint"),
        wraplength=1460,
        style="ReadableMuted.TLabel"
    ).pack(anchor="w", pady=(0, 10))

    detected_groups = build_detected_ap_groups(app.session.rows, app.channel_sort_key)
    aliases = app.session.get_ap_aliases()
    saved_groups = app.session.get_ap_groups()
    groups = (
        merge_new_bssids_into_manual_groups(saved_groups, app.session.rows)
        if saved_groups
        else build_default_manual_groups(app.session.rows)
    )
    detected_by_bssid = {
        bssid: detected_group
        for detected_group in detected_groups
        for bssid in detected_group["bssids"]
    }

    def refresh_group_details(group):
        group["alias"] = group.get("alias") or aliases.get(group["group_id"], "")
        seen_ssids = set()
        seen_channels = set()
        display_groups = set()
        for bssid in group.get("bssids", []):
            detected_group = detected_by_bssid.get(bssid)
            if not detected_group:
                continue
            seen_ssids.update(detected_group["ssids"])
            seen_channels.update(detected_group["channels"])
            display_groups.update(detected_group["display_groups"])
        group["ssids"] = sorted(seen_ssids)
        group["channels"] = sorted(seen_channels, key=app.channel_sort_key)
        group["display_groups"] = sorted(display_groups) or [group["group_id"]]

    def refresh_all_group_details():
        for group in groups:
            refresh_group_details(group)

    refresh_all_group_details()

    def reset_groups_to_auto():
        if not messagebox.askyesno(
            app.tr("ap_groups_reset_title"),
            app.tr("ap_groups_reset_confirm"),
            parent=dialog
        ):
            return

        aliases_by_group = {
            group["group_id"]: group.get("alias", "")
            for group in groups
            if group.get("alias", "")
        }
        groups[:] = build_default_manual_groups(app.session.rows)
        for group in groups:
            group["alias"] = aliases_by_group.get(group["group_id"], aliases.get(group["group_id"], ""))
            group["locked"] = False
        refresh_all_group_details()
        render_alias_rows()
        schedule_alias_table_resize()

    if not groups:
        ttk.Label(frame, text=app.tr("ap_aliases_empty"), bootstyle=WARNING).pack(anchor="w")
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        app.center_dialog(dialog)
        return

    search_frame = ttk.Frame(frame)
    search_frame.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(search_frame, text=app.tr("ap_alias_search")).pack(side=tk.LEFT)
    search_var = tk.StringVar(value="")
    search_entry = ttk.Entry(search_frame, textvariable=search_var, width=42)
    search_entry.pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)
    alias_action_buttons = {"delete": None}

    table_frame = ttk.Frame(frame)
    table_frame.pack(fill=tk.BOTH, expand=True)
    tree = ttk.Treeview(table_frame, columns=AP_GROUP_COLUMNS, show="headings", height=16)
    tree.column("status", width=42, minwidth=36, anchor="center", stretch=False)
    tree.column("group", width=270, minwidth=210, anchor="w", stretch=True)
    tree.column("alias", width=230, minwidth=170, anchor="w", stretch=True)
    tree.column("position", width=120, minwidth=100, anchor="center", stretch=False)
    tree.column("bssids", width=390, minwidth=250, anchor="w", stretch=True)
    tree.column("ssids", width=320, minwidth=210, anchor="w", stretch=True)
    tree.column("channels", width=120, minwidth=90, anchor="center", stretch=False)
    tree.column("locked", width=110, minwidth=90, anchor="center", stretch=False)
    tree.tag_configure("aliased", background="#e9f7ef")
    scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(0, weight=1)

    sort_state = {"column": "ssids", "reverse": False}

    def format_list_preview(values, limit=2):
        clean_values = [str(value) for value in values if str(value)]
        if len(clean_values) <= limit:
            return ", ".join(clean_values)

        return f"{', '.join(clean_values[:limit])} (+{len(clean_values) - limit})"

    def get_group_display_values(group):
        alias = group.get("alias", "")
        position = group.get("position") or {}
        position_label = f"{position.get('x')}, {position.get('y')}" if position else "-"
        return (
            "OK" if alias else "",
            format_list_preview(group["display_groups"]),
            alias,
            position_label,
            format_list_preview(group["bssids"]),
            ", ".join(group["ssids"]),
            ", ".join(group["channels"]),
            app.tr("yes") if group.get("locked") else app.tr("no"),
        )

    def group_matches_search(group, query):
        if not query:
            return True

        alias = group.get("alias", "")
        position = group.get("position") or {}
        position_text = f"{position.get('x', '')} {position.get('y', '')}" if position else ""
        haystack = " ".join([
            group["group_id"],
            " ".join(group["display_groups"]),
            alias,
            position_text,
            " ".join(group["bssids"]),
            " ".join(group["ssids"]),
            " ".join(group["channels"]),
        ]).lower()
        return query.lower() in haystack

    def sort_value(group, column):
        alias = group.get("alias", "")
        if column == "status":
            return 0 if alias else 1
        if column == "alias":
            return alias.lower()
        if column == "position":
            position = group.get("position") or {}
            return (position.get("x", 999999), position.get("y", 999999))
        if column == "bssids":
            return " ".join(group["bssids"]).lower()
        if column == "ssids":
            return " ".join(group["ssids"]).lower()
        if column == "channels":
            return [app.channel_sort_key(channel) for channel in group["channels"]]
        if column == "locked":
            return 0 if group.get("locked") else 1
        return " ".join(group["display_groups"]).lower()

    def render_alias_rows():
        query = search_var.get().strip()
        selected_group = tree.selection()[0] if tree.selection() else ""
        visible_groups = [
            group
            for group in groups
            if group_matches_search(group, query)
        ]
        visible_groups.sort(
            key=lambda group: sort_value(group, sort_state["column"]),
            reverse=sort_state["reverse"]
        )
        tree.delete(*tree.get_children())
        for group in visible_groups:
            tree.insert(
                "",
                tk.END,
                iid=group["group_id"],
                tags=("aliased",) if group.get("alias") else (),
                values=get_group_display_values(group)
            )
        if selected_group and tree.exists(selected_group):
            tree.selection_set(selected_group)
        update_alias_action_state()

    def get_selected_group_key(show_warning=True):
        selection = tree.selection()
        if not selection:
            if show_warning:
                messagebox.showwarning(
                    app.tr("ap_groups_title"),
                    app.tr("ap_group_select_group"),
                    parent=dialog
                )
            return ""

        return selection[0]

    def get_group_by_key(group_key):
        return next((item for item in groups if item["group_id"] == group_key), None)

    def update_alias_action_state(_event=None):
        delete_button = alias_action_buttons.get("delete")
        if delete_button is None:
            return

        group_key = get_selected_group_key(show_warning=False)
        group = get_group_by_key(group_key) if group_key else None
        delete_button.configure(
            state=tk.NORMAL if group and group.get("alias", "") else tk.DISABLED
        )

    def sort_by_column(column):
        if column == "status":
            sort_state["column"] = column
            sort_state["reverse"] = False
        elif sort_state["column"] == column:
            sort_state["reverse"] = not sort_state["reverse"]
        else:
            sort_state["column"] = column
            sort_state["reverse"] = False
        render_alias_rows()

    tree.heading("status", text="", command=lambda: sort_by_column("status"))
    tree.heading("group", text=app.tr("ap_alias_group"), command=lambda: sort_by_column("group"))
    tree.heading("alias", text=app.tr("ap_alias_value"), command=lambda: sort_by_column("alias"))
    tree.heading("position", text=app.tr("ap_group_position"), command=lambda: sort_by_column("position"))
    tree.heading("bssids", text=app.tr("ap_alias_bssids"), command=lambda: sort_by_column("bssids"))
    tree.heading("ssids", text=app.tr("ap_alias_ssids"), command=lambda: sort_by_column("ssids"))
    tree.heading("channels", text=app.tr("ap_alias_channels"), command=lambda: sort_by_column("channels"))
    tree.heading("locked", text=app.tr("ap_group_locked"), command=lambda: sort_by_column("locked"))
    search_entry.bind("<KeyRelease>", lambda _event: render_alias_rows())

    def schedule_alias_table_resize(_event=None):
        if app.alias_table_resize_after_id is not None:
            app.root.after_cancel(app.alias_table_resize_after_id)

        app.alias_table_resize_after_id = app.root.after(
            50,
            lambda: adjust_ap_group_table_columns(app, tree, AP_GROUP_COLUMNS)
        )

    def set_alias(group_key, value):
        value = value.strip()
        for group in groups:
            if group["group_id"] == group_key:
                group["alias"] = value
                group["locked"] = True
                break

        current_values = list(tree.item(group_key, "values"))
        current_values[0] = "OK" if value else ""
        current_values[2] = value
        current_values[7] = app.tr("yes")
        tree.item(group_key, values=current_values)
        tree.item(group_key, tags=("aliased",) if value else ())
        update_alias_action_state()

    def prompt_alias_for_selected_group():
        group_key = get_selected_group_key()
        if not group_key:
            return

        group = get_group_by_key(group_key) or {}
        value = simpledialog.askstring(
            app.tr("ap_group_alias_title"),
            app.tr("ap_group_alias_prompt"),
            initialvalue=group.get("alias", ""),
            parent=dialog
        )
        if value is None:
            return

        set_alias(group_key, value)

    def delete_alias_for_selected_group():
        group_key = get_selected_group_key()
        if not group_key:
            return

        group = get_group_by_key(group_key)
        if not group or not group.get("alias", ""):
            return

        if not messagebox.askyesno(
            app.tr("ap_group_delete_alias_title"),
            app.tr("ap_group_delete_alias_confirm"),
            parent=dialog
        ):
            return

        set_alias(group_key, "")

    def open_bssid_group_dialog(group_key):
        group = get_group_by_key(group_key)
        if group is None:
            return

        bssid_dialog = app.create_modal_dialog(app.tr("ap_group_bssid_title"))
        bssid_dialog.geometry("980x700")
        bssid_dialog.minsize(900, 620)

        content = ttk.Frame(bssid_dialog, padding=12)
        content.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            content,
            text=app.tr("ap_group_bssid_hint"),
            wraplength=920,
            style="ReadableMuted.TLabel"
        ).pack(anchor="w", pady=(0, 10))

        bssid_search_frame = ttk.Frame(content)
        bssid_search_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(bssid_search_frame, text=app.tr("ap_alias_search")).pack(side=tk.LEFT)
        bssid_search_var = tk.StringVar(value="")
        bssid_search_entry = ttk.Entry(bssid_search_frame, textvariable=bssid_search_var, width=56)
        bssid_search_entry.pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)

        list_frame = ttk.Frame(content)
        list_frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        checks_frame = ttk.Frame(canvas)
        checks_frame.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=checks_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        current_bssids = set(group.get("bssids", []))
        bssid_vars = {}
        assigned_groups = {
            bssid: item
            for item in groups
            for bssid in item.get("bssids", [])
        }
        all_bssids = sorted(detected_by_bssid.keys())
        for bssid in all_bssids:
            bssid_vars[bssid] = tk.BooleanVar(value=bssid in current_bssids)

        def format_assigned_label(bssid):
            assigned_group = assigned_groups.get(bssid, {})
            assigned_alias = assigned_group.get("alias", "")
            assigned_group_id = assigned_group.get("group_id", "")
            if not assigned_group_id:
                return "-"
            if assigned_group_id == group_key:
                return ""
            return assigned_alias or assigned_group_id

        def render_bssid_checks(_event=None):
            query = bssid_search_var.get().strip().lower()
            for child in checks_frame.winfo_children():
                child.destroy()

            for bssid in all_bssids:
                detected_group = detected_by_bssid.get(bssid, {})
                ssids = ", ".join(detected_group.get("ssids", [])) or "-"
                channels = ", ".join(detected_group.get("channels", [])) or "-"
                assigned_label = format_assigned_label(bssid)
                if assigned_label:
                    label = app.tr(
                        "ap_group_bssid_row_with_group",
                        bssid=bssid,
                        ssids=ssids,
                        channels=channels,
                        group=assigned_label
                    )
                else:
                    label = app.tr(
                        "ap_group_bssid_row",
                        bssid=bssid,
                        ssids=ssids,
                        channels=channels
                    )
                if query and query not in label.lower():
                    continue

                ttk.Checkbutton(
                    checks_frame,
                    text=label,
                    variable=bssid_vars[bssid]
                ).pack(anchor="w", pady=2)

        bssid_search_entry.bind("<KeyRelease>", render_bssid_checks)
        render_bssid_checks()

        def apply_bssid_selection():
            selected_bssids = sorted([
                bssid
                for bssid, var in bssid_vars.items()
                if var.get()
            ])
            if not selected_bssids:
                messagebox.showwarning(
                    app.tr("ap_groups_title"),
                    app.tr("ap_group_empty_selection"),
                    parent=bssid_dialog
                )
                return

            selected_set = set(selected_bssids)
            for other_group in groups:
                if other_group["group_id"] == group_key:
                    other_group["bssids"] = selected_bssids
                    other_group["locked"] = True
                else:
                    other_group["bssids"] = [
                        bssid
                        for bssid in other_group.get("bssids", [])
                        if bssid not in selected_set
                    ]

            groups[:] = [
                item
                for item in groups
                if item.get("bssids")
            ]
            groups[:] = merge_new_bssids_into_manual_groups(groups, app.session.rows)
            refresh_all_group_details()
            render_alias_rows()
            schedule_alias_table_resize()
            bssid_dialog.destroy()

        buttons = ttk.Frame(content)
        buttons.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(buttons, text=app.tr("cancel"), command=bssid_dialog.destroy, bootstyle=SECONDARY).pack(side=tk.RIGHT)
        ttk.Button(buttons, text=app.tr("save"), command=apply_bssid_selection, bootstyle=PRIMARY).pack(side=tk.RIGHT, padx=(0, 8))
        bssid_dialog.bind("<Escape>", lambda _event: bssid_dialog.destroy())
        app.center_dialog(bssid_dialog)

    def start_positioning_for_selected_group():
        group_key = get_selected_group_key()
        if not group_key:
            return

        aliases = {
            group["group_id"]: group.get("alias", "")
            for group in groups
            if group.get("alias", "").strip()
        }
        aliases_changed = app.session.set_ap_aliases(aliases)
        groups_changed = app.session.set_ap_groups(groups)
        if aliases_changed or groups_changed:
            app.session.dirty = True
        app.refresh_session_labels()
        app.schedule_live_update(force=True)
        dialog.destroy()
        app.start_ap_positioning(group_key)

    def save_aliases():
        aliases = {
            group["group_id"]: group.get("alias", "")
            for group in groups
            if group.get("alias", "").strip()
        }
        aliases_changed = app.session.set_ap_aliases(aliases)
        groups_changed = app.session.set_ap_groups(groups)
        if aliases_changed or groups_changed:
            app.session.dirty = True
        app.refresh_session_labels()
        app.schedule_live_update(force=True)
        app.status_var.set(app.tr("ap_groups_saved"))
        dialog.destroy()

    tree.bind("<<TreeviewSelect>>", update_alias_action_state)
    table_frame.bind("<Configure>", schedule_alias_table_resize)
    tree.bind("<Configure>", schedule_alias_table_resize, add="+")
    render_alias_rows()
    schedule_alias_table_resize()
    buttons = ttk.Frame(frame)
    buttons.pack(fill=tk.X, pady=(12, 0))
    ttk.Button(buttons, text=app.tr("cancel"), command=dialog.destroy, bootstyle=SECONDARY).pack(side=tk.RIGHT)
    ttk.Button(buttons, text=app.tr("save"), command=save_aliases, bootstyle=PRIMARY).pack(side=tk.RIGHT, padx=(0, 8))
    ttk.Button(
        buttons,
        text=app.tr("ap_groups_reset_auto"),
        command=reset_groups_to_auto,
        bootstyle=WARNING
    ).pack(side=tk.LEFT)
    ttk.Button(
        buttons,
        text=app.tr("ap_group_split"),
        command=lambda: open_bssid_group_dialog(get_selected_group_key()),
        bootstyle=SECONDARY
    ).pack(side=tk.LEFT, padx=(8, 0))
    ttk.Button(
        buttons,
        text=app.tr("ap_group_set_alias"),
        command=prompt_alias_for_selected_group,
        bootstyle=INFO
    ).pack(side=tk.LEFT, padx=(8, 0))
    delete_alias_button = ttk.Button(
        buttons,
        text=app.tr("ap_group_delete_alias"),
        command=delete_alias_for_selected_group,
        bootstyle=DANGER,
        state=tk.DISABLED
    )
    delete_alias_button.pack(side=tk.LEFT, padx=(8, 0))
    ttk.Separator(buttons, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=(12, 8))
    ttk.Button(
        buttons,
        text=app.tr("ap_group_set_position"),
        command=start_positioning_for_selected_group,
        bootstyle=PRIMARY
    ).pack(side=tk.LEFT)
    alias_action_buttons["delete"] = delete_alias_button
    update_alias_action_state()
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    app.center_dialog(dialog)


def adjust_ap_group_table_columns(app, tree, columns):
    app.alias_table_resize_after_id = None

    if not tree.winfo_exists():
        return

    body_font = app.get_treeview_font("Treeview")
    heading_font = app.get_treeview_font("Treeview.Heading")
    min_widths = {
        "status": 38,
        "group": 220,
        "alias": 180,
        "position": 100,
        "bssids": 260,
        "ssids": 220,
        "channels": 92,
        "locked": 90,
    }
    max_widths = {
        "status": 46,
        "group": 420,
        "alias": 360,
        "position": 130,
        "bssids": 620,
        "ssids": 440,
        "channels": 140,
        "locked": 120,
    }
    measured = {}

    for column in columns:
        heading = tree.heading(column).get("text", "")
        measured[column] = max(min_widths[column], heading_font.measure(str(heading)) + 28)

    for item in tree.get_children():
        values = tree.item(item, "values")
        for column, value in zip(columns, values):
            measured[column] = max(measured[column], body_font.measure(str(value)) + 34)

    fixed_columns = ("status", "position", "channels", "locked")
    flexible_columns = ("group", "alias", "bssids", "ssids")
    widths = {
        column: min(max(measured[column], min_widths[column]), max_widths[column])
        for column in columns
    }
    available_width = max(0, tree.winfo_width() - 8)
    fixed_total = sum(widths[column] for column in fixed_columns)
    flexible_min_total = sum(min_widths[column] for column in flexible_columns)
    flexible_available = max(flexible_min_total, available_width - fixed_total)
    desired_flexible_total = sum(widths[column] for column in flexible_columns)

    if desired_flexible_total > flexible_available:
        scale = flexible_available / desired_flexible_total
        for column in flexible_columns:
            widths[column] = max(min_widths[column], int(widths[column] * scale))
    elif desired_flexible_total < flexible_available:
        extra = flexible_available - desired_flexible_total
        priority = ("bssids", "ssids", "group", "alias")
        for column in priority:
            room = max_widths[column] - widths[column]
            added = min(room, extra)
            widths[column] += added
            extra -= added
            if extra <= 0:
                break

    for column in columns:
        tree.column(
            column,
            width=widths[column],
            minwidth=min_widths[column],
            stretch=column in flexible_columns
        )
