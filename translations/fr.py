"""French translations."""

from translations.en import TRANSLATIONS as EN_TRANSLATIONS


LANGUAGE_LABEL = "Français"

TRANSLATIONS = dict(EN_TRANSLATIONS)
TRANSLATIONS.update({
    "wifi_scan_timeout": "Le délai de l'analyse Wi-Fi est dépassé. Vérifiez l'adaptateur et réessayez.",
    "wifi_scan_failed": "L'analyse Wi-Fi a échoué. Vérifiez l'adaptateur, les autorisations Windows et le journal de l'application.",
    "loading_app": "Chargement des composants...",
    "loading_app_ready": "Prêt",
    "loading_app_error": "Erreur pendant le chargement de l'application.",
    "start_subtitle": "Relevés réels, cartes Live et diagnostics RF",
    "start_workflow_title": "Workflow",
    "start_workflow_1": "1. Créez ou ouvrez un relevé et chargez le plan.",
    "start_workflow_2": "2. Enregistrez les points avec scans multi-échantillons et réseaux pertinents.",
    "start_workflow_3": "3. Analysez couverture, interférences, roaming, groupes AP et qualité.",
    "start_loading_title": "Démarrage",
    "start_actions_title": "Relevé",
    "start_actions_hint": "Les commandes s'activent quand les composants d'analyse sont prêts.",
    "start_ready_hint": "La fenêtre principale s'ouvrira directement sur le relevé sélectionné.",
    "qt_start_hint_title": "Interface actuelle",
    "qt_start_hint": "Cette release utilise l'interface Qt avec relevé, carte Live, groupes AP, qualité, génération de cartes et calibration d'échelle.",
    "toolbar_project": "Projet",
    "toolbar_view": "Vue",
    "toolbar_analysis": "Analyse",
    "toolbar_settings": "Paramètres",
    "qt_survey_file_filter": "CSV relevé Wi-Fi (*.csv);;Tous les fichiers (*.*)",
    "qt_plan_file_filter": "PDF et images (*.pdf *.png *.jpg *.jpeg *.bmp);;Tous les fichiers (*.*)",
    "qt_points": "Points",
    "qt_raw_rows": "Scans bruts",
    "qt_table_networks": "Réseaux",
    "qt_table_best_dbm": "Meilleur dBm",
    "qt_table_timestamp": "Horodatage",
    "summary_ap_groups": "Groupes AP",
    "points_panel_show": "▲ Points de mesure",
    "points_panel_hide": "▼ Points de mesure",
    "points_panel_resize": "Glissez vers le haut ou le bas pour redimensionner le panneau des points.",
    "new_survey": "Nouveau relevé",
    "new_survey_measurement_system_title": "Unités du nouveau relevé",
    "new_survey_measurement_system_message": "Choisissez le système de mesure pour ce relevé.\n\nL'échelle et la grille du plan blanc généré seront créées à partir de ce choix.",
    "new_survey_close_current_title": "Démarrer un nouveau relevé ?",
    "new_survey_close_current_message": "Cette opération fermera le relevé actuel avant d'en créer un nouveau.\n\nEnregistrer le relevé actuel, annuler les changements ou abandonner ?",
    "discard_changes": "Annuler les changements",
    "open_existing_survey": "Ouvrir relevé",
    "invalid_survey_title": "Relevé incompatible",
    "invalid_survey_format": "Le fichier sélectionné n'est pas un CSV de relevé Wi-Fi valide. Créez un nouveau relevé ou ouvrez le CSV principal généré par le programme.",
    "raw_scan_file_selected": "Vous avez sélectionné le fichier de données brutes. Ouvrez le CSV principal du relevé, pas le fichier _raw_data.scan.",
    "invalid_raw_scan_format": "Le fichier de scans bruts associé à ce relevé n'est pas valide. Recréez le relevé ou supprimez le sidecar invalide.",
    "exit": "Quitter",
    "language": "Langue",
    "ui_scale": "Échelle UI",
    "ui_scale_auto": "Auto ({percent}%)",
    "measurement_system": "Système de mesure",
    "measurement_system_metric": "Métrique (m)",
    "measurement_system_imperial": "Impérial (ft)",
    "workspace_settings_section": "Workspace",
    "go_to_point_zoom": "Zoom Aller au point",
    "measurement_unit_metric": "mètres",
    "measurement_unit_imperial": "pieds",
    "measurement_system_scale_reset_title": "La calibration d'échelle sera réinitialisée",
    "measurement_system_scale_reset_message": "Ce relevé possède déjà une échelle calibrée. Changer le système de mesure supprimera la calibration actuelle.\n\nRelancez Calibrer l'échelle avant d'interpréter les distances. Continuer ?",
    "measurement_system_scale_reset_button": "Changer et effacer l'échelle",
    "measurement_system_scale_reset_done": "Système de mesure changé. Échelle effacée ; relancez Calibrer l'échelle.",
    "ui_scale_restart_title": "Redémarrage requis",
    "ui_scale_restart_message": "Appliquer l'échelle UI {scale} nécessite un redémarrage.\n\nEnregistrer ce choix et redémarrer maintenant ?",
    "save_and_restart": "Enregistrer et redémarrer",
    "settings_save_failed": "Impossible d'enregistrer les paramètres.",
    "ap_memory_settings_title": "Mémoire AP",
    "open_memory_folder": "Ouvrir dossier mémoire",
    "open_memory_folder_failed": "Impossible d'ouvrir le dossier Mémoire AP.",
    "clear_ap_memory": "Vider Mémoire AP...",
    "clear_ap_memory_title": "Vider Mémoire AP",
    "clear_ap_memory_confirm": "Cette action supprimera les alias, rôles, métadonnées et positions AP mémorisés pour les futurs relevés.\n\nLe relevé ouvert ne sera pas modifié. Continuer ?",
    "clear_ap_memory_confirm_button": "Vider Mémoire AP",
    "clear_ap_memory_failed": "Impossible de vider la Mémoire AP.",
    "restart_failed": "Impossible de redémarrer l'application.",
    "restart_blocked_busy": "Attendez la fin du scan ou de la mise à jour de carte avant de changer l'échelle UI.",
    "active_survey": "Relevé actif : {name}",
    "survey_tab": "Relevé",
    "live_map_tab": "Carte Live",
    "live_auto_update": "Mise à jour auto",
    "live_update_now": "Mettre à jour",
    "live_export_pdf": "Exporter PDF",
    "live_pdf_exported": "PDF exporté",
    "save_live_pdf_title": "Enregistrer PDF carte Live",
    "live_pdf_file_filter": "PDF (*.pdf);;Tous les fichiers (*.*)",
    "live_pdf_problem_report_title": "Rapport problèmes",
    "live_pdf_issue": "Problème",
    "live_pdf_no_interference_issues": "Aucun problème d'interférence pertinent détecté.",
    "live_pdf_no_dominant_issues": "Aucun problème d'AP dominant pertinent détecté.",
    "live_options_show": "Options",
    "live_options_hide": "Options",
    "live_preview_empty": "Carte Live : chargez un plan et enregistrez au moins 3 points.",
    "live_preview_insufficient": "Carte Live : données insuffisantes pour cette vue.",
    "live_preview_rendering": "Mise à jour de la carte Live...",
    "live_preview_updated": "Carte Live mise à jour.",
    "ap_group_filter": "Groupe AP",
    "all_ap_groups_option": "Tous les groupes AP",
    "footer_survey_info": "CSV : {csv} | Plan : {map} | Points : {points} | Dernier : {last}",
    "ap_memory_status_missing": "Mémoire AP : non créée",
    "ap_memory_status_empty": "Mémoire AP : vide",
    "ap_memory_status_saved": "Mémoire AP : enregistrée ({count} AP)",
    "ap_memory_status_applied": "Mémoire AP : {applied} à confirmer / {total} enregistrés",
    "unsaved_survey": "Relevé non enregistré",
    "no_map": "Aucun plan",
    "default_floorplan_name": "Plan vierge",
    "replace_default_floorplan_title": "Remplacer le plan blanc ?",
    "replace_default_floorplan": "Le plan blanc généré sera enregistré sous :\n{path}\n\nCe fichier existe déjà. Le remplacer ?",
    "generated_floorplan_cleanup_failed": "Impossible de supprimer le plan blanc remplacé : {path}",
    "load_plan": "Charger plan",
    "generate_heatmap": "Générer heatmap",
    "generate": "Générer",
    "save": "Enregistrer",
    "save_clean_tooltip": "Relevé enregistré",
    "save_dirty_tooltip": "Changements non enregistrés",
    "ap_aliases": "Groupes AP",
    "quality_dashboard_title": "Qualité relevé",
    "quality_dashboard_hint": "Vérifiez qualité des scans, setup AP et diagnostics de carte avant de vous fier aux cartes générées.",
    "quality_dashboard_status_ok_title": "Relevé cohérent",
    "quality_dashboard_status_ok_message": "Aucun point ne nécessite un rescan. Les contrôles qualité n'ont trouvé aucun problème sur {total} points.",
    "quality_dashboard_status_early_title": "Données initiales",
    "quality_dashboard_status_early_message": "Aucun problème de scan détecté sur {total} points, mais l'analyse sera plus utile avec plus de points.",
    "quality_dashboard_status_review_title": "Révision recommandée",
    "quality_dashboard_status_review_message": "{count} points sur {total} doivent être révisés ou rescannés avant d'utiliser les cartes.",
    "quality_dashboard_status_setup_title": "Setup AP à vérifier",
    "quality_dashboard_status_setup_message": "Les points ne nécessitent pas de rescan, mais positions AP, métadonnées ou changements de canal doivent être revus.",
    "quality_dashboard_metric_points": "Total points",
    "quality_dashboard_metric_ok": "Points OK",
    "quality_dashboard_metric_review": "Points à revoir",
    "quality_dashboard_metric_group_survey": "Points relevé",
    "quality_dashboard_metric_group_scan": "Qualité scan",
    "quality_dashboard_metric_group_ap": "Modèle AP",
    "quality_dashboard_metric_scan_ok": "Scan OK",
    "quality_dashboard_metric_rescan": "Points à revoir",
    "quality_dashboard_metric_missing": "Réseaux pertinents manquants",
    "quality_dashboard_metric_sparse": "Données rares",
    "quality_dashboard_metric_scanner_details": "Détails scanner manquants",
    "quality_dashboard_metric_low_confidence": "Faible confiance scan",
    "quality_dashboard_metric_unstable": "Signal instable",
    "quality_dashboard_metric_connected_client": "Roaming client",
    "quality_dashboard_metric_ap_diagnostic_points": "Findings AP dominant",
    "quality_dashboard_metric_ap_memory_applied": "Révision Mémoire AP",
    "quality_dashboard_metric_ap_position_warnings": "Avertissements position AP",
    "quality_dashboard_metric_ap_missing_positions": "AP sans position",
    "quality_dashboard_metric_ap_metadata_warnings": "Avertissements config AP",
    "quality_dashboard_metric_channel_changes": "Changements canal",
    "quality_dashboard_fix_next_title": "À corriger ensuite",
    "quality_dashboard_fix_missing_title": "Rescanner réseaux manquants",
    "quality_dashboard_fix_missing_detail": "{count} points ne voient pas un ou plusieurs SSID attendus. Rescannez-les, vérifiez les réseaux pertinents ou le scope Local Area.",
    "quality_dashboard_fix_sparse_title": "Répéter scans rares",
    "quality_dashboard_fix_sparse_detail": "{count} points ont trop peu d'échantillons utilisables. Répétez ces scans avant de vous fier à l'interpolation.",
    "quality_dashboard_fix_scanner_details_title": "Rescanner points avec détails limités",
    "quality_dashboard_fix_scanner_details_detail": "{count} points manquent de détails scanner utiles à l'analyse sensible au canal. Rescannez avant Interférence, largeur 5 GHz ou lecture 6 GHz.",
    "quality_dashboard_fix_scanner_details_dialog_detail": "Utilisez Aller au point et rescannez quand largeur canal, fréquence ou fallback scanner influencent les conclusions.",
    "quality_dashboard_fix_low_confidence_title": "Rescanner points peu fiables",
    "quality_dashboard_fix_low_confidence_detail": "{count} points ont une faible confiance du candidat dominant. Répétez-les ou vérifiez la stabilité du scanner.",
    "quality_dashboard_fix_unstable_title": "Répéter points instables",
    "quality_dashboard_fix_unstable_detail": "{count} points ont une dispersion d'échantillons pouvant affecter les cartes. Répétez-les s'ils guident des décisions.",
    "quality_dashboard_fix_connected_client_title": "Vérifier roaming client",
    "quality_dashboard_fix_connected_client_detail": "{count} points montrent le laptop associé à un AP plus faible alors qu'un autre groupe AP du même SSID est plus fort. Vérifiez le sticky client ou rescannez après reconnexion.",
    "quality_dashboard_fix_ap_memory_title": "Réviser Mémoire AP",
    "quality_dashboard_fix_ap_memory_detail": "{count} groupes AP nécessitent une révision Mémoire AP. Confirmez les données appliquées ou décidez si les données manuelles doivent remplacer la mémoire.",
    "quality_dashboard_fix_ap_memory_dialog_detail": "Utilisez Ouvrir groupe AP pour inspecter les groupes avec état mémoire. Confirmez ou mettez à jour selon l'écart avec la Mémoire AP.",
    "quality_dashboard_fix_ap_position_title": "Réviser warnings AP dominant",
    "quality_dashboard_fix_ap_position_detail": "{count} points contredisent les positions AP physiques. Inspectez les marqueurs avant les conclusions basées sur AP.",
    "quality_dashboard_fix_ap_position_dialog_detail": "Utilisez Aller au point pour inspecter chaque finding sur le plan.",
    "quality_dashboard_fix_ap_missing_title": "Placer AP manquants",
    "quality_dashboard_fix_ap_missing_detail": "{count} groupes AP pertinents n'ont pas de position. Ajoutez leur position physique avant les diagnostics de distance AP.",
    "quality_dashboard_fix_ap_missing_dialog_detail": "Seuls les groupes AP pertinents non-test sans position sont listés. Utilisez Ouvrir groupe AP pour placer chaque AP.",
    "quality_dashboard_fix_ap_metadata_title": "Réviser métadonnées AP",
    "quality_dashboard_fix_ap_metadata_detail": "{count} groupes AP ont des canaux ou bandes attendus incohérents. Corrigez les métadonnées ou définissez un canal d'analyse override.",
    "quality_dashboard_fix_ap_metadata_dialog_detail": "Utilisez Ouvrir métadonnées AP pour corriger canaux/bandes attendus ou définir un override de canal d'analyse.",
    "quality_dashboard_fix_channel_change_clean_title": "Réviser modèle de changement canal",
    "quality_dashboard_fix_channel_change_ambiguous_title": "Résoudre changements canal ambigus",
    "quality_dashboard_fix_channel_change_detail": "{count} groupes AP ont changé de canal pendant le relevé ({clean} propres, {ambiguous} ambigus). Les cartes sensibles au canal utilisent le dernier canal propre par défaut.",
    "quality_dashboard_fix_channel_change_dialog_detail": "Utilisez Ouvrir métadonnées AP pour inspecter chaque changement et définir un override si le choix automatique est incorrect.",
    "quality_dashboard_fix_more_points_title": "Collecter plus de points",
    "quality_dashboard_fix_more_points_detail": "Seulement {total} points disponibles. Ajoutez des positions avant de lire les trous de couverture.",
    "quality_dashboard_fix_ready_title": "Générer cartes",
    "quality_dashboard_fix_ready_detail": "Les contrôles principaux sont propres. Générez les cartes ou ouvrez les listes KPI pour un dernier passage.",
    "quality_dashboard_context_scope": "Scope relevé\nPertinents : {networks}\nPositions AP : {positions}\nAP test : {test_aps}",
    "quality_dashboard_scope_title": "Scope relevé",
    "quality_dashboard_scope_relevant": "Pertinents : {networks}",
    "quality_dashboard_scope_positions": "Positions AP : {positions}",
    "quality_dashboard_scope_test_aps": "AP test : {test_aps}",
    "quality_dashboard_action_open_dominant": "Carte AP dominant",
    "quality_dashboard_action_open_ap_channels": "Carte canaux AP",
    "quality_dashboard_action_open_interference": "Carte interférence",
    "quality_dashboard_action_open_ap_metadata": "Ouvrir métadonnées AP",
    "quality_dashboard_action_open_ap_group": "Ouvrir groupe AP",
    "quality_dashboard_action_focus_point": "Aller au point",
    "quality_dashboard_action_metadata_for": "Métadonnées : {ap}",
    "quality_dashboard_action_group_for": "Groupe AP : {ap}",
    "quality_dashboard_channel_change_status_clean": "propre",
    "quality_dashboard_channel_change_status_ambiguous": "ambigu",
    "quality_dashboard_channel_change_label": "{ap} {band} : {status}, canaux {channels}, actuel {current}",
    "quality_dashboard_channel_change_item_detail": "<b>Bande :</b> {band}<br><b>Canaux observés :</b> {channels}<br><b>Cartes utilisent :</b> {current}<br><b>État :</b> {status}",
    "quality_dashboard_expand_details": "Détails ({count})",
    "quality_dashboard_detail_count": "{count} lignes détail",
    "quality_dashboard_detail_ap_groups": "{count} groupes AP",
    "quality_dashboard_detail_measurement_points": "{count} points de mesure",
    "quality_dashboard_detail_channel_changes": "{count} changements canal",
    "quality_dashboard_missing_position_item_detail": "<b>Groupe AP :</b> {group}<br><b>Action requise :</b> placer cet AP sur le plan",
    "quality_dashboard_point_detail_label": "Point {point} ({x}, {y})",
    "quality_dashboard_ap_position_finding": "Finding : {finding}",
    "quality_dashboard_ap_position_detail": "AP dominant : {dominant} | Signal : {signal} | Distance : {dominant_distance}\nAP le plus proche : {closest} | Distance : {closest_distance}",
    "quality_dashboard_context_relevant_networks": "Réseaux pertinents",
    "quality_dashboard_context_ap_positions": "État positions AP",
    "quality_dashboard_context_test_aps": "AP test exclus",
    "quality_dashboard_context_missing_positions": "AP sans position",
    "quality_dashboard_context_config_warnings": "Détails config AP",
    "quality_dashboard_ap_metadata_channels": "<b>Canaux observés :</b> {channels}<br><b>Canaux attendus :</b> {expected}",
    "quality_dashboard_ap_metadata_bands": "<b>Bandes observées :</b> {bands}<br><b>Bandes attendues :</b> {expected}",
    "quality_dashboard_ap_memory_item_detail": "<b>État mémoire :</b> M - appliqué depuis Mémoire AP<br><b>BSSID associés :</b> {matched_bssids}<br><b>Suite :</b> confirmer ou modifier les données AP mémorisées",
    "quality_dashboard_ap_memory_update_item_detail": "<b>État mémoire :</b> <s>M</s> - les données AP actuelles diffèrent de la Mémoire AP<br><b>Champs différents :</b> {fields}<br><b>Suite :</b> mettre à jour depuis la mémoire, ou garder les données actuelles et les enregistrer",
    "quality_dashboard_scanner_details_issue": "Détails scanner : {detail}",
    "quality_dashboard_scanner_details_fallback": "Scanner utilisé : <b>{backends}</b> (détails canal limités)",
    "quality_dashboard_scanner_details_missing_width": "Largeur canal manquante sur <b>{count}</b> lignes scan",
    "quality_dashboard_scanner_details_missing_frequency": "Fréquence 6 GHz manquante sur <b>{count}</b> lignes scan",
    "quality_dashboard_scanner_details_finding": "Détails scanner limités",
    "quality_dashboard_scanner_details_scanner": "Scanner : <b>{backends}</b>{fallback} | Lignes scan brutes : <b>{count}</b>",
    "quality_dashboard_scanner_details_fallback_suffix": " (fallback)",
    "quality_dashboard_scanner_details_missing_width_detail": "Largeur canal manquante : <b>{count}</b> lignes sensibles au canal",
    "quality_dashboard_scanner_details_missing_frequency_detail": "Fréquence 6 GHz manquante : <b>{count}</b> lignes 6 GHz",
    "quality_dashboard_scanner_details_impact": "Impact : les cartes sensibles au canal peuvent être moins fiables ici.",
    "quality_dashboard_issue_missing_relevant": "<b>{ssid}</b> : réseau pertinent non détecté à ce point",
    "quality_dashboard_issue_low_confidence": "<b>{ssid}</b> : niveau de confiance {confidence}",
    "quality_dashboard_issue_unstable_signal": "<b>{ssid}</b> : signal varie de {range} dB",
    "quality_dashboard_issue_sparse_data": "Pas assez d'échantillons à ce point",
    "quality_dashboard_connected_client_issue": "<b>{ssid}</b> : AP connecté <b>{connected}</b> ({connected_signal}) ; AP plus fort <b>{stronger}</b> ({stronger_signal}) ; écart {delta} dB",
    "quality_dashboard_more_issues": "+{count} de plus",
    "quality_dashboard_metric_view_points": "Voir points",
    "quality_dashboard_metric_extra_details": "Détails",
    "quality_dashboard_metric_click_points": "Cliquer pour voir les points",
    "quality_dashboard_metric_click_details": "Cliquer pour ouvrir les détails",
    "quality_dashboard_points_dialog_title": "{label} - {count} points",
    "quality_dashboard_check_kpi_issue": "Contrôle KPI : {kpis}",
    "quality_dashboard_visible_count": "{shown}/{total} points affichés",
    "quality_dashboard_quality": "Qualité",
    "quality_dashboard_scan_quality": "Qualité scan",
    "quality_dashboard_confidence": "Confiance",
    "quality_dashboard_issue": "Problème",
    "quality_dashboard_relevant_ssids": "SSID pertinents",
    "quality_dashboard_no_issue": "Aucun problème détecté",
    "quality_dashboard_ap_position_issue": "AP dominant : <b>{dominant}</b> ({signal}, {dominant_distance}) | AP le plus proche : <b>{closest}</b> ({closest_distance}) | <b>{warning}</b>",
    "quality_dashboard_missing_positions_none": "aucun",
    "quality_dashboard_missing_positions_more": "{names}, +{count}",
    "calibrate_scale": "Calibrer échelle",
    "calibrate_scale_title": "Calibration d'échelle",
    "calibrate_scale_start": "Clic gauche sur le premier point de la distance réelle connue.",
    "calibrate_scale_second_point": "Clic gauche sur le second point de la distance connue.",
    "calibrate_scale_distance_prompt": "Distance réelle entre les deux points ({unit}) :",
    "calibrate_scale_saved": "Échelle calibrée : {scale}.",
    "calibrate_scale_invalid": "Distance invalide.",
    "calibrate_scale_cancelled": "Calibration annulée.",
    "calibrate_scale_already_set": "Échelle déjà calibrée. Supprimez l'échelle actuelle pour recalibrer.",
    "grid": "Grille",
    "grid_enabled": "Grille activée.",
    "grid_disabled": "Grille désactivée.",
    "grid_scale_label": "1 carré = {interval}",
    "boundaries": "Confins",
    "boundaries_enabled": "Mode Confins activé.",
    "boundaries_disabled": "Mode Confins désactivé.",
    "boundaries_draw_tooltip": "Glisser-clic droit pour dessiner le masque",
    "boundaries_eraser_tooltip": "Glisser-clic droit pour gommer le masque",
    "boundaries_circle_tooltip": "Brosse ronde",
    "boundaries_square_tooltip": "Brosse carrée",
    "boundaries_brush_size_tooltip": "Taille de brosse Confins",
    "boundaries_brush_size_increase_tooltip": "Augmenter la taille de brosse",
    "boundaries_brush_size_decrease_tooltip": "Réduire la taille de brosse",
    "boundaries_brush_size_value_tooltip": "Taille brosse : {size} px ({minimum}-{maximum} px, pas {step} px)",
    "boundaries_clear_tooltip": "Effacer le masque Confins",
    "boundaries_clear_title": "Effacer les Confins ?",
    "boundaries_clear_confirm": "Effacer le masque Confins actuel ?",
    "boundaries_cleared": "Masque Confins effacé.",
    "boundaries_save_failed": "Impossible d'enregistrer le masque Confins : {path}",
    "boundaries_cleanup_failed": "Impossible de supprimer le masque Confins remplacé : {path}",
    "delete_scale": "Suppr. échelle",
    "delete_scale_title": "Supprimer calibration ?",
    "delete_scale_confirm": "Supprimer la calibration d'échelle actuelle ?",
    "delete_scale_done": "Calibration supprimée.",
    "ap_groups_title": "Groupes AP",
    "ap_groups_hint": "Regroupez les BSSID qui appartiennent au même AP physique. Alias, rôle, métadonnées et position alimentent cartes et contrôles qualité.",
    "ap_group_bssid_title": "Gestionnaire BSSID",
    "ap_group_bssid_hint": "Corrigez les appartenances BSSID sans reconstruire tout le modèle AP.",
    "ap_group_bssid_warning_focus_hint": "Cette vue est focalisée sur les BSSID liés à l'avertissement sélectionné.",
    "ap_group_bssid_scope": "Scope",
    "ap_group_bssid_scope_current": "Groupe actuel",
    "ap_group_bssid_scope_other": "Autres groupes",
    "ap_group_bssid_scope_unassigned": "Non assignés",
    "ap_group_bssid_scope_checked": "Sélectionnés",
    "ap_group_bssid_scope_warning": "Focus warning",
    "ap_group_bssid_filter_all": "Tous",
    "ap_group_bssid_select_visible": "Sélect. visibles",
    "ap_group_bssid_clear_visible": "Vider visibles",
    "ap_group_bssid_invert_visible": "Inverser visibles",
    "ap_group_bssid_new_group_from_rows": "Nouveau groupe des lignes",
    "ap_group_bssid_move_rows": "Déplacer lignes...",
    "ap_group_bssid_select_rows_required": "Sélectionnez d'abord une ou plusieurs lignes BSSID.",
    "ap_group_bssid_visible_count": "{visible}/{total} BSSID",
    "ap_group_bssid_management": "Gestion BSSID",
    "ap_group_conflict_title": "Détails conflit AP",
    "ap_group_conflict_hint": "Le diagnostic explique pourquoi le regroupement automatique peut être ambigu.",
    "ap_group_conflict_diagnosis_title": "Diagnostic",
    "ap_group_conflict_recommendation_title": "Recommandation",
    "ap_group_conflict_diagnosis_body": "Des BSSID de ce groupe montrent canaux, bandes ou SSID incohérents pour un seul AP physique.",
    "ap_group_conflict_recommendation_body": "Utilisez Gestionnaire BSSID pour séparer les radios ou confirmer que le groupe représente bien le même AP physique.",
    "ap_group_set_alias": "Alias",
    "ap_group_set_role": "Rôle",
    "ap_group_metadata_title": "Métadonnées AP",
    "ap_group_set_position": "Position",
    "ap_group_delete_alias_title": "Supprimer alias",
    "ap_group_delete_alias_confirm": "Supprimer l'alias du groupe AP sélectionné ?",
    "ap_group_select_group": "Sélectionnez d'abord un groupe AP.",
    "ap_groups_reset_auto": "Reset auto",
    "ap_groups_reset_title": "Réinitialiser groupes AP",
    "ap_groups_reset_confirm": "Restaurer le regroupement BSSID automatique ? Les alias compatibles seront conservés, mais les edits manuels seront perdus.",
    "ap_alias_group": "Groupe AP",
    "ap_label": "Label",
    "ap_alias_bssids": "BSSID",
    "ap_alias_ssids": "SSID vus",
    "ap_alias_channels": "Canaux",
    "ap_alias_bands": "Bandes",
    "ap_alias_value": "Alias",
    "ap_group_management": "Gestion",
    "ap_group_state_manual": "Manuel",
    "ap_group_state_auto": "Auto",
    "ap_group_state_memory": "Depuis mémoire",
    "ap_group_state_memory_update": "Mise à jour mémoire",
    "ap_group_filter_status": "État",
    "ap_group_filter_status_all": "Tous états",
    "ap_group_filter_status_warning": "Warnings",
    "ap_group_filter_status_ok": "OK",
    "ap_group_filter_role": "Rôle",
    "ap_group_filter_role_all": "Tous rôles",
    "ap_group_filter_band": "Bande",
    "ap_group_filter_band_all": "Toutes bandes",
    "ap_group_filter_state": "État",
    "ap_group_filter_state_all": "Tous états",
    "ap_group_clear_filters": "Effacer filtres",
    "ap_group_visible_count": "{visible}/{total} groupes",
    "ap_alias_search": "Recherche",
    "ap_groups_saved": "Groupes AP enregistrés.",
    "yes": "Oui",
    "help": "Aide",
    "fit": "Ajuster",
    "map": "Plan",
    "saved_network": "Réseaux pertinents",
    "relevant_networks_none": "Aucun réseau pertinent défini",
    "manage_relevant_networks": "Gérer",
    "manage_relevant_networks_title": "Gérer réseaux pertinents",
    "manage_relevant_networks_message": "Sélectionnez les SSID à traiter comme pertinents pour ce relevé. Ce choix met aussi à jour les points déjà collectés.",
    "no_relevant_networks_to_manage": "Aucun SSID détecté à gérer pour l'instant.",
    "relevant_networks_updated": "Réseaux pertinents mis à jour.",
    "forget_saved_network": "Effacer",
    "relevant_networks_cleared": "Réseaux pertinents effacés.",
    "best_dbm": "Meilleur dBm",
    "quality": "Qualité",
    "quality_good": "OK",
    "quality_missing_relevant": "Réseau manquant",
    "quality_low_confidence": "Faible confiance",
    "quality_unstable_signal": "Instable",
    "quality_sparse_data": "Rare",
    "quality_breakdown_title": "Détails qualité point",
    "rows": "Lignes",
    "survey_point_tooltip_title": "Point de mesure",
    "wifi_ap_tooltip_title": "AP Wi-Fi",
    "tooltip_signal_scope": "Scope signal",
    "tooltip_scope_relevant": "Réseaux pertinents",
    "tooltip_scope_all": "Tous réseaux",
    "tooltip_rows_relevant": "{relevant}/{total} pertinentes",
    "tooltip_time": "Heure",
    "tooltip_detected_ssids": "SSID détectés",
    "tooltip_section_location": "Position",
    "tooltip_section_signal": "Signal",
    "tooltip_section_networks": "Réseaux",
    "tooltip_section_identity": "Identité",
    "tooltip_section_radio": "Radio",
    "tooltip_section_metadata": "Métadonnées",
    "tooltip_section_position": "Position",
    "tooltip_section_analysis": "Analyse",
    "tooltip_section_reference": "Référence",
    "tooltip_section_interference": "Interférence",
    "tooltip_section_serving_ap": "AP serveur",
    "tooltip_section_interferer": "Interférent",
    "tooltip_section_dominant_ap": "AP dominant",
    "tooltip_section_second_ap": "Second AP",
    "go_to_point": "Aller au point",
    "rescan_point": "Rescanner point",
    "point_rescanned": "Point rescanné : x={x}, y={y}, anciennes lignes={rows}, nouveaux réseaux={count}.",
    "delete_selected": "Suppr. sélection",
    "delete_last": "Suppr. dernier",
    "band": "Bande",
    "all_bands_option": "Toutes",
    "map_type": "Type carte",
    "map_type_signal": "Couverture signal",
    "map_type_interference": "Interférence AP",
    "map_type_channel": "Canaux AP",
    "map_type_dominant": "AP dominant",
    "channel_map_legend_title": "Canaux AP",
    "channel_map_intermediate_24": "Canaux intermédiaires",
    "dominant_map_legend_title": "AP dominant",
    "dominant_roaming_issue_title": "Overlap roaming",
    "dominant_roaming_issue_detail": "L'AP le plus fort est dans le seuil de roaming {threshold} :\nAP dominant : {dominant} | {dominant_signal}\nAP secondaire : {second} | {second_signal}\nLes clients peuvent roamer ou osciller ici.",
    "point_labels": "Labels points",
    "point_labels_auto": "Automatique",
    "point_labels_critical": "Critiques seuls",
    "point_labels_all": "Tous",
    "point_labels_none": "Aucun",
    "reference_table_info": "Référence",
    "reference_more_in_report": "+ {count} de plus dans le rapport CSV",
    "legend_other": "Autre",
    "signal": "Signal",
    "coverage_aggregation": "Agrégation",
    "samples": "Échantillons",
    "scan_confidence": "Confiance",
    "reference_channel": "Canal",
    "reference_width": "Largeur",
    "channel_width": "Largeur canal",
    "reference_ap": "AP",
    "reference_delta": "Delta second AP",
    "reference_risk": "Risque",
    "reference_serving_channel": "Canal serveur",
    "reference_interferer_channel": "Canal interférent",
    "second_ap": "Second AP",
    "second_ap_role": "Rôle second AP",
    "second_channel": "Second canal",
    "second_signal": "Second signal",
    "second_samples": "Second échantillons",
    "second_confidence": "Seconde confiance",
    "signal_delta": "Delta signal",
    "roaming_overlap": "Overlap roaming",
    "serving_ap": "AP serveur",
    "export_signal_title": "Couverture signal Wi-Fi",
    "export_channel_title": "Canaux AP Wi-Fi",
    "export_dominant_title": "AP dominant Wi-Fi",
    "export_interference_title": "Interférence AP Wi-Fi",
    "export_signal_colorbar": "Signal estimé dBm",
    "export_points": "points",
    "export_measurements": "mesures",
    "export_roaming_overlap": "overlap roaming",
    "interference_mode": "Analyse interférence",
    "interference_mode_intra_ssid": "Intra-SSID",
    "interference_mode_all": "Tous SSID",
    "interference_colorbar": "Risque interférence %",
    "interference_legend_title": "Risque AP",
    "interference_low": "faible",
    "interference_medium": "moyen",
    "interference_high": "élevé",
    "interference_top_risk": "Risque max",
    "interference_summary_title": "Synthèse interférence",
    "interference_summary_band": "Bande",
    "interference_summary_max_risk": "Risque maximal",
    "interference_summary_point": "Point",
    "interference_summary_serving_ap": "AP serveur",
    "interference_summary_serving_role": "Rôle serveur",
    "interference_summary_serving_channel": "Canal serveur",
    "interference_summary_serving_width": "Largeur serveur",
    "interference_summary_serving_dbm": "Signal serveur",
    "interference_summary_interferer": "Interférent principal",
    "interference_summary_interferer_role": "Rôle interférent",
    "interference_summary_interferer_ssid": "SSID interférent",
    "interference_summary_interferer_channel": "Canal interférent",
    "interference_summary_interferer_width": "Largeur interférente",
    "interference_summary_interferer_dbm": "Signal interférent",
    "interference_summary_test_ignored": "AP test ignorés",
    "interference_overlap": "Overlap",
    "interference_contributors": "Interférents",
    "interference_ignored": "Ignorés",
    "interference_ignored_same_ap": "même AP",
    "interference_ignored_test_ap": "AP test",
    "interference_channel_change": "Changement canal",
    "interference_channel_change_note": "{ap} a changé de canal pendant le relevé ({channels} -> {current}) ; les cartes sensibles au canal utilisent le dernier canal {current}.",
    "interference_channel_change_manual_note": "{ap} utilise le canal d'analyse manuel {current} ; canaux observés : {channels}.",
    "interference_summary_diagnosis": "Diagnostic",
    "interference_diagnosis_low": "Le risque principal est faible : la coexistence AP ne semble pas critique ici.",
    "interference_diagnosis_same_channel_strong": "Le problème principal est un interférent fort sur le même canal que l'AP serveur.",
    "interference_diagnosis_same_channel": "Le problème principal est un AP sur le même canal que l'AP serveur.",
    "interference_diagnosis_wide_channel": "Le problème principal est l'overlap causé par des canaux larges.",
    "interference_diagnosis_strong": "Le problème principal est un interférent fort sur un canal contribuant au risque.",
    "interference_diagnosis_nearby": "Le problème principal semble être un canal voisin ou partiellement superposé.",
    "interference_quality_title": "Qualité données interférence",
    "interference_quality_width_coverage": "Largeur canal disponible : {available}/{total} points ({percent}%).",
    "interference_quality_good": "L'estimation utilise la largeur canal sur une part suffisante de points.",
    "interference_quality_warning": "La largeur canal est disponible sur peu de points : l'estimation utilise un fallback quand la donnée manque.",
    "interference_quality_warning_5ghz": "La largeur canal est disponible sur peu de points : en 5/6 GHz, l'estimation peut sous-estimer l'overlap entre canaux larges.",
    "usable_only": "Seulement >= -70 dBm",
    "survey_bounds": "Limite relevé",
    "max_distance_px": "Distance max (px)",
    "interpolation": "Interpolation",
    "interpolation_rbf": "RBF lissé",
    "interpolation_linear": "Linéaire",
    "aggregation": "Agrégation point",
    "aggregation_max": "Meilleur",
    "aggregation_mean": "Moyenne",
    "aggregation_median": "Médiane",
    "color_scale": "Échelle couleur",
    "color_scale_fixed": "Fixe",
    "color_scale_auto": "Automatique",
    "smoothing": "Lissage",
    "theme": "Thème",
    "qt_theme_light": "Bleu sable",
    "qt_theme_soft": "Olive doux",
    "qt_theme_dark": "Bleu ardoise",
    "qt_theme_contrast": "Vert graphite",
    "close": "Fermer",
    "cancel": "Annuler",
    "select_plan_title": "Sélectionner plan",
    "images": "Images",
    "load_plan_first": "Chargez d'abord un plan.",
    "warning": "Avertissement",
    "empty_csv": "Le relevé est vide.",
    "no_ssid": "Aucun SSID disponible.",
    "select_ssid_heatmap": "Sélectionnez un SSID pour exporter la carte.",
    "insufficient_data_title": "Données insuffisantes",
    "insufficient_data": "Au moins 3 points sont requis pour générer une heatmap en {band}.",
    "interference_requires_band": "Sélectionnez 2.4 GHz, 5 GHz ou 6 GHz pour la carte d'interférence.",
    "save_required_title": "Enregistrement requis",
    "save_required": "Vous devez enregistrer le CSV du relevé avant d'exporter le PDF.",
    "save_failed": "Enregistrement annulé. Heatmap non générée.",
    "heatmap_generated": "Heatmap générée",
    "file_created": "Fichier créé :\n{path}",
    "files_created": "Fichiers créés :\n{paths}",
    "unsaved_changes_title": "Relevé non enregistré",
    "unsaved_changes": "Changements non enregistrés.\n\nEnregistrer le relevé avant de quitter ?",
    "survey_saved": "Relevé enregistré : {name}",
    "best": "Meilleur",
    "confidence": "confiance",
    "connected_ssid_option": "{ssid} (connecté)",
    "relevant_networks_title": "Réseaux pertinents",
    "relevant_networks_first_message": "Sélectionnez les SSID pertinents pour ce relevé. Tous les réseaux seront enregistrés, mais ceux-ci seront contrôlés aux prochains points.",
    "new_relevant_networks_title": "Nouveaux réseaux détectés",
    "new_relevant_networks_message": "De nouveaux SSID ont été détectés. Sélectionnez ceux qui sont pertinents pour ce relevé.",
    "missing_relevant_networks_title": "Réseaux pertinents manquants",
    "missing_relevant_networks_message": "Ces réseaux pertinents n'ont pas été détectés :\n{ssids}\n\nEnregistrer quand même le point, relancer le scan ou annuler ?",
    "cancelled": "annulé",
    "no_networks_found": "Aucun réseau trouvé. Vérifiez que le Wi-Fi est activé.",
    "error": "Erreur",
    "point_saved": "Point enregistré : x={x}, y={y}, réseaux={count}",
    "scanning": "Scan Wi-Fi en cours à x={x}, y={y}...",
    "map_loaded_points": "Plan chargé. Points restaurés={count}. Relevé : {name}",
    "map_loaded": "Plan chargé. Relevé actif : {name}. Cliquez votre position.",
    "map_not_found_title": "Plan introuvable",
    "map_not_found": "Le CSV référence un plan qui n'existe plus :\n{path}\n\nSélectionnez manuellement le plan mis à jour.",
    "select_point": "Sélectionnez un point dans le tableau.",
    "no_point_to_delete": "Aucun point à supprimer dans cette session.",
    "last_point_deleted": "Dernier point supprimé : x={x}, y={y}, lignes supprimées={rows}",
    "point_deleted": "Point supprimé : x={x}, y={y}, lignes supprimées={rows}",
    "zoom": "Zoom : {zoom:.0%}",
    "survey_zoom": "Zoom relevé : {zoom:.0%}",
    "survey_zoom_empty": "Zoom relevé : -",
    "live_zoom": "Zoom carte Live : {zoom:.0%}",
    "live_zoom_empty": "Zoom carte Live : -",
    "all_bands_label": "toutes bandes",
    "help_title": "Centre d'aide",
    "help_overview_nav": "Workflow conseillé",
    "help_overview_title": "Workflow de relevé conseillé",
    "help_overview_subtitle": "Utilisez l'application comme workflow de validation : collecter, vérifier, corriger le modèle AP, puis exporter.",
    "help_controls_nav": "Contrôles",
    "help_controls_title": "Aide-mémoire contrôles",
    "help_controls_subtitle": "Le relevé utilise des gestes directs sur la carte. Ce sont les contrôles les plus fréquents.",
    "help_control_right_click_title": "Clic droit",
    "help_control_right_click_text": "Crée un point de mesure sur la carte Relevé. En mode Confins, glisser-clic droit dessine ou gomme le masque.",
    "help_control_left_click_title": "Clic gauche",
    "help_control_left_click_text": "Sélectionne un point de mesure ou utilise le mode temporaire actif, comme calibration ou placement AP.",
    "help_control_left_drag_title": "Clic gauche + glisser",
    "help_control_left_drag_text": "Déplace le plan ou la carte Live quand la vue est plus grande que la viewport.",
    "help_control_scroll_title": "Molette",
    "help_control_scroll_text": "Fait défiler listes, panneaux et vues carte verticalement.",
    "help_control_shift_title": "Shift + molette",
    "help_control_shift_text": "Déplace horizontalement le plan ou la carte Live quand le défilement horizontal est disponible.",
    "help_control_ctrl_title": "Ctrl + molette",
    "help_control_ctrl_text": "Zoome le plan ou l'aperçu de carte Live.",
    "help_survey_nav": "Relevé et scans",
    "help_survey_title": "Points, scans bruts et confiance",
    "help_survey_subtitle": "Un point est plus qu'une valeur de signal : l'app stocke les échantillons bruts et suit la confiance.",
    "help_quality_nav": "Qualité relevé",
    "help_quality_title": "Dashboard qualité relevé",
    "help_quality_subtitle": "Le dashboard sépare évidence de scan, diagnostic modèle AP et points à revoir avant de faire confiance aux cartes.",
    "help_ap_groups_nav": "Groupes AP",
    "help_ap_groups_title": "Groupes AP, rôles et métadonnées",
    "help_ap_groups_subtitle": "AP Group Manager transforme les BSSID bruts en modèle d'AP physique utilisé par cartes et contrôles qualité.",
    "help_live_maps_nav": "Cartes Live",
    "help_live_maps_title": "Cartes Live et options",
    "help_live_maps_subtitle": "La Carte Live est la surface principale de révision après contrôles qualité et modèle AP.",
    "help_reports_nav": "Rapports PDF",
    "help_reports_title": "Rapports PDF Live",
    "help_reports_subtitle": "L'export PDF capture les options de carte Live et ajoute des pages diagnostic quand le type de carte le supporte.",
    "help_diagnostics_nav": "Avertissements",
    "help_diagnostics_title": "Avertissements et diagnostics",
    "help_diagnostics_subtitle": "Les avertissements invitent à vérifier les hypothèses ; ils ne prouvent pas automatiquement qu'un point est faux.",
    "help_glossary_nav": "Glossaire",
    "help_glossary_title": "Glossaire",
    "help_glossary_subtitle": "Termes utilisés par le workflow de relevé et les rapports.",
    "help_legal_nav": "À propos et légal",
    "help_legal_title": "À propos, licence et usage responsable",
    "help_legal_subtitle": "Identité application, licence projet, notes tierces et limites d'usage prévu.",
    "help_overview_body": """
        <table class="callout-table"><tr><td class="callout-accent-good"></td><td class="callout-content"><span class="callout-label">Règle principale</span><br>Ne faites confiance à une carte que lorsque les données du relevé et le modèle AP sont assez cohérents.</td></tr></table>
        <h2>Workflow</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>1. Préparer</b><br>Créez ou ouvrez un relevé, choisissez les unités, chargez le plan et calibrez l'échelle.</td><td class="workflow-gap"></td><td class="workflow-card"><b>2. Mesurer</b><br>Placez les points là où les clients travaillent ou roament. Collectez plusieurs scans par point.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>3. Valider</b><br>Contrôlez Qualité relevé, réseaux pertinents, AP Memory, rôles, métadonnées et positions AP.</td><td class="workflow-gap"></td><td class="workflow-card"><b>4. Exporter</b><br>Lisez les cartes Live et exportez le rapport HTML seulement après validation des données.</td></tr></table>
        <h2>Points de décision</h2>
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Ordre conseillé</span><br>Corrigez d'abord les points à rescanner, puis le modèle AP, puis les cartes. Les warnings sont des hypothèses à vérifier, pas des erreurs automatiques.</td></tr></table>
    """,
    "help_controls_body": """
        <h2>Gestes carte</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>Clic droit</b><br>Ajoute un point de mesure. En mode Confins, glisser-clic droit dessine ou gomme le masque.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Clic gauche</b><br>Sélectionne un marqueur ou exécute le mode temporaire actif, par exemple calibration ou position AP.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Glisser</b><br>Déplace le plan ou la carte Live quand la vue dépasse la viewport.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Molette</b><br>Défilement vertical ; Shift + molette pour horizontal ; Ctrl + molette pour zoom.</td></tr></table>
        <h2>Overlays</h2>
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Grille et Confins</span><br>Grille et Confins sont des overlays alternatifs. L'échelle calibrée reste commune.</td></tr></table>
    """,
    "help_survey_body": """
        <h2>Fichiers du relevé</h2>
        <table class="survey-grid"><tr><td class="survey-card"><span class="survey-card-title">CSV</span><br>Données agrégées et métadonnées.</td><td class="survey-gap"></td><td class="survey-card"><span class="survey-card-title">.scan</span><br>Échantillons bruts répétés.</td><td class="survey-gap"></td><td class="survey-card"><span class="survey-card-title">Plan</span><br>PDF/image ou plan généré.</td></tr></table>
        <h2>Collecte</h2>
        <p>Placez les points dans les zones réellement utilisées : bureaux, salles, couloirs, portes et zones de problème. Pour un relevé précis, visez environ 2-3 m entre points quand l'espace le permet.</p>
        <h2>Réseaux pertinents</h2>
        <p>Les SSID pertinents pilotent les contrôles qualité, les cartes Live et les rapports. Tous les réseaux sont conservés, mais seuls les pertinents définissent les attentes du relevé.</p>
    """,
    "help_quality_body": """
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Lire avant les cartes</span><br>Qualité relevé indique si les points, le scanner ou le modèle AP doivent être corrigés avant interprétation.</td></tr></table>
        <h2>KPI</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>Points</b><br>Réseaux manquants, données rares, faible confiance, signal instable ou roaming client.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Modèle AP</b><br>Mémoire AP, positions, métadonnées, changements canal et findings AP dominant.</td></tr></table>
        <h2>Actions</h2>
        <p>Les cartes KPI ouvrent des listes de points ou Extra Details. Utilisez Aller au point, Ouvrir groupe AP ou Ouvrir métadonnées AP pour corriger l'élément concerné.</p>
    """,
    "help_ap_groups_body": """
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Règle modèle AP</span><br>Le programme peut suggérer des groupes, mais le modèle final doit représenter les AP physiques réels.</td></tr></table>
        <h2>Groupes AP</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>Évidence</b><br>BSSID, SSID, bandes, canaux et historique signal décrivent ce qui est observé.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Modèle utilisateur</b><br>Alias, rôle, position, métadonnées et overrides décrivent le déploiement attendu.</td></tr></table>
        <h2>Gestionnaire BSSID</h2>
        <p>Utilisez filtres de scope, bande, canal et recherche pour isoler les BSSID à déplacer, séparer ou confirmer.</p>
        <h2>Métadonnées</h2>
        <p>Vendor, modèle, montage, bandes/canaux attendus et override de canal d'analyse améliorent les diagnostics et les rapports.</p>
    """,
    "help_live_maps_body": """
        <h2>Types de carte</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>Couverture</b><br>Signal estimé en dBm pour un SSID et une bande.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Interférence</b><br>Risque lié aux canaux, largeurs et AP interférents.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Canaux AP</b><br>Vue discrète des canaux observés.</td><td class="workflow-gap"></td><td class="workflow-card"><b>AP dominant</b><br>AP le plus fort et zones de roaming potentiel.</td></tr></table>
        <h2>Options</h2>
        <p>SSID, bande, type carte, labels, interpolation, lissage, distance max, groupe AP et Survey Bounds sont mémorisés par type de carte pendant la session.</p>
        <h2>Confins</h2>
        <p>Si un masque Confins existe, il remplace la limite automatique pour les cartes continues et les exports HTML supportés.</p>
    """,
    "help_reports_body": """
        <h2>Export PDF</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>Précondition</b><br>Le relevé doit être enregistré avant export.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Options actives</b><br>Le PDF utilise l'état courant de la carte Live : SSID, bande, type carte, couleurs, labels et limites.</td></tr></table>
        <h2>Page carte</h2>
        <p>La première page rend la carte sur le plan indépendamment du zoom/pan courant. L'espace de fond uniforme peut être coupé si aucun point ou AP ne l'utilise.</p>
        <h2>Pages diagnostic</h2>
        <p>Interférence et AP dominant peuvent ajouter des pages de problèmes avec callouts numérotés et cartes de détail.</p>
    """,
    "help_diagnostics_body": """
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Règle warning</span><br>Un warning indique une hypothèse à vérifier : scan, modèle AP, canal, position ou comportement RF réel.</td></tr></table>
        <h2>Patterns fréquents</h2>
        <p>Réseau pertinent absent, confiance faible, signal instable, détails scanner limités, AP sans position, métadonnées incohérentes ou canal changé.</p>
        <h2>Priorité</h2>
        <p>Corrigez les problèmes de points avant les problèmes de modèle, puis relisez les cartes Live et les HTML.</p>
    """,
    "help_glossary_body": """
        <h2>Évidence Wi-Fi</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>SSID</b><br>Nom du réseau Wi-Fi.</td><td class="workflow-gap"></td><td class="workflow-card"><b>BSSID</b><br>Adresse MAC radio vue dans les scans.</td></tr></table>
        <h2>Modèle AP</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>Groupe AP</b><br>Modèle d'un AP physique, souvent avec plusieurs BSSID.</td><td class="workflow-gap"></td><td class="workflow-card"><b>AP dominant</b><br>Groupe AP avec le signal observé le plus fort au point.</td></tr></table>
        <h2>Cartes et rapports</h2>
        <p>Interpolation, distance max, Survey Bounds et masque Confins contrôlent où et comment le rendu visuel s'étend entre les mesures réelles.</p>
    """,
    "help_legal_body": """
        <h2>Application</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>Produit</b><br>Wi-Fi RF Survey Analyzer</td><td class="workflow-card"><b>Version</b><br>{version}</td></tr><tr><td class="workflow-vertical-gap" colspan="2"></td></tr><tr><td class="workflow-card"><b>Copyright</b><br>{copyright}</td><td class="workflow-card"><b>Licence</b><br>{license_name} (<code>{license_id}</code>)<br>{license_url}</td></tr></table>
        <h2>Usage responsable</h2>
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Réseaux autorisés uniquement</span><br>Ce logiciel est destiné à l'analyse, au relevé et au troubleshooting Wi-Fi légitimes sur des réseaux que vous possédez ou êtes autorisé à évaluer.</td></tr></table>
        <h2>Composants tiers</h2>
        <p>Voir <code>THIRD_PARTY_LICENSES</code> pour les licences des dépendances.</p>
    """,
    "help_commands": "Commandes",
    "help_workflow": "Workflow",
    "help_workflow_title": "Comment utiliser le programme",
    "help_live": "Carte Live",
    "help_live_title": "Comment utiliser la carte Live",
    "help_heatmap": "Heatmap",
    "help_heatmap_title": "Comment lire et générer la heatmap",
    "help_scan": "Scan",
    "help_scan_title": "Comment gérer les scans Wi-Fi",
    "keep_scan": "Garder scan",
    "retry_scan": "Réessayer",
    "cancel_point": "Annuler point",
})

TRANSLATIONS.update({
    "start_workflow_title": "Processus",
    "workspace_settings_section": "Espace de travail",
    "quality_dashboard_metric_scan_ok": "Scans OK",
    "quality_dashboard_metric_ap_diagnostic_points": "Constats AP dominant",
    "quality_dashboard_ap_position_finding": "Constat : {finding}",
    "quality_dashboard_scanner_details_fallback_suffix": " (repli)",
    "boundaries": "Limites",
    "boundaries_enabled": "Mode Limites activé.",
    "boundaries_disabled": "Mode Limites désactivé.",
    "boundaries_draw_tooltip": "Glisser-clic droit pour dessiner le masque",
    "boundaries_eraser_tooltip": "Glisser-clic droit pour gommer le masque",
    "boundaries_brush_size_tooltip": "Taille de brosse Limites",
    "boundaries_brush_size_value_tooltip": "Taille brosse : {size} px ({minimum}-{maximum} px, pas {step} px)",
    "boundaries_clear_tooltip": "Effacer le masque Limites",
    "boundaries_clear_title": "Effacer les limites ?",
    "boundaries_clear_confirm": "Effacer le masque de limites actuel ?",
    "boundaries_cleared": "Masque de limites effacé.",
    "boundaries_save_failed": "Impossible d'enregistrer le masque de limites : {path}",
    "boundaries_cleanup_failed": "Impossible de supprimer le masque de limites remplacé : {path}",
    "max_distance_unit": "Distance max ({unit})",
    "max_distance_m": "Distance max (m)",
    "ap_group_bssid_other_group": "Autre groupe",
    "ap_group_bssid_scope_all": "Tous",
    "ap_group_empty_selection": "Le groupe doit contenir au moins un BSSID.",
    "ap_group_split_source_empty": "Laissez au moins un BSSID dans le groupe actuel avant de créer un nouveau groupe.",
    "ap_group_move_no_target": "Aucun autre groupe AP n'est disponible pour déplacer les BSSID sélectionnés.",
    "ap_group_move_target_title": "Déplacer des BSSID",
    "ap_group_move_target_prompt": "Groupe AP cible :",
    "ap_group_move_target_with_alias": "{alias} ({group}, {count} BSSID)",
    "ap_group_move_target_without_alias": "{group} ({count} BSSID)",
    "ap_group_fix_from_warning": "Corriger groupe AP",
    "ap_group_conflict_count": "Conflits possibles : {count}",
    "ap_group_conflict_details": "Détails de l'avertissement",
    "ap_group_conflict_none": "Aucun avertissement sur le groupe sélectionné.",
    "ap_group_conflict_group": "Groupe AP : {group}",
    "ap_group_conflict_details_title": "Canaux observés",
    "ap_group_conflict_band_summary": "{band} : {channel_count} canaux, {bssid_count} BSSID ({channels})",
    "ap_group_conflict_band_row": "Bande {band} : canaux {channels}",
    "ap_group_memory_menu": "Mémoire",
    "ap_group_confirm_memory": "Confirmer mémoire",
    "ap_group_confirm_memory_selected": "Confirmer sélection",
    "ap_group_confirm_memory_all": "Confirmer tout depuis la mémoire...",
    "ap_group_confirm_memory_all_title": "Confirmer mémoire AP",
    "ap_group_confirm_memory_all_confirm": "Confirmer {count} groupes AP appliqués depuis la Mémoire AP ?",
    "ap_group_update_from_memory": "Mettre à jour depuis la mémoire",
    "ap_group_update_memory_selected": "Mettre à jour la sélection depuis la mémoire",
    "ap_group_status_warning_tooltip": "Ce groupe AP contient des diagnostics d'avertissement.",
    "ap_group_status_memory_tooltip": "Des métadonnées ont été appliquées depuis la Mémoire AP. Vérifiez-les puis confirmez-les, ou modifiez les données AP.",
    "ap_group_status_memory_update_tooltip": "La Mémoire AP contient des données différentes pour : {fields}. Utilisez Mettre à jour depuis la mémoire pour aligner ce groupe AP.",
    "ap_group_delete_alias": "Supprimer alias...",
    "ap_group_role": "Rôle",
    "ap_group_role_title": "Rôle du groupe AP",
    "ap_group_role_prompt": "Rôle à attribuer à ce groupe AP :",
    "ap_group_role_internal": "Interne",
    "ap_group_role_external": "Externe",
    "ap_group_role_interferer": "Interférent",
    "ap_group_role_test": "Test/masqué",
    "ap_group_metadata": "Métadonnées",
    "ap_group_metadata_hint": "Ajoutez les informations descriptives de l'AP physique. Les bandes et canaux attendus sont guidés car les contrôles qualité les utilisent.",
    "ap_group_metadata_vendor": "Fabricant",
    "ap_group_metadata_model": "Modèle",
    "ap_group_metadata_mounting": "Montage",
    "ap_group_metadata_expected_bands": "Bandes attendues",
    "ap_group_metadata_expected_channels": "Canaux attendus",
    "ap_group_metadata_band": "Bande",
    "ap_group_metadata_channels": "Canaux",
    "ap_group_metadata_selected_channels": "Sélection active",
    "ap_group_metadata_edit_channels": "Canaux...",
    "ap_group_metadata_channel_picker_title": "Canaux {band}",
    "ap_group_metadata_no_channels": "Aucun canal sélectionné",
    "ap_group_metadata_band_disabled": "Bande non sélectionnée",
    "ap_group_metadata_channels_unavailable": "Canaux indisponibles",
    "ap_group_metadata_channel_group_5_low": "5 GHz bas",
    "ap_group_metadata_channel_group_5_high": "5 GHz haut",
    "ap_group_metadata_select_all": "Tous",
    "ap_group_metadata_clear": "Aucun",
    "ap_group_metadata_analysis_channels": "Canal d'analyse forcé",
    "ap_group_metadata_analysis_channel_hint": "Utilisé par les cartes sensibles au canal quand cet AP a changé de canal pendant le relevé. Laissez Auto pour utiliser le dernier canal propre.",
    "ap_group_metadata_analysis_channel": "Canal d'analyse",
    "ap_group_metadata_analysis_channel_not_observed": "Non observé",
    "ap_group_metadata_coverage_scope": "Périmètre de couverture",
    "ap_group_metadata_coverage_expected_area": "Zone attendue",
    "ap_group_metadata_coverage_site_wide": "Site complet",
    "ap_group_metadata_coverage_local": "Zone locale",
    "ap_group_metadata_coverage_radius": "Rayon local",
    "ap_group_metadata_coverage_auto_area": "Zone auto",
    "ap_group_metadata_coverage_hint": "Choisissez si cet AP est attendu sur tout le relevé ou seulement près de sa zone locale.",
    "ap_group_metadata_coverage_site_wide_hint": "Les contrôles qualité traitent cet AP/réseau comme présent dans toute la zone relevée.",
    "ap_group_metadata_coverage_local_hint": "Les contrôles qualité peuvent limiter cet AP/réseau à sa zone locale. Zone auto fonctionne mieux avec position AP et échelle calibrée ; sinon elle se base sur l'évidence de signal.",
    "ap_group_metadata_notes": "Notes",
    "ap_group_position": "Position",
    "ap_group_position_tooltip_title": "Position AP",
    "ap_position_pick": "Clic gauche sur le plan pour placer la position physique de {group}. Échap annule.",
    "ap_position_saved": "Position AP enregistrée : {group} x={x}, y={y}.",
    "ap_position_cancelled": "Placement AP annulé.",
    "ap_position_distance": "Distance AP",
    "ap_position_nearest": "AP physique le plus proche",
    "ap_position_analysis": "Analyse de position",
    "ap_position_detail": "Détail position",
    "ap_position_ok": "Cohérent",
    "ap_position_no_scale": "Échelle non calibrée",
    "ap_position_strong_far": "Signal fort loin de l'AP",
    "ap_position_weak_close": "Signal faible près de l'AP",
    "ap_position_unexpected_dominant": "L'AP dominant n'est pas physiquement proche",
    "ap_position_warning_legend": "Triangle = position AP suspecte",
    "ap_position_unknown_warning": "Avertissement position",
    "ap_group_not_found": "Groupe AP introuvable.",
    "ap_group_alias_title": "Alias du groupe AP",
    "ap_group_alias_prompt": "Alias à utiliser pour cet AP :",
    "help_workflow": "Processus",
    "help_heatmap": "Carte de chaleur",
    "help_workflow_steps": (
        "1-a. Créez un nouveau relevé et chargez le plan.\n"
        "1-b. Ou ouvrez un relevé enregistré : le plan sera rechargé automatiquement.\n"
        "2. Déplacez-vous physiquement dans la zone et utilisez le clic droit sur la carte pour enregistrer les points de mesure.\n"
        "3. Utilisez Groupes AP pour attribuer les alias, corriger les groupes et placer les positions physiques des AP quand elles sont connues.\n"
        "4. Enregistrez le relevé après avoir collecté assez de points.\n"
        "5. Ouvrez la Carte Live et choisissez SSID, bande Wi-Fi et type d'analyse.\n"
        "6. Utilisez Couverture signal pour le niveau dBm, Interférence AP pour les recouvrements, Canaux AP pour les canaux et AP dominant pour le roaming."
    ),
    "help_live_steps": (
        "La Carte Live affiche un aperçu du relevé et exporte la vue courante en HTML.\n"
        "Choisissez SSID, bande et type de carte directement dans l'onglet Carte Live.\n"
        "Couverture signal et Interférence AP sont calculées en arrière-plan pour garder l'interface utilisable.\n"
        "Canaux AP et AP dominant montrent les points réels avec leur légende.\n"
        "Dans AP dominant, un triangle jaune marque un possible avertissement de position AP : le tooltip indique la distance à l'AP dominant et à l'AP physique le plus proche.\n"
        "Le zoom Live ne régénère pas la carte : il redimensionne l'aperçu puis affine la qualité après une courte pause."
    ),
    "help_heatmap_steps": (
        "Couverture signal génère une carte de chaleur dBm continue par SSID et bande.\n"
        "RBF lissé donne une visualisation plus continue ; Linéaire est plus conservateur.\n"
        "Distance max limite le rendu aux zones proches des points réels et réduit les formes inventées.\n"
        "Seulement >= -70 dBm met en évidence les zones normalement utilisables.\n"
        "Interférence AP calcule un risque en pourcentage et ajoute les principaux problèmes au HTML.\n"
        "Canaux AP n'interpole pas : il colore les points réels par canal, avec CH 36 / 80 quand la largeur est disponible.\n"
        "AP dominant montre l'AP le plus fort par point et marque en jaune les points où le second AP est à 5 dB ou moins."
    ),
    "help_scan_steps": (
        "Nouveau relevé enregistre la carte choisie ; chaque mesure l'utilise via lswifi.\n"
        "lswifi est préféré car il détecte souvent plus de BSSID et plus de détails radio.\n"
        "Quand lswifi le fournit, la largeur de canal est enregistrée dans channel_width_mhz.\n"
        "Si la carte manque, la mesure s'arrête sans changer de carte ni passer à netsh.\n"
        "Si un scan voit beaucoup moins de réseaux que le précédent, il est marqué suspect.\n"
        "Quand un scan est suspect, relancez-le avant d'enregistrer le point.\n"
        "Avec Mémoriser le choix, le programme garde automatiquement le même SSID tant qu'il est détecté."
    ),
    "help_commands_text": (
        "Clic droit sur la carte : crée un point de relevé ; en mode Limites, glisser-clic droit dessine ou gomme le masque.\n"
        "Maintenir clic gauche : déplace la carte.\n"
        "Clic gauche sur un marqueur : sélectionne le point.\n"
        "Molette : défilement vertical.\n"
        "Shift + molette : défilement horizontal.\n"
        "Ctrl + molette : zoom."
    ),
    "help_overview_body": """
        <table class="callout-table"><tr><td class="callout-accent-good"></td><td class="callout-content"><span class="callout-label">Règle principale</span><br>La carte est la sortie finale du relevé, pas la première preuve. Avant de l'utiliser pour décider, vérifiez que les points, les scans bruts et le modèle AP décrivent correctement le site.</td></tr></table>
        <h2>Séquence opérationnelle</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr><td class="workflow-card"><div class="step-label">1. Préparer</div><div class="step-title">Définir le cadre du relevé</div><p>Créez ou ouvrez le relevé, choisissez métrique ou impérial, chargez le plan si disponible, calibrez l'échelle et sélectionnez les SSID pertinents.</p><div class="step-gate"><b>Passer à la suite quand :</b> plan, échelle et réseaux à juger sont corrects.</div></td><td class="workflow-gap"></td><td class="workflow-card"><div class="step-label">2. Mesurer</div><div class="step-title">Collecter l'évidence RF</div><p>Placez les points dans les pièces, couloirs, zones de transition, portes et emplacements où les utilisateurs signalent des problèmes.</p><div class="step-gate"><b>Passer à la suite quand :</b> les zones importantes ont assez de points et les scans suspects ont été répétés.</div></td></tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr><td class="workflow-card"><div class="step-label">3. Valider</div><div class="step-title">Lire Qualité relevé</div><p>Séparez les problèmes de point à rescanner des diagnostics de configuration AP. Un avertissement est une hypothèse à vérifier, pas une erreur automatique.</p><div class="step-gate"><b>Passer à la suite quand :</b> la qualité des points est acceptable et les constats restants sont compris.</div></td><td class="workflow-gap"></td><td class="workflow-card"><div class="step-label">4. Modéliser les AP</div><div class="step-title">Rendre le modèle crédible</div><p>Vérifiez groupes AP, alias, rôles, BSSID, métadonnées, positions physiques, canaux d'analyse forcés et états Mémoire AP.</p><div class="step-gate"><b>Passer à la suite quand :</b> le modèle AP correspond au déploiement ou que les inconnues sont assumées.</div></td></tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr><td class="workflow-card" colspan="3"><div class="step-label">5. Analyser</div><div class="step-title">Utiliser les cartes comme résultat contrôlé</div><p>Ouvrez les cartes Live et les exports HTML pour lire couverture, canaux, roaming et interférences après la revue des données.</p><div class="step-gate"><b>Passer à la suite quand :</b> les avertissements ont été relus et peuvent être expliqués.</div></td></tr>
        </table>
        <h2>Portes de décision</h2>
        <div class="gate-list">
            <div class="gate-row"><b>Distances :</b> le système de mesure est lié au relevé. Changer d'unités après calibration supprime l'échelle ; recalibrez avant de lire distances, grille ou positions AP.</div>
            <div class="gate-row"><b>Couverture :</b> contrôlez SSID pertinents et qualité des points avant d'interpréter une zone rouge ou verte.</div>
            <div class="gate-row"><b>Interférences :</b> vérifiez groupes AP, rôles, canaux changés et overrides d'analyse avant de croire une carte sensible au canal.</div>
            <div class="gate-row"><b>Export :</b> ouvrez la carte Live correspondante, lisez les tooltips et les détails avant de générer le rapport HTML.</div>
        </div>
        <table class="section-card callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Logique de l'application</span><br>Points, scans bruts, métadonnées, Mémoire AP et positions physiques sont traités comme des éléments d'évidence. Le programme signale l'hypothèse à vérifier : qualité de point, groupement AP, modèle canal, position physique ou comportement RF réel.</td></tr></table>
    """,
    "help_controls_body": """
        <table class="callout-table" width="100%" cellspacing="0" cellpadding="0"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Règle des gestes</span><br>Clic gauche, glisser-clic gauche et molette avec modificateurs sont des commandes distinctes. Ctrl et Shift comptent quand ils sont combinés à la molette.</td></tr></table>
        <h2>Le contexte compte</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr><td class="workflow-card"><b>Carte relevé normale</b><br>Le clic droit crée un point de mesure. Le clic gauche sélectionne un marqueur existant ou efface la sélection si vous cliquez le fond.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Modes temporaires</b><br>Calibration d'échelle et placement AP capturent le clic gauche jusqu'à la fin de l'action ou annulation.</td></tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr><td class="workflow-card"><b>Mode Limites</b><br>Vue &gt; Limites transforme la carte Relevé en éditeur de masque. Le glisser-clic droit dessine ou gomme avec la brosse choisie ; sélection, zoom et pan restent disponibles.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Grille et Limites</b><br>Ce sont deux overlays alternatifs : activer l'un désactive l'autre. L'échelle calibrée reste commune aux deux.</td></tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr><td class="workflow-card"><b>Glisser n'est pas cliquer</b><br>Un clic sélectionne ; un glisser déplace le plan ou la carte Live quand la vue dépasse la fenêtre.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Zoom/pan sont visuels</b><br>Zoomer, défiler ou déplacer la vue ne modifie ni les points ni les scans enregistrés.</td></tr>
        </table>
        <h2>Molette et navigation</h2>
        <table class="gate-list">
            <tr><td class="gate-row"><b>Molette :</b> défilement vertical dans listes, panneaux et cartes.</td></tr>
            <tr><td class="gate-row"><b>Shift + molette :</b> déplacement horizontal quand le contenu dépasse la largeur visible.</td></tr>
            <tr><td class="gate-row"><b>Ctrl + molette :</b> zoom du plan ou de l'aperçu Live. Le zoom Live redimensionne l'image et affine la qualité après une courte pause, sans recalculer les données.</td></tr>
        </table>
    """,
    "help_survey_body": """
        <h2>Blocs de l'écran Relevé</h2>
        <table class="survey-grid">
            <tr><td class="survey-card"><span class="survey-card-title">CSV</span><br>Fichier principal du relevé avec lignes agrégées et commentaires de métadonnées.<br><span class="survey-card-use">À enregistrer avant export HTML ou transfert de machine.</span></td><td class="survey-gap"></td><td class="survey-card"><span class="survey-card-title">Plan</span><br>Fichier PDF/image lié au relevé. Un nouveau relevé peut commencer avec un plan blanc déjà à l'échelle.<br><span class="survey-card-use">Si aucun plan réel n'est chargé, une image PNG du même nom est écrite près du CSV.</span></td><td class="survey-gap"></td><td class="survey-card"><span class="survey-card-title">Points</span><br>Positions de mesure placées sur le plan.<br><span class="survey-card-use">Ajoutez-les là où les clients travaillent, roament ou signalent un problème.</span></td></tr>
            <tr><td class="survey-vertical-gap" colspan="5"></td></tr>
            <tr><td class="survey-card"><span class="survey-card-title">Scans bruts</span><br>Échantillons répétés conservés dans le sidecar <code>.scan</code>.<br><span class="survey-card-use">Plus d'évidence brute améliore confiance et diagnostics.</span></td><td class="survey-gap"></td><td class="survey-card"><span class="survey-card-title">Groupes AP</span><br>Modèle d'AP physiques utilisé par cartes et qualité.<br><span class="survey-card-use">À revoir avant AP dominant, Interférence ou Canaux AP.</span></td><td class="survey-gap"></td><td class="survey-card"><span class="survey-card-title">SSID pertinents</span><br>Réseaux jugés importants par les contrôles qualité.<br><span class="survey-card-use">Gérer ajoute ou retire des SSID ; Effacer supprime la sélection.</span></td></tr>
        </table>
        <h2>Ce qui est enregistré</h2>
        <p>Chaque point peut contenir plusieurs réseaux observés. Le CSV principal stocke les lignes agrégées utilisées par les cartes. Le fichier <code>.scan</code> lié conserve les échantillons répétés, le backend scanner et les détails radio disponibles.</p>
        <h2>SSID pertinents</h2>
        <p>Les SSID pertinents indiquent au moteur qualité quels réseaux doivent être présents. L'absence d'un réseau pertinent devient un constat de qualité ; l'absence d'un voisin non pertinent ne l'est pas forcément. Définissez-les tôt pour éviter de découvrir trop tard que des points doivent être revus.</p>
        <h2>Sidecar de scans bruts</h2>
        <table><tr><th>Valeur stockée</th><th>Pourquoi c'est utile</th></tr><tr><td>Médiane dBm</td><td>Réduit l'effet d'un pic temporaire de signal.</td></tr><tr><td>Min/max dBm</td><td>Montre l'amplitude de variation pendant les scans répétés.</td></tr><tr><td>Échantillons vus/total</td><td>Alimente confiance et détection de données rares.</td></tr><tr><td>Bande, fréquence, largeur canal</td><td>Améliore Canaux AP, Interférence et lecture 6 GHz.</td></tr></table>
        <h2>Backend scanner</h2>
        <table><tr><th>Backend</th><th>Usage</th><th>Notes</th></tr><tr><td>Mesure du relevé</td><td>Carte fixe</td><td>Utilise <code>lswifi</code> avec l'identifiant de la carte enregistrée. Si elle manque, la mesure s'arrête.</td></tr><tr><td>lswifi</td><td>Scanner préféré</td><td>Capture souvent plus de BSSID, bande, fréquence, sécurité et largeur canal.</td></tr><tr><td>netsh</td><td>Données anciennes / diagnostic</td><td>Instantané non vérifié avec dBm estimés. Aucun repli vers netsh pour les relevés à carte fixe.</td></tr></table>
        <h2>Placement des points</h2>
        <table class="callout-table"><tr><td class="callout-accent-good"></td><td class="callout-content"><span class="callout-label">Règle terrain</span><br><ul><li>Placez les points aux postes, salles, couloirs, portes et zones problématiques.</li><li>Pour un relevé précis, visez environ 2-3 m entre points quand l'espace le permet, et resserrez autour des transitions AP.</li><li>Ne scannez pas en marchant : arrêtez-vous, laissez finir le scan, puis avancez.</li></ul></td></tr></table>
        <h2>Plan blanc, grille et limites</h2>
        <p>Un relevé peut commencer sans plan externe. Le choix métrique/impérial crée un blanc pré-échelonné, avec grille activée. Sur plan réel, la grille devient disponible après calibration. Vue &gt; Limites permet de dessiner un masque PNG <code>&lt;survey&gt;.boundaries.png</code> avec brosse ronde ou carrée de 20 à 120 px. Un masque vide équivaut à aucun masque.</p>
    """,
    "help_quality_body": """
        <table class="callout-table" width="100%" cellspacing="0" cellpadding="0"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Règle principale</span><br>Lisez Qualité relevé avant les cartes Live ou les HTML. Le tableau de bord indique si l'évidence de point doit être rescannée, si le modèle AP doit être revu ou si les cartes peuvent être générées avec une confiance raisonnable.</td></tr></table>
        <h2>Deux couches de lecture</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr><td class="workflow-card"><div class="step-label">Couche 1</div><div class="step-title">Qualité des points</div><p>Réseaux pertinents manquants, données rares, détails scanner limités, faible confiance et signal instable concernent l'évidence du point.</p><div class="step-gate"><b>Action habituelle :</b> focaliser le point, inspecter les lignes, rescanner ou collecter des points proches.</div></td><td class="workflow-gap"></td><td class="workflow-card"><div class="step-label">Couche 2</div><div class="step-title">Modèle AP</div><p>Groupes AP, rôles, métadonnées, état mémoire, changements de canal et positions physiques expliquent comment interpréter les mesures.</p><div class="step-gate"><b>Action habituelle :</b> ouvrir la carte, les métadonnées ou le gestionnaire AP concerné et corriger le modèle.</div></td></tr>
        </table>
        <h2>Statut et périmètre</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Statut haut</b><br>Cohérent signifie que les contrôles principaux sont propres. Révision recommandée indique un ou plusieurs points à vérifier. Setup AP à vérifier signifie que les points peuvent être utilisables mais que métadonnées, mémoire, canaux ou positions AP demandent revue.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Périmètre du relevé</b><br>Le bloc de contexte rappelle les SSID pertinents, les positions AP connues et les AP de test exclus. Les AP en Zone locale ne sont attendus que dans leur périmètre local.</td></tr></table>
        <h2>Cartes KPI et détails</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr><td class="workflow-card"><b>Listes de points</b><br>Points à revoir, réseaux manquants, données rares, faible confiance, signal instable et roaming client ouvrent des listes compactes avec numéro, X/Y et problème spécifique.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Détails extra</b><br>Détails scanner, constats AP dominant, avertissements config AP, changements canal, Mémoire AP et AP sans position ouvrent des cartes plus détaillées.</td></tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr><td class="workflow-card"><b>Actions carte</b><br>Canaux AP, Interférence et AP dominant ouvrent la carte Live avec bande, groupe AP ou point pertinent quand le constat possède un contexte visuel.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Actions modèle AP</b><br>Ouvrir groupe AP ou Métadonnées AP amène directement à l'éditeur capable de corriger le modèle.</td></tr>
        </table>
        <h2>Signification des KPI</h2>
        <table class="survey-grid"><tr><td class="survey-card"><b>Points du relevé</b><br>Total points mesure l'évidence spatiale. Scan OK indique les points utilisables. Points à revoir ne veut pas dire tout rescanner : certains demandent seulement une revue AP ou position.</td><td class="survey-gap"></td><td class="survey-card"><b>Qualité scan</b><br>Réseau pertinent manquant, données rares, détails scanner limités, faible confiance et signal instable peuvent affaiblir toutes les cartes.</td><td class="survey-gap"></td><td class="survey-card"><b>Modèle AP</b><br>Mémoire AP, positions manquantes, métadonnées incohérentes, canaux changés et constats AP dominant influencent surtout AP dominant, Canaux AP, Interférence et HTML.</td></tr></table>
        <h2>Ordre de correction</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>1. Corriger l'évidence de point</b><br>Rescannez ou ajoutez des points si les données brutes ne sont pas fiables.</td></tr><tr><td class="gate-row"><b>2. Corriger identité et position AP</b><br>Alias, rôles, groupes BSSID et coordonnées AP doivent représenter le déploiement réel.</td></tr><tr><td class="gate-row"><b>3. Corriger métadonnées et canaux</b><br>Bandes/canaux attendus et override d'analyse décident si un warning est une erreur ou un comportement prévu.</td></tr><tr><td class="gate-row"><b>4. Lire les cartes</b><br>Interprétez couverture, roaming et interférences seulement après ces contrôles.</td></tr></table>
    """,
    "help_ap_groups_body": """
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Règle du modèle AP</span><br>Le regroupement automatique est une hypothèse. Le modèle final doit représenter les AP physiques réels, avec leurs BSSID, rôles, positions et métadonnées.</td></tr></table>
        <h2>Deux types d'information</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Évidence observée</b><br>BSSID, SSID vus, bandes, canaux, largeur canal et historique de signal proviennent des scans.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Modèle utilisateur</b><br>Alias, rôle, position, métadonnées, périmètre de couverture et canal d'analyse décrivent ce que vous savez du déploiement.</td></tr></table>
        <h2>Gestionnaire BSSID</h2>
        <p>Utilisez les filtres de périmètre, bande, canal, état et recherche pour isoler les BSSID à corriger. Déplacer des lignes retire automatiquement les BSSID d'un autre groupe. Créer un nouveau groupe est utile quand deux radios ont été fusionnées à tort.</p>
        <h2>Rôles AP</h2>
        <table class="survey-grid"><tr><td class="survey-card"><b>Interne</b><br>AP normal du réseau analysé. Utilisé pour couverture, AP dominant et interférence.</td><td class="survey-gap"></td><td class="survey-card"><b>Externe</b><br>AP voisin ou tiers. Peut contribuer à l'interférence, mais n'est pas attendu comme couverture interne.</td><td class="survey-gap"></td><td class="survey-card"><b>Test/masqué</b><br>AP à ignorer dans les cartes et diagnostics principaux, par exemple laboratoire ou SSID temporaire.</td></tr></table>
        <h2>Métadonnées AP</h2>
        <p>Fabricant, modèle, montage, notes, bandes attendues et canaux attendus enrichissent les diagnostics. Si un AP change de canal pendant le relevé, le canal d'analyse forcé permet de choisir quel canal utiliser dans les cartes sensibles au canal. Laissez Auto quand la dernière transition propre est fiable.</p>
        <h2>Périmètre de couverture</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Site complet</b><br>Le réseau/AP est attendu dans toute la zone relevée. Une absence peut devenir warning de qualité.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Zone locale</b><br>Le réseau/AP est attendu seulement près de sa zone. La Zone auto fonctionne mieux avec position AP et échelle calibrée ; sinon elle utilise l'évidence de signal.</td></tr></table>
        <h2>Positions AP</h2>
        <p>Placer physiquement les AP active les contrôles de distance de la carte AP dominant. Un signal fort très loin, un signal faible très près ou un AP dominant qui n'est pas le plus proche deviennent des constats à vérifier. Ces constats peuvent révéler une mauvaise position, un mauvais groupe AP, un comportement de roaming ou une propagation RF réelle.</p>
        <h2>Mémoire AP</h2>
        <p>La Mémoire AP réutilise alias, rôles, métadonnées, canaux d'analyse et positions compatibles dans les nouveaux relevés. L'état Depuis mémoire demande confirmation : il indique que les données ont été appliquées mais doivent être validées dans le contexte du relevé courant. Mise à jour mémoire signale que le groupe actuel diffère de la mémoire sauvegardée.</p>
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Contrôle conseillé</span><br>Avant d'exporter Interférence ou AP dominant, relisez les groupes avec avertissement, les changements canal et les AP sans position.</td></tr></table>
    """,
    "help_live_maps_body": """
        <h2>Types de carte</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Couverture signal</b><br>Carte continue du signal dBm par SSID et bande. Elle dépend fortement de la qualité des points et de la distance max.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Interférence AP</b><br>Carte de risque construite à partir du canal serveur, des interférents, largeur canal, rôles AP et mode Intra-SSID/Tous SSID.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Canaux AP</b><br>Vue discrète des points réels colorés par canal. Elle n'invente pas de surface entre les mesures.</td><td class="workflow-gap"></td><td class="workflow-card"><b>AP dominant</b><br>Montre le groupe AP le plus fort par point, les zones de roaming potentiel et les warnings de position si les AP sont placés.</td></tr></table>
        <h2>Options par carte</h2>
        <p>SSID, bande, type de carte, labels, interpolation, lissage, distance max, groupe AP et limite relevé sont mémorisés par type de carte pendant la session. Changer de type peut donc restaurer les options utilisées lors de la dernière lecture de cette carte.</p>
        <h2>Interpolation, lissage et distance max</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>RBF lissé :</b> donne une surface continue, utile pour lecture visuelle, mais peut paraître trop optimiste loin des points.</td></tr><tr><td class="gate-row"><b>Linéaire :</b> plus conservateur et plus proche des triangles entre points, mais parfois moins agréable visuellement.</td></tr><tr><td class="gate-row"><b>Distance max :</b> limite le rendu autour de l'évidence mesurée. La valeur automatique se base sur la densité des points quand il y en a assez ; elle évite les grandes zones inventées.</td></tr></table>
        <h2>Limites et masque manuel</h2>
        <p>La limite automatique réduit le rendu hors de l'enveloppe des points. Si un masque Limites existe, il devient prioritaire pour les cartes continues et les exports HTML supportés. Le meilleur résultat arrive quand les points suivent aussi le bord réel des pièces : la carte et le masque racontent alors la même géométrie.</p>
        <h2>Tooltips et légendes</h2>
        <p>Les tooltips Live sont structurés par sections pour lecture rapide : signal, radio, position, interférence, AP serveur, interférent, AP dominant ou second AP selon la carte. Les cartes discrètes utilisent la légende pour se concentrer sur un AP ou un canal ; double-cliquer un élément de légende centre le point ou le groupe sur la carte.</p>
        <h2>Performance</h2>
        <p>Couverture et interférence peuvent prendre plusieurs secondes à la première ouverture car les surfaces sont calculées en arrière-plan. Les mises à jour suivantes réutilisent davantage d'état. Le zoom Live ne recalcule pas les données : il redimensionne l'aperçu et affine le rendu après une courte pause.</p>
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Lire avec prudence</span><br>Une carte continue entre des points espacés reste une estimation. Si une zone est importante pour une décision, ajoutez des mesures plutôt que de vous fier uniquement à l'interpolation.</td></tr></table>
    """,
    "help_reports_body": """
        <h2>Export PDF</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Précondition</b><br>Le relevé doit être enregistré avant export afin que CSV, plan, scans bruts et sidecars soient cohérents.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Options actives</b><br>Le PDF utilise l'état courant de la carte Live : SSID, bande, type, échelle couleur, labels, limites, masque et modèle AP.</td></tr></table>
        <h2>Page carte</h2>
        <p>La première page rend la carte sur le plan indépendamment du zoom ou pan courant. Les fonds uniformes inutilisés au bas d'un plan peuvent être recoupés pour éviter d'exporter une grande zone vide, quelle que soit la couleur de fond. Les points et marqueurs AP restent protégés du recadrage.</p>
        <h2>Cartes continues et discrètes</h2>
        <table class="survey-grid"><tr><td class="survey-card"><b>Couverture</b><br>Carte avec barre dBm. Pas de page problème dédiée : les problèmes de qualité se lisent dans Qualité relevé.</td><td class="survey-gap"></td><td class="survey-card"><b>Interférence</b><br>Carte avec risque et pages de diagnostic si des problèmes pertinents existent.</td><td class="survey-gap"></td><td class="survey-card"><b>Canaux/AP dominant</b><br>Cartes discrètes avec légendes. AP dominant peut ajouter des pages pour roaming et position AP.</td></tr></table>
        <h2>Pages diagnostic</h2>
        <p>Interférence et AP dominant peuvent ajouter des cartes de détail paginées. Les callouts numérotés relient les points visibles sur la carte à des fiches qui expliquent AP serveur, interférent, canal, largeur, risque, AP dominant, AP secondaire ou AP physique le plus proche.</p>
        <h2>Avant d'envoyer un rapport</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>1. Confirmer le périmètre</b><br>SSID, bande et type de carte doivent être ceux que vous voulez documenter.</td></tr><tr><td class="gate-row"><b>2. Confirmer le modèle AP</b><br>Relisez groupes, rôles, alias et positions avant Interférence ou AP dominant.</td></tr><tr><td class="gate-row"><b>3. Confirmer les canaux</b><br>Relisez changements propres, changements ambigus et overrides d'analyse.</td></tr><tr><td class="gate-row"><b>4. Lire les cartes comme diagnostic</b><br>Une fiche d'avertissement peut décrire un vrai problème de déploiement, pas une erreur du logiciel.</td></tr></table>
    """,
    "help_diagnostics_body": """
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Règle des avertissements</span><br>Un avertissement dit quelle hypothèse mérite revue. Décidez d'abord si le problème vient de l'évidence du point, de l'identité AP, de la position, des métadonnées, du canal ou du comportement RF réel.</td></tr></table>
        <h2>Catégories fréquentes</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Points à rescanner</b><br>SSID pertinent absent, données rares, faible confiance ou signal instable indiquent que le point peut être faible.<br><span class="survey-card-use">Vérifier :</span> focaliser le point, lire l'évidence brute et rescanner si nécessaire.</td><td class="workflow-gap"></td><td class="workflow-card"><b>AP dominant inattendu</b><br>L'AP le plus fort n'est pas cohérent avec la position physique ou l'AP le plus proche.<br><span class="survey-card-use">Vérifier :</span> positions, alias, échelle et comportement de roaming.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Ambiguïté de roaming</b><br>Le premier et le second AP sont proches en dB.<br><span class="survey-card-use">Vérifier :</span> les clients peuvent choisir l'un ou l'autre ; ce n'est pas forcément une mauvaise mesure.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Canal ou bande inattendu</b><br>L'observation ne correspond pas aux métadonnées AP.<br><span class="survey-card-use">Vérifier :</span> configuration contrôleur, canaux/bandes attendus, fréquence scanner et override.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Changement de canal</b><br>Le même AP a bougé de canal pendant le relevé. Les changements propres utilisent le dernier canal ; les ambigus gardent les mesures sauf override.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Position AP manquante</b><br>Un groupe AP pertinent n'a pas de marqueur physique. Les diagnostics de distance AP dominant sont alors plus faibles.</td></tr></table>
        <h2>Patterns de dépannage</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>Couverture trop optimiste loin des points</b><br>Cause probable : l'interpolation remplit un espace non mesuré. Action : réduire distance max ou collecter plus de points.</td></tr><tr><td class="gate-row"><b>Interférence sur un ancien canal</b><br>Cause probable : changement canal, séquence ambiguë ou override manquant. Action : lire le détail de changement et les métadonnées AP.</td></tr><tr><td class="gate-row"><b>AP dominant loin de son marqueur</b><br>Cause probable : mauvaise position, mauvais groupe, roaming client ou fuite RF réelle. Action : ouvrir le détail AP dominant et vérifier l'AP le plus proche.</td></tr><tr><td class="gate-row"><b>Beaucoup de points à revoir</b><br>Cause probable : SSID pertinents absents, signal instable ou scans rares. Action : focaliser et rescanner avant d'interpréter.</td></tr><tr><td class="gate-row"><b>Canaux inattendus sur un AP</b><br>Cause probable : métadonnées obsolètes, configuration changée ou preuve bande/canal ambiguë. Action : comparer avec le contrôleur réel.</td></tr></table>
        <h2>Ordre de revue</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>1. Évidence de point</b><br>Corrigez réseaux manquants, scans rares, faible confiance et instabilité avant les cartes.</td></tr><tr><td class="gate-row"><b>2. Identité et position AP</b><br>Corrigez groupe, alias, rôle et coordonnées car ils affectent AP dominant, Interférence, Canaux AP et HTML.</td></tr><tr><td class="gate-row"><b>3. Métadonnées et canaux</b><br>Les attentes de bande/canal et l'override d'analyse déterminent si un warning est réel.</td></tr><tr><td class="gate-row"><b>4. Cartes en dernier</b><br>Lisez couverture, canaux, roaming et interférences quand les hypothèses sont assez cohérentes.</td></tr></table>
    """,
    "help_glossary_body": """
        <table class="callout-table" width="100%" cellspacing="0" cellpadding="0"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Utilisation</span><br>Ce glossaire stabilise les mots employés dans l'interface et les rapports. Les pages de workflow expliquent les actions ; cette page explique le vocabulaire.</td></tr></table>
        <h2>Évidence Wi-Fi</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>SSID</b><br>Nom du réseau Wi-Fi. Un SSID peut être diffusé par plusieurs BSSID.</td><td class="workflow-gap"></td><td class="workflow-card"><b>BSSID</b><br>Adresse MAC radio observée dans les scans Wi-Fi.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>SSID pertinent</b><br>Réseau choisi comme important pour qualité, cartes Live et rapports.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Sidecar brut</b><br>Fichier <code>.scan</code> lié qui contient les échantillons répétés.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Confiance</b><br>Fiabilité d'une ligne agrégée, calculée à partir des scans répétés.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Constat de rescan</b><br>Problème qualité qui suggère que le point de mesure peut nécessiter un autre scan.</td></tr></table>
        <h2>Modèle AP</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Groupe AP</b><br>Modèle d'un AP physique, contenant souvent plusieurs BSSID.</td><td class="workflow-gap"></td><td class="workflow-card"><b>AP dominant</b><br>Groupe AP avec le signal observé le plus fort au point.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Ambiguïté de roaming</b><br>Point où le premier et le second AP sont assez proches pour que les clients choisissent l'un ou l'autre.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Canal d'analyse forcé</b><br>Canal observé choisi par l'utilisateur pour les cartes sensibles au canal d'un groupe AP et d'une bande.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Changement canal propre</b><br>AP qui change de canal sans preuve de conflit BSSID mélangé.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Changement canal ambigu</b><br>Séquence où le programme ne peut pas traiter le changement comme transition propre.</td></tr></table>
        <h2>Qualité et avertissements</h2>
        <table class="survey-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="survey-card"><b>Warning setup</b><br>Problème de modèle ou déploiement qui ne demande pas forcément de rescanner le point.</td><td class="survey-gap"></td><td class="survey-card"><b>Canal/bande inattendu</b><br>Évidence Wi-Fi qui ne correspond pas aux métadonnées AP attendues.</td><td class="survey-gap"></td><td class="survey-card"><b>Position AP manquante</b><br>Un groupe AP pertinent n'a pas de coordonnée physique ; les contrôles de distance sont plus faibles.</td></tr></table>
        <h2>Mémoire et persistance</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Mémoire AP</b><br>Fichier persistant avec alias, rôles, métadonnées, canaux forcés et positions compatibles pour futurs relevés.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Depuis mémoire</b><br>État indiquant que les données ont été appliquées depuis la Mémoire AP et attendent confirmation.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Mise à jour mémoire</b><br>État signalant que la mémoire contient des données différentes de celles du groupe actuel.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Mémoire options carte</b><br>La Carte Live mémorise les options séparément par type de carte pendant la session.</td></tr></table>
        <h2>Cartes et rapports</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Interpolation</b><br>Estimation visuelle entre mesures réelles. Utile pour lire, pas pour remplacer des points.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Distance max</b><br>Limite de rendu qui évite aux cartes continues de s'étendre trop loin de l'évidence.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Limite relevé</b><br>Option Live qui atténue le rendu continu hors de la zone mesurée.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Masque Limites</b><br>PNG dessiné par l'utilisateur qui définit la zone valide pour les cartes continues et HTML supportés.</td></tr></table>
    """,
    "help_legal_body": """
        <h2>Application</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Produit</b><br>Wi-Fi RF Survey Analyzer</td><td class="workflow-card"><b>Version</b><br>{version}</td></tr><tr><td class="workflow-vertical-gap" colspan="2"></td></tr><tr><td class="workflow-card"><b>Copyright</b><br>{copyright}</td><td class="workflow-card"><b>Licence</b><br>{license_name} (<code>{license_id}</code>)<br>{license_url}</td></tr></table>
        <h2>Usage responsable</h2>
        <table class="callout-table" width="100%" cellspacing="0" cellpadding="0"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Réseaux autorisés uniquement</span><br>Ce logiciel est destiné aux activités légitimes d'analyse, de relevé et de dépannage Wi-Fi sur des réseaux que vous possédez ou êtes autorisé à évaluer. L'auteur n'assume aucune responsabilité en cas de mauvaise utilisation.</td></tr></table>
        <h2>Composants tiers</h2>
        <p>L'application utilise des bibliothèques tierces telles que PySide6/Qt, matplotlib, numpy, scipy, pandas, Pillow et lswifi. Le résumé des licences se trouve dans <code>THIRD_PARTY_LICENSES</code>, inclus avec le code source et les releases packagées.</p>
        <h2>Accès au code source</h2>
        <p>Les releases exécutables publiques doivent pointer vers le tag source ou l'état du dépôt correspondant au build publié.</p>
        <table class="callout-table" width="100%" cellspacing="0" cellpadding="0"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Aucune garantie</span><br>Le logiciel est fourni tel quel, sans garantie d'aucune sorte.</td></tr></table>
    """,
})

TRANSLATIONS.update({
    "help_survey_body": TRANSLATIONS["help_survey_body"] + """
        <h2>Actions sur les points</h2>
        <table><tr><th>Action</th><th>Usage</th></tr><tr><td>Aller au point</td><td>Sélectionne le point, ajuste le zoom jusqu'à la cible configurée et place le marqueur dans la partie haute de la vue pour rester visible avec le panneau des points ouvert.</td></tr><tr><td>Rescanner point</td><td>Relance la mesure au même endroit quand Qualité relevé indique réseau manquant, signal instable, confiance faible ou données rares.</td></tr><tr><td>Supprimer sélection / dernier</td><td>Retire l'évidence quand le point a été placé au mauvais endroit ou capturé dans de mauvaises conditions.</td></tr></table>
        <h2>Quand ajouter des points</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>Transition AP :</b> ajoutez des points de part et d'autre des portes, couloirs et changements de pièce. AP dominant et roaming ont besoin d'évidence autour de ces limites.</td></tr><tr><td class="gate-row"><b>Zone vide :</b> si une carte semble extrapoler trop loin, collectez un point au centre de la zone avant de conclure.</td></tr><tr><td class="gate-row"><b>Plan blanc :</b> utilisez la grille comme repère spatial. En métrique le carré représente 1 m ; en impérial le carré représente 3 ft.</td></tr></table>
    """,
    "help_quality_body": TRANSLATIONS["help_quality_body"] + """
        <h2>Détails des constats</h2>
        <table class="survey-grid"><tr><td class="survey-card"><b>Réseaux pertinents manquants</b><br>Indique qu'un SSID attendu n'a pas été vu au point. Vérifiez si le réseau est réellement attendu dans cette zone, surtout pour les AP en Zone locale.</td><td class="survey-gap"></td><td class="survey-card"><b>Détails scanner limités</b><br>Le backend n'a pas fourni assez d'information pour certains raisonnements de canal : largeur canal, fréquence 6 GHz ou données scanner de fallback.</td><td class="survey-gap"></td><td class="survey-card"><b>Roaming client</b><br>Le laptop de relevé est resté associé à un AP plus faible alors qu'un autre AP du même SSID était nettement plus fort. C'est une preuve utile de sticky client.</td></tr></table>
        <h2>Lire les détails AP</h2>
        <p>Les constats AP dominant combinent signal, AP dominant, AP physique le plus proche et distance. Ils ne signifient pas toujours que le point est faux : ils peuvent révéler un placement AP incorrect, un alias ambigu, une propagation RF réelle ou un comportement de roaming acceptable.</p>
        <table class="gate-list"><tr><td class="gate-row"><b>Mémoire AP :</b> confirmez les données appliquées depuis la mémoire quand elles sont correctes pour ce site. Si le relevé courant a des informations meilleures, gardez-les et mettez la mémoire à jour.</td></tr><tr><td class="gate-row"><b>Changements canal :</b> un changement propre peut être traité automatiquement ; un changement ambigu mérite un canal d'analyse forcé si vous connaissez le canal à documenter.</td></tr><tr><td class="gate-row"><b>AP sans position :</b> placez les AP pertinents avant de tirer des conclusions de distance AP dominant.</td></tr></table>
    """,
    "help_ap_groups_body": TRANSLATIONS["help_ap_groups_body"] + """
        <h2>Conflits de groupe AP</h2>
        <p>Un conflit apparaît quand un groupe semble contenir des BSSID incompatibles pour un seul AP physique, par exemple plusieurs canaux dans la même bande. Cela peut être un vrai changement de canal, un AP spécial multi-radio ou un regroupement incorrect. Utilisez Corriger groupe AP pour séparer les lignes seulement quand l'évidence montre des AP différents.</p>
        <h2>Bonnes pratiques de nommage</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>Alias lisibles :</b> utilisez des noms opérationnels stables, par exemple étage, zone ou numéro AP. Les alias apparaissent dans tooltips, légendes et PDF.</td></tr><tr><td class="gate-row"><b>Rôles cohérents :</b> marquez comme Externe les voisins et comme Test/masqué les AP à ignorer. Ne laissez pas un AP de test polluer Couverture, Interférence ou AP dominant.</td></tr><tr><td class="gate-row"><b>Métadonnées utiles :</b> les canaux attendus et bandes attendues doivent refléter le contrôleur réel, pas seulement ce que le scanner a vu pendant le relevé.</td></tr></table>
        <h2>Quand utiliser un override</h2>
        <p>Un override de canal d'analyse est utile quand un AP a changé de canal pendant le relevé et que vous savez quel canal doit représenter l'analyse. Il évite qu'une carte Interférence ou Canaux AP mélange une transition temporaire avec l'état que vous voulez documenter.</p>
    """,
    "help_live_maps_body": TRANSLATIONS["help_live_maps_body"] + """
        <h2>Lecture par carte</h2>
        <table class="survey-grid"><tr><td class="survey-card"><b>Couverture</b><br>Contrôlez d'abord la couleur et le dBm estimé, puis vérifiez les points réels autour de la zone. Une surface lisse n'est pas une mesure supplémentaire.</td><td class="survey-gap"></td><td class="survey-card"><b>Interférence</b><br>Lisez le risque avec le contexte : AP serveur, canal, largeur, rôle de l'interférent et mode Intra-SSID ou Tous SSID.</td><td class="survey-gap"></td><td class="survey-card"><b>Cartes discrètes</b><br>Canaux AP et AP dominant montrent les mesures, pas une interpolation. Les couleurs doivent être lues comme catégories par point.</td></tr></table>
        <h2>Zoom et centrage</h2>
        <p>Les actions depuis Qualité relevé, les listes de points et certaines légendes peuvent centrer automatiquement un point ou un groupe. Si le plan est très large ou très haut, le programme tente le meilleur repositionnement possible sans forcer la carte hors de ses limites de pan.</p>
        <h2>Quand régénérer</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>Après rescans :</b> mettez à jour la carte Live pour relire la surface avec les nouveaux points.</td></tr><tr><td class="gate-row"><b>Après correction AP :</b> Interférence, Canaux AP et AP dominant doivent être recalculées car groupes, rôles ou canaux peuvent changer le résultat.</td></tr><tr><td class="gate-row"><b>Après masque Limites :</b> vérifiez les cartes continues et le PDF, car le masque modifie la zone visible du rendu.</td></tr></table>
    """,
})
