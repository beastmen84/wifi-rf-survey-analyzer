"""Circular design geometry and fixed measurement HUD."""
LANGUAGES = ("en", "it", "fr", "es")
TEXT = {
    "blank_tool_circle": ("Circle", "Cerchio", "Cercle", "Círculo"),
    "blank_tool_arc": ("Circular arc", "Arco circolare", "Arc de cercle", "Arco circular"),
    "curve_circle_title": ("Circle dimensions", "Dimensioni del cerchio", "Dimensions du cercle", "Dimensiones del círculo"),
    "curve_arc_title": ("Arc dimensions", "Dimensioni dell'arco", "Dimensions de l'arc", "Dimensiones del arco"),
    "curve_radius": ("Radius", "Raggio", "Rayon", "Radio"),
    "curve_edit_help": ("Select a curve and right-double-click it, or use the pencil action, to inspect and edit its radius or chord/sagitta. Dimensions use the survey's m/ft units; orientation and circle center or chord midpoint stay fixed.",
                        "Seleziona una curva e fai doppio clic destro, oppure usa la matita, per leggere e modificare raggio o corda/freccia. Le misure usano m/ft del rilievo; orientamento e centro del cerchio o della corda restano fissi.",
                        "Sélectionnez une courbe puis double-cliquez à droite, ou utilisez le crayon, pour consulter et modifier rayon ou corde/flèche. Les mesures utilisent les unités m/ft du relevé ; orientation et centre restent fixes.",
                        "Selecciona una curva y haz doble clic derecho, o usa el lápiz, para consultar y editar radio o cuerda/flecha. Usa las unidades m/ft del estudio; conserva orientación y centro del círculo o de la cuerda."),
    "curve_edit": ("Edit curve dimensions", "Modifica misure della curva", "Modifier les dimensions de la courbe", "Editar medidas de la curva"),
    "curve_edit_hint": ("Change the curve's dimensions. Its orientation and circle center or chord midpoint are preserved. The side is relative to the ordered chord A–B. Changes outside the sheet are rejected.",
                        "Modifica le misure della curva. Restano fissi l'orientamento e il centro del cerchio o della corda. Il lato è relativo alla direzione A–B della corda. Le modifiche fuori dal foglio vengono rifiutate.",
                        "Modifiez les dimensions. L'orientation et le centre du cercle ou de la corde restent fixes. Le côté se rapporte à la direction A–B. Les modifications hors de la feuille sont refusées.",
                        "Modifica las medidas. Conserva la orientación y el centro del círculo o de la cuerda. El lado se refiere a la dirección A–B. Los cambios fuera de la hoja se rechazan."),
    "curve_chord": ("Chord A–B", "Corda A–B", "Corde A–B", "Cuerda A–B"),
    "curve_sagitta": ("Sagitta", "Freccia", "Flèche", "Flecha"),
    "curve_side": ("Bend towards", "Curvatura verso", "Courbure vers", "Curvatura hacia"),
    "circle_selection_hint": ("M: move · Del: delete", "M: sposta · Del: cancella", "M : déplacer · Suppr : effacer", "M: mover · Supr: borrar"),
    "circle_move_hint": ("Right-click to place · Esc: cancel", "Clic destro posiziona · Esc annulla", "Clic droit pour placer · Échap annule", "Clic derecho coloca · Esc cancela"),
    "circle_rotation_help": ("A single complete circle has no rotation command, including its numeric preview and moving selection. R applies to arcs. When a group rotates, circle centers move with the group; circles do not acquire an orientation.",
                             "Un singolo cerchio completo non ha il comando di rotazione, nemmeno nell'anteprima numerica o durante lo spostamento. R si applica agli archi. Ruotando un gruppo, i centri dei cerchi si spostano col gruppo; i cerchi non acquisiscono un orientamento.",
                             "Un cercle complet seul n'a pas de commande de rotation, même dans l'aperçu ou pendant le déplacement. R s'applique aux arcs. Lorsqu'un groupe tourne, les centres des cercles suivent le groupe, sans orientation propre.",
                             "Un círculo completo aislado no tiene rotación, tampoco en la vista previa o al moverlo. R se aplica a los arcos. Al girar un grupo, los centros de los círculos siguen al grupo, sin orientación propia."),
    "curve_side_positive": ("Below the chord", "Sotto la corda", "Sous la corde", "Debajo de la cuerda"),
    "curve_side_negative": ("Above the chord", "Sopra la corda", "Au-dessus de la corde", "Encima de la cuerda"),
    "curve_circle_hint": (
        "Enter the radius. OK starts a preview that follows the cursor; right-click to place it.",
        "Inserisci il raggio. OK avvia l'anteprima che segue il cursore; clic destro per posizionarla.",
        "Saisissez le rayon. OK lance l'aperçu qui suit le pointeur ; clic droit pour le placer.",
        "Introduce el radio. OK inicia la vista previa que sigue al cursor; clic derecho para colocarla."),
    "curve_arc_hint": (
        "The chord is the distance A–B. The sagitta is the perpendicular distance from the chord midpoint to the arc. Repeat both values and the side to reproduce the curve. The side refers to the initial horizontal preview.",
        "La corda è la distanza A–B. La freccia è la distanza perpendicolare dal centro della corda all'arco. Ripeti queste due misure e il lato per replicare la curva. Il lato si riferisce all'anteprima iniziale orizzontale.",
        "La corde est la distance A–B. La flèche est la distance perpendiculaire du milieu de la corde à l'arc. Répétez ces mesures et le côté pour reproduire la courbe. Le côté concerne l'aperçu initial horizontal.",
        "La cuerda es la distancia A–B. La flecha es la distancia perpendicular del centro de la cuerda al arco. Repite ambas medidas y el lado para reproducir la curva. El lado corresponde a la vista previa horizontal inicial."),
    "curve_pull_hint": ("Move to bend · Right-click confirms · Esc cancels",
                        "Muovi per curvare · Clic destro conferma · Esc annulla",
                        "Bougez pour courber · Clic droit confirme · Échap annule",
                        "Mueve para curvar · Clic derecho confirma · Esc cancela"),
    "circle_tools_note": (
        "Right-drag from the center sets the radius. Right-click enters a radius, then another right-click places the preview. Left-drag pans; Alt bypasses snapping; Esc cancels.",
        "Trascina col destro dal centro per il raggio. Clic destro per inserire il raggio, poi altro clic destro per posizionare. Il sinistro sposta la vista; Alt sospende gli agganci; Esc annulla.",
        "Glissez à droite depuis le centre pour le rayon. Clic droit pour saisir le rayon, puis pour placer. Le bouton gauche déplace la vue ; Alt suspend l'alignement ; Échap annule.",
        "Arrastra con el derecho desde el centro para el radio. Clic derecho para introducir el radio y otro para colocar. El izquierdo desplaza la vista; Alt suspende el ajuste; Esc cancela."),
    "arc_tools_note": (
        "Right-drag A–B and release; move to set the bend, then right-click to confirm. A simple right-click enters chord and sagitta. During placement: R rotates, hold R + mouse for 5° steps. Esc cancels.",
        "Trascina A–B col destro e rilascia; muovi per curvare, poi clic destro conferma. Un clic destro semplice chiede corda e freccia. Nel posizionamento: R ruota, tieni R + mouse per scatti di 5°. Esc annulla.",
        "Glissez A–B à droite et relâchez ; bougez pour courber, puis clic droit pour confirmer. Un clic droit simple saisit corde et flèche. Au placement : R tourne, R maintenu + souris par pas de 5°. Échap annule.",
        "Arrastra A–B con el derecho y suelta; mueve para curvar y clic derecho confirma. Un clic derecho simple pide cuerda y flecha. Al colocar: R gira, mantén R + ratón para pasos de 5°. Esc cancela."),
    "plan_curves_help": (
        "Circle: right-drag from its center defines the radius; a simple right-click accepts an exact radius. Arc: right-drag A–B defines the chord, release and move perpendicularly to set its signed sagitta, then right-click confirms. A simple right-click accepts chord, sagitta and side; the previous dimensions are remembered during the survey. Numeric previews follow the cursor; arc previews support R tap/hold. Measurements stay at the top right of the drawing viewport. Circles and arcs snap to actual geometry, split at intersections and rejoin when obsolete cuts disappear. Selection, M, R, Del, undo/redo, closed-area fading, Boundaries Fill/Auto Fill and PNG/Live/HTML exports also support curves. Chord and sagitta remain parametric in the saved survey; curves are never stored as many short straight walls.",
        "Cerchio: trascina col destro dal centro per il raggio; il clic destro semplice chiede il raggio preciso. Arco: trascina A–B col destro per la corda, rilascia e muovi perpendicolarmente per la freccia con segno; clic destro conferma. Il clic semplice chiede corda, freccia e lato; le ultime misure restano disponibili durante il rilievo. Le anteprime numeriche seguono il cursore; quelle degli archi supportano R breve/prolungato. Le misure restano in alto a destra dell'area di disegno. Cerchi e archi si agganciano alla geometria reale, si spezzano agli incroci e si ricongiungono quando i tagli non servono più. Selezione, M, R, Del, annulla/ripeti, griglia attenuata nelle aree chiuse, Boundaries Fill/Auto Fill ed export PNG/Live/HTML supportano le curve. Corda e freccia restano parametriche nel rilievo salvato; le curve non sono memorizzate come tanti piccoli muri rettilinei.",
        "Cercle : glissez à droite depuis le centre pour le rayon ; un clic droit simple saisit le rayon exact. Arc : glissez A–B pour la corde, relâchez puis bougez perpendiculairement pour la flèche signée ; clic droit confirme. Un clic simple saisit corde, flèche et côté ; les dernières mesures sont mémorisées pendant le relevé. Les aperçus suivent le pointeur ; ceux des arcs acceptent R bref/maintenu. Les mesures restent en haut à droite. Les courbes s'alignent sur la géométrie réelle, se coupent aux intersections et se rejoignent quand les coupures deviennent inutiles. Sélection, M, R, Suppr, annuler/rétablir, grille atténuée, Remplir/Remplissage automatique et exports PNG/Live/HTML fonctionnent aussi. Les courbes restent paramétriques dans le relevé enregistré, sans être stockées comme de petits murs droits.",
        "Círculo: arrastra con el derecho desde el centro para el radio; un clic simple pide el radio exacto. Arco: arrastra A–B para la cuerda, suelta y mueve perpendicularmente para la flecha con signo; clic derecho confirma. Un clic simple pide cuerda, flecha y lado; recuerda las últimas medidas durante el estudio. Las vistas previas siguen al cursor; las de los arcos aceptan R breve/mantenida. Las medidas permanecen arriba a la derecha. Las curvas se ajustan a la geometría real, se dividen en intersecciones y se unen al desaparecer cortes innecesarios. Selección, M, R, Supr, deshacer/rehacer, rejilla atenuada, Rellenar/Relleno automático y exportaciones PNG/Live/HTML funcionan también. Las curvas siguen siendo paramétricas al guardar, sin almacenarse como pequeños muros rectos."),
}


def dictionary(language):
    return {key: values[LANGUAGES.index(language)] for key, values in TEXT.items()}
