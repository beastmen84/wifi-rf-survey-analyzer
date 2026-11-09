"""Plan origin is fixed at survey creation; legacy flags identify older surveys."""
from app_core.constants import DEFAULT_FLOORPLAN_METADATA_KEY, GENERATED_FLOORPLAN_METADATA_KEY

PLAN_MODE_KEY = "plan_mode"
DRAW_PLAN = "draw"
LOAD_PLAN = "load"


def is_drawn_plan(metadata):
    generated = any(metadata.get(key) == "1" for key in
                    (DEFAULT_FLOORPLAN_METADATA_KEY, GENERATED_FLOORPLAN_METADATA_KEY))
    return generated and metadata.get(PLAN_MODE_KEY, DRAW_PLAN) == DRAW_PLAN


def is_loaded_plan(metadata):
    """Recognize explicit and legacy imported plans without reclassifying drawings."""
    return (metadata.get(PLAN_MODE_KEY) == LOAD_PLAN
            or (not is_drawn_plan(metadata) and bool(metadata.get("map_file"))
                and metadata.get(PLAN_MODE_KEY) in (None, LOAD_PLAN)))


def supports_plan_annotations(metadata):
    return is_drawn_plan(metadata) or is_loaded_plan(metadata)
