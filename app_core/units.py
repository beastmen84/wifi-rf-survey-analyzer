"""Display-unit helpers for survey distances.

The survey model stores calibrated scale as pixels per meter. Measurement
system preferences only affect UI input and displayed distances.
"""

MEASUREMENT_SYSTEM_METRIC = "metric"
MEASUREMENT_SYSTEM_IMPERIAL = "imperial"
MEASUREMENT_SYSTEM_OPTIONS = (
    MEASUREMENT_SYSTEM_METRIC,
    MEASUREMENT_SYSTEM_IMPERIAL,
)

FEET_PER_METER = 3.280839895013123


def normalize_measurement_system(value, default=MEASUREMENT_SYSTEM_METRIC):
    value = str(value or "").strip().lower()
    return value if value in MEASUREMENT_SYSTEM_OPTIONS else default


def distance_unit_label(system):
    return "ft" if normalize_measurement_system(system) == MEASUREMENT_SYSTEM_IMPERIAL else "m"


def meters_to_display_units(meters, system):
    value = float(meters)
    if normalize_measurement_system(system) == MEASUREMENT_SYSTEM_IMPERIAL:
        return value * FEET_PER_METER
    return value


def display_units_to_meters(value, system):
    value = float(value)
    if normalize_measurement_system(system) == MEASUREMENT_SYSTEM_IMPERIAL:
        return value / FEET_PER_METER
    return value


def pixels_per_display_unit(px_per_meter, system):
    px_per_meter = float(px_per_meter)
    if normalize_measurement_system(system) == MEASUREMENT_SYSTEM_IMPERIAL:
        return px_per_meter / FEET_PER_METER
    return px_per_meter


def format_distance_meters(meters, system, decimals=1):
    value = meters_to_display_units(meters, system)
    suffix = distance_unit_label(system)
    text = f"{value:.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return f"{text} {suffix}"


def format_scale_density(px_per_meter, system):
    value = pixels_per_display_unit(px_per_meter, system)
    return f"{value:.2f} px/{distance_unit_label(system)}"
