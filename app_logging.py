import sys
import traceback
from datetime import datetime
from pathlib import Path


def application_log_file():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).with_name("wifi_heatmap_error.log")
    return Path.cwd() / "wifi_heatmap_error.log"


def log_event(message):
    try:
        with application_log_file().open("a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now().isoformat(timespec='seconds')} {message}\n")
    except Exception:
        pass


def log_exception(context, error=None):
    try:
        with application_log_file().open("a", encoding="utf-8") as handle:
            handle.write(f"\n=== {datetime.now().isoformat(timespec='seconds')} {context} ===\n")
            if error is None:
                traceback.print_exc(file=handle)
            else:
                handle.write(f"{type(error).__name__}: {error}\n")
    except Exception:
        pass


def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    try:
        with application_log_file().open("a", encoding="utf-8") as handle:
            handle.write(f"\n=== {datetime.now().isoformat(timespec='seconds')} Unhandled exception ===\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=handle)
    except Exception:
        pass
