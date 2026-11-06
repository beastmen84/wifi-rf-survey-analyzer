"""Drawing colors/picker palette; no survey geometry or text content is stored."""
import re

from app_core.settings import load_app_settings, save_app_settings

PALETTE_KEY = "plan_custom_colors"
TOOL_COLORS_KEY = "plan_tool_colors"
FIELDS = {"structure": ("color",), "marker": ("color",), "door": ("color",), "window": ("color",),
          "desk": ("color", "fill"), "symbol": ("color", "fill"), "text": ("color", "outline_color")}


def rgb(value):
    return value.lower() if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value) else None


def saved_palette():
    colors = load_app_settings().get(PALETTE_KEY, [])
    return [rgb(value) for value in colors[:16]] if isinstance(colors, list) else []


def save_palette(colors):
    settings = load_app_settings()
    settings[PALETTE_KEY] = [rgb(value) or "#ffffff" for value in colors[:16]]
    return save_app_settings(settings)


def tool_colors(kind):
    tools = load_app_settings().get(TOOL_COLORS_KEY, {})
    source = tools.get(kind, {}) if isinstance(tools, dict) else {}
    if not isinstance(source, dict):
        return {}
    return {key: rgb(source[key]) for key in FIELDS.get(kind, ()) if key in source
            and (rgb(source[key]) is not None or key == "fill" and source[key] is None)}


def save_tool_colors(kind, values):
    if kind not in FIELDS:
        return False
    clean = {key: rgb(values[key]) for key in FIELDS[kind] if key in values
             and (rgb(values[key]) is not None or key == "fill" and values[key] is None)}
    settings = load_app_settings()
    tools = settings.get(TOOL_COLORS_KEY, {})
    tools = dict(tools) if isinstance(tools, dict) else {}
    tools[kind] = clean
    settings[TOOL_COLORS_KEY] = tools
    return save_app_settings(settings)
