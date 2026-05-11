import unittest
import string

from i18n import (
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
