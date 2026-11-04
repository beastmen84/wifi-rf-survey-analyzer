# Audit di precisione e idoneità al rilascio 1.1.0

Audit iniziale: 2026-11-03, sorgente `8941b0d`.
Correzioni e verifica conclusiva: 2026-11-04, successive a `53262ef`.
Ambiente: CPython 3.15.2 x64, Windows, dipendenze di `requirements-lock.txt`.

**Esito aggiornato: implementate e verificate le correzioni R1-R11.** I rilievi
iniziali sono conservati sotto come evidenza del comportamento precedente.
La verifica software e quella di freschezza reale sono positive; resta distinta
la decisione sulla release, che richiede le prove sul campo e sul pacchetto
indicate in fondo. Non viene dichiarata una precisione assoluta dell'RSSI.

## Correzioni e prove dopo l'intervento

| ID | Risultato implementato | Verifica di regressione |
| --- | --- | --- |
| R1 | Notifiche native complete/fail e timeout, lettura BSS con errori espliciti, timestamp originali e deduplica per adapter/BSS/timestamp. Cache esclusa; RSSI uguali con timestamp nuovi restano validi. | Richieste fallite, timeout, notifica di altra scheda, duplicati e cache non danno campioni freschi. Prova hardware sotto. |
| R2 | Identità SSID esatta, spazi/parole preservati, BSS nascosti mantenuti, lunghezza nativa esplicita e byte originali in esadecimale. | Parser lswifi/netsh, SSID vuoti, NUL interno e byte non UTF-8; selezione/relevance non normalizza gli spazi. |
| R3 | Range massimo fra aggregati e raw associati; raw parziale non sostituisce l'evidenza già nota. Advisor richiede raw fresco completo e coerente. | L'intervallo -90..-40 resta instabile; raw assente/parziale non autorizza proposte precise. |
| R4 | HT40 usa la direzione secondaria; 80+80 non diventa 160. Geometria sconosciuta o 320 senza allineamento comprovato resta non calcolabile. | Overlap HT40 noto, direzione mancante e larghezze non rappresentabili; rischio sconosciuto grigio/«non determinabile» anche nei report. |
| R5 | Banda solo se univoca e coerente con frequenza e canale primario. | Canale 5 senza banda, frequenze/bande contraddittorie e canali non validi bloccano le prescrizioni. |
| R6 | `physical_confirmed` separato dal nome/lock; azione esplicita per confermare il gruppo fisico. Euristica MAC non elimina vicini; ruoli e metadati restano associati. | Gruppi automatici versus confermati, rinomina senza conferma, salvataggio, conferma UI, filtri/configurazioni Live/export e metadati dei BSSID separati. |
| R7 | Valori finiti e intervalli controllati prima delle mutazioni; BSS invalido isolato e cattura marcata incompleta. | NaN/inf, coordinate/RSSI/contatori incoerenti, import e aggiunta falliti senza alterare il rilievo. |
| R8 | Un ricevitore per cattura, preferendo quello connesso; provenienza salvata e denominatore cinque. Confronti multi-ricevitore bloccati nell'advisor. | Selezione deterministica, conteggi 5/5, round-trip adapter/raw e dataset con ricevitori misti. |
| R9 | Politica di confidenza condivisa: provenienza/freschezza sconosciuta vale zero, senza promozione implicita al 100%. | File precedenti leggibili, confidenza assente/NaN/incoerente, mappe e analisi conservative. |
| R10 | Prova potenza solo con luoghi separati almeno 2 m, scala valida e copertura alternativa in tutti i punti misurati serviti dall'AP. | ID ripetuti nella stessa posizione e piccoli spostamenti non bastano; caso positivo con punti realmente separati. |
| R11 | Ledger dei punti nei metadati CSV: esito vuoto verificato distinto da errore e assenza di misura, senza RSSI inventato. Rescan sostituisce per ID dopo validazione. | Salvataggio/apertura/cancellazione, tabella e marker grigio, dashboard e report; errore/unverified non crea falso vuoto, rescan nello stesso secondo preserva il nuovo punto. |

Verifica conclusiva del 2026-11-04:

- **453 test e 475 sottotest passati**, sia offscreen (14.65 s) sia Windows
  nativo (15.47 s), exit 0. Inclusi 59 nuovi casi parametrizzati rispetto ai 394
  test iniziali e aggiornamento dei fixture al contratto di provenienza reale.
- Avvio tramite `main.main()`, completamento del worker iniziale e costruzione
  del workspace con tre tab verificati su Windows nativo, exit 0.
- Report HTML/PDF generati in IT/EN/FR/ES; nove pagine per il dataset sintetico,
  testo e impaginazione verificati, con ispezione visiva delle pagine italiane
  e del tab analisi. Provenienza del segnale visibile nelle tabelle.
- `pip check`, Ruff essenziale (`E9,F63,F7,F82`) e controllo del diff superati.
  Nessuna modifica alle dipendenze runtime rispetto alla migrazione precedente.
- Prova reale con **lo scanner di produzione corretto**: cinque completamenti,
  una scheda, nove reti, **37 campioni freschi unici accettati**, **sei letture
  da cache escluse**, zero duplicati accettati, zero campioni antecedenti alla
  propria richiesta, zero record invalidi. Età mediana 2.276 s, massima 2.779 s;
  durata 22.26 s. Questi tempi descrivono la prova, non una garanzia temporale.
  Una prima prova corretta aveva accettato 48 osservazioni uniche, senza cache.
  Prima della correzione erano state riusate 24 delle 54 letture. Sono conteggi
  di prove separate, con reti osservate variabili; non un confronto di sensibilità
  radio né un incremento di precisione in dB. Conservati solo conteggi anonimi.
- Fallback netsh eseguito sul sistema reale: una osservazione nello snapshot,
  esito `unverified`, dBm `estimated`, freschezza `unknown` e confidenza zero.
  La prova verifica il contratto conservativo del fallback, senza confrontare
  la sensibilità o la copertura con una cattura nativa svolta in un altro momento.
- Nessun diagnostico Qt/COM nel passaggio nativo conclusivo; il precedente
  `0x8001010d` intermittente resta aperto perché non è stata dimostrata la causa.

Compatibilità: CSV e raw schema 2 precedenti rimangono leggibili. Le colonne
opzionali e il ledger aggiungono provenienza senza fabbricarla per i vecchi dati;
i punti senza timestamp/raw adeguati richiedono una nuova misura prima di
ottenere suggerimenti operativi precisi. I gruppi manuali precedenti conservano
la semantica esplicita; i nuovi gruppi automatici richiedono conferma fisica.

## Verifiche dell'audit iniziale, prima delle correzioni

- Revisione del percorso acquisizione -> normalizzazione -> aggregazione ->
  CSV/raw -> qualità -> mappe -> raccomandazioni -> report.
- Suite corrente rieseguita: **394 test e 475 sottotest passati**, offscreen,
  in 23.81 secondi. Questo risultato non copre i casi avversi seguenti.
- **14 scenari sintetici riprodotti**, raggruppati nei rilievi sotto. Includono
  errori dimostrati e limiti di modello; non sono 14 difetti indipendenti.
- Controllo reale della freschezza BSS sul computer corrente, usando gli stessi
  cinque tentativi e l'attesa di 1.5 secondi dell'app: 54 letture, 30 coppie
  BSS/timestamp uniche, **24 letture ripetute** e 10 BSS con almeno un riuso.
  Età mediana delle osservazioni: 1.087 s; massima: 7.169 s. Nessun errore di
  richiesta scan in questa prova. Sono stati conservati solo conteggi aggregati,
  senza nomi di reti o indirizzi dei dispositivi.
- Contratto delle API verificato nella documentazione Microsoft; verifiche RF
  confrontate con documentazione tecnica Cisco. Le prove non equivalgono a
  calibrazione metrologica del ricevitore o validazione hardware 6 GHz.

## Blocchi prioritari

### R1 - P1: letture da cache contate come scansioni nuove

Riferimenti: `wifi/scanner.py:233`, `wifi/scanner.py:649`,
`app_core/constants.py:21`.

`WLAN.scan` avvia la richiesta asincrona. L'app ignora eventuali eccezioni,
attende 1.5 secondi e legge la lista BSS senza attendere la notifica di
completamento. `samples_seen` conta le righe e non le osservazioni nuove.
Il timestamp BSS disponibile in lswifi non viene conservato nel raw.

Prova sintetica: cinque chiamate scan fallite e la stessa lista BSS disponibile
in cache producono `samples_seen=5`, `samples_total=5`, `scan_confidence=1.0`.
Anche cinque duplicati del solo `scan_attempt=1` producono confidenza 1.0.
La prova hardware conferma il riuso dei timestamp, senza simulare errori.

Conseguenza: campioni vecchi possono essere attribuiti a una nuova posizione;
la ripetizione della cache può sembrare stabilità del segnale e affidabilità.

Correzione: attendere `scan_complete`/`scan_fail` con timeout, distinguere
fallimento e risultato vuoto, conservare adapter/timestamp/tentativo e contare
osservazioni fresche uniche. La cache va dichiarata, non promossa a nuova misura.

Riferimento esterno: [Microsoft WlanScan](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/nf-wlanapi-wlanscan).
La documentazione richiede l'attesa della notifica o del timeout di 4 secondi
prima di interrogare i risultati.

### R2 - P1: perdita di BSS nascosti e alterazione dell'identità SSID

Riferimenti: `wifi/scanner.py:358`, `wifi/scanner.py:368`,
`wifi/scanner.py:710`, `maps/quality.py:405`.

La pulizia generica rimuove spazi e interpreta parole come `unknown`, `none`
e `--` come dati mancanti, anche quando sono veri nomi SSID. La conversione
di `" Office "` in `"Office"` confonde due identità distinte. In lswifi un SSID
vuoto fa scartare l'intero BSS, compresi BSSID, RSSI, canale e larghezza validi.
Nel parser netsh un'intestazione SSID vuota non viene riconosciuta: nel caso
`Office` seguito da un BSS nascosto entrambi vengono attribuiti a `Office`.

Conseguenza: scompaiono interferenti reali e possono essere unite reti diverse.
Questo errore avviene prima delle successive regole conservative dell'advisor.

Correzione: separare identità originale e nome visualizzato; non usare i valori
segnaposto dei metadati per gli SSID. Conservare i BSS nascosti e includerli
nel contesto RF usando il BSSID, senza inventare un nome o unirli fra loro.

Riferimento esterno: [Microsoft DOT11_SSID](https://learn.microsoft.com/en-us/windows/win32/nativewifi/dot11-ssid).
La struttura contiene una sequenza di byte con lunghezza esplicita.

### R3 - P1: raw parziale nasconde instabilita già nota

Riferimenti: `maps/quality.py:331`, `advisor/engine.py:97`.

`get_signal_ranges_by_key` restituisce subito i range raw se ne esiste almeno
uno. Non integra i range aggregati per le altre reti mancanti dal raw.

Prova: l'AP dominante ha range aggregato da -90 a -40 dBm; il raw contiene solo
un altro AP stabile. Senza raw il punto risulta `UNSTABLE_SIGNAL`; aggiungendo
quel raw parziale diventa `GOOD`. Con quattro punti di questo tipo vengono
accettate due proposte di canale.

Correzione: unire le evidenze per singola chiave di rete/radio, verificare
corrispondenza e completezza dei raw e non annullare un range aggregato valido
solo perché una rete diversa ha dati raw. Assenza di evidenza non significa
range zero.

### R4 - P1: larghezze non rappresentate correttamente possono dare rischio zero

Riferimenti: `maps/heatmap.py:572`, `wifi/scanner.py:585`.

- In 2.4 GHz il modello ignora le larghezze. Un HT40+ con primario 1 e un
  canale 6 a 20 MHz restituiscono overlap e rischio zero. Nell'esempio i blocchi
  nominali 2402-2442 e 2427-2447 MHz si sovrappongono per 15 MHz.
- `80+80` viene convertito in `160`, perdendo la natura discontinua e il secondo
  segmento. Un radio con blocchi 36-48 e 149-161 viene modellato come un
  singolo blocco contiguo: l'interferenza con il segmento superiore può sparire.

L'advisor impedisce già le proposte precise HT40 in 2.4 GHz, ma la mappa di
interferenza continua a mostrare il valore errato. La guardia non protegge
automaticamente tutti gli altri percorsi.

Correzione: rappresentare i segmenti effettivi e il secondario HT40. Dove manca
questa evidenza, mostrare un risultato incompleto/non determinabile e limitare
le prescrizioni; non trasformare un caso non supportato in overlap zero.
Verificare separatamente 320 MHz, inclusi allineamento dei blocchi e puncturing.

Riferimenti esterni: [Cisco RF Reference Guide](https://www.cisco.com/c/en/us/td/docs/wireless/controller/9800/technical-reference/wireless-rf-reference-guide.html),
[Cisco 802.11ac deployment](https://www.cisco.com/c/en/us/td/docs/wireless/controller/technotes/8-1/1850_DG/b_Cisco_Aironet_Series_1850_Access_Point_Deployment_Guide.pdf).

### R5 - P1: banda inferita o contraddittoria trattata come certa

Riferimenti: `wifi/band.py:92`, `advisor/engine.py:277`.

Il canale 5 senza banda/frequenza diventa sempre 2.4 GHz, anche se quel numero
esiste anche in 6 GHz. Una banda esplicita ha priorita senza verifica di
coerenza: `band=2.4`, `channel=5`, `frequency_mhz=5975` resta classificato 2.4.
La prova con questi dati contraddittori emette due proposte di canale.

Correzione: verificare insieme frequenza, primario, banda e larghezza. Conservare
la provenienza della classificazione; i casi ambigui devono restare incerti e
quelli contraddittori devono bloccare i calcoli che richiedono identità radio
certa. Applicare la stessa regola a mappe, qualità e report.

### R6 - P1, assunzione di modello: gruppi fisici automatici non confermati

Riferimenti: `ap/groups.py:56`, `ap/groups.py:295`, `maps/heatmap.py:375`,
`advisor/engine.py:205`.

La chiave automatica elimina il primo ottetto MAC e l'ultima cifra esadecimale.
Per esempio `02:aa:bb:cc:dd:11` e `06:aa:bb:cc:dd:12` diventano un solo gruppo
`aa:bb:cc:dd:1*`. Questo è un indizio di raggruppamento, non prova che siano
un solo dispositivo fisico.

In un dataset sintetico che rappresenta due AP indipendenti, il gruppo
automatico sopprime tutte le segnalazioni di overlap; i gruppi espliciti ne
producono due. L'app non richiede conferma del modello prima di ignorare quei
BSSID come stessa sorgente fisica.

Correzione: distinguere suggerimento automatico e gruppo confermato. Non
eliminare interferenti o prescrivere modifiche fisiche sulla sola euristica MAC;
richiedere conferma o rendere il risultato esplicitamente provvisorio.
La prova non dimostra che gruppi specifici del rilievo reale siano errati.

## Altri rilievi e limiti di precisione

| ID | Priorità/tipo | Evidenza e conseguenza | Intervento |
| --- | --- | --- | --- |
| R7 | P2, validazione | `survey/store.py:421` verifica le intestazioni ma accetta una coordinata `inf`; il riepilogo genera `OverflowError` in `:558`. Un RSSI `NaN` in un solo BSS genera `ValueError` in `wifi/scanner.py:384` e annulla il parsing della lista. | Validazione finita e coerente dei valori in tutti gli ingressi; segnalazione della riga anomala, senza perdere gli altri campioni validi. |
| R8 | P2, multi-adapter | `wifi/scanner.py:240` usa tentativi x numero di schede come denominatore, senza salvare la scheda sorgente. Due BSS visti ciascuno 5/5 dalla propria scheda risultano entrambi 5/10, confidenza 50%. | Selezione della scheda o statistiche separate per adapter; confronti fra ricevitori solo con provenienza e calibrazione esplicite. |
| R9 | P2, incertezza | `maps/heatmap.py:787` converte confidenza vuota/non numerica in 1.0; le mappe trattano dati sconosciuti come pienamente affidabili. L'advisor usa una guardia più severa, quindi i percorsi divergono. | Conservare lo stato sconosciuto e condividere la politica di qualità fra mappe, advisor e report. |
| R10 | P2, guardia sul consiglio | `advisor/engine.py:175` conta ID di punto: quattro osservazioni nelle stesse coordinate possono autorizzare una prova di riduzione potenza. Sono osservazioni temporali ripetute di un solo luogo. | Distinguere ripetizione temporale e copertura spaziale; richiedere posizioni distinte e controllare le zone dipendenti dal solo AP interessato. La prova resta un consiglio controllato, non una riduzione automatica. |
| R11 | Limite funzionale | `qt_ui/qt_point_workflow.py:70` scarta una posizione quando non ci sono reti: nessun punto o esito della misura viene conservato. Una zona realmente priva di BSS non si distingue nel dataset da una posizione mai rilevata. | Rappresentare separatamente punto, esito dello scan e osservazioni BSS. Una scansione valida con zero reti non deve diventare un RSSI inventato, e un errore scanner non deve diventare una falsa assenza. Definire il perimetro della 1.1.0. |

## Precisione delle misure e precisione dei calcoli

Il backend lswifi espone l'RSSI fornito dal driver. Questo è un dato misurato dal
ricevitore, ma l'audit non ne determina l'errore assoluto in dB rispetto a uno
strumento di riferimento. Scheda, antenna, orientamento e driver contano.

Il fallback netsh deriva i dBm dalla percentuale di qualità. La trasformazione
è limitata e non invertibile: -35 dBm -> 100% -> -50 dBm nelle funzioni attuali.
I report devono distinguere RSSI diretto e stima, includere backend/adapter e
non suggerire precisione numerica superiore a quella della sorgente.
Vedi [Microsoft WLAN_AVAILABLE_NETWORK](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/ns-wlanapi-wlan_available_network).

Le mappe interpolate e l'indice di overlap sono modelli, non nuove misure.
Le condizioni di laboratorio per RSSI assoluto, il traffico/airtime, le retry,
le interferenze non Wi-Fi e la propagazione dopo uno spostamento non sono
coperti. La validazione 6 GHz/6E/7 e 320 MHz rimane incompleta.

## Condizioni per decidere la release, stato aggiornato

1. **Completato:** correggere R1-R5 e impedire che R6 produca conclusioni certe senza conferma.
2. **Completato:** promuovere gli esempi riproducibili a regression test, compresi errori scan,
   cache/duplicati, SSID nascosti/spazi, raw parziale, larghezze e bande incoerenti.
3. **Completato:** uniformare validazione numerica, provenienza e incertezza, risolvendo R7-R9;
   rivedere la guardia spaziale R10 e dichiarare il perimetro di R11.
4. **Freschezza verificata; prove controllate ancora pendenti:** ripetere il cambio posizione, usando un AP
   controllato e confronti fra backend. Calibrare/confrontare il ricevitore se si
   vuole dichiarare una precisione assoluta dell'RSSI.
5. **Prescrizioni limitate; hardware da validare:** validare i casi 6 GHz/larghi con hardware adeguato oppure limitarne le
   prescrizioni e indicarli chiaramente come sperimentali/incompleti.
6. **Suite completa superata; pacchetto da verificare quando richiesto:** eseguire, quando si prepara intenzionalmente una build,
   lo smoke test del pacchetto Windows. Il diagnostico Qt/COM `0x8001010d` già
   osservato nei test nativi resta aperto e non deve essere soppresso o dichiarato
   risolto senza una spiegazione verificata.

L'audit non crea tag, cambia versione o valida un nuovo eseguibile. L'ambiente
Python 3.15 e la migrazione delle dipendenze restano quelli già verificati;
i blocchi sopra riguardano acquisizione, significato e uso delle evidenze RF.
