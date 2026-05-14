"""Application resource path helpers."""

import sys
from pathlib import Path


def resource_path(*parts):
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base_path.joinpath(*parts)
