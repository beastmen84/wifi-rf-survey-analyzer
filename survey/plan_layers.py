"""Versioned independent drawing layers; legacy drawings are the permanent base."""
from copy import deepcopy
import json
from uuid import uuid4

from survey.plan_drawing import PLAN_DRAWING_KEY, drawing_geometry, encode_drawing, validate_segments
from survey.plan_curves import PLAN_CURVES_KEY, validate_curves, encode_curves
from survey.plan_labels import PLAN_LABELS_KEY, drawing_labels, validate_labels, encode_labels
from survey.plan_annotations import (PLAN_ANNOTATIONS_KEY, drawing_annotations, validate_annotations,
    encode_annotations, supported, overlaps)
from survey.plan_curve_geometry import normalize_plan
from survey.plan_mode import is_drawn_plan, is_loaded_plan

PLAN_LAYERS_KEY = "plan_layers"
STATE_KEYS = ("segments", "labels", "curves", "annotations")
MAX_LAYERS = 32


def legacy_state(metadata):
    lines, curves = drawing_geometry(metadata)
    return dict(segments=lines, curves=curves, labels=drawing_labels(metadata) or [],
                annotations=drawing_annotations(metadata) or [])


def empty_state():
    return dict(segments=[], curves=[], labels=[], annotations=[])


def validate_state(state):
    if not isinstance(state, dict):
        raise ValueError("Invalid layer drawing")
    curves = validate_curves(state.get("curves", []))
    raw = state.get("segments")
    if raw is not None and not isinstance(raw, list):
        raise ValueError("Invalid layer segment list")
    lines, curves = normalize_plan(validate_segments(raw or []), curves)
    annotations = validate_annotations(state.get("annotations", []))
    for index, item in enumerate(annotations):
        if not supported(item, lines) or overlaps(item, annotations[:index]):
            raise ValueError("Invalid layer opening support")
    return dict(segments=None if raw is None and not curves else lines, curves=curves,
                labels=validate_labels(state.get("labels", [])), annotations=annotations)


def validate_document(document):
    if not isinstance(document, dict) or document.get("version") not in (1, 2, 3):
        raise ValueError("Unsupported layer document")
    layers = document.get("layers")
    if not isinstance(layers, list) or not 1 <= len(layers) <= MAX_LAYERS:
        raise ValueError("Invalid layer list")
    result, ids, names = [], set(), set()
    totals = [0, 0, 0, 0]
    for source in layers:
        if not isinstance(source, dict):
            raise ValueError("Invalid layer")
        identity, name = source.get("id"), source.get("name")
        if (not isinstance(identity, str) or not identity or len(identity) > 64 or identity in ids
                or not isinstance(name, str) or not name.strip() or len(name) > 80
                or any(ord(c) < 32 for c in name) or name.strip().casefold() in names
                or not isinstance(source.get("visible"), bool) or not isinstance(source.get("locked"), bool)):
            raise ValueError("Invalid layer properties")
        if identity == "0" and not source["visible"]:
            raise ValueError("Layer 0 must stay visible")
        state = validate_state(source.get("drawing"))
        totals = [total + len(state[key] or []) for total, key in zip(totals, STATE_KEYS)]
        result.append(dict(id=identity, name=name.strip(), visible=source["visible"],
                           locked=source["locked"], drawing=state))
        ids.add(identity)
        names.add(name.strip().casefold())
    if "0" not in ids or document.get("active") not in ids:
        raise ValueError("Missing base or active layer")
    points = sum(len(item.get("points", [])) for layer in result for item in layer["drawing"]["annotations"])
    commands = sum(len(item["path"]) for layer in result for item in layer["drawing"]["labels"])
    if (any(n > maximum for n, maximum in zip(totals, (40000, 500, 5000, 1000)))
            or totals[0] + totals[2] > 40000 or points > 100000 or commands > 250000):
        raise ValueError("Layer document exceeds drawing limits")
    from survey.plan_symbols import validate_symbols
    validate_symbols(dict(layers=result))
    from survey.rack_inventory import validate_inventory_totals
    validate_inventory_totals(a for layer in result for a in layer['drawing']['annotations'])
    physical = any(s.get("wall") for layer in result for s in [*(layer["drawing"]["segments"] or []), *layer["drawing"]["curves"]])
    inventory=any(a.get('rack') for layer in result for a in layer['drawing']['annotations'])
    return dict(version=3 if inventory else 2 if physical else 1, active=document["active"], layers=result)


def validate_plan_document(metadata, document):
    """Imported backgrounds accept free annotations, never editable structure."""
    document = validate_document(document)
    if is_loaded_plan(metadata):
        for layer in document["layers"]:
            state = layer["drawing"]
            if state["segments"] or state["curves"] or any(
                    item["kind"] in ("door", "window") for item in state["annotations"]):
                raise ValueError("loaded_plan_annotations_only")
    return document


def read_layers(metadata):
    if PLAN_LAYERS_KEY in metadata:
        return validate_plan_document(metadata, json.loads(metadata[PLAN_LAYERS_KEY]))
    return validate_plan_document(metadata, dict(version=1, active="0", layers=[dict(id="0", name="Layer 0", visible=True,
                locked=False, drawing=legacy_state(metadata))]))


def active_layer(document):
    return next(layer for layer in document["layers"] if layer["id"] == document["active"])


def editable_layer(document):
    layer = active_layer(document)
    return layer["visible"] and not layer["locked"]


def visible_layers(metadata):
    if PLAN_LAYERS_KEY not in metadata:
        # Also composite legacy imported overlays on their original background.
        if not is_loaded_plan(metadata) or not any(metadata.get(key) for key in (PLAN_LABELS_KEY, PLAN_ANNOTATIONS_KEY)):
            return None
    return dict(generated=is_drawn_plan(metadata),
                layers=[layer for layer in read_layers(metadata)["layers"] if layer["visible"]])


def write_layers(metadata, document):
    document = validate_plan_document(metadata, document)
    encoded = {PLAN_LAYERS_KEY: json.dumps(document, ensure_ascii=False, separators=(",", ":"))}
    # Legacy fields always describe Layer 0, never the currently active layer.
    state = next(layer["drawing"] for layer in document["layers"] if layer["id"] == "0")
    if state["segments"] is not None:
        encoded[PLAN_DRAWING_KEY] = encode_drawing(state["segments"], state["curves"])
    for key, field, encode in ((PLAN_CURVES_KEY, "curves", encode_curves),
                                (PLAN_LABELS_KEY, "labels", encode_labels),
                                (PLAN_ANNOTATIONS_KEY, "annotations", encode_annotations)):
        encoded[key] = encode(state[field])
    # All encoders must succeed before replacing any part of the document.
    metadata.update(encoded)
    if state["segments"] is None:
        metadata.pop(PLAN_DRAWING_KEY, None)
    return document


def add_layer(document, name):
    result = deepcopy(document)
    identity = uuid4().hex
    result["layers"].append(dict(id=identity, name=name, visible=True, locked=False, drawing=empty_state()))
    result["active"] = identity
    return validate_document(result)


def move_selection(document, target_id, selected):
    result = deepcopy(document)
    source = active_layer(result)
    target = next(layer for layer in result["layers"] if layer["id"] == target_id)
    if source is target or not editable_layer(result) or target["locked"] or not target["visible"]:
        raise ValueError("Layer is not editable")
    state, destination = source["drawing"], target["drawing"]
    indexes = {key: set(selected.get(key, ())) for key in STATE_KEYS}
    chosen_lines = [line for i, line in enumerate(state["segments"] or []) if i in indexes["segments"]]
    for i, annotation in enumerate(state["annotations"]):
        if annotation["kind"] in ("door", "window") and supported(annotation, chosen_lines):
            indexes["annotations"].add(i)
    for key in STATE_KEYS:
        items = state[key] or []
        if any(not isinstance(i, int) or not 0 <= i < len(items) for i in indexes[key]):
            raise ValueError("Invalid layer selection")
        destination[key] = list(destination[key] or []) + [item for i, item in enumerate(items) if i in indexes[key]]
        state[key] = [item for i, item in enumerate(items) if i not in indexes[key]]
    result["active"] = target_id
    return validate_document(result)
