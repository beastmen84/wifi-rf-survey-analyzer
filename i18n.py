"""Translation helpers for the Qt interfaces."""

from translations import SUPPORTED_LANGUAGES, TRANSLATIONS


DEFAULT_LANGUAGE = "en"


def normalize_language(language):
    language = str(language or DEFAULT_LANGUAGE).lower()
    return language if language in TRANSLATIONS else DEFAULT_LANGUAGE


def translate(language, key, **kwargs):
    language = normalize_language(language)
    text = TRANSLATIONS[language].get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))
    return text.format(**kwargs) if kwargs else text
