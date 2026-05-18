"""Translation registry."""

from translations.en import LANGUAGE_LABEL as EN_LANGUAGE_LABEL
from translations.en import TRANSLATIONS as EN_TRANSLATIONS
from translations.es import LANGUAGE_LABEL as ES_LANGUAGE_LABEL
from translations.es import TRANSLATIONS as ES_TRANSLATIONS
from translations.fr import LANGUAGE_LABEL as FR_LANGUAGE_LABEL
from translations.fr import TRANSLATIONS as FR_TRANSLATIONS
from translations.it import LANGUAGE_LABEL as IT_LANGUAGE_LABEL
from translations.it import TRANSLATIONS as IT_TRANSLATIONS


TRANSLATIONS = {
    "it": IT_TRANSLATIONS,
    "en": EN_TRANSLATIONS,
    "fr": FR_TRANSLATIONS,
    "es": ES_TRANSLATIONS,
}

LANGUAGE_LABELS = {
    "it": IT_LANGUAGE_LABEL,
    "en": EN_LANGUAGE_LABEL,
    "fr": FR_LANGUAGE_LABEL,
    "es": ES_LANGUAGE_LABEL,
}

SUPPORTED_LANGUAGES = tuple(language.upper() for language in TRANSLATIONS)
LANGUAGE_OPTIONS = tuple((language.upper(), LANGUAGE_LABELS[language]) for language in TRANSLATIONS)
