"""Additional segment editing controls and help in the four UI languages."""
LANGUAGES = ("en", "it", "fr", "es")
TEXT = {
    "blank_tool_line": ("Line", "Linea", "Ligne", "Línea"),
    "blank_tool_select": ("Select", "Seleziona", "Sélectionner", "Seleccionar"),
    "line_length": ("Length", "Lunghezza", "Longueur", "Longitud"),
    "line_size_title": ("Line length", "Lunghezza della linea", "Longueur de la ligne", "Longitud de la línea"),
    "line_size_hint": (
        "Enter a length, then move the preview and right-click to place it. R rotates by 90°; Esc cancels.",
        "Inserisci la lunghezza, poi muovi l'anteprima e posizionala col destro. R ruota di 90°; Esc annulla.",
        "Saisissez une longueur, déplacez l'aperçu et placez-le par clic droit. R tourne de 90° ; Échap annule.",
        "Introduce la longitud, mueve la vista previa y colócala con clic derecho. R gira 90°; Esc cancela."),
    "design_rotate_hint": ("R: rotate 90°", "R: ruota di 90°", "R : tourner de 90°", "R: girar 90°"),
    "design_rotation_outside": (
        "This rotation does not fit the sheet. Move the selection or use another orientation.",
        "La rotazione non entra nel foglio. Sposta la selezione o usa un altro orientamento.",
        "Cette rotation dépasse la feuille. Déplacez la sélection ou choisissez une autre orientation.",
        "Este giro no cabe en la hoja. Mueve la selección o usa otra orientación."),
    "design_edit_limit": (
        "The edit exceeds the drawing limits. The existing drawing is preserved.",
        "La modifica supera i limiti del disegno. Il disegno esistente viene conservato.",
        "La modification dépasse les limites du dessin. Le dessin existant est conservé.",
        "La edición supera los límites del dibujo. Se conserva el dibujo existente."),
    "line_tools_note": (
        "Right-drag draws a horizontal or vertical line with live length. Right-click enters its length, then click again to place. R rotates the moving preview; Alt suspends snapping. Esc cancels.",
        "Trascina col destro per una linea orizzontale o verticale con misura. Clic destro per inserire la lunghezza, poi ancora per posizionare. R ruota l'anteprima; Alt sospende gli agganci. Esc annulla.",
        "Glissez avec le bouton droit pour une ligne horizontale ou verticale mesurée. Clic droit pour sa longueur, puis pour placer. R tourne l'aperçu ; Alt suspend l'alignement. Échap annule.",
        "Arrastra con el derecho para una línea horizontal o vertical con medida. Clic derecho para la longitud y de nuevo para colocar. R gira la vista previa; Alt suspende el ajuste. Esc cancela."),
    "selection_tools_note": (
        "Right-click selects a segment; right-drag selects touched segments. R rotates the selection 90°. M starts a cursor-following move; right-click places it. R also rotates while moving. Esc cancels; left-drag pans.",
        "Clic destro seleziona un tratto; trascinando selezioni quelli toccati. R ruota di 90°. M avvia lo spostamento col cursore; clic destro posiziona. R ruota anche durante lo spostamento. Esc annulla; il sinistro sposta la vista.",
        "Clic droit pour un segment ; glissez pour les segments touchés. R tourne de 90°. M déplace la sélection avec le pointeur ; clic droit pour placer. R tourne aussi pendant le déplacement. Échap annule ; le bouton gauche déplace la vue.",
        "Clic derecho selecciona un tramo; arrastra para los tramos tocados. R gira 90°. M mueve la selección con el cursor; clic derecho la coloca. R también gira al mover. Esc cancela; el izquierdo desplaza la vista."),
    "selection_count": ("Selected segments: {count}", "Tratti selezionati: {count}",
                        "Segments sélectionnés : {count}", "Tramos seleccionados: {count}"),
    "selection_keys_hint": ("R: rotate · M: move", "R: ruota · M: sposta", "R : tourner · M : déplacer", "R: girar · M: mover"),
    "selection_move_hint": ("Right-click to place · R: rotate · Esc: cancel", "Clic destro posiziona · R ruota · Esc annulla",
                            "Clic droit pour placer · R tourne · Échap annule", "Clic derecho coloca · R gira · Esc cancela"),
    "drawing_edit_help": (
        "Intersections now split the actual editable segments, including T joints and collinear overlap endpoints. The eraser deletes a single fragment between cuts. Existing drawings gain these cuts when opened; saving preserves them. Line draws horizontal/vertical strokes by right-drag, or asks only for length on right-click before placement. R rotates cursor-following Line and Rectangle previews in 90° steps without changing measurements. Select uses right-click for one fragment or a right-drag area for all touched fragments. R rotates selected fragments around their bounding-box center. M starts a rigid move; right-click places it, Esc cancels. R also rotates during a move. Moving selections snap using their bounding box to unselected geometry or the optional grid; Alt bypasses snapping. Every committed edit is undoable and recomputes cuts and closed areas. Shortcuts do not apply in text fields or dialogs. Left-drag pans and RF point capture stays suspended in Design Mode.",
        "Gli incroci dividono ora i segmenti realmente modificabili, comprese giunzioni a T ed estremi di tratti sovrapposti. La gomma elimina un frammento tra due tagli. I disegni esistenti acquisiscono i tagli all'apertura; il salvataggio li conserva. Linea disegna tratti orizzontali/verticali trascinando col destro, oppure chiede la sola lunghezza col clic destro prima del posizionamento. R ruota le anteprime di Linea e Rettangolo che seguono il cursore, a passi di 90° senza cambiare le misure. Seleziona usa clic destro per un frammento o un'area trascinata col destro per tutti i tratti toccati. R ruota i tratti scelti intorno al centro del loro riquadro. M avvia lo spostamento rigido; clic destro posiziona, Esc annulla. R ruota anche durante lo spostamento. Il riquadro della selezione si aggancia alle geometrie non selezionate o alla griglia opzionale; Alt sospende gli agganci. Ogni modifica confermata è annullabile e ricalcola tagli e aree chiuse. Le scorciatoie non agiscono nei campi di testo o nelle finestre di dialogo. Il sinistro sposta la vista e l'acquisizione RF resta sospesa in Design Mode.",
        "Les intersections divisent les segments modifiables, y compris les jonctions en T et les extrémités superposées. La gomme efface un fragment entre deux coupures. Les dessins existants reçoivent ces coupures à l'ouverture et les conservent à l'enregistrement. Ligne trace horizontalement ou verticalement par glissement du bouton droit, ou demande seulement la longueur par clic droit avant placement. R tourne les aperçus de Ligne et Rectangle de 90° sans changer les mesures. Sélectionner utilise le clic droit pour un fragment ou une zone glissée pour tous les fragments touchés. R tourne autour du centre du cadre de sélection. M démarre un déplacement rigide ; clic droit place, Échap annule. R tourne aussi pendant le déplacement. Le cadre s'aligne sur les formes non sélectionnées ou la grille facultative ; Alt suspend l'alignement. Chaque modification confirmée est annulable et recalcule coupures et zones fermées. Les raccourcis sont inactifs dans les champs de texte et les dialogues. Le bouton gauche déplace la vue et les captures RF restent suspendues en mode conception.",
        "Las intersecciones dividen los segmentos editables, incluidas uniones en T y extremos superpuestos. El borrador elimina un fragmento entre cortes. Los dibujos existentes reciben los cortes al abrir y los conservan al guardar. Línea dibuja trazos horizontales o verticales arrastrando con el derecho, o pide solo la longitud con clic derecho antes de colocar. R gira las vistas previas de Línea y Rectángulo 90° sin cambiar las medidas. Seleccionar usa clic derecho para un fragmento o un área arrastrada para todos los tramos tocados. R gira alrededor del centro del marco de selección. M inicia un movimiento rígido; clic derecho coloca, Esc cancela. R también gira al mover. El marco se ajusta a geometrías no seleccionadas o la cuadrícula opcional; Alt suspende el ajuste. Cada edición confirmada se puede deshacer y recalcula cortes y áreas cerradas. Los atajos no actúan en campos de texto ni diálogos. El izquierdo desplaza la vista y las capturas RF siguen suspendidas en modo diseño."),
}


def dictionary(language):
    return {key: values[LANGUAGES.index(language)] for key, values in TEXT.items()}
