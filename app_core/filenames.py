"""Filename normalization helpers."""

import re


def sanitize_filename(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "ssid"
