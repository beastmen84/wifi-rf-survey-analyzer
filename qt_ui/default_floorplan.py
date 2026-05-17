"""Generated blank floor plan helpers for new unsaved surveys."""

from pathlib import Path
import tempfile

from PIL import Image

from app_core.constants import (
    APP_ID,
    DEFAULT_FLOORPLAN_HEIGHT_PX,
    DEFAULT_FLOORPLAN_IMPERIAL_PX_PER_FOOT,
    DEFAULT_FLOORPLAN_METRIC_PX_PER_METER,
    DEFAULT_FLOORPLAN_WIDTH_PX,
)
from app_core.units import FEET_PER_METER, MEASUREMENT_SYSTEM_IMPERIAL, normalize_measurement_system


DEFAULT_FLOORPLAN_FILENAME = "blank_a4_floorplan.png"


def default_floorplan_temp_path():
    return Path(tempfile.gettempdir()) / APP_ID / DEFAULT_FLOORPLAN_FILENAME


def write_default_floorplan(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new(
        "RGB",
        (DEFAULT_FLOORPLAN_WIDTH_PX, DEFAULT_FLOORPLAN_HEIGHT_PX),
        "white",
    ).save(path, format="PNG")
    return path


def ensure_default_floorplan():
    return write_default_floorplan(default_floorplan_temp_path())


def default_floorplan_save_path(csv_file):
    return Path(csv_file).with_suffix(".png")


def default_floorplan_px_per_meter(measurement_system):
    if normalize_measurement_system(measurement_system) == MEASUREMENT_SYSTEM_IMPERIAL:
        return DEFAULT_FLOORPLAN_IMPERIAL_PX_PER_FOOT * FEET_PER_METER

    return DEFAULT_FLOORPLAN_METRIC_PX_PER_METER
