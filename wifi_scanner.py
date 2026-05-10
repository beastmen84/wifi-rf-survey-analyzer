"""Wi-Fi scan backends and normalization of observed networks."""

import re
import subprocess
import sys
import time
from collections import Counter
from statistics import median

from app_logging import log_event, log_exception
from constants import WIFI_SCAN_ATTEMPTS, WIFI_SCAN_DELAY_SECONDS
from utils import dbm_to_percent, percent_to_dbm


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
            timeout=5
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
                errors="ignore"
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


def parse_lswifi_bss_list(bss_list):
    networks = []

    for item in bss_list:
        ssid = str(lswifi_value(getattr(item, "ssid", ""))).strip()
        bssid = str(lswifi_value(getattr(item, "bssid", ""))).strip()

        if not ssid or not bssid:
            continue

        try:
            signal_dbm = float(lswifi_value(getattr(item, "rssi", None)))
        except (TypeError, ValueError):
            continue

        channel = str(lswifi_value(getattr(item, "channel_number", ""))).strip()
        channel_width_mhz = get_lswifi_channel_width_mhz(item)
        radio = format_lswifi_radio(getattr(item, "phy_type", None))

        networks.append({
            "ssid": ssid,
            "bssid": bssid,
            "signal_percent": dbm_to_percent(signal_dbm),
            "signal_dbm": signal_dbm,
            "channel": channel,
            "channel_width_mhz": channel_width_mhz,
            "radio": radio
        })

    return networks


def get_lswifi_channel_width_mhz(item):
    for attribute_name in ("channel_width", "channel_width_mhz", "width", "bandwidth"):
        raw_value = getattr(item, attribute_name, None)
        width = normalize_channel_width_mhz(lswifi_value(raw_value, ""))

        if width:
            return width

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
            network.get("ssid"),
            network.get("bssid"),
            network.get("channel")
        )
        merged_networks.setdefault(key, []).append(network)

    aggregated_networks = []

    for samples in merged_networks.values():
        signal_values = [
            float(sample["signal_dbm"])
            for sample in samples
            if sample.get("signal_dbm") not in ("", None)
        ]

        if not signal_values:
            continue

        signal_median = float(median(signal_values))
        signal_max = max(signal_values)
        signal_min = min(signal_values)
        representative = max(samples, key=lambda sample: float(sample.get("signal_dbm", -1000)))
        samples_seen = len(signal_values)
        scan_confidence = samples_seen / max(1, samples_total)

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
            "radio": most_common_non_empty(samples, "radio"),
            "raw_samples": samples
        })

    return aggregated_networks


def most_common_non_empty(samples, key):
    values = [
        str(sample.get(key, "")).strip()
        for sample in samples
        if str(sample.get(key, "")).strip()
    ]

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

    def append_current_network():
        if current_ssid and current_bssid and current_signal is not None:
            networks.append({
                "ssid": current_ssid,
                "bssid": current_bssid,
                "signal_percent": current_signal,
                "signal_dbm": percent_to_dbm(current_signal),
                "channel": current_channel,
                "channel_width_mhz": "",
                "radio": current_radio
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
            continue

        bssid_match = re.match(r"BSSID\s+\d+\s+:\s+(.*)", line)
        if bssid_match:
            append_current_network()
            current_bssid = bssid_match.group(1).strip()
            current_signal = None
            current_channel = None
            current_radio = None
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
