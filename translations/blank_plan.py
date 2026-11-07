"""Blank-sheet dimensions and the drawing toolbar shell, EN/IT/FR/ES."""

LANGUAGES = ("en", "it", "fr", "es")
TEXT = {
    "save_plan_jpeg": ("Save as JPEG", "Salva come JPEG", "Enregistrer en JPEG", "Guardar como JPEG"),
    "save_plan_jpeg_hint": (
        "Clean plan with scale reference, fitted to the selected page with its proportions preserved.",
        "Pianta pulita con riferimento di scala, adattata al formato scelto mantenendo le proporzioni.",
        "Plan seul avec référence d'échelle, ajusté au format choisi en conservant ses proportions.",
        "Plano limpio con referencia de escala, ajustado al formato elegido manteniendo sus proporciones."),
    "plan_jpeg_paper": ("Paper size", "Formato carta", "Format papier", "Tamaño de papel"),
    "plan_jpeg_orientation": ("Page orientation", "Orientamento pagina", "Orientation de page", "Orientación de página"),
    "plan_jpeg_portrait": ("Portrait", "Verticale", "Portrait (vertical)", "Vertical"),
    "plan_jpeg_landscape": ("Landscape", "Orizzontale", "Paysage", "Horizontal"),
    "plan_jpeg_resolution": ("Resolution", "Risoluzione", "Résolution", "Resolución"),
    "plan_jpeg_draft": ("Draft", "Bozza", "Brouillon", "Borrador"),
    "plan_jpeg_quality": ("High quality", "Alta qualità", "Haute qualité", "Alta calidad"),
    "plan_jpeg_detail": ("Fine detail", "Dettagli fini", "Détails fins", "Detalles finos"),
    "plan_jpeg_size_limit": (
        "This page exceeds the 150-megapixel JPEG limit. Select 300 DPI or a smaller paper size.",
        "Questa pagina supera il limite JPEG di 150 megapixel. Scegli 300 DPI o un formato carta più piccolo.",
        "Cette page dépasse la limite JPEG de 150 mégapixels. Choisissez 300 DPI ou un papier plus petit.",
        "Esta página supera el límite JPEG de 150 megapíxeles. Elige 300 DPI o un papel más pequeño."),
    "plan_jpeg_detail_help": (
        "300 DPI is the standard high-quality setting; 600 DPI adds resolution for fine lines and small text. Drawn plans are rendered from their paths at the selected resolution in both JPEG and Print Plan. Imported bitmap plans retain the detail of the source image. JPEG pages are limited to 150 megapixels: A3/A2 support 600 DPI, while A1/A0 require 300 DPI or less.",
        "300 DPI è l'impostazione standard per l'alta qualità; 600 DPI aggiunge risoluzione per linee fini e testi piccoli. Le piante disegnate vengono renderizzate dai tracciati alla risoluzione scelta sia in JPEG sia in Stampa Pianta. Le planimetrie bitmap caricate mantengono il dettaglio dell'immagine originale. Il JPEG è limitato a 150 megapixel: A3/A2 supportano 600 DPI, mentre A1/A0 richiedono 300 DPI o meno.",
        "300 DPI est le réglage standard de haute qualité ; 600 DPI ajoute de la résolution pour les traits fins et les petits textes. Les plans dessinés sont rendus depuis leurs tracés à la résolution choisie en JPEG et à l'impression. Les plans bitmap importés conservent le détail de l'image source. Les JPEG sont limités à 150 mégapixels : A3/A2 acceptent 600 DPI ; A1/A0 nécessitent 300 DPI ou moins.",
        "300 DPI es el ajuste estándar de alta calidad; 600 DPI añade resolución para líneas finas y texto pequeño. Los planos dibujados se renderizan desde sus trazados a la resolución elegida, en JPEG e impresión. Los planos bitmap importados conservan el detalle de la imagen original. El JPEG está limitado a 150 megapíxeles: A3/A2 admiten 600 DPI; A1/A0 requieren 300 DPI o menos."),
    "plan_jpeg_saved": ("JPEG saved: {path}", "JPEG salvato: {path}", "JPEG enregistré : {path}", "JPEG guardado: {path}"),
    "plan_jpeg_error": ("Could not save the plan as JPEG: {error}", "Impossibile salvare la pianta come JPEG: {error}",
        "Impossible d'enregistrer le plan en JPEG : {error}", "No se pudo guardar el plano como JPEG: {error}"),
    "plan_jpeg_replace": ("Replace the existing file {name}?", "Sostituire il file esistente {name}?",
        "Remplacer le fichier existant {name} ?", "¿Reemplazar el archivo existente {name}?"),
    "plan_jpeg_help": (
        "Save as JPEG, beside Print Plan in Project, exports the clean plan with the same scale reference. Choose A5–A0, Letter or Legal, portrait/landscape and 150/300/600 DPI. The dialog previews the page and shows its exact pixel size. The whole plan fits the selected page with 10 mm margins and its proportions preserved. The JPEG stores its resolution for printing; choose actual size in the image-printing application to preserve the chosen paper size. Unsaved drawing edits are included without requiring a survey save. Canceling either dialog creates no file.",
        "Salva come JPEG, accanto a Stampa Pianta in Progetto, esporta la pianta pulita con lo stesso riferimento di scala. Scegli A5–A0, Letter o Legal, verticale/orizzontale e 150/300/600 DPI. La finestra mostra l'anteprima e le dimensioni esatte in pixel. La pianta intera si adatta alla pagina con margini di 10 mm mantenendo le proporzioni. Il JPEG memorizza la risoluzione per la stampa: nell'app usata per stampare l'immagine scegli dimensioni effettive per mantenere il formato carta scelto. Include le modifiche al disegno non salvate, senza richiedere il salvataggio del rilievo. Annullando una delle due finestre non viene creato alcun file.",
        "Enregistrer en JPEG, à côté d'Imprimer le plan dans Projet, exporte le plan seul avec la même référence d'échelle. Choisissez A5–A0, Letter ou Legal, portrait/paysage et 150/300/600 DPI. La fenêtre montre l'aperçu et les dimensions exactes en pixels. Le plan entier s'ajuste à la page avec des marges de 10 mm sans déformation. Le JPEG mémorise sa résolution d'impression : choisissez la taille réelle dans l'application d'impression pour conserver le format papier choisi. Les modifications non enregistrées sont incluses sans enregistrer le relevé. Annuler l'une des fenêtres ne crée aucun fichier.",
        "Guardar como JPEG, junto a Imprimir plano en Proyecto, exporta el plano limpio con la misma referencia de escala. Elige A5–A0, Letter o Legal, vertical/horizontal y 150/300/600 DPI. La ventana muestra la vista previa y las dimensiones exactas en píxeles. El plano completo se ajusta a la página con márgenes de 10 mm sin deformarse. El JPEG guarda su resolución de impresión: elige tamaño real en la aplicación de impresión para conservar el papel elegido. Incluye cambios sin guardar, sin guardar el estudio. Cancelar cualquiera de las ventanas no crea archivos."),
    "print_plan_not_started": ("Printing was not started.", "Stampa non avviata.", "L'impression n'a pas été lancée.", "No se inició la impresión."),
    "print_scale_help": (
        "The footer includes a calibrated graphical scale reference in m/ft, resized with the plan when the paper changes. Uncalibrated plans explicitly report that scale is unavailable.",
        "Il piè di pagina include un riferimento grafico di scala calibrato in m/ft, ridimensionato insieme alla pianta quando cambia la carta. Le piante non calibrate indicano esplicitamente che la scala non è disponibile.",
        "Le pied de page comprend une référence graphique d'échelle étalonnée en m/ft, redimensionnée avec le plan lorsque le papier change. Un plan non étalonné indique explicitement que l'échelle est indisponible.",
        "El pie de página incluye una referencia gráfica de escala calibrada en m/ft, ajustada junto con el plano al cambiar el papel. Los planos sin calibrar indican que la escala no está disponible."),
    "print_plan_scale": ("Scale reference", "Riferimento di scala", "Référence d'échelle", "Referencia de escala"),
    "print_plan_scale_missing": ("Scale unavailable: plan not calibrated", "Scala non disponibile: pianta non calibrata", "Échelle indisponible : plan non étalonné", "Escala no disponible: plano sin calibrar"),
    "print_plan": ("Print Plan", "Stampa Pianta", "Imprimer le plan", "Imprimir plano"),
    "print_plan_setup": ("Page Setup", "Imposta Pagina", "Mise en page", "Configurar página"),
    "print_plan_send": ("Print…", "Stampa…", "Imprimer…", "Imprimir…"),
    "print_plan_hint": (
        "Preview and print the clean plan, fitted to the paper, without survey overlays.",
        "Anteprima e stampa della pianta pulita, adattata al foglio, senza sovrapposizioni del rilievo.",
        "Aperçu et impression du plan seul, ajusté au papier, sans superpositions du relevé.",
        "Vista previa e impresión del plano limpio, ajustado al papel, sin superposiciones del estudio."),
    "print_plan_error": ("Could not prepare the plan for printing: {error}",
        "Impossibile preparare la pianta per la stampa: {error}",
        "Impossible de préparer le plan pour l'impression : {error}",
        "No se pudo preparar el plano para imprimir: {error}"),
    "print_plan_help": (
        "Print Plan, at the right of the Project heading, opens a print preview. It includes the loaded plan and committed structures, text, doors, windows and markers, including unsaved edits. Survey points, AP symbols, grid, analysis masks, heatmaps, selection and tool previews are omitted. The whole plan fits one page with its proportions preserved; this is not a 1:1 architectural-scale print. Choose paper and printer in the preview. No survey save is required.",
        "Stampa Pianta, a destra del titolo Progetto, apre l'anteprima di stampa. Include la pianta caricata e struttura, testo, porte, finestre e marker confermati, anche con modifiche non salvate. Esclude punti di rilevamento, simboli AP, griglia, maschere di analisi, heatmap, selezioni e anteprime degli strumenti. La pianta intera si adatta a una pagina mantenendo le proporzioni; non è una stampa in scala architettonica 1:1. Scegli carta e stampante dall'anteprima. Non richiede di salvare il rilievo.",
        "Imprimer le plan, à droite du titre Projet, ouvre un aperçu. Il inclut le plan chargé et les structures, textes, portes, fenêtres et marqueurs validés, même non enregistrés. Points de mesure, symboles AP, grille, masques d'analyse, cartes thermiques, sélection et aperçus des outils sont exclus. Le plan entier tient sur une page sans déformation ; ce n'est pas une impression architecturale à l'échelle 1:1. Choisissez papier et imprimante dans l'aperçu, sans devoir enregistrer le relevé.",
        "Imprimir plano, a la derecha del título Proyecto, abre una vista previa. Incluye el plano cargado y estructuras, textos, puertas, ventanas y marcadores confirmados, aunque no se hayan guardado. Excluye puntos de medición, símbolos AP, cuadrícula, máscaras de análisis, mapas de calor, selección y vistas previas de herramientas. El plano completo cabe en una página sin deformarse; no es una impresión arquitectónica a escala 1:1. Elige papel e impresora en la vista previa, sin guardar el estudio."),
    "blank_plan_defaults_help": (
        "New sheets default to 35 × 25 m or 115 × 81 ft. Switching units selects that unit's preset until you edit the dimensions; afterwards, it converts the same physical size.",
        "I nuovi fogli partono da 35 × 25 m o 115 × 81 ft. Cambiare unità sceglie il relativo preset finché non modifichi le dimensioni; dopo, converte la stessa misura fisica.",
        "Les nouvelles feuilles mesurent 35 × 25 m ou 115 × 81 ft. Changer d'unités choisit le préréglage associé tant que les dimensions ne sont pas modifiées ; ensuite, la taille physique est conservée par conversion.",
        "Las hojas nuevas miden 35 × 25 m o 115 × 81 ft. Cambiar de unidades usa el valor predeterminado hasta que edites las dimensiones; después, convierte el mismo tamaño físico."),
    "blank_plan_size": ("Blank sheet", "Foglio bianco", "Feuille vierge", "Hoja en blanco"),
    "blank_plan_width": ("Width", "Larghezza", "Largeur", "Ancho"),
    "blank_plan_height": ("Height", "Altezza", "Hauteur", "Alto"),
    "blank_plan_size_hint": (
        "Choose the sheet dimensions and grid spacing. The scale is calculated automatically.",
        "Scegli le dimensioni del foglio e il passo della griglia. La scala viene calcolata automaticamente.",
        "Choisissez les dimensions de la feuille et le pas de la grille. L'échelle est calculée automatiquement.",
        "Elige las dimensiones de la hoja y el paso de la cuadrícula. La escala se calcula automáticamente."),
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
    "blank_pan_help": (
        "Left-drag pans even when the entire sheet is visible, including from the surrounding margin. Move the sheet to reach areas covered by Design Mode; its controls stay fixed. Fit recenters the sheet and shows it in full. The surrounding margin is for navigation only.",
        "Il trascinamento col sinistro sposta la vista anche quando il foglio è tutto visibile, anche partendo dal margine esterno. Sposta il foglio per raggiungere le zone coperte da Design Mode; i controlli restano fermi. Fit ricentra il foglio e lo mostra per intero. Il margine esterno serve solo alla navigazione.",
        "Le glissement gauche déplace la vue même si toute la feuille est visible, y compris depuis la marge extérieure. Déplacez la feuille pour atteindre les zones masquées par le mode conception ; ses commandes restent fixes. Ajuster recentre la feuille et l'affiche en entier. La marge sert uniquement à naviguer.",
        "Arrastrar con el izquierdo desplaza la vista aunque toda la hoja sea visible, también desde el margen exterior. Mueve la hoja para llegar a zonas tapadas por el modo diseño; sus controles permanecen fijos. Ajustar centra la hoja y la muestra completa. El margen solo sirve para navegar."),
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
    from translations.design_measurements import dictionary as measurements_dictionary
    result.update(measurements_dictionary(language))
    result["blank_plan_help"] += " " + result["blank_pan_help"]
    result["blank_plan_help"] += " " + result["design_regions_help"]
    result["blank_plan_help"] += " " + result["drawing_edit_help"]
    result["blank_plan_help"] += " " + result["drawing_join_help"]
    result["blank_plan_help"] += " " + result["rotation_hold_help"]
    result["blank_plan_help"] += " " + result["plan_extensions_help"]
    result["blank_plan_help"] += " " + result["grid_all_vertices_help"]
    result["blank_plan_help"] += " " + result["plan_curves_help"]
    result["blank_plan_help"] += " " + result["curve_edit_help"]
    result["blank_plan_help"] += " " + result["circle_rotation_help"]
    result["blank_plan_help"] += " " + result["blank_plan_defaults_help"]
    result["blank_plan_help"] += " " + result["curve_precision_help"]
    result["blank_plan_help"] += " " + result["design_measurements_help"]
    return result
