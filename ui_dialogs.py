import os
from tkinter import filedialog


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
