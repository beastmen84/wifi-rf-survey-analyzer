DEFAULT_LANGUAGE = "it"
SUPPORTED_LANGUAGES = ("IT", "EN")


TRANSLATIONS = {
    "it": {
        "app_title": "Wi-Fi Heatmap Survey",
        "copyright": "© Davide Marchi",
        "loading_app": "Caricamento componenti...",
        "loading_app_ready": "Pronto",
        "loading_app_error": "Errore durante il caricamento dell'app.",
        "start_subtitle": "Rilievi Wi-Fi su pianta, heatmap e controllo punti",
        "new_survey": "Nuovo rilievo",
        "open_existing_survey": "Apri rilievo esistente",
        "invalid_survey_title": "Rilievo non compatibile",
        "invalid_survey_format": "Il file selezionato non è un CSV rilievo V2 valido. Crea un nuovo rilievo o apri il CSV principale generato dal programma.",
        "raw_scan_file_selected": "Hai selezionato il file dati raw. Apri il CSV principale del rilievo, non il file _raw_data.scan.",
        "invalid_raw_scan_format": "Il file raw scan associato al rilievo non ha un formato valido. Ricrea il rilievo o rimuovi il sidecar raw non valido.",
        "exit": "Esci",
        "language": "Lingua",
        "active_survey": "Rilievo attivo: {name}",
        "survey_tab": "Rilievo",
        "live_map_tab": "Mappa live",
        "live_auto_update": "Auto aggiorna",
        "live_update_now": "Aggiorna ora",
        "live_preview_empty": "Mappa live: carica una pianta e registra almeno 3 punti.",
        "live_preview_insufficient": "Mappa live: dati insufficienti per questa vista.",
        "live_preview_rendering": "Aggiornamento mappa live...",
        "live_preview_updated": "Mappa live aggiornata.",
        "live_missing_band_points": "{missing}/{total} punti senza dati {band}",
        "live_missing_data_title": "Dati mancanti",
        "live_missing_point_tooltip": "Nessun dato {band}\nSSID: {ssid}\nx={x}, y={y}",
        "live_legend_signal": "nero = punto misurato",
        "live_legend_channel": "colore = canale",
        "live_legend_dominant": "colore = AP dominante, bordo giallo = delta <= 5 dB",
        "live_legend_interference": "verde/giallo/rosso = rischio basso/medio/alto",
        "live_zoom": "Zoom live",
        "footer_survey_info": "CSV: {csv} | Mappa: {map} | Punti: {points} | Ultimo: {last}",
        "unsaved_survey": "Rilievo non salvato",
        "no_map": "Nessuna mappa",
        "no_scan": "Nessuna scansione",
        "scan_quality_empty": "Qualità scansione: -",
        "backend_used_empty": "Backend usato: -",
        "load_plan": "Carica pianta",
        "generate_heatmap": "Genera heatmap",
        "generate": "Genera",
        "open_csv": "Apri CSV",
        "save": "Salva",
        "options": "Opzioni",
        "ap_aliases": "Alias AP",
        "calibrate_scale": "Calibra scala",
        "calibrate_scale_title": "Calibrazione scala",
        "calibrate_scale_start": "Clicca due punti sulla pianta con distanza reale nota.",
        "calibrate_scale_second_point": "Seleziona il secondo punto della distanza nota.",
        "calibrate_scale_distance_prompt": "Distanza reale tra i due punti (metri):",
        "calibrate_scale_saved": "Scala calibrata: {px_per_meter:.2f} px/m.",
        "calibrate_scale_invalid": "Distanza non valida.",
        "max_distance_m": "Distanza max (m)",
        "ap_aliases_title": "Alias AP",
        "ap_aliases_empty": "Nessun BSSID rilevato nel rilievo.",
        "ap_aliases_hint": "Doppio click nella colonna Alias per modificare. I BSSID virtuali dello stesso AP vengono raggruppati, così l'alias si assegna una sola volta e viene usato in tooltip e legende.",
        "ap_alias_group": "Gruppo AP",
        "ap_alias_bssids": "BSSID",
        "ap_alias_ssids": "SSID visti",
        "ap_alias_channels": "Canali",
        "ap_alias_value": "Alias",
        "ap_alias_search": "Cerca",
        "ap_alias_saved": "Alias AP salvati.",
        "edit_alias": "Modifica alias",
        "help": "Help",
        "fit": "Fit",
        "survey": "Rilievo",
        "map": "Mappa",
        "points": "Punti",
        "last": "Ultimo",
        "last_scan": "Ultima scansione",
        "saved_network": "Reti rilevanti",
        "saved_network_none": "Nessuna rete rilevante definita",
        "saved_network_all": "Tutte le reti",
        "relevant_networks_none": "Nessuna rete rilevante definita",
        "forget_saved_network": "Azzera rilevanti",
        "points_legend": "Legenda punti",
        "detected_points": "Punti rilevati",
        "best_dbm": "Migliore dBm",
        "quality": "Qualità",
        "quality_good": "OK",
        "quality_missing_relevant": "Manca rete",
        "quality_low_confidence": "Bassa conf.",
        "quality_unstable_signal": "Instabile",
        "quality_sparse_data": "Scarso",
        "quality_breakdown_title": "Dettaglio qualità punto",
        "rows": "Righe",
        "go_to_point": "Vai al punto",
        "delete_selected": "Elimina selezionato",
        "delete_last": "Elimina ultimo",
        "scan": "Scansione",
        "appearance": "Aspetto",
        "band": "Banda",
        "ap_filter": "AP",
        "ap_filter_all": "Tutti",
        "all_bands_option": "Tutte",
        "map_type": "Tipo mappa",
        "map_type_signal": "Copertura segnale",
        "map_type_interference": "Interferenza AP",
        "map_type_channel": "Canali AP",
        "map_type_dominant": "AP dominante",
        "channel_map_legend_title": "Canali AP",
        "channel_map_intermediate_24": "Canali intermedi",
        "channel_map_other": "Altri canali",
        "dominant_map_legend_title": "AP dominante",
        "dominant_map_roaming_overlap": "Δ <= 5 dB",
        "point_labels": "Etichette punti",
        "point_labels_auto": "Automatiche",
        "point_labels_critical": "Solo criticità",
        "point_labels_all": "Tutte",
        "point_labels_none": "Nessuna",
        "reference_table_info": "Riferimento",
        "reference_more_in_report": "+ {count} altri nel report CSV",
        "legend_other": "Altri",
        "reference_channel": "Canale",
        "reference_width": "larghezza",
        "channel_width": "Larghezza canale",
        "reference_ap": "AP",
        "reference_delta": "delta secondo AP",
        "reference_risk": "Rischio",
        "reference_serving_channel": "servente canale",
        "reference_interferer_channel": "interferente canale",
        "second_ap": "Secondo AP",
        "second_confidence": "Conf. secondo",
        "serving_ap": "AP servente",
        "interfering_ap": "AP interferente",
        "interferer_confidence": "Conf. interferente",
        "export_signal_title": "Copertura segnale Wi-Fi",
        "export_channel_title": "Canali AP Wi-Fi",
        "export_dominant_title": "AP dominante Wi-Fi",
        "export_interference_title": "Interferenza AP Wi-Fi",
        "export_signal_colorbar": "Segnale stimato dBm",
        "export_points": "punti",
        "export_measurements": "rilevamenti",
        "export_roaming_overlap": "overlap roaming",
        "interference_mode": "Analisi interferenza",
        "interference_mode_intra_ssid": "Intra-SSID",
        "interference_mode_all": "Tutti gli SSID",
        "interference_colorbar": "Rischio interferenza %",
        "interference_legend_title": "Rischio AP",
        "interference_low": "basso",
        "interference_medium": "medio",
        "interference_high": "alto",
        "interference_top_risk": "Rischio max",
        "interference_summary_title": "Riepilogo interferenze",
        "interference_summary_band": "Banda",
        "interference_summary_max_risk": "Rischio massimo",
        "interference_summary_point": "Punto",
        "interference_summary_serving_ap": "AP servente",
        "interference_summary_serving_channel": "Canale servente",
        "interference_summary_serving_width": "Larghezza servente",
        "interference_summary_interferer": "Interferente principale",
        "interference_summary_interferer_ssid": "SSID interferente",
        "interference_summary_interferer_channel": "Canale interferente",
        "interference_summary_interferer_width": "Larghezza interferente",
        "interference_summary_interferer_dbm": "Segnale interferente",
        "interference_summary_diagnosis": "Diagnosi",
        "interference_diagnosis_low": "Il rischio principale è basso: la coesistenza tra AP non sembra critica in questo punto.",
        "interference_diagnosis_same_channel_strong": "Il problema principale è un interferente forte sullo stesso canale dell'AP servente.",
        "interference_diagnosis_same_channel": "Il problema principale è la presenza di un AP sullo stesso canale dell'AP servente.",
        "interference_diagnosis_wide_channel": "Il problema principale è una sovrapposizione causata da canali larghi.",
        "interference_diagnosis_strong": "Il problema principale è un interferente forte su un canale che contribuisce al rischio.",
        "interference_diagnosis_nearby": "Il problema principale sembra un canale vicino o parzialmente sovrapposto.",
        "interference_quality_title": "Qualità dati interferenza",
        "interference_quality_width_coverage": "Larghezza canale disponibile: {available}/{total} punti ({percent}%).",
        "interference_quality_good": "La stima usa larghezza canale su una quota sufficiente di punti.",
        "interference_quality_warning": "La larghezza canale è disponibile su pochi punti: la stima usa fallback dove il dato manca.",
        "interference_quality_warning_5ghz": "La larghezza canale è disponibile su pochi punti: sul 5 GHz la stima può sottovalutare sovrapposizioni tra canali larghi.",
        "usable_only": "Solo >= -70 dBm",
        "max_distance_px": "Distanza max (px)",
        "interpolation": "Interpolazione",
        "interpolation_rbf": "RBF morbida",
        "interpolation_linear": "Lineare",
        "aggregation": "Aggregazione punto",
        "aggregation_max": "Migliore",
        "aggregation_mean": "Media",
        "aggregation_median": "Mediana",
        "color_scale": "Scala colori",
        "color_scale_fixed": "Fissa",
        "color_scale_auto": "Automatica",
        "attempts": "Tentativi: {count}",
        "theme": "Tema",
        "apply_theme": "Applica tema",
        "close": "Chiudi",
        "cancel": "Annulla",
        "select_plan_title": "Seleziona pianta",
        "pdf_or_images": "PDF o immagini",
        "images": "Immagini",
        "load_plan_first": "Carica prima una pianta.",
        "warning": "Attenzione",
        "empty_csv": "Il rilievo è vuoto.",
        "no_ssid": "Nessun SSID disponibile.",
        "select_ssid": "Seleziona un SSID.",
        "select_ssid_heatmap": "Seleziona un SSID per generare la heatmap.",
        "insufficient_data_title": "Dati insufficienti",
        "insufficient_data": "Servono almeno 3 punti per generare una heatmap nella banda {band}.",
        "interference_requires_band": "Per la mappa interferenza seleziona 2.4 GHz o 5 GHz.",
        "save_required_title": "Salvataggio richiesto",
        "save_required": "Per generare la heatmap devi prima salvare il rilievo CSV.",
        "save_failed": "Salvataggio annullato. Heatmap non generata.",
        "heatmap_generated": "Heatmap generata",
        "file_created": "File creato:\n{path}",
        "files_created": "File creati:\n{paths}",
        "csv_not_saved": "CSV non ancora salvato.",
        "unsaved_changes_title": "Rilievo non salvato",
        "unsaved_changes": "Ci sono modifiche non salvate.\n\nVuoi salvare il rilievo prima di uscire?",
        "survey_saved": "Rilievo salvato: {name}",
        "theme_applied": "Tema applicato: {theme}",
        "best": "Migliore",
        "confidence": "confidenza",
        "filter": "Filtro",
        "all_networks": "Tutte le reti",
        "networks_to_save": "Reti da salvare",
        "detected_networks_count": "Reti rilevate: {count}",
        "connected_network": "Rete connessa: {ssid}",
        "connected_ssid_option": "{ssid} (connessa)",
        "remember_choice": "Ricorda scelta",
        "relevant_networks_title": "Reti rilevanti",
        "relevant_networks_first_message": "Seleziona gli SSID rilevanti per questo rilievo. Tutte le reti verranno salvate, ma queste saranno controllate nei punti successivi.",
        "new_relevant_networks_title": "Nuove reti rilevate",
        "new_relevant_networks_message": "Sono stati rilevati nuovi SSID. Se qualcuno è rilevante per il rilievo, selezionalo.",
        "missing_relevant_networks_title": "Reti rilevanti mancanti",
        "missing_relevant_networks_message": "Queste reti rilevanti non sono state rilevate:\n{ssids}\n\nVuoi salvare comunque il punto, ritentare la scansione o annullare?",
        "remembered_network_missing_title": "Rete ricordata non disponibile",
        "remembered_network_missing": (
            "La rete salvata non è stata rilevata:\n{ssid}\n\n"
            "Premi OK per selezionare un'altra rete oppure Annulla per annullare il punto."
        ),
        "scan_quality_no_data": "Qualità scansione: nessun dato",
        "scan_quality_suspicious": "Qualità scansione: sospetta",
        "scan_quality_reduced": "Qualità scansione: ridotta",
        "scan_quality_good": "Qualità scansione: buona",
        "scan_quality_missing_relevant": "Qualità scansione: mancano {ssids}",
        "backend_used": "Backend usato: {backend}",
        "cancelled": "annullato",
        "no_networks_found": "Nessuna rete trovata. Verifica che il Wi-Fi sia attivo.",
        "error": "Errore",
        "no_matching_ssid": "Nessuna rete trovata con questo SSID.",
        "point_saved": "Punto salvato: x={x}, y={y}, reti registrate={count}",
        "scanning": "Scansione Wi-Fi in corso nel punto x={x}, y={y}...",
        "map_loaded_points": "Pianta caricata. Punti ripristinati={count}. Rilievo: {name}",
        "map_loaded": "Pianta caricata. Rilievo attivo: {name}. Clicca sulla posizione.",
        "map_not_found_title": "Mappa non trovata",
        "map_not_found": "Il CSV fa riferimento a una mappa che non esiste più:\n{path}\n\nSeleziona manualmente la pianta aggiornata.",
        "select_point": "Seleziona un punto nella tabella.",
        "no_point_to_delete": "Nessun punto da eliminare in questa sessione.",
        "last_point_deleted": "Ultimo punto eliminato: x={x}, y={y}, righe rimosse={rows}",
        "point_deleted": "Punto eliminato: x={x}, y={y}, righe rimosse={rows}",
        "zoom": "Zoom: {zoom:.0%}",
        "all_bands_label": "tutte le bande",
        "start_step_plan": "1. Carica una pianta PDF o immagine",
        "start_step_points": "2. Crea punti con tasto destro",
        "start_step_heatmap": "3. Genera heatmap per SSID e banda",
        "start_shortcuts": "Tasto sinistro premuto: trascina mappa | Ctrl + rotella: zoom",
        "mouse_right_action": "Crea punto",
        "mouse_left_action": "Trascina mappa",
        "mouse_marker_action": "Seleziona punto",
        "mouse_wheel_action": "Scorrimento verticale",
        "mouse_shift_scroll_action": "Scorrimento orizzontale",
        "mouse_ctrl_scroll_action": "Zoom",
        "help_title": "Guida rapida",
        "help_commands": "Comandi",
        "help_workflow": "Flusso",
        "help_workflow_title": "Come usare il programma",
        "help_workflow_steps": (
            "1-a. Crea un nuovo rilievo e carica la pianta dell'ambiente.\n"
            "1-b. Oppure apri un rilievo già salvato: la pianta verrà caricata automaticamente.\n"
            "2. Spostati fisicamente nell'area e usa il tasto destro sulla mappa per registrare i punti di misura.\n"
            "3. Salva il rilievo dopo aver raccolto abbastanza punti.\n"
            "4. Genera la mappa e scegli SSID, banda Wi-Fi e tipo analisi.\n"
            "5. Usa Copertura segnale per valutare il livello dBm, Interferenza AP per trovare sovrapposizioni, Canali AP per controllare i canali e AP dominante per analizzare il roaming."
        ),
        "help_live": "Mappa live",
        "help_live_title": "Come usare la mappa live",
        "help_live_steps": (
            "La Mappa live mostra una preview del rilievo senza generare file PNG.\n"
            "Scegli SSID, banda e tipo mappa direttamente nel tab Mappa live.\n"
            "Copertura segnale e Interferenza AP vengono calcolate in background, quindi la GUI resta utilizzabile durante l'aggiornamento.\n"
            "Canali AP e AP dominante mostrano i punti reali con legenda inferiore.\n"
            "Se sei nel tab Rilievo, la live view viene aggiornata quando entri nel tab Mappa live o premi Aggiorna ora.\n"
            "Lo zoom della live view non rigenera la mappa: ridimensiona la preview e rifinisce la qualità dopo una breve pausa."
        ),
        "help_heatmap": "Heatmap",
        "help_heatmap_title": "Come leggere e generare la heatmap",
        "help_heatmap_steps": (
            "Copertura segnale genera una heatmap continua del livello dBm per SSID e banda.\n"
            "RBF morbida crea una visualizzazione più continua; Lineare è più conservativa.\n"
            "Distanza max limita la heatmap alle aree vicine ai punti reali e riduce forme inventate.\n"
            "Solo >= -70 dBm evidenzia le zone normalmente utilizzabili.\n"
            "Interferenza AP calcola il rischio in percentuale, salva anche un report CSV e mostra un riepilogo con AP servente, interferente principale e qualità dati.\n"
            "Canali AP non interpola: mostra i punti reali colorati per canale, con etichette tipo CH 36 / 80 quando la larghezza canale è disponibile.\n"
            "AP dominante mostra quale BSSID è più forte in ogni punto e marca in giallo le zone dove il secondo AP è entro 5 dB."
        ),
        "help_scan": "Scansione",
        "help_scan_title": "Come gestire la scansione Wi-Fi",
        "help_scan_steps": (
            "Backend Auto prova lswifi e usa netsh come fallback.\n"
            "lswifi è preferibile quando disponibile perché di solito rileva più BSSID.\n"
            "Con lswifi, quando disponibile, viene salvata anche la larghezza canale in channel_width_mhz.\n"
            "netsh resta utile come alternativa integrata in Windows.\n"
            "Se una scansione trova molte meno reti della precedente, viene segnalata come sospetta.\n"
            "Quando una scansione è sospetta, conviene riprovare prima di salvare il punto.\n"
            "Se usi Ricorda scelta, il programma salva automaticamente lo stesso SSID finché viene rilevato."
        ),
        "help_commands_text": (
            "Tasto destro sulla mappa: crea un punto di rilievo.\n"
            "Tasto sinistro premuto: trascina la mappa.\n"
            "Click sinistro su un marker: seleziona il punto.\n"
            "Rotella: scorrimento verticale.\n"
            "Shift + rotella: scorrimento orizzontale.\n"
            "Ctrl + rotella: zoom."
        ),
        "help_workflow_text": (
            "1. Crea un nuovo rilievo o apri un CSV esistente.\n"
            "2. Carica la pianta dell'ambiente.\n"
            "3. Crea i punti reali camminando lungo il percorso.\n"
            "4. Salva il rilievo.\n"
            "5. Scegli SSID, banda e tipo mappa.\n"
            "6. Genera Copertura segnale, Interferenza AP, Canali AP o AP dominante."
        ),
        "help_live_text": (
            "La Mappa live mostra una preview del rilievo senza generare file PNG.\n"
            "Copertura segnale e Interferenza AP vengono calcolate in background.\n"
            "Canali AP e AP dominante usano i marker reali e la legenda inferiore.\n"
            "Aggiorna ora forza un ricalcolo con le opzioni correnti."
        ),
        "help_heatmap_text": (
            "RBF morbida produce mappe più continue; lineare è più conservativa.\n"
            "Aggregazione migliore mostra il segnale migliore del punto; media e mediana sono più stabili.\n"
            "Scala fissa permette confronti tra mappe; automatica rende più leggibile una singola mappa.\n"
            "Distanza max limita le aree generate lontano dai punti reali.\n"
            "Solo >= -70 dBm evidenzia le zone normalmente utilizzabili.\n"
            "Interferenza AP genera PNG e report CSV con diagnosi del punto peggiore.\n"
            "Canali AP mostra solo i punti reali, colorati per canale.\n"
            "AP dominante genera PNG e report CSV con AP migliore, secondo AP e differenza dB."
        ),
        "help_scan_text": (
            "Auto prova lswifi e usa netsh come fallback.\n"
            "lswifi di solito vede più BSSID ed è preferibile quando disponibile.\n"
            "lswifi può fornire channel_width_mhz, utile per stimare meglio le interferenze 5 GHz.\n"
            "Se una scansione trova molte meno reti della precedente, il programma la segnala come sospetta.\n"
            "In quel caso conviene riprovare prima di salvare il punto."
        ),
        "suspicious_scan_title": "Scansione Wi-Fi sospetta",
        "suspicious_scan_message": (
            "La scansione ha trovato molte meno reti della precedente.\n\n"
            "Ora: {current} rilevamenti\n"
            "Ultima scansione buona: {previous} rilevamenti\n\n"
            "Scegli se mantenere questa scansione, riprovare o annullare il punto."
        ),
        "keep_scan": "Mantieni scansione",
        "retry_scan": "Riprova",
        "cancel_point": "Annulla punto",
        "retrying_scan": "Riprovo scansione Wi-Fi nel punto x={x}, y={y}...",
        "use_suspicious_scan_title": "Usare scansione sospetta?",
        "use_suspicious_scan_message": (
            "Vuoi usare comunque questa scansione incompleta?\n\n"
            "Sì: salva i dati trovati.\n"
            "No: annulla il punto."
        ),
    },
    "en": {
        "app_title": "Wi-Fi Heatmap Survey",
        "copyright": "© Davide Marchi",
        "loading_app": "Loading components...",
        "loading_app_ready": "Ready",
        "loading_app_error": "Error while loading the app.",
        "start_subtitle": "Wi-Fi surveys on floor plans, heatmaps, and point checks",
        "new_survey": "New survey",
        "open_existing_survey": "Open existing survey",
        "invalid_survey_title": "Incompatible survey",
        "invalid_survey_format": "The selected file is not a valid V2 survey CSV. Create a new survey or open the main CSV generated by the program.",
        "raw_scan_file_selected": "You selected the raw data file. Open the main survey CSV, not the _raw_data.scan file.",
        "invalid_raw_scan_format": "The raw scan file associated with this survey is not valid. Recreate the survey or remove the invalid raw sidecar.",
        "exit": "Exit",
        "language": "Language",
        "active_survey": "Active survey: {name}",
        "survey_tab": "Survey",
        "live_map_tab": "Live map",
        "live_auto_update": "Auto update",
        "live_update_now": "Update now",
        "live_preview_empty": "Live map: load a floor plan and record at least 3 points.",
        "live_preview_insufficient": "Live map: insufficient data for this view.",
        "live_preview_rendering": "Updating live map...",
        "live_preview_updated": "Live map updated.",
        "live_missing_band_points": "{missing}/{total} points without {band} data",
        "live_missing_data_title": "Missing data",
        "live_missing_point_tooltip": "No {band} data\nSSID: {ssid}\nx={x}, y={y}",
        "live_legend_signal": "black = measured point",
        "live_legend_channel": "color = channel",
        "live_legend_dominant": "color = dominant AP, yellow outline = delta <= 5 dB",
        "live_legend_interference": "green/yellow/red = low/medium/high risk",
        "live_zoom": "Live zoom",
        "footer_survey_info": "CSV: {csv} | Map: {map} | Points: {points} | Last: {last}",
        "unsaved_survey": "Unsaved survey",
        "no_map": "No map",
        "no_scan": "No scan",
        "scan_quality_empty": "Scan quality: -",
        "backend_used_empty": "Backend used: -",
        "load_plan": "Load plan",
        "generate_heatmap": "Generate heatmap",
        "generate": "Generate",
        "open_csv": "Open CSV",
        "save": "Save",
        "options": "Options",
        "ap_aliases": "AP aliases",
        "calibrate_scale": "Calibrate scale",
        "calibrate_scale_title": "Scale calibration",
        "calibrate_scale_start": "Click two points on the floor plan with known real distance.",
        "calibrate_scale_second_point": "Select the second point of the known distance.",
        "calibrate_scale_distance_prompt": "Real distance between the two points (meters):",
        "calibrate_scale_saved": "Scale calibrated: {px_per_meter:.2f} px/m.",
        "calibrate_scale_invalid": "Invalid distance.",
        "max_distance_m": "Max distance (m)",
        "ap_aliases_title": "AP aliases",
        "ap_aliases_empty": "No BSSID detected in the survey.",
        "ap_aliases_hint": "Double click the Alias column to edit. Virtual BSSIDs from the same AP are grouped, so one alias is used in tooltips and legends.",
        "ap_alias_group": "AP group",
        "ap_alias_bssids": "BSSID",
        "ap_alias_ssids": "Seen SSIDs",
        "ap_alias_channels": "Channels",
        "ap_alias_value": "Alias",
        "ap_alias_search": "Search",
        "ap_alias_saved": "AP aliases saved.",
        "edit_alias": "Edit alias",
        "help": "Help",
        "fit": "Fit",
        "survey": "Survey",
        "map": "Map",
        "points": "Points",
        "last": "Last",
        "last_scan": "Last scan",
        "saved_network": "Relevant networks",
        "saved_network_none": "No relevant network defined",
        "saved_network_all": "All networks",
        "relevant_networks_none": "No relevant network defined",
        "forget_saved_network": "Clear relevant",
        "points_legend": "Point legend",
        "detected_points": "Detected points",
        "best_dbm": "Best dBm",
        "quality": "Quality",
        "quality_good": "OK",
        "quality_missing_relevant": "Missing net",
        "quality_low_confidence": "Low conf.",
        "quality_unstable_signal": "Unstable",
        "quality_sparse_data": "Sparse",
        "quality_breakdown_title": "Point quality details",
        "rows": "Rows",
        "go_to_point": "Go to point",
        "delete_selected": "Delete selected",
        "delete_last": "Delete last",
        "scan": "Scan",
        "appearance": "Appearance",
        "band": "Band",
        "ap_filter": "AP",
        "ap_filter_all": "All",
        "all_bands_option": "All",
        "map_type": "Map type",
        "map_type_signal": "Signal coverage",
        "map_type_interference": "AP interference",
        "map_type_channel": "AP channels",
        "map_type_dominant": "Dominant AP",
        "channel_map_legend_title": "AP channels",
        "channel_map_intermediate_24": "Intermediate channels",
        "channel_map_other": "Other channels",
        "dominant_map_legend_title": "Dominant AP",
        "dominant_map_roaming_overlap": "Δ <= 5 dB",
        "point_labels": "Point labels",
        "point_labels_auto": "Automatic",
        "point_labels_critical": "Critical only",
        "point_labels_all": "All",
        "point_labels_none": "None",
        "reference_table_info": "Reference",
        "reference_more_in_report": "+ {count} more in CSV report",
        "legend_other": "Other",
        "reference_channel": "Channel",
        "reference_width": "width",
        "channel_width": "Channel width",
        "reference_ap": "AP",
        "reference_delta": "second AP delta",
        "reference_risk": "Risk",
        "reference_serving_channel": "serving channel",
        "reference_interferer_channel": "interferer channel",
        "second_ap": "Second AP",
        "second_confidence": "Second confidence",
        "serving_ap": "Serving AP",
        "interfering_ap": "Interfering AP",
        "interferer_confidence": "Interferer confidence",
        "export_signal_title": "Wi-Fi signal coverage",
        "export_channel_title": "Wi-Fi AP channels",
        "export_dominant_title": "Wi-Fi dominant AP",
        "export_interference_title": "Wi-Fi AP interference",
        "export_signal_colorbar": "Estimated signal dBm",
        "export_points": "points",
        "export_measurements": "measurements",
        "export_roaming_overlap": "roaming overlap",
        "interference_mode": "Interference analysis",
        "interference_mode_intra_ssid": "Intra-SSID",
        "interference_mode_all": "All SSIDs",
        "interference_colorbar": "Interference risk %",
        "interference_legend_title": "AP risk",
        "interference_low": "low",
        "interference_medium": "medium",
        "interference_high": "high",
        "interference_top_risk": "Top risk",
        "interference_summary_title": "Interference summary",
        "interference_summary_band": "Band",
        "interference_summary_max_risk": "Maximum risk",
        "interference_summary_point": "Point",
        "interference_summary_serving_ap": "Serving AP",
        "interference_summary_serving_channel": "Serving channel",
        "interference_summary_serving_width": "Serving width",
        "interference_summary_interferer": "Main interferer",
        "interference_summary_interferer_ssid": "Interfering SSID",
        "interference_summary_interferer_channel": "Interfering channel",
        "interference_summary_interferer_width": "Interfering width",
        "interference_summary_interferer_dbm": "Interfering signal",
        "interference_summary_diagnosis": "Diagnosis",
        "interference_diagnosis_low": "The main risk is low: AP coexistence does not look critical at this point.",
        "interference_diagnosis_same_channel_strong": "The main issue is a strong interferer on the same channel as the serving AP.",
        "interference_diagnosis_same_channel": "The main issue is an AP on the same channel as the serving AP.",
        "interference_diagnosis_wide_channel": "The main issue is overlap caused by wide channels.",
        "interference_diagnosis_strong": "The main issue is a strong interferer on a channel that contributes to the risk.",
        "interference_diagnosis_nearby": "The main issue appears to be a nearby or partially overlapping channel.",
        "interference_quality_title": "Interference data quality",
        "interference_quality_width_coverage": "Channel width available: {available}/{total} points ({percent}%).",
        "interference_quality_good": "The estimate uses channel width on a sufficient share of points.",
        "interference_quality_warning": "Channel width is available on few points: the estimate uses fallback where data is missing.",
        "interference_quality_warning_5ghz": "Channel width is available on few points: on 5 GHz the estimate may underestimate overlap between wide channels.",
        "usable_only": "Only >= -70 dBm",
        "max_distance_px": "Max distance px",
        "interpolation": "Interpolation",
        "interpolation_rbf": "Smooth RBF",
        "interpolation_linear": "Linear",
        "aggregation": "Point aggregation",
        "aggregation_max": "Best",
        "aggregation_mean": "Mean",
        "aggregation_median": "Median",
        "color_scale": "Color scale",
        "color_scale_fixed": "Fixed",
        "color_scale_auto": "Automatic",
        "attempts": "Attempts: {count}",
        "theme": "Theme",
        "apply_theme": "Apply theme",
        "close": "Close",
        "cancel": "Cancel",
        "select_plan_title": "Select floor plan",
        "pdf_or_images": "PDF or images",
        "images": "Images",
        "load_plan_first": "Load a floor plan first.",
        "warning": "Warning",
        "empty_csv": "The survey is empty.",
        "no_ssid": "No SSID available.",
        "select_ssid": "Select an SSID in the Heatmap panel.",
        "select_ssid_heatmap": "Select an SSID to generate the heatmap.",
        "insufficient_data_title": "Insufficient data",
        "insufficient_data": "At least 3 points are required to generate a heatmap on {band}.",
        "interference_requires_band": "Select 2.4 GHz or 5 GHz for the interference map.",
        "save_required_title": "Save required",
        "save_required": "You must save the survey CSV before generating the heatmap.",
        "save_failed": "Save cancelled. Heatmap not generated.",
        "heatmap_generated": "Heatmap generated",
        "file_created": "File created:\n{path}",
        "files_created": "Files created:\n{paths}",
        "csv_not_saved": "CSV not saved yet.",
        "unsaved_changes_title": "Unsaved survey",
        "unsaved_changes": "There are unsaved changes.\n\nDo you want to save the survey before exiting?",
        "survey_saved": "Survey saved: {name}",
        "theme_applied": "Theme applied: {theme}",
        "best": "Best",
        "confidence": "confidence",
        "filter": "Filter",
        "all_networks": "All networks",
        "networks_to_save": "Networks to save",
        "detected_networks_count": "Networks detected: {count}",
        "connected_network": "Connected network: {ssid}",
        "connected_ssid_option": "{ssid} (connected)",
        "remember_choice": "Remember choice",
        "relevant_networks_title": "Relevant networks",
        "relevant_networks_first_message": "Select the SSIDs that are relevant for this survey. All networks will be saved, but these will be checked at the next points.",
        "new_relevant_networks_title": "New networks detected",
        "new_relevant_networks_message": "New SSIDs were detected. Select any that are relevant for this survey.",
        "missing_relevant_networks_title": "Relevant networks missing",
        "missing_relevant_networks_message": "These relevant networks were not detected:\n{ssids}\n\nDo you want to save the point anyway, retry the scan, or cancel?",
        "remembered_network_missing_title": "Remembered network unavailable",
        "remembered_network_missing": (
            "The saved network was not detected:\n{ssid}\n\n"
            "Press OK to select another network or Cancel to cancel the point."
        ),
        "scan_quality_no_data": "Scan quality: no data",
        "scan_quality_suspicious": "Scan quality: suspicious",
        "scan_quality_reduced": "Scan quality: reduced",
        "scan_quality_good": "Scan quality: good",
        "scan_quality_missing_relevant": "Scan quality: missing {ssids}",
        "backend_used": "Backend used: {backend}",
        "cancelled": "cancelled",
        "no_networks_found": "No networks found. Check that Wi-Fi is enabled.",
        "error": "Error",
        "no_matching_ssid": "No network found with this SSID.",
        "point_saved": "Point saved: x={x}, y={y}, networks saved={count}",
        "scanning": "Wi-Fi scan in progress at x={x}, y={y}...",
        "map_loaded_points": "Plan loaded. Restored points={count}. Survey: {name}",
        "map_loaded": "Plan loaded. Active survey: {name}. Click your position.",
        "map_not_found_title": "Map not found",
        "map_not_found": "The CSV references a map that no longer exists:\n{path}\n\nSelect the updated floor plan manually.",
        "select_point": "Select a point in the table.",
        "no_point_to_delete": "No point to delete in this session.",
        "last_point_deleted": "Last point deleted: x={x}, y={y}, removed rows={rows}",
        "point_deleted": "Point deleted: x={x}, y={y}, removed rows={rows}",
        "zoom": "Zoom: {zoom:.0%}",
        "all_bands_label": "all bands",
        "start_step_plan": "1. Load a PDF or image floor plan",
        "start_step_points": "2. Create points with right click",
        "start_step_heatmap": "3. Generate heatmaps by SSID and band",
        "start_shortcuts": "Hold left button: pan map | Ctrl + wheel: zoom",
        "mouse_right_action": "Create point",
        "mouse_left_action": "Pan map",
        "mouse_marker_action": "Select point",
        "mouse_wheel_action": "Vertical scroll",
        "mouse_shift_scroll_action": "Horizontal scroll",
        "mouse_ctrl_scroll_action": "Zoom",
        "help_title": "Quick help",
        "help_commands": "Commands",
        "help_workflow": "Workflow",
        "help_workflow_title": "How to use the program",
        "help_workflow_steps": (
            "1-a. Create a new survey and load the floor plan.\n"
            "1-b. Or open a saved survey: the floor plan will be loaded automatically.\n"
            "2. Physically move through the area and use right click on the map to record measurement points.\n"
            "3. Save the survey after collecting enough points.\n"
            "4. Generate the map and choose SSID, Wi-Fi band, and analysis type.\n"
            "5. Use Signal coverage to evaluate dBm level, AP interference to find overlaps, AP channels to inspect channels, and Dominant AP to analyze roaming."
        ),
        "help_live": "Live map",
        "help_live_title": "How to use the live map",
        "help_live_steps": (
            "The Live map shows a survey preview without generating PNG files.\n"
            "Choose SSID, band, and map type directly in the Live map tab.\n"
            "Signal coverage and AP interference are calculated in the background, so the GUI stays usable while updating.\n"
            "AP channels and Dominant AP show real points with the bottom legend.\n"
            "If you are in the Survey tab, the live view updates when you enter the Live map tab or press Update now.\n"
            "Live zoom does not regenerate the map: it resizes the preview and refines quality after a short pause."
        ),
        "help_heatmap": "Heatmap",
        "help_heatmap_title": "How to read and generate the heatmap",
        "help_heatmap_steps": (
            "Signal coverage generates a continuous dBm heatmap by SSID and band.\n"
            "Smooth RBF creates a more continuous visualization; Linear is more conservative.\n"
            "Max distance limits the heatmap to areas near real points and reduces invented shapes.\n"
            "Only >= -70 dBm highlights normally usable areas.\n"
            "AP interference calculates percentage risk, also saves a CSV report, and shows a summary with serving AP, main interferer, and data quality.\n"
            "AP channels does not interpolate: it shows real points colored by channel, with labels like CH 36 / 80 when channel width is available.\n"
            "Dominant AP shows which BSSID is strongest at each point and marks in yellow where the second AP is within 5 dB."
        ),
        "help_scan": "Scan",
        "help_scan_title": "How to handle Wi-Fi scans",
        "help_scan_steps": (
            "Auto backend tries lswifi and falls back to netsh.\n"
            "lswifi is preferred when available because it usually detects more BSSIDs.\n"
            "With lswifi, channel width is also saved in channel_width_mhz when available.\n"
            "netsh remains useful as the built-in Windows alternative.\n"
            "If a scan finds far fewer networks than the previous one, it is marked suspicious.\n"
            "When a scan is suspicious, retry before saving the point.\n"
            "If you use Remember choice, the program automatically saves the same SSID while it is detected."
        ),
        "help_commands_text": (
            "Right click on the map: create a survey point.\n"
            "Hold left button: pan the map.\n"
            "Left click on a marker: select the point.\n"
            "Mouse wheel: vertical scroll.\n"
            "Shift + wheel: horizontal scroll.\n"
            "Ctrl + wheel: zoom."
        ),
        "help_workflow_text": (
            "1. Create a new survey or open an existing CSV.\n"
            "2. Load the floor plan.\n"
            "3. Create real points while walking the route.\n"
            "4. Save the survey.\n"
            "5. Choose SSID, band, and map type.\n"
            "6. Generate Signal coverage, AP interference, AP channels, or Dominant AP."
        ),
        "help_live_text": (
            "The Live map shows a survey preview without generating PNG files.\n"
            "Signal coverage and AP interference are calculated in the background.\n"
            "AP channels and Dominant AP use real markers and the bottom legend.\n"
            "Update now forces a recalculation with the current options."
        ),
        "help_heatmap_text": (
            "Smooth RBF produces more continuous maps; linear is more conservative.\n"
            "Best aggregation shows the strongest signal at the point; mean and median are more stable.\n"
            "Fixed scale helps compare maps; automatic scale improves readability for one map.\n"
            "Max distance limits areas generated far from real points.\n"
            "Only >= -70 dBm highlights normally usable areas.\n"
            "AP interference generates a PNG and CSV report with diagnosis of the worst point.\n"
            "AP channels shows only real points, colored by channel.\n"
            "Dominant AP generates a PNG and CSV report with best AP, second AP, and dB delta."
        ),
        "help_scan_text": (
            "Auto tries lswifi and falls back to netsh.\n"
            "lswifi usually sees more BSSIDs and is preferred when available.\n"
            "lswifi can provide channel_width_mhz, useful for better 5 GHz interference estimates.\n"
            "If a scan finds far fewer networks than the previous good scan, it is marked suspicious.\n"
            "In that case, retry before saving the point."
        ),
        "suspicious_scan_title": "Suspicious Wi-Fi scan",
        "suspicious_scan_message": (
            "This scan found far fewer networks than the previous one.\n\n"
            "Now: {current} detections\n"
            "Last good scan: {previous} detections\n\n"
            "Choose whether to keep this scan, retry, or cancel the point."
        ),
        "keep_scan": "Keep scan",
        "retry_scan": "Retry",
        "cancel_point": "Cancel point",
        "retrying_scan": "Retrying Wi-Fi scan at x={x}, y={y}...",
        "use_suspicious_scan_title": "Use suspicious scan?",
        "use_suspicious_scan_message": (
            "Do you want to use this incomplete scan anyway?\n\n"
            "Yes: save the found data.\n"
            "No: cancel the point."
        ),
    },
}


def normalize_language(language):
    language = str(language or DEFAULT_LANGUAGE).lower()
    return language if language in TRANSLATIONS else DEFAULT_LANGUAGE


def translate(language, key, **kwargs):
    language = normalize_language(language)
    text = TRANSLATIONS[language].get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))
    return text.format(**kwargs) if kwargs else text
