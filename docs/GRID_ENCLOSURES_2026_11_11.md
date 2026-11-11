# Chiusure fisiche e attenuazione della griglia

Il controllo sul progetto aggiornato distingue due problemi:

- Le facce dei muri possono chiudere un ambiente grazie allo spessore, anche
  quando le linee di riferimento non formano un anello. Il precedente fade
  considerava soltanto queste ultime e saltava una sala con parete curva.
- Un raccordo fra vetro e cemento aveva un varco reale di circa 1,16 cm.
  Attraverso quel punto i corridoi comunicavano con l'esterno. Il programma non
  deve chiuderlo inventando una tolleranza o cambiando le dimensioni del progetto.

La griglia ora integra le chiusure fisiche ottenute dai corpi dei muri, prima
dei tagli delle porte e finestre. Usa i contorni vettoriali originali, comprese
le curve. I contorni delle aree racchiuse contribuiscono con winding positivo:
questo evita falsi buchi dovuti a unioni booleane fra maschere coincidenti.
Le isole di muro interne restano coperte dal disegno dei muri.

Ogni livello visibile viene valutato separatamente. La maschera viene
ricostruita solo se cambiano geometria, gruppi di muri o dimensioni del foglio;
i corpi già calcolati dal renderer/picker vengono riusati. Nessun nuovo calcolo
di chiusura viene eseguito durante il paint o il pan.

Questo modifica il fade, **non la topologia editabile**: selezione delle stanze,
misure e vincoli continuano a usare le connessioni esatte delle linee. Una zona
attenuata grazie allo spessore non diventa automaticamente una stanza editabile.

## Verifiche

- 617 casi di regressione esistenti su regioni, livelli, curve, materiali,
  spessori, dialoghi e navigazione.
- 12 casi mirati, superati sia sul percorso nativo sia sul renderer software
  headless: chiusure attraverso lo spessore, varchi reali anche subpixel,
  concavità aperte, curve, regioni annidate, maschere sovrapposte e pixel della
  griglia, cache, undo/redo, limiti geometrici e livelli nascosti/indipendenti.
- Progetto reale di 202 segmenti, una curva, 37 testi e 50 annotazioni: la sala
  curva viene riconosciuta dal fade senza modificare il progetto.
- Una copia di revisione estende un solo estremo del muro in vetro di
  1,1582 cm. Restano invariati gli altri segmenti, curva, testi e annotazioni.
  Dopo salvataggio e riapertura, tutti i 37 centri dei testi e quattro punti nei
  corridoi risultano interni; tre punti esterni restano esclusi.
- Navigazione reale sulla GPU integrata: nove paint, zero componenti diverse
  fra pan e ridisegno completo della copia verificata.
- Ruff sui file modificati e controllo whitespace. Tutti i file originali
  mantengono il loro SHA-256; dati e immagini del progetto restano fuori dal commit.

Versione invariata. Nessuna build EXE o pubblicazione.
