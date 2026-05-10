import math


DEFAULT_UI_SCALE_MODE = "auto"
UI_SCALE_OPTIONS = ("auto", "100", "110", "125", "150", "175")


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

    geometry = screen.availableGeometry()
    short_edge = min(geometry.width(), geometry.height())
    logical_dpi = float(screen.logicalDotsPerInch() or 96.0)

    # Use a softened resolution scale so 1440p feels like a scaled 1080p UI
    # without making dense toolbars or tables disproportionately large.
    resolution_scale = math.pow(short_edge / 1080.0, 0.65)
    dpi_scale = logical_dpi / 96.0
    scale = max(resolution_scale, dpi_scale, 1.0)
    return round(min(max(scale, 1.0), 1.75), 2)


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
