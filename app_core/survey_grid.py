"""Per-survey physical grid size, independent of map calibration and zoom."""
import math

from app_core.units import (MEASUREMENT_SYSTEM_IMPERIAL, normalize_measurement_system,
                            display_units_to_meters, meters_to_display_units)

GRID_SPACING_KEY = "grid_spacing_m"


def default_grid_spacing_m(system):
    return display_units_to_meters(3 if normalize_measurement_system(system) == MEASUREMENT_SYSTEM_IMPERIAL else 1, system)


def grid_input_decimals(system):
    return 0 if normalize_measurement_system(system) == MEASUREMENT_SYSTEM_IMPERIAL else 1


def normalize_grid_spacing(value, system):
    """Match the input's precision: tenths of a meter or whole feet."""
    display = meters_to_display_units(float(value), system)
    if not math.isfinite(display):
        raise ValueError("Invalid grid spacing")
    decimals = grid_input_decimals(system)
    minimum = 1 if decimals == 0 else .1
    display = max(minimum, min(10000, round(display, decimals)))
    return display_units_to_meters(display, system)


def survey_grid_spacing(metadata):
    if GRID_SPACING_KEY not in metadata:
        return None  # Legacy surveys retain their automatic grid spacing.
    value = float(metadata[GRID_SPACING_KEY])
    if not math.isfinite(value) or not .1 <= value <= 10000:
        raise ValueError("Invalid survey grid spacing")
    return value
