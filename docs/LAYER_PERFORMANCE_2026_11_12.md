# Reattivita dei livelli — 12 novembre 2026

Ogni comando dei livelli ricostruiva il disegno completo, anche quando cambiava
soltanto il livello attivo, il nome o il blocco. Il profilo iniziale comprendeva
validazioni ripetute, ricostruzione di muri/aperture/contorni dei testi e nuovi
indici geometrici. Il limite osservato era nel lavoro ripetuto della CPU.

Il controller ora conserva gli elementi Qt dei livelli invariati e ne aggiorna
visibilita e ordine. Le modifiche al disegno sostituiscono solo il livello
interessato; le modifiche ai testi riutilizzano geometria e indici dei muri.
Le cache sono limitate e dipendono dai valori effettivi e dalle dimensioni del
foglio. Non cambiano il formato del progetto o le regole geometriche.

## Misura sul progetto di prova

Una copia temporanea del progetto contiene **202 segmenti, 1 curva, 37 testi e
50 annotazioni**. Nella copia vengono creati un livello struttura e un livello
testi, con Layer 0 vuoto. Si alternano sei volte attivazione, visibilita, blocco,
rinomina e trasferimento dei 37 testi. Finestra Qt 1440 × 980; nessun altro test
Qt viene eseguito contemporaneamente alla misura.

| Operazione | Prima, mediana ms | Dopo, mediana ms |
| --- | ---: | ---: |
| Livello attivo | 2396,1 | 79,1 |
| Nascondi/mostra struttura | 2161,6 | 209,7 |
| Blocca/sblocca struttura | 2392,8 | 70,0 |
| Rinomina livello testi | 1690,8 | 75,8 |
| Trasferisci testi | 1742,1 | 105,6 |

Il tempo parte dalla richiesta al controller e include `processEvents()` dopo
il comando. Preparazione del documento, scelta nel dialogo e latenza fisica del
mouse sono escluse. Le mediane comprendono la prima operazione e le ripetizioni;
non costituiscono una garanzia di frame rate o un confronto con Draw.io. Mostrare
di nuovo la struttura richiede ancora l'aggiornamento delle maschere della griglia.

La misura iniziale usa il sorgente `d56a46e`; quella finale usa le modifiche di
questo intervento. Entrambe applicano la stessa sequenza e la stessa divisione
del progetto su copie temporanee. Campioni numerici:
[prima](audit-assets/layers-2026-11-12/before.json),
[dopo](audit-assets/layers-2026-11-12/after.json).

La procedura riutilizzabile e:

```powershell
.venv315/Scripts/python.exe tools/check_layer_performance.py "test_data/Wifi Test 2.csv" --output .private/layer-performance.json
```

Il tool isola impostazioni e memoria AP, copia il progetto con i file collegati
e verifica alla fine gli hash degli originali. Non salva il progetto, non avvia
scansioni e produce solo conteggi, versioni e tempi.

## Verifiche

- 327 regressioni passate su livelli, Load Plan, selezione e trasferimento,
  Ctrl/Shift, testi, simboli/AP, aperture, ridimensionamento, materiali/Priority
  e pan. I 12 test della cache sono stati ripetuti dopo l'ultima verifica grafica.
- Altre 179 regressioni passate su stampa, legende, JPEG e Live: **506 test
  distinti** complessivi, oltre alla ripetizione finale dei 12 test della cache.
- I nuovi test controllano identita degli elementi invariati, visibilita/ordine,
  sostituzione del solo livello modificato, riuso dopo modifiche ai testi,
  eliminazione, annulla/ripristina, ridimensionamento e sostituzione della scena.
- Controllati risultati indipendenti delle validazioni, invalidazione per input
  modificato, distinzione lista/tupla, limiti della cache, duplicati di simboli
  tra livelli, restrizioni Load Plan e rifiuto di geometria nascosta fuori foglio.
- Confronto pixel tra scena conservata e sorgente vettoriale con muri fisici,
  tratteggio e testo. Ruff e compilazione dei moduli modificati passati.

Queste verifiche riguardano il sorgente Python e Qt nativo. Nessun nuovo
eseguibile/ZIP e stato costruito e il pacchetto v1.5.0 resta invariato.
