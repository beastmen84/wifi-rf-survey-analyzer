"""Drawing layer controls and help, EN/IT/FR/ES."""
LANGUAGES = ("en", "it", "fr", "es")
TEXT = {
    "layers_title": ("Layers", "Livelli", "Calques", "Capas"),
    "layer_visible": ("Show", "Vis.", "Voir", "Ver"),
    "layer_locked": ("Lock", "Bloc.", "Verrou", "Bloq."),
    "layer_name": ("Layer name", "Nome livello", "Nom du calque", "Nombre de capa"),
    "layer_add": ("New", "Nuovo", "Nouveau", "Nueva"),
    "layer_rename": ("Rename", "Rinomina", "Renommer", "Renombrar"),
    "layer_delete": ("Delete", "Elimina", "Supprimer", "Eliminar"),
    "layer_up": ("Up", "Su", "Monter", "Subir"),
    "layer_down": ("Down", "Giù", "Descendre", "Bajar"),
    "layer_move_selection": ("Move selection to layer…", "Sposta selezione su livello…", "Déplacer la sélection vers un calque…", "Mover selección a capa…"),
    "layer_order_hint": (
        "Top layers are drawn above the others. Select a row to edit that layer; drag rows to reorder.",
        "I livelli in cima sono disegnati sopra gli altri. Seleziona una riga per modificarne il livello; trascina le righe per riordinarle.",
        "Les calques du haut sont dessinés au-dessus. Sélectionnez une ligne pour modifier son calque ; faites glisser pour réordonner.",
        "Las capas superiores se dibujan encima. Selecciona una fila para editar su capa; arrastra para ordenar."),
    "layer_base_hint": ("Layer 0 is always visible and cannot be deleted.", "Il livello 0 è sempre visibile e non può essere eliminato.",
        "Le calque 0 reste visible et ne peut pas être supprimé.", "La capa 0 siempre está visible y no se puede eliminar."),
    "layer_readonly": ("This layer is hidden or locked. Select a visible, unlocked layer to draw.",
        "Questo livello è nascosto o bloccato. Per disegnare seleziona un livello visibile e sbloccato.",
        "Ce calque est masqué ou verrouillé. Choisissez un calque visible et déverrouillé pour dessiner.",
        "Esta capa está oculta o bloqueada. Para dibujar elige una capa visible y desbloqueada."),
    "layer_invalid": ("Layer change rejected. Check names, drawing limits and complete door/window support.",
        "Modifica del livello non applicata. Verifica nomi, limiti del disegno e supporto completo di porte/finestre.",
        "Modification refusée. Vérifiez noms, limites du dessin et support complet des portes/fenêtres.",
        "Cambio rechazado. Revisa nombres, límites del dibujo y soporte completo de puertas/ventanas."),
    "layer_select_first": ("Select drawing elements and provide a visible, unlocked destination layer.",
        "Seleziona elementi del disegno e un livello di destinazione visibile e sbloccato.",
        "Sélectionnez des éléments et un calque de destination visible et déverrouillé.",
        "Selecciona elementos y una capa de destino visible y desbloqueada."),
    "layer_delete_confirm": ("Delete this layer and its drawing? Undo can restore it.",
        "Eliminare questo livello e il suo disegno? Puoi ripristinarli con Annulla.",
        "Supprimer ce calque et son dessin ? Annuler permet de les restaurer.",
        "¿Eliminar esta capa y su dibujo? Deshacer permite restaurarlos."),
    "layers_help": (
        "The Layers column is available in Survey outside Design Mode. Layer 0 can be renamed and locked, but stays visible and cannot be deleted. New layers can be hidden, locked and reordered; the top row is drawn above the others. Selecting a row makes it active. Drawing, selection and erasing operate only on that visible, unlocked layer. Structural intersections, joins and closed rooms remain within a layer. Furniture/text/markers can reference visible structure in other layers without changing it; doors/windows stay with their supporting walls. Move selection transfers objects, or structural fragments with their supported openings, to an editable layer. Layer properties and edits support undo/redo and survive save/reopen; existing surveys start entirely on Layer 0. Print Plan, JPEG, saved plan PNG, Live Map and HTML exports use visible layers in the same order. Measurement points, operational AP data, RF statistics and Boundaries masks are independent of layer visibility. Expanding/collapsing the panel does not dirty the survey.",
        "La colonna Livelli è disponibile nel Survey anche fuori da Design Mode. Il livello 0 si può rinominare e bloccare, ma resta visibile e non è eliminabile. I nuovi livelli si possono nascondere, bloccare e riordinare; la riga in cima è disegnata sopra le altre. Selezionare una riga rende attivo il livello. Disegno, selezione e gomma lavorano solo sul livello attivo visibile e sbloccato. Intersezioni, fusioni e chiusura degli ambienti restano all'interno di un livello. Arredi/testo/marker possono usare riferimenti alla struttura visibile su altri livelli senza modificarla; porte/finestre restano con le pareti di supporto. Sposta selezione trasferisce oggetti o tratti strutturali con le aperture supportate verso un livello modificabile. Proprietà e modifiche supportano annulla/ripeti e salvataggio/riapertura; i rilievi esistenti partono interamente sul livello 0. Stampa Pianta, JPEG, PNG salvato, Live Map ed export HTML usano i livelli visibili nello stesso ordine. Punti di misura, dati AP operativi, statistiche RF e maschere Boundaries sono indipendenti dalla visibilità. Aprire/chiudere il pannello non modifica il rilievo.",
        "La colonne Calques reste disponible dans Survey hors du mode conception. Le calque 0 peut être renommé et verrouillé, mais reste visible et ne peut pas être supprimé. Les nouveaux calques peuvent être masqués, verrouillés et réordonnés ; celui du haut est dessiné au-dessus. La ligne sélectionnée devient active. Dessin, sélection et gomme agissent uniquement sur le calque actif visible et déverrouillé. Intersections, jonctions et pièces fermées restent dans un même calque. Mobilier/texte/marqueurs peuvent utiliser la structure visible d'autres calques comme référence sans la modifier ; portes/fenêtres restent avec leur mur. Déplacer la sélection transfère objets ou fragments avec leurs ouvertures vers un calque modifiable. Propriétés et modifications sont annulables et enregistrées ; les anciens relevés commencent sur le calque 0. Impression, JPEG, PNG enregistré, Live Map et HTML utilisent les calques visibles dans le même ordre. Mesures, données AP, statistiques RF et masques Boundaries restent indépendants. Ouvrir/fermer la colonne ne modifie pas le relevé.",
        "La columna Capas está disponible en Survey fuera del modo diseño. La capa 0 se puede renombrar y bloquear, pero siempre está visible y no se elimina. Las nuevas capas se pueden ocultar, bloquear y ordenar; la fila superior se dibuja encima. La fila seleccionada es la activa. Dibujo, selección y goma actúan solo sobre la capa activa visible y desbloqueada. Intersecciones, uniones y áreas cerradas quedan dentro de cada capa. Muebles/texto/marcadores pueden referenciar estructura visible de otras capas sin modificarla; puertas/ventanas permanecen con su pared. Mover selección transfiere objetos o fragmentos con sus aberturas a una capa editable. Propiedades y cambios se pueden deshacer y guardar; los estudios antiguos empiezan en la capa 0. Impresión, JPEG, PNG guardado, Live Map y HTML usan las capas visibles en el mismo orden. Mediciones, datos AP, estadísticas RF y máscaras Boundaries son independientes. Abrir/cerrar la columna no modifica el estudio."),
}


def dictionary(language):
    return {key: values[LANGUAGES.index(language)] for key, values in TEXT.items()}
