"""Physical thickness on existing reference geometry, with explicit net areas."""
from copy import deepcopy
import math

from survey.plan_faces import RegionPicker
from survey.wall_geometry import wall_solids, united, usable_floor, validate_wall_bounds
from survey.wall_layout import WallLayout, room_side


def reference_regions(state):
    def plain(items):
        return [{k: v for k, v in item.items() if k != "wall"} for item in items]
    return RegionPicker(plain(state["segments"] or []), plain(state["curves"]))


def convert_wall_reference(state, selected_lines, selected_curves, width, bounds, *, mode="axis", room_index=0):
    if isinstance(width, bool) or not isinstance(width, (int, float)) or not math.isfinite(width) or not 0 <= width <= 10000:
        raise ValueError("wall_invalid_width")
    if mode not in ("axis", "face", "keep"):
        raise ValueError("wall_reference_mode")
    result = deepcopy(state)
    lines, curves = result["segments"] or [], result["curves"]
    if not (selected_lines or selected_curves) or any(i not in range(len(lines)) for i in selected_lines) or any(i not in range(len(curves)) for i in selected_curves):
        raise ValueError("wall_no_selection")
    picker = reference_regions(state)
    if picker.limited or len(picker.records) > 200 or len(lines)+len(curves) > 4000:
        raise ValueError("wall_complexity")
    chosen = [lines[i] for i in selected_lines]+[curves[i] for i in selected_curves]
    protected = None
    if mode == "face":
        if room_index not in range(len(picker.records)):
            raise ValueError("wall_no_anchor")
        protected, region = picker.records[room_index]
        if not set(selected_lines) <= set(region.lines) or not set(selected_curves) <= set(region.curves):
            raise ValueError("wall_select_room")
    for item in chosen:
        old = item.pop("wall", None)
        if not width:
            continue
        if mode == "keep" and old:
            item["wall"] = dict(old, width=float(width), reference=old.get("reference", "face"))
        elif mode == "face":
            item["wall"] = dict(width=float(width), side=room_side(item, protected), reference="face",
                                **{k:v for k,v in (old or {}).items() if k in ('material','pattern','priority')})
        else:
            item["wall"] = dict(width=float(width), side=0, reference="axis",
                                **{k:v for k,v in (old or {}).items() if k in ('material','pattern','priority')})
    validate_wall_bounds(lines, curves, bounds)
    material = united(path for _c, path in wall_solids(lines, curves))
    areas, usable = [], []
    for path, region in picker.records:
        _floor, area, changed = usable_floor(path, region.area, material)
        # Region paths sample analytic curves at 0.05 px. Ignore only the
        # resulting boundary slivers, never a visible interior intrusion.
        if protected is path and changed and path_area_interior_overlap(path, material):
            raise ValueError("wall_room_collision")
        if protected is path:
            area = region.area
        areas.append(region.area)
        usable.append(area)
    return WallLayout(result, ((0.0, 0.0),)*len(areas), tuple(areas), False, tuple(usable), bool(curves))


def path_area_interior_overlap(path, material):
    from PySide6.QtGui import QPainterPathStroker
    margin = QPainterPathStroker()
    margin.setWidth(.12)
    interior = path.subtracted(margin.createStroke(path))
    return not interior.intersected(material).simplified().isEmpty()
