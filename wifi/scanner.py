"""Wi-Fi scan backends and normalization of observed networks."""

import re
import subprocess
import sys
import time
from collections import Counter
from statistics import median

from app_core.logging import log_event, log_exception
from app_core.constants import SCAN_DETAIL_FIELDNAMES, WIFI_SCAN_ATTEMPTS, WIFI_SCAN_DELAY_SECONDS
from wifi.signal import dbm_to_percent, percent_to_dbm
from wifi.band import get_row_band, infer_band_from_channel, infer_band_from_frequency_mhz, normalize_band, normalize_frequency_mhz


def scan_wifi(backend="auto", show_errors=True):
    if backend == "lswifi":
        return scan_wifi_lswifi(show_errors=show_errors), "lswifi"

    if backend == "netsh":
        return scan_wifi_netsh(show_errors=show_errors), "netsh"

    networks = scan_wifi_lswifi(show_errors=False)
    if networks:
        return networks, "lswifi"

    return scan_wifi_netsh(show_errors=show_errors), "netsh fallback"


def get_connected_ssid():
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=5,
            **hidden_subprocess_kwargs(),
        )

        for line in result.stdout.splitlines():
            line = line.strip()

            if re.match(r"^BSSID\s+:", line, flags=re.IGNORECASE):
                continue

            ssid_match = re.match(r"^SSID\s+:\s+(.*)", line, flags=re.IGNORECASE)
            if ssid_match:
                return ssid_match.group(1).strip()

    except Exception:
        return None

    return None


def hidden_subprocess_kwargs():
    if not sys.platform.startswith("win") or not hasattr(subprocess, "STARTUPINFO"):
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
    kwargs = {"startupinfo": startupinfo}
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if creationflags:
        kwargs["creationflags"] = creationflags
    return kwargs


def scan_wifi_netsh(show_errors=True):
    try:
        log_event("scan_wifi_netsh start", logger_name="wifi_scanner")
        scans = []

        for attempt in range(WIFI_SCAN_ATTEMPTS):
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                **hidden_subprocess_kwargs(),
            )
            scans.extend(annotate_raw_scan_samples(parse_netsh_output(result.stdout), attempt + 1, "netsh"))

            if attempt < WIFI_SCAN_ATTEMPTS - 1:
                time.sleep(WIFI_SCAN_DELAY_SECONDS)

        networks = merge_wifi_scans(scans, WIFI_SCAN_ATTEMPTS)
        log_event(
            f"scan_wifi_netsh done networks={len(networks)} raw_samples={len(scans)}",
            logger_name="wifi_scanner",
        )
        return networks

    except Exception as e:
        log_exception("scan_wifi_netsh failed", e, logger_name="wifi_scanner")
        report_scan_error(show_errors, "Errore scan Wi-Fi", e)
        return []


def scan_wifi_lswifi(show_errors=True):
    try:
        log_event("scan_wifi_lswifi start", logger_name="wifi_scanner")
        from lswifi import wlanapi as lswifi_wlanapi

        scans = []
        interfaces = lswifi_wlanapi.WLAN.get_wireless_interfaces()
        interface_count = max(1, len(interfaces))

        for _interface_index, interface in interfaces.items():
            for attempt in range(WIFI_SCAN_ATTEMPTS):
                try:
                    lswifi_wlanapi.WLAN.scan(interface.guid)
                except Exception:
                    pass

                time.sleep(WIFI_SCAN_DELAY_SECONDS)

                bss_list = lswifi_wlanapi.WLAN.get_wireless_network_bss_list(
                    interface,
                    False
                )
                scans.extend(annotate_raw_scan_samples(parse_lswifi_bss_list(bss_list), attempt + 1, "lswifi"))

        networks = merge_wifi_scans(scans, WIFI_SCAN_ATTEMPTS * interface_count)
        log_event(
            f"scan_wifi_lswifi done interfaces={interface_count} networks={len(networks)} raw_samples={len(scans)}",
            logger_name="wifi_scanner",
        )
        return networks

    except Exception as e:
        log_exception("scan_wifi_lswifi failed", e, logger_name="wifi_scanner")
        report_scan_error(show_errors, "Errore scan Wi-Fi lswifi", e)
        return []


def report_scan_error(show_errors, title, error):
    if show_errors:
        print(f"{title}: {error}", file=sys.stderr)


def annotate_raw_scan_samples(networks, scan_attempt, backend):
    for network in networks:
        network["scan_attempt"] = scan_attempt
        network["backend"] = backend

    return networks


def lswifi_value(value, default=""):
    return getattr(value, "value", value if value is not None else default)


def clean_scan_text(value):
    value = lswifi_value(value, "")
    text = str(value if value is not None else "").strip()

    if text.lower() in {"", "--", "-", "none", "unknown", "n/a", "na"}:
        return ""

    return text


def parse_lswifi_bss_list(bss_list):
    networks = []

    for item in bss_list:
        ssid = clean_scan_text(getattr(item, "ssid", ""))
        bssid = clean_scan_text(getattr(item, "bssid", ""))

        if not ssid or not bssid:
            continue

        try:
            signal_dbm = float(lswifi_value(getattr(item, "rssi", None)))
        except (TypeError, ValueError):
            continue

        channel = clean_scan_text(getattr(item, "channel_number", ""))
        frequency_mhz = get_lswifi_frequency_mhz(item)
        channel_width_mhz = get_lswifi_channel_width_mhz(item)
        band = get_lswifi_band(item, channel, frequency_mhz)
        radio = format_lswifi_radio(getattr(item, "phy_type", None))
        extra_details = get_lswifi_extra_details(item, frequency_mhz)

        networks.append({
            "ssid": ssid,
            "bssid": bssid,
            "signal_percent": dbm_to_percent(signal_dbm),
            "signal_dbm": signal_dbm,
            "channel": channel,
            "channel_width_mhz": channel_width_mhz,
            "band": band,
            "radio": radio,
            **extra_details,
        })

    return networks


def get_lswifi_channel_width_mhz(item):
    for attribute_name in ("channel_width", "channel_width_mhz", "width", "bandwidth"):
        raw_value = getattr(item, attribute_name, None)
        width = normalize_channel_width_mhz(lswifi_value(raw_value, ""))

        if width:
            return width

    return ""


def get_lswifi_frequency_mhz(item):
    for attribute_name in (
        "frequency_mhz",
        "center_frequency_mhz",
        "channel_frequency",
        "frequency",
        "center_frequency",
        "ch_center_frequency",
        "channel_number",
    ):
        raw_value = getattr(item, attribute_name, None)
        if attribute_name == "channel_number" and not hasattr(raw_value, "frequency"):
            continue

        for value in get_lswifi_frequency_candidates(raw_value):
            frequency = format_frequency_mhz(value)
            if frequency:
                return frequency

    return ""


def get_lswifi_frequency_candidates(value):
    if value is None:
        return []

    candidates = []
    for attribute_name in ("frequency", "value"):
        if hasattr(value, attribute_name):
            candidates.append(getattr(value, attribute_name))

    candidates.append(value)
    return candidates


def format_frequency_mhz(value):
    frequency = normalize_frequency_mhz(value)
    if frequency is None:
        return ""

    if abs(frequency - round(frequency)) < 0.001:
        return str(int(round(frequency)))

    return f"{frequency:.3f}".rstrip("0").rstrip(".")


def get_lswifi_band(item, channel, frequency_mhz=""):
    for attribute_name in ("band", "frequency_band", "wifi_band"):
        band = normalize_band(lswifi_value(getattr(item, attribute_name, ""), ""))
        if band:
            return band

    if frequency_mhz:
        band = infer_band_from_frequency_mhz(frequency_mhz)
        if band:
            return band

    for attribute_name in ("channel_frequency", "frequency_mhz", "frequency", "center_frequency", "center_frequency_mhz"):
        band = infer_band_from_frequency_mhz(lswifi_value(getattr(item, attribute_name, ""), ""))
        if band:
            return band

    return infer_band_from_channel(channel)


def get_lswifi_extra_details(item, frequency_mhz=""):
    return {
        "frequency_mhz": frequency_mhz,
        "security": get_lswifi_text(item, "security"),
        "auth": get_lswifi_text(item, "auth", "authentication"),
        "encryption": get_lswifi_text(item, "encryption", "cipher"),
        "pmf": get_lswifi_text(item, "pmf"),
        "country_code": get_lswifi_text(item, "country_code"),
        "spatial_streams": get_lswifi_text(item, "spatial_streams"),
        "stations": get_lswifi_text(item, "stations"),
        "channel_utilization": get_lswifi_text(item, "utilization", "channel_utilization"),
        "wifi_modes": get_lswifi_list_text(item, "modes"),
        "amendments": get_lswifi_list_text(item, "amendments"),
        "vendor": get_lswifi_vendor(item),
        "model": get_lswifi_model(item),
        "ap_name": get_lswifi_text(item, "apname", "ap_name", "device_name"),
    }


def get_lswifi_text(item, *attribute_names):
    for attribute_name in attribute_names:
        text = clean_scan_text(getattr(item, attribute_name, None))
        if text:
            return text

    return ""


def get_lswifi_list_text(item, attribute_name):
    value = getattr(item, attribute_name, None)
    elements = getattr(value, "elements", None)
    if elements is not None:
        return format_scan_list(elements)

    if isinstance(value, (list, tuple, set)):
        return format_scan_list(value)

    return clean_scan_text(value)


def format_scan_list(values):
    clean_values = sorted({
        str(value).strip()
        for value in values
        if str(value).strip()
    })
    return "/".join(clean_values)


def get_lswifi_vendor(item):
    vendor = get_lswifi_text(item, "vendor", "manufacturer", "oui_vendor", "bssid_vendor")
    if vendor:
        return vendor

    return extract_lswifi_information_element_value(item, "manufacturer")


def get_lswifi_model(item):
    model = get_lswifi_text(item, "model", "model_name", "model_number")
    if model:
        return model

    return (
        extract_lswifi_information_element_value(item, "model name")
        or extract_lswifi_information_element_value(item, "model number")
    )


def extract_lswifi_information_element_value(item, label):
    label_pattern = re.escape(label).replace(r"\ ", r"\s+")
    pattern = re.compile(rf"^\s*{label_pattern}\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)

    for information_element in getattr(item, "information_elements", []) or []:
        decoded = clean_scan_text(getattr(information_element, "decoded", ""))
        if not decoded:
            continue

        match = pattern.search(decoded)
        if match:
            return clean_scan_text(match.group(1))

    return ""


def normalize_channel_width_mhz(value):
    text = str(value or "").strip()

    if not text or text == "--":
        return ""

    if "80+80" in text:
        return 160

    match = re.search(r"(20|40|80|160|320)", text)
    if not match:
        return ""

    return int(match.group(1))


def format_lswifi_radio(phy_type):
    amendment = str(getattr(phy_type, "amendment", "") or "").strip()
    name = str(getattr(phy_type, "name", "") or "").strip()

    if amendment:
        return f"802.11{amendment}"

    if "802.11" in name:
        match = re.search(r"802\.11([a-z]+)", name)
        if match:
            return f"802.11{match.group(1)}"

    return name


def merge_wifi_scans(networks, samples_total=1):
    merged_networks = {}

    for network in networks:
        key = (
            normalize_merge_text(network.get("ssid")),
            normalize_merge_text(network.get("bssid")).lower(),
            normalize_merge_text(network.get("channel")),
            get_row_band(network),
        )
        merged_networks.setdefault(key, []).append(network)

    aggregated_networks = []

    for samples in merged_networks.values():
        valid_samples = []
        signal_values = []
        for sample in samples:
            try:
                signal_dbm = float(sample.get("signal_dbm", ""))
            except (TypeError, ValueError):
                continue

            valid_samples.append((sample, signal_dbm))
            signal_values.append(signal_dbm)

        if not signal_values:
            continue

        signal_median = float(median(signal_values))
        signal_max = max(signal_values)
        signal_min = min(signal_values)
        representative = max(valid_samples, key=lambda item: item[1])[0]
        samples_seen = len(signal_values)
        scan_confidence = min(1.0, samples_seen / max(1, samples_total))

        aggregated_networks.append({
            "ssid": representative.get("ssid", ""),
            "bssid": representative.get("bssid", ""),
            "signal_percent": dbm_to_percent(signal_median),
            "signal_dbm": signal_median,
            "signal_median_dbm": signal_median,
            "signal_max_dbm": signal_max,
            "signal_min_dbm": signal_min,
            "signal_samples_dbm": ";".join(format_dbm_sample(value) for value in signal_values),
            "samples_seen": samples_seen,
            "samples_total": samples_total,
            "scan_confidence": round(scan_confidence, 3),
            "channel": representative.get("channel", ""),
            "channel_width_mhz": most_common_non_empty(samples, "channel_width_mhz"),
            "band": most_common_non_empty(samples, "band") or most_common_row_band(samples) or infer_band_from_channel(representative.get("channel")),
            "radio": most_common_non_empty(samples, "radio"),
            **{field: most_common_non_empty(samples, field) for field in SCAN_DETAIL_FIELDNAMES},
            "raw_samples": samples
        })

    return aggregated_networks


def normalize_merge_text(value):
    return str(value or "").strip()


def most_common_non_empty(samples, key):
    values = [
        str(sample.get(key, "")).strip()
        for sample in samples
        if str(sample.get(key, "")).strip()
    ]

    if not values:
        return ""

    return Counter(values).most_common(1)[0][0]


def most_common_row_band(samples):
    values = []
    for sample in samples:
        band = get_row_band(sample)
        if band:
            values.append(band)

    if not values:
        return ""

    return Counter(values).most_common(1)[0][0]


def format_dbm_sample(value):
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"


def parse_netsh_output(output):
    networks = []

    current_ssid = None
    current_bssid = None
    current_signal = None
    current_channel = None
    current_radio = None
    current_auth = None
    current_encryption = None

    def append_current_network():
        if current_ssid and current_bssid and current_signal is not None:
            security = " / ".join(value for value in (current_auth, current_encryption) if value)
            networks.append({
                "ssid": current_ssid,
                "bssid": current_bssid,
                "signal_percent": current_signal,
                "signal_dbm": percent_to_dbm(current_signal),
                "channel": current_channel,
                "channel_width_mhz": "",
                "band": infer_band_from_channel(current_channel),
                "radio": current_radio,
                "security": security,
                "auth": current_auth or "",
                "encryption": current_encryption or "",
            })

    for line in output.splitlines():
        line = line.strip()

        ssid_match = re.match(r"SSID\s+\d+\s+:\s+(.*)", line)
        if ssid_match:
            append_current_network()
            current_ssid = ssid_match.group(1).strip()
            current_bssid = None
            current_signal = None
            current_channel = None
            current_radio = None
            current_auth = None
            current_encryption = None
            continue

        bssid_match = re.match(r"BSSID\s+\d+\s+:\s+(.*)", line)
        if bssid_match:
            append_current_network()
            current_bssid = bssid_match.group(1).strip()
            current_signal = None
            current_channel = None
            current_radio = None
            continue

        auth_match = re.match(r"Authentication\s+:\s+(.*)", line)
        if auth_match:
            current_auth = auth_match.group(1).strip()
            continue

        encryption_match = re.match(r"Encryption\s+:\s+(.*)", line)
        if encryption_match:
            current_encryption = encryption_match.group(1).strip()
            continue

        signal_match = re.match(r"Signal\s+:\s+(\d+)%", line)
        if signal_match:
            current_signal = int(signal_match.group(1))
            continue

        channel_match = re.match(r"Channel\s+:\s+(\d+)", line)
        if channel_match:
            current_channel = channel_match.group(1)
            continue

        radio_match = re.match(r"Radio type\s+:\s+(.*)", line)
        if radio_match:
            current_radio = radio_match.group(1).strip()
            continue

    append_current_network()

    return networks
