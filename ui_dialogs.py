import os
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

import ttkbootstrap as ttk
from ttkbootstrap.constants import INFO, PRIMARY, SECONDARY
from constants import CSV_PREFIX
from i18n import translate


def create_new_survey_file():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.abspath(f"{CSV_PREFIX}_{timestamp}.csv")


def save_survey_file_as(parent, initial_file=None):
    csv_file = filedialog.asksaveasfilename(
        parent=parent,
        title="Salva rilievo",
        initialfile=os.path.basename(initial_file) if initial_file else None,
        defaultextension=".csv",
        filetypes=[
            ("CSV rilievo Wi-Fi", "*.csv"),
            ("Tutti i file", "*.*")
        ]
    )

    if not csv_file:
        return None

    return csv_file


def open_existing_survey_file(parent):
    csv_file = filedialog.askopenfilename(
        parent=parent,
        title="Apri rilievo esistente",
        filetypes=[
            ("CSV rilievo Wi-Fi", "*.csv"),
            ("Tutti i file", "*.*")
        ]
    )

    if not csv_file:
        return None

    return csv_file


def choose_survey_file(root):
    start_new = messagebox.askyesnocancel(
        "Rilievo Wi-Fi",
        "Vuoi iniziare un nuovo rilievo?\n\n"
        "Si: crea un nuovo CSV per questa sessione.\n"
        "No: apri un CSV esistente.\n"
        "Annulla: chiudi il programma.",
        parent=root
    )

    if start_new is None:
        return None

    if start_new:
        return create_new_survey_file()

    return open_existing_survey_file(root)
def ask_capture_ssid_filter(parent, networks, connected_ssid=None, remembered_choice=None, language="it"):
    dialog = tk.Toplevel(parent)
    dialog.title(translate(language, "networks_to_save"))
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    ssids = sorted({network["ssid"] for network in networks if network.get("ssid")})
    default_value = get_default_ssid_choice(ssids, connected_ssid, remembered_choice)
    selected_value = tk.StringVar(value=default_value)
    remember_var = tk.BooleanVar(value=remembered_choice is not None)
    result = {"value": None, "remember": False}

    frame = ttk.Frame(dialog, padding=12)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text=translate(language, "detected_networks_count", count=len(networks))).pack(anchor="w")

    if connected_ssid:
        ttk.Label(
            frame,
            text=translate(language, "connected_network", ssid=connected_ssid),
            bootstyle=INFO
        ).pack(anchor="w", pady=(4, 0))

    all_frame = ttk.Frame(frame)
    all_frame.pack(fill=tk.X, pady=(10, 0))
    ttk.Radiobutton(
        all_frame,
        text=translate(language, "all_networks"),
        value="",
        variable=selected_value
    ).pack(anchor="w")

    ttk.Separator(frame).pack(fill=tk.X, pady=(8, 8))

    networks_frame = ttk.Frame(frame)
    networks_frame.pack(fill=tk.X)

    for ssid in ssids:
        label = ssid
        if connected_ssid and ssid.lower() == connected_ssid.lower():
            label = translate(language, "connected_ssid_option", ssid=ssid)

        ttk.Radiobutton(
            networks_frame,
            text=label,
            value=ssid,
            variable=selected_value
        ).pack(anchor="w", pady=1)

    ttk.Checkbutton(
        frame,
        text=translate(language, "remember_choice"),
        variable=remember_var
    ).pack(anchor="w", pady=(12, 0))

    buttons = ttk.Frame(frame)
    buttons.pack(fill=tk.X, pady=(12, 0))

    def confirm():
        result["value"] = selected_value.get()
        result["remember"] = remember_var.get()
        dialog.destroy()

    def cancel():
        result["value"] = None
        result["remember"] = False
        dialog.destroy()

    ttk.Button(buttons, text=translate(language, "cancel"), command=cancel, bootstyle=SECONDARY).pack(side=tk.RIGHT)
    ttk.Button(buttons, text=translate(language, "save"), command=confirm, bootstyle=PRIMARY).pack(side=tk.RIGHT, padx=(0, 6))

    dialog.bind("<Return>", lambda _event: confirm())
    dialog.bind("<Escape>", lambda _event: cancel())
    center_dialog(parent, dialog)
    parent.wait_window(dialog)
    return result


def get_default_ssid_choice(ssids, connected_ssid=None, remembered_choice=None):
    if connected_ssid:
        for ssid in ssids:
            if ssid.lower() == connected_ssid.lower():
                return ssid

    if remembered_choice is not None:
        if remembered_choice == "":
            return ""

        for ssid in ssids:
            if ssid.lower() == remembered_choice.lower():
                return ssid

    return ""


def center_dialog(parent, dialog):
    dialog.update_idletasks()
    parent_x = parent.winfo_rootx()
    parent_y = parent.winfo_rooty()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()
    dialog_width = dialog.winfo_width()
    dialog_height = dialog.winfo_height()

    if parent_width <= 1 or parent_height <= 1:
        parent_x = 0
        parent_y = 0
        parent_width = parent.winfo_screenwidth()
        parent_height = parent.winfo_screenheight()

    x = parent_x + max(0, (parent_width - dialog_width) // 2)
    y = parent_y + max(0, (parent_height - dialog_height) // 2)
    dialog.geometry(f"+{x}+{y}")
    bring_dialog_to_front(dialog)


def bring_dialog_to_front(dialog):
    if not dialog or not dialog.winfo_exists():
        return

    dialog.deiconify()
    dialog.lift()
    try:
        dialog.attributes("-topmost", True)
        dialog.after(150, lambda: dialog.winfo_exists() and dialog.attributes("-topmost", False))
    except tk.TclError:
        pass
    dialog.focus_force()
