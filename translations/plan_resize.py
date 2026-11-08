"""Origin-anchored Draw Plan page controls."""
LANGUAGES = ('en','it','fr','es')
TEXT = {
    'resize_plan': ('Resize','Resize','Redimensionner','Redimensionar'),
    'resize_scale': ('Calibrate the plan before resizing in physical units.','Calibra la pianta prima di ridimensionarla in unità fisiche.','Étalonnez le plan avant de modifier ses dimensions physiques.','Calibra el plano antes de cambiar sus dimensiones físicas.'),
    'resize_grid_limit': ('The grid is too dense for this page size. Increase grid square size first.','La griglia è troppo fitta per questa pagina. Aumenta prima la misura del quadrato.','La grille est trop dense pour cette page. Augmentez la taille des carreaux.','La cuadrícula es demasiado densa. Aumenta primero el tamaño del cuadrado.'),
    'resize_title': ('Resize drawn plan','Ridimensiona la pianta','Redimensionner le plan','Redimensionar plano'),
    'resize_hint': (
        'The top-left origin stays fixed. The page grows or shrinks only at the right and bottom; coordinates, calibration and grid spacing do not change.',
        "L'origine in alto a sinistra resta fissa. La pagina cresce o cala solo a destra e in basso; coordinate, calibrazione e passo della griglia non cambiano.",
        "L'origine en haut à gauche reste fixe. La page change uniquement à droite et en bas ; coordonnées, étalonnage et grille sont conservés.",
        'El origen superior izquierdo permanece fijo. La página cambia solo a derecha y abajo; coordenadas, calibración y cuadrícula no cambian.'),
    'resize_valid': ('All saved content fits. Resize can be undone.','Tutti i contenuti rientrano. Il ridimensionamento può essere annullato.','Tous les éléments tiennent. Le redimensionnement peut être annulé.','Todo el contenido cabe. El cambio se puede deshacer.'),
    'resize_limit': ('Invalid page size: each side must be between 1 and 4096 pixels at the current calibration.','Dimensioni non valide: ogni lato deve essere fra 1 e 4096 pixel con la calibrazione attuale.','Dimensions incorrectes : entre 1 et 4096 pixels par côté avec cet étalonnage.','Tamaño inválido: cada lado debe tener entre 1 y 4096 píxeles con la calibración actual.'),
    'resize_content': ('This size would cut drawing content, including hidden layers or physical wall thickness.','Questa misura taglierebbe elementi del disegno, inclusi livelli nascosti o spessori delle pareti.','Cette taille couperait le dessin, y compris les calques cachés ou les murs physiques.','Este tamaño cortaría el dibujo, incluidas capas ocultas o el espesor de muros.'),
    'resize_points': ('This size would exclude a measurement point or AP position.','Questa misura escluderebbe un punto di rilevamento o una posizione AP.','Cette taille exclurait une mesure ou une position AP.','Este tamaño excluiría una medición o una posición AP.'),
    'resize_mask': ('This size would cut the Boundaries mask.','Questa misura taglierebbe la maschera Boundaries.','Cette taille couperait le masque Boundaries.','Este tamaño cortaría la máscara Boundaries.'),
    'resize_draw_only': ('Resize is available only in Draw Plan.','Resize è disponibile solo in Draw Plan.','Redimensionner est disponible uniquement pour les plans dessinés.','Redimensionar solo está disponible en Dibujar plano.'),
    'resize_busy': ('Finish the current capture before resizing.','Termina il rilevamento in corso prima di ridimensionare.','Terminez la capture avant de redimensionner.','Finaliza la captura antes de redimensionar.'),
    'resize_done': ('Page resized. Coordinates and calibration preserved.','Pagina ridimensionata. Coordinate e calibrazione conservate.','Page redimensionnée. Coordonnées et étalonnage conservés.','Página redimensionada. Coordenadas y calibración conservadas.'),
    'resize_help': (
        'Draw Plan: Project → Resize changes page width and height from the fixed top-left origin. It preserves pixel density, RF coordinates, APs and grid spacing. Shrinking is blocked if it would cut any drawing layer, physical wall, point, AP or Boundaries mask. Undo/redo also checks newly acquired evidence before restoring an older page size. Legend is in the Analysis toolbar heading.',
        "Draw Plan: Project → Resize modifica larghezza e altezza dall'origine fissa in alto a sinistra. Conserva densità dei pixel, coordinate RF, AP e passo della griglia. La riduzione è bloccata se taglia livelli del disegno, pareti fisiche, punti, AP o maschere Boundaries. Anche annulla/ripristina controlla i dati acquisiti dopo il ridimensionamento prima di tornare alla pagina precedente. Legend è nell'intestazione della barra Analysis.",
        "Dessiner un plan : Projet → Redimensionner conserve l'origine en haut à gauche, la densité, les coordonnées RF/AP et la grille. Une réduction qui coupe dessin, murs physiques, mesures, AP ou masque est refusée. Annuler/rétablir contrôle aussi les nouvelles mesures. Légende est dans l'en-tête Analyse.",
        'Dibujar plano: Proyecto → Redimensionar conserva el origen superior izquierdo, densidad, coordenadas RF/AP y cuadrícula. Se bloquea una reducción que corte dibujo, muros, mediciones, AP o máscara. Deshacer/rehacer también comprueba las nuevas mediciones. Leyenda está en la cabecera Análisis.'),
}


def dictionary(language):
    return {key:values[LANGUAGES.index(language)] for key,values in TEXT.items()}
