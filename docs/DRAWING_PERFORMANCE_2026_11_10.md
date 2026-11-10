# Prestazioni del disegno — 2026-11-10

Il rallentamento è stato riprodotto su una copia temporanea del progetto fornito:
93 segmenti rettilinei, 19 testi e 6 annotazioni, senza livelli espliciti.
CSV, PNG, dati delle scansioni e file di lock originali restano invariati.
Questo rapporto contiene solo quantità e misure; nessuna geometria o immagine
del progetto reale viene aggiunta al repository.

## Causa e correzione

Il costo principale del pan era il ritaglio della griglia durante ogni paint:
Qt applicava ripetutamente le maschere complesse delle stanze all'intero percorso
delle linee. Nel profilo iniziale occupava circa 3,50 dei 3,77 secondi della
sequenza di pan; i materiali dei muri occupavano circa 0,17 secondi.

La griglia ora prepara le porzioni interne ed esterne quando cambiano le regioni
o lo stile. Ogni linea mantiene il proprio percorso vettoriale; durante il paint
vengono disegnate solo quelle che intersecano l'area esposta. La griglia attenuata
nelle stanze, i colori, gli intervalli e gli spessori rimangono disponibili senza
ricorrere a una cache raster del dispositivo.

Anche i progetti senza livelli espliciti usano la cache del documento già
validato. Prima ogni lettura di segmenti o curve decodificava e normalizzava di
nuovo i dati. Le letture restituiscono copie indipendenti; modifiche ai metadati,
cambio sessione e cambio livello invalidano i dati conservati.

La finestra degli spessori evita l'anteprima iniziale poi subito scartata e
riutilizza i percorsi dei materiali quando cambia soltanto il lato selezionato.
Una variazione di spessore, materiale, priorità o direzione ricostruisce il
risultato; la conferma mantiene le verifiche di geometria e transazione.

## Misure sul progetto fornito

Qt nativo, finestra 1440 × 980, zoom 2,5, DPR effettivo 1,5. Mediana di tre
esecuzioni senza profiler; ogni interazione comprende l'elaborazione degli eventi
e il ridisegno richiesto. Il confronto precedente ripristina soltanto i tre
comportamenti modificati attraverso un adattatore temporaneo, senza cambiare i
file di lavoro. Le misure dipendono dalla macchina e non sono soglie di test.
[Dati prima/dopo](audit-assets/drawing-performance-2026-11-10/results.json).

| Operazione | Prima | Dopo | Riduzione |
| --- | ---: | ---: | ---: |
| Apertura progetto | 340 ms | 223 ms | 34% |
| 5 letture complete del modello | 186 ms | 15 ms | 92% |
| 8 movimenti del cursore | 541 ms | 66 ms | 88% |
| 8 trascinamenti del pan | 3.774 ms | 389 ms | 90% |
| 8 movimenti dell'anteprima di posa | 150 ms | 99 ms | 34% |
| Apertura e annullamento revisione muri | 336 ms | 317 ms | 6% |
| Revisione, conferma e applicazione nuova forma | 1.320 ms | 833 ms | 37% |

Il pan impiega circa **9,7 volte meno tempo** nella stessa sequenza. Ogni
trascinamento comprende pressione, movimento, rilascio e ridisegni: questi tempi
non rappresentano la durata di un singolo frame. La conferma automatica della
revisione esclude il tempo impiegato dall'utente per scegliere gli spessori.

Benchmark ripetibile su una copia temporanea:

```powershell
.venv315/Scripts/python.exe tools/check_drawing_performance.py `
  --project "percorso/progetto.csv" `
  --output .private/drawing-performance.json
```

Se l'angolo inferiore destro del foglio è occupato, specificare una posizione
libera con `--rectangle X Y WIDTH HEIGHT`, in coordinate della planimetria.
Il risultato JSON contiene solo quantità e tempi. Lo strumento verifica gli hash
dei file sorgenti e usa impostazioni e memoria AP temporanee, senza scansioni RF.

## Il PNG accanto al CSV

Nei progetti disegnati il salvataggio genera anche l'immagine della planimetria.
Il CSV conserva muri, testi e annotazioni modificabili e il riferimento al PNG;
l'immagine è la rappresentazione materializzata della pianta. Conservare insieme
i file del progetto. Il PNG fornito misura 3250 × 1500 pixel e circa 72 kB:
il collo di bottiglia rilevato è il paint della griglia, non il peso dell'immagine.

## Verifiche

- Prime verifiche su griglia, livelli, rettangoli e materiali durante il pan:
  **95 test passati**.
- Nuove regressioni e suite mirate su revisione dei lati e materiali:
  **96 test passati**. Copie indipendenti delle letture, invalidazione di tutti i
  metadati del disegno, pan e pan inverso, zoom frazionari, cambio tema e ripristino
  della griglia, selezione di un lato senza ricalcolo, ricostruzione dopo modifica
  dello spessore. I confronti del pan verificano i pixel rispetto a un ridisegno
  completo nella stessa posizione e l'invarianza del modello.

- Suite completa: **2.649 test e 479 subtest passati**, exit code 0,
  327,80 secondi. [Output](audit-assets/drawing-performance-2026-11-10/full-suite.txt).
- **18 casi aggiuntivi** con DPR effettivo 1,25 / 1,5 / 2: due temi e tre zoom,
  pan e pan inverso. **54 confronti grafici con zero componenti di colore
  differenti** rispetto al ridisegno completo nella stessa posizione.
  [Dati e risultati](audit-assets/drawing-performance-2026-11-10/results.json).
- Parsing Python, Ruff sui file interessati con esclusione delle convenzioni
  preesistenti `E741/F401/F811`, e `git diff --check` passati.
- Hash SHA-256 dei **quattro file** originali in `test_data/` invariati, compreso
  il lock preesistente. Cartella esclusa dal commit.

Nessuna nuova build EXE o modifica della versione 1.4.0.
