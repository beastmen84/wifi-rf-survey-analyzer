"""Small JSON-backed application preferences.

These settings are intentionally separate from survey CSV files. They store
user interface preferences such as theme and UI scale, so changing appearance
does not dirty the active survey.
"""

import json
import os
from pathlib import Path


APP_SETTINGS_DIR = "WifiHeatmap"
SETTINGS_FILE_NAME = "settings.json"
THEME_KEY = "theme"
UI_SCALE_KEY = "ui_scale"
LAST_SURVEY_PATH_KEY = "last_survey_path"


def get_settings_path():
    override = os.environ.get("WIFI_HEATMAP_SETTINGS_FILE")
    if override:
        return Path(override)

    appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    if appdata:
        return Path(appdata) / APP_SETTINGS_DIR / SETTINGS_FILE_NAME

    return Path.home() / ".wifi_heatmap" / SETTINGS_FILE_NAME


def load_app_settings():
    path = get_settings_path()
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def save_app_settings(settings):
    path = get_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
    except OSError:
        return False

    return True


def get_saved_theme(default="light", valid_themes=None):
    theme = str(load_app_settings().get(THEME_KEY, "")).strip()
    if not theme:
        return default
    if valid_themes is not None and theme not in valid_themes:
        return default
    return theme


def save_theme(theme):
    settings = load_app_settings()
    settings[THEME_KEY] = str(theme)
    return save_app_settings(settings)


def get_saved_ui_scale(default="auto", valid_modes=None):
    mode = str(load_app_settings().get(UI_SCALE_KEY, "")).strip()
    if not mode:
        return default
    if valid_modes is not None and mode not in valid_modes:
        return default
    return mode


def save_ui_scale(mode):
    settings = load_app_settings()
    settings[UI_SCALE_KEY] = str(mode)
    return save_app_settings(settings)


def get_last_survey_directory(default=""):
    path = Path(str(load_app_settings().get(LAST_SURVEY_PATH_KEY, "")).strip())
    if not str(path):
        return default

    if path.is_dir():
        return str(path)

    parent = path.parent
    return str(parent) if parent.exists() else default


def save_last_survey_path(file_path):
    clean_path = str(file_path or "").strip()
    if not clean_path:
        return False

    settings = load_app_settings()
    settings[LAST_SURVEY_PATH_KEY] = str(Path(clean_path).resolve())
    return save_app_settings(settings)
