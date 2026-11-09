# Faccia residua dopo la cancellazione di una stanza — 2026-11-09

Eliminando i lati esterni di una stanza adiacente, la sua faccia interna del
muro comune restava come segmento autonomo. La pulizia ora rimuove quella
faccia quando non delimita piu una stanza e la faccia opposta delimita ancora
la stanza conservata. Il riferimento residuo viene normalizzato, mantenendo
spessore, materiale e area della stanza rimasta.

Gomma e cancellazione della selezione applicano la stessa operazione. Porte e
finestre sulla faccia rimossa vengono riferite alla faccia fisica conservata:
identita, posizione visibile, verso e dimensioni restano invariati. Eliminare
il muro fisico continua invece a eliminare le aperture che non hanno supporto.
Undo/redo e salvataggio includono la pulizia nella normale transazione.

La modifica riguarda le nuove cancellazioni. Non riscrive automaticamente i
progetti gia salvati con facce residue e non elimina segmenti aperti estranei
alla stanza cancellata.

## Verifiche

- Riproduzione confrontata con il codice del commit precedente: una stanza con
  condivisione parziale lasciava **7 segmenti**, inclusa la faccia superflua;
  dopo la correzione ne restano **4**. Area conservata: **40.000 px quadrati**.
  [Risultato](audit-assets/wall-face-2026-11-09/regression.json).
- **32 nuovi casi di regressione**: entrambi i lati di cancellazione, rotazioni,
  condivisione parziale, materiali, stanze curve, segmenti aperti intenzionali,
  cinque tipi di aperture, gomma/Canc, selezione, undo/redo e riapertura.
- Verifica finale mirata, incluse le suite pareti e giunzioni: **164 test
  passati**. [Output](audit-assets/wall-face-2026-11-09/focused.txt).
- La suite completa iniziale ha prodotto **2.519 test e 479 subtest passati**
  e un errore nel test preesistente dello spostamento di segmenti: confronto
  esatto tra `200` e `199.99999999999997`. Il test e passato isolatamente,
  ma ha ripresentato lo scarto nella verifica combinata. Il suo controllo usa
  ora una tolleranza assoluta di `1e-7` px, conservando le verifiche di unione,
  colore, selezione, picking e cronologia. Nessuna modifica alla geometria
  applicativa per questo arrotondamento. Il test passa nella verifica finale
  combinata. La suite completa non e stata ripetuta dopo questo adeguamento
  del test e l'aggiunta dei due casi curvi.
  [Output iniziale](audit-assets/wall-face-2026-11-09/full-suite-initial.txt).
- Parsing Python, Ruff sui file interessati con esclusione delle convenzioni
  preesistenti `E741/F401/F811`, e `git diff --check` passati.

Prove Qt con disegni sintetici; nessuna nuova build EXE. I problemi successivi
di precedenza visiva dei materiali e sovrapposizione all'angolo sono esclusi
da questa modifica, in attesa della conferma dell'utente.
