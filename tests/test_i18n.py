import ast
import re
import string
import unittest
from pathlib import Path

from translations.i18n import (
    DEFAULT_LANGUAGE,
    LANGUAGE_LABELS,
    LANGUAGE_OPTIONS,
    SUPPORTED_LANGUAGES,
    TRANSLATIONS,
    normalize_language,
    translate,
)


def format_fields(text):
    return {
        field_name
        for _literal, field_name, _format_spec, _conversion in string.Formatter().parse(text)
        if field_name
    }


def iter_app_source_paths():
    root = Path(__file__).resolve().parents[1]
    source_roots = (
        root / "advisor",
        root / "ap",
        root / "app_core",
        root / "exporting",
        root / "maps",
        root / "qt_ui",
        root / "survey",
        root / "wifi",
    )
    yield root / "main.py"
    for source_root in source_roots:
        for path in source_root.glob("*.py"):
            yield path


def collect_static_translation_keys():
    keys = set()
    for path in iter_app_source_paths():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            key_arg = None
            if isinstance(node.func, ast.Name) and node.func.id == "translate" and len(node.args) >= 2:
                key_arg = node.args[1]
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "tr" and node.args:
                key_arg = node.args[0]
            if isinstance(key_arg, ast.Constant) and isinstance(key_arg.value, str):
                keys.add(key_arg.value)
    return keys


CAPITALIZED_UI_KEYS = (
    "new_survey",
    "open_existing_survey",
    "invalid_survey_title",
    "points_panel_show",
    "points_panel_hide",
    "live_map_tab",
    "live_update_now",
    "save_live_pdf_title",
    "live_pdf_problem_report_title",
    "all_ap_groups_option",
    "load_plan",
    "generate_heatmap",
    "quality_dashboard_title",
    "quality_dashboard_status_ok_title",
    "quality_dashboard_status_early_title",
    "quality_dashboard_status_review_title",
    "quality_dashboard_status_setup_title",
    "calibrate_scale",
    "delete_scale",
    "ap_group_bssid_title",
    "ap_group_bssid_select_visible",
    "ap_group_bssid_new_group_from_rows",
    "ap_group_conflict_title",
    "ap_group_set_alias",
    "ap_group_set_role",
    "ap_group_metadata_title",
    "ap_group_set_position",
    "ap_groups_reset_title",
    "ap_group_clear_filters",
    "saved_network",
    "manage_relevant_networks_title",
    "go_to_point",
    "delete_selected",
    "map_type",
    "map_type_signal",
    "map_type_interference",
    "map_type_channel",
    "map_type_dominant",
    "point_labels",
    "export_signal_title",
    "interference_mode",
    "interference_summary_title",
    "select_plan_title",
    "save_required_title",
    "help_title",
    "keep_scan",
    "cancel_point",
)

CRITICAL_LOCALIZED_KEYS = (
    "loading_app",
    "start_subtitle",
    "toolbar_project",
    "toolbar_view",
    "toolbar_analysis",
    "toolbar_settings",
    "new_survey",
    "open_existing_survey",
    "discard_changes",
    "language",
    "ui_scale",
    "measurement_system",
    "go_to_point_zoom",
    "live_map_tab",
    "live_update_now",
    "live_export_pdf",
    "live_pdf_problem_report_title",
    "load_plan",
    "save",
    "quality_dashboard_title",
    "quality_dashboard_metric_missing",
    "quality_dashboard_metric_scanner_details",
    "quality_dashboard_metric_ap_metadata_warnings",
    "quality_dashboard_fix_missing_title",
    "quality_dashboard_action_open_ap_metadata",
    "calibrate_scale",
    "grid",
    "boundaries",
    "boundaries_draw_tooltip",
    "boundaries_eraser_tooltip",
    "delete_scale",
    "ap_groups_title",
    "ap_group_bssid_title",
    "ap_group_conflict_title",
    "ap_group_metadata_title",
    "ap_group_filter_status_all",
    "ap_group_clear_filters",
    "manage_relevant_networks_title",
    "survey_point_tooltip_title",
    "wifi_ap_tooltip_title",
    "tooltip_section_interference",
    "tooltip_section_dominant_ap",
    "go_to_point",
    "rescan_point",
    "delete_selected",
    "map_type_signal",
    "map_type_interference",
    "map_type_channel",
    "map_type_dominant",
    "export_signal_title",
    "export_channel_title",
    "export_dominant_title",
    "export_interference_title",
    "interference_mode",
    "interference_summary_title",
    "interference_summary_interferer_channel",
    "interference_summary_diagnosis",
    "survey_bounds",
    "max_distance_px",
    "aggregation",
    "color_scale",
    "smoothing",
    "theme",
    "close",
    "cancel",
    "select_plan_title",
    "insufficient_data_title",
    "save_required_title",
    "missing_relevant_networks_title",
    "help_title",
    "help_overview_title",
    "help_controls_title",
    "help_survey_title",
    "help_quality_title",
    "help_ap_groups_title",
    "help_live_maps_title",
    "help_reports_title",
    "help_diagnostics_title",
    "help_legal_title",
    "keep_scan",
    "retry_scan",
    "cancel_point",
)

LAYOUT_SENSITIVE_KEYS = (
    "new_survey",
    "open_existing_survey",
    "discard_changes",
    "live_update_now",
    "live_export_pdf",
    "load_plan",
    "save",
    "calibrate_scale",
    "grid",
    "boundaries",
    "delete_scale",
    "ap_groups_title",
    "quality_dashboard_title",
    "help",
    "go_to_point",
    "rescan_point",
    "delete_selected",
    "map_type_signal",
    "map_type_interference",
    "map_type_channel",
    "map_type_dominant",
    "interference_summary_interferer_channel",
    "save_required_title",
    "keep_scan",
    "retry_scan",
    "cancel_point",
)

ALLOWED_IDENTICAL_TRANSLATION_KEYS = frozenset({
    "symbol_position",  # Position, description and plan are also French nouns.
    "legend_description",
    "legend_plan_page",
    "object_symbol_triangle",  # Triangle is also the correct French noun.
    "annotation_structure",  # These three labels are also correct French nouns.
    "annotation_group",
    "annotation_type",
    "blank_tool_rectangle",  # Rectangle is also the French noun.
    "design_caption_rectangle",  # Rectangle and arc are also French nouns.
    "design_caption_arc",
    "design_caption_color",  # Color is also the Spanish noun.
    "app_title",
    "copyright",
    "qt_csv",
    "qt_points",
    "ui_scale_auto",
    "live_options_show",
    "live_options_hide",
    "quality_dashboard_point_detail_label",
    "ap_group_alias_menu",
    "ap_group_metadata_channel_group_24",
    "ap_group_metadata_channel_group_5_dfs",
    "ap_group_metadata_analysis_channel_auto",
    "ap_group_metadata_notes",
    "ap_group_position",
    "ap_label",
    "ap_alias_bssids",
    "ap_alias_value",
    "ap_group_state_manual",
    "ap_group_state_auto",
    "ap_group_filter_status_warning",
    "tooltip_section_signal",
    "tooltip_section_radio",
    "tooltip_section_position",
    "tooltip_section_second_ap",
    "signal",
    "second_ap",
    "export_points",
    "interference_mode_intra_ssid",
    "interference_summary_point",
    "interference_overlap",
    "interpolation",
    "images",
    "help_scan",
    "error",
    "zoom",
})

HELP_BODY_KEYS = tuple(
    key for key in TRANSLATIONS[DEFAULT_LANGUAGE]
    if key.startswith("help_") and key.endswith("_body")
)


def first_alpha(text):
    for character in text:
        if character.isalpha():
            return character
    return ""


def visible_text_length(text):
    text_without_tags = re.sub(r"<[^>]+>", " ", text)
    compact = re.sub(r"\s+", " ", text_without_tags).strip()
    return len(compact)


def has_meaningful_words(text):
    text_without_placeholders = re.sub(r"\{[^}]+\}", " ", text)
    return bool(re.search(r"[A-Za-zÀ-ÿ]{3,}", text_without_placeholders))


class I18nTests(unittest.TestCase):
    def test_supported_languages_match_translation_registry(self):
        self.assertEqual(
            tuple(language.upper() for language in TRANSLATIONS),
            SUPPORTED_LANGUAGES,
        )
        self.assertIn(DEFAULT_LANGUAGE, TRANSLATIONS)

    def test_language_options_expose_display_labels(self):
        self.assertEqual(
            tuple(code for code, _label in LANGUAGE_OPTIONS),
            SUPPORTED_LANGUAGES,
        )
        for code, label in LANGUAGE_OPTIONS:
            with self.subTest(language=code):
                language = code.lower()
                self.assertEqual(LANGUAGE_LABELS[language], label)
                self.assertTrue(label.strip())

    def test_all_languages_define_the_same_keys(self):
        expected_keys = set(TRANSLATIONS[DEFAULT_LANGUAGE])
        for language, translations in TRANSLATIONS.items():
            with self.subTest(language=language):
                self.assertEqual(set(translations), expected_keys)

    def test_all_languages_keep_default_placeholders(self):
        default_translations = TRANSLATIONS[DEFAULT_LANGUAGE]
        for language, translations in TRANSLATIONS.items():
            with self.subTest(language=language):
                for key, default_text in default_translations.items():
                    self.assertEqual(
                        format_fields(translations[key]),
                        format_fields(default_text),
                        key,
                    )

    def test_translate_falls_back_to_default_language(self):
        self.assertEqual(normalize_language("missing"), DEFAULT_LANGUAGE)
        self.assertEqual(translate("missing", "save"), TRANSLATIONS[DEFAULT_LANGUAGE]["save"])
        self.assertEqual(translate("it", "__missing_key__"), "__missing_key__")

    def test_static_app_translation_keys_exist(self):
        self.assertFalse(collect_static_translation_keys() - set(TRANSLATIONS[DEFAULT_LANGUAGE]))

    def test_user_facing_validation_text_avoids_internal_generation_labels(self):
        for language, translations in TRANSLATIONS.items():
            with self.subTest(language=language):
                self.assertNotIn("V2", translations["invalid_survey_format"])

    def test_french_and_spanish_localize_operational_strings(self):
        default_translations = TRANSLATIONS[DEFAULT_LANGUAGE]
        for language in ("fr", "es"):
            translations = TRANSLATIONS[language]
            for key in CRITICAL_LOCALIZED_KEYS:
                with self.subTest(language=language, key=key):
                    self.assertNotEqual(translations[key], default_translations[key])

    def test_french_and_spanish_avoid_meaningful_english_fallbacks(self):
        default_translations = TRANSLATIONS[DEFAULT_LANGUAGE]
        for language in ("fr", "es"):
            translations = TRANSLATIONS[language]
            untranslated = [
                key
                for key, default_text in default_translations.items()
                if key not in ALLOWED_IDENTICAL_TRANSLATION_KEYS
                and isinstance(default_text, str)
                and translations[key] == default_text
                and has_meaningful_words(default_text)
            ]
            with self.subTest(language=language):
                self.assertEqual([], untranslated)

    def test_help_body_lengths_stay_balanced_across_languages(self):
        default_translations = TRANSLATIONS[DEFAULT_LANGUAGE]
        for key in HELP_BODY_KEYS:
            default_length = visible_text_length(default_translations[key])
            localized_lengths = {
                language: visible_text_length(TRANSLATIONS[language][key])
                for language in ("fr", "es")
            }
            with self.subTest(key=key):
                for language, length in localized_lengths.items():
                    self.assertGreaterEqual(
                        length,
                        int(default_length * 0.55),
                        f"{language} {key} is too short compared with English",
                    )
                longest = max(localized_lengths.values())
                shortest = min(localized_lengths.values())
                self.assertLessEqual(
                    longest,
                    int(shortest * 1.2),
                    f"French and Spanish {key} lengths drifted apart",
                )

    def test_localized_operational_labels_keep_reasonable_length(self):
        default_translations = TRANSLATIONS[DEFAULT_LANGUAGE]
        for language in ("fr", "es"):
            translations = TRANSLATIONS[language]
            for key in LAYOUT_SENSITIVE_KEYS:
                with self.subTest(language=language, key=key):
                    default_length = len(default_translations[key])
                    translated_length = len(translations[key])
                    limit = max(default_length + 24, int(default_length * 2.2))
                    self.assertLessEqual(translated_length, limit, translations[key])

    def test_localized_terms_preserve_wifi_identifiers(self):
        for language in ("fr", "es"):
            translations = TRANSLATIONS[language]
            joined = "\n".join(
                str(translations[key])
                for key in (
                    "ap_groups_hint",
                    "ap_group_bssid_title",
                    "manage_relevant_networks_message",
                    "export_interference_title",
                    "interference_quality_warning_5ghz",
                )
            )
            with self.subTest(language=language):
                self.assertIn("AP", joined)
                self.assertIn("BSSID", joined)
                self.assertIn("SSID", joined)
                self.assertIn("5", joined)
                self.assertIn("6", joined)

    def test_titles_and_buttons_start_capitalized_in_all_languages(self):
        for language, translations in TRANSLATIONS.items():
            for key in CAPITALIZED_UI_KEYS:
                with self.subTest(language=language, key=key):
                    character = first_alpha(translations[key])
                    self.assertTrue(character and character.isupper(), translations[key])
