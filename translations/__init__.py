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

from translations.advisor import dictionary as advisor_dictionary
from translations.reports import dictionary as report_dictionary
from translations.capture import dictionary as capture_dictionary
from translations.measurement import dictionary as measurement_dictionary
from translations.blank_plan import dictionary as blank_plan_dictionary
from translations.annotations import dictionary as annotation_dictionary
from translations.objects import dictionary as objects_dictionary
for _language, _dictionary in TRANSLATIONS.items():
    _dictionary.update(advisor_dictionary(_language))
    _dictionary.update(report_dictionary(_language))
    _dictionary.update(capture_dictionary(_language))
    _dictionary.update(measurement_dictionary(_language))
    _dictionary.update(blank_plan_dictionary(_language))
    _dictionary.update(annotation_dictionary(_language))
    _dictionary.update(objects_dictionary(_language))
    _dictionary["blank_plan_help"] += " " + _dictionary["annotation_help"]
    _dictionary["blank_plan_help"] += " " + _dictionary["drawing_precision_help"]
    _dictionary["blank_plan_help"] += " " + _dictionary["objects_help"]
    _dictionary["help_ap_groups_body"] += _dictionary["advisor_group_confirmation_help"]
    _dictionary["help_ap_groups_body"] += _dictionary["ap_confirmation_priority_help"]

LANGUAGE_LABELS = {
    "it": IT_LANGUAGE_LABEL,
    "en": EN_LANGUAGE_LABEL,
    "fr": FR_LANGUAGE_LABEL,
    "es": ES_LANGUAGE_LABEL,
}

SUPPORTED_LANGUAGES = tuple(language.upper() for language in TRANSLATIONS)
LANGUAGE_OPTIONS = tuple((language.upper(), LANGUAGE_LABELS[language]) for language in TRANSLATIONS)
