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
    "eraser_tools_note": (
        "Right-click erases one highlighted segment. Right-drag erases whole segments touched by the red area, on release. Left-drag pans; Esc cancels, then exits. Undo restores the deletion.",
        "Clic destro: cancella il segmento evidenziato. Trascina col destro: al rilascio cancella i segmenti interi toccati dall'area rossa. Il sinistro sposta la vista; Esc annulla, poi esce. Annulla ripristina i lati.",
        "Clic droit : efface le segment surligné. Glissez avec le bouton droit : au relâchement, les segments entiers touchés par la zone rouge sont effacés. Le bouton gauche déplace la vue ; Échap annule, puis quitte. Annuler restaure les segments.",
        "Clic derecho: borra un segmento resaltado. Arrastra con el derecho: al soltar, borra los segmentos completos tocados por el área roja. El izquierdo mueve la vista; Esc cancela y después sale. Deshacer restaura los lados."),
    "eraser_one_segment": ("1 segment", "1 segmento", "1 segment à effacer", "1 segmento"),
    "eraser_many_segments": ("{count} segments", "{count} segmenti", "{count} segments à effacer", "{count} segmentos"),
    "eraser_click": ("Right-click to erase", "Clic destro per cancellare", "Clic droit pour effacer", "Clic derecho para borrar"),
    "eraser_release": ("Release to erase · Esc cancels", "Rilascia per cancellare · Esc annulla", "Relâchez pour effacer · Échap annule", "Suelta para borrar · Esc cancela"),
    "blank_tool_undo": ("Undo", "Annulla", "Annuler", "Deshacer"),
    "blank_tool_redo": ("Redo", "Ripristina", "Rétablir", "Rehacer"),
    "blank_tool_snap": ("Snap to grid", "Aggancia alla griglia", "Aligner sur la grille", "Ajustar a la cuadrícula"),
    "design_snap_corner": ("Corner", "Angolo", "Sommet", "Esquina"),
    "design_snap_edge": ("Edge", "Bordo", "Bord", "Borde"),
    "design_snap_grid": ("Grid", "Griglia", "Grille", "Cuadrícula"),
    "design_snap_alignment": ("Alignment", "Allineamento", "Alignement", "Alineación"),
    "design_regions_limited": (
        "Drawing too complex for closed-area detection. The grid keeps its normal appearance.",
        "Disegno troppo complesso per riconoscere le aree chiuse. La griglia mantiene l'aspetto normale.",
        "Dessin trop complexe pour détecter les zones fermées. La grille garde son aspect normal.",
        "Dibujo demasiado complejo para detectar áreas cerradas. La cuadrícula mantiene su aspecto normal."),
    "design_regions_help": (
        "While dragging a rectangle, its moving sides also align with nearby sides of existing shapes, even when the pointer extends beyond them; orange guides show the alignment. The starting corner stays fixed. The grid is softer inside perimeters actually closed by the current segments, including joined or overlapping shapes. Erasing an outer side opens that area and restores its normal grid; undo restores the closure. Unclosed gaps stay open. This is a display aid and does not add RF wall attenuation.",
        "Trascinando un rettangolo, anche i lati mobili si allineano ai lati vicini delle altre forme, quando il cursore li supera; le guide arancioni mostrano l'allineamento. L'angolo iniziale resta fermo. La griglia è attenuata nei perimetri effettivamente chiusi dai segmenti attuali, anche con forme unite o sovrapposte. Cancellando un lato esterno si apre l'area e torna la griglia normale; Annulla ripristina la chiusura. Gli spazi aperti rimangono aperti. È un aiuto visivo e non introduce attenuazione RF delle pareti.",
        "Pendant le tracé d'un rectangle, ses côtés mobiles s'alignent aussi sur les côtés proches des autres formes, même si le pointeur les dépasse ; les guides orange montrent l'alignement. Le sommet initial reste fixe. La grille est atténuée dans les périmètres réellement fermés par les segments actuels, y compris les formes jointes ou superposées. Effacer un côté extérieur ouvre la zone et rétablit la grille normale ; Annuler restaure la fermeture. Les espaces ouverts restent ouverts. Cet effet visuel n'ajoute aucune atténuation RF des murs.",
        "Al arrastrar un rectángulo, sus lados móviles también se alinean con lados cercanos de otras formas, aunque el cursor los sobrepase; las guías naranjas muestran la alineación. La esquina inicial queda fija. La cuadrícula se atenúa dentro de perímetros realmente cerrados por los segmentos actuales, incluidas formas unidas o superpuestas. Borrar un lado exterior abre el área y restaura la cuadrícula normal; Deshacer restaura el cierre. Los huecos abiertos siguen abiertos. Es una ayuda visual y no añade atenuación RF de paredes."),
    "blank_tool_color": ("Stroke color", "Colore del tratto", "Couleur du trait", "Color del trazo"),
    "blank_tools_note": (
        "Right-drag draws; right-click sets dimensions. In placement: tap R for 90°, hold R + mouse for 5° steps. Shapes snap automatically; the grid button adds grid snapping. Alt bypasses; Esc cancels, then exits.",
        "Trascina col destro; clic destro per le misure. Nel posizionamento: tocco R per 90°, tieni R + mouse per scatti di 5°. Aggancio automatico alle forme; il pulsante griglia aggiunge lo snap al reticolo. Alt sospende; Esc annulla, poi esce.",
        "Glissez avec le bouton droit ; cliquez pour les dimensions. Au placement : R bref pour 90°, maintenez R + souris par pas de 5°. Alignement automatique sur les formes ; le bouton grille ajoute le quadrillage. Alt suspend ; Échap annule, puis quitte.",
        "Arrastra con el derecho; clic derecho para las medidas. Al colocar: toque R para 90°, mantén R + ratón en pasos de 5°. Ajuste automático a formas; el botón cuadrícula añade la rejilla. Alt suspende; Esc cancela y después sale."),
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
        "New Survey asks for blank-sheet dimensions in m or ft and preserves its scale on save/reopen. Design Mode draws axis-aligned rectangles: right-drag with live dimensions, or right-click to enter exact dimensions, then move and right-click to place. Left-drag pans. Esc cancels the current preview; Esc again exits the mode and restores point capture. Color and undo/redo are available; nearby corners take priority over edges and the optional visible grid. Numeric placement preserves dimensions. Orange markers and the dimension label show active targets. Hold Alt to suspend snapping. Select Eraser to right-click one highlighted segment, or right-drag a red selection area. Whole segments touched by the area are erased on release; Esc cancels. Each deletion is one undo action. Editable segments are saved with the survey and rendered in PNG/Live/HTML backgrounds. Loading an external plan replaces the sheet and drawing.",
        "Nuovo rilievo chiede le dimensioni del foglio in m o ft e ne conserva la scala al salvataggio e alla riapertura. Design Mode disegna rettangoli allineati agli assi: trascina col destro con misure in tempo reale, oppure fai clic destro per inserire misure esatte, poi muovi e fai clic destro per posizionare. Il sinistro trascina la vista. Esc annulla l'anteprima corrente; un altro Esc chiude la modalità e riattiva l'acquisizione dei punti. Sono disponibili colore e annulla/ripristina; gli angoli vicini hanno priorità sui bordi e sulla griglia visibile opzionale. Il posizionamento numerico conserva le dimensioni. Indicatori arancioni e misure mostrano gli agganci attivi. Tieni Alt per sospenderli. Seleziona la gomma: clic destro cancella un segmento evidenziato; trascinando col destro compare un'area rossa. Al rilascio vengono cancellati i segmenti interi toccati dall'area; Esc annulla. Ogni cancellazione è una sola azione annullabile. I segmenti modificabili sono salvati con il rilievo e visualizzati negli sfondi PNG/Live/HTML. Una pianta esterna sostituisce foglio e disegno.",
        "Nouveau relevé demande les dimensions en m ou ft et conserve l'échelle à la réouverture. Le mode conception dessine des rectangles alignés sur les axes : glissez avec le bouton droit pour voir les dimensions, ou cliquez pour saisir des dimensions exactes, puis déplacez et cliquez à nouveau pour placer. Le bouton gauche déplace la vue. Échap annule l'aperçu, puis quitte le mode et rétablit les mesures. Couleur et annuler/rétablir sont disponibles ; les sommets proches priment sur les bords et la grille visible facultative. Le placement numérique conserve les dimensions. Des repères orange et les mesures indiquent les cibles. Alt suspend les alignements. Sélectionnez la gomme : clic droit pour effacer un segment surligné, ou glissez avec le bouton droit pour une zone rouge. Les segments entiers touchés sont effacés au relâchement ; Échap annule. Chaque suppression est une seule action annulable. Les segments modifiables sont enregistrés avec le relevé et visibles dans les fonds PNG/Live/HTML. Un plan externe remplace la feuille et le dessin.",
        "Nuevo estudio solicita dimensiones en m o ft y conserva la escala al reabrir. El modo diseño dibuja rectángulos alineados: arrastra con el botón derecho para ver las medidas o haz clic para introducir medidas exactas, mueve y vuelve a hacer clic para colocar. El botón izquierdo desplaza la vista. Esc cancela la vista previa y después sale del modo y restaura las capturas. Color y deshacer/rehacer están disponibles; las esquinas cercanas tienen prioridad sobre los bordes y la cuadrícula visible opcional. La colocación numérica conserva las medidas. Marcas naranjas y medidas indican los ajustes. Alt los suspende. Selecciona el borrador: clic derecho borra un segmento resaltado; arrastra con el derecho para un área roja. Los segmentos completos tocados se borran al soltar; Esc cancela. Cada borrado es una sola acción que se puede deshacer. Los segmentos editables se guardan con el estudio y aparecen en fondos PNG/Live/HTML. Un plano externo sustituye la hoja y el dibujo."),
}


def dictionary(language):
    result = {key: values[LANGUAGES.index(language)] for key, values in TEXT.items()}
    from translations.drawing_edit import dictionary as editing_dictionary
    result.update(editing_dictionary(language))
    from translations.plan_extensions import dictionary as extensions_dictionary
    result.update(extensions_dictionary(language))
    from translations.plan_curves import dictionary as curves_dictionary
    result.update(curves_dictionary(language))
    result["blank_plan_help"] += " " + result["design_regions_help"]
    result["blank_plan_help"] += " " + result["drawing_edit_help"]
    result["blank_plan_help"] += " " + result["drawing_join_help"]
    result["blank_plan_help"] += " " + result["rotation_hold_help"]
    result["blank_plan_help"] += " " + result["plan_extensions_help"]
    result["blank_plan_help"] += " " + result["grid_all_vertices_help"]
    result["blank_plan_help"] += " " + result["plan_curves_help"]
    result["blank_plan_help"] += " " + result["curve_edit_help"]
    result["blank_plan_help"] += " " + result["circle_rotation_help"]
    return result
