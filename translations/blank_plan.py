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
    "blank_tools": ("Design Mode", "Design Mode", "Mode conception", "Modo diseño"),
    "blank_tools_hint": ("Blank-sheet drawing tools", "Strumenti per il foglio bianco", "Outils pour la feuille vierge", "Herramientas de la hoja en blanco"),
    "blank_tool_rectangle": ("Rectangle", "Rettangolo", "Rectangle", "Rectángulo"),
    "blank_tool_eraser": ("Erase a segment", "Cancella segmento", "Effacer un segment", "Borrar segmento"),
    "blank_tool_undo": ("Undo", "Annulla", "Annuler", "Deshacer"),
    "blank_tool_redo": ("Redo", "Ripristina", "Rétablir", "Rehacer"),
    "blank_tool_snap": ("Snap to grid", "Aggancia alla griglia", "Aligner sur la grille", "Ajustar a la cuadrícula"),
    "design_snap_corner": ("Corner", "Angolo", "Sommet", "Esquina"),
    "design_snap_edge": ("Edge", "Bordo", "Bord", "Borde"),
    "design_snap_grid": ("Grid", "Griglia", "Grille", "Cuadrícula"),
    "blank_tool_color": ("Stroke color", "Colore del tratto", "Couleur du trait", "Color del trazo"),
    "blank_tools_note": (
        "Right-drag draws; right-click sets dimensions. Shapes snap automatically; the grid button adds grid snapping. Alt suspends snapping. Esc cancels, then exits.",
        "Trascina col destro; clic destro per le misure. Aggancio automatico alle forme; il pulsante griglia aggiunge lo snap al reticolo. Alt sospende gli agganci. Esc annulla, poi esce.",
        "Glissez avec le bouton droit ; cliquez pour les dimensions. Alignement automatique sur les formes ; le bouton grille ajoute le quadrillage. Alt suspend l'alignement. Échap annule, puis quitte.",
        "Arrastra con el botón derecho; haz clic para las medidas. Ajuste automático a formas; el botón cuadrícula añade la rejilla. Alt suspende el ajuste. Esc cancela y después sale."),
    "rectangle_size_title": ("Rectangle dimensions", "Dimensioni del rettangolo", "Dimensions du rectangle", "Dimensiones del rectángulo"),
    "rectangle_size_hint": ("Enter the dimensions, then right-click the sheet to place the preview. Esc cancels placement.",
        "Inserisci le misure, poi fai clic destro sul foglio per posizionare l'anteprima. Esc annulla il posizionamento.",
        "Saisissez les dimensions, puis cliquez avec le bouton droit sur la feuille pour placer l'aperçu. Échap annule le placement.",
        "Introduce las medidas y haz clic derecho en la hoja para colocar la vista previa. Esc cancela la colocación."),
    "rectangle_invalid_drawing": ("The saved drawing contains invalid data and cannot be edited.",
        "Il disegno salvato contiene dati non validi e non può essere modificato.",
        "Le dessin enregistré contient des données invalides et ne peut pas être modifié.",
        "El dibujo guardado contiene datos inválidos y no se puede editar."),
    "blank_plan_help": (
        "New Survey asks for blank-sheet dimensions in m or ft and preserves its scale on save/reopen. Design Mode draws axis-aligned rectangles: right-drag with live dimensions, or right-click to enter exact dimensions, then move and right-click to place. Left-drag pans. Esc cancels the current preview; Esc again exits the mode and restores point capture. Color and undo/redo are available; nearby corners take priority over edges and the optional visible grid. Numeric placement preserves dimensions. Orange markers and the dimension label show active targets. Hold Alt to suspend snapping; segment erasing is not yet available. Editable segments are saved with the survey and rendered in PNG/Live/HTML backgrounds. Loading an external plan replaces the sheet and drawing.",
        "Nuovo rilievo chiede le dimensioni del foglio in m o ft e ne conserva la scala al salvataggio e alla riapertura. Design Mode disegna rettangoli allineati agli assi: trascina col destro con misure in tempo reale, oppure fai clic destro per inserire misure esatte, poi muovi e fai clic destro per posizionare. Il sinistro trascina la vista. Esc annulla l'anteprima corrente; un altro Esc chiude la modalità e riattiva l'acquisizione dei punti. Sono disponibili colore e annulla/ripristina; gli angoli vicini hanno priorità sui bordi e sulla griglia visibile opzionale. Il posizionamento numerico conserva le dimensioni. Indicatori arancioni e misure mostrano gli agganci attivi. Tieni Alt per sospenderli; la gomma per segmenti non è ancora disponibile. I segmenti modificabili sono salvati con il rilievo e visualizzati negli sfondi PNG/Live/HTML. Una pianta esterna sostituisce foglio e disegno.",
        "Nouveau relevé demande les dimensions en m ou ft et conserve l'échelle à la réouverture. Le mode conception dessine des rectangles alignés sur les axes : glissez avec le bouton droit pour voir les dimensions, ou cliquez pour saisir des dimensions exactes, puis déplacez et cliquez à nouveau pour placer. Le bouton gauche déplace la vue. Échap annule l'aperçu, puis quitte le mode et rétablit les mesures. Couleur et annuler/rétablir sont disponibles ; les sommets proches priment sur les bords et la grille visible facultative. Le placement numérique conserve les dimensions. Des repères orange et les mesures indiquent les cibles. Alt suspend les alignements ; la gomme reste indisponible. Les segments modifiables sont enregistrés avec le relevé et visibles dans les fonds PNG/Live/HTML. Un plan externe remplace la feuille et le dessin.",
        "Nuevo estudio solicita dimensiones en m o ft y conserva la escala al reabrir. El modo diseño dibuja rectángulos alineados: arrastra con el botón derecho para ver las medidas o haz clic para introducir medidas exactas, mueve y vuelve a hacer clic para colocar. El botón izquierdo desplaza la vista. Esc cancela la vista previa y después sale del modo y restaura las capturas. Color y deshacer/rehacer están disponibles; las esquinas cercanas tienen prioridad sobre los bordes y la cuadrícula visible opcional. La colocación numérica conserva las medidas. Marcas naranjas y medidas indican los ajustes. Alt los suspende; el borrador aún no está disponible. Los segmentos editables se guardan con el estudio y aparecen en fondos PNG/Live/HTML. Un plano externo sustituye la hoja y el dibujo."),
}


def dictionary(language):
    return {key: values[LANGUAGES.index(language)] for key, values in TEXT.items()}
