"""Spanish translations."""

from translations.en import TRANSLATIONS as EN_TRANSLATIONS


LANGUAGE_LABEL = "Español"

TRANSLATIONS = dict(EN_TRANSLATIONS)
TRANSLATIONS.update({
    "wifi_scan_timeout": "El análisis Wi-Fi agotó el tiempo de espera. Comprueba el adaptador e inténtalo de nuevo.",
    "wifi_scan_failed": "El análisis Wi-Fi falló. Comprueba el adaptador, los permisos de Windows y el registro de la aplicación.",
    "loading_app": "Cargando componentes...",
    "loading_app_ready": "Listo",
    "loading_app_error": "Error al cargar la aplicación.",
    "start_subtitle": "Estudios reales, mapas Live y diagnósticos RF",
    "start_workflow_title": "Workflow",
    "start_workflow_1": "1. Cree o abra un estudio y cargue el plano.",
    "start_workflow_2": "2. Registre puntos con escaneos multi-muestra y redes relevantes.",
    "start_workflow_3": "3. Analice cobertura, interferencias, roaming, grupos AP y calidad.",
    "start_loading_title": "Inicio",
    "start_actions_title": "Estudio",
    "start_actions_hint": "Los comandos se activan cuando los componentes de análisis están listos.",
    "start_ready_hint": "La ventana principal se abrirá directamente en el estudio seleccionado.",
    "qt_start_hint_title": "Interfaz actual",
    "qt_start_hint": "Esta release usa la base Qt con estudio, mapa Live, grupos AP, calidad, generación de mapas y calibración de escala.",
    "toolbar_project": "Proyecto",
    "toolbar_view": "Vista",
    "toolbar_analysis": "Análisis",
    "toolbar_settings": "Ajustes",
    "qt_survey_file_filter": "CSV estudio Wi-Fi (*.csv);;Todos los archivos (*.*)",
    "qt_plan_file_filter": "PDF e imágenes (*.pdf *.png *.jpg *.jpeg *.bmp);;Todos los archivos (*.*)",
    "qt_points": "Puntos",
    "qt_raw_rows": "Escaneos brutos",
    "qt_table_networks": "Redes",
    "qt_table_best_dbm": "Mejor dBm",
    "qt_table_timestamp": "Marca temporal",
    "summary_ap_groups": "Grupos AP",
    "points_panel_show": "▲ Puntos de medición",
    "points_panel_hide": "▼ Puntos de medición",
    "points_panel_resize": "Arrastre arriba o abajo para redimensionar el panel de puntos.",
    "new_survey": "Nuevo estudio",
    "new_survey_measurement_system_title": "Unidades del nuevo estudio",
    "new_survey_measurement_system_message": "Elija el sistema de medida para este estudio.\n\nLa escala y la cuadrícula del plano blanco generado se crearán a partir de esta elección.",
    "new_survey_close_current_title": "¿Iniciar nuevo estudio?",
    "new_survey_close_current_message": "Esta operación cerrará el estudio actual antes de crear uno nuevo.\n\n¿Guardar el estudio actual, descartar cambios o cancelar?",
    "discard_changes": "Descartar cambios",
    "open_existing_survey": "Abrir estudio",
    "invalid_survey_title": "Estudio incompatible",
    "invalid_survey_format": "El archivo seleccionado no es un CSV de estudio Wi-Fi válido. Cree un nuevo estudio o abra el CSV principal generado por el programa.",
    "raw_scan_file_selected": "Ha seleccionado el archivo de datos brutos. Abra el CSV principal del estudio, no el archivo _raw_data.scan.",
    "invalid_raw_scan_format": "El archivo de escaneos brutos asociado a este estudio no es válido. Recree el estudio o elimine el sidecar inválido.",
    "exit": "Salir",
    "language": "Idioma",
    "ui_scale": "Escala UI",
    "ui_scale_auto": "Auto ({percent}%)",
    "measurement_system": "Sistema de medida",
    "measurement_system_metric": "Métrico (m)",
    "measurement_system_imperial": "Imperial (ft)",
    "workspace_settings_section": "Workspace",
    "go_to_point_zoom": "Zoom Ir al punto",
    "measurement_unit_metric": "metros",
    "measurement_unit_imperial": "pies",
    "measurement_system_scale_reset_title": "La calibración de escala se reiniciará",
    "measurement_system_scale_reset_message": "Este estudio ya tiene una escala calibrada. Cambiar el sistema de medida eliminará la calibración actual.\n\nEjecute Calibrar escala de nuevo antes de interpretar distancias. ¿Continuar?",
    "measurement_system_scale_reset_button": "Cambiar y borrar escala",
    "measurement_system_scale_reset_done": "Sistema de medida cambiado. Escala borrada; ejecute Calibrar escala de nuevo.",
    "ui_scale_restart_title": "Reinicio requerido",
    "ui_scale_restart_message": "Aplicar la escala UI {scale} requiere reiniciar la app.\n\n¿Guardar esta opción y reiniciar ahora?",
    "save_and_restart": "Guardar y reiniciar",
    "settings_save_failed": "No se pudieron guardar los ajustes.",
    "ap_memory_settings_title": "Memoria AP",
    "open_memory_folder": "Abrir carpeta memoria",
    "open_memory_folder_failed": "No se pudo abrir la carpeta de Memoria AP.",
    "clear_ap_memory": "Borrar Memoria AP...",
    "clear_ap_memory_title": "Borrar Memoria AP",
    "clear_ap_memory_confirm": "Esto eliminará alias, roles, metadatos y posiciones AP recordados para futuros estudios.\n\nEl estudio abierto no se modificará. ¿Continuar?",
    "clear_ap_memory_confirm_button": "Borrar Memoria AP",
    "clear_ap_memory_failed": "No se pudo borrar la Memoria AP.",
    "restart_failed": "No se pudo reiniciar la aplicación.",
    "restart_blocked_busy": "Espere a que termine el escaneo o la actualización del mapa antes de cambiar la escala UI.",
    "active_survey": "Estudio activo: {name}",
    "survey_tab": "Estudio",
    "live_map_tab": "Mapa Live",
    "live_auto_update": "Actualización auto",
    "live_update_now": "Actualizar",
    "live_export_pdf": "Exportar PDF",
    "live_pdf_exported": "PDF exportado",
    "save_live_pdf_title": "Guardar PDF mapa Live",
    "live_pdf_file_filter": "PDF (*.pdf);;Todos los archivos (*.*)",
    "live_pdf_problem_report_title": "Reporte de problemas",
    "live_pdf_issue": "Problema",
    "live_pdf_no_interference_issues": "No se detectaron problemas relevantes de interferencia.",
    "live_pdf_no_dominant_issues": "No se detectaron problemas relevantes de AP dominante.",
    "live_options_show": "Opciones",
    "live_options_hide": "Opciones",
    "live_preview_empty": "Mapa Live: cargue un plano y registre al menos 3 puntos.",
    "live_preview_insufficient": "Mapa Live: datos insuficientes para esta vista.",
    "live_preview_rendering": "Actualizando mapa Live...",
    "live_preview_updated": "Mapa Live actualizado.",
    "ap_group_filter": "Grupo AP",
    "all_ap_groups_option": "Todos los grupos AP",
    "footer_survey_info": "CSV: {csv} | Plano: {map} | Puntos: {points} | Último: {last}",
    "ap_memory_status_missing": "Memoria AP: no creada",
    "ap_memory_status_empty": "Memoria AP: vacía",
    "ap_memory_status_saved": "Memoria AP: guardada ({count} AP)",
    "ap_memory_status_applied": "Memoria AP: {applied} por confirmar / {total} guardados",
    "unsaved_survey": "Estudio sin guardar",
    "no_map": "Sin plano",
    "default_floorplan_name": "Plano en blanco",
    "replace_default_floorplan_title": "¿Reemplazar plano blanco?",
    "replace_default_floorplan": "El plano blanco generado se guardará como:\n{path}\n\nEse archivo ya existe. ¿Reemplazarlo?",
    "generated_floorplan_cleanup_failed": "No se pudo eliminar el plano blanco reemplazado: {path}",
    "load_plan": "Cargar plano",
    "generate_heatmap": "Generar heatmap",
    "generate": "Generar",
    "save": "Guardar",
    "save_clean_tooltip": "Estudio guardado",
    "save_dirty_tooltip": "Hay cambios sin guardar",
    "ap_aliases": "Grupos AP",
    "quality_dashboard_title": "Calidad estudio",
    "quality_dashboard_hint": "Revise calidad de escaneo, setup AP y diagnósticos de mapa antes de confiar en los mapas generados.",
    "quality_dashboard_status_ok_title": "Estudio coherente",
    "quality_dashboard_status_ok_message": "Ningún punto necesita reescaneo. Los controles de calidad no encontraron problemas en {total} puntos.",
    "quality_dashboard_status_early_title": "Datos iniciales",
    "quality_dashboard_status_early_message": "No se detectaron problemas de escaneo en {total} puntos, pero el análisis será más útil con más puntos.",
    "quality_dashboard_status_review_title": "Revisión recomendada",
    "quality_dashboard_status_review_message": "{count} de {total} puntos deben revisarse o reescanearse antes de usar los mapas.",
    "quality_dashboard_status_setup_title": "Setup AP requiere atención",
    "quality_dashboard_status_setup_message": "Los puntos no necesitan reescaneo, pero posiciones AP, metadatos o cambios de canal requieren revisión.",
    "quality_dashboard_metric_points": "Total puntos",
    "quality_dashboard_metric_ok": "Puntos OK",
    "quality_dashboard_metric_review": "Puntos a revisar",
    "quality_dashboard_metric_group_survey": "Puntos estudio",
    "quality_dashboard_metric_group_scan": "Calidad escaneo",
    "quality_dashboard_metric_group_ap": "Modelo AP",
    "quality_dashboard_metric_scan_ok": "Escaneo OK",
    "quality_dashboard_metric_rescan": "Puntos a revisar",
    "quality_dashboard_metric_missing": "Redes relevantes ausentes",
    "quality_dashboard_metric_sparse": "Datos escasos",
    "quality_dashboard_metric_scanner_details": "Faltan detalles scanner",
    "quality_dashboard_metric_low_confidence": "Baja confianza escaneo",
    "quality_dashboard_metric_unstable": "Señal inestable",
    "quality_dashboard_metric_connected_client": "Roaming cliente",
    "quality_dashboard_metric_ap_diagnostic_points": "Findings AP dominante",
    "quality_dashboard_metric_ap_memory_applied": "Revisión Memoria AP",
    "quality_dashboard_metric_ap_position_warnings": "Warnings posición AP",
    "quality_dashboard_metric_ap_missing_positions": "AP sin posición",
    "quality_dashboard_metric_ap_metadata_warnings": "Warnings config AP",
    "quality_dashboard_metric_channel_changes": "Cambios canal",
    "quality_dashboard_fix_next_title": "Qué corregir ahora",
    "quality_dashboard_fix_missing_title": "Reescanear redes ausentes",
    "quality_dashboard_fix_missing_detail": "{count} puntos no ven uno o más SSID esperados. Reescanee, revise redes relevantes o scope Local Area.",
    "quality_dashboard_fix_sparse_title": "Repetir escaneos escasos",
    "quality_dashboard_fix_sparse_detail": "{count} puntos tienen muy pocas muestras útiles. Repita esos escaneos antes de confiar en la interpolación.",
    "quality_dashboard_fix_scanner_details_title": "Reescanear puntos con detalles limitados",
    "quality_dashboard_fix_scanner_details_detail": "{count} puntos carecen de detalles scanner usados por análisis sensibles al canal. Reescanee antes de Interferencia, ancho 5 GHz o lectura 6 GHz.",
    "quality_dashboard_fix_scanner_details_dialog_detail": "Use Ir al punto y reescanee cuando ancho de canal, frecuencia o fallback scanner afecten las conclusiones.",
    "quality_dashboard_fix_low_confidence_title": "Reescanear puntos poco fiables",
    "quality_dashboard_fix_low_confidence_detail": "{count} puntos tienen baja confianza del candidato dominante. Repítalos o verifique estabilidad del scanner.",
    "quality_dashboard_fix_unstable_title": "Repetir puntos inestables",
    "quality_dashboard_fix_unstable_detail": "{count} puntos tienen dispersión de muestras capaz de afectar los mapas. Repítalos si guían decisiones.",
    "quality_dashboard_fix_connected_client_title": "Revisar roaming cliente",
    "quality_dashboard_fix_connected_client_detail": "{count} puntos muestran el portátil asociado a un AP más débil mientras otro grupo AP del mismo SSID era más fuerte. Revise sticky client o reescanee tras reconectar.",
    "quality_dashboard_fix_ap_memory_title": "Revisar Memoria AP",
    "quality_dashboard_fix_ap_memory_detail": "{count} grupos AP requieren revisión de Memoria AP. Confirme datos aplicados o decida si los datos manuales reemplazan la memoria.",
    "quality_dashboard_fix_ap_memory_dialog_detail": "Use Abrir grupo AP para inspeccionar grupos con estado memoria. Confirme o actualice según la diferencia con Memoria AP.",
    "quality_dashboard_fix_ap_position_title": "Revisar warnings AP dominante",
    "quality_dashboard_fix_ap_position_detail": "{count} puntos no coinciden con posiciones AP físicas. Inspeccione marcadores antes de conclusiones basadas en AP.",
    "quality_dashboard_fix_ap_position_dialog_detail": "Use Ir al punto para inspeccionar cada finding en el plano.",
    "quality_dashboard_fix_ap_missing_title": "Colocar AP ausentes",
    "quality_dashboard_fix_ap_missing_detail": "{count} grupos AP relevantes no tienen posición. Añada su posición física antes de diagnósticos de distancia AP.",
    "quality_dashboard_fix_ap_missing_dialog_detail": "Solo se listan grupos AP relevantes no-test sin posición. Use Abrir grupo AP para colocar cada AP.",
    "quality_dashboard_fix_ap_metadata_title": "Revisar metadatos AP",
    "quality_dashboard_fix_ap_metadata_detail": "{count} grupos AP tienen canales o bandas esperadas incoherentes. Corrija metadatos o defina un override de canal de análisis.",
    "quality_dashboard_fix_ap_metadata_dialog_detail": "Use Abrir metadatos AP para corregir canales/bandas esperadas o definir un override de canal de análisis.",
    "quality_dashboard_fix_channel_change_clean_title": "Revisar modelo de cambio canal",
    "quality_dashboard_fix_channel_change_ambiguous_title": "Resolver cambios canal ambiguos",
    "quality_dashboard_fix_channel_change_detail": "{count} grupos AP cambiaron canal durante el estudio ({clean} limpios, {ambiguous} ambiguos). Los mapas sensibles al canal usan el último canal limpio por defecto.",
    "quality_dashboard_fix_channel_change_dialog_detail": "Use Abrir metadatos AP para inspeccionar cada cambio y definir un override si la elección automática no es correcta.",
    "quality_dashboard_fix_more_points_title": "Recoger más puntos",
    "quality_dashboard_fix_more_points_detail": "Solo hay {total} puntos disponibles. Añada posiciones antes de leer huecos de cobertura.",
    "quality_dashboard_fix_ready_title": "Generar mapas",
    "quality_dashboard_fix_ready_detail": "Los controles principales están limpios. Genere mapas o abra listas KPI para una última revisión.",
    "quality_dashboard_context_scope": "Scope estudio\nRelevantes: {networks}\nPosiciones AP: {positions}\nAP test: {test_aps}",
    "quality_dashboard_scope_title": "Scope estudio",
    "quality_dashboard_scope_relevant": "Relevantes: {networks}",
    "quality_dashboard_scope_positions": "Posiciones AP: {positions}",
    "quality_dashboard_scope_test_aps": "AP test: {test_aps}",
    "quality_dashboard_action_open_dominant": "Mapa AP dominante",
    "quality_dashboard_action_open_ap_channels": "Mapa canales AP",
    "quality_dashboard_action_open_interference": "Mapa interferencia",
    "quality_dashboard_action_open_ap_metadata": "Abrir metadatos AP",
    "quality_dashboard_action_open_ap_group": "Abrir grupo AP",
    "quality_dashboard_action_focus_point": "Ir al punto",
    "quality_dashboard_action_metadata_for": "Metadatos: {ap}",
    "quality_dashboard_action_group_for": "Grupo AP: {ap}",
    "quality_dashboard_channel_change_status_clean": "limpio",
    "quality_dashboard_channel_change_status_ambiguous": "ambiguo",
    "quality_dashboard_channel_change_label": "{ap} {band}: {status}, canales {channels}, actual {current}",
    "quality_dashboard_channel_change_item_detail": "<b>Banda:</b> {band}<br><b>Canales observados:</b> {channels}<br><b>Mapas usan:</b> {current}<br><b>Estado:</b> {status}",
    "quality_dashboard_expand_details": "Detalles ({count})",
    "quality_dashboard_detail_count": "{count} filas detalle",
    "quality_dashboard_detail_ap_groups": "{count} grupos AP",
    "quality_dashboard_detail_measurement_points": "{count} puntos de medición",
    "quality_dashboard_detail_channel_changes": "{count} cambios canal",
    "quality_dashboard_missing_position_item_detail": "<b>Grupo AP:</b> {group}<br><b>Acción requerida:</b> colocar este AP en el plano",
    "quality_dashboard_point_detail_label": "Punto {point} ({x}, {y})",
    "quality_dashboard_ap_position_finding": "Finding: {finding}",
    "quality_dashboard_ap_position_detail": "AP dominante: {dominant} | Señal: {signal} | Distancia: {dominant_distance}\nAP más cercano: {closest} | Distancia: {closest_distance}",
    "quality_dashboard_context_relevant_networks": "Redes relevantes",
    "quality_dashboard_context_ap_positions": "Estado posiciones AP",
    "quality_dashboard_context_test_aps": "AP test excluidos",
    "quality_dashboard_context_missing_positions": "AP sin posición",
    "quality_dashboard_context_config_warnings": "Detalles config AP",
    "quality_dashboard_ap_metadata_channels": "<b>Canales observados:</b> {channels}<br><b>Canales esperados:</b> {expected}",
    "quality_dashboard_ap_metadata_bands": "<b>Bandas observadas:</b> {bands}<br><b>Bandas esperadas:</b> {expected}",
    "quality_dashboard_ap_memory_item_detail": "<b>Estado memoria:</b> M - aplicado desde Memoria AP<br><b>BSSID asociados:</b> {matched_bssids}<br><b>Siguiente paso:</b> confirmar o editar datos AP recordados",
    "quality_dashboard_ap_memory_update_item_detail": "<b>Estado memoria:</b> <s>M</s> - los datos AP actuales difieren de Memoria AP<br><b>Campos distintos:</b> {fields}<br><b>Siguiente paso:</b> actualizar desde memoria, o conservar datos actuales y guardarlos",
    "quality_dashboard_scanner_details_issue": "Detalles scanner: {detail}",
    "quality_dashboard_scanner_details_fallback": "Scanner usado: <b>{backends}</b> (detalles canal limitados)",
    "quality_dashboard_scanner_details_missing_width": "Ancho canal ausente en <b>{count}</b> filas de escaneo",
    "quality_dashboard_scanner_details_missing_frequency": "Frecuencia 6 GHz ausente en <b>{count}</b> filas de escaneo",
    "quality_dashboard_scanner_details_finding": "Detalles scanner limitados",
    "quality_dashboard_scanner_details_scanner": "Scanner: <b>{backends}</b>{fallback} | Filas brutas: <b>{count}</b>",
    "quality_dashboard_scanner_details_fallback_suffix": " (fallback)",
    "quality_dashboard_scanner_details_missing_width_detail": "Ancho canal ausente: <b>{count}</b> filas sensibles al canal",
    "quality_dashboard_scanner_details_missing_frequency_detail": "Frecuencia 6 GHz ausente: <b>{count}</b> filas 6 GHz",
    "quality_dashboard_scanner_details_impact": "Impacto: los mapas sensibles al canal pueden ser menos fiables aquí.",
    "quality_dashboard_issue_missing_relevant": "<b>{ssid}</b>: red relevante no detectada en este punto",
    "quality_dashboard_issue_low_confidence": "<b>{ssid}</b>: nivel de confianza {confidence}",
    "quality_dashboard_issue_unstable_signal": "<b>{ssid}</b>: señal varía {range} dB",
    "quality_dashboard_issue_sparse_data": "No hay suficientes muestras en este punto",
    "quality_dashboard_connected_client_issue": "<b>{ssid}</b>: AP conectado <b>{connected}</b> ({connected_signal}); AP más fuerte <b>{stronger}</b> ({stronger_signal}); diferencia {delta} dB",
    "quality_dashboard_more_issues": "+{count} más",
    "quality_dashboard_metric_view_points": "Ver puntos",
    "quality_dashboard_metric_extra_details": "Detalles",
    "quality_dashboard_metric_click_points": "Clic para ver puntos",
    "quality_dashboard_metric_click_details": "Clic para abrir detalles",
    "quality_dashboard_points_dialog_title": "{label} - {count} puntos",
    "quality_dashboard_check_kpi_issue": "Control KPI: {kpis}",
    "quality_dashboard_visible_count": "{shown}/{total} puntos mostrados",
    "quality_dashboard_quality": "Calidad",
    "quality_dashboard_scan_quality": "Calidad escaneo",
    "quality_dashboard_confidence": "Confianza",
    "quality_dashboard_issue": "Problema",
    "quality_dashboard_relevant_ssids": "SSID relevantes",
    "quality_dashboard_no_issue": "Sin problemas detectados",
    "quality_dashboard_ap_position_issue": "AP dominante: <b>{dominant}</b> ({signal}, {dominant_distance}) | AP más cercano: <b>{closest}</b> ({closest_distance}) | <b>{warning}</b>",
    "quality_dashboard_missing_positions_none": "ninguno",
    "quality_dashboard_missing_positions_more": "{names}, +{count}",
    "calibrate_scale": "Calibrar escala",
    "calibrate_scale_title": "Calibración de escala",
    "calibrate_scale_start": "Clic izquierdo en el primer punto de la distancia real conocida.",
    "calibrate_scale_second_point": "Clic izquierdo en el segundo punto de la distancia conocida.",
    "calibrate_scale_distance_prompt": "Distancia real entre los dos puntos ({unit}):",
    "calibrate_scale_saved": "Escala calibrada: {scale}.",
    "calibrate_scale_invalid": "Distancia inválida.",
    "calibrate_scale_cancelled": "Calibración cancelada.",
    "calibrate_scale_already_set": "Escala ya calibrada. Elimine la escala actual para recalibrar.",
    "grid": "Cuadrícula",
    "grid_enabled": "Cuadrícula activada.",
    "grid_disabled": "Cuadrícula desactivada.",
    "grid_scale_label": "1 cuadrado = {interval}",
    "boundaries": "Límites",
    "boundaries_enabled": "Modo Límites activado.",
    "boundaries_disabled": "Modo Límites desactivado.",
    "boundaries_draw_tooltip": "Arrastrar con clic derecho para dibujar máscara",
    "boundaries_eraser_tooltip": "Arrastrar con clic derecho para borrar máscara",
    "boundaries_circle_tooltip": "Pincel circular",
    "boundaries_square_tooltip": "Pincel cuadrado",
    "boundaries_brush_size_tooltip": "Tamaño pincel Límites",
    "boundaries_brush_size_increase_tooltip": "Aumentar tamaño del pincel",
    "boundaries_brush_size_decrease_tooltip": "Reducir tamaño del pincel",
    "boundaries_brush_size_value_tooltip": "Tamaño pincel: {size} px ({minimum}-{maximum} px, paso {step} px)",
    "boundaries_clear_tooltip": "Limpiar máscara Límites",
    "boundaries_clear_title": "¿Limpiar Límites?",
    "boundaries_clear_confirm": "¿Limpiar la máscara Límites actual?",
    "boundaries_cleared": "Máscara Límites limpiada.",
    "boundaries_save_failed": "No se pudo guardar la máscara Límites: {path}",
    "boundaries_cleanup_failed": "No se pudo eliminar la máscara Límites reemplazada: {path}",
    "delete_scale": "Borrar escala",
    "delete_scale_title": "¿Borrar calibración?",
    "delete_scale_confirm": "¿Borrar la calibración de escala actual?",
    "delete_scale_done": "Calibración eliminada.",
    "ap_groups_title": "Grupos AP",
    "ap_groups_hint": "Agrupe BSSID que pertenecen al mismo AP físico. Alias, rol, metadatos y posición alimentan mapas y controles de calidad.",
    "ap_group_bssid_title": "Gestor BSSID",
    "ap_group_bssid_hint": "Corrija pertenencias BSSID sin reconstruir todo el modelo AP.",
    "ap_group_bssid_warning_focus_hint": "Esta vista está centrada en los BSSID relacionados con el warning seleccionado.",
    "ap_group_bssid_scope": "Scope",
    "ap_group_bssid_scope_current": "Grupo actual",
    "ap_group_bssid_scope_other": "Otros grupos",
    "ap_group_bssid_scope_unassigned": "Sin asignar",
    "ap_group_bssid_scope_checked": "Seleccionados",
    "ap_group_bssid_scope_warning": "Focus warning",
    "ap_group_bssid_filter_all": "Todos",
    "ap_group_bssid_select_visible": "Selec. visibles",
    "ap_group_bssid_clear_visible": "Limpiar visibles",
    "ap_group_bssid_invert_visible": "Invertir visibles",
    "ap_group_bssid_new_group_from_rows": "Nuevo grupo desde filas",
    "ap_group_bssid_move_rows": "Mover filas...",
    "ap_group_bssid_select_rows_required": "Seleccione primero una o más filas BSSID.",
    "ap_group_bssid_visible_count": "{visible}/{total} BSSID",
    "ap_group_bssid_management": "Gestión BSSID",
    "ap_group_conflict_title": "Detalles conflicto AP",
    "ap_group_conflict_hint": "El diagnóstico explica por qué el agrupamiento automático puede ser ambiguo.",
    "ap_group_conflict_diagnosis_title": "Diagnóstico",
    "ap_group_conflict_recommendation_title": "Recomendación",
    "ap_group_conflict_diagnosis_body": "Algunos BSSID de este grupo muestran canales, bandas o SSID incoherentes para un único AP físico.",
    "ap_group_conflict_recommendation_body": "Use Gestor BSSID para separar radios o confirmar que el grupo representa el mismo AP físico.",
    "ap_group_set_alias": "Alias",
    "ap_group_set_role": "Rol",
    "ap_group_metadata_title": "Metadatos AP",
    "ap_group_set_position": "Posición",
    "ap_group_delete_alias_title": "Borrar alias",
    "ap_group_delete_alias_confirm": "¿Borrar el alias del grupo AP seleccionado?",
    "ap_group_select_group": "Seleccione primero un grupo AP.",
    "ap_groups_reset_auto": "Reset auto",
    "ap_groups_reset_title": "Reiniciar grupos AP",
    "ap_groups_reset_confirm": "¿Restaurar agrupamiento BSSID automático? Se conservarán alias compatibles, pero se perderán ediciones manuales.",
    "ap_alias_group": "Grupo AP",
    "ap_label": "Etiqueta",
    "ap_alias_bssids": "BSSID",
    "ap_alias_ssids": "SSID vistos",
    "ap_alias_channels": "Canales",
    "ap_alias_bands": "Bandas",
    "ap_alias_value": "Alias",
    "ap_group_management": "Gestión",
    "ap_group_state_manual": "Manual",
    "ap_group_state_auto": "Auto",
    "ap_group_state_memory": "Desde memoria",
    "ap_group_state_memory_update": "Actualización memoria",
    "ap_group_filter_status": "Estado",
    "ap_group_filter_status_all": "Todos estados",
    "ap_group_filter_status_warning": "Warnings",
    "ap_group_filter_status_ok": "OK",
    "ap_group_filter_role": "Rol",
    "ap_group_filter_role_all": "Todos roles",
    "ap_group_filter_band": "Banda",
    "ap_group_filter_band_all": "Todas bandas",
    "ap_group_filter_state": "Estado",
    "ap_group_filter_state_all": "Todos estados",
    "ap_group_clear_filters": "Limpiar filtros",
    "ap_group_visible_count": "{visible}/{total} grupos",
    "ap_alias_search": "Buscar",
    "ap_groups_saved": "Grupos AP guardados.",
    "yes": "Sí",
    "help": "Ayuda",
    "fit": "Ajustar",
    "map": "Plano",
    "saved_network": "Redes relevantes",
    "relevant_networks_none": "Sin red relevante definida",
    "manage_relevant_networks": "Gestionar",
    "manage_relevant_networks_title": "Gestionar redes relevantes",
    "manage_relevant_networks_message": "Seleccione los SSID relevantes para este estudio. La elección también actualiza los puntos ya recogidos.",
    "no_relevant_networks_to_manage": "Aún no hay SSID detectados para gestionar.",
    "relevant_networks_updated": "Redes relevantes actualizadas.",
    "forget_saved_network": "Limpiar",
    "relevant_networks_cleared": "Redes relevantes limpiadas.",
    "best_dbm": "Mejor dBm",
    "quality": "Calidad",
    "quality_good": "OK",
    "quality_missing_relevant": "Red ausente",
    "quality_low_confidence": "Baja confianza",
    "quality_unstable_signal": "Inestable",
    "quality_sparse_data": "Escaso",
    "quality_breakdown_title": "Detalles calidad punto",
    "rows": "Filas",
    "survey_point_tooltip_title": "Punto de medición",
    "wifi_ap_tooltip_title": "AP Wi-Fi",
    "tooltip_signal_scope": "Scope señal",
    "tooltip_scope_relevant": "Redes relevantes",
    "tooltip_scope_all": "Todas redes",
    "tooltip_rows_relevant": "{relevant}/{total} relevantes",
    "tooltip_time": "Hora",
    "tooltip_detected_ssids": "SSID detectados",
    "tooltip_section_location": "Ubicación",
    "tooltip_section_signal": "Señal",
    "tooltip_section_networks": "Redes",
    "tooltip_section_identity": "Identidad",
    "tooltip_section_radio": "Radio",
    "tooltip_section_metadata": "Metadatos",
    "tooltip_section_position": "Posición",
    "tooltip_section_analysis": "Análisis",
    "tooltip_section_reference": "Referencia",
    "tooltip_section_interference": "Interferencia",
    "tooltip_section_serving_ap": "AP servidor",
    "tooltip_section_interferer": "Interferente",
    "tooltip_section_dominant_ap": "AP dominante",
    "tooltip_section_second_ap": "Segundo AP",
    "go_to_point": "Ir al punto",
    "rescan_point": "Reescanear punto",
    "point_rescanned": "Punto reescaneado: x={x}, y={y}, filas anteriores={rows}, redes nuevas={count}.",
    "delete_selected": "Borrar selección",
    "delete_last": "Borrar último",
    "band": "Banda",
    "all_bands_option": "Todas",
    "map_type": "Tipo mapa",
    "map_type_signal": "Cobertura señal",
    "map_type_interference": "Interferencia AP",
    "map_type_channel": "Canales AP",
    "map_type_dominant": "AP dominante",
    "channel_map_legend_title": "Canales AP",
    "channel_map_intermediate_24": "Canales intermedios",
    "dominant_map_legend_title": "AP dominante",
    "dominant_roaming_issue_title": "Overlap roaming",
    "dominant_roaming_issue_detail": "El AP más fuerte está dentro del umbral de roaming {threshold}:\nAP dominante: {dominant} | {dominant_signal}\nAP secundario: {second} | {second_signal}\nLos clientes pueden hacer roaming u oscilar aquí.",
    "point_labels": "Etiquetas puntos",
    "point_labels_auto": "Automático",
    "point_labels_critical": "Solo críticos",
    "point_labels_all": "Todos",
    "point_labels_none": "Ninguno",
    "reference_table_info": "Referencia",
    "reference_more_in_report": "+ {count} más en reporte CSV",
    "legend_other": "Otro",
    "signal": "Señal",
    "coverage_aggregation": "Agregación",
    "samples": "Muestras",
    "scan_confidence": "Confianza",
    "reference_channel": "Canal",
    "reference_width": "Ancho",
    "channel_width": "Ancho canal",
    "reference_ap": "AP",
    "reference_delta": "Delta segundo AP",
    "reference_risk": "Riesgo",
    "reference_serving_channel": "Canal servidor",
    "reference_interferer_channel": "Canal interferente",
    "second_ap": "Segundo AP",
    "second_ap_role": "Rol segundo AP",
    "second_channel": "Segundo canal",
    "second_signal": "Segunda señal",
    "second_samples": "Segundas muestras",
    "second_confidence": "Segunda confianza",
    "signal_delta": "Delta señal",
    "roaming_overlap": "Overlap roaming",
    "serving_ap": "AP servidor",
    "export_signal_title": "Cobertura señal Wi-Fi",
    "export_channel_title": "Canales AP Wi-Fi",
    "export_dominant_title": "AP dominante Wi-Fi",
    "export_interference_title": "Interferencia AP Wi-Fi",
    "export_signal_colorbar": "Señal estimada dBm",
    "export_points": "puntos",
    "export_measurements": "mediciones",
    "export_roaming_overlap": "overlap roaming",
    "interference_mode": "Análisis interferencia",
    "interference_mode_intra_ssid": "Intra-SSID",
    "interference_mode_all": "Todos SSID",
    "interference_colorbar": "Riesgo interferencia %",
    "interference_legend_title": "Riesgo AP",
    "interference_low": "bajo",
    "interference_medium": "medio",
    "interference_high": "alto",
    "interference_top_risk": "Riesgo max",
    "interference_summary_title": "Resumen interferencia",
    "interference_summary_band": "Banda",
    "interference_summary_max_risk": "Riesgo máximo",
    "interference_summary_point": "Punto",
    "interference_summary_serving_ap": "AP servidor",
    "interference_summary_serving_role": "Rol servidor",
    "interference_summary_serving_channel": "Canal servidor",
    "interference_summary_serving_width": "Ancho servidor",
    "interference_summary_serving_dbm": "Señal servidor",
    "interference_summary_interferer": "Interferente principal",
    "interference_summary_interferer_role": "Rol interferente",
    "interference_summary_interferer_ssid": "SSID interferente",
    "interference_summary_interferer_channel": "Canal interferente",
    "interference_summary_interferer_width": "Ancho interferente",
    "interference_summary_interferer_dbm": "Señal interferente",
    "interference_summary_test_ignored": "AP test ignorados",
    "interference_overlap": "Overlap",
    "interference_contributors": "Interferentes",
    "interference_ignored": "Ignorados",
    "interference_ignored_same_ap": "mismo AP",
    "interference_ignored_test_ap": "AP test",
    "interference_channel_change": "Cambio canal",
    "interference_channel_change_note": "{ap} cambió de canal durante el estudio ({channels} -> {current}); los mapas sensibles al canal usan el último canal {current}.",
    "interference_channel_change_manual_note": "{ap} usa canal de análisis manual {current}; canales observados: {channels}.",
    "interference_summary_diagnosis": "Diagnóstico",
    "interference_diagnosis_low": "El riesgo principal es bajo: la coexistencia AP no parece crítica aquí.",
    "interference_diagnosis_same_channel_strong": "El problema principal es un interferente fuerte en el mismo canal que el AP servidor.",
    "interference_diagnosis_same_channel": "El problema principal es un AP en el mismo canal que el AP servidor.",
    "interference_diagnosis_wide_channel": "El problema principal es el overlap causado por canales anchos.",
    "interference_diagnosis_strong": "El problema principal es un interferente fuerte en un canal que aporta riesgo.",
    "interference_diagnosis_nearby": "El problema principal parece ser un canal cercano o parcialmente solapado.",
    "interference_quality_title": "Calidad datos interferencia",
    "interference_quality_width_coverage": "Ancho canal disponible: {available}/{total} puntos ({percent}%).",
    "interference_quality_good": "La estimación usa ancho canal en una proporción suficiente de puntos.",
    "interference_quality_warning": "El ancho canal está disponible en pocos puntos: la estimación usa fallback donde falta el dato.",
    "interference_quality_warning_5ghz": "El ancho canal está disponible en pocos puntos: en 5/6 GHz la estimación puede subestimar overlap entre canales anchos.",
    "usable_only": "Solo >= -70 dBm",
    "survey_bounds": "Límite estudio",
    "max_distance_px": "Distancia max (px)",
    "interpolation": "Interpolación",
    "interpolation_rbf": "RBF suave",
    "interpolation_linear": "Lineal",
    "aggregation": "Agregación punto",
    "aggregation_max": "Mejor",
    "aggregation_mean": "Media",
    "aggregation_median": "Mediana",
    "color_scale": "Escala color",
    "color_scale_fixed": "Fija",
    "color_scale_auto": "Automática",
    "smoothing": "Suavizado",
    "theme": "Tema",
    "qt_theme_light": "Azul arena",
    "qt_theme_soft": "Oliva suave",
    "qt_theme_dark": "Azul pizarra",
    "qt_theme_contrast": "Verde grafito",
    "close": "Cerrar",
    "cancel": "Cancelar",
    "select_plan_title": "Seleccionar plano",
    "images": "Imágenes",
    "load_plan_first": "Cargue primero un plano.",
    "warning": "Advertencia",
    "empty_csv": "El estudio está vacío.",
    "no_ssid": "No hay SSID disponible.",
    "select_ssid_heatmap": "Seleccione un SSID para exportar el mapa.",
    "insufficient_data_title": "Datos insuficientes",
    "insufficient_data": "Se requieren al menos 3 puntos para generar un heatmap en {band}.",
    "interference_requires_band": "Seleccione 2.4 GHz, 5 GHz o 6 GHz para el mapa de interferencia.",
    "save_required_title": "Guardado requerido",
    "save_required": "Debe guardar el CSV del estudio antes de exportar el PDF.",
    "save_failed": "Guardado cancelado. Heatmap no generado.",
    "heatmap_generated": "Heatmap generado",
    "file_created": "Archivo creado:\n{path}",
    "files_created": "Archivos creados:\n{paths}",
    "unsaved_changes_title": "Estudio sin guardar",
    "unsaved_changes": "Hay cambios sin guardar.\n\n¿Guardar el estudio antes de salir?",
    "survey_saved": "Estudio guardado: {name}",
    "best": "Mejor",
    "confidence": "confianza",
    "connected_ssid_option": "{ssid} (conectado)",
    "relevant_networks_title": "Redes relevantes",
    "relevant_networks_first_message": "Seleccione los SSID relevantes para este estudio. Todas las redes se guardarán, pero estas se comprobarán en los siguientes puntos.",
    "new_relevant_networks_title": "Nuevas redes detectadas",
    "new_relevant_networks_message": "Se detectaron nuevos SSID. Seleccione los que sean relevantes para este estudio.",
    "missing_relevant_networks_title": "Redes relevantes ausentes",
    "missing_relevant_networks_message": "Estas redes relevantes no se detectaron:\n{ssids}\n\n¿Guardar el punto igualmente, repetir el escaneo o cancelar?",
    "cancelled": "cancelado",
    "no_networks_found": "No se encontraron redes. Verifique que Wi-Fi esté activado.",
    "error": "Error",
    "point_saved": "Punto guardado: x={x}, y={y}, redes={count}",
    "scanning": "Escaneo Wi-Fi en curso en x={x}, y={y}...",
    "map_loaded_points": "Plano cargado. Puntos restaurados={count}. Estudio: {name}",
    "map_loaded": "Plano cargado. Estudio activo: {name}. Haga clic en su posición.",
    "map_not_found_title": "Plano no encontrado",
    "map_not_found": "El CSV referencia un plano que ya no existe:\n{path}\n\nSeleccione manualmente el plano actualizado.",
    "select_point": "Seleccione un punto en la tabla.",
    "no_point_to_delete": "No hay punto que borrar en esta sesión.",
    "last_point_deleted": "Último punto borrado: x={x}, y={y}, filas eliminadas={rows}",
    "point_deleted": "Punto borrado: x={x}, y={y}, filas eliminadas={rows}",
    "zoom": "Zoom: {zoom:.0%}",
    "survey_zoom": "Zoom estudio: {zoom:.0%}",
    "survey_zoom_empty": "Zoom estudio: -",
    "live_zoom": "Zoom mapa Live: {zoom:.0%}",
    "live_zoom_empty": "Zoom mapa Live: -",
    "all_bands_label": "todas bandas",
    "help_title": "Centro de ayuda",
    "help_overview_nav": "Workflow recomendado",
    "help_overview_title": "Workflow recomendado de estudio",
    "help_overview_subtitle": "Use la aplicación como workflow de validación: recoger evidencia, revisar calidad, corregir modelo AP y exportar.",
    "help_controls_nav": "Controles",
    "help_controls_title": "Guía rápida de controles",
    "help_controls_subtitle": "El estudio usa gestos directos sobre el mapa. Estos son los controles más frecuentes.",
    "help_control_right_click_title": "Clic derecho",
    "help_control_right_click_text": "Crea un punto de medición en el mapa Estudio. En modo Límites, arrastrar con clic derecho dibuja o borra la máscara.",
    "help_control_left_click_title": "Clic izquierdo",
    "help_control_left_click_text": "Selecciona un punto de medición o usa el modo temporal activo, como calibración o posición AP.",
    "help_control_left_drag_title": "Clic izquierdo + arrastrar",
    "help_control_left_drag_text": "Desplaza el plano o el mapa Live cuando la vista es mayor que la viewport.",
    "help_control_scroll_title": "Rueda",
    "help_control_scroll_text": "Desplaza verticalmente listas, paneles y vistas de mapa.",
    "help_control_shift_title": "Shift + rueda",
    "help_control_shift_text": "Desplaza horizontalmente el plano o mapa Live cuando hay scroll horizontal.",
    "help_control_ctrl_title": "Ctrl + rueda",
    "help_control_ctrl_text": "Hace zoom en el plano o la vista previa del mapa Live.",
    "help_survey_nav": "Estudio y escaneos",
    "help_survey_title": "Puntos, escaneos brutos y confianza",
    "help_survey_subtitle": "Un punto es más que una señal: la app guarda muestras brutas, las agrega y calcula confianza.",
    "help_quality_nav": "Calidad estudio",
    "help_quality_title": "Dashboard calidad estudio",
    "help_quality_subtitle": "El dashboard separa evidencia de escaneo, diagnóstico de modelo AP y puntos a revisar antes de confiar en mapas.",
    "help_ap_groups_nav": "Grupos AP",
    "help_ap_groups_title": "Grupos AP, roles y metadatos",
    "help_ap_groups_subtitle": "AP Group Manager convierte BSSID brutos en un modelo de AP físico usado por mapas y controles de calidad.",
    "help_live_maps_nav": "Mapas Live",
    "help_live_maps_title": "Mapas Live y opciones",
    "help_live_maps_subtitle": "El Mapa Live es la superficie principal de revisión tras calidad y modelo AP.",
    "help_reports_nav": "Reportes PDF",
    "help_reports_title": "Reportes PDF Live",
    "help_reports_subtitle": "La exportación PDF captura opciones del mapa Live y añade páginas de diagnóstico cuando el tipo de mapa lo soporta.",
    "help_diagnostics_nav": "Advertencias",
    "help_diagnostics_title": "Advertencias y diagnósticos",
    "help_diagnostics_subtitle": "Las advertencias piden revisar supuestos; no prueban automáticamente que un punto esté mal.",
    "help_glossary_nav": "Glosario",
    "help_glossary_title": "Glosario",
    "help_glossary_subtitle": "Términos usados por el workflow de estudio y reportes.",
    "help_legal_nav": "Acerca de y legal",
    "help_legal_title": "Acerca de, licencia y uso responsable",
    "help_legal_subtitle": "Identidad de la app, licencia del proyecto, avisos de terceros y límites de uso.",
    "help_overview_body": """
        <table class="callout-table"><tr><td class="callout-accent-good"></td><td class="callout-content"><span class="callout-label">Regla principal</span><br>No confíes en un mapa hasta que los datos del estudio y el modelo AP sean suficientemente coherentes.</td></tr></table>
        <h2>Workflow</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>1. Preparar</b><br>Crea o abre un estudio, elige unidades, carga el plano y calibra la escala.</td><td class="workflow-gap"></td><td class="workflow-card"><b>2. Medir</b><br>Coloca puntos donde trabajan o hacen roaming los clientes. Recoge varios escaneos por punto.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>3. Validar</b><br>Revisa Calidad estudio, redes relevantes, AP Memory, roles, metadatos y posiciones AP.</td><td class="workflow-gap"></td><td class="workflow-card"><b>4. Exportar</b><br>Lee los mapas Live y exporta HTML solo después de validar los datos.</td></tr></table>
        <h2>Puntos de decisión</h2>
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Orden recomendado</span><br>Corrige primero los puntos a reescanear, luego el modelo AP y después los mapas. Los warnings son hipótesis a revisar, no errores automáticos.</td></tr></table>
    """,
    "help_controls_body": """
        <h2>Gestos del mapa</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>Clic derecho</b><br>Añade un punto de medición. En modo Límites, arrastrar con clic derecho dibuja o borra la máscara.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Clic izquierdo</b><br>Selecciona un marcador o ejecuta el modo temporal activo, por ejemplo calibración o posición AP.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Arrastrar</b><br>Desplaza el plano o el mapa Live cuando la vista supera la viewport.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Rueda</b><br>Scroll vertical; Shift + rueda para horizontal; Ctrl + rueda para zoom.</td></tr></table>
        <h2>Overlays</h2>
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Grid y Límites</span><br>Grid y Límites son overlays alternativos. La escala calibrada sigue siendo común.</td></tr></table>
    """,
    "help_survey_body": """
        <h2>Archivos del estudio</h2>
        <table class="survey-grid"><tr><td class="survey-card"><span class="survey-card-title">CSV</span><br>Datos agregados y metadatos.</td><td class="survey-gap"></td><td class="survey-card"><span class="survey-card-title">.scan</span><br>Muestras brutas repetidas.</td><td class="survey-gap"></td><td class="survey-card"><span class="survey-card-title">Plano</span><br>PDF/imagen o plano generado.</td></tr></table>
        <h2>Recogida</h2>
        <p>Coloca puntos en las zonas realmente usadas: puestos de trabajo, salas, pasillos, puertas y áreas problemáticas. Para un estudio preciso, apunta a unos 2-3 m entre puntos cuando el espacio lo permita.</p>
        <h2>Redes relevantes</h2>
        <p>Los SSID relevantes guían los controles de calidad, los mapas Live y los reportes. Todas las redes se conservan, pero solo las relevantes definen las expectativas del estudio.</p>
    """,
    "help_quality_body": """
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Leer antes de los mapas</span><br>Calidad estudio indica si hay que corregir puntos, scanner o modelo AP antes de interpretar los mapas.</td></tr></table>
        <h2>KPI</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>Puntos</b><br>Redes ausentes, pocos datos, baja confianza, señal inestable o roaming del cliente.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Modelo AP</b><br>AP Memory, posiciones, metadatos, cambios de canal y findings de AP dominante.</td></tr></table>
        <h2>Acciones</h2>
        <p>Las tarjetas KPI abren listas de puntos o Extra Details. Usa Ir al punto, Abrir grupo AP o Abrir metadatos AP para corregir el elemento afectado.</p>
    """,
    "help_ap_groups_body": """
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Regla del modelo AP</span><br>El programa puede sugerir grupos, pero el modelo final debe representar los AP físicos reales.</td></tr></table>
        <h2>Grupos AP</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>Evidencia</b><br>BSSID, SSID, bandas, canales e historial de señal describen lo observado.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Modelo usuario</b><br>Alias, rol, posición, metadatos y overrides describen el despliegue esperado.</td></tr></table>
        <h2>Gestor BSSID</h2>
        <p>Usa filtros de scope, banda, canal y búsqueda para aislar los BSSID que deban moverse, separarse o confirmarse.</p>
        <h2>Metadatos</h2>
        <p>Vendor, modelo, montaje, bandas/canales esperados y override de canal de análisis mejoran los diagnósticos y reportes.</p>
    """,
    "help_live_maps_body": """
        <h2>Tipos de mapa</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>Cobertura</b><br>Señal estimada en dBm para un SSID y una banda.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Interferencia</b><br>Riesgo ligado a canales, anchos e AP interferentes.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Canales AP</b><br>Vista discreta de los canales observados.</td><td class="workflow-gap"></td><td class="workflow-card"><b>AP dominante</b><br>AP más fuerte y zonas de roaming potencial.</td></tr></table>
        <h2>Opciones</h2>
        <p>SSID, banda, tipo de mapa, labels, interpolación, smoothing, distancia máxima, grupo AP y Survey Bounds se memorizan por tipo de mapa durante la sesión.</p>
        <h2>Límites</h2>
        <p>Si existe una máscara de Límites, sustituye el límite automático en los mapas continuos y los exports HTML soportados.</p>
    """,
    "help_reports_body": """
        <h2>Exportación PDF</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>Precondición</b><br>El estudio debe guardarse antes de exportar.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Opciones activas</b><br>El PDF usa el estado actual del mapa Live: SSID, banda, tipo de mapa, colores, labels y límites.</td></tr></table>
        <h2>Página mapa</h2>
        <p>La primera página renderiza el mapa sobre el plano independientemente del zoom/pan actual. El fondo uniforme no usado puede recortarse si no contiene puntos ni marcadores AP.</p>
        <h2>Páginas diagnóstico</h2>
        <p>Interferencia y AP dominante pueden añadir páginas de problemas con callouts numerados y tarjetas de detalle.</p>
    """,
    "help_diagnostics_body": """
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Regla warning</span><br>Un warning indica una hipótesis a verificar: escaneo, modelo AP, canal, posición o comportamiento RF real.</td></tr></table>
        <h2>Patrones frecuentes</h2>
        <p>Red relevante ausente, baja confianza, señal inestable, detalles scanner limitados, AP sin posición, metadatos incoherentes o canal cambiado.</p>
        <h2>Prioridad</h2>
        <p>Corrige los problemas de puntos antes que los del modelo, y luego vuelve a leer los mapas Live y los HTML.</p>
    """,
    "help_glossary_body": """
        <h2>Evidencia Wi-Fi</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>SSID</b><br>Nombre de red Wi-Fi.</td><td class="workflow-gap"></td><td class="workflow-card"><b>BSSID</b><br>Dirección MAC radio vista en los escaneos.</td></tr></table>
        <h2>Modelo AP</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>Grupo AP</b><br>Modelo de un AP físico, a menudo con varios BSSID.</td><td class="workflow-gap"></td><td class="workflow-card"><b>AP dominante</b><br>Grupo AP con la señal observada más fuerte en el punto.</td></tr></table>
        <h2>Mapas y reportes</h2>
        <p>Interpolación, distancia máxima, Survey Bounds y máscara de Límites controlan dónde y cómo se extiende el render visual entre mediciones reales.</p>
    """,
    "help_legal_body": """
        <h2>Aplicación</h2>
        <table class="workflow-grid"><tr><td class="workflow-card"><b>Producto</b><br>Wi-Fi RF Survey Analyzer</td><td class="workflow-card"><b>Versión</b><br>{version}</td></tr><tr><td class="workflow-vertical-gap" colspan="2"></td></tr><tr><td class="workflow-card"><b>Copyright</b><br>{copyright}</td><td class="workflow-card"><b>Licencia</b><br>{license_name} (<code>{license_id}</code>)<br>{license_url}</td></tr></table>
        <h2>Uso responsable</h2>
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Solo redes autorizadas</span><br>Este software está destinado a análisis, estudios y troubleshooting Wi-Fi legítimos sobre redes propias o que tienes autorización para evaluar.</td></tr></table>
        <h2>Componentes de terceros</h2>
        <p>Consulta <code>THIRD_PARTY_LICENSES</code> para las licencias de las dependencias.</p>
    """,
    "help_commands": "Comandos",
    "help_workflow": "Workflow",
    "help_workflow_title": "Cómo usar el programa",
    "help_live": "Mapa Live",
    "help_live_title": "Cómo usar el mapa Live",
    "help_heatmap": "Heatmap",
    "help_heatmap_title": "Cómo leer y generar el heatmap",
    "help_scan": "Escaneo",
    "help_scan_title": "Cómo gestionar escaneos Wi-Fi",
    "keep_scan": "Guardar escaneo",
    "retry_scan": "Reintentar",
    "cancel_point": "Cancelar punto",
})

TRANSLATIONS.update({
    "start_workflow_title": "Flujo de trabajo",
    "measurement_system_imperial": "Imperial (pies)",
    "workspace_settings_section": "Área de trabajo",
    "quality_dashboard_metric_scan_ok": "Escaneos OK",
    "quality_dashboard_metric_ap_diagnostic_points": "Hallazgos AP dominante",
    "quality_dashboard_ap_position_finding": "Hallazgo: {finding}",
    "quality_dashboard_scanner_details_fallback_suffix": " (respaldo)",
    "max_distance_unit": "Distancia max ({unit})",
    "max_distance_m": "Distancia max (m)",
    "ap_group_bssid_other_group": "Otro grupo",
    "ap_group_bssid_scope_all": "Todos",
    "ap_group_empty_selection": "El grupo debe contener al menos un BSSID.",
    "ap_group_split_source_empty": "Deje al menos un BSSID en el grupo actual antes de crear un grupo nuevo.",
    "ap_group_move_no_target": "No hay otro grupo AP al que mover los BSSID seleccionados.",
    "ap_group_move_target_title": "Mover BSSID",
    "ap_group_move_target_prompt": "Grupo AP destino:",
    "ap_group_move_target_with_alias": "{alias} ({group}, {count} BSSID)",
    "ap_group_move_target_without_alias": "{group} ({count} BSSID)",
    "ap_group_fix_from_warning": "Corregir grupo AP",
    "ap_group_conflict_count": "Conflictos posibles: {count}",
    "ap_group_conflict_details": "Detalles de advertencia",
    "ap_group_conflict_none": "Sin advertencias en el grupo seleccionado.",
    "ap_group_conflict_group": "Grupo AP: {group}",
    "ap_group_conflict_details_title": "Canales observados",
    "ap_group_conflict_band_summary": "{band}: {channel_count} canales, {bssid_count} BSSID ({channels})",
    "ap_group_conflict_band_row": "Banda {band}: canales {channels}",
    "ap_group_memory_menu": "Memoria",
    "ap_group_confirm_memory": "Confirmar memoria",
    "ap_group_confirm_memory_selected": "Confirmar selección",
    "ap_group_confirm_memory_all": "Confirmar todo desde memoria...",
    "ap_group_confirm_memory_all_title": "Confirmar Memoria AP",
    "ap_group_confirm_memory_all_confirm": "¿Confirmar {count} grupos AP aplicados desde Memoria AP?",
    "ap_group_update_from_memory": "Actualizar desde memoria",
    "ap_group_update_memory_selected": "Actualizar selección desde memoria",
    "ap_group_status_warning_tooltip": "Este grupo AP tiene diagnósticos de advertencia.",
    "ap_group_status_memory_tooltip": "Se aplicaron metadatos desde Memoria AP. Revise y confirme, o edite los datos AP.",
    "ap_group_status_memory_update_tooltip": "Memoria AP contiene datos guardados diferentes para: {fields}. Use Actualizar desde memoria para alinear este grupo AP.",
    "ap_group_delete_alias": "Borrar alias...",
    "ap_group_role": "Rol",
    "ap_group_role_title": "Rol del grupo AP",
    "ap_group_role_prompt": "Rol que se asignará a este grupo AP:",
    "ap_group_role_internal": "Interno",
    "ap_group_role_external": "Externo",
    "ap_group_role_interferer": "Interferente",
    "ap_group_role_test": "Prueba/oculto",
    "ap_group_metadata": "Metadatos",
    "ap_group_metadata_hint": "Añada información descriptiva del AP físico. Las bandas y canales esperados son guiados porque los controles de calidad los usan.",
    "ap_group_metadata_vendor": "Fabricante",
    "ap_group_metadata_model": "Modelo",
    "ap_group_metadata_mounting": "Montaje",
    "ap_group_metadata_expected_bands": "Bandas esperadas",
    "ap_group_metadata_expected_channels": "Canales esperados",
    "ap_group_metadata_band": "Banda",
    "ap_group_metadata_channels": "Canales",
    "ap_group_metadata_selected_channels": "Selección activa",
    "ap_group_metadata_edit_channels": "Canales...",
    "ap_group_metadata_channel_picker_title": "Canales {band}",
    "ap_group_metadata_no_channels": "Sin canal seleccionado",
    "ap_group_metadata_band_disabled": "Banda no seleccionada",
    "ap_group_metadata_channels_unavailable": "Canales no disponibles",
    "ap_group_metadata_channel_group_5_low": "5 GHz bajos",
    "ap_group_metadata_channel_group_5_high": "5 GHz altos",
    "ap_group_metadata_select_all": "Todos",
    "ap_group_metadata_clear": "Ninguno",
    "ap_group_metadata_analysis_channels": "Canal de análisis forzado",
    "ap_group_metadata_analysis_channel_hint": "Usado por mapas sensibles al canal cuando este AP cambió de canal durante el estudio. Deje Auto para usar el último canal limpio.",
    "ap_group_metadata_analysis_channel": "Canal de análisis",
    "ap_group_metadata_analysis_channel_not_observed": "No observado",
    "ap_group_metadata_coverage_scope": "Ámbito de cobertura",
    "ap_group_metadata_coverage_expected_area": "Área esperada",
    "ap_group_metadata_coverage_site_wide": "Todo el sitio",
    "ap_group_metadata_coverage_local": "Área local",
    "ap_group_metadata_coverage_radius": "Radio local",
    "ap_group_metadata_coverage_auto_area": "Área auto",
    "ap_group_metadata_coverage_hint": "Elija si este AP se espera en todo el estudio o solo cerca de su área local.",
    "ap_group_metadata_coverage_site_wide_hint": "Los controles de calidad tratan este AP/red como parte de toda el área estudiada.",
    "ap_group_metadata_coverage_local_hint": "Los controles de calidad pueden limitar este AP/red a su área local. Área auto funciona mejor con posición AP y escala calibrada; si no, usa evidencia de señal.",
    "ap_group_metadata_notes": "Notas",
    "ap_group_position": "Posición",
    "ap_group_position_tooltip_title": "Posición AP",
    "ap_position_pick": "Clic izquierdo en el plano para fijar la posición física de {group}. Esc cancela.",
    "ap_position_saved": "Posición AP guardada: {group} x={x}, y={y}.",
    "ap_position_cancelled": "Colocación AP cancelada.",
    "ap_position_distance": "Distancia AP",
    "ap_position_nearest": "AP físico más cercano",
    "ap_position_analysis": "Análisis de posición",
    "ap_position_detail": "Detalle posición",
    "ap_position_ok": "Coherente",
    "ap_position_no_scale": "Escala no calibrada",
    "ap_position_strong_far": "Señal fuerte lejos del AP",
    "ap_position_weak_close": "Señal débil cerca del AP",
    "ap_position_unexpected_dominant": "El AP dominante no está físicamente cerca",
    "ap_position_warning_legend": "Triángulo = posición AP sospechosa",
    "ap_position_unknown_warning": "Advertencia posición",
    "ap_group_not_found": "Grupo AP no encontrado.",
    "ap_group_alias_title": "Alias de grupo AP",
    "ap_group_alias_prompt": "Alias que se usará para este AP:",
    "help_workflow": "Flujo de trabajo",
    "help_heatmap": "Mapa de calor",
    "help_workflow_steps": (
        "1-a. Cree un estudio nuevo y cargue el plano.\n"
        "1-b. O abra un estudio guardado: el plano se cargará automáticamente.\n"
        "2. Desplácese físicamente por el área y use clic derecho en el mapa para registrar puntos de medición.\n"
        "3. Use Grupos AP para asignar alias, corregir grupos y colocar posiciones físicas de AP cuando se conozcan.\n"
        "4. Guarde el estudio después de recoger suficientes puntos.\n"
        "5. Abra el Mapa Live y elija SSID, banda Wi-Fi y tipo de análisis.\n"
        "6. Use Cobertura señal para el nivel dBm, Interferencia AP para solapes, Canales AP para canales y AP dominante para roaming."
    ),
    "help_live_steps": (
        "El Mapa Live muestra una vista previa del estudio y puede exportar la vista actual a HTML.\n"
        "Elija SSID, banda y tipo de mapa directamente en el Mapa Live.\n"
        "Cobertura señal e Interferencia AP se calculan en segundo plano para mantener la interfaz utilizable.\n"
        "Canales AP y AP dominante muestran puntos reales con leyenda dedicada.\n"
        "En AP dominante, un triángulo amarillo marca una posible advertencia de posición AP: el tooltip muestra distancia al AP dominante y al AP físico más cercano.\n"
        "El zoom Live no regenera el mapa: redimensiona la vista previa y afina la calidad tras una breve pausa."
    ),
    "help_heatmap_steps": (
        "Cobertura señal genera un mapa de calor dBm continuo por SSID y banda.\n"
        "RBF suave crea una visualización más continua; Lineal es más conservador.\n"
        "Distancia max limita el mapa a zonas cercanas a puntos reales y reduce formas inventadas.\n"
        "Solo >= -70 dBm resalta áreas normalmente utilizables.\n"
        "Interferencia AP calcula riesgo porcentual y añade los principales problemas al HTML.\n"
        "Canales AP no interpola: muestra puntos reales coloreados por canal, con CH 36 / 80 cuando hay ancho de canal.\n"
        "AP dominante muestra qué AP es más fuerte en cada punto y marca en amarillo donde el segundo AP está a 5 dB o menos."
    ),
    "help_scan_steps": (
        "Nuevo estudio guarda el receptor elegido; cada captura lo usa mediante lswifi.\n"
        "lswifi es preferible porque suele detectar más BSSID y más detalle radio.\n"
        "Cuando lswifi lo proporciona, el ancho de canal se guarda en channel_width_mhz.\n"
        "Si falta el receptor, la captura se detiene sin cambiar de adaptador ni recurrir a netsh.\n"
        "Si un escaneo ve muchos menos redes que el anterior, se marca como sospechoso.\n"
        "Cuando un escaneo es sospechoso, repítalo antes de guardar el punto.\n"
        "Con Recordar elección, el programa guarda automáticamente el mismo SSID mientras se detecte."
    ),
    "help_commands_text": (
        "Clic derecho en el mapa: crea un punto de estudio; en modo Límites, arrastrar con clic derecho dibuja o borra la máscara.\n"
        "Mantener botón izquierdo: desplaza el mapa.\n"
        "Clic izquierdo sobre un marcador: selecciona el punto.\n"
        "Rueda del ratón: desplazamiento vertical.\n"
        "Shift + rueda: desplazamiento horizontal.\n"
        "Ctrl + rueda: zoom."
    ),
    "help_overview_body": """
        <table class="callout-table"><tr><td class="callout-accent-good"></td><td class="callout-content"><span class="callout-label">Regla principal</span><br>El mapa es la salida final del estudio, no la primera prueba. Antes de usarlo para decidir, confirme que los puntos, los escaneos brutos y el modelo AP describen correctamente el sitio.</td></tr></table>
        <h2>Secuencia operativa</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr><td class="workflow-card"><div class="step-label">1. Preparar</div><div class="step-title">Definir el alcance</div><p>Cree o abra el estudio, elija métrico o imperial, cargue el plano si existe, calibre la escala y seleccione los SSID relevantes.</p><div class="step-gate"><b>Avance cuando:</b> plano, escala y redes a evaluar sean correctos.</div></td><td class="workflow-gap"></td><td class="workflow-card"><div class="step-label">2. Medir</div><div class="step-title">Recoger evidencia RF</div><p>Coloque puntos en salas, pasillos, áreas de transición, puertas y zonas donde los usuarios reportan problemas.</p><div class="step-gate"><b>Avance cuando:</b> las áreas importantes tengan suficientes puntos y los escaneos sospechosos se hayan repetido.</div></td></tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr><td class="workflow-card"><div class="step-label">3. Validar</div><div class="step-title">Leer Calidad estudio</div><p>Separe problemas de punto a reescanear de diagnósticos de configuración AP. Una advertencia es una hipótesis que revisar, no un error automático.</p><div class="step-gate"><b>Avance cuando:</b> la calidad de puntos sea aceptable y los hallazgos restantes estén entendidos.</div></td><td class="workflow-gap"></td><td class="workflow-card"><div class="step-label">4. Modelar AP</div><div class="step-title">Hacer creíble el modelo</div><p>Revise grupos AP, alias, roles, BSSID, metadatos, posiciones físicas, canales de análisis forzados y estados de Memoria AP.</p><div class="step-gate"><b>Avance cuando:</b> el modelo AP coincida con el despliegue o las incógnitas queden documentadas.</div></td></tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr><td class="workflow-card" colspan="3"><div class="step-label">5. Analizar</div><div class="step-title">Usar mapas como resultado revisado</div><p>Use mapas Live y HTML para leer cobertura, canales, roaming e interferencias después de revisar los datos.</p><div class="step-gate"><b>Avance cuando:</b> las advertencias hayan sido revisadas y puedan explicarse.</div></td></tr>
        </table>
        <h2>Puertas de decisión</h2>
        <div class="gate-list">
            <div class="gate-row"><b>Distancias:</b> el sistema de medida pertenece al estudio. Cambiar unidades tras calibrar elimina la escala; vuelva a calibrar antes de leer distancias, cuadrícula o posiciones AP.</div>
            <div class="gate-row"><b>Cobertura:</b> revise SSID relevantes y calidad de puntos antes de interpretar zonas rojas o verdes.</div>
            <div class="gate-row"><b>Interferencias:</b> valide grupos AP, roles, cambios de canal y overrides de análisis antes de confiar en mapas sensibles al canal.</div>
            <div class="gate-row"><b>Exportación:</b> abra el mapa Live correspondiente y lea tooltips o detalles antes de generar el informe HTML.</div>
        </div>
        <table class="section-card callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Cómo piensa la aplicación</span><br>Puntos, escaneos brutos, metadatos, Memoria AP y posiciones físicas son evidencia. El programa señala qué supuesto revisar: calidad del punto, agrupación AP, modelo de canal, posición física o comportamiento RF real.</td></tr></table>
    """,
    "help_controls_body": """
        <table class="callout-table" width="100%" cellspacing="0" cellpadding="0"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Regla de gestos</span><br>Clic izquierdo, arrastrar con clic izquierdo y rueda con modificadores son controles distintos. Ctrl y Shift importan cuando se combinan con la rueda.</td></tr></table>
        <h2>El contexto importa</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr><td class="workflow-card"><b>Mapa de estudio normal</b><br>El clic derecho crea un punto de medición. El clic izquierdo selecciona un marcador existente o limpia la selección al hacer clic en el fondo.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Modos temporales</b><br>Calibración de escala y colocación AP capturan el clic izquierdo hasta completar o cancelar la acción.</td></tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr><td class="workflow-card"><b>Modo Límites</b><br>Vista &gt; Límites convierte el mapa Estudio en editor de máscara. Arrastrar con clic derecho dibuja o borra con el pincel elegido; selección, zoom y pan siguen disponibles.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Cuadrícula y Límites</b><br>Son overlays alternativos: activar uno desactiva el otro. La escala calibrada sigue siendo común.</td></tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr><td class="workflow-card"><b>Arrastrar no es clic</b><br>Un clic selecciona; arrastrar desplaza el plano o el Mapa Live cuando la vista supera la ventana.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Zoom/pan son visuales</b><br>Zoom, scroll y pan no cambian puntos ni escaneos guardados.</td></tr>
        </table>
        <h2>Rueda y navegación</h2>
        <table class="gate-list">
            <tr><td class="gate-row"><b>Rueda:</b> desplazamiento vertical en listas, paneles y mapas.</td></tr>
            <tr><td class="gate-row"><b>Shift + rueda:</b> desplazamiento horizontal cuando el contenido supera el ancho visible.</td></tr>
            <tr><td class="gate-row"><b>Ctrl + rueda:</b> zoom del plano o vista Live. El zoom Live redimensiona la imagen y afina la calidad tras una breve pausa, sin recalcular datos.</td></tr>
        </table>
    """,
    "help_survey_body": """
        <h2>Bloques de la pantalla Estudio</h2>
        <table class="survey-grid">
            <tr><td class="survey-card"><span class="survey-card-title">CSV</span><br>Archivo principal con filas agregadas y comentarios de metadatos.<br><span class="survey-card-use">Guárdelo antes de exportar HTML o mover el estudio entre equipos.</span></td><td class="survey-gap"></td><td class="survey-card"><span class="survey-card-title">Plano</span><br>PDF/imagen vinculado al estudio. Un estudio nuevo puede empezar con un blanco ya escalado.<br><span class="survey-card-use">Si no se carga un plano real, se escribe un PNG con el mismo nombre junto al CSV.</span></td><td class="survey-gap"></td><td class="survey-card"><span class="survey-card-title">Puntos</span><br>Posiciones de medición colocadas sobre el plano.<br><span class="survey-card-use">Añádalas donde los clientes trabajan, hacen roaming o reportan problemas.</span></td></tr>
            <tr><td class="survey-vertical-gap" colspan="5"></td></tr>
            <tr><td class="survey-card"><span class="survey-card-title">Escaneos brutos</span><br>Muestras repetidas conservadas en el sidecar <code>.scan</code>.<br><span class="survey-card-use">Más evidencia bruta mejora confianza y diagnósticos.</span></td><td class="survey-gap"></td><td class="survey-card"><span class="survey-card-title">Grupos AP</span><br>Modelo de AP físicos usado por mapas y calidad.<br><span class="survey-card-use">Revíselo antes de AP dominante, Interferencia o Canales AP.</span></td><td class="survey-gap"></td><td class="survey-card"><span class="survey-card-title">SSID relevantes</span><br>Redes consideradas importantes por controles de calidad.<br><span class="survey-card-use">Gestionar añade o quita SSID; Limpiar borra la selección.</span></td></tr>
        </table>
        <h2>Qué se guarda</h2>
        <p>Cada punto puede contener varias redes observadas. El CSV principal guarda las filas agregadas usadas por los mapas. El archivo <code>.scan</code> vinculado conserva muestras repetidas, backend de escaneo y detalles radio disponibles.</p>
        <h2>SSID relevantes</h2>
        <p>Los SSID relevantes indican al motor de calidad qué redes deben estar presentes. La ausencia de una red relevante se convierte en hallazgo de calidad; la ausencia de un vecino no relevante normalmente no. Defínalos pronto para no descubrir tarde que hay puntos que revisar.</p>
        <h2>Sidecar de escaneos brutos</h2>
        <table><tr><th>Valor guardado</th><th>Por qué importa</th></tr><tr><td>Mediana dBm</td><td>Reduce el efecto de un pico temporal de señal.</td></tr><tr><td>Min/max dBm</td><td>Muestra cuánto varió la señal durante escaneos repetidos.</td></tr><tr><td>Muestras vistas/total</td><td>Alimenta confianza y detección de datos escasos.</td></tr><tr><td>Banda, frecuencia, ancho canal</td><td>Mejora Canales AP, Interferencia y lectura 6 GHz.</td></tr></table>
        <h2>Backend scanner</h2>
        <table><tr><th>Backend</th><th>Uso</th><th>Notas</th></tr><tr><td>Captura del estudio</td><td>Receptor fijo</td><td>Usa <code>lswifi</code> con el ID del adaptador guardado. Si falta, la captura se detiene.</td></tr><tr><td>lswifi</td><td>Scanner preferido</td><td>Suele capturar más BSSID, banda, frecuencia, seguridad y ancho de canal.</td></tr><tr><td>netsh</td><td>Datos anteriores / diagnóstico</td><td>Instantánea no verificada con dBm estimados. No se usa como alternativa para capturas con receptor fijo.</td></tr></table>
        <h2>Colocación de puntos</h2>
        <table class="callout-table"><tr><td class="callout-accent-good"></td><td class="callout-content"><span class="callout-label">Regla de campo</span><br><ul><li>Coloque puntos en puestos, salas, pasillos, puertas y zonas problemáticas.</li><li>Para un estudio preciso, apunte a unos 2-3 m entre puntos cuando el espacio lo permita, y cierre la distancia en transiciones AP.</li><li>No escanee caminando: deténgase, espere a que termine el escaneo y avance.</li></ul></td></tr></table>
        <h2>Plano blanco, cuadrícula y límites</h2>
        <p>Un estudio puede empezar sin plano externo. La elección métrico/imperial crea un blanco preescalado, con cuadrícula activa. En planos reales, la cuadrícula aparece tras calibrar. Vista &gt; Límites permite dibujar una máscara PNG <code>&lt;survey&gt;.boundaries.png</code> con pincel circular o cuadrado de 20 a 120 px. Una máscara vacía equivale a no tener máscara.</p>
    """,
    "help_quality_body": """
        <table class="callout-table" width="100%" cellspacing="0" cellpadding="0"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Regla principal</span><br>Lea Calidad estudio antes de interpretar mapas Live o HTML. El dashboard indica si la evidencia de punto debe reescanearse, si el modelo AP necesita revisión o si los mapas pueden generarse con confianza razonable.</td></tr></table>
        <h2>Dos capas de lectura</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr><td class="workflow-card"><div class="step-label">Capa 1</div><div class="step-title">Calidad de puntos</div><p>Redes relevantes ausentes, datos escasos, detalles scanner limitados, baja confianza y señal inestable pertenecen a la evidencia del punto.</p><div class="step-gate"><b>Acción habitual:</b> enfocar el punto, inspeccionar filas, reescanear o recoger puntos cercanos.</div></td><td class="workflow-gap"></td><td class="workflow-card"><div class="step-label">Capa 2</div><div class="step-title">Modelo AP</div><p>Grupos AP, roles, metadatos, estado de memoria, cambios de canal y posiciones físicas explican cómo interpretar lo medido.</p><div class="step-gate"><b>Acción habitual:</b> abrir mapa, metadatos o gestor AP afectado y corregir el modelo.</div></td></tr>
        </table>
        <h2>Estado y alcance</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Estado superior</b><br>Coherente significa que los controles principales están limpios. Revisión recomendada indica uno o más puntos a revisar. Setup AP requiere atención significa que los puntos pueden ser utilizables, pero metadatos, memoria, canales o posiciones AP necesitan revisión.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Alcance del estudio</b><br>El bloque de contexto recuerda SSID relevantes, posiciones AP conocidas y AP de prueba excluidos. Los AP de Área local solo se esperan dentro de su ámbito local.</td></tr></table>
        <h2>Tarjetas KPI y detalles</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0">
            <tr><td class="workflow-card"><b>Listas de puntos</b><br>Puntos a revisar, redes ausentes, datos escasos, baja confianza, señal inestable y roaming cliente abren listas compactas con número, X/Y y problema específico.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Detalles extra</b><br>Detalles scanner, hallazgos AP dominante, advertencias config AP, cambios de canal, Memoria AP y AP sin posición abren tarjetas más detalladas.</td></tr>
            <tr><td class="workflow-vertical-gap" colspan="3"></td></tr>
            <tr><td class="workflow-card"><b>Acciones de mapa</b><br>Canales AP, Interferencia y AP dominante abren el Mapa Live con banda, grupo AP o punto relevante cuando el hallazgo tiene contexto visual.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Acciones de modelo AP</b><br>Abrir grupo AP o Metadatos AP lleva al editor que puede corregir el modelo.</td></tr>
        </table>
        <h2>Significado de KPI</h2>
        <table class="survey-grid"><tr><td class="survey-card"><b>Puntos del estudio</b><br>Total puntos mide evidencia espacial. Escaneo OK indica puntos utilizables. Puntos a revisar no significa reescanear todo: algunos requieren revisar AP o posición.</td><td class="survey-gap"></td><td class="survey-card"><b>Calidad escaneo</b><br>Red relevante ausente, datos escasos, detalles scanner limitados, baja confianza y señal inestable pueden debilitar todos los mapas.</td><td class="survey-gap"></td><td class="survey-card"><b>Modelo AP</b><br>Memoria AP, posiciones ausentes, metadatos incoherentes, canales cambiados y hallazgos AP dominante afectan sobre todo AP dominante, Canales AP, Interferencia y HTML.</td></tr></table>
        <h2>Orden de corrección</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>1. Corregir evidencia de punto</b><br>Reescanee o añada puntos si los datos brutos no son fiables.</td></tr><tr><td class="gate-row"><b>2. Corregir identidad y posición AP</b><br>Alias, roles, grupos BSSID y coordenadas AP deben representar el despliegue real.</td></tr><tr><td class="gate-row"><b>3. Corregir metadatos y canales</b><br>Bandas/canales esperados y override de análisis deciden si una advertencia es error o comportamiento previsto.</td></tr><tr><td class="gate-row"><b>4. Leer mapas</b><br>Interprete cobertura, roaming e interferencias solo después de estos controles.</td></tr></table>
    """,
    "help_ap_groups_body": """
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Regla del modelo AP</span><br>El agrupamiento automático es una hipótesis. El modelo final debe representar los AP físicos reales, con sus BSSID, roles, posiciones y metadatos.</td></tr></table>
        <h2>Dos tipos de información</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Evidencia observada</b><br>BSSID, SSID vistos, bandas, canales, ancho canal e historial de señal vienen de los escaneos.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Modelo del usuario</b><br>Alias, rol, posición, metadatos, ámbito de cobertura y canal de análisis describen lo que sabe del despliegue.</td></tr></table>
        <h2>Gestor BSSID</h2>
        <p>Use filtros de ámbito, banda, canal, estado y búsqueda para aislar los BSSID que corregir. Mover filas retira automáticamente los BSSID de otro grupo. Crear un grupo nuevo es útil cuando dos radios se fusionaron por error.</p>
        <h2>Roles AP</h2>
        <table class="survey-grid"><tr><td class="survey-card"><b>Interno</b><br>AP normal de la red analizada. Se usa para cobertura, AP dominante e interferencia.</td><td class="survey-gap"></td><td class="survey-card"><b>Externo</b><br>AP vecino o de terceros. Puede contribuir a interferencia, pero no se espera como cobertura interna.</td><td class="survey-gap"></td><td class="survey-card"><b>Prueba/oculto</b><br>AP que se ignora en mapas y diagnósticos principales, por ejemplo laboratorio o SSID temporal.</td></tr></table>
        <h2>Metadatos AP</h2>
        <p>Fabricante, modelo, montaje, notas, bandas esperadas y canales esperados enriquecen los diagnósticos. Si un AP cambia de canal durante el estudio, el canal de análisis forzado permite elegir qué canal usar en mapas sensibles al canal. Deje Auto cuando la última transición limpia sea fiable.</p>
        <h2>Ámbito de cobertura</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Todo el sitio</b><br>La red/AP se espera en toda el área estudiada. Una ausencia puede convertirse en advertencia de calidad.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Área local</b><br>La red/AP se espera solo cerca de su zona. Área auto funciona mejor con posición AP y escala calibrada; si no, usa evidencia de señal.</td></tr></table>
        <h2>Posiciones AP</h2>
        <p>Colocar físicamente los AP activa controles de distancia del mapa AP dominante. Señal fuerte lejos, señal débil cerca o un AP dominante que no es el más próximo se convierten en hallazgos que revisar. Pueden indicar mala posición, grupo AP incorrecto, roaming o propagación RF real.</p>
        <h2>Memoria AP</h2>
        <p>Memoria AP reutiliza alias, roles, metadatos, canales de análisis y posiciones compatibles en nuevos estudios. El estado Desde memoria pide confirmación: los datos se aplicaron, pero deben validarse en el contexto actual. Actualización memoria indica que el grupo actual difiere de la memoria guardada.</p>
        <table class="callout-table"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Control recomendado</span><br>Antes de exportar Interferencia o AP dominante, revise grupos con advertencia, cambios de canal y AP sin posición.</td></tr></table>
    """,
    "help_live_maps_body": """
        <h2>Tipos de mapa</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Cobertura señal</b><br>Mapa continuo de señal dBm por SSID y banda. Depende mucho de la calidad de puntos y distancia max.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Interferencia AP</b><br>Mapa de riesgo construido desde canal servidor, interferentes, ancho canal, roles AP y modo Intra-SSID/Todos SSID.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Canales AP</b><br>Vista discreta de puntos reales coloreados por canal. No inventa superficie entre mediciones.</td><td class="workflow-gap"></td><td class="workflow-card"><b>AP dominante</b><br>Muestra el grupo AP más fuerte por punto, zonas de roaming potencial y advertencias de posición si los AP están colocados.</td></tr></table>
        <h2>Opciones por mapa</h2>
        <p>SSID, banda, tipo de mapa, etiquetas, interpolación, suavizado, distancia max, grupo AP y límite estudio se memorizan por tipo de mapa durante la sesión. Cambiar de tipo puede restaurar las opciones usadas en la última lectura de ese mapa.</p>
        <h2>Interpolación, suavizado y distancia max</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>RBF suave:</b> genera una superficie continua, útil visualmente, pero puede parecer demasiado optimista lejos de los puntos.</td></tr><tr><td class="gate-row"><b>Lineal:</b> más conservador y cercano a los triángulos entre puntos, aunque a veces menos agradable visualmente.</td></tr><tr><td class="gate-row"><b>Distancia max:</b> limita el render alrededor de la evidencia medida. El valor automático se basa en la densidad de puntos cuando hay suficientes, y evita grandes zonas inventadas.</td></tr></table>
        <h2>Límites y máscara manual</h2>
        <p>El límite automático reduce el render fuera de la envolvente de puntos. Si existe una máscara Límites, tiene prioridad para mapas continuos y HTML soportados. El mejor resultado se obtiene cuando los puntos también siguen el borde real de las salas: mapa y máscara describen la misma geometría.</p>
        <h2>Tooltips y leyendas</h2>
        <p>Los tooltips Live están estructurados por secciones para lectura rápida: señal, radio, posición, interferencia, AP servidor, interferente, AP dominante o segundo AP según el mapa. Los mapas discretos usan la leyenda para centrarse en un AP o canal; doble clic en un elemento centra el punto o grupo en la vista.</p>
        <h2>Rendimiento</h2>
        <p>Cobertura e interferencia pueden tardar varios segundos en la primera apertura porque las superficies se calculan en segundo plano. Las actualizaciones posteriores reutilizan más estado. El zoom Live no recalcula datos: redimensiona la vista previa y afina el render tras una breve pausa.</p>
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Leer con prudencia</span><br>Un mapa continuo entre puntos separados sigue siendo una estimación. Si una zona es importante para una decisión, añada mediciones en lugar de confiar solo en interpolación.</td></tr></table>
    """,
    "help_reports_body": """
        <h2>Exportación PDF</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Precondición</b><br>El estudio debe guardarse antes de exportar para que CSV, plano, escaneos brutos y sidecars sean coherentes.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Opciones activas</b><br>El PDF usa el estado actual del Mapa Live: SSID, banda, tipo, escala color, etiquetas, límites, máscara y modelo AP.</td></tr></table>
        <h2>Página mapa</h2>
        <p>La primera página renderiza el mapa sobre el plano independientemente del zoom o pan actual. Los fondos uniformes no usados al fondo del plano pueden recortarse para evitar exportar una gran zona vacía, sea cual sea el color de fondo. Puntos y marcadores AP quedan protegidos del recorte.</p>
        <h2>Mapas continuos y discretos</h2>
        <table class="survey-grid"><tr><td class="survey-card"><b>Cobertura</b><br>Mapa con barra dBm. No tiene página de problemas por diseño: los problemas de calidad se leen en Calidad estudio.</td><td class="survey-gap"></td><td class="survey-card"><b>Interferencia</b><br>Mapa con riesgo y páginas de diagnóstico si existen problemas relevantes.</td><td class="survey-gap"></td><td class="survey-card"><b>Canales/AP dominante</b><br>Mapas discretos con leyendas. AP dominante puede añadir páginas para roaming y posición AP.</td></tr></table>
        <h2>Páginas diagnóstico</h2>
        <p>Interferencia y AP dominante pueden añadir tarjetas de detalle paginadas. Los callouts numerados conectan puntos visibles en el mapa con fichas que explican AP servidor, interferente, canal, ancho, riesgo, AP dominante, AP secundario o AP físico más cercano.</p>
        <h2>Antes de enviar un reporte</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>1. Confirmar alcance</b><br>SSID, banda y tipo de mapa deben ser los que quiere documentar.</td></tr><tr><td class="gate-row"><b>2. Confirmar modelo AP</b><br>Revise grupos, roles, alias y posiciones antes de Interferencia o AP dominante.</td></tr><tr><td class="gate-row"><b>3. Confirmar canales</b><br>Revise cambios limpios, cambios ambiguos y overrides de análisis.</td></tr><tr><td class="gate-row"><b>4. Leer tarjetas como diagnóstico</b><br>Una ficha de advertencia puede describir un problema real de despliegue, no un error del software.</td></tr></table>
    """,
    "help_diagnostics_body": """
        <table class="callout-table"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Regla de advertencias</span><br>Una advertencia indica qué supuesto merece revisión. Decida primero si el problema viene de la evidencia del punto, identidad AP, posición, metadatos, canal o comportamiento RF real.</td></tr></table>
        <h2>Categorías frecuentes</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Puntos a reescanear</b><br>SSID relevante ausente, datos escasos, baja confianza o señal inestable indican que el punto puede ser débil.<br><span class="survey-card-use">Revisar:</span> enfocar el punto, leer evidencia bruta y reescanear si hace falta.</td><td class="workflow-gap"></td><td class="workflow-card"><b>AP dominante inesperado</b><br>El AP más fuerte no es coherente con la posición física o el AP más cercano.<br><span class="survey-card-use">Revisar:</span> posiciones, alias, escala y roaming real.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Ambigüedad roaming</b><br>Primer y segundo AP están cercanos en dB.<br><span class="survey-card-use">Revisar:</span> los clientes pueden elegir cualquiera; no es necesariamente mala medición.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Canal o banda inesperada</b><br>La observación no coincide con metadatos AP.<br><span class="survey-card-use">Revisar:</span> configuración de controlador, canales/bandas esperados, frecuencia scanner y override.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Cambio de canal</b><br>El mismo AP cambió canal durante el estudio. Los cambios limpios usan el último canal; los ambiguos conservan mediciones salvo override.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Posición AP ausente</b><br>Un grupo AP relevante no tiene marcador físico. Los diagnósticos de distancia AP dominante son entonces más débiles.</td></tr></table>
        <h2>Patrones de troubleshooting</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>Cobertura demasiado optimista lejos de puntos</b><br>Causa probable: interpolación rellenando espacio no medido. Acción: reducir distancia max o recoger más puntos.</td></tr><tr><td class="gate-row"><b>Interferencia en un canal antiguo</b><br>Causa probable: cambio de canal, secuencia ambigua u override ausente. Acción: leer detalle de cambio y metadatos AP.</td></tr><tr><td class="gate-row"><b>AP dominante lejos de su marcador</b><br>Causa probable: mala posición, grupo equivocado, roaming cliente o fuga RF real. Acción: abrir detalle AP dominante y verificar AP más cercano.</td></tr><tr><td class="gate-row"><b>Muchos puntos a revisar</b><br>Causa probable: SSID relevantes ausentes, señal inestable o escaneos escasos. Acción: enfocar y reescanear antes de interpretar.</td></tr><tr><td class="gate-row"><b>Canales inesperados en un AP</b><br>Causa probable: metadatos obsoletos, configuración cambiada o evidencia banda/canal ambigua. Acción: comparar con el controlador real.</td></tr></table>
        <h2>Orden de revisión</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>1. Evidencia de punto</b><br>Corrija redes ausentes, escaneos escasos, baja confianza e inestabilidad antes de mapas.</td></tr><tr><td class="gate-row"><b>2. Identidad y posición AP</b><br>Corrija grupo, alias, rol y coordenadas porque afectan AP dominante, Interferencia, Canales AP y HTML.</td></tr><tr><td class="gate-row"><b>3. Metadatos y canales</b><br>Expectativas de banda/canal y override de análisis determinan si una advertencia es real.</td></tr><tr><td class="gate-row"><b>4. Mapas al final</b><br>Lea cobertura, canales, roaming e interferencias cuando los supuestos sean suficientemente coherentes.</td></tr></table>
    """,
    "help_glossary_body": """
        <table class="callout-table" width="100%" cellspacing="0" cellpadding="0"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Uso</span><br>Este glosario estabiliza los términos usados en la interfaz y reportes. Las páginas de workflow explican acciones; esta página explica vocabulario.</td></tr></table>
        <h2>Evidencia Wi-Fi</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>SSID</b><br>Nombre de la red Wi-Fi. Un SSID puede difundirse por varios BSSID.</td><td class="workflow-gap"></td><td class="workflow-card"><b>BSSID</b><br>Dirección MAC radio observada en escaneos Wi-Fi.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>SSID relevante</b><br>Red elegida como importante para calidad, mapas Live y reportes.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Sidecar bruto</b><br>Archivo <code>.scan</code> vinculado con muestras repetidas.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Confianza</b><br>Fiabilidad de una fila agregada, calculada desde escaneos repetidos.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Hallazgo de reescaneo</b><br>Problema de calidad que sugiere que el punto puede necesitar otro escaneo.</td></tr></table>
        <h2>Modelo AP</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Grupo AP</b><br>Modelo de un AP físico, normalmente con varios BSSID.</td><td class="workflow-gap"></td><td class="workflow-card"><b>AP dominante</b><br>Grupo AP con la señal observada más fuerte en el punto.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Ambigüedad roaming</b><br>Punto donde primer y segundo AP están lo bastante cerca para que los clientes elijan cualquiera.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Canal de análisis forzado</b><br>Canal observado elegido por el usuario para mapas sensibles al canal de un grupo AP y banda.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Cambio canal limpio</b><br>AP que cambia canal sin evidencia de conflicto BSSID mezclado.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Cambio canal ambiguo</b><br>Secuencia donde el programa no puede tratar el cambio como transición limpia.</td></tr></table>
        <h2>Calidad y advertencias</h2>
        <table class="survey-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="survey-card"><b>Warning setup</b><br>Problema de modelo o despliegue que no requiere necesariamente reescanear el punto.</td><td class="survey-gap"></td><td class="survey-card"><b>Canal/banda inesperado</b><br>Evidencia Wi-Fi que no coincide con metadatos AP esperados.</td><td class="survey-gap"></td><td class="survey-card"><b>Posición AP ausente</b><br>Un grupo AP relevante no tiene coordenada física; los controles de distancia son más débiles.</td></tr></table>
        <h2>Memoria y persistencia</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Memoria AP</b><br>Archivo persistente con alias, roles, metadatos, canales forzados y posiciones compatibles para futuros estudios.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Desde memoria</b><br>Estado que indica datos aplicados desde Memoria AP y pendientes de confirmación.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Actualización memoria</b><br>Estado que indica que la memoria contiene datos diferentes a los del grupo actual.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Memoria opciones mapa</b><br>El Mapa Live recuerda opciones por tipo de mapa durante la sesión.</td></tr></table>
        <h2>Mapas y reportes</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Interpolación</b><br>Estimación visual entre mediciones reales. Ayuda a leer, no reemplaza puntos.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Distancia max</b><br>Límite de render que evita que los mapas continuos se extiendan demasiado lejos de la evidencia.</td></tr><tr><td class="workflow-vertical-gap" colspan="3"></td></tr><tr><td class="workflow-card"><b>Límite estudio</b><br>Opción Live que atenúa el render continuo fuera del área medida.</td><td class="workflow-gap"></td><td class="workflow-card"><b>Máscara Límites</b><br>PNG dibujado por el usuario que define el área válida para mapas continuos y HTML soportados.</td></tr></table>
    """,
    "help_legal_body": """
        <h2>Aplicación</h2>
        <table class="workflow-grid" width="100%" cellspacing="0" cellpadding="0"><tr><td class="workflow-card"><b>Producto</b><br>Wi-Fi RF Survey Analyzer</td><td class="workflow-card"><b>Versión</b><br>{version}</td></tr><tr><td class="workflow-vertical-gap" colspan="2"></td></tr><tr><td class="workflow-card"><b>Copyright</b><br>{copyright}</td><td class="workflow-card"><b>Licencia</b><br>{license_name} (<code>{license_id}</code>)<br>{license_url}</td></tr></table>
        <h2>Uso responsable</h2>
        <table class="callout-table" width="100%" cellspacing="0" cellpadding="0"><tr><td class="callout-accent-warning"></td><td class="callout-content"><span class="callout-label">Solo redes autorizadas</span><br>Este software está destinado a actividades legítimas de análisis, estudio y troubleshooting Wi-Fi sobre redes propias o que tiene autorización para evaluar. El autor no asume responsabilidad por usos indebidos.</td></tr></table>
        <h2>Componentes de terceros</h2>
        <p>La aplicación usa bibliotecas de terceros como PySide6/Qt, matplotlib, numpy, scipy, pandas, Pillow y lswifi. El resumen de licencias está en <code>THIRD_PARTY_LICENSES</code>, incluido con el código fuente y las releases empaquetadas.</p>
        <h2>Acceso al código fuente</h2>
        <p>Las releases públicas ejecutables deben apuntar al tag de código fuente o estado del repositorio correspondiente al build publicado.</p>
        <table class="callout-table" width="100%" cellspacing="0" cellpadding="0"><tr><td class="callout-accent-info"></td><td class="callout-content"><span class="callout-label">Sin garantía</span><br>El software se entrega tal cual, sin garantía de ningún tipo.</td></tr></table>
    """,
})

TRANSLATIONS.update({
    "help_survey_body": TRANSLATIONS["help_survey_body"] + """
        <h2>Acciones sobre puntos</h2>
        <table><tr><th>Acción</th><th>Uso</th></tr><tr><td>Ir al punto</td><td>Selecciona el punto, ajusta el zoom hasta el objetivo configurado y coloca el marcador en la parte alta de la vista para que siga visible con el panel de puntos abierto.</td></tr><tr><td>Reescanear punto</td><td>Repite la medición en la misma ubicación cuando Calidad estudio indica red ausente, señal inestable, baja confianza o datos escasos.</td></tr><tr><td>Borrar selección / último</td><td>Retira evidencia cuando el punto se colocó mal o se capturó en malas condiciones.</td></tr></table>
        <h2>Cuándo añadir puntos</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>Transición AP:</b> añada puntos a ambos lados de puertas, pasillos y cambios de sala. AP dominante y roaming necesitan evidencia alrededor de esos límites.</td></tr><tr><td class="gate-row"><b>Zona vacía:</b> si un mapa parece extrapolar demasiado lejos, recoja un punto en el centro de la zona antes de concluir.</td></tr><tr><td class="gate-row"><b>Plano blanco:</b> use la cuadrícula como referencia espacial. En métrico el cuadrado representa 1 m; en imperial representa 3 ft.</td></tr></table>
    """,
    "help_quality_body": TRANSLATIONS["help_quality_body"] + """
        <h2>Detalles de hallazgos</h2>
        <table class="survey-grid"><tr><td class="survey-card"><b>Redes relevantes ausentes</b><br>Indica que un SSID esperado no se vio en el punto. Revise si la red realmente se espera en esa zona, especialmente para AP en Área local.</td><td class="survey-gap"></td><td class="survey-card"><b>Detalles scanner limitados</b><br>El backend no entregó suficiente información para algunos razonamientos de canal: ancho de canal, frecuencia 6 GHz o datos scanner de respaldo.</td><td class="survey-gap"></td><td class="survey-card"><b>Roaming cliente</b><br>El portátil del estudio permaneció asociado a un AP más débil mientras otro AP del mismo SSID era claramente más fuerte. Es evidencia útil de sticky client.</td></tr></table>
        <h2>Leer detalles AP</h2>
        <p>Los hallazgos AP dominante combinan señal, AP dominante, AP físico más cercano y distancia. No siempre significan que el punto esté mal: pueden revelar una posición AP incorrecta, un alias ambiguo, propagación RF real o un comportamiento de roaming aceptable.</p>
        <table class="gate-list"><tr><td class="gate-row"><b>Memoria AP:</b> confirme los datos aplicados desde memoria cuando sean correctos para este sitio. Si el estudio actual tiene mejor información, consérvela y actualice la memoria.</td></tr><tr><td class="gate-row"><b>Cambios de canal:</b> un cambio limpio puede tratarse automáticamente; un cambio ambiguo merece un canal de análisis forzado si conoce el canal que debe documentarse.</td></tr><tr><td class="gate-row"><b>AP sin posición:</b> coloque los AP relevantes antes de sacar conclusiones de distancia AP dominante.</td></tr></table>
    """,
    "help_ap_groups_body": TRANSLATIONS["help_ap_groups_body"] + """
        <h2>Conflictos de grupo AP</h2>
        <p>Un conflicto aparece cuando un grupo parece contener BSSID incompatibles para un único AP físico, por ejemplo varios canales en la misma banda. Puede ser un cambio real de canal, un AP especial multi-radio o una agrupación incorrecta. Use Corregir grupo AP para separar filas solo cuando la evidencia indique AP distintos.</p>
        <h2>Buenas prácticas de nombres</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>Alias legibles:</b> use nombres operativos estables, por ejemplo planta, zona o número AP. Los alias aparecen en tooltips, leyendas y PDF.</td></tr><tr><td class="gate-row"><b>Roles coherentes:</b> marque como Externo los vecinos y como Prueba/oculto los AP que ignorar. No deje que un AP de prueba contamine Cobertura, Interferencia o AP dominante.</td></tr><tr><td class="gate-row"><b>Metadatos útiles:</b> los canales esperados y bandas esperadas deben reflejar el controlador real, no solo lo que el scanner vio durante el estudio.</td></tr></table>
        <h2>Cuándo usar un override</h2>
        <p>Un override de canal de análisis es útil cuando un AP cambió de canal durante el estudio y sabe qué canal debe representar el análisis. Evita que un mapa Interferencia o Canales AP mezcle una transición temporal con el estado que quiere documentar.</p>
    """,
    "help_live_maps_body": TRANSLATIONS["help_live_maps_body"] + """
        <h2>Lectura por mapa</h2>
        <table class="survey-grid"><tr><td class="survey-card"><b>Cobertura</b><br>Revise primero color y dBm estimado, luego verifique los puntos reales alrededor de la zona. Una superficie suave no es una medición adicional.</td><td class="survey-gap"></td><td class="survey-card"><b>Interferencia</b><br>Lea el riesgo con contexto: AP servidor, canal, ancho, rol del interferente y modo Intra-SSID o Todos SSID.</td><td class="survey-gap"></td><td class="survey-card"><b>Mapas discretos</b><br>Canales AP y AP dominante muestran mediciones, no interpolación. Los colores deben leerse como categorías por punto.</td></tr></table>
        <h2>Zoom y centrado</h2>
        <p>Las acciones desde Calidad estudio, listas de puntos y algunas leyendas pueden centrar automáticamente un punto o grupo. Si el plano es muy ancho o alto, el programa intenta el mejor reposicionamiento posible sin forzar el mapa fuera de sus límites de pan.</p>
        <h2>Cuándo regenerar</h2>
        <table class="gate-list"><tr><td class="gate-row"><b>Tras reescaneos:</b> actualice el Mapa Live para releer la superficie con los nuevos puntos.</td></tr><tr><td class="gate-row"><b>Tras corregir AP:</b> Interferencia, Canales AP y AP dominante deben recalcularse porque grupos, roles o canales pueden cambiar el resultado.</td></tr><tr><td class="gate-row"><b>Tras máscara Límites:</b> verifique mapas continuos y PDF, porque la máscara modifica el área visible del render.</td></tr></table>
    """,
})
