"""Italian translations."""

LANGUAGE_LABEL = "Italiano"

TRANSLATIONS = {
    "app_title": "Wi-Fi RF Survey Analyzer",
    "copyright": "© Davide Marchi",
    "loading_app": "Caricamento componenti...",
    "loading_app_ready": "Pronto",
    "loading_app_error": "Errore durante il caricamento dell'app.",
    "start_subtitle": "Rilievi Reali, Mappe Live e Diagnostica RF",
    "start_workflow_title": "Flusso Operativo",
    "start_workflow_1": "1. Crea o apri un rilievo e carica la pianta dell'ambiente.",
    "start_workflow_2": "2. Registra i punti con scansioni multi-campione e reti rilevanti.",
    "start_workflow_3": "3. Analizza copertura, interferenze, roaming, AP group e qualità.",
    "start_loading_title": "Avvio Applicazione",
    "start_actions_title": "Rilievo",
    "start_actions_hint": "I comandi si attivano quando i componenti di analisi sono pronti.",
    "start_ready_hint": "La schermata principale si aprirà direttamente sul rilievo scelto.",
    "qt_start_hint_title": "Interfaccia Corrente",
    "qt_start_hint": "Questa release usa la base Qt con rilievo, mappa live, gruppi AP, qualità, generazione mappe e calibrazione scala.",
    "toolbar_project": "Progetto",
    "toolbar_view": "Vista",
    "toolbar_analysis": "Analisi",
    "toolbar_settings": "Impostazioni",
    "qt_survey_file_filter": "CSV rilievo Wi-Fi (*.csv);;Tutti i file (*.*)",
    "qt_plan_file_filter": "PDF e immagini (*.pdf *.png *.jpg *.jpeg *.bmp);;Tutti i file (*.*)",
    "qt_csv": "CSV",
    "qt_points": "Punti",
    "qt_raw_rows": "Scansioni Raw",
    "qt_table_networks": "Reti",
    "qt_table_best_dbm": "Migliore dBm",
    "qt_table_timestamp": "Timestamp",
    "summary_ap_groups": "Gruppi AP",
    "points_panel_show": "▲ Punti Rilevati",
    "points_panel_hide": "▼ Punti Rilevati",
    "points_panel_resize": "Trascina verso l'alto o il basso per ridimensionare il pannello punti.",
    "new_survey": "Nuovo Rilievo",
    "open_existing_survey": "Apri Rilievo",
    "invalid_survey_title": "Rilievo Non Compatibile",
    "invalid_survey_format": "Il file selezionato non è un CSV rilievo V2 valido. Crea un nuovo rilievo o apri il CSV principale generato dal programma.",
    "raw_scan_file_selected": "Hai selezionato il file dati raw. Apri il CSV principale del rilievo, non il file _raw_data.scan.",
    "invalid_raw_scan_format": "Il file raw scan associato al rilievo non ha un formato valido. Ricrea il rilievo o rimuovi il sidecar raw non valido.",
    "exit": "Esci",
    "language": "Lingua",
    "ui_scale": "Scala UI",
    "ui_scale_auto": "Auto ({percent}%)",
    "measurement_system": "Sistema Di Misura",
    "measurement_system_metric": "Metrico (m)",
    "measurement_system_imperial": "Imperiale (ft)",
    "measurement_unit_metric": "metri",
    "measurement_unit_imperial": "piedi",
    "measurement_system_scale_reset_title": "La Calibrazione Scala Verrà Resettata",
    "measurement_system_scale_reset_message": "Questo rilievo ha già una scala calibrata. Cambiare sistema di misura cancellerà la calibrazione scala attuale.\n\nEsegui di nuovo Calibra Scala prima di interpretare le distanze. Continuare?",
    "measurement_system_scale_reset_button": "Cambia Ed Elimina Scala",
    "measurement_system_scale_reset_done": "Sistema di misura cambiato. Scala eliminata; esegui di nuovo Calibra Scala.",
    "ui_scale_restart_title": "Riavvio Richiesto",
    "ui_scale_restart_message": "Per applicare la scala UI {scale} serve riavviare l'app.\n\nVuoi salvare la scelta e riavviare ora?",
    "save_and_restart": "Salva e Riavvia",
    "settings_save_failed": "Impossibile salvare le impostazioni.",
    "ap_memory_settings_title": "Memoria AP",
    "open_memory_folder": "Apri Cartella Memoria",
    "open_memory_folder_failed": "Impossibile aprire la cartella della memoria AP.",
    "clear_ap_memory": "Svuota Memoria AP...",
    "clear_ap_memory_title": "Svuota Memoria AP",
    "clear_ap_memory_confirm": "Questa azione elimina alias, ruoli, metadati e posizioni mappa AP ricordati per i rilievi futuri.\n\nIl rilievo aperto non verrà modificato. Vuoi continuare?",
    "clear_ap_memory_confirm_button": "Svuota Memoria AP",
    "clear_ap_memory_failed": "Impossibile svuotare la memoria AP.",
    "restart_failed": "Impossibile riavviare l'applicazione.",
    "restart_blocked_busy": "Attendi il termine della scansione o dell'aggiornamento mappa prima di cambiare scala UI.",
    "active_survey": "Rilievo attivo: {name}",
    "survey_tab": "Rilievo",
    "live_map_tab": "Mappa Live",
    "live_auto_update": "Aggiornamento Auto",
    "live_update_now": "Aggiorna Ora",
    "live_export_pdf": "Esporta PDF",
    "live_pdf_exported": "PDF esportato",
    "save_live_pdf_title": "Salva PDF Mappa Live",
    "live_pdf_file_filter": "PDF (*.pdf);;Tutti i file (*.*)",
    "live_pdf_problem_report_title": "Report Problemi",
    "live_pdf_issue": "Problema",
    "live_pdf_no_interference_issues": "Nessun problema di interferenza rilevante rilevato.",
    "live_pdf_no_dominant_issues": "Nessun problema di AP dominante rilevante rilevato.",
    "live_options_show": "Opzioni",
    "live_options_hide": "Opzioni",
    "live_preview_empty": "Mappa live: carica una pianta e registra almeno 3 punti.",
    "live_preview_insufficient": "Mappa live: dati insufficienti per questa vista.",
    "live_preview_rendering": "Aggiornamento mappa live...",
    "live_preview_updated": "Mappa live aggiornata.",
    "ap_group_filter": "Gruppo AP",
    "all_ap_groups_option": "Tutti i Gruppi AP",
    "footer_survey_info": "CSV: {csv} | Mappa: {map} | Punti: {points} | Ultimo: {last}",
    "ap_memory_status_missing": "Memoria AP: Non Creata",
    "ap_memory_status_empty": "Memoria AP: Vuota",
    "ap_memory_status_saved": "Memoria AP: Salvata ({count} AP)",
    "ap_memory_status_applied": "Memoria AP: {applied} Da Confermare / {total} Salvati",
    "unsaved_survey": "Rilievo Non Salvato",
    "no_map": "Nessuna Mappa",
    "load_plan": "Carica Pianta",
    "generate_heatmap": "Genera Heatmap",
    "generate": "Genera",
    "save": "Salva",
    "save_clean_tooltip": "Rilievo salvato",
    "save_dirty_tooltip": "Ci sono modifiche non salvate",
    "ap_aliases": "Gruppi AP",
    "quality_dashboard_title": "Qualità Rilievo",
    "quality_dashboard_hint": "Controlla qualità scansione, configurazione AP e diagnostica mappe prima di affidarti alle mappe generate.",
    "quality_dashboard_status_ok_title": "Rilievo Coerente",
    "quality_dashboard_status_ok_message": "Nessun punto richiede una nuova scansione. I controlli qualità non hanno rilevato problemi sui {total} punti.",
    "quality_dashboard_status_early_title": "Dati Iniziali",
    "quality_dashboard_status_early_message": "Nessun problema di scansione rilevato sui {total} punti, ma il quadro sarà più utile dopo altri punti di misura.",
    "quality_dashboard_status_review_title": "Controlli Consigliati",
    "quality_dashboard_status_review_message": "{count} punti su {total} meritano verifica o nuova scansione prima di usare le mappe come riferimento.",
    "quality_dashboard_status_setup_title": "Configurazione AP da Completare",
    "quality_dashboard_status_setup_message": "I punti non richiedono nuova scansione, ma posizioni AP, metadati o diagnostica cambi canale richiedono verifica.",
    "quality_dashboard_metric_points": "Punti Totali",
    "quality_dashboard_metric_ok": "Punti OK",
    "quality_dashboard_metric_review": "Punti da Controllare",
    "quality_dashboard_metric_group_survey": "Punti Rilievo",
    "quality_dashboard_metric_group_scan": "Qualità Scansione",
    "quality_dashboard_metric_group_ap": "Modello AP",
    "quality_dashboard_metric_scan_ok": "Scansione OK",
    "quality_dashboard_metric_rescan": "Punti Da Verificare",
    "quality_dashboard_metric_missing": "Reti Rilevanti Mancanti",
    "quality_dashboard_metric_sparse": "Dati Scarsi",
    "quality_dashboard_metric_scanner_details": "Dettagli Scanner Mancanti",
    "quality_dashboard_metric_low_confidence": "Bassa Confidenza Scansione",
    "quality_dashboard_metric_unstable": "Segnale Instabile",
    "quality_dashboard_metric_ap_diagnostic_points": "Anomalie Dominant AP",
    "quality_dashboard_metric_ap_memory_applied": "Dati Da Memoria",
    "quality_dashboard_metric_ap_position_warnings": "Warning Posizione AP",
    "quality_dashboard_metric_ap_missing_positions": "AP Senza Posizione",
    "quality_dashboard_metric_ap_metadata_warnings": "Warning Configurazione AP",
    "quality_dashboard_metric_channel_changes": "Cambi Canale",
    "quality_dashboard_fix_next_title": "Cosa Sistemare Ora",
    "quality_dashboard_fix_missing_title": "Ripeti Reti Mancanti",
    "quality_dashboard_fix_missing_detail": "{count} punti non vedono gli SSID rilevanti selezionati. Ripeti la scansione o controlla la lista reti rilevanti.",
    "quality_dashboard_fix_sparse_title": "Ripeti Scansioni Scarse",
    "quality_dashboard_fix_sparse_detail": "{count} punti hanno troppo pochi campioni utilizzabili. Ripeti quelle scansioni prima di fidarti dell'interpolazione.",
    "quality_dashboard_fix_scanner_details_title": "Ripeti Punti Con Dettagli Scanner Limitati",
    "quality_dashboard_fix_scanner_details_detail": "{count} punti non hanno tutti i dettagli scanner usati dalle analisi sensibili al canale. Ripetili prima di fidarti di Interferenza, overlap ampiezza 5 GHz o interpretazione 6 GHz.",
    "quality_dashboard_fix_scanner_details_dialog_detail": "Usa Vai Al Punto e ripeti questi punti quando ampiezza canale, frequenza o dati da scanner fallback possono influenzare le conclusioni delle mappe.",
    "quality_dashboard_fix_low_confidence_title": "Ripeti Punti a Bassa Confidenza",
    "quality_dashboard_fix_low_confidence_detail": "{count} punti hanno bassa confidenza sul candidato dominante. Ripetili o verifica la stabilità dello scanner.",
    "quality_dashboard_fix_unstable_title": "Ripeti Punti Instabili",
    "quality_dashboard_fix_unstable_detail": "{count} punti hanno una variazione dei campioni sufficiente a influenzare le mappe. Ripetili se guidano decisioni.",
    "quality_dashboard_fix_ap_position_title": "Verifica Warning Dominant AP",
    "quality_dashboard_fix_ap_position_detail": "{count} punti non tornano con le posizioni fisiche AP. Controlla i marker warning prima di trarre conclusioni.",
    "quality_dashboard_fix_ap_position_dialog_detail": "Usa Vai Al Punto per controllare ogni finding sulla pianta.",
    "quality_dashboard_fix_ap_missing_title": "Posiziona AP Mancanti",
    "quality_dashboard_fix_ap_missing_detail": "{count} gruppi AP rilevanti non hanno posizione. Aggiungi la posizione fisica prima di fidarti della diagnostica basata su distanza AP.",
    "quality_dashboard_fix_ap_metadata_title": "Verifica Metadati AP",
    "quality_dashboard_fix_ap_metadata_detail": "{count} gruppi AP hanno canali o bande fuori dai metadati attesi. Correggi i metadati oppure imposta un override del canale di analisi quando il canale misurato è intenzionale.",
    "quality_dashboard_fix_ap_metadata_dialog_detail": "Usa Apri Metadati AP per correggere canali/bande attesi o impostare un override del canale di analisi per ogni gruppo AP.",
    "quality_dashboard_fix_channel_change_clean_title": "Verifica Modello Cambio Canale",
    "quality_dashboard_fix_channel_change_ambiguous_title": "Risolvi Cambi Canale Ambigui",
    "quality_dashboard_fix_channel_change_detail": "{count} gruppi AP hanno cambiato canale durante il rilievo ({clean} puliti, {ambiguous} ambigui). Le mappe sensibili al canale usano il canale più recente per i cambi puliti; i casi ambigui restano misurati salvo override.",
    "quality_dashboard_fix_channel_change_dialog_detail": "Usa Apri Metadati AP per verificare ogni cambio canale e impostare un override quando la scelta automatica non è corretta.",
    "quality_dashboard_fix_more_points_title": "Aggiungi Punti",
    "quality_dashboard_fix_more_points_detail": "Sono disponibili solo {total} punti. Aggiungi altre posizioni prima di leggere i vuoti di copertura.",
    "quality_dashboard_fix_ready_title": "Genera Mappe",
    "quality_dashboard_fix_ready_detail": "I controlli principali sono puliti. Genera le mappe o apri le liste punti da KPI per un ultimo passaggio.",
    "quality_dashboard_context_scope": "Ambito Rilievo\nRilevanti: {networks}\nPosizioni AP: {positions}\nAP Test: {test_aps}",
    "quality_dashboard_scope_title": "Ambito Rilievo",
    "quality_dashboard_scope_relevant": "Rilevanti: {networks}",
    "quality_dashboard_scope_positions": "Posizioni AP: {positions}",
    "quality_dashboard_scope_test_aps": "AP Test: {test_aps}",
    "quality_dashboard_action_open_dominant": "Mappa Dominant AP",
    "quality_dashboard_action_open_ap_channels": "Mappa AP Channels",
    "quality_dashboard_action_open_interference": "Mappa Interference",
    "quality_dashboard_action_open_ap_metadata": "Apri Metadati AP",
    "quality_dashboard_action_open_ap_group": "Apri Gruppo AP",
    "quality_dashboard_action_focus_point": "Vai Al Punto",
    "quality_dashboard_action_metadata_for": "Metadati: {ap}",
    "quality_dashboard_action_group_for": "Gruppo AP: {ap}",
    "quality_dashboard_channel_change_status_clean": "pulito",
    "quality_dashboard_channel_change_status_ambiguous": "ambiguo",
    "quality_dashboard_channel_change_label": "{ap} {band}: {status}, canali {channels}, corrente {current}",
    "quality_dashboard_channel_change_item_detail": "{band}: canali rilevati {channels} | Mappe Usano: {current} | Stato: {status}.",
    "quality_dashboard_expand_details": "Dettagli ({count})",
    "quality_dashboard_detail_count": "{count} righe dettaglio",
    "quality_dashboard_detail_ap_groups": "{count} Gruppi AP",
    "quality_dashboard_detail_measurement_points": "{count} Punti Misura",
    "quality_dashboard_detail_channel_changes": "{count} Cambi Canale",
    "quality_dashboard_missing_position_item_detail": "Manca la posizione fisica per questo gruppo AP rilevante.",
    "quality_dashboard_point_detail_label": "Punto {point} ({x}, {y})",
    "quality_dashboard_ap_position_finding": "Finding: {finding}",
    "quality_dashboard_ap_position_detail": "AP Dominante: {dominant} | Segnale: {signal} | Distanza: {dominant_distance}\nAP Più Vicino: {closest} | Distanza: {closest_distance}",
    "quality_dashboard_context_relevant_networks": "Reti Rilevanti",
    "quality_dashboard_context_ap_positions": "Stato Posizioni AP",
    "quality_dashboard_context_test_aps": "AP Test Esclusi",
    "quality_dashboard_context_missing_positions": "AP Senza Posizione",
    "quality_dashboard_context_config_warnings": "Dettagli Configurazione AP",
    "quality_dashboard_ap_metadata_channels": "Canali Rilevati: {channels} | Canali Attesi: {expected}",
    "quality_dashboard_ap_metadata_bands": "Bande Rilevate: {bands} | Bande Attese: {expected}",
    "quality_dashboard_scanner_details_issue": "Dettagli Scanner: {detail}",
    "quality_dashboard_scanner_details_fallback": "Scanner usato: <b>{backends}</b> (dettagli canale limitati)",
    "quality_dashboard_scanner_details_missing_width": "Ampiezza canale mancante su <b>{count}</b> righe scan",
    "quality_dashboard_scanner_details_missing_frequency": "Frequenza 6 GHz mancante su <b>{count}</b> righe scan",
    "quality_dashboard_scanner_details_finding": "Dettagli Scanner Limitati",
    "quality_dashboard_scanner_details_scanner": "Scanner: <b>{backends}</b>",
    "quality_dashboard_scanner_details_checked_rows": "Righe Scan Controllate: <b>{count}</b>",
    "quality_dashboard_scanner_details_missing_width_detail": "Ampiezza Canale Mancante: <b>{count}</b> righe scan",
    "quality_dashboard_scanner_details_missing_frequency_detail": "Frequenza 6 GHz Mancante: <b>{count}</b> righe scan",
    "quality_dashboard_scanner_details_fallback_detail": "Righe Scanner Fallback: <b>{count}</b>",
    "quality_dashboard_scanner_details_impact": "Impatto: le mappe sensibili al canale possono essere meno affidabili in questo punto.",
    "quality_dashboard_issue_missing_relevant": "<b>{ssid}</b>: rete rilevante non rilevata in questo punto",
    "quality_dashboard_issue_low_confidence": "<b>{ssid}</b>: livello di confidenza {confidence}",
    "quality_dashboard_issue_unstable_signal": "<b>{ssid}</b>: segnale variabile di {range} dB",
    "quality_dashboard_issue_sparse_data": "Campioni scansione insufficienti in questo punto",
    "quality_dashboard_more_issues": "+{count} altri",
    "quality_dashboard_metric_view_points": "Vedi Punti",
    "quality_dashboard_metric_extra_details": "Extra Details",
    "quality_dashboard_metric_click_points": "Clicca Per Vedere I Punti Corrispondenti",
    "quality_dashboard_metric_click_details": "Clicca Per Aprire I Dettagli",
    "quality_dashboard_points_dialog_title": "{label} - {count} Punti",
    "quality_dashboard_check_kpi_issue": "Controlla KPI: {kpis}",
    "quality_dashboard_visible_count": "{shown}/{total} punti mostrati",
    "quality_dashboard_quality": "Qualità",
    "quality_dashboard_scan_quality": "Qualità Scansione",
    "quality_dashboard_confidence": "Confidenza",
    "quality_dashboard_issue": "Problema",
    "quality_dashboard_relevant_ssids": "SSID rilevanti",
    "quality_dashboard_no_issue": "Nessun Problema Rilevato",
    "quality_dashboard_ap_position_issue": "AP dominante: <b>{dominant}</b> ({signal}, {dominant_distance}) | AP più vicino: <b>{closest}</b> ({closest_distance}) | <b>{warning}</b>",
    "quality_dashboard_missing_positions_none": "nessuno",
    "quality_dashboard_missing_positions_more": "{names}, +{count}",
    "calibrate_scale": "Calibra Scala",
    "calibrate_scale_title": "Calibrazione Scala",
    "calibrate_scale_start": "Clicca col sinistro il primo punto della distanza reale nota.",
    "calibrate_scale_second_point": "Clicca col sinistro il secondo punto della distanza nota.",
    "calibrate_scale_distance_prompt": "Distanza reale tra i due punti ({unit}):",
    "calibrate_scale_saved": "Scala calibrata: {scale}.",
    "calibrate_scale_invalid": "Distanza non valida.",
    "calibrate_scale_cancelled": "Calibrazione scala annullata.",
    "calibrate_scale_already_set": "Scala già calibrata. Elimina la scala attuale per rifarla.",
    "delete_scale": "Elimina Scala",
    "delete_scale_title": "Elimina Scala",
    "delete_scale_confirm": "Vuoi eliminare la calibrazione della scala salvata per questo rilievo?",
    "delete_scale_done": "Scala eliminata. Puoi eseguire una nuova calibrazione.",
    "max_distance_unit": "Distanza Max ({unit})",
    "max_distance_m": "Distanza Max (m)",
    "ap_groups_title": "AP Group Manager",
    "ap_groups_hint": "Seleziona un gruppo e usa i pulsanti per modificare alias, ruolo, BSSID, metadati o posizione. La colonna Gestione indica se il gruppo è automatico o bloccato da modifiche manuali.",
    "ap_group_bssid_title": "BSSID del Gruppo",
    "ap_group_bssid_hint": "Seleziona i BSSID che appartengono a questo AP fisico. I BSSID selezionati verranno rimossi automaticamente dagli altri gruppi.",
    "ap_group_bssid_warning_focus_hint": "I BSSID coinvolti nel warning sono mostrati per primi. Usa i checkbox per definire l'AP corrente, oppure seleziona righe per creare/spostare un gruppo separato.",
    "ap_group_bssid_other_group": "Altro Gruppo",
    "ap_group_bssid_scope": "Mostra",
    "ap_group_bssid_scope_all": "Tutti",
    "ap_group_bssid_scope_current": "Gruppo Corrente",
    "ap_group_bssid_scope_other": "Altri Gruppi",
    "ap_group_bssid_scope_unassigned": "Non assegnati",
    "ap_group_bssid_scope_checked": "Selezionati",
    "ap_group_bssid_scope_warning": "Solo Warning",
    "ap_group_bssid_filter_all": "Tutti",
    "ap_group_bssid_select_visible": "Seleziona Visibili",
    "ap_group_bssid_clear_visible": "Deseleziona Visibili",
    "ap_group_bssid_invert_visible": "Inverti Visibili",
    "ap_group_bssid_new_group_from_rows": "Nuovo Gruppo",
    "ap_group_bssid_move_rows": "Sposta Righe...",
    "ap_group_bssid_select_rows_required": "Seleziona prima una o più righe BSSID.",
    "ap_group_bssid_visible_count": "{visible}/{total} BSSID",
    "ap_group_empty_selection": "Il gruppo deve contenere almeno un BSSID.",
    "ap_group_split_source_empty": "Lascia almeno un BSSID nel gruppo corrente prima di creare un nuovo gruppo.",
    "ap_group_move_no_target": "Non ci sono altri gruppi AP in cui spostare i BSSID selezionati.",
    "ap_group_move_target_title": "Sposta BSSID",
    "ap_group_move_target_prompt": "Gruppo AP di destinazione:",
    "ap_group_move_target_with_alias": "{alias} ({group}, {count} BSSID)",
    "ap_group_move_target_without_alias": "{group} ({count} BSSID)",
    "ap_group_bssid_management": "Gestione BSSID",
    "ap_group_fix_from_warning": "Correggi gruppo AP",
    "ap_group_conflict_count": "Possibili conflitti: {count}",
    "ap_group_conflict_details": "Dettaglio Warning",
    "ap_group_conflict_title": "Possibile Gruppo AP Incoerente",
    "ap_group_conflict_none": "Nessun warning sul gruppo selezionato.",
    "ap_group_conflict_hint": "Questo warning indica che lo stesso gruppo AP contiene BSSID osservati su più canali nella stessa banda.",
    "ap_group_conflict_group": "Gruppo AP: {group}",
    "ap_group_conflict_diagnosis_title": "Cosa Può Significare",
    "ap_group_conflict_diagnosis_body": "- un canale è cambiato durante il rilievo\n- un AP multiradio particolare usa la stessa banda in modo non comune\n- BSSID non collegati tra loro sono stati raggruppati e vanno separati",
    "ap_group_conflict_recommendation_title": "Controllo Consigliato",
    "ap_group_conflict_recommendation_body": "Se i BSSID non appartengono allo stesso AP fisico, usa Correggi gruppo AP, seleziona le righe BSSID coinvolte e crea un nuovo gruppo o spostale in un altro gruppo. Se sono lo stesso AP, mantieni il gruppo e validalo con un rilievo più ampio o con i metadati AP.",
    "ap_group_conflict_details_title": "Canali Osservati",
    "ap_group_conflict_band_summary": "{band}: {channel_count} canali, {bssid_count} BSSID ({channels})",
    "ap_group_conflict_band_row": "Banda {band}: canali {channels}",
    "ap_group_conflict_channel_row": "CH {channel}: {bssids}",
    "ap_group_memory_menu": "Memoria",
    "ap_group_confirm_memory": "Conferma Memoria",
    "ap_group_confirm_memory_selected": "Conferma Selezionato",
    "ap_group_confirm_memory_all": "Conferma Tutti Da Memoria...",
    "ap_group_confirm_memory_all_title": "Conferma Memoria AP",
    "ap_group_confirm_memory_all_confirm": "Confermare {count} gruppi AP applicati dalla memoria AP?",
    "ap_group_update_from_memory": "Aggiorna Da Memoria",
    "ap_group_update_memory_selected": "Aggiorna Selezionato Da Memoria",
    "ap_group_status_warning_tooltip": "Questo Gruppo AP ha diagnostiche di warning.",
    "ap_group_status_memory_tooltip": "I metadati sono stati applicati dalla memoria AP. Verificali e confermali, oppure modifica i dati AP.",
    "ap_group_status_memory_update_tooltip": "La memoria AP contiene dati salvati diversi per: {fields}. Usa Aggiorna Da Memoria per allineare questo Gruppo AP.",
    "ap_group_alias_menu": "Alias",
    "ap_group_set_alias": "Imposta/Modifica Alias",
    "ap_group_delete_alias": "Elimina Alias...",
    "ap_group_set_role": "Imposta Ruolo",
    "ap_group_role": "Ruolo",
    "ap_group_role_title": "Ruolo Gruppo AP",
    "ap_group_role_prompt": "Ruolo da assegnare a questo gruppo AP:",
    "ap_group_role_internal": "Interno",
    "ap_group_role_external": "Esterno",
    "ap_group_role_interferer": "Interferente",
    "ap_group_role_test": "Test/nascosto",
    "ap_group_metadata": "Metadati",
    "ap_group_metadata_title": "Metadati Gruppo AP",
    "ap_group_metadata_hint": "Aggiungi informazioni descrittive sull'AP fisico. Bande e canali attesi sono guidati perché vengono usati dai controlli qualità.",
    "ap_group_metadata_vendor": "Vendor",
    "ap_group_metadata_model": "Modello",
    "ap_group_metadata_mounting": "Montaggio",
    "ap_group_metadata_expected_bands": "Bande Attese",
    "ap_group_metadata_band": "Banda",
    "ap_group_metadata_channels": "Canali",
    "ap_group_metadata_selected_channels": "Selezione Attiva",
    "ap_group_metadata_edit_channels": "Canali...",
    "ap_group_metadata_channel_picker_title": "Canali {band}",
    "ap_group_metadata_no_channels": "Nessun canale selezionato",
    "ap_group_metadata_band_disabled": "Banda non selezionata",
    "ap_group_metadata_channels_unavailable": "Canali non disponibili",
    "ap_group_metadata_channel_group_24": "2.4 GHz",
    "ap_group_metadata_channel_group_5_low": "5 GHz Basso",
    "ap_group_metadata_channel_group_5_dfs": "5 GHz DFS",
    "ap_group_metadata_channel_group_5_high": "5 GHz Alto",
    "ap_group_metadata_select_all": "Tutti",
    "ap_group_metadata_clear": "Nessuno",
    "ap_group_metadata_analysis_channels": "Override Canale Analisi",
    "ap_group_metadata_analysis_channel_hint": "Usato dalle mappe sensibili al canale quando questo AP ha cambiato canale durante il rilievo. Lascia Auto per usare l'ultimo canale pulito.",
    "ap_group_metadata_analysis_channel": "Canale Analisi",
    "ap_group_metadata_analysis_channel_auto": "Auto",
    "ap_group_metadata_analysis_channel_not_observed": "Non Rilevata",
    "ap_group_metadata_notes": "Note",
    "ap_group_set_position": "Posiziona su Mappa",
    "ap_group_position": "Posizione",
    "ap_group_position_tooltip_title": "Posizione AP",
    "ap_position_pick": "Clic sinistro sulla pianta per impostare la posizione fisica di {group}. Esc annulla.",
    "ap_position_saved": "Posizione AP salvata: {group} x={x}, y={y}.",
    "ap_position_cancelled": "Posizionamento AP annullato.",
    "ap_position_distance": "Distanza AP",
    "ap_position_nearest": "AP Fisico più Vicino",
    "ap_position_analysis": "Analisi Posizione",
    "ap_position_detail": "Dettaglio Posizione",
    "ap_position_distance_m": "{distance} m",
    "ap_position_distance_px": "{distance} px",
    "ap_position_ok": "Coerente",
    "ap_position_no_scale": "Scala non calibrata",
    "ap_position_strong_far": "Segnale forte lontano dall'AP",
    "ap_position_weak_close": "Segnale debole vicino all'AP",
    "ap_position_unexpected_dominant": "AP dominante non vicino fisicamente",
    "ap_position_warning_legend": "Triangolo = posizione AP sospetta",
    "ap_position_unknown_warning": "Warning Posizione",
    "ap_group_not_found": "Gruppo AP non trovato.",
    "ap_group_alias_title": "Alias Gruppo AP",
    "ap_group_alias_prompt": "Alias da usare per questo AP:",
    "ap_group_delete_alias_title": "Elimina Alias",
    "ap_group_delete_alias_confirm": "Vuoi eliminare l'alias dal gruppo AP selezionato?",
    "ap_group_select_group": "Seleziona prima un gruppo AP.",
    "ap_groups_reset_auto": "Reset Auto",
    "ap_groups_reset_title": "Ripristina Gruppi AP",
    "ap_groups_reset_confirm": "Vuoi ripristinare il raggruppamento automatico dei BSSID? Gli alias compatibili verranno mantenuti, ma le modifiche manuali ai gruppi verranno perse.",
    "ap_alias_group": "Gruppo AP",
    "ap_label": "Etichetta",
    "ap_alias_bssids": "BSSID",
    "ap_alias_ssids": "SSID visti",
    "ap_alias_channels": "Canali",
    "ap_alias_value": "Alias",
    "ap_group_management": "Gestione",
    "ap_group_state_manual": "Manuale",
    "ap_group_state_auto": "Auto",
    "ap_group_state_memory": "Da Memoria",
    "ap_group_state_memory_update": "Memoria Da Aggiornare",
    "ap_group_filter_status": "Stato",
    "ap_group_filter_status_all": "Tutti gli Stati",
    "ap_group_filter_status_warning": "Warning",
    "ap_group_filter_status_ok": "OK",
    "ap_group_filter_role": "Ruolo",
    "ap_group_filter_role_all": "Tutti i Ruoli",
    "ap_group_filter_band": "Banda",
    "ap_group_filter_band_all": "Tutte le Bande",
    "ap_group_filter_state": "Gestione",
    "ap_group_filter_state_all": "Tutte",
    "ap_group_clear_filters": "Pulisci Filtri",
    "ap_group_visible_count": "{visible}/{total} gruppi",
    "ap_alias_search": "Cerca",
    "ap_groups_saved": "Gruppi AP salvati.",
    "yes": "Sì",
    "help": "Help",
    "fit": "Fit",
    "map": "Mappa",
    "saved_network": "Reti Rilevanti",
    "relevant_networks_none": "Nessuna Rete Rilevante Definita",
    "manage_relevant_networks": "Gestisci",
    "manage_relevant_networks_title": "Gestisci Reti Rilevanti",
    "manage_relevant_networks_message": "Seleziona gli SSID da considerare rilevanti per il rilievo. La scelta aggiorna anche i punti già raccolti.",
    "no_relevant_networks_to_manage": "Non ci sono ancora SSID rilevati da gestire.",
    "relevant_networks_updated": "Reti rilevanti aggiornate.",
    "forget_saved_network": "Azzera",
    "relevant_networks_cleared": "Reti rilevanti azzerate.",
    "best_dbm": "Migliore dBm",
    "quality": "Qualità",
    "quality_good": "OK",
    "quality_missing_relevant": "Manca Rete",
    "quality_low_confidence": "Bassa Confidenza",
    "quality_unstable_signal": "Instabile",
    "quality_sparse_data": "Scarso",
    "quality_breakdown_title": "Dettaglio Qualità Punto",
    "rows": "Righe",
    "go_to_point": "Vai al Punto",
    "rescan_point": "Rimisura Punto",
    "point_rescanned": "Punto rimisurato: x={x}, y={y}, vecchie righe rimosse={rows}, nuove reti={count}.",
    "delete_selected": "Elimina Selezionato",
    "delete_last": "Elimina Ultimo",
    "band": "Banda",
    "all_bands_option": "Tutte",
    "map_type": "Tipo Mappa",
    "map_type_signal": "Copertura Segnale",
    "map_type_interference": "Interferenza AP",
    "map_type_channel": "Canali AP",
    "map_type_dominant": "AP Dominante",
    "channel_map_legend_title": "Canali AP",
    "channel_map_intermediate_24": "Canali Intermedi",
    "dominant_map_legend_title": "AP Dominante",
    "dominant_map_roaming_overlap": "Δ <= 5 dB",
    "dominant_roaming_issue_title": "Sovrapposizione Roaming",
    "dominant_roaming_issue_detail": "L'AP più forte è entro la soglia roaming di {threshold}:\nAP Dominante: {dominant} | {dominant_signal}\nAP Secondario: {second} | {second_signal}\nIl client può fare roaming o oscillare qui.",
    "point_labels": "Etichette Punti",
    "point_labels_auto": "Automatiche",
    "point_labels_critical": "Solo Criticità",
    "point_labels_all": "Tutte",
    "point_labels_none": "Nessuna",
    "reference_table_info": "Riferimento",
    "reference_more_in_report": "+ {count} altri nel report CSV",
    "legend_other": "Altri",
    "reference_channel": "Canale",
    "reference_width": "Larghezza",
    "channel_width": "Larghezza Canale",
    "reference_ap": "AP",
    "reference_delta": "Delta Secondo AP",
    "reference_risk": "Rischio",
    "reference_serving_channel": "Canale Servente",
    "reference_interferer_channel": "Canale Interferente",
    "second_ap": "Secondo AP",
    "second_ap_role": "Ruolo Secondo AP",
    "second_confidence": "Conf. Secondo",
    "serving_ap": "AP Servente",
    "export_signal_title": "Copertura Segnale Wi-Fi",
    "export_channel_title": "Canali AP Wi-Fi",
    "export_dominant_title": "AP Dominante Wi-Fi",
    "export_interference_title": "Interferenza AP Wi-Fi",
    "export_signal_colorbar": "Segnale stimato dBm",
    "export_points": "punti",
    "export_measurements": "rilevamenti",
    "export_roaming_overlap": "overlap roaming",
    "interference_mode": "Analisi Interferenza",
    "interference_mode_intra_ssid": "Intra-SSID",
    "interference_mode_all": "Tutti gli SSID",
    "interference_colorbar": "Rischio interferenza %",
    "interference_legend_title": "Rischio AP",
    "interference_low": "basso",
    "interference_medium": "medio",
    "interference_high": "alto",
    "interference_top_risk": "Rischio Max",
    "interference_summary_title": "Riepilogo Interferenze",
    "interference_summary_band": "Banda",
    "interference_summary_max_risk": "Rischio Massimo",
    "interference_summary_point": "Punto",
    "interference_summary_serving_ap": "AP Servente",
    "interference_summary_serving_role": "Ruolo Servente",
    "interference_summary_serving_channel": "Canale Servente",
    "interference_summary_serving_width": "Larghezza Servente",
    "interference_summary_interferer": "Interferente Principale",
    "interference_summary_interferer_role": "Ruolo Interferente",
    "interference_summary_interferer_ssid": "SSID Interferente",
    "interference_summary_interferer_channel": "Canale Interferente",
    "interference_summary_interferer_width": "Larghezza Interferente",
    "interference_summary_interferer_dbm": "Segnale Interferente",
    "interference_summary_test_ignored": "AP Test Ignorati",
    "interference_channel_change": "Cambio Canale",
    "interference_channel_change_note": "{ap} ha cambiato canale durante il rilievo ({channels} -> {current}); le mappe sensibili al canale usano l'ultimo canale {current}.",
    "interference_channel_change_manual_note": "{ap} usa il canale analisi manuale {current}; canali osservati: {channels}.",
    "interference_summary_diagnosis": "Diagnosi",
    "interference_diagnosis_low": "Il rischio principale è basso: la coesistenza tra AP non sembra critica in questo punto.",
    "interference_diagnosis_same_channel_strong": "Il problema principale è un interferente forte sullo stesso canale dell'AP servente.",
    "interference_diagnosis_same_channel": "Il problema principale è la presenza di un AP sullo stesso canale dell'AP servente.",
    "interference_diagnosis_wide_channel": "Il problema principale è una sovrapposizione causata da canali larghi.",
    "interference_diagnosis_strong": "Il problema principale è un interferente forte su un canale che contribuisce al rischio.",
    "interference_diagnosis_nearby": "Il problema principale sembra un canale vicino o parzialmente sovrapposto.",
    "interference_quality_title": "Qualità Dati Interferenza",
    "interference_quality_width_coverage": "Larghezza canale disponibile: {available}/{total} punti ({percent}%).",
    "interference_quality_good": "La stima usa larghezza canale su una quota sufficiente di punti.",
    "interference_quality_warning": "La larghezza canale è disponibile su pochi punti: la stima usa fallback dove il dato manca.",
    "interference_quality_warning_5ghz": "La larghezza canale è disponibile su pochi punti: su 5/6 GHz la stima può sottovalutare sovrapposizioni tra canali larghi.",
    "usable_only": "Solo >= -70 dBm",
    "max_distance_px": "Distanza max (px)",
    "interpolation": "Interpolazione",
    "interpolation_rbf": "RBF Morbida",
    "interpolation_linear": "Lineare",
    "aggregation": "Aggregazione Punto",
    "aggregation_max": "Migliore",
    "aggregation_mean": "Media",
    "aggregation_median": "Mediana",
    "color_scale": "Scala Colori",
    "color_scale_fixed": "Fissa",
    "color_scale_auto": "Automatica",
    "smoothing": "Smoothing",
    "theme": "Tema",
    "qt_theme_light": "Sand Blue",
    "qt_theme_soft": "Soft Olive",
    "qt_theme_dark": "Slate Blue",
    "qt_theme_contrast": "Graphite Green",
    "close": "Chiudi",
    "cancel": "Annulla",
    "select_plan_title": "Seleziona Pianta",
    "images": "Immagini",
    "load_plan_first": "Carica prima una pianta.",
    "warning": "Attenzione",
    "empty_csv": "Il rilievo è vuoto.",
    "no_ssid": "Nessun SSID disponibile.",
    "select_ssid_heatmap": "Seleziona un SSID per esportare la mappa.",
    "insufficient_data_title": "Dati Insufficienti",
    "insufficient_data": "Servono almeno 3 punti per generare una heatmap nella banda {band}.",
    "interference_requires_band": "Per la mappa interferenza seleziona 2.4 GHz, 5 GHz o 6 GHz.",
    "save_required_title": "Salvataggio Richiesto",
    "save_required": "Per esportare il PDF devi prima salvare il rilievo CSV.",
    "save_failed": "Salvataggio annullato. Heatmap non generata.",
    "heatmap_generated": "Heatmap Generata",
    "file_created": "File creato:\n{path}",
    "files_created": "File creati:\n{paths}",
    "unsaved_changes_title": "Rilievo Non Salvato",
    "unsaved_changes": "Ci sono modifiche non salvate.\n\nVuoi salvare il rilievo prima di uscire?",
    "survey_saved": "Rilievo salvato: {name}",
    "best": "Migliore",
    "confidence": "confidenza",
    "connected_ssid_option": "{ssid} (connessa)",
    "relevant_networks_title": "Reti Rilevanti",
    "relevant_networks_first_message": "Seleziona gli SSID rilevanti per questo rilievo. Tutte le reti verranno salvate, ma queste saranno controllate nei punti successivi.",
    "new_relevant_networks_title": "Nuove Reti Rilevate",
    "new_relevant_networks_message": "Sono stati rilevati nuovi SSID. Se qualcuno è rilevante per il rilievo, selezionalo.",
    "missing_relevant_networks_title": "Reti Rilevanti Mancanti",
    "missing_relevant_networks_message": "Queste reti rilevanti non sono state rilevate:\n{ssids}\n\nVuoi salvare comunque il punto, ritentare la scansione o annullare?",
    "cancelled": "annullato",
    "no_networks_found": "Nessuna rete trovata. Verifica che il Wi-Fi sia attivo.",
    "error": "Errore",
    "point_saved": "Punto salvato: x={x}, y={y}, reti registrate={count}",
    "scanning": "Scansione Wi-Fi in corso nel punto x={x}, y={y}...",
    "map_loaded_points": "Pianta caricata. Punti ripristinati={count}. Rilievo: {name}",
    "map_loaded": "Pianta caricata. Rilievo attivo: {name}. Clicca sulla posizione.",
    "map_not_found_title": "Mappa Non Trovata",
    "map_not_found": "Il CSV fa riferimento a una mappa che non esiste più:\n{path}\n\nSeleziona manualmente la pianta aggiornata.",
    "select_point": "Seleziona un punto nella tabella.",
    "no_point_to_delete": "Nessun punto da eliminare in questa sessione.",
    "last_point_deleted": "Ultimo punto eliminato: x={x}, y={y}, righe rimosse={rows}",
    "point_deleted": "Punto eliminato: x={x}, y={y}, righe rimosse={rows}",
    "zoom": "Zoom: {zoom:.0%}",
    "all_bands_label": "tutte le bande",
    "help_title": "Centro Guida",
    "help_overview_nav": "Workflow Consigliato",
    "help_overview_title": "Workflow Consigliato Per Il Rilievo",
    "help_overview_subtitle": "Usa il programma come flusso di validazione: raccogli evidenze, controlla la qualità, sistema il modello AP e poi esporta le mappe.",
    "help_overview_body": """
        <table class="callout-table"><tr><td class="callout-accent-good"></td><td class="callout-content"><span class="callout-label">Regola Principale</span><br>Non fidarti di una mappa prima di aver controllato dati del rilievo e modello AP. La heatmap è il risultato finale, non il primo passaggio.</td></tr></table>
        <h2>Sequenza Operativa</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card">
                    <div class="step-label">1. Setup</div>
                    <div class="step-title">Prepara il rilievo</div>
                    <p>Crea o apri il rilievo, carica la pianta, scegli il sistema di misura se serve, calibra la scala e scegli gli SSID rilevanti.</p>
                    <div class="step-gate"><b>Vai avanti quando:</b> pianta, scala e reti da giudicare sono corrette.</div>
                </td>
                <td class="workflow-gap"></td>
                <td class="workflow-card">
                    <div class="step-label">2. Acquisizione</div>
                    <div class="step-title">Raccogli evidenze RF</div>
                    <p>Registra punti in stanze, corridoi, zone di transizione e punti deboli noti.</p>
                    <div class="step-gate"><b>Vai avanti quando:</b> le aree importanti hanno abbastanza punti e le scansioni sospette sono state riprovate.</div>
                </td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card">
                    <div class="step-label">3. Validazione</div>
                    <div class="step-title">Controlla la qualità</div>
                    <p>Apri Qualità Rilievo e separa problemi di rescan da diagnostica AP.</p>
                    <div class="step-gate"><b>Vai avanti quando:</b> la qualità dei punti è accettabile e i finding rimasti sono compresi.</div>
                </td>
                <td class="workflow-gap"></td>
                <td class="workflow-card">
                    <div class="step-label">4. Modello AP</div>
                    <div class="step-title">Rendi credibile il modello AP</div>
                    <p>Rivedi gruppi AP, alias, ruoli, BSSID, metadata, posizioni AP, override canale e flag AP Memory.</p>
                    <div class="step-gate"><b>Vai avanti quando:</b> il modello AP corrisponde al deployment o è documentato come incerto.</div>
                </td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card" colspan="3">
                    <div class="step-label">5. Analisi</div>
                    <div class="step-title">Usa le mappe come output validato</div>
                    <p>Usa Mappe Live e PDF per controllare copertura, canali, roaming e interferenza.</p>
                    <div class="step-gate"><b>Vai avanti quando:</b> i warning sono stati rivisti e sai spiegarli.</div>
                </td>
            </tr>
        </table>
        <h2>Punti Di Controllo</h2>
        <div class="gate-list">
            <div class="gate-row"><b>Distanze:</b> scegli metrico o imperiale nei settings prima della calibrazione. Cambiare sistema di misura dopo cancella la scala attuale, quindi va rifatta prima di interpretare warning sulle posizioni AP.</div>
            <div class="gate-row"><b>Copertura:</b> verifica SSID rilevanti e qualità punti prima di fidarti di zone buone o problematiche.</div>
            <div class="gate-row"><b>Interferenza:</b> verifica gruppi AP, ruoli, gestione cambi canale e override canale prima di fidarti delle mappe sensibili al canale.</div>
            <div class="gate-row"><b>Export:</b> apri la live map collegata e leggi tooltip warning o righe dettaglio prima di generare il PDF.</div>
        </div>
        <table class="section-card callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Come Ragiona Il Programma</span><br>Punti, raw scan, metadata AP, stato AP Memory e posizioni fisiche sono trattati come evidenze. I warning non sono automaticamente errori. Indicano quale ipotesi va controllata: qualità punto, gruppo AP, modello canale, posizione fisica o comportamento RF reale.</td></tr></table>
    """,
    "help_controls_nav": "Controlli",
    "help_controls_title": "Comandi Rapidi",
    "help_controls_subtitle": "Il workflow V2 usa ancora gesti diretti sulla mappa. Questi sono i controlli più frequenti durante rilievo e revisione.",
    "help_controls_body": """
        <table class="callout-table" width="100%" cellspacing="0" cellpadding="0"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Regola Dei Gesti</span><br>Clic sinistro, trascinamento con sinistro e modificatori della rotella sono controlli separati. Ctrl e Shift sono tasti modificatori: servono in combinazione con la rotella, non come azioni mappa autonome.</td></tr></table>
        <h2>Il Contesto Conta</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>Mappa Survey Normale</b><br>Il tasto destro crea punti di misura. Il sinistro seleziona un marker punto esistente o pulisce la selezione se clicchi lo sfondo.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Modalità Temporanee</b><br>Calibrazione scala e posizionamento AP catturano il clic sinistro finché la modalità non viene completata o annullata.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Trascina Non È Click</b><br>Il clic sinistro seleziona; clic sinistro e movimento trascinano quando la vista mappa supporta il pan.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Zoom/Pan Sono Visuali</b><br>Zoom, scroll e pan cambiano solo la vista. Non modificano i dati raccolti.</td>
            </tr>
        </table>
    """,
    "help_control_right_click_title": "Tasto Destro",
    "help_control_right_click_text": "Crea un punto di misura sulla mappa del rilievo.",
    "help_control_left_click_title": "Tasto Sinistro",
    "help_control_left_click_text": "Seleziona un punto di misura o usa la modalità temporanea attiva, per esempio calibrazione scala o posizionamento AP.",
    "help_control_left_drag_title": "Tasto Sinistro + Trascina",
    "help_control_left_drag_text": "Sposta la pianta o la mappa live quando la vista corrente è più grande della viewport e il pan è disponibile.",
    "help_control_scroll_title": "Rotella",
    "help_control_scroll_text": "Scorre verticalmente liste, pannelli e viste mappa.",
    "help_control_shift_title": "Shift + Rotella",
    "help_control_shift_text": "Sposta orizzontalmente la pianta o la mappa live quando lo scorrimento orizzontale è disponibile.",
    "help_control_ctrl_title": "Ctrl + Rotella",
    "help_control_ctrl_text": "Esegue lo zoom sulla pianta o sulla preview della mappa live.",
    "help_survey_nav": "Rilievo E Scansioni",
    "help_survey_title": "Punti, Raw Scan E Confidenza",
    "help_survey_subtitle": "Un punto non è solo un valore di segnale: V2 salva campioni grezzi, li aggrega e misura la confidenza.",
    "help_survey_body": """
        <h2>Box Schermata Rilievo</h2>
        <table class="survey-grid">
            <tr>
                <td class="survey-card"><span class="survey-card-title">CSV</span><br>Il file rilievo salvato, con commenti metadata e righe aggregate.<br><span class="survey-card-use">Salva prima di esportare PDF o spostare il rilievo su un altro PC.</span></td>
                <td class="survey-gap"></td>
                <td class="survey-card"><span class="survey-card-title">Mappa</span><br>Il file pianta collegato al rilievo.<br><span class="survey-card-use">Se il vecchio percorso manca, seleziona manualmente la pianta aggiornata.</span></td>
                <td class="survey-gap"></td>
                <td class="survey-card"><span class="survey-card-title">Punti</span><br>Posizioni di misura raccolte sulla pianta.<br><span class="survey-card-use">Aggiungi punti dove i client lavorano, fanno roaming o segnalano problemi.</span></td>
            </tr>
            <tr><td class="survey-vertical-gap" colspan="5"></td></tr>
            <tr>
                <td class="survey-card"><span class="survey-card-title">Raw Rows</span><br>Campioni ripetuti salvati nel sidecar <code>.scan</code> collegato.<br><span class="survey-card-use">Più evidenza grezza migliora confidenza e diagnostica.</span></td>
                <td class="survey-gap"></td>
                <td class="survey-card"><span class="survey-card-title">Gruppi AP</span><br>Il modello AP fisico corrente disponibile a mappe e controlli qualità.<br><span class="survey-card-use">Rivedilo prima di fidarti di AP Dominante, Interferenza o Canali AP.</span></td>
                <td class="survey-gap"></td>
                <td class="survey-card"><span class="survey-card-title">SSID Rilevanti</span><br>Reti selezionate come importanti per i controlli qualità.<br><span class="survey-card-use">Usa Gestisci per aggiungerle/rimuoverle; Azzera pulisce la selezione.</span></td>
            </tr>
        </table>
        <h2>Cosa Viene Salvato</h2>
        <p>Ogni punto di misura può contenere più reti osservate. Il CSV principale salva le righe aggregate usate dalle mappe. Il sidecar <code>.scan</code> collegato salva l'evidenza grezza delle scansioni ripetute.</p>
        <h2>SSID Rilevanti</h2>
        <p>Gli SSID rilevanti indicano al motore qualità quali reti contano. Una rete rilevante mancante è un finding qualità. Una rete vicina non importante, di solito, no.</p>
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Regola Pratica</span><br>Imposta presto gli SSID rilevanti. Se li aggiungi solo dopo aver raccolto punti, la dashboard può rivelare punti da rivedere perché le reti previste non erano state viste.</td></tr></table>
        <h2>Sidecar Raw Scan</h2>
        <p>Il file <code>.scan</code> è un sidecar, non qualcosa che l'utente normalmente apre direttamente. Conserva campioni ripetuti, dettagli backend e campi specifici dello scanner quando disponibili. Per questo V2 può spiegare confidenza, segnale instabile e dati radi invece di disegnare solo colori.</p>
        <table>
            <tr><th>Valore Salvato</th><th>Perché Conta</th></tr>
            <tr><td>Mediana dBm</td><td>Riduce l'effetto di uno spike temporaneo.</td></tr>
            <tr><td>Min/max dBm</td><td>Mostra quanto si è mosso il segnale durante le scansioni ripetute.</td></tr>
            <tr><td>Campioni visti/totali</td><td>Alimenta confidenza e controlli dati radi.</td></tr>
            <tr><td>Banda/frequenza/larghezza canale</td><td>Migliora Canali AP, Interferenza e interpretazione 6 GHz.</td></tr>
        </table>
        <h2>Backend Scanner</h2>
        <table>
            <tr><th>Backend</th><th>Uso</th><th>Note</th></tr>
            <tr><td>Auto</td><td>Scelta consigliata</td><td>Prova prima <code>lswifi</code>, poi usa <code>netsh</code> come fallback.</td></tr>
            <tr><td>lswifi</td><td>Scanner preferito</td><td>Di solito cattura più dettagli su BSSID, banda, frequenza, sicurezza e larghezza canale.</td></tr>
            <tr><td>netsh</td><td>Fallback Windows</td><td>Utile quando lswifi non è disponibile, ma in genere espone meno dettagli RF.</td></tr>
        </table>
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Scansioni Sospette</span><br>Se una scansione vede molte meno reti rilevanti, riprova prima di salvare il punto. È quasi sempre più rapido che correggere un punto sporco dopo.</td></tr></table>
        <h2>Azioni Tabella Punti</h2>
        <table>
            <tr><th>Azione</th><th>Uso</th></tr>
            <tr><td>Vai Al Punto</td><td>Centra il punto selezionato sulla pianta.</td></tr>
            <tr><td>Riscansiona Punto</td><td>Ripete la scansione del punto selezionato quando i finding qualità suggeriscono evidenza sporca.</td></tr>
            <tr><td>Elimina Selezionato / Elimina Ultimo</td><td>Rimuove evidenza di misura quando il punto è stato posizionato o acquisito male.</td></tr>
        </table>
        <h2>Buon Posizionamento Punti</h2>
        <table class="callout-table"><tr><td class="callout-accent-good"></td><td class="callout-content"><span class="callout-label">Regola Sul Campo</span><br>
            <ul>
                <li>Metti punti dove i client lavorano davvero: scrivanie, sale riunioni, corridoi, porte e zone problematiche note.</li>
                <li>Aggiungi punti vicino alle transizioni AP. AP Dominante e roaming dipendono dall'evidenza in quelle zone.</li>
                <li>Evita scansioni mentre ti muovi. Fermati, lascia completare la scansione, poi passa al punto successivo.</li>
            </ul>
        </td></tr></table>
    """,
    "help_quality_nav": "Qualità Rilievo",
    "help_quality_title": "Dashboard Qualità Rilievo",
    "help_quality_subtitle": "La dashboard separa evidenza di scansione, diagnostica modello AP e punti da controllare prima di fidarsi delle mappe.",
    "help_quality_body": """
        <h2>Leggi La Dashboard Su Due Livelli</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card">
                    <div class="step-label">Livello 1</div>
                    <div class="step-title">Qualità Punto</div>
                    <p>Decidi se i punti di misura sono affidabili. Reti rilevanti mancanti, evidenza rada, dettagli scanner limitati, bassa confidenza e segnale instabile sono finding a livello punto.</p>
                    <div class="step-gate"><b>Azione tipica:</b> vai al punto, ispezionalo, riscansionalo o raccogli punti vicini prima di fidarti delle mappe costruite da quei dati.</div>
                </td>
                <td class="workflow-gap"></td>
                <td class="workflow-card">
                    <div class="step-label">Livello 2</div>
                    <div class="step-title">Modello AP</div>
                    <p>Decidi se gruppi AP, ruoli, metadata, stato memoria, cambi canale e posizioni fisiche AP spiegano quello che è stato misurato.</p>
                    <div class="step-gate"><b>Azione tipica:</b> apri la mappa, i metadata AP o AP Group Manager e correggi il modello prima di interpretare la mappa.</div>
                </td>
            </tr>
        </table>
        <h2>Controlli Dashboard</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card">
                    <div class="step-title">Liste Punti Da KPI</div>
                    <p>La dashboard principale non mostra subito la tabella punti. Clicca le KPI di evidenza punto, per esempio Punti Da Verificare, Bassa Confidenza Scansione o Segnale Instabile, per aprire liste punti compatte. Dettagli Scanner Mancanti e Anomalie Dominant AP aprono invece le rispettive finestre Extra Details più ricche. Totale Punti e Scan OK sono solo riepiloghi. La colonna Problema segue il contesto della KPI; le diagnostiche lunghe restano su una riga e mostrano il testo completo nel tooltip.</p>
                    <div class="step-gate"><b>Vai Al Punto:</b> da una lista punti chiude la dashboard, seleziona il punto nel tab Survey e apre il pannello punto per ispezione o rescan.</div>
                </td>
                <td class="workflow-gap"></td>
                <td class="workflow-card">
                    <div class="step-title">Dettagli Raccomandazioni</div>
                    <p><b>Dettagli</b> apre una finestra più grande per una raccomandazione. Così la dashboard principale resta compatta anche con molti gruppi AP o punti da rivedere.</p>
                    <div class="step-gate"><b>Usalo quando:</b> il riepilogo della card non basta per decidere l'azione successiva.</div>
                </td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card">
                    <div class="step-title">Azioni Mappa</div>
                    <p>I pulsanti Canali AP, Interferenza e AP Dominante aprono la mappa live con focus su banda, gruppo AP o punto quando il finding ha contesto mappa.</p>
                </td>
                <td class="workflow-gap"></td>
                <td class="workflow-card">
                    <div class="step-title">Azioni Modello AP</div>
                    <p>Apri Metadati AP e Apri Gruppo AP portano all'editor o alla riga AP Group Manager che può correggere il problema di modello.</p>
                </td>
            </tr>
        </table>
        <h2>Significato KPI</h2>
        <table class="survey-grid">
            <tr>
                <td class="survey-card">
                    <div class="survey-card-title">Punti Rilievo</div>
                    <p><b>Punti Totali:</b> evidenza spaziale raccolta.</p>
                    <p><b>Scan OK:</b> punti con evidenza scan utilizzabile.</p>
                    <p><b>Punti Da Verificare:</b> punti da ispezionare prima di fidarsi delle mappe. Non tutti richiedono per forza una nuova misura: alcuni richiedono controllo del modello o della posizione AP.</p>
                    <p><b>Card cliccabili:</b> aprono una lista punti o una finestra Extra Details, in base al tipo di diagnostica.</p>
                </td>
                <td class="survey-gap"></td>
                <td class="survey-card">
                    <div class="survey-card-title">Qualità Scan</div>
                    <p><b>Reti Rilevanti Mancanti:</b> SSID previsti non visti in un punto.</p>
                    <p><b>Dati Radi:</b> evidenza ripetuta troppo limitata.</p>
                    <p><b>Dettagli Scanner Mancanti:</b> dati da scanner fallback o ampiezza/frequenza mancanti possono indebolire conclusioni su Interferenza e 6 GHz.</p>
                    <p><b>Bassa Confidenza / Segnale Instabile:</b> scan ripetuti deboli o incoerenti.</p>
                </td>
                <td class="survey-gap"></td>
                <td class="survey-card">
                    <div class="survey-card-title">Modello AP</div>
                    <p><b>Finding AP Dominante:</b> osservazioni roaming o posizione AP da controllare.</p>
                    <p><b>AP Senza Posizione:</b> gruppi AP rilevanti senza coordinate mappa.</p>
                    <p><b>Warning Config AP:</b> mismatch metadata/deployment.</p>
                    <p><b>Memoria Applicata / Cambi Canale:</b> dati AP o ipotesi canale ancora da rivedere.</p>
                </td>
            </tr>
        </table>
        <h2>Cosa Sistemare Prima</h2>
        <div class="gate-list">
            <div class="gate-row"><b>1. Sistema prima l'evidenza dei punti:</b> reti rilevanti mancanti, dati radi, dettagli scanner limitati, bassa confidenza e segnale instabile possono falsare ogni mappa. Vai al punto e riscansiona prima di ragionare sugli AP.</div>
            <div class="gate-row"><b>2. Sistema poi identità e posizione AP:</b> finding AP Dominante e AP senza posizione di solito indicano che il modello AP va rivisto prima di fidarsi di roaming o diagnostica posizione.</div>
            <div class="gate-row"><b>3. Rivedi metadata AP e canali:</b> warning config AP e cambi canale influenzano Canali AP e Interferenza. Apri Metadati AP quando canali attesi, osservati o override canale analisi vanno controllati.</div>
            <div class="gate-row"><b>4. Conferma i dati AP da memoria:</b> Da Memoria non è un errore. Significa che alias, ruoli, metadata, override o posizioni compatibili sono stati riusati e vanno confermati o modificati.</div>
        </div>
        <h2>Finestra Dettagli</h2>
        <p>Usa le KPI punto per aprire liste filtrate dei punti di misura. Usa <b>Dettagli</b> quando una card raccomandazione mostra gruppi AP, cambi canale o contesto diagnostico lungo. Le righe dettaglio sono pensate per survey grandi: ogni punto, gruppo AP o cambio canale coinvolto ha la sua riga, e i pulsanti aprono la mappa o l'editor corretto senza caricare tutto nella dashboard principale.</p>
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Scalabile Per Scelta</span><br>La dashboard principale mostra conteggi e priorità. Le finestre dettaglio contengono le liste lunghe, così molti gruppi AP o molti punti problematici restano leggibili.</td></tr></table>
        <h2>Revisione Memoria AP</h2>
        <p>Quando un nuovo rilievo vede BSSID già noti, il programma può riusare alias, ruoli, metadata, override canale analisi e posizioni mappa compatibili. Qualità Rilievo mantiene questa cosa visibile come finding del modello AP finché i dati non vengono confermati o modificati da Gruppi AP.</p>
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Importante</span><br>Un warning di setup non significa che il punto sia sbagliato. Significa che modello AP, canale atteso o deployment reale vanno controllati.</td></tr></table>
    """,
    "help_ap_groups_nav": "Gruppi AP",
    "help_ap_groups_title": "Gruppi AP, Ruoli E Metadati",
    "help_ap_groups_subtitle": "AP Group Manager trasforma BSSID grezzi in un modello di AP fisico che le mappe possono interpretare.",
    "help_ap_groups_body": """
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Regola Base</span><br>Il programma può suggerire gruppi AP, ma il modello finale deve descrivere il deployment fisico reale. Considera il raggruppamento automatico come evidenza, non come verità finale.</td></tr></table>
        <h2>Come Ragiona AP Group Manager</h2>
        <table class="survey-grid">
            <tr>
                <td class="survey-card"><b>Evidenza In Ingresso</b><br>BSSID, SSID, bande, canali, storico segnale e metadata dello scanner descrivono cosa è stato osservato.</td>
                <td class="survey-gap"></td>
                <td class="survey-card"><b>Modello Utente</b><br>Alias, ruolo, posizione, metadata e override canale descrivono cosa dovrebbe essere il deployment.</td>
                <td class="survey-gap"></td>
                <td class="survey-card"><b>Output</b><br>Controlli qualità, mappe live e report PDF usano questo modello per decidere cosa mostrare, ignorare o segnalare.</td>
            </tr>
        </table>
        <h2>Livelli Del Manager</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>Trova Righe</b><br>Ricerca più filtri Stato, Ruolo, Banda e Gestione riducono liste AP grandi a righe warning, un ruolo, una banda, gruppi manuali/auto, Da Memoria o candidati Aggiornamento Memoria.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Evidenza Tabella</b><br>Stato, gruppo, alias, ruolo, posizione, metadata, BSSID, SSID, canali e gestione mostrano il modello AP fisico corrente.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Menu Memoria E Alias</b><br>Memoria raggruppa Conferma Selezionato, Conferma Tutti Da Memoria e Aggiorna Selezionato Da Memoria. Alias raggruppa Imposta/Modifica ed Elimina, con conferma dove serve.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Editor Principali</b><br>Gestione BSSID, Imposta Ruolo, Metadati e Posiziona Su Mappa correggono il modello usato da mappe e controlli qualità.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Diagnostica</b><br>Dettagli Warning spiega i conflitti. Reset Auto chiede conferma e ricostruisce il raggruppamento automatico.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Salva / Annulla / X Finestra</b><br>Salva scrive metadata survey e aggiorna Memoria AP. Annulla e X scartano le modifiche pendenti del dialog.</td>
            </tr>
        </table>
        <h2>Cosa Controllare</h2>
        <table class="gate-list">
            <tr><td class="gate-row"><b>1. Appartenenza Gruppo</b><br>SSID guest/main e radio multiple dello stesso AP fisico dovrebbero stare nello stesso gruppo AP. Separa o sposta BSSID quando il suggerimento automatico è sbagliato.</td></tr>
            <tr><td class="gate-row"><b>2. Alias E Ruolo</b><br>Usa nomi fisici leggibili per legende, tooltip e schede PDF. Marca AP temporanei come Test/nascosto, vicini come Esterno e dispositivi solo interferenti come Interferente.</td></tr>
            <tr><td class="gate-row"><b>3. Posizione</b><br>La diagnostica AP Dominante richiede coordinate fisiche degli AP. Usa Imposta Posizione e clicca sulla pianta per gli AP importanti per il rilievo.</td></tr>
            <tr><td class="gate-row"><b>4. Metadata E Modello Canale</b><br>Bande/canali attesi rendono significativi i warning setup. Gli override canale sono scelte di modellazione per mappe sensibili al canale, non etichette estetiche.</td></tr>
            <tr><td class="gate-row"><b>5. Stato Memoria</b><br>Le righe Da Memoria o Aggiornamento Memoria vanno riviste, così i dati AP riusati non diventano ipotesi silenziose.</td></tr>
        </table>
        <h2>BSSID Manager</h2>
        <p>Gestione BSSID serve a correggere appartenenza dei BSSID senza ricostruire tutto manualmente. Usa il filtro Mostra per vedere tutti i BSSID, solo il gruppo corrente, altri gruppi, non assegnati, selezionati o BSSID con warning. I filtri banda, canale e ricerca isolano una radio o un canale problematico.</p>
        <table class="survey-grid">
            <tr>
                <td class="survey-card"><b>Filtra L'Evidenza</b><br>Scope, banda, canale e ricerca isolano una radio, un canale problematico o un set di BSSID non assegnati.</td>
                <td class="survey-gap"></td>
                <td class="survey-card"><b>Seleziona In Blocco</b><br>Seleziona Visibili, Deseleziona Visibili e Inverti Visibili operano solo sulle righe attualmente filtrate.</td>
                <td class="survey-gap"></td>
                <td class="survey-card"><b>Sposta O Separa</b><br>Nuovo Gruppo crea un gruppo AP manuale. Sposta Righe sposta i BSSID selezionati nel gruppo AP scelto.</td>
            </tr>
        </table>
        <h2>Ruoli</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>Interno</b><br>AP normale usato per copertura, AP dominante e interferenza.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Esterno</b><br>AP vicino o esterno. Utile come contesto, ma non parte del modello interno pianificato.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Interferente</b><br>AP che vuoi soprattutto tracciare come sorgente di interferenza.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Test/nascosto</b><br>Escluso dall'analisi utente per non far distorcere mappe da AP temporanei o nascosti.</td>
            </tr>
        </table>
        <h2>Metadata E Override Canale</h2>
        <p>Bande/canali attesi sono regole di validazione. L'override del canale di analisi è diverso: è una scelta esplicita di modellazione usata dalle mappe sensibili al canale quando il rilievo ha osservato un cambio canale pulito o ambiguo.</p>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>Campi Di Documentazione</b><br>Vendor, modello, montaggio e note sono contesto di revisione. Il montaggio non è ancora usato come formula RF.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Campi Di Validazione</b><br>Bande attese e canali attesi rilevano AP osservati su bande o canali non previsti, incluso 6 GHz quando esiste evidenza di frequenza.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Override Canale Analisi</b><br>Forza le mappe sensibili al canale a usare il canale osservato selezionato per quel gruppo AP e banda.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Regola Del Selettore</b><br>Il selettore elenca solo i canali realmente osservati per quel gruppo AP/banda. Se una banda non è stata osservata, l'override è disattivato e mostra Non Rilevata.</td>
            </tr>
        </table>
        <h2>Cambi Canale Puliti</h2>
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Comportamento Mappa Di Default</span><br>Se lo stesso gruppo AP/set BSSID passa pulitamente da un canale a un altro durante il rilievo, AP Group non lo tratta come conflitto BSSID. Interferenza e Canali AP usano di default il canale più recente.</td></tr></table>
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Quando Usare Override</span><br>Usa override solo quando sai che il canale operativo previsto è diverso dallo stato osservato nel rilievo, per esempio dopo riavvii schedulati degli AP.</td></tr></table>
        <h2>Memoria AP</h2>
        <p>Memoria AP è automatica. Il programma salva i dati revisionati dei Gruppi AP in un file persistente e li applica ai rilievi successivi dopo il normale raggruppamento BSSID quando rivede BSSID già noti.</p>
        <table class="survey-grid">
            <tr>
                <td class="survey-card"><b>Da Memoria</b><br>Alias, ruolo, metadata, override o posizione mappa compatibile sono stati applicati da Memoria AP. Rivedi la riga, poi usa Memoria &gt; Conferma Selezionato o Conferma Tutti Da Memoria.</td>
                <td class="survey-gap"></td>
                <td class="survey-card"><b>Memoria Da Aggiornare</b><br>I dati AP manuali correnti sono diversi dai dati più recenti salvati in Memoria AP. Usa Memoria &gt; Aggiorna Selezionato Da Memoria quando il dato salvato è più corretto.</td>
                <td class="survey-gap"></td>
                <td class="survey-card"><b>Salvata</b><br>Il file Memoria AP contiene record AP riusabili. Il footer mostra lo stato memoria; Impostazioni può aprire la cartella o svuotare la memoria con conferma.</td>
            </tr>
        </table>
        <p>Premere <b>Salva</b> in AP Group Manager scrive il modello AP e aggiorna Memoria AP. Chiudere AP Group Manager con la X della finestra equivale ad Annulla e non salva le modifiche AP Group in sospeso.</p>
    """,
    "help_live_maps_nav": "Mappe Live",
    "help_live_maps_title": "Mappe Live E Opzioni",
    "help_live_maps_subtitle": "Mappa Live è la superficie principale di revisione dopo controlli qualità e modello AP.",
    "help_live_maps_body": """
        <h2>Toolbar Superiore</h2>
        <table class="survey-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="survey-card"><b>Tipo Mappa</b><br>Seleziona Copertura Segnale, Interferenza AP, Canali AP o AP Dominante.</td>
                <td class="survey-gap"></td>
                <td class="survey-card"><b>SSID</b><br>Sceglie la rete da analizzare fra gli SSID presenti nel rilievo.</td>
                <td class="survey-gap"></td>
                <td class="survey-card"><b>Esporta PDF</b><br>Esporta il tipo mappa live e le opzioni correnti. Il rilievo viene salvato prima se necessario.</td>
            </tr>
        </table>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>Aggiorna Ora</b><br>Renderizza la mappa corrente con le opzioni selezionate.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Aggiornamento Auto</b><br>Rirenderizza automaticamente dopo cambi opzione quando il rilievo può essere renderizzato.</td>
            </tr>
        </table>
        <h2>Scegli La Mappa In Base Alla Domanda</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>Copertura Segnale</b><br>Livello segnale continuo per SSID e banda.<br><span class="survey-card-use">Lettura:</span> usa scala colori e distanza max per non sovrainterpretare zone lontane dai punti reali.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Interferenza AP</b><br>Rischio di sovrapposizione canale fra AP servente e AP vicini.<br><span class="survey-card-use">Lettura:</span> controlla ruoli AP e override canale prima di fidarti dello score.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Canali AP</b><br>Colori discreti dei punti in base al canale servente.<br><span class="survey-card-use">Lettura:</span> usala per verificare piano canali e gestione dei cambi canale.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>AP Dominante</b><br>Quale gruppo AP è più forte in ogni punto.<br><span class="survey-card-use">Lettura:</span> i marker issue indicano ambiguità roaming o incoerenza con posizione AP.</td>
            </tr>
        </table>
        <h2>Pannello Opzioni</h2>
        <p>Il tab verticale Opzioni apre l'overlay a sinistra. Il programma mostra solo i controlli utili per il tipo mappa corrente e ricorda le opzioni separatamente per ogni tipo mappa.</p>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>Copertura Segnale</b><br><span class="survey-card-use">Opzioni Visibili:</span> Banda, Aggregazione, Scala Colori, Interpolazione, Distanza Max, Smoothing, Filtro Gruppo AP, Solo &gt;= -70 dBm.<br>Filtro Gruppo AP appare solo quando esistono gruppi AP non-test compatibili con SSID/banda selezionati.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Interferenza AP</b><br><span class="survey-card-use">Opzioni Visibili:</span> Banda, Scala Colori, Modalità Interferenza, Interpolazione, Distanza Max, Smoothing.<br>Interferenza non offre Tutte Le Bande; parte da 2.4 GHz di default.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Canali AP</b><br><span class="survey-card-use">Opzioni Visibili:</span> Banda, Label Punti, Filtro Gruppo AP.<br>Mappa discreta a punti; niente interpolazione o smoothing.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>AP Dominante</b><br><span class="survey-card-use">Opzioni Visibili:</span> Banda, Label Punti.<br>Mappa discreta a punti; i warning posizione AP usano il modello fisico AP.</td>
            </tr>
        </table>
        <h2>Significato Opzioni</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>Banda</b><br>Limita l'analisi a 2.4, 5, 6 GHz o tutte le bande dove supportato.<br><span class="survey-card-use">Usala Con Attenzione:</span> righe senza banda/frequenza esplicita possono rendere ambigui canali bassi.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Aggregazione</b><br>Copertura Segnale può usare Migliore, Mediana o Media quando più righe contribuiscono a un punto.<br><span class="survey-card-use">Usala Con Attenzione:</span> Migliore è ottimistica; Mediana è di solito più stabile con evidenza ripetuta.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Scala Colori</b><br>Fissa mantiene colori confrontabili; Automatica adatta la scala ai dati della mappa corrente.<br><span class="survey-card-use">Usala Con Attenzione:</span> usa Fissa quando confronti più report.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Interpolazione</b><br>Smooth RBF o Lineare per stimare fra punti reali nelle mappe continue.<br><span class="survey-card-use">Usala Con Attenzione:</span> aree grandi senza punti non vanno sovrainterpretate.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Smoothing</b><br>Rende copertura/interferenza visivamente più calme.<br><span class="survey-card-use">Usala Con Attenzione:</span> smoothing alto può nascondere transizioni RF nette.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Distanza Max</b><br>Limita il rendering continuo alle aree vicine ai punti misurati. Usa il sistema di misura selezionato quando la scala è calibrata, pixel altrimenti. Se cambi sistema di misura dopo la calibrazione, la scala viene eliminata e va rifatta.<br><span class="survey-card-use">Usala Con Attenzione:</span> aumentala solo quando la densità punti è buona.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Modalità Interferenza</b><br>Intra-SSID si concentra sull'SSID selezionato; Tutti Gli SSID include altri SSID osservati nel modello di rischio.<br><span class="survey-card-use">Usala Con Attenzione:</span> Tutti Gli SSID può essere utile per contesto vicini, ma può risultare più rumoroso.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Label Punti</b><br>Disponibile per Canali AP e AP Dominante. Auto etichetta cambi canale/AP e inizi roaming; Tutti etichetta ogni punto; Nessuno nasconde le label.<br><span class="survey-card-use">Usala Con Attenzione:</span> usa Tutti per audit attribuzione punti; usa Auto nei report normali.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Filtro Gruppo AP</b><br>Limita/evidenzia Copertura Segnale o Canali AP per un gruppo AP selezionato.<br><span class="survey-card-use">Usala Con Attenzione:</span> ispeziona un AP problematico senza cambiare i dati del rilievo.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Solo &gt;= -70 dBm</b><br>Filtro Copertura Segnale per zone con segnale normalmente utilizzabile.<br><span class="survey-card-use">Usala Con Attenzione:</span> è un filtro di vista, non elimina misure deboli.</td>
            </tr>
        </table>
        <h2>Limiti Di Lettura</h2>
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Regola Lettura Mappa</span><br>Le mappe live aggiornano la visualizzazione, non i dati raccolti. Una mappa pulita può comunque dipendere da densità punti debole, metadata AP non aggiornati o posizioni AP mancanti.</td></tr></table>
        <table class="gate-list">
            <tr><td class="gate-row"><b>1. Controlla Il Percorso Evidenza</b><br>Se una mappa sembra sbagliata, rivedi qualità punto, gruppi AP, ruoli, metadata, calibrazione scala e posizioni AP prima di trattarla come conclusione RF.</td></tr>
            <tr><td class="gate-row"><b>2. Tieni Limitate Le Mappe Continue</b><br>Copertura e Interferenza interpolano fra punti reali. Scala colori, distanza max e smoothing decidono quanta area vuota della pianta viene stimata visivamente.</td></tr>
            <tr><td class="gate-row"><b>3. Usa Le Mappe Discrete Per Attribuire</b><br>Canali AP e AP Dominante sono mappe a punti. Usa label e filtro Gruppo AP quando devi spiegare quale AP/canale serve un punto specifico.</td></tr>
        </table>
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Cambi Canale</span><br>Se lo stesso gruppo AP passa pulitamente da un canale a un altro durante il rilievo, le mappe sensibili al canale usano di default il canale più recente. Se la sequenza è ambigua, le mappe preservano i canali misurati salvo override esplicito.</td></tr></table>
    """,
    "help_reports_nav": "Report PDF",
    "help_reports_title": "Report PDF Live",
    "help_reports_subtitle": "L'export PDF cattura le opzioni della Mappa Live corrente e aggiunge pagine diagnostiche dove il tipo mappa le supporta.",
    "help_reports_body": """
        <h2>Workflow Esportazione</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>Controllo Salvataggio</b><br>L'export PDF richiede un rilievo salvato. Se il rilievo è modificato o non ha percorso CSV, l'app chiede/salva prima.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>File Di Output</b><br>Il dialog di salvataggio propone un nome PDF basato su survey, tipo mappa, banda e timestamp. Se manca il suffisso, viene aggiunto `.pdf`.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Intera Estensione Mappa</b><br>Il PDF usa tutta l'estensione della pianta, non zoom/pan live correnti.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Opzioni Attive</b><br>SSID, banda, tipo mappa, scala colori, label, filtro Gruppo AP e opzioni specifiche arrivano dallo stato Mappa Live.</td>
            </tr>
        </table>
        <h2>Pagina Mappa</h2>
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Cosa Rappresenta La Prima Pagina</span><br>La prima pagina è la mappa live renderizzata sull'intera pianta. Legende, scale colori, marker AP, label punti e focus Gruppo AP seguono le opzioni attive della Mappa Live.</td></tr></table>
        <h2>Report Per Tipo Mappa</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>Copertura</b><br><span class="survey-card-use">Pagine:</span> solo pagina mappa.<br>Nessuna pagina problemi per scelta. Usa Qualità Rilievo per problemi qualità dati e setup AP.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Canali AP</b><br><span class="survey-card-use">Pagine:</span> solo pagina mappa.<br>Utile per revisione piano canali. Schede diagnostiche non aggiunte finché non esiste una regola chiara.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>AP Dominante</b><br><span class="survey-card-use">Pagine:</span> mappa più pagina/e diagnostiche.<br>Le schede spiegano ambiguità roaming, contesto AP dominante/secondario e coerenza AP dominante/AP fisico più vicino.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Interferenza</b><br><span class="survey-card-use">Pagine:</span> mappa più pagina/e diagnostiche.<br>Le schede mostrano AP/canale servente, interferente principale/canale, overlap, contesto ampiezza canale e rischio.</td>
            </tr>
        </table>
        <h2>Schede Problema</h2>
        <table class="survey-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="survey-card"><b>Callout Mappa</b><br>I callout quadrati numerati sulla mappa corrispondono alle schede numerate, così puoi attribuire ogni punto a una diagnosi specifica.</td>
                <td class="survey-gap"></td>
                <td class="survey-card"><b>Schede Interferenza</b><br>I punti a rischio alto sono paginati in schede compatte. Il report mantiene la lista limitata per restare leggibile anche su survey grandi.</td>
                <td class="survey-gap"></td>
                <td class="survey-card"><b>Schede AP Dominante</b><br>Roaming overlap e finding posizione AP sono paginati con contesto AP dominante, secondario o AP fisico più vicino.</td>
            </tr>
        </table>
        <h2>Prima Di Inviare Un Report</h2>
        <table class="gate-list">
            <tr><td class="gate-row"><b>1. Conferma Lo Scope</b><br>Controlla che SSID, banda e tipo mappa selezionati siano quelli da documentare.</td></tr>
            <tr><td class="gate-row"><b>2. Conferma Il Modello AP</b><br>Rivedi gruppi AP, ruoli, alias e posizioni AP prima di esportare report AP Dominante o Interferenza.</td></tr>
            <tr><td class="gate-row"><b>3. Conferma Il Modello Canale</b><br>Rivedi note cambio canale pulito e override canale analisi prima di esportare Interferenza o Canali AP.</td></tr>
            <tr><td class="gate-row"><b>4. Leggi Le Schede Come Diagnostica</b><br>Una scheda warning può descrivere un problema reale del deployment, non un errore software.</td></tr>
        </table>
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Copertura Non Ha Pagina Problemi Per Scelta</span><br>È una visualizzazione del segnale. Problemi qualità o setup AP si rivedono in Qualità Rilievo e AP Group Manager.</td></tr></table>
        <h2>Comportamento Attuale Canali AP</h2>
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Comportamento Attuale Canali AP</span><br>L'export Canali AP è solo mappa finché non esiste una regola diagnostica chiara che meriti schede report. Usa Qualità Rilievo e warning metadata AP per problemi di piano canali.</td></tr></table>
    """,
    "help_diagnostics_nav": "Warning",
    "help_diagnostics_title": "Warning E Diagnostica",
    "help_diagnostics_subtitle": "I warning sono inviti a controllare ipotesi, non prova automatica che un punto sia sbagliato.",
    "help_diagnostics_body": """
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Regola Revisione Warning</span><br>Un warning indica quale ipotesi va rivista. Prima distingui se il problema è evidenza del punto, identità/posizione AP, metadata AP, comportamento canale o normale comportamento RF.</td></tr></table>
        <h2>Categorie Warning</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>Finding Rescan Punto</b><br>SSID rilevanti mancanti, dati radi, bassa confidenza o segnale instabile indicano che l'evidenza del punto può essere debole.<br><span class="survey-card-use">Controlla:</span> focalizza il punto, ispeziona l'evidenza raw e rifai la scansione quando serve.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>AP Dominante Inatteso</b><br>L'AP più forte non è coerente con posizione fisica o AP più vicino.<br><span class="survey-card-use">Controlla:</span> posizioni AP, alias, calibrazione scala e roaming reale.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Ambiguità Roaming</b><br>AP più forte e secondo AP sono vicini in dB.<br><span class="survey-card-use">Controlla:</span> aspettati roaming client poco prevedibile in quella zona; non trattarlo automaticamente come dato survey sbagliato.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Canale O Banda Inattesi</b><br>Il canale o la banda osservata non coincide con i metadata AP.<br><span class="survey-card-use">Controlla:</span> configurazione controller, canali/bande attesi, evidenza banda/frequenza dello scanner e override canale.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Cambio Canale Pulito O Ambiguo</b><br>Lo stesso AP ha cambiato canale durante il rilievo. I cambi puliti usano il canale più recente; quelli ambigui mantengono i canali misurati salvo override.<br><span class="survey-card-use">Controlla:</span> metadata AP prima di fidarti di Canali AP o Interferenza.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Posizione AP Mancante</b><br>Un gruppo AP rilevante non ha marker fisico.<br><span class="survey-card-use">Controlla:</span> posiziona l'AP per abilitare la diagnostica Dominant AP basata sulle distanze.</td>
            </tr>
        </table>
        <h2>Pattern Di Troubleshooting</h2>
        <table class="gate-list">
            <tr><td class="gate-row"><b>Copertura Troppo Ottimistica Lontano Dai Punti</b><br>Causa probabile: l'interpolazione sta riempiendo spazio non misurato. Azione successiva: abbassa distanza max o raccogli più punti prima di fidarti di quell'area.</td></tr>
            <tr><td class="gate-row"><b>Interferenza Appare Su Un Vecchio Canale</b><br>Causa probabile: AP cambiato canale durante il rilievo, sequenza ambigua o override mancante/errato. Azione successiva: controlla dettaglio cambio canale e override metadata AP.</td></tr>
            <tr><td class="gate-row"><b>AP Dominante Lontano Dal Suo Marker Fisico</b><br>Causa probabile: posizione AP sbagliata, gruppo AP errato, roaming client o propagazione RF reale. Azione successiva: apri dettaglio AP Dominante, verifica AP più vicino e alias gruppi.</td></tr>
            <tr><td class="gate-row"><b>Molti Punti Richiedono Rescan</b><br>Causa probabile: SSID rilevanti mancanti, segnale instabile o dati radi. Azione successiva: focalizza i punti coinvolti e rifai scansione prima di interpretare mappe.</td></tr>
            <tr><td class="gate-row"><b>Canali Inattesi Su Un AP</b><br>Causa probabile: metadata vecchio, configurazione AP cambiata o evidenza banda/canale ambigua. Azione successiva: controlla metadata AP, configurazione reale controller e dati banda/frequenza dello scanner.</td></tr>
        </table>
        <h2>Ordine Di Revisione</h2>
        <table class="gate-list">
            <tr><td class="gate-row"><b>1. Sistema Prima L'Evidenza Dei Punti</b><br>Reti mancanti, scansioni rade, bassa confidenza e segnale instabile possono influenzare ogni mappa. Rifai scansioni o aggiungi punti vicini prima di interpretare il comportamento RF.</td></tr>
            <tr><td class="gate-row"><b>2. Sistema Identità E Posizione AP</b><br>Gruppi AP, alias, ruolo e posizione influenzano AP Dominante, Interferenza, Canali AP e diagnostica PDF.</td></tr>
            <tr><td class="gate-row"><b>3. Sistema Metadata E Modello Canale</b><br>Canali/bande attesi e override canale analisi decidono se i warning setup sono problemi reali o comportamento previsto.</td></tr>
            <tr><td class="gate-row"><b>4. Interpreta Le Mappe Per Ultime</b><br>Leggi copertura, canali, roaming e interferenza solo dopo che evidenza e modello AP sono abbastanza coerenti.</td></tr>
        </table>
        <table class="callout-table"><tr><td class="callout-accent-danger"></td><td class="callout-content"><span class="callout-label">Non Silenziare I Warning Alla Cieca</span><br>Un warning che riflette comportamento reale del deployment è evidenza utile e dovrebbe restare visibile finché non lo capisci.</td></tr></table>
    """,
    "help_glossary_nav": "Glossario",
    "help_glossary_title": "Glossario",
    "help_glossary_subtitle": "Termini usati dal workflow V2 e dai report.",
    "help_glossary_body": """
        <table class="callout-table" width="100%" cellspacing="0" cellpadding="0"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Come Usare Questa Pagina</span><br>È un riferimento rapido per termini che nel programma hanno un significato specifico. Le pagine operative spiegano le azioni; questa pagina stabilizza il vocabolario.</td></tr></table>
        <h2>Evidenza Wi-Fi</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>SSID</b><br>Il nome della rete Wi-Fi. Uno stesso SSID può essere trasmesso da molti BSSID.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>BSSID</b><br>Il MAC radio visto dalle scansioni Wi-Fi.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>SSID Rilevante</b><br>Una rete selezionata come importante per controlli qualità, mappe live e report.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Sidecar Raw</b><br>Il file <code>.scan</code> collegato che contiene i campioni grezzi delle scansioni ripetute.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Confidenza</b><br>Quanto è affidabile una riga aggregata, in base alle scansioni ripetute.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Finding Rescan Punto</b><br>Problema qualità che suggerisce di rifare la scansione del punto di misura.</td>
            </tr>
        </table>
        <h2>Modello AP</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>Gruppo AP</b><br>Il modello del programma per un AP fisico, di solito con più BSSID.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>AP Dominante</b><br>Il gruppo AP con segnale osservato più forte in un punto di misura.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Ambiguità Roaming</b><br>Un punto dove AP più forte e secondo AP sono abbastanza vicini da poter essere scelti entrambi dai client.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Override Canale Analisi</b><br>Canale osservato scelto dall'utente per mappe sensibili al canale su uno specifico gruppo AP e banda.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Cambio Canale Pulito</b><br>Un gruppo AP che cambia canale nel tempo senza evidenza di conflitti BSSID misti.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Cambio Canale Ambiguo</b><br>Sequenza canale in cui il programma non può trattare con certezza il cambio come transizione pulita.</td>
            </tr>
        </table>
        <h2>Qualità E Warning</h2>
        <table class="survey-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="survey-card"><b>Warning Setup</b><br>Problema di modello o deployment che non richiede necessariamente di rifare il punto.</td>
                <td class="survey-gap"></td>
                <td class="survey-card"><b>Canale O Banda Inattesi</b><br>Evidenza Wi-Fi osservata che non corrisponde ai metadata AP attesi.</td>
                <td class="survey-gap"></td>
                <td class="survey-card"><b>Posizione AP Mancante</b><br>Un gruppo AP rilevante non ha coordinate fisiche sulla mappa, quindi i controlli distanza AP dominante sono più deboli.</td>
            </tr>
        </table>
        <h2>Memoria E Persistenza</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>Memoria AP</b><br>File persistente in cui vengono salvati alias, ruoli, metadata, override canale analisi e posizioni compatibili per rilievi futuri.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Da Memoria</b><br>Stato Gruppo AP che indica dati applicati da Memoria AP e ancora da confermare o modificare.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Aggiornamento Memoria</b><br>Stato Gruppo AP che indica dati salvati in Memoria AP diversi dai dati manuali correnti.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Memoria Opzioni Mappa</b><br>Mappa Live ricorda i valori delle opzioni separatamente per ogni tipo mappa durante la sessione corrente.</td>
            </tr>
        </table>
        <h2>Mappe Live E Report</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td class="workflow-card"><b>Interpolazione</b><br>Stima visuale fra punti misurati. Aiuta la leggibilità ma non sostituisce misure reali.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Distanza Max</b><br>Limite di rendering che evita alle mappe continue di estendersi troppo lontano dall'evidenza misurata.</td>
            </tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr>
                <td class="workflow-card"><b>Scheda Diagnostica</b><br>Scheda del report PDF che spiega punto, gruppo AP, canale o warning coinvolto.</td>
                <td class="workflow-gap"></td>
                <td class="workflow-card"><b>Callout Mappa</b><br>Marker numerato sulla mappa PDF che collega una posizione visibile alla relativa scheda dettaglio.</td>
            </tr>
        </table>
    """,
    "help_commands": "Comandi",
    "help_workflow": "Flusso",
    "help_workflow_title": "Come Usare il Programma",
    "help_workflow_steps": (
        "1-a. Crea un nuovo rilievo e carica la pianta dell'ambiente.\n"
        "1-b. Oppure apri un rilievo già salvato: la pianta verrà caricata automaticamente.\n"
        "2. Spostati fisicamente nell'area e usa il tasto destro sulla mappa per registrare i punti di misura.\n"
        "3. Usa Gruppi AP per assegnare alias, correggere i gruppi e, se conosci la posizione fisica degli AP, posizionarli sulla mappa.\n"
        "4. Salva il rilievo dopo aver raccolto abbastanza punti.\n"
        "5. Apri la Mappa live e scegli SSID, banda Wi-Fi e tipo analisi.\n"
        "6. Usa Copertura segnale per valutare il livello dBm, Interferenza AP per trovare sovrapposizioni, Canali AP per controllare i canali e AP dominante per analizzare il roaming."
    ),
    "help_live": "Mappa live",
    "help_live_title": "Come Usare la Mappa Live",
    "help_live_steps": (
        "La Mappa live mostra una preview del rilievo e può esportare il PDF della vista corrente.\n"
        "Scegli SSID, banda e tipo mappa direttamente nel tab Mappa live.\n"
        "Copertura segnale e Interferenza AP vengono calcolate in background, quindi la GUI resta utilizzabile durante l'aggiornamento.\n"
        "Canali AP e AP dominante mostrano i punti reali con legenda dedicata.\n"
        "In AP dominante, un triangolo giallo indica un possibile warning di posizione AP: il tooltip mostra distanza dall'AP dominante e AP fisico più vicino.\n"
        "Se sei nel tab Rilievo, la live view viene aggiornata quando entri nel tab Mappa live o premi Aggiorna ora.\n"
        "Lo zoom della live view non rigenera la mappa: ridimensiona la preview e rifinisce la qualità dopo una breve pausa."
    ),
    "help_heatmap": "Heatmap",
    "help_heatmap_title": "Come Leggere e Generare la Heatmap",
    "help_heatmap_steps": (
        "Copertura segnale genera una heatmap continua del livello dBm per SSID e banda.\n"
        "RBF morbida crea una visualizzazione più continua; Lineare è più conservativa.\n"
        "Distanza max limita la heatmap alle aree vicine ai punti reali e riduce forme inventate.\n"
        "Solo >= -70 dBm evidenzia le zone normalmente utilizzabili.\n"
        "Interferenza AP calcola il rischio in percentuale e aggiunge al PDF un report dei problemi principali.\n"
        "Canali AP non interpola: mostra i punti reali colorati per canale, con etichette tipo CH 36 / 80 quando la larghezza canale è disponibile.\n"
        "AP dominante mostra quale AP è più forte in ogni punto e marca in giallo le zone dove il secondo AP è entro 5 dB.\n"
        "Se hai posizionato fisicamente gli AP, AP dominante aggiunge triangoli di warning quando il segnale non è coerente con la posizione attesa e aggiunge i problemi al PDF."
    ),
    "help_scan": "Scansione",
    "help_scan_title": "Come Gestire la Scansione Wi-Fi",
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
        "Clic sinistro su un marker: seleziona il punto.\n"
        "Rotella: scorrimento verticale.\n"
        "Shift + rotella: scorrimento orizzontale.\n"
        "Ctrl + rotella: zoom."
    ),
    "keep_scan": "Mantieni Scansione",
    "retry_scan": "Riprova",
    "cancel_point": "Annulla Punto",
}
