"""Generated blank floor plan helpers for new unsaved surveys."""

from pathlib import Path
import tempfile
import math

from PIL import Image
from survey.plan_drawing import render_plan_drawing

from app_core.constants import (
    APP_ID,
    DEFAULT_FLOORPLAN_HEIGHT_PX,
    DEFAULT_FLOORPLAN_IMPERIAL_PX_PER_FOOT,
    DEFAULT_FLOORPLAN_METRIC_PX_PER_METER,
    DEFAULT_FLOORPLAN_WIDTH_PX,
)
from app_core.units import (FEET_PER_METER, MEASUREMENT_SYSTEM_IMPERIAL,
                            normalize_measurement_system, display_units_to_meters)


DEFAULT_FLOORPLAN_FILENAME = "blank_a4_floorplan.png"
BLANK_PLAN_WIDTH_KEY = "blank_plan_width_m"
BLANK_PLAN_HEIGHT_KEY = "blank_plan_height_m"
BLANK_PLAN_MIN_METERS = 1.0
BLANK_PLAN_MAX_METERS = 500.0
BLANK_PLAN_MAX_PIXELS = 4096


def default_blank_dimensions_m(measurement_system):
    system = normalize_measurement_system(measurement_system)
    dimensions = (115, 81) if system == MEASUREMENT_SYSTEM_IMPERIAL else (35, 25)
    return tuple(display_units_to_meters(value, system) for value in dimensions)


def blank_floorplan_geometry(measurement_system, width_m=None, height_m=None):
    """Use one isotropic scale, bounding raster memory even for large sites."""
    density = default_floorplan_px_per_meter(measurement_system)
    if width_m is None and height_m is None:
        width_m, height_m = default_blank_dimensions_m(measurement_system)
    try:
        dimensions = tuple(float(value) for value in (width_m, height_m))
    except (TypeError, ValueError) as exc:
        raise ValueError("Both blank floor-plan dimensions are required") from exc
    if any(not math.isfinite(value) or not BLANK_PLAN_MIN_METERS <= value <= BLANK_PLAN_MAX_METERS
           for value in dimensions):
        raise ValueError("Blank floor-plan dimensions must be between 1 and 500 meters")
    density = min(density, BLANK_PLAN_MAX_PIXELS / max(dimensions))
    return (*(max(1, round(value * density)) for value in dimensions), density)


def default_floorplan_temp_path():
    return Path(tempfile.gettempdir()) / APP_ID / DEFAULT_FLOORPLAN_FILENAME


def write_default_floorplan(path, width_px=DEFAULT_FLOORPLAN_WIDTH_PX, height_px=DEFAULT_FLOORPLAN_HEIGHT_PX, segments=None, labels=None, curves=None, annotations=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new(
        "RGB",
        (int(width_px), int(height_px)),
        "white",
    )
    render_plan_drawing(image, segments, labels, curves, annotations).save(path, format="PNG")
    return path


def ensure_default_floorplan(width_px=DEFAULT_FLOORPLAN_WIDTH_PX, height_px=DEFAULT_FLOORPLAN_HEIGHT_PX):
    path = default_floorplan_temp_path()
    # Two open surveys with different canvas sizes must not overwrite one another.
    if (width_px, height_px) != (DEFAULT_FLOORPLAN_WIDTH_PX, DEFAULT_FLOORPLAN_HEIGHT_PX):
        path = path.with_name(f"blank_{width_px}x{height_px}.png")
    return write_default_floorplan(path, width_px, height_px)


def default_floorplan_save_path(csv_file):
    return Path(csv_file).with_suffix(".png")


def default_floorplan_px_per_meter(measurement_system):
    if normalize_measurement_system(measurement_system) == MEASUREMENT_SYSTEM_IMPERIAL:
        return DEFAULT_FLOORPLAN_IMPERIAL_PX_PER_FOOT * FEET_PER_METER

    return DEFAULT_FLOORPLAN_METRIC_PX_PER_METER
