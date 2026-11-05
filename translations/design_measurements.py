"""Survey grid and measured drawing selections, EN/IT/FR/ES."""
LANGUAGES = ("en", "it", "fr", "es")
TEXT = {
    "grid_square_size": ("Grid square", "Quadrato griglia", "Carré de grille", "Cuadro de rejilla"),
    "grid_size_action": ("Grid square size…", "Misura quadrato griglia…", "Taille des carrés…", "Tamaño de cuadrícula…"),
    "grid_size_prompt": ("Square side ({unit}). Meters: 0.1 steps; feet: whole units.",
                         "Lato del quadrato ({unit}). Metri: passi di 0,1; piedi: unità intere.",
                         "Côté du carré ({unit}). Mètres : pas de 0,1 ; pieds : unités entières.",
                         "Lado del cuadro ({unit}). Metros: pasos de 0,1; pies: unidades enteras."),
    "grid_options_hint": ("Show/hide grid. Right-click to change its square size for this survey.",
                          "Mostra/nascondi griglia. Clic destro per cambiare la misura dei quadrati di questo rilievo.",
                          "Afficher/masquer la grille. Clic droit pour changer la taille des carrés de ce relevé.",
                          "Mostrar/ocultar cuadrícula. Clic derecho para cambiar su tamaño en este estudio."),
    "grid_invalid_spacing": ("Invalid saved grid size; using the automatic grid.",
                             "Misura griglia salvata non valida; uso la griglia automatica.",
                             "Taille de grille enregistrée invalide ; grille automatique utilisée.",
                             "Tamaño de cuadrícula guardado no válido; se usa la cuadrícula automática."),
    "selection_area": ("Area", "Area", "Surface", "Superficie"),
    "selection_arc_length": ("Arc length", "Lunghezza arco", "Longueur de l'arc", "Longitud del arco"),
    "selection_action_rotate": ("R: rotate", "R: ruota", "R : tourner", "R: girar"),
    "selection_action_move": ("M: move", "M: sposta", "M : déplacer", "M: mover"),
    "selection_action_delete": ("Del: delete", "Del: cancella", "Suppr : effacer", "Supr: borrar"),
    "selection_action_cancel": ("Esc: cancel", "Esc: annulla", "Échap : annuler", "Esc: cancelar"),
    "selection_action_place": ("Right-click: place", "Clic destro: posiziona", "Clic droit : placer", "Clic derecho: colocar"),
    "selection_action_edit": ("Edit: right ×2", "Modifica: destro ×2", "Modifier : droit ×2", "Editar: derecho ×2"),
    "selection_tools_note": (
        "Right-click: item / closed area\nRight-drag: selection box\nR: rotate (hold + mouse: 5°)\nM: move\nDel: delete\nEsc: cancel",
        "Clic destro: elemento / area chiusa\nTrascina col destro: riquadro\nR: ruota (tieni + mouse: 5°)\nM: sposta\nDel: cancella\nEsc: annulla",
        "Clic droit : élément / zone fermée\nGlisser à droite : sélection\nR : tourner (maintenir + souris : 5°)\nM : déplacer\nSuppr : effacer\nÉchap : annuler",
        "Clic derecho: pieza / área cerrada\nArrastrar con derecho: selección\nR: girar (mantén + ratón: 5°)\nM: mover\nSupr: borrar\nEsc: cancelar"),
    "design_measurements_help": (
        "New Survey includes a grid-square size, default 1 m or 3 ft. Use tenths of meters (minimum 0.1 m) or whole feet (minimum 1 ft); switching units rounds to the target input precision. The physical size is saved with the survey and used by both the visible grid and snapping. Right-click the main Grid button to change it later. Older surveys without a saved size retain the automatic grid until edited. In Select, a click within about six screen pixels of a stroke picks that single segment or curve first. A click inside a closed region selects all its boundary pieces and displays its area in m²/ft², accounting for nested holes. Open-space clicks leave the selection unchanged. Single lines show length, circles radius, and arcs length, radius, chord and sagitta. Circular areas use analytic geometry. Commands are listed one per line; M/R/Del and undo/redo also work on selected perimeters.",
        "Nuovo rilievo include la misura del quadrato della griglia, di default 1 m o 3 ft. Usa decimi di metro (minimo 0,1 m) o piedi interi (minimo 1 ft); cambiare unità arrotonda alla precisione del nuovo campo. La misura fisica viene salvata nel rilievo e usata da griglia e agganci. Clic destro sul pulsante Griglia per modificarla in seguito. I rilievi precedenti senza misura salvata mantengono la griglia automatica finché non viene cambiata. In Seleziona, un clic entro circa sei pixel visibili dal tratto sceglie prima quel segmento o curva. Un clic dentro un'area chiusa seleziona tutti i pezzi del contorno e mostra l'area in m²/ft², sottraendo gli spazi interni chiusi. I clic nello spazio aperto non cambiano la selezione. Le linee mostrano la lunghezza, i cerchi il raggio, gli archi lunghezza, raggio, corda e freccia. Le aree circolari usano la geometria analitica. I comandi sono uno per riga; M/R/Del e annulla/ripeti valgono anche sui perimetri selezionati.",
        "Nouveau relevé permet de choisir le côté des carrés : 1 m ou 3 ft par défaut. Utilisez des dixièmes de mètre (minimum 0,1 m) ou des pieds entiers (minimum 1 ft) ; changer d'unités arrondit à la précision du champ cible. La taille physique est enregistrée et utilisée par la grille et l'alignement. Clic droit sur Grille pour la modifier ensuite. Les anciens relevés gardent leur grille automatique jusqu'à modification. En Sélectionner, un clic à environ six pixels d'un trait choisit d'abord ce segment ou cette courbe. À l'intérieur d'une zone fermée, tous les éléments du contour sont sélectionnés et la surface m²/ft² tient compte des trous. Un clic dans l'espace ouvert conserve la sélection. Une ligne affiche sa longueur, un cercle son rayon, un arc sa longueur, son rayon, sa corde et sa flèche. Les surfaces circulaires sont analytiques. Les commandes figurent une par ligne ; M/R/Suppr et annuler/rétablir fonctionnent aussi sur les contours.",
        "Nuevo estudio permite elegir el lado de la cuadrícula: 1 m o 3 ft por defecto. Usa décimas de metro (mínimo 0,1 m) o pies enteros (mínimo 1 ft); cambiar de unidad redondea a la precisión del campo nuevo. Guarda la medida física y la usa en la cuadrícula y el ajuste. Clic derecho en Cuadrícula para modificarla después. Los estudios antiguos mantienen la cuadrícula automática hasta editarla. En Seleccionar, un clic a unos seis píxeles de un trazo elige primero ese segmento o curva. Dentro de un área cerrada selecciona todo el contorno y muestra m²/ft² descontando los huecos. Un clic en espacio abierto conserva la selección. Las líneas muestran longitud, los círculos radio y los arcos longitud, radio, cuerda y flecha. Las áreas circulares son analíticas. Los comandos aparecen uno por línea; M/R/Supr y deshacer/rehacer funcionan también en los contornos."),
}


def dictionary(language):
    return {key: values[LANGUAGES.index(language)] for key, values in TEXT.items()}
