"""Drawing annotation tools and their isolated editing workflow."""
LANGUAGES = ("en", "it", "fr", "es")
TEXT = {
    "annotation_structure": ("Structure", "Struttura", "Structure", "Estructura"),
    "annotation_group": ("Annotations", "Annotazioni", "Annotations", "Anotaciones"),
    "annotation_controls": ("Shared controls", "Controlli comuni", "Commandes communes", "Controles comunes"),
    "annotation_marker": ("Marker", "Marker", "Marqueur", "Marcador"),
    "annotation_door": ("Door", "Porta", "Porte", "Puerta"),
    "annotation_window": ("Window", "Finestra", "Fenêtre", "Ventana"),
    "annotation_select": ("Select annotations", "Seleziona annotazioni", "Sélectionner les annotations", "Seleccionar anotaciones"),
    "annotation_select_structure": ("Select structure", "Seleziona struttura", "Sélectionner la structure", "Seleccionar estructura"),
    "annotation_properties": ("Properties", "Proprietà", "Propriétés", "Propiedades"),
    "annotation_stroke": ("Stroke width", "Spessore del tratto", "Épaisseur du trait", "Grosor del trazo"),
    "annotation_grid": ("Follow grid", "Segui la griglia", "Suivre la grille", "Seguir la cuadrícula"),
    "annotation_type": ("Type", "Tipo", "Type", "Tipo"),
    "annotation_single": ("Single leaf", "Singola", "Un vantail", "Una hoja"),
    "annotation_double": ("Double leaf", "Doppia", "Deux vantaux", "Dos hojas"),
    "annotation_sliding": ("Sliding", "Scorrevole", "Coulissante", "Corredera"),
    "annotation_hinge": ("Hinge at opposite end", "Cerniera all'estremità opposta", "Charnière à l'autre extrémité", "Bisagra en el extremo opuesto"),
    "annotation_side": ("Open on opposite side", "Apri sul lato opposto", "Ouvrir de l'autre côté", "Abrir hacia el lado opuesto"),
    "annotation_properties_hint": (
        "Annotations do not change rooms or their area. Width uses survey units; stroke width is graphical.",
        "Le annotazioni non cambiano ambienti o aree. La larghezza usa le unità del rilievo; lo spessore del tratto è grafico.",
        "Les annotations ne changent ni les pièces ni leur surface. La largeur utilise les unités du relevé ; l'épaisseur du trait est graphique.",
        "Las anotaciones no cambian las habitaciones ni su área. La anchura usa las unidades del estudio; el grosor del trazo es gráfico."),
    "annotation_marker_note": (
        "Right-drag: dashed path\nProperties: color, width, free/grid\nAlt: bypass grid · Esc: cancel",
        "Trascina col destro: tratto tratteggiato\nProprietà: colore, spessore, libero/griglia\nAlt: sospendi griglia · Esc: annulla",
        "Glisser à droite : trait discontinu\nPropriétés : couleur, épaisseur, libre/grille\nAlt : suspendre la grille · Échap : annuler",
        "Arrastra con el derecho: trazo discontinuo\nPropiedades: color, grosor, libre/cuadrícula\nAlt: suspender cuadrícula · Esc: cancelar"),
    "annotation_place_note": (
        "Right-click: place on wall\nProperties: width and appearance\nEsc: cancel",
        "Clic destro: posa sulla parete\nProprietà: larghezza e aspetto\nEsc: annulla",
        "Clic droit : placer sur le mur\nPropriétés : largeur et aspect\nÉchap : annuler",
        "Clic derecho: colocar en pared\nPropiedades: anchura y aspecto\nEsc: cancelar"),
    "annotation_invalid": (
        "Choose a straight wall with enough room, without overlapping another opening.",
        "Scegli una parete rettilinea con spazio sufficiente, senza sovrapporre altre aperture.",
        "Choisissez un mur droit assez long, sans chevaucher une autre ouverture.",
        "Elige una pared recta con espacio suficiente, sin solapar otra abertura."),
    "annotation_selection_note": (
        "Right-click / drag: annotations only\nM: move · Right-click: place\nR: rotate marker/text or flip door\nDouble-click / Properties: edit\nDel: delete · Esc: cancel",
        "Clic destro / trascina: solo annotazioni\nM: sposta · Clic destro: posa\nR: ruota marker/testo o inverti porta\nDoppio clic / Proprietà: modifica\nDel: elimina · Esc: annulla",
        "Clic droit / glisser : annotations seules\nM : déplacer · Clic droit : placer\nR : tourner marqueur/texte ou inverser porte\nDouble clic / Propriétés : modifier\nSuppr : supprimer · Échap : annuler",
        "Clic derecho / arrastra: solo anotaciones\nM: mover · Clic derecho: colocar\nR: girar marcador/texto o invertir puerta\nDoble clic / Propiedades: editar\nSupr: eliminar · Esc: cancelar"),
    "annotation_help": (
        "Design Mode separates Structure from Annotations, each with its own selection. Structure selection never picks annotation paths or text. Marker draws dashed freehand or grid-following paths with independent color and graphical width. Door/Window ask for width before placement and snap to straight walls, including oblique ones. Doors support single, double and sliding leaves; hinge end and opening side are independent. Covered wall ink is hidden only visually: rooms, areas and Fill retain the full structure. Overlapping or unsupported openings are rejected. Select annotations to move with M, delete with Del or edit with a right double-click/Properties. R rotates markers/text by 90° and flips door opening side; windows stay aligned to walls. During a move, right-click places the preview. Host moves carry openings; deleting their support removes them in the same undo action. Save/reopen and PNG/Live/HTML include annotations. Physical wall thickness/materials remain future work.",
        "Design Mode distingue Struttura e Annotazioni, ciascuna con la propria selezione. La selezione strutturale ignora annotazioni e testo. Marker disegna percorsi tratteggiati liberi o sulla griglia con colore e spessore grafico propri. Porta/Finestra chiedono la larghezza prima della posa e si agganciano a pareti rettilinee, anche oblique. Le porte possono essere singole, doppie o scorrevoli; estremità della cerniera e lato di apertura sono indipendenti. Il tratto coperto è nascosto solo visivamente: ambienti, aree e Fill mantengono la struttura intera. Aperture sovrapposte o senza supporto vengono rifiutate. Seleziona annotazioni per spostare con M, eliminare con Del o modificare con doppio clic destro/Proprietà. R ruota marker/testo di 90° e inverte il lato di apertura delle porte; le finestre restano sulla parete. Durante lo spostamento un clic destro posa l'anteprima. Le aperture seguono la parete spostata; eliminando il supporto scompaiono nella stessa azione annullabile. Salvataggio/riapertura e PNG/Live/HTML includono le annotazioni. Spessore fisico e materiali delle pareti restano lavori futuri.",
        "Le mode conception sépare Structure et Annotations avec deux sélections. La sélection structurelle ignore annotations et texte. Marqueur dessine des traits discontinus libres ou sur grille, avec couleur et épaisseur propres. Porte/Fenêtre demandent la largeur avant placement et s'alignent sur les murs droits, même obliques. Portes simples, doubles ou coulissantes : charnière et côté d'ouverture indépendants. Seul le trait visible est masqué ; pièces, surfaces et remplissage gardent la structure entière. Les ouvertures superposées ou sans support sont refusées. Sélectionnez les annotations : M déplace, Suppr supprime, double clic droit/Propriétés modifie. R tourne marqueurs/textes de 90° ou inverse l'ouverture d'une porte ; les fenêtres restent alignées. Clic droit place un déplacement. Les ouvertures suivent leur mur ; supprimer leur support les supprime dans la même action annulable. Enregistrement et exports PNG/Live/HTML incluent les annotations. Épaisseur physique et matériaux des murs restent à venir.",
        "El modo diseño separa Estructura y Anotaciones con dos selecciones. La selección estructural ignora anotaciones y texto. Marcador dibuja trazos discontinuos libres o sobre cuadrícula, con color y grosor propios. Puerta/Ventana piden anchura antes de colocar y se ajustan a paredes rectas, incluso oblicuas. Puertas simples, dobles o correderas: bisagra y lado de apertura independientes. Solo se oculta el trazo visible; habitaciones, áreas y relleno mantienen toda la estructura. Se rechazan aberturas solapadas o sin soporte. Selecciona anotaciones: M mueve, Supr elimina, doble clic derecho/Propiedades edita. R gira marcadores/textos 90° o invierte la apertura de una puerta; las ventanas siguen alineadas. Clic derecho coloca al mover. Las aberturas siguen su pared; borrar su soporte las elimina en la misma acción reversible. Guardado y exportaciones PNG/Live/HTML incluyen anotaciones. Grosor físico y materiales de paredes quedan para el futuro."),
}


def dictionary(language):
    return {key: values[LANGUAGES.index(language)] for key, values in TEXT.items()}
