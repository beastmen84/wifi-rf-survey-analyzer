DEFAULT_UI_SCALE_MODE = "auto"
UI_SCALE_OPTIONS = ("auto", "100", "110", "125", "150", "175")
RESOLUTION_SCALE_BREAKPOINTS = (
    ((1920, 1200), 100),
    ((2560, 1600), 125),
    ((3440, 1600), 125),
    ((3840, 2400), 150),
)


def normalize_ui_scale_mode(value, default=DEFAULT_UI_SCALE_MODE):
    mode = str(value or "").strip().lower().replace("%", "")
    if not mode:
        return default
    if mode == "auto":
        return mode
    try:
        numeric = float(mode)
    except ValueError:
        return default
    if numeric <= 0:
        return default
    return str(int(round(numeric)))


def detect_auto_ui_scale(app=None):
    percent = detect_auto_ui_scale_percent(app)
    return effective_scale_for_percent(percent, percent)


def detect_auto_ui_scale_percent(app=None):
    try:
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError:
        return 100

    app = app or QApplication.instance()
    screen = app.primaryScreen() if app is not None else None
    if screen is None:
        return 100

    width, height = detect_screen_resolution(screen)
    return scale_percent_for_resolution(width, height)


def detect_screen_resolution(screen):
    geometry = screen.geometry()
    ratio = float(screen.devicePixelRatio() or 1.0)
    width = int(round(geometry.width() * ratio))
    height = int(round(geometry.height() * ratio))
    return max(width, height), min(width, height)


def scale_percent_for_resolution(width, height):
    long_edge = max(int(width), int(height))
    short_edge = min(int(width), int(height))
    for (max_long, max_short), scale in RESOLUTION_SCALE_BREAKPOINTS:
        if long_edge <= max_long and short_edge <= max_short:
            return scale
    return 175


def effective_scale_for_percent(percent, base_percent):
    try:
        percent = float(percent)
        base_percent = float(base_percent)
    except (TypeError, ValueError):
        return 1.0
    if percent <= 0 or base_percent <= 0:
        return 1.0
    return min(max(percent / base_percent, 0.6), 1.75)


def resolve_ui_scale(mode=None, app=None):
    mode = normalize_ui_scale_mode(mode)
    base_percent = detect_auto_ui_scale_percent(app)
    if mode == "auto":
        return effective_scale_for_percent(base_percent, base_percent)
    try:
        return effective_scale_for_percent(float(mode), base_percent)
    except ValueError:
        return detect_auto_ui_scale(app)


def scale_px(value, scale):
    value = float(value)
    if value == 0:
        return 0
    scaled = int(round(value * float(scale)))
    return max(1, scaled) if value > 0 else min(-1, scaled)


def scale_font(value, scale):
    # Fonts need less aggressive growth than spacing on high resolution screens.
    font_scale = 1.0 + ((float(scale) - 1.0) * 0.82)
    return round(float(value) * font_scale, 2)


def scale_font_px(value, scale):
    return max(1, int(round(scale_font(value, scale))))


def widget_ui_scale(owner=None):
    current = owner
    while current is not None:
        value = getattr(current, "ui_scale", None)
        if value:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
        try:
            current = current.parent()
        except RuntimeError:
            current = None
        except AttributeError:
            current = None
    return resolve_ui_scale()


def widget_px(owner, value):
    return scale_px(value, widget_ui_scale(owner))


def widget_font(owner, value):
    return scale_font(value, widget_ui_scale(owner))
