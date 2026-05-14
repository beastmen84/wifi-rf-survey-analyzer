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
    "quality_dashboard_metric_rescan": "Da Ripetere",
    "quality_dashboard_metric_missing": "Reti Rilevanti Mancanti",
    "quality_dashboard_metric_sparse": "Dati Scarsi",
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
    "quality_dashboard_fix_ready_detail": "I controlli principali sono puliti. Genera le mappe o usa il filtro problemi per un ultimo passaggio.",
    "quality_dashboard_context_scope": "Ambito Rilievo: Rilevanti {networks} | Posizioni AP {positions} | AP Test {test_aps}",
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
    "quality_dashboard_more_issues": "+{count} altri",
    "quality_dashboard_show_issues_only": "Mostra Solo Punti Con Finding",
    "quality_dashboard_visible_count": "{shown}/{total} punti mostrati",
    "quality_dashboard_quality": "Qualità",
    "quality_dashboard_scan_quality": "Qualità Scansione",
    "quality_dashboard_confidence": "Confidenza",
    "quality_dashboard_issue": "Problema",
    "quality_dashboard_relevant_ssids": "SSID rilevanti",
    "quality_dashboard_no_issue": "Nessun problema rilevato",
    "quality_dashboard_ap_position_issue": "Posizione AP: {ap} - {warning}",
    "quality_dashboard_missing_positions_none": "nessuno",
    "quality_dashboard_missing_positions_more": "{names}, +{count}",
    "calibrate_scale": "Calibra Scala",
    "calibrate_scale_title": "Calibrazione Scala",
    "calibrate_scale_start": "Clicca col sinistro il primo punto della distanza reale nota.",
    "calibrate_scale_second_point": "Clicca col sinistro il secondo punto della distanza nota.",
    "calibrate_scale_distance_prompt": "Distanza reale tra i due punti (metri):",
    "calibrate_scale_saved": "Scala calibrata: {px_per_meter:.2f} px/m.",
    "calibrate_scale_invalid": "Distanza non valida.",
    "calibrate_scale_cancelled": "Calibrazione scala annullata.",
    "calibrate_scale_already_set": "Scala già calibrata. Elimina la scala attuale per rifarla.",
    "delete_scale": "Elimina Scala",
    "delete_scale_title": "Elimina Scala",
    "delete_scale_confirm": "Vuoi eliminare la calibrazione della scala salvata per questo rilievo?",
    "delete_scale_done": "Scala eliminata. Puoi eseguire una nuova calibrazione.",
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
                    <p>Crea o apri il rilievo, carica la pianta, calibra la scala e scegli gli SSID rilevanti.</p>
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
            <div class="gate-row"><b>Distanze:</b> calibra la scala prima di interpretare warning sulle posizioni AP.</div>
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
        <div class="callout"><b>Nota:</b> quando la modalità di posizionamento AP è attiva, il clic sinistro sulla pianta assegna la posizione fisica dell'AP invece di selezionare un punto.</div>
        <h2>Il contesto conta</h2>
        <p>Lo stesso gesto può avere significato diverso in base alla modalità attiva. Nel rilievo normale il tasto destro crea punti e il sinistro seleziona marker. In posizionamento AP o calibrazione scala, il sinistro viene catturato da quella modalità temporanea.</p>
        <table>
            <tr><th>Contesto</th><th>Comportamento clic sinistro</th><th>Cosa controllare</th></tr>
            <tr><td>Mappa Survey normale</td><td>Seleziona un marker punto o pulisce la selezione se clicchi lo sfondo.</td><td>Per creare un punto usa il tasto destro.</td></tr>
            <tr><td>Calibrazione scala</td><td>Sceglie gli estremi della calibrazione.</td><td>Completa i due punti di calibrazione prima di continuare.</td></tr>
            <tr><td>Posizionamento AP</td><td>Salva il marker fisico del gruppo AP selezionato.</td><td>La posizione AP influisce sulla diagnostica AP Dominante.</td></tr>
            <tr><td>Mappa Live</td><td>Trascina quando la mappa è più grande della viewport; il click sullo sfondo può pulire selezioni legenda.</td><td>Zoom/pan non cambiano i dati raccolti.</td></tr>
        </table>
    """,
    "help_control_right_click_title": "Tasto Destro",
    "help_control_right_click_text": "Crea un punto di misura sulla mappa del rilievo.",
    "help_control_left_click_title": "Tasto Sinistro / Trascina",
    "help_control_left_click_text": "Seleziona un punto di misura, trascina la mappa quando il pan è disponibile, oppure posiziona un AP quando la modalità AP è attiva.",
    "help_control_scroll_title": "Rotella",
    "help_control_scroll_text": "Scorre liste e pannelli. Usa Ctrl + rotella per lo zoom sulla mappa.",
    "help_control_shift_title": "Shift",
    "help_control_shift_text": "Usa Shift con la rotella per lo scorrimento orizzontale in tabelle o viste larghe.",
    "help_control_ctrl_title": "Ctrl",
    "help_control_ctrl_text": "Usa Ctrl con la rotella per lo zoom sulla pianta.",
    "help_control_wifi_title": "Marker Wi-Fi",
    "help_control_wifi_text": "Le posizioni fisiche degli AP usano il marker Wi-Fi nelle mappe live e nei report esportati.",
    "help_survey_nav": "Rilievo E Scansioni",
    "help_survey_title": "Punti, Raw Scan E Confidenza",
    "help_survey_subtitle": "Un punto non è solo un valore di segnale: V2 salva campioni grezzi, li aggrega e misura la confidenza.",
    "help_survey_body": """
        <h2>Cosa viene salvato</h2>
        <p>Ogni punto di misura può contenere più reti osservate. Il CSV principale salva le righe aggregate usate dalle mappe. Il sidecar <code>.scan</code> collegato salva l'evidenza grezza delle scansioni ripetute.</p>
        <h2>Reti rilevanti</h2>
        <p>Gli SSID rilevanti indicano al motore qualità quali reti contano. Una rete rilevante mancante è un finding qualità. Una rete vicina non importante, di solito, no.</p>
        <div class="section-card"><b>Regola pratica:</b> imposta presto gli SSID rilevanti. Se li aggiungi solo dopo aver raccolto punti, la dashboard può rivelare punti da rivedere perché le reti previste non erano state viste.</div>
        <h2>Sidecar raw scan</h2>
        <p>Il sidecar conserva campioni ripetuti, dettagli backend e campi specifici dello scanner quando disponibili. Per questo V2 può spiegare confidenza, segnale instabile e dati radi invece di disegnare solo colori.</p>
        <table>
            <tr><th>Valore salvato</th><th>Perché conta</th></tr>
            <tr><td>Mediana dBm</td><td>Riduce l'effetto di uno spike temporaneo.</td></tr>
            <tr><td>Min/max dBm</td><td>Mostra quanto si è mosso il segnale durante le scansioni ripetute.</td></tr>
            <tr><td>Campioni visti/totali</td><td>Alimenta confidenza e controlli dati radi.</td></tr>
            <tr><td>Banda/frequenza/larghezza canale</td><td>Migliora Canali AP, Interferenza e interpretazione 6 GHz.</td></tr>
        </table>
        <h2>Backend scanner</h2>
        <table>
            <tr><th>Backend</th><th>Uso</th><th>Note</th></tr>
            <tr><td><span class="pill">Auto</span></td><td>Scelta predefinita</td><td>Prova prima <code>lswifi</code>, poi usa <code>netsh</code> come fallback.</td></tr>
            <tr><td><span class="pill">lswifi</span></td><td>Scanner preferito</td><td>Di solito cattura più dettagli su BSSID, banda, frequenza, sicurezza e larghezza canale.</td></tr>
            <tr><td><span class="pill">netsh</span></td><td>Fallback Windows</td><td>Utile quando lswifi non è disponibile, ma in genere espone meno dettagli RF.</td></tr>
        </table>
        <div class="callout warning"><b>Scansioni sospette:</b> se una scansione vede molte meno reti rilevanti, riprova prima di salvare il punto. È quasi sempre più rapido che correggere un punto sporco dopo.</div>
        <h2>Buon posizionamento punti</h2>
        <ul>
            <li>Metti punti dove i client lavorano davvero: scrivanie, sale riunioni, corridoi, porte e zone problematiche note.</li>
            <li>Aggiungi punti vicino alle transizioni AP. AP Dominante e roaming dipendono dall'evidenza in quelle zone.</li>
            <li>Evita scansioni mentre ti muovi. Fermati, lascia completare la scansione, poi passa al punto successivo.</li>
        </ul>
    """,
    "help_quality_nav": "Qualità Rilievo",
    "help_quality_title": "Dashboard Qualità Rilievo",
    "help_quality_subtitle": "La dashboard separa i punti che possono richiedere rescan dalla diagnostica di setup AP.",
    "help_quality_body": """
        <h2>Leggi la dashboard su due livelli</h2>
        <p>Il primo livello è la qualità dei punti: queste misure sono affidabili? Il secondo livello è il setup AP: il modello AP spiega quello che è stato misurato?</p>
        <h2>Cosa sistemare prima</h2>
        <p>La dashboard ordina i problemi in modo operativo. I problemi di punto vengono prima perché dati sporchi possono falsare ogni mappa. I problemi AP vengono dopo perché influenzano l'interpretazione.</p>
        <table>
            <tr><th>Area</th><th>Significato</th><th>Azione tipica</th></tr>
            <tr><td>Reti Rilevanti Mancanti</td><td>Un punto non ha visto una rete che dovrebbe contare.</td><td>Vai al punto e rifai la scansione.</td></tr>
            <tr><td>Bassa Confidenza</td><td>Le scansioni ripetute non hanno prodotto abbastanza evidenza affidabile.</td><td>Rifai il punto o aggiungi punti vicini.</td></tr>
            <tr><td>Segnale Instabile</td><td>Il segnale è variato troppo durante le scansioni ripetute.</td><td>Controlla movimento, cambi RF temporanei o AP instabili.</td></tr>
            <tr><td>Finding AP Dominante</td><td>L'AP più forte non è coerente con il modello fisico.</td><td>Apri la mappa AP Dominante e verifica posizioni AP o roaming reale.</td></tr>
            <tr><td>Warning Config AP</td><td>Bande/canali osservati non coincidono con i metadata.</td><td>Apri metadata AP e decidi se è sbagliato il metadata o il deployment.</td></tr>
            <tr><td>Memoria Applicata</td><td>Dati AP riusati dal file persistente Memoria AP.</td><td>Apri Gruppi AP, verifica i dati riusati e confermali o modificali.</td></tr>
        </table>
        <h2>Significato KPI</h2>
        <table>
            <tr><th>KPI</th><th>Interpretazione</th></tr>
            <tr><td>Punti Totali</td><td>Quanta evidenza spaziale contiene il rilievo.</td></tr>
            <tr><td>Scan OK / Rescan Necessario</td><td>Se i punti di misura sono utilizzabili.</td></tr>
            <tr><td>Dati Radi</td><td>Punti con poca evidenza ripetuta per una confidenza forte.</td></tr>
            <tr><td>Finding AP Dominante</td><td>Osservazioni roaming o posizione AP da rivedere, non automaticamente dati errati.</td></tr>
            <tr><td>Warning Config AP</td><td>Mismatch metadata/deployment, per esempio canali inattesi.</td></tr>
            <tr><td>Memoria Applicata</td><td>Gruppi AP i cui alias, ruoli, metadata o posizione arrivano da Memoria AP e richiedono ancora revisione.</td></tr>
            <tr><td>Cambi Canale</td><td>AP la cui sequenza canale influenza analisi sensibili al canale.</td></tr>
        </table>
        <h2>Finestra dettagli</h2>
        <p>Usa <b>Extra Details</b> quando una card mostra più di un semplice stato OK. Le righe dettaglio rendono gestibili survey grandi: ogni punto o gruppo AP coinvolto ha la sua riga e i pulsanti aprono la mappa o l'editor corretto.</p>
        <h2>Revisione Memoria AP</h2>
        <p>Quando un nuovo rilievo vede BSSID già noti, il programma può riusare alias, ruoli, metadata, override canale analisi e posizioni mappa compatibili. Qualità Rilievo mantiene questa cosa visibile come finding del modello AP finché i dati non vengono confermati o modificati da Gruppi AP.</p>
        <div class="callout"><b>Importante:</b> un warning di setup non significa che il punto sia sbagliato. Significa che modello AP, canale atteso o deployment reale vanno controllati.</div>
    """,
    "help_ap_groups_nav": "Gruppi AP",
    "help_ap_groups_title": "Gruppi AP, Ruoli E Metadata",
    "help_ap_groups_subtitle": "AP Group Manager trasforma BSSID grezzi in un modello di AP fisico che le mappe possono interpretare.",
    "help_ap_groups_body": """
        <h2>I suggerimenti automatici non sono verità finale</h2>
        <p>Il programma raggruppa automaticamente i BSSID, ma deployment reali possono usare più SSID, bande e radio sullo stesso AP fisico. Considera il gruppo automatico come punto di partenza.</p>
        <h2>Cosa controllare</h2>
        <table>
            <tr><th>Area</th><th>Perché conta</th><th>Fix tipico</th></tr>
            <tr><td>Alias</td><td>Nomi leggibili rendono usabili legende, tooltip e PDF.</td><td>Rinomina i gruppi con nomi fisici tipo corridoio, ufficio o stanza.</td></tr>
            <tr><td>Raggruppamento BSSID</td><td>Guest/main SSID sullo stesso AP non dovrebbero interferire fra loro.</td><td>Sposta i BSSID nel gruppo AP corretto o separa gruppi sbagliati.</td></tr>
            <tr><td>Ruolo</td><td>I ruoli decidono cosa includono o ignorano le mappe.</td><td>Marca AP temporanei come Test/nascosto, vicini come Esterno o Interferente.</td></tr>
            <tr><td>Posizione</td><td>La diagnostica AP Dominante richiede coordinate fisiche degli AP.</td><td>Usa Imposta Posizione e clicca sulla pianta.</td></tr>
            <tr><td>Metadata</td><td>Bande/canali attesi rendono significativi i warning setup AP.</td><td>Imposta bande attese, canali attesi e note.</td></tr>
        </table>
        <h2>Ruoli</h2>
        <table>
            <tr><th>Ruolo</th><th>Effetto</th></tr>
            <tr><td>Interno</td><td>AP normale usato per copertura, AP dominante e interferenza.</td></tr>
            <tr><td>Esterno</td><td>AP vicino o esterno. Utile come contesto, ma non parte del modello interno pianificato.</td></tr>
            <tr><td>Interferente</td><td>AP che vuoi soprattutto tracciare come sorgente di interferenza.</td></tr>
            <tr><td>Test/nascosto</td><td>Escluso dall'analisi utente per non far distorcere mappe da AP temporanei o nascosti.</td></tr>
        </table>
        <h2>Metadata e override canale</h2>
        <p>Bande/canali attesi sono regole di validazione. L'override del canale di analisi è diverso: è una scelta esplicita di modellazione usata dalle mappe sensibili al canale quando il rilievo ha osservato un cambio canale pulito o ambiguo.</p>
        <table>
            <tr><th>Campo metadata</th><th>Uso</th></tr>
            <tr><td>Vendor / Modello / Montaggio / Note</td><td>Documentazione e contesto di revisione. Il montaggio non è ancora usato come formula RF.</td></tr>
            <tr><td>Bande Attese</td><td>Aiuta a rilevare AP osservati su bande non previste, incluso 6 GHz quando esiste evidenza banda/frequenza.</td></tr>
            <tr><td>Canali Attesi</td><td>Crea warning setup quando i canali osservati non coincidono con l'operazione prevista.</td></tr>
            <tr><td>Override Canale Analisi</td><td>Forza le mappe sensibili al canale a usare il canale selezionato per quel gruppo AP e banda.</td></tr>
        </table>
        <h2>Cambi canale puliti</h2>
        <p>Se lo stesso gruppo AP/set BSSID passa pulitamente da un canale a un altro durante il rilievo, AP Group non lo tratta come conflitto BSSID. Interferenza e Canali AP usano di default il canale più recente. Usa override solo quando sai che il canale operativo previsto è diverso.</p>
        <h2>Memoria AP</h2>
        <p>Memoria AP è automatica. Il programma salva i dati revisionati dei Gruppi AP in un file persistente e li applica ai rilievi successivi dopo il normale raggruppamento BSSID quando rivede BSSID già noti.</p>
        <table>
            <tr><th>Stato</th><th>Significato</th><th>Azione</th></tr>
            <tr><td>Da Memoria</td><td>Alias, ruolo, metadata, override o posizione mappa compatibile sono stati applicati da Memoria AP.</td><td>Rivedi la riga, poi usa Memoria &gt; Conferma Selezionato o Conferma Tutti Da Memoria.</td></tr>
            <tr><td>Aggiornamento Memoria</td><td>I dati AP manuali correnti sono diversi dai dati più recenti salvati in Memoria AP.</td><td>Usa Memoria &gt; Aggiorna Selezionato Da Memoria quando il dato salvato è più corretto.</td></tr>
            <tr><td>Salvata</td><td>Il file Memoria AP contiene record AP riusabili.</td><td>Il footer mostra lo stato memoria; Impostazioni può aprire la cartella o svuotare la memoria.</td></tr>
        </table>
        <p>Premere <b>Salva</b> in AP Group Manager scrive il modello AP e aggiorna Memoria AP. Chiudere AP Group Manager con la X della finestra equivale ad Annulla e non salva le modifiche AP Group in sospeso.</p>
        <div class="callout warning"><b>Non usare gli override per nascondere dati brutti.</b> Usali quando sai che il canale operativo corretto è diverso dallo stato osservato nel rilievo, per esempio per riavvii schedulati degli AP.</div>
    """,
    "help_live_maps_nav": "Mappe Live",
    "help_live_maps_title": "Mappe Live E Opzioni",
    "help_live_maps_subtitle": "Mappa Live è la superficie principale di revisione dopo controlli qualità e modello AP.",
    "help_live_maps_body": """
        <h2>Scegli la mappa in base alla domanda</h2>
        <table>
            <tr><th>Mappa</th><th>Cosa mostra</th><th>Come leggerla</th></tr>
            <tr><td>Copertura</td><td>Livello segnale continuo per SSID e banda.</td><td>Usa scala colori e distanza max per non sovrainterpretare zone lontane dai punti reali.</td></tr>
            <tr><td>Canali AP</td><td>Colori discreti dei punti in base al canale servente.</td><td>Usala per verificare piano canali e gestione dei cambi canale.</td></tr>
            <tr><td>AP Dominante</td><td>Quale gruppo AP è più forte in ogni punto.</td><td>Marker gialli o issue indicano ambiguità roaming o incoerenza con posizione AP.</td></tr>
            <tr><td>Interferenza</td><td>Rischio di sovrapposizione canale fra AP servente e AP vicini.</td><td>Controlla ruoli AP e override canale prima di fidarti dello score.</td></tr>
        </table>
        <h2>Opzioni</h2>
        <p>Le mappe continue espongono interpolazione, smoothing, scala colori e distanza max. Le mappe discrete usano legende e label punti perché rappresentano misure reali, non superfici interpolate.</p>
        <table>
            <tr><th>Opzione</th><th>Significato</th><th>Usala con attenzione quando</th></tr>
            <tr><td>Banda</td><td>Limita l'analisi a 2.4, 5, 6 GHz o tutte le bande dove supportato.</td><td>Righe senza banda/frequenza esplicita possono rendere ambigui canali bassi.</td></tr>
            <tr><td>Interpolazione</td><td>Controlla come le superfici continue vengono stimate fra punti reali.</td><td>Aree grandi senza punti non vanno sovrainterpretate.</td></tr>
            <tr><td>Smoothing</td><td>Rende copertura/interferenza visivamente più calme.</td><td>Smoothing alto può nascondere transizioni RF nette.</td></tr>
            <tr><td>Distanza Max</td><td>Limita il rendering continuo alle aree vicine ai punti misurati.</td><td>Aumentala solo quando la densità punti è buona.</td></tr>
            <tr><td>Label Punti</td><td>Controlla le etichette sulle mappe discrete.</td><td>Usa Auto nei report; usa Tutti quando vuoi auditare l'attribuzione punti.</td></tr>
            <tr><td>Filtro Gruppo AP</td><td>Evidenzia o limita l'analisi a un gruppo AP dove applicabile.</td><td>Usalo per verificare un AP problematico senza perdere il contesto generale.</td></tr>
        </table>
        <h2>Limiti di lettura</h2>
        <p>Le mappe live aggiornano la visualizzazione, non i dati raccolti. Se una mappa sembra sbagliata, controlla il percorso evidenza: qualità punto, gruppi AP, ruoli, metadata, scala e posizioni AP.</p>
        <div class="section-card"><b>Cambi canale:</b> se lo stesso gruppo AP passa pulitamente da un canale a un altro durante il rilievo, le mappe sensibili al canale usano di default il canale più recente. Se la sequenza è ambigua, le mappe preservano i canali misurati salvo override esplicito.</div>
    """,
    "help_reports_nav": "Report PDF",
    "help_reports_title": "Report PDF Live",
    "help_reports_subtitle": "L'export PDF cattura le opzioni della Mappa Live corrente e aggiunge pagine diagnostiche dove il tipo mappa ha finding azionabili.",
    "help_reports_body": """
        <h2>Pagina mappa</h2>
        <p>La prima pagina usa tutta l'estensione della pianta, non lo zoom corrente. Legende, scale colori e label punti seguono le opzioni attive della Mappa Live.</p>
        <h2>Report per tipo mappa</h2>
        <table>
            <tr><th>Export</th><th>Pagine</th><th>Note</th></tr>
            <tr><td>Copertura</td><td>Solo pagina mappa</td><td>Nessuna pagina problemi per scelta. Usa Qualità Rilievo per problemi dati.</td></tr>
            <tr><td>Canali AP</td><td>Solo pagina mappa</td><td>Utile per revisione piano canali. Schede diagnostiche non aggiunte finché non esiste una regola chiara.</td></tr>
            <tr><td>AP Dominante</td><td>Mappa più schede problema quando ci sono finding</td><td>Le schede spiegano contesto AP dominante/vicino e warning posizione AP.</td></tr>
            <tr><td>Interferenza</td><td>Mappa più schede problema quando ci sono finding</td><td>Le schede mostrano AP/canale servente, interferente principale/canale, overlap e rischio.</td></tr>
        </table>
        <h2>Schede problema</h2>
        <p>Interferenza e AP Dominante possono aggiungere schede problema paginate. I callout quadrati numerati sulla mappa corrispondono alle schede numerate, così puoi attribuire ogni punto a una diagnosi specifica.</p>
        <h2>Prima di inviare un report</h2>
        <ul>
            <li>Conferma che SSID, banda e tipo mappa selezionati siano quelli da documentare.</li>
            <li>Controlla che le posizioni AP siano complete quando rivedi finding AP Dominante.</li>
            <li>Rivedi note cambio canale e override canale analisi prima di esportare Interferenza o Canali AP.</li>
            <li>Usa le schede report come diagnostica. Una scheda warning può descrivere un problema reale del deployment, non un errore software.</li>
        </ul>
        <div class="callout"><b>Copertura non ha pagina problemi per scelta.</b> È una visualizzazione del segnale. Problemi qualità o setup AP si rivedono in Qualità Rilievo e AP Group Manager.</div>
        <h2>Comportamento attuale Canali AP</h2>
        <p>L'export Canali AP è solo mappa finché non esiste una regola diagnostica chiara che meriti schede report.</p>
    """,
    "help_diagnostics_nav": "Warning",
    "help_diagnostics_title": "Warning E Diagnostica",
    "help_diagnostics_subtitle": "I warning sono inviti a controllare ipotesi, non prova automatica che un punto sia sbagliato.",
    "help_diagnostics_body": """
        <h2>Categorie warning</h2>
        <table>
            <tr><th>Finding</th><th>Ragionamento</th><th>Cosa controllare</th></tr>
            <tr><td>AP Dominante Inatteso</td><td>L'AP più forte non è coerente con posizione fisica o AP più vicino.</td><td>Verifica posizioni AP, alias, calibrazione scala e roaming reale.</td></tr>
            <tr><td>Ambiguità Roaming</td><td>AP più forte e secondo AP sono vicini in dB.</td><td>Aspettati roaming client poco prevedibile in quella zona.</td></tr>
            <tr><td>Canale Inatteso</td><td>Il canale osservato non coincide con i metadata AP.</td><td>Controlla configurazione AP o aggiorna i canali attesi.</td></tr>
            <tr><td>Cambio Canale Pulito</td><td>Lo stesso AP ha cambiato canale nel tempo senza conflitto BSSID.</td><td>Accetta il default canale recente o imposta un override canale analisi.</td></tr>
            <tr><td>Posizione AP Mancante</td><td>Un gruppo AP rilevante non ha marker fisico.</td><td>Posiziona l'AP per abilitare la diagnostica basata sulle distanze.</td></tr>
        </table>
        <h2>Pattern di troubleshooting</h2>
        <table>
            <tr><th>Sintomo</th><th>Causa probabile</th><th>Azione successiva</th></tr>
            <tr><td>Copertura troppo ottimistica lontano dai punti</td><td>L'interpolazione sta riempiendo spazio non misurato.</td><td>Abbassa distanza max o raccogli più punti.</td></tr>
            <tr><td>Interferenza appare su un vecchio canale</td><td>AP cambiato canale durante il rilievo o override mancante/errato.</td><td>Controlla dettaglio cambio canale e override metadata AP.</td></tr>
            <tr><td>AP Dominante lontano dal suo marker fisico</td><td>Posizione AP sbagliata, gruppo errato, roaming client o propagazione RF reale.</td><td>Apri dettaglio AP Dominante, verifica AP più vicino e alias gruppi.</td></tr>
            <tr><td>Molti punti richiedono rescan</td><td>SSID rilevanti mancanti, segnale instabile o dati radi.</td><td>Focalizza i punti coinvolti e rifai scansione prima di interpretare mappe.</td></tr>
            <tr><td>Canali inattesi su un AP</td><td>Metadata vecchio, configurazione AP cambiata o evidenza banda/canale ambigua.</td><td>Controlla metadata AP, config reale controller e dati banda/frequenza dello scanner.</td></tr>
        </table>
        <div class="section-card"><b>Ordine di revisione:</b> qualità punto prima, gruppi AP poi, metadata e posizioni dopo, interpretazione mappa per ultima.</div>
        <div class="callout danger"><b>Non silenziare i warning alla cieca.</b> Un warning che riflette comportamento reale del deployment è evidenza utile e dovrebbe restare visibile finché non lo capisci.</div>
    """,
    "help_glossary_nav": "Glossario",
    "help_glossary_title": "Glossario",
    "help_glossary_subtitle": "Termini usati dal workflow V2 e dai report.",
    "help_glossary_body": """
        <table>
            <tr><th>Termine</th><th>Significato</th></tr>
            <tr><td>Gruppo AP</td><td>Il modello del programma per un AP fisico, di solito con più BSSID.</td></tr>
            <tr><td>Memoria AP</td><td>File persistente in cui vengono salvati alias, ruoli, metadata, override canale analisi e posizioni compatibili per rilievi futuri.</td></tr>
            <tr><td>BSSID</td><td>Il MAC radio visto dalle scansioni Wi-Fi.</td></tr>
            <tr><td>SSID</td><td>Il nome della rete Wi-Fi. Uno stesso SSID può essere trasmesso da molti BSSID.</td></tr>
            <tr><td>SSID Rilevante</td><td>Una rete selezionata come importante per controlli qualità e analisi.</td></tr>
            <tr><td>Confidenza</td><td>Quanto è affidabile una riga aggregata, in base alle scansioni ripetute.</td></tr>
            <tr><td>Sidecar Raw</td><td>Il file <code>.scan</code> collegato che contiene i campioni grezzi delle scansioni ripetute.</td></tr>
            <tr><td>AP Dominante</td><td>Il gruppo AP con segnale osservato più forte in un punto di misura.</td></tr>
            <tr><td>Ambiguità Roaming</td><td>Un punto dove AP più forte e secondo AP sono abbastanza vicini da poter essere scelti entrambi dai client.</td></tr>
            <tr><td>Cambio Canale Pulito</td><td>Un gruppo AP che cambia canale nel tempo senza evidenza di conflitti BSSID misti.</td></tr>
            <tr><td>Cambio Canale Ambiguo</td><td>Sequenza canale in cui il programma non può trattare con certezza il cambio come transizione pulita.</td></tr>
            <tr><td>Override Canale Analisi</td><td>Canale scelto dall'utente per mappe sensibili al canale su uno specifico gruppo AP e banda.</td></tr>
            <tr><td>Warning Setup</td><td>Problema di modello/deployment che non richiede necessariamente di rifare il punto.</td></tr>
            <tr><td>Finding Rescan Punto</td><td>Problema qualità che suggerisce di rifare la scansione del punto di misura.</td></tr>
            <tr><td>Da Memoria</td><td>Stato Gruppo AP che indica dati applicati da Memoria AP e ancora da confermare o modificare.</td></tr>
            <tr><td>Aggiornamento Memoria</td><td>Stato Gruppo AP che indica dati salvati in Memoria AP diversi dai dati manuali correnti.</td></tr>
            <tr><td>Interpolazione</td><td>Stima visuale fra punti misurati. Aiuta la leggibilità ma non sostituisce misure reali.</td></tr>
            <tr><td>Distanza Max</td><td>Limite di rendering che evita alle mappe continue di estendersi troppo lontano dall'evidenza misurata.</td></tr>
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
