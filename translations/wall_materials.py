"""Wall material catalog and schematic rendering controls."""
LANGUAGES = ('en','it','fr','es')
TEXT = {
    'wall_shared_changed': ('Changing shared thickness, material or appearance also updates the existing wall. Thickness changes may move connected rooms. Review before confirming.','Cambiare spessore, materiale o aspetto condivisi aggiorna anche la parete già posata. Lo spessore può spostare gli ambienti collegati. Controlla prima di confermare.','Changer l’épaisseur, le matériau ou l’aspect communs modifie aussi le mur existant. L’épaisseur peut déplacer les pièces voisines. Vérifiez avant de confirmer.','Cambiar espesor, material o aspecto compartidos actualiza también el muro existente. El espesor puede mover habitaciones conectadas. Revisa antes de confirmar.'),
    'wall_side_shared_hint': ('Shared wall: inherits existing thickness, material and appearance.','Parete condivisa: eredita spessore, materiale e aspetto esistenti.','Mur commun : reprend épaisseur, matériau et aspect existants.','Muro compartido: hereda espesor, material y aspecto existentes.'),
    'wall_material': ('Material','Materiale','Matériau','Material del muro'),
    'wall_material_apply_all': ('Apply to all sides','Applica a tutti i lati','Appliquer à tous les côtés','Aplicar a todos los lados'),
    'wall_material_apply_all_hint': (
        "Copy this side's material to all walls of this shape with positive thickness. Each side keeps its thickness and appearance. Shared walls still require confirmation.",
        'Copia il materiale di questo lato su tutti i muri della forma con spessore positivo. Ogni lato mantiene spessore e aspetto grafico. I muri condivisi richiedono comunque conferma.',
        'Copiez le matériau de ce côté sur tous les murs de cette forme ayant une épaisseur positive. Chaque côté conserve son épaisseur et son aspect. Les murs communs exigent toujours une confirmation.',
        'Copia el material de este lado a todos los muros de esta forma con espesor positivo. Cada lado conserva su espesor y representación. Los muros compartidos siguen requiriendo confirmación.'),
    'wall_material_apply_all_scope': (
        'Select a side with positive thickness in one complete shape. For multiple selected shapes, choose a side belonging to only one shape or open that shape by double-clicking inside it.',
        'Seleziona un lato con spessore positivo di una forma completa. Se sono selezionate più forme, scegli un lato che appartiene a una sola forma oppure aprila con un doppio clic al suo interno.',
        'Sélectionnez un côté avec une épaisseur positive dans une forme complète. Pour plusieurs formes sélectionnées, choisissez un côté appartenant à une seule forme ou ouvrez-la par un double clic à l’intérieur.',
        'Selecciona un lado con espesor positivo de una forma completa. Si hay varias formas seleccionadas, elige un lado que pertenezca a una sola forma o ábrela con doble clic en su interior.'),
    'wall_pattern': ('Appearance','Aspetto grafico','Aspect graphique','Representación'),
    'wall_material_hint': (
        'Choose a side, then its material and appearance. A thickness greater than zero is required. Patterns are schematic; materials do not change RF analysis.',
        'Seleziona un lato, poi materiale e aspetto. Serve uno spessore maggiore di zero. I retini sono schematici; i materiali non modificano l’analisi RF.',
        'Sélectionnez un côté, puis son matériau et son aspect. Une épaisseur positive est nécessaire. Les motifs sont schématiques et ne modifient pas l’analyse RF.',
        'Selecciona un lado y su material y aspecto. Se necesita un espesor positivo. Los patrones son esquemáticos y no modifican el análisis RF.'),
    'wall_invalid_material': ('Invalid wall material or appearance.','Materiale o aspetto della parete non valido.','Matériau ou aspect du mur invalide.','Material o aspecto del muro no válido.'),
    'wall_shared_material_conflict': ('Conflicting materials on a shared wall. Choose one material and appearance for both faces.','Materiali diversi su una parete condivisa. Scegli un materiale e un aspetto comuni alle due facce.','Matériaux incompatibles sur un mur commun. Choisissez un matériau et un aspect pour les deux faces.','Materiales en conflicto en un muro compartido. Elige un material y aspecto para ambas caras.'),
    'wall_material_help': (
        'Wall Edit stores material and appearance per side, for straight and curved walls. Select a numbered side or a table row, set a positive thickness, then choose its material. Automatic appearance uses the material color and schematic hatch; you can override the hatch. Shared faces inherit the same material and appearance, and changing them requires acknowledgment. Cancel discards changes; Apply is one undoable edit. These properties survive save/reopen, splits, moves, rotations and layer transfers. Editor, Live Map, HTML, print and JPEG use the same clipped vector patterns, including door/window gaps. Old walls remain neutral until assigned a material. This is descriptive drawing metadata, without automatic RF attenuation or construction certification.',
        'Wall Edit salva materiale e aspetto per lato, su pareti dritte e curve. Seleziona un lato numerato o una riga, imposta uno spessore positivo e scegli il materiale. Aspetto automatico usa colore e retino schematico del materiale; puoi cambiare il retino. Le facce condivise ereditano materiale e aspetto comuni: le modifiche richiedono conferma. Annulla scarta tutto; Applica è una sola azione annullabile. Le proprietà restano dopo salvataggio, riapertura, tagli, spostamenti, rotazioni e cambi di livello. Editor, Live Map, HTML, stampa e JPEG usano gli stessi retini vettoriali, ritagliati anche in corrispondenza di porte e finestre. Le pareti precedenti restano neutre finché non assegni un materiale. Sono dati descrittivi del disegno, senza attenuazione RF automatica o certificazione edilizia.',
        'Wall Edit enregistre matériau et aspect par côté, droit ou courbe. Sélectionnez un côté numéroté ou une ligne, définissez une épaisseur positive puis le matériau. Le mode automatique utilise sa couleur et son motif schématique ; le motif peut être remplacé. Les faces communes héritent du même matériau et aspect ; toute modification exige confirmation. Annuler abandonne tout ; Appliquer est une seule action annulable. Les propriétés persistent après sauvegarde, découpe, déplacement, rotation et transfert de calque. Éditeur, carte, HTML, impression et JPEG utilisent les mêmes motifs vectoriels découpés aux ouvertures. Les anciens murs restent neutres. Ces données descriptives ne donnent aucune atténuation RF automatique ni certification de construction.',
        'Wall Edit guarda material y aspecto por lado, recto o curvo. Selecciona un lado numerado o una fila, define un espesor positivo y el material. El aspecto automático usa su color y patrón esquemático; puedes cambiar el patrón. Las caras compartidas heredan el mismo material y aspecto; los cambios requieren confirmación. Cancelar descarta todo; Aplicar es una acción deshacible. Se conserva al guardar, cortar, mover, girar y cambiar de capa. Editor, mapa, HTML, impresión y JPEG usan los mismos patrones vectoriales recortados en las aberturas. Los muros antiguos siguen neutros. Son datos descriptivos, sin atenuación RF automática ni certificación constructiva.'),
}
MATERIAL_NAMES = {
    'unspecified': ('Unspecified','Non specificato','Non précisé','Sin especificar'),
    'wood': ('Wood','Legno','Bois','Madera'),
    'clay_block': ('Hollow clay blocks','Laterizio forato','Blocs de terre cuite creux','Bloques cerámicos huecos'),
    'brick': ('Solid clay bricks','Mattoni pieni','Briques pleines','Ladrillo macizo'),
    'concrete_block': ('Concrete blocks','Blocchi in calcestruzzo','Blocs de béton','Bloques de hormigón'),
    'aerated_concrete': ('Aerated concrete blocks','Calcestruzzo cellulare','Béton cellulaire','Hormigón celular'),
    'drywall': ('Plasterboard / drywall','Cartongesso','Plaques de plâtre','Placa de yeso'),
    'concrete': ('Concrete','Calcestruzzo','Béton','Hormigón'),
    'reinforced_concrete': ('Reinforced concrete','Calcestruzzo armato','Béton armé','Hormigón armado'),
    'stone': ('Stone masonry','Muratura in pietra','Maçonnerie en pierre','Mampostería de piedra'),
    'glass': ('Glass','Vetro','Verre','Vidrio'),
    'metal': ('Metal panels','Pannelli metallici','Panneaux métalliques','Paneles metálicos'),
    'insulation': ('Insulating panels','Pannelli isolanti','Panneaux isolants','Paneles aislantes'),
}
PATTERN_NAMES = {
    'auto': ('Automatic (material)','Automatico (materiale)','Automatique (matériau)','Automático (material)'),
    'solid': ('Solid fill','Uniforme','Uni','Uniforme'),
    'diagonal': ('Diagonal hatch','Tratteggio diagonale','Hachures diagonales','Rayado diagonal'),
    'cross': ('Cross hatch','Tratteggio incrociato','Hachures croisées','Rayado cruzado'),
    'dots': ('Stipple','Puntinato','Pointillé','Punteado'),
    'brick': ('Staggered blocks','Blocchi sfalsati','Blocs décalés','Bloques alternados'),
    'grid': ('Grid','Griglia','Quadrillage','Cuadrícula'),
    'wood': ('Paired diagonal lines','Diagonali accoppiate','Diagonales doubles','Diagonales dobles'),
}
TEXT.update({'wall_material_'+k:v for k,v in MATERIAL_NAMES.items()})
TEXT.update({'wall_pattern_'+k:v for k,v in PATTERN_NAMES.items()})


def dictionary(language):
    return {key:values[LANGUAGES.index(language)] for key,values in TEXT.items()}
