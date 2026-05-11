"""Template for adding a new language.

Copy this file to ``translations/<language_code>.py``, set ``LANGUAGE_LABEL``,
translate the values, then register the module in ``translations/__init__.py``.
"""

from translations.en import TRANSLATIONS as EN_TRANSLATIONS


LANGUAGE_LABEL = "Language name"

TRANSLATIONS = {
    key: value
    for key, value in EN_TRANSLATIONS.items()
}
