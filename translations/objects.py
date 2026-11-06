"""Freely placed desks and symbols, EN/IT/FR/ES."""
LANGUAGES = ("en", "it", "fr", "es")
TEXT = {
    "annotation_desk": ("Desks", "Scrivanie", "Bureaux", "Escritorios"),
    "annotation_symbol": ("Symbols", "Simboli", "Symboles", "Símbolos"),
    "object_desk_square": ("Square desk", "Scrivania quadrata", "Bureau carré", "Escritorio cuadrado"),
    "object_desk_rectangle": ("Rectangular desk", "Scrivania rettangolare", "Bureau rectangulaire", "Escritorio rectangular"),
    "object_desk_l": ("L desk · unequal sides", "Scrivania a L · lati diversi", "Bureau en L · côtés inégaux", "Escritorio en L · lados distintos"),
    "object_desk_l_equal": ("L desk · equal sides", "Scrivania a L · lati uguali", "Bureau en L · côtés égaux", "Escritorio en L · lados iguales"),
    "object_desk_round": ("Round desk", "Scrivania tonda", "Bureau rond", "Escritorio redondo"),
    "object_symbol_circle": ("Circle", "Cerchio", "Cercle", "Círculo"),
    "object_symbol_x": ("X symbol", "Simbolo X", "Symbole X", "Símbolo X"),
    "object_symbol_plus": ("Plus symbol", "Simbolo più", "Symbole plus", "Símbolo más"),
    "object_symbol_square": ("Square symbol", "Simbolo quadrato", "Symbole carré", "Símbolo cuadrado"),
    "object_symbol_triangle": ("Triangle", "Triangolo", "Triangle", "Triángulo"),
    "object_symbol_diamond": ("Diamond", "Rombo", "Losange", "Rombo"),
    "object_symbol_star": ("Star", "Stella", "Étoile", "Estrella"),
    "object_symbol_arrow": ("Arrow", "Freccia", "Flèche", "Flecha"),
    "object_outline_color": ("Outline color", "Colore bordo", "Couleur du contour", "Color del borde"),
    "object_outline_width": ("Outline width", "Spessore bordo", "Épaisseur du contour", "Grosor del borde"),
    "object_fill_color": ("Fill color", "Colore riempimento", "Couleur de remplissage", "Color de relleno"),
    "object_fill_enabled": ("Fill", "Riempi", "Remplir", "Rellenar"),
    "object_depth": ("Depth", "Profondità", "Profondeur", "Profundidad"),
    "object_side_a": ("Side A", "Lato A", "Côté A", "Lado A"),
    "object_side_b": ("Side B", "Lato B", "Côté B", "Lado B"),
    "object_size": ("Side length", "Lunghezza lato", "Longueur du côté", "Longitud del lado"),
    "object_symbol_size": ("Size", "Dimensione", "Taille", "Tamaño"),
    "object_diameter": ("Diameter", "Diametro", "Diamètre", "Diámetro"),
    "object_arm_depth": ("Desktop depth", "Profondità piano", "Profondeur du plateau", "Fondo del tablero"),
    "object_properties_hint": (
        "Choose a variant and dimensions in survey units. Outline color/width and fill color are independent. Disable Fill for an empty outline. Objects are annotations and do not change rooms or RF analysis.",
        "Scegli variante e misure nelle unità del rilievo. Colore e spessore del bordo sono separati dal colore di riempimento. Disattiva Riempi per il solo contorno. Sono annotazioni: non cambiano ambienti o analisi RF.",
        "Choisissez une variante et les dimensions dans les unités du relevé. Couleur et épaisseur du contour sont séparées du remplissage. Désactivez Remplir pour un contour vide. Ces annotations ne changent ni pièces ni analyse RF.",
        "Elige variante y medidas en las unidades del estudio. Color y grosor del borde son independientes del relleno. Desactiva Rellenar para dejar solo el contorno. Son anotaciones: no cambian habitaciones ni análisis RF."),
    "object_place_note": (
        "Right-click: place\nR: rotate 90°\nProperties: dimensions, outline, fill\nLeft-drag: pan · Esc: cancel",
        "Clic destro: posa\nR: ruota di 90°\nProprietà: misure, bordo, riempimento\nTrascina col sinistro: pan · Esc: annulla",
        "Clic droit : placer\nR : tourner de 90°\nPropriétés : dimensions, contour, fond\nGlisser à gauche : déplacer · Échap : annuler",
        "Clic derecho: colocar\nR: girar 90°\nPropiedades: medidas, borde, relleno\nArrastrar izquierdo: desplazar · Esc: cancelar"),
    "object_round_note": (
        "Right-click: place\nProperties: diameter, outline, fill\nLeft-drag: pan · Esc: cancel",
        "Clic destro: posa\nProprietà: diametro, bordo, riempimento\nTrascina col sinistro: pan · Esc: annulla",
        "Clic droit : placer\nPropriétés : diamètre, contour, fond\nGlisser à gauche : déplacer · Échap : annuler",
        "Clic derecho: colocar\nPropiedades: diámetro, borde, relleno\nArrastrar izquierdo: desplazar · Esc: cancelar"),
    "object_selection_note": (
        "M: move · Right-click: place\nR: rotate objects / flip swing doors\nDouble-click / Properties: edit\nDel: delete · Esc: cancel",
        "M: sposta · Clic destro: posa\nR: ruota oggetti / inverti porte a battente\nDoppio clic / Proprietà: modifica\nDel: elimina · Esc: annulla",
        "M : déplacer · Clic droit : placer\nR : tourner objets / inverser portes battantes\nDouble clic / Propriétés : modifier\nSuppr : supprimer · Échap : annuler",
        "M: mover · Clic derecho: colocar\nR: girar objetos / invertir puertas batientes\nDoble clic / Propiedades: editar\nSupr: eliminar · Esc: cancelar"),
    "object_round_selection_note": (
        "M: move · Right-click: place\nDouble-click / Properties: edit\nDel: delete · Esc: cancel",
        "M: sposta · Clic destro: posa\nDoppio clic / Proprietà: modifica\nDel: elimina · Esc: annulla",
        "M : déplacer · Clic droit : placer\nDouble clic / Propriétés : modifier\nSuppr : supprimer · Échap : annuler",
        "M: mover · Clic derecho: colocar\nDoble clic / Propiedades: editar\nSupr: eliminar · Esc: cancelar"),
    "object_invalid": ("The object does not fit inside the sheet.", "L'oggetto non rientra nel foglio.",
        "L'objet ne tient pas dans la feuille.", "El objeto no cabe en la hoja."),
    "objects_help": (
        "Desks and Symbols are free annotations on generated sheets. Desks offer square, rectangular, unequal/equal-sided L and round variants; L desks also have an editable desktop depth. Symbols offer circle, X, plus, square, triangle, diamond, star and arrow. Icon rows choose the variant. Dimensions use survey m/ft; outline color and width are independent of an optional fill color. After OK, the centered preview follows the cursor; right-click places it. R rotates non-round previews and selected objects by 90°, including while moving. Round objects have no orientation. Vertices and centers use drawing/grid magnets; Alt suspends them. Select Annotations picks the outline or interior, while open notches stay empty. M moves, Del/annotation eraser deletes, double-click/Properties edits; undo/redo restores changes. Objects do not require walls or cut structural ink, change room closure/area or influence RF results. They persist and appear in PNG, Live Map, HTML and Print Plan.",
        "Scrivanie e Simboli sono annotazioni libere sui fogli generati. Le scrivanie sono quadrate, rettangolari, a L con lati diversi/uguali e tonde; per le L è modificabile anche la profondità del piano. I simboli sono cerchio, X, più, quadrato, triangolo, rombo, stella e freccia. Le icone scelgono la variante. Le misure usano m/ft del rilievo; colore e spessore del bordo sono separati dal riempimento opzionale. Dopo OK, l'anteprima centrata segue il cursore; clic destro posa. R ruota di 90° anteprime e oggetti selezionati non tondi, anche nello spostamento. Gli oggetti tondi non hanno orientamento. Vertici e centri usano gli agganci al disegno/griglia; Alt li sospende. Seleziona annotazioni sceglie contorno o interno; gli incavi aperti restano vuoti. M sposta, Del/gomma annotazioni elimina, doppio clic/Proprietà modifica; annulla/ripeti ripristina. Non richiedono pareti e non modificano struttura, chiusura o area degli ambienti, né i risultati RF. Si salvano e compaiono in PNG, Live Map, HTML e Stampa Pianta.",
        "Bureaux et Symboles sont des annotations libres sur les feuilles générées. Bureaux carrés, rectangulaires, en L à côtés inégaux/égaux ou ronds ; profondeur du plateau réglable pour les L. Symboles : cercle, X, plus, carré, triangle, losange, étoile et flèche. Les icônes choisissent la variante. Dimensions en m/ft du relevé ; couleur et épaisseur du contour séparées du fond facultatif. Après OK, l'aperçu centré suit le pointeur ; clic droit place. R tourne de 90° les aperçus et objets non ronds, aussi au déplacement. Les objets ronds n'ont pas d'orientation. Sommets et centres utilisent les alignements dessin/grille ; Alt les suspend. La sélection des annotations reconnaît contour et intérieur, pas les encoches vides. M déplace, Suppr/gomme supprime, double clic/Propriétés modifie ; annuler/rétablir restaure. Aucun mur requis, aucun trait structurel coupé, aucune modification des pièces, surfaces ou résultats RF. Enregistrement et sorties PNG, carte en direct, HTML et impression incluent ces objets.",
        "Escritorios y Símbolos son anotaciones libres en hojas generadas. Escritorios cuadrados, rectangulares, en L de lados distintos/iguales o redondos; fondo del tablero editable para las L. Símbolos: círculo, X, más, cuadrado, triángulo, rombo, estrella y flecha. Los iconos eligen la variante. Medidas en m/ft del estudio; color y grosor del borde separados del relleno opcional. Tras OK, la vista previa centrada sigue al cursor; clic derecho coloca. R gira 90° objetos no redondos, también durante el movimiento. Los redondos no tienen orientación. Vértices y centros usan ajustes al dibujo/cuadrícula; Alt los suspende. Seleccionar anotaciones reconoce contorno e interior, sin seleccionar huecos abiertos. M mueve, Supr/borrador elimina, doble clic/Propiedades edita; deshacer/rehacer restaura. No requieren paredes y no modifican la estructura, las habitaciones, sus áreas ni los resultados RF. Persisten y aparecen en PNG, mapa en vivo, HTML e impresión."),
}


def dictionary(language):
    return {key: values[LANGUAGES.index(language)] for key, values in TEXT.items()}
