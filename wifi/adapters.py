"""Stable receiver identities and read-only Windows Wi-Fi adapter discovery."""

from app_core.logging import log_exception

CAPTURE_ADAPTER_KEY = "capture_adapter"


def adapter_identity(value):
    return str(value or "").strip().strip("{}").casefold()


def adapter_details(interface):
    def label(attribute):
        value = str(getattr(interface, attribute, "") or "").strip()
        return "" if value.casefold() == "unknown" else value

    return {
        "id": str(interface.guid),
        "name": label("connection_name"),
        "description": label("description"),
    }


def adapter_name(adapter):
    description = adapter.get("description", "")
    name = adapter.get("name", "")
    return " · ".join(dict.fromkeys(value for value in (name, description) if value)) or adapter.get("id", "")


def list_wifi_adapters():
    """Enumerate receivers without starting a scan or changing a connection."""
    try:
        from lswifi import wlanapi

        adapters = []
        for interface in wlanapi.WLAN.get_wireless_interfaces().values():
            adapter = adapter_details(interface)
            adapter["connected"] = getattr(interface, "state_string", "") == "connected"
            adapter["ready"] = getattr(interface, "state_string", "") != "not_ready"
            adapters.append(adapter)
        return sorted(adapters, key=lambda item: (not item["ready"], not item["connected"], adapter_identity(item["id"])))
    except Exception as exc:
        log_exception("Wi-Fi adapter discovery failed", exc, logger_name="wifi_scanner")
        raise RuntimeError("capture_adapter_discovery_failed") from exc
