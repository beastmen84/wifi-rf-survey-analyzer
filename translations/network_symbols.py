"""Draw Plan network apparatus, stable references and automatic legends."""
LANGUAGES = ("en", "it", "fr", "es")
TEXT = {
    "plan_legend": ("Legend", "Legenda", "Légende", "Leyenda"),
    "symbol_numbered_group": ("Numbered markers", "Marcatori numerati", "Repères numérotés", "Marcadores numerados"),
    "symbol_network_group": ("Network equipment", "Apparati di rete", "Équipements réseau", "Equipos de red"),
    "symbol_generic_group": ("Generic signs", "Segni generici", "Signes génériques", "Signos genéricos"),
    "symbol_numbered": ("Automatic number", "Numero automatico", "Numéro automatique", "Número automático"),
    "object_symbol_rack": ("Rack", "Rack", "Baie réseau", "Rack de red"),
    "object_symbol_wifi_ap": ("Wi-Fi AP", "Wi-Fi AP", "Point d'accès Wi-Fi", "AP Wi-Fi"),
    "symbol_position": ("Position", "Posizione", "Position", "Posición"),
    "legend_description": ("Description", "Descrizione", "Description", "Descripción"),
    "legend_number": ("Number", "Numero", "Numéro", "Número"),
    "legend_table": ("Table {number} · {symbol}", "Tabella {number} · {symbol}", "Tableau {number} · {symbol}", "Tabla {number} · {symbol}"),
    "legend_hint": (
        "Tables follow the placed symbols. Numbers are unique per shape across all layers and remain stable. Edit descriptions here; hidden/locked layers are read-only. Print/JPEG includes visible layers only.",
        "Le tabelle seguono i simboli posizionati. I numeri sono unici per forma fra tutti i livelli e restano stabili. Modifica qui le descrizioni; livelli nascosti/bloccati sono di sola lettura. Stampa/JPEG include solo i livelli visibili.",
        "Les tableaux suivent les symboles placés. Les numéros restent uniques par forme dans tous les calques. Modifiez les descriptions ; les calques masqués/verrouillés restent en lecture seule. Impression/JPEG inclut les calques visibles.",
        "Las tablas siguen los símbolos colocados. Los números son únicos por forma entre todas las capas y permanecen estables. Edita descripciones; capas ocultas/bloqueadas son de solo lectura. Impresión/JPEG incluye capas visibles."),
    "legend_show_hidden": ("Show hidden layers (read-only)", "Mostra livelli nascosti (sola lettura)", "Afficher les calques masqués (lecture seule)", "Mostrar capas ocultas (solo lectura)"),
    "legend_empty": ("Place numbered markers, Rack or Wi-Fi AP symbols in Design Mode to create legend tables.",
        "Posiziona marcatori numerati, Rack o Wi-Fi AP in Design Mode per creare le tabelle della legenda.",
        "Placez des repères numérotés, des baies ou des points d'accès dans le mode conception pour créer les tableaux.",
        "Coloca marcadores numerados, Rack o AP Wi-Fi en modo diseño para crear las tablas."),
    "legend_number_existing": ("Number existing visible markers", "Numera marcatori visibili esistenti", "Numéroter les repères visibles existants", "Numerar marcadores visibles existentes"),
    "legend_stale": ("The survey changed while the legend was open. Reopen it to edit the current symbols.",
        "Il rilievo è cambiato mentre la legenda era aperta. Riaprila per modificare i simboli attuali.",
        "Le relevé a changé pendant l'ouverture de la légende. Rouvrez-la pour modifier les symboles actuels.",
        "El estudio cambió con la leyenda abierta. Vuelve a abrirla para editar los símbolos actuales."),
    "legend_include": ("Include legend pages", "Includi pagine legenda", "Inclure les pages de légende", "Incluir páginas de leyenda"),
    "legend_preview_page": ("Preview page", "Pagina in anteprima", "Page d'aperçu", "Página de vista previa"),
    "legend_plan_page": ("Plan", "Planimetria", "Plan", "Plano"),
    "legend_page_number": ("Legend · page {number}", "Legenda · pagina {number}", "Légende · page {number}", "Leyenda · página {number}"),
    "legend_visible_export": ("Symbols on visible layers", "Simboli nei livelli visibili", "Symboles des calques visibles", "Símbolos en capas visibles"),
    "legend_replace_files": ("Replace these existing legend images?\n{files}", "Sostituire queste immagini della legenda?\n{files}",
        "Remplacer ces images de légende existantes ?\n{files}", "¿Reemplazar estas imágenes de leyenda?\n{files}"),
    "legend_jpeg_saved": ("Plan saved: {path} · {count} legend images", "Pianta salvata: {path} · {count} immagini legenda",
        "Plan enregistré : {path} · {count} images de légende", "Plano guardado: {path} · {count} imágenes de leyenda"),
    "ap_symbol_assign": ("Assign AP symbol…", "Assegna simbolo AP…", "Associer un symbole AP…", "Asignar símbolo AP…"),
    "ap_symbol_unassign": ("Unassign symbol", "Scollega simbolo", "Dissocier le symbole", "Desvincular símbolo"),
    "ap_symbol_convert": ("Convert existing placement", "Converti posizione esistente", "Convertir le placement existant", "Convertir posición existente"),
    "ap_symbol_hint": (
        "Choose a Wi-Fi AP symbol on a visible, unlocked layer. Each symbol belongs to one physical AP; each AP uses one symbol. Place a Wi-Fi AP symbol in Design Mode if the list is empty. Its center supplies the analysis position.",
        "Scegli un simbolo Wi-Fi AP su un livello visibile e sbloccato. Ogni simbolo appartiene a un AP fisico e ogni AP usa un simbolo. Se la lista è vuota, posiziona un Wi-Fi AP in Design Mode. Il centro fornisce la posizione all'analisi.",
        "Choisissez un symbole Wi-Fi AP sur un calque visible et déverrouillé. Un symbole correspond à un AP physique et chaque AP utilise un symbole. Si la liste est vide, placez un symbole en mode conception. Son centre fournit la position à l'analyse.",
        "Elige un símbolo AP Wi-Fi en una capa visible y desbloqueada. Cada símbolo corresponde a un AP físico y cada AP usa un símbolo. Si la lista está vacía, coloca un símbolo en modo diseño. Su centro aporta la posición al análisis."),
    "ap_symbol_error": ("Cannot change AP assignment: {error}", "Impossibile modificare l'assegnazione AP: {error}",
        "Impossible de modifier l'association AP : {error}", "No se pudo cambiar la asignación AP: {error}"),
    "network_symbols_help": (
        "Draw Plan only: Symbols separates numbered circle/square/diamond/triangle markers, Rack/Wi-Fi AP equipment and generic signs. Automatic numbering is per shape across all layers; numbers remain stable after moves and deletions. Numbers stay upright, fit the interior and use a readable external badge when needed. Description is shared with Legend. Existing unnumbered markers are preserved; Legend can number visible, unlocked ones. In AP Groups, Assign AP symbol links an existing visible, unlocked Wi-Fi AP symbol one-to-one with a physical AP. Assigned symbols have a colored fill and AP label. Moving the symbol updates exact AP coordinates; deleting/unassigning it clears the position without deleting the AP group. Undo restores the binding and position. Hidden layers affect drawing visibility, not RF analysis. Existing placements can be converted at the same coordinates. Load Plan retains direct AP positioning and has no Legend action. Legend creates automatic tables with readonly references and editable descriptions. Print Plan/JPEG can include visible-layer legend pages, paginate long descriptions and preview individual pages. JPEG saves the plan plus -legend-01.jpg and subsequent pages at the same paper/DPI. Cancel preserves existing files; a multi-image export is staged and recoverable as a set.",
        "Solo Disegna pianta: Simboli separa marcatori cerchio/quadrato/rombo/triangolo numerati, apparati Rack/Wi-Fi AP e segni generici. La numerazione automatica è per forma fra tutti i livelli; i numeri restano stabili dopo spostamenti e cancellazioni. Restano dritti, si adattano all'interno e usano un cartellino esterno leggibile quando serve. La descrizione è condivisa con Legenda. I marcatori vecchi senza numero restano invariati; Legenda può numerare quelli visibili e sbloccati. In Gruppi AP, Assegna simbolo AP collega un Wi-Fi AP esistente, visibile e sbloccato a un solo AP fisico e viceversa. I simboli assegnati hanno riempimento colorato ed etichetta AP. Lo spostamento aggiorna le coordinate esatte; cancellare/scollegare libera la posizione senza eliminare il gruppo AP. Annulla ripristina collegamento e posizione. Nascondere un livello modifica la visibilità, non l'analisi RF. Le posizioni esistenti si possono convertire mantenendo le coordinate. Carica Pianta mantiene il posizionamento AP diretto e non mostra Legenda. Legenda crea tabelle automatiche con riferimenti in sola lettura e descrizioni modificabili. Stampa Pianta/JPEG possono includere pagine di legenda dei livelli visibili, distribuire descrizioni lunghe su più pagine e mostrarle in anteprima. JPEG salva la pianta più -legend-01.jpg e successive con lo stesso formato/DPI. Annullare conserva i file; l'esportazione multipla viene preparata e recuperata come insieme.",
        "Uniquement Dessiner un plan : symboles numérotés par forme, baies/AP Wi-Fi et signes génériques. Les numéros restent stables dans tous les calques, droits et lisibles, avec une étiquette extérieure si nécessaire. La description est partagée avec la légende. Les anciens repères restent inchangés et peuvent être numérotés explicitement. Associer un symbole AP lie un symbole existant visible/déverrouillé à un AP physique, un à un. Remplissage coloré et nom indiquent l'association. Déplacer met à jour la position exacte ; supprimer/dissocier efface la position sans supprimer l'AP. Annuler restaure le lien. Masquer un calque ne change pas l'analyse RF. Les anciens placements peuvent être convertis. Charger plan conserve le placement AP direct sans légende. La légende génère des tableaux automatiques à références fixes et descriptions modifiables. Impression/JPEG peuvent inclure les pages des calques visibles et paginer les textes longs. Le JPEG crée le plan et -legend-01.jpg puis les pages suivantes, au même papier/DPI. Annuler conserve les fichiers ; l'export multiple est préparé et récupérable en ensemble.",
        "Solo Dibujar plano: símbolos numerados por forma, Rack/AP Wi-Fi y signos genéricos. Los números permanecen estables entre capas, rectos y legibles, con etiqueta exterior si hace falta. La descripción se comparte con Leyenda. Los marcadores antiguos se conservan y se pueden numerar explícitamente. Asignar símbolo AP enlaza un símbolo existente visible/desbloqueado con un AP físico, uno a uno. Relleno de color y nombre indican el vínculo. Mover actualiza la posición exacta; borrar/desvincular elimina la posición sin borrar el AP. Deshacer restaura el vínculo. Ocultar una capa no cambia el análisis RF. Las posiciones antiguas se pueden convertir. Cargar plano mantiene el posicionamiento AP directo sin Leyenda. La leyenda genera tablas automáticas con referencias fijas y descripciones editables. Impresión/JPEG pueden incluir páginas de capas visibles y paginar textos largos. El JPEG guarda el plano y -legend-01.jpg y siguientes al mismo papel/DPI. Cancelar conserva archivos; la exportación múltiple se prepara y recupera como conjunto."),
}


def dictionary(language):
    return {key: values[LANGUAGES.index(language)] for key, values in TEXT.items()}
