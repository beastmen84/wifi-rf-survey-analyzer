"""A completed Windows scan and a strict BSS read, with explicit handle lifetime."""

from ctypes import CFUNCTYPE, POINTER, byref, c_void_p, sizeof, string_at, addressof
from threading import Event
import time

FILETIME_EPOCH = 116444736000000000
SCAN_TIMEOUT_SECONDS = 4.0


def ssid_bytes_from_native(dot11_ssid):
    """Read the explicit length; ctypes c_char fields truncate at embedded NUL."""
    length = int(dot11_ssid.SSIDLength)
    if not 0 <= length <= 32:
        raise ValueError("Invalid native SSID length")
    return string_at(addressof(dot11_ssid) + type(dot11_ssid).SSID.offset, length)


def filetime_now():
    return FILETIME_EPOCH + time.time_ns() // 100


def scan_and_wait(api, interface, timeout=SCAN_TIMEOUT_SECONDS):
    """Return lifecycle evidence. Never read cache after a failure/timeout."""
    event = Event()
    state = {"status": "timeout", "started": 0, "completed": 0}
    guid_bytes = string_at(byref(interface.guid), sizeof(interface.guid))

    def notification(pointer, _context):
        data = pointer.contents
        if (data.NotificationSource & 8 and state["started"]
                and string_at(byref(data.InterfaceGuid), sizeof(data.InterfaceGuid)) == guid_bytes):
            if data.NotificationCode in (7, 8):
                state["status"] = "complete" if data.NotificationCode == 7 else "failed"
                state["completed"] = filetime_now()
                event.set()

    handle = api.WLAN.open_handle()
    callback_type = CFUNCTYPE(None, POINTER(api.WLANNotificationData), c_void_p)
    callback = callback_type(notification)  # Keep alive until handle is closed.
    try:
        register = api.WLAN_API.WlanRegisterNotification
        register.argtypes = [api.HANDLE, api.DWORD, api.BOOL, callback_type,
                             c_void_p, c_void_p, POINTER(api.DWORD)]
        register.restype = api.DWORD
        result = register(handle, 8, False, callback, None, None, None)
        if result:
            raise OSError(result, "WlanRegisterNotification")
        state["started"] = filetime_now()
        api.WLAN.wlan_scan(handle, interface.guid)
        event.wait(timeout)
    except Exception:
        state["status"] = "failed"
    finally:
        api.WLAN.close_handle(handle)
    return state


def read_bss_list(api, interface):
    """The upstream convenience reader suppresses errors as []; do not use it here."""
    from lswifi.backends.windows import bss_entry_to_record
    from lswifi.elements import WirelessNetworkBss

    handle, memory = api.WLAN.open_handle(), None
    try:
        memory = api.WLAN.get_network_bss_list(handle, interface.guid)
        entries = memory.contents
        array_type = entries.wlanBssEntries._type_ * entries.NumberOfItems
        result = []
        for entry in array_type.from_address(addressof(entries.wlanBssEntries)):
            record = bss_entry_to_record(entry, None)
            record.ssid = ssid_bytes_from_native(entry.dot11Ssid)
            try:
                parsed = WirelessNetworkBss(record, is_bytes_arg=False)
                parsed.ssid_bytes = record.ssid
                result.append(parsed)
            except Exception:
                # Preserve base RF evidence even when an optional IE cannot be decoded.
                from types import SimpleNamespace
                from wifi.band import infer_band_from_frequency_mhz
                frequency = record.frequency_mhz
                band = infer_band_from_frequency_mhz(frequency)
                channel = (14 if frequency == 2484 else (frequency - 2407) / 5) if band == "2.4" else (
                    (2 if frequency == 5935 else (frequency - 5950) / 5) if band == "6" else (frequency - 5000) / 5)
                result.append(SimpleNamespace(ssid_bytes=record.ssid, bssid=record.bssid,
                    rssi=record.rssi_dbm, frequency_mhz=frequency, channel_number=channel,
                    host_timestamp=record.host_timestamp, band=band))
        return result
    finally:
        if memory is not None:
            api.WLAN.free_memory(memory)
        api.WLAN.close_handle(handle)
