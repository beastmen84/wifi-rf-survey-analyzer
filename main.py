"""Application entry point for the Wi-Fi survey app."""

import sys

try:
    from PySide6.QtWidgets import QApplication
except ModuleNotFoundError as exc:
    print("PySide6 is required for main.py. Run: pip install -r requirements.txt")
    raise SystemExit(1) from exc

from app_logging import configure_logging, log_event, log_unhandled_exception
from qt_startup import StartWindow
from qt_windowing import install_dialog_centering


def install_exception_logging():
    def handle_exception(exc_type, exc_value, exc_traceback):
        log_unhandled_exception(exc_type, exc_value, exc_traceback)
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception


def main():
    configure_logging()
    install_exception_logging()
    log_event("qt launcher start", logger_name="startup")
    app = QApplication(sys.argv)
    install_dialog_centering(app)
    app.setApplicationName("Wi-Fi RF Survey Analyzer")
    window = StartWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
