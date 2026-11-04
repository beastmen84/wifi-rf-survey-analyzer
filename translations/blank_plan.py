"""Blank-sheet dimensions and the drawing toolbar shell, EN/IT/FR/ES."""

LANGUAGES = ("en", "it", "fr", "es")
TEXT = {
    "blank_plan_size": ("Blank sheet", "Foglio bianco", "Feuille vierge", "Hoja en blanco"),
    "blank_plan_width": ("Width", "Larghezza", "Largeur", "Ancho"),
    "blank_plan_height": ("Height", "Altezza", "Hauteur", "Alto"),
    "blank_plan_size_hint": (
        "Choose the size of the gridded sheet. Loading a floor plan replaces this sheet and uses its own calibration.",
        "Scegli le dimensioni del foglio con griglia. Caricando una planimetria, il foglio viene sostituito e si usa la sua calibrazione.",
        "Choisissez les dimensions de la feuille quadrillée. Un plan chargé remplace cette feuille et utilise son propre étalonnage.",
        "Elige el tamaño de la hoja cuadriculada. Al cargar un plano se sustituye esta hoja y se usa su propia calibración."),
    "blank_tools": ("Draw", "Disegna", "Dessiner", "Dibujar"),
    "blank_tools_hint": ("Blank-sheet drawing tools", "Strumenti per il foglio bianco", "Outils pour la feuille vierge", "Herramientas de la hoja en blanco"),
    "blank_tool_rectangle": ("Rectangle", "Rettangolo", "Rectangle", "Rectángulo"),
    "blank_tool_eraser": ("Erase a segment", "Cancella segmento", "Effacer un segment", "Borrar segmento"),
    "blank_tool_undo": ("Undo", "Annulla", "Annuler", "Deshacer"),
    "blank_tool_redo": ("Redo", "Ripristina", "Rétablir", "Rehacer"),
    "blank_tool_snap": ("Snap to grid", "Aggancia alla griglia", "Aligner sur la grille", "Ajustar a la cuadrícula"),
    "blank_tool_color": ("Stroke color", "Colore del tratto", "Couleur du trait", "Color del trazo"),
    "blank_tools_note": (
        "Rectangle and eraser are not available yet. Point capture stays active.",
        "Rettangolo e gomma non sono ancora disponibili. L'acquisizione dei punti resta attiva.",
        "Le rectangle et la gomme ne sont pas encore disponibles. La capture des points reste active.",
        "El rectángulo y el borrador aún no están disponibles. La captura de puntos sigue activa."),
    "blank_plan_help": (
        "New Survey also asks for the blank-sheet width and height in m or ft. Changing units converts the dimensions. The sheet is already scaled; its dimensions and scale survive saving and reopening. Loading a floor plan replaces it. Draw opens the blank-sheet toolbar, also on reopened generated sheets. Rectangle, eraser and history controls are currently disabled; snap and stroke color can be selected. Opening the toolbar alone leaves point capture active.",
        "Nuovo rilievo chiede anche larghezza e altezza del foglio bianco in m o ft. Cambiando unità, le dimensioni vengono convertite. Il foglio è già in scala; dimensioni e scala restano salvate alla riapertura. Caricare una planimetria lo sostituisce. Disegna apre la pulsantiera del foglio bianco, anche sui fogli generati e riaperti. Rettangolo, gomma e cronologia sono attualmente disabilitati; si possono scegliere aggancio alla griglia e colore del tratto. Aprire la sola pulsantiera lascia attiva l'acquisizione dei punti.",
        "Nouveau relevé demande aussi largeur et hauteur de la feuille vierge en m ou ft. Changer les unités convertit les dimensions. La feuille est déjà à l'échelle ; ses dimensions et son échelle sont conservées à la réouverture. Charger un plan la remplace. Dessiner ouvre sa barre d'outils, y compris après réouverture. Rectangle, gomme et historique sont désactivés ; alignement sur la grille et couleur sont sélectionnables. Ouvrir la barre seule laisse la capture des points active.",
        "Nuevo estudio también solicita ancho y alto de la hoja en blanco en m o ft. Cambiar las unidades convierte las dimensiones. La hoja ya está a escala y conserva tamaño y escala al reabrir. Cargar un plano la sustituye. Dibujar abre su barra de herramientas, también al reabrir hojas generadas. Rectángulo, borrador e historial están desactivados; se pueden seleccionar ajuste y color. Abrir solo la barra mantiene activa la captura de puntos."),
}


def dictionary(language):
    return {key: values[LANGUAGES.index(language)] for key, values in TEXT.items()}
