"""Persistent symbol identities, per-shape sequences, legend rows and AP links."""
from copy import deepcopy
import json

from survey.plan_objects import NUMBERED_SYMBOLS

SYMBOL_STATE_KEY = "plan_symbol_sequences"


def symbols(document, visible_only=False):
    for layer in document["layers"]:
        if visible_only and not layer["visible"]:
            continue
        for item in layer["drawing"]["annotations"]:
            if item["kind"] == "symbol":
                yield layer, item


def validate_symbols(document):
    numbers, groups, ids = set(), set(), set()
    for _layer, item in symbols(document):
        if "number" in item or item["variant"] == "wifi_ap":
            if item["id"] in ids:
                raise ValueError("Duplicate symbol identity across layers")
            ids.add(item["id"])
        if "number" in item:
            key = (item["variant"], item["number"])
            if key in numbers:
                raise ValueError("Duplicate symbol number across layers")
            numbers.add(key)
        if "ap_group" in item:
            if item["ap_group"] in groups:
                raise ValueError("AP is assigned to multiple symbols")
            groups.add(item["ap_group"])


def sequences(metadata, document):
    raw = json.loads(metadata.get(SYMBOL_STATE_KEY, '{"version":1,"next":{}}'))
    if not isinstance(raw, dict) or raw.get("version") != 1 or not isinstance(raw.get("next"), dict):
        raise ValueError("Invalid symbol sequences")
    result = {}
    for kind in NUMBERED_SYMBOLS:
        value = raw["next"].get(kind, 1)
        if type(value) is not int or not 1 <= value <= 1000000:
            raise ValueError("Invalid symbol counter")
        result[kind] = value
    for _layer, item in symbols(document):
        if "number" in item:
            result[item["variant"]] = max(result[item["variant"]], item["number"] + 1)
    return result


def next_number(metadata, document, kind):
    number = sequences(metadata, document)[kind]
    if number > 999999:
        raise ValueError("Symbol sequence exhausted")
    return number


def retain_sequences(metadata, document):
    counters = sequences(metadata, document)
    if SYMBOL_STATE_KEY in metadata or any("number" in item for _layer, item in symbols(document)):
        metadata[SYMBOL_STATE_KEY] = json.dumps(dict(version=1, next=counters), sort_keys=True)


def prepare_symbol(metadata, document, item, previous=None):
    item = deepcopy(item)
    numbered = item.pop("_numbered", item.get("number") is not None or previous is None)
    if item.get("kind") != "symbol":
        return item
    if item["variant"] in NUMBERED_SYMBOLS and numbered:
        if not previous or previous["variant"] != item["variant"] or "number" not in previous:
            item["number"] = next_number(metadata, document, item["variant"])
    else:
        item.pop("number", None)
    if item["variant"] != "wifi_ap":
        item.pop("ap_group", None)
        item.pop("ap_label", None)
    return item


def legend_tables(document, groups=(), visible_only=True):
    records = {}
    from survey.rack_inventory import rack_records
    rack_indices={(layer['id'],item['id']):i for i,(layer,item) in enumerate(rack_records(document),1)}
    aliases = {str(g["group_id"]): str(g.get("alias") or g["group_id"])[:256] for g in groups}
    for layer, item in symbols(document, visible_only):
        if "number" not in item and item["variant"] not in ("rack", "wifi_ap"):
            continue
        record = dict(id=item["id"], layer=layer["id"], layer_name=layer["name"],
                      number=item.get("number"), description=item.get("description", ""),
                      item=deepcopy(item), ap=aliases.get(item.get("ap_group"), ""))
        if item['variant']=='rack':
            record.update(rack_index=rack_indices[layer['id'],item['id']],rack_name=item.get('rack',{}).get('name',''))
        records.setdefault(item["variant"], []).append(record)
    tables = [dict(kind=kind, rows=sorted(records[kind], key=lambda row: (row["number"] or 0, row["layer_name"], row["id"])))
              for kind in (*NUMBERED_SYMBOLS, "rack", "wifi_ap") if kind in records]
    from survey.rack_inventory import inventory_tables
    return tables + inventory_tables(document,visible_only)


def bind_ap(document, symbol_id, group_id):
    result = deepcopy(document)
    target = None
    for layer, item in symbols(result):
        if item["id"] == symbol_id and item["variant"] == "wifi_ap":
            if not layer["visible"] or layer["locked"]:
                raise ValueError("The symbol layer is not editable")
            target = item
    if target is None:
        raise ValueError("Missing AP symbol")
    if target.get("ap_group") and target["ap_group"] != group_id:
        raise ValueError("The symbol already belongs to an AP")
    for layer, item in symbols(result):
        if item.get("ap_group") == group_id:
            if layer["locked"]:
                raise ValueError("The current AP symbol is locked")
            item.pop("ap_group", None)
    if group_id:
        target["ap_group"] = group_id
    return result


def reconcile_ap_positions(document, groups):
    """Keep source geometry canonical; preserve unrelated AP metadata/positions."""
    from ap.groups import invalidate_ap_group_confirmation
    from ap.memory import clear_group_memory_flag
    document, groups = deepcopy(document), deepcopy(groups)
    by_group = {str(group["group_id"]): group for group in groups}
    claimed = {item["ap_group"] for _layer, item in symbols(document) if item.get("ap_group") in by_group}
    bound = {}
    for _layer, item in symbols(document):
        group_id = item.get("ap_group")
        if group_id and group_id not in by_group:
            successors = [key for key, group in by_group.items() if (group.get("position") or {}).get("symbol_id") == item["id"]]
            if len(successors) == 1 and successors[0] not in claimed:
                group_id = item["ap_group"] = successors[0]
                claimed.add(group_id)
        if group_id:
            if group_id not in by_group:
                item.pop("ap_group", None)
                item.pop("ap_label", None)
            else:
                item["ap_label"] = str(by_group[group_id].get("alias") or group_id)[:256]
                bound[group_id] = item
        else:
            item.pop("ap_label", None)
    for group_id, group in by_group.items():
        old = group.get("position")
        item = bound.get(group_id)
        if item:
            position = dict(x=item["cx"], y=item["cy"], symbol_id=item["id"])
            if old != position:
                if not old or old.get("x") != position["x"] or old.get("y") != position["y"]:
                    invalidate_ap_group_confirmation(group)
                group["position"] = position
                group.pop("position_cleared", None)
                group["locked"] = True
                clear_group_memory_flag(group)
        elif old and old.get("symbol_id"):
            group.pop("position", None)
            group["position_cleared"] = True
            invalidate_ap_group_confirmation(group)
            clear_group_memory_flag(group)
    return document, groups
