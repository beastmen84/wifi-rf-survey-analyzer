DEFAULT_UI_SCALE_MODE = "auto"
UI_SCALE_OPTIONS = ("auto", "100", "110", "125", "150", "175")
RESOLUTION_SCALE_BREAKPOINTS = (
    ((1920, 1200), 1.0),
    ((2560, 1600), 1.25),
    ((3440, 1600), 1.25),
    ((3840, 2400), 1.5),
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
    try:
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError:
        return 1.0

    app = app or QApplication.instance()
    screen = app.primaryScreen() if app is not None else None
    if screen is None:
        return 1.0

    width, height = detect_screen_resolution(screen)
    return scale_for_resolution(width, height)


def detect_screen_resolution(screen):
    geometry = screen.geometry()
    ratio = float(screen.devicePixelRatio() or 1.0)
    width = int(round(geometry.width() * ratio))
    height = int(round(geometry.height() * ratio))
    return max(width, height), min(width, height)


def scale_for_resolution(width, height):
    long_edge = max(int(width), int(height))
    short_edge = min(int(width), int(height))
    for (max_long, max_short), scale in RESOLUTION_SCALE_BREAKPOINTS:
        if long_edge <= max_long and short_edge <= max_short:
            return scale
    return 1.75


def resolve_ui_scale(mode=None, app=None):
    mode = normalize_ui_scale_mode(mode)
    if mode == "auto":
        return detect_auto_ui_scale(app)
    try:
        return min(max(float(mode) / 100.0, 0.75), 1.75)
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
