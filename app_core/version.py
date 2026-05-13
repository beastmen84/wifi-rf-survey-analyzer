"""Product version metadata.

This is the public application version, not the V2 survey CSV schema version.
"""

APP_DISPLAY_NAME = "Wi-Fi RF Survey Analyzer"
APP_VERSION = "0.9.0-beta.1"
APP_RELEASE_TAG = f"v{APP_VERSION}"
APP_VERSION_LABEL = APP_RELEASE_TAG
APP_RELEASE_CHANNEL = "beta"


def format_versioned_title(title=APP_DISPLAY_NAME):
    return f"{title} {APP_VERSION_LABEL}"


def configure_qt_application_metadata(app):
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationVersion(APP_VERSION)
