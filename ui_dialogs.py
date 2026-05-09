import os
from tkinter import filedialog, messagebox
from datetime import datetime

from constants import CSV_PREFIX


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
