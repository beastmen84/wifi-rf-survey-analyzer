"""Translation registry."""

from translations.en import TRANSLATIONS as EN_TRANSLATIONS
from translations.it import TRANSLATIONS as IT_TRANSLATIONS


TRANSLATIONS = {
    "it": IT_TRANSLATIONS,
    "en": EN_TRANSLATIONS,
}

SUPPORTED_LANGUAGES = tuple(language.upper() for language in TRANSLATIONS)
