"""Central logging setup for the Qt Wi-Fi heatmap application.

The executable and source-run modes share the same logger namespace. Source
runs log to the current working directory and console; frozen builds log next
to the executable so user reports can include a predictable file.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOGGER_NAME = "wifi_heatmap"
LOG_FILE_NAME = "wifi_heatmap_qt.log"
LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_LOG_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 5

_CONFIGURED = False


def application_log_file():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).with_name(LOG_FILE_NAME)
    return Path.cwd() / LOG_FILE_NAME


def configure_logging(level=logging.INFO):
    global _CONFIGURED

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if _CONFIGURED and logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    log_file = application_log_file()

    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.handlers.clear()
        logger.addHandler(file_handler)

        if not getattr(sys, "frozen", False):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        logging.captureWarnings(True)
        warnings_logger = logging.getLogger("py.warnings")
        warnings_logger.handlers.clear()
        warnings_logger.setLevel(level)
        warnings_logger.propagate = False
        for handler in logger.handlers:
            warnings_logger.addHandler(handler)

        _CONFIGURED = True
        logger.info("logging initialized file=%s frozen=%s", log_file, getattr(sys, "frozen", False))
    except Exception:
        logger.addHandler(logging.NullHandler())
        _CONFIGURED = True

    return logger


def get_logger(component="app"):
    configure_logging()
    component = str(component or "app").strip(".")
    return logging.getLogger(f"{LOGGER_NAME}.{component}")


def log_event(message, level=logging.INFO, logger_name="app"):
    get_logger(logger_name).log(level, "%s", message)


def log_exception(context, error=None, logger_name="app"):
    logger = get_logger(logger_name)
    current_error = sys.exc_info()[1]

    if error is not None and current_error is error:
        logger.exception("%s: %s", context, error)
    elif error is not None:
        logger.error("%s: %s: %s", context, type(error).__name__, error)
    else:
        logger.exception("%s", context)


def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    get_logger("unhandled").critical(
        "unhandled exception",
        exc_info=(exc_type, exc_value, exc_traceback),
    )
