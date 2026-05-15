"""Product version metadata.

This is the public application version, not the V2 survey CSV schema version.
"""

APP_DISPLAY_NAME = "Wi-Fi RF Survey Analyzer"
APP_VERSION = "0.9.3-beta.1"
APP_RELEASE_TAG = f"v{APP_VERSION}"
APP_VERSION_LABEL = APP_RELEASE_TAG
APP_RELEASE_CHANNEL = "beta"


def get_app_icon_path():
    from app_core.resources import resource_path

    return resource_path("images", "app_icon.png")


def format_versioned_title(title=APP_DISPLAY_NAME):
    return f"{title} {APP_VERSION_LABEL}"


def configure_qt_application_metadata(app):
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationVersion(APP_VERSION)
    icon_path = get_app_icon_path()
    if icon_path.exists():
        from PySide6.QtGui import QIcon

        app.setWindowIcon(QIcon(str(icon_path)))
