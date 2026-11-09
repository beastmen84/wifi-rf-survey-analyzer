"""Survey plan origin choices and workflow help, EN/IT/FR/ES."""
LANGUAGES = ("en", "it", "fr", "es")
TEXT = {
    "loaded_plan_annotations_hint": (
        "Add text, markers, desks and symbols above the imported plan. Manage their layers and legend.",
        "Aggiungi testi, tracce, scrivanie e simboli sopra la pianta importata. Organizzali con livelli e legenda.",
        "Ajoutez textes, tracés, bureaux et symboles sur le plan importé. Gérez leurs calques et leur légende.",
        "Añade textos, trazos, escritorios y símbolos sobre el plano importado. Organízalos con capas y leyenda."),
    "loaded_plan_scale_hint": (
        "Calibrate the plan scale to add or edit annotations.",
        "Calibra la scala della pianta per inserire o modificare le annotazioni.",
        "Étalonnez le plan pour ajouter ou modifier les annotations.",
        "Calibra la escala del plano para añadir o editar anotaciones."),
    "loaded_plan_choose_annotation": (
        "Choose an annotation tool. Left-drag pans; Esc closes this panel. The imported plan stays fixed in the background.",
        "Scegli uno strumento di annotazione. Trascina col sinistro per spostare la vista; Esc chiude il pannello. La pianta importata resta fissa sullo sfondo.",
        "Choisissez un outil d'annotation. Glisser à gauche déplace la vue ; Échap ferme le panneau. Le plan importé reste fixe en arrière-plan.",
        "Elige una herramienta de anotación. Arrastra con el izquierdo para mover la vista; Esc cierra el panel. El plano importado permanece fijo al fondo."),
    "loaded_plan_annotations_only": (
        "Imported plans support free annotations only: no structure, doors or windows.",
        "Le piante importate consentono solo annotazioni libere: niente struttura, porte o finestre.",
        "Les plans importés acceptent uniquement les annotations libres : ni structure, ni portes, ni fenêtres.",
        "Los planos importados solo admiten anotaciones libres: sin estructura, puertas ni ventanas."),
    "draw_plan": ("Draw Plan", "Disegna pianta", "Dessiner un plan", "Dibujar plano"),
    "survey_plan_source": ("Floor plan", "Planimetria", "Plan", "Plano"),
    "survey_plan_file": ("Plan file", "File planimetria", "Fichier du plan", "Archivo del plano"),
    "survey_plan_browse": ("Browse…", "Sfoglia…", "Parcourir…", "Examinar…"),
    "survey_plan_choose_file": ("Select an image or PDF floor plan.", "Seleziona una planimetria immagine o PDF.",
        "Sélectionnez un plan image ou PDF.", "Selecciona un plano en imagen o PDF."),
    "survey_draw_hint": (
        "Start with a gridded sheet, automatic scale, Design Mode and Layers. The plan source is fixed for this survey.",
        "Parti da un foglio con griglia, scala automatica, Design Mode e Livelli. L'origine della pianta resta fissa per questo rilievo.",
        "Commencez avec une feuille quadrillée, une échelle automatique, le mode conception et les calques. La source du plan reste fixe pour ce relevé.",
        "Empieza con una hoja cuadriculada, escala automática, modo diseño y capas. El origen del plano queda fijo para este estudio."),
    "survey_load_hint": (
        "Use an existing image or PDF, then calibrate its scale to annotate it. Layers and a symbol legend are available; structure, doors and windows are excluded. To use another plan, create a new survey.",
        "Usa un'immagine o un PDF esistente, poi calibra la scala per annotarlo. Sono disponibili livelli e legenda dei simboli; struttura, porte e finestre sono escluse. Per usare un'altra pianta, crea un nuovo rilievo.",
        "Utilisez une image ou un PDF, puis étalonnez-le pour l'annoter. Calques et légende des symboles sont disponibles ; structure, portes et fenêtres sont exclues. Pour un autre plan, créez un nouveau relevé.",
        "Usa una imagen o un PDF y calibra la escala para anotarlo. Hay capas y leyenda de símbolos; se excluyen estructura, puertas y ventanas. Para usar otro plano, crea un estudio nuevo."),
    "survey_plan_invalid": ("The selected file could not be decoded as a floor plan.",
        "Il file selezionato non può essere letto come planimetria.", "Le fichier sélectionné ne peut pas être lu comme plan.",
        "El archivo seleccionado no se puede leer como plano."),
    "survey_plan_error": ("Could not create the survey plan: {error}", "Impossibile creare la planimetria del rilievo: {error}",
        "Impossible de créer le plan du relevé : {error}", "No se pudo crear el plano del estudio: {error}"),
    "survey_plan_help": (
        "New Survey asks for Draw Plan or Load Plan, together with units and Wi-Fi receiver. Draw Plan creates a sized gridded sheet with an automatic scale, Design Mode and Layers. Load Plan uses an image or PDF selected during setup and requires scale calibration; Annotations, Layers and symbol legends are available; structural drawing, doors and windows are excluded. Manual Boundaries, measurements, Live Map, Analysis, Print Plan and JPEG remain available in both modes. Fill/Auto Fill from closed drawing regions belongs to Draw Plan. The source is fixed for the survey: Project has no Load Plan action. Create a new survey to use another source. Canceling setup or a file selection, or failing to decode a file, preserves the current survey. Existing surveys reopen with their original plan type.",
        "Nuovo rilievo chiede Disegna pianta o Carica Pianta, insieme a unità e scheda Wi-Fi. Disegna pianta crea un foglio con dimensioni, griglia, scala automatica, Design Mode e Livelli. Carica Pianta usa un'immagine o PDF scelto nella creazione e richiede la calibrazione della scala; Sono disponibili Annotazioni, Livelli e legenda dei simboli; disegno strutturale, porte e finestre sono esclusi. Boundaries manuale, misure, Live Map, Analysis, Stampa Pianta e JPEG restano disponibili in entrambi. Fill/Auto Fill dagli ambienti disegnati appartiene a Disegna pianta. L'origine resta fissa: Progetto non ha il comando Carica Pianta. Per un'altra origine crea un nuovo rilievo. Annullare la creazione o la scelta del file, o un errore di lettura, conserva il rilievo corrente. I rilievi esistenti riaprono con lo stesso tipo di planimetria.",
        "Nouveau relevé propose Dessiner un plan ou Charger plan, avec unités et carte Wi-Fi. Dessiner crée une feuille dimensionnée, quadrillée et étalonnée avec outils de dessin et calques. Charger utilise une image ou un PDF choisi à la création, puis nécessite l'étalonnage ; annotations, calques et légende des symboles sont disponibles ; structure, portes et fenêtres sont exclues. Limites manuelles, mesures, Live Map, analyse, impression et JPEG restent disponibles dans les deux modes. Remplir/Remplissage auto des pièces dessinées appartient au dessin. La source reste fixe : Projet n'a pas d'action Charger plan. Créez un nouveau relevé pour une autre source. Annuler ou échouer à lire le fichier conserve le relevé courant. Les relevés existants conservent leur type de plan.",
        "Nuevo estudio ofrece Dibujar plano o Cargar plano, con unidades y adaptador Wi-Fi. Dibujar crea una hoja dimensionada, cuadriculada y calibrada con dibujo y capas. Cargar usa una imagen o PDF elegido al crear y requiere calibrar la escala; hay anotaciones, capas y leyenda de símbolos; se excluyen estructura, puertas y ventanas. Límites manuales, medidas, Live Map, análisis, impresión y JPEG siguen disponibles en ambos. Relleno automático de áreas dibujadas pertenece al dibujo. El origen queda fijo: Proyecto no tiene la acción Cargar plano. Crea un estudio nuevo para otro origen. Cancelar o fallar al leer el archivo conserva el estudio actual. Los estudios existentes conservan su tipo de plano."),
}


def dictionary(language):
    return {key: values[LANGUAGES.index(language)] for key, values in TEXT.items()}
