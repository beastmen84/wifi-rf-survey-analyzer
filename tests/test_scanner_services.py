from tests._common import *
from unittest.mock import patch
import wifi.scanner as scanner_module

class WifiScannerTests(unittest.TestCase):
    def test_get_connected_ssid_hides_netsh_window_on_windows(self):
        calls = []

        class Result:
            stdout = """
Name                   : Wi-Fi
SSID                   : MAIN
BSSID                  : 70:4f:57:aa:bb:10
"""

        def fake_run(*_args, **kwargs):
            calls.append(kwargs)
            return Result()

        with (
            patch.object(scanner_module, "get_connected_ssid_lswifi", return_value=""),
            patch.object(scanner_module.subprocess, "run", side_effect=fake_run),
        ):
            ssid = scanner_module.get_connected_ssid()

        self.assertEqual(ssid, "MAIN")
        self.assertEqual(len(calls), 1)
        if scanner_module.sys.platform.startswith("win") and hasattr(scanner_module.subprocess, "STARTUPINFO"):
            self.assertIn("startupinfo", calls[0])
            creationflags = getattr(scanner_module.subprocess, "CREATE_NO_WINDOW", 0)
            if creationflags:
                self.assertEqual(calls[0].get("creationflags"), creationflags)

    def test_get_connected_ssid_prefers_lswifi_without_netsh(self):
        with (
            patch.object(scanner_module, "get_connected_ssid_lswifi", return_value="MAIN"),
            patch.object(scanner_module.subprocess, "run") as run_mock,
        ):
            ssid = scanner_module.get_connected_ssid()

        self.assertEqual(ssid, "MAIN")
        run_mock.assert_not_called()

    def test_decode_lswifi_ssid_strips_null_padding(self):
        self.assertEqual(scanner_module.decode_lswifi_ssid(b"MAIN\x00\x00\x00"), "MAIN")

    def test_parse_netsh_interfaces_output_reads_connected_bssid(self):
        output = """
Name                   : Wi-Fi
State                  : connected
SSID                   : MAIN
AP BSSID               : 70:4f:57:aa:bb:10
Band                   : 5 GHz
Channel                : 40
Radio type             : 802.11ax
Signal                 : 90%
Rssi                   : -44
"""

        connected = scanner_module.parse_netsh_interfaces_output(output)

        self.assertEqual(connected["ssid"], "MAIN")
        self.assertEqual(connected["bssid"], "70:4f:57:aa:bb:10")
        self.assertEqual(connected["band"], "5")
        self.assertEqual(connected["channel"], "40")
        self.assertEqual(connected["radio"], "802.11ax")
        self.assertEqual(connected["signal_percent"], 90)
        self.assertEqual(connected["signal_dbm"], -44.0)

    def test_parse_netsh_interfaces_output_ignores_disconnected_interface(self):
        output = """
Name                   : Wi-Fi
State                  : disconnected
SSID                   : MAIN
AP BSSID               : 70:4f:57:aa:bb:10
"""

        self.assertEqual(scanner_module.parse_netsh_interfaces_output(output), {})

    def test_parse_netsh_output_handles_multiple_bssids_per_ssid(self):
        output = """
SSID 1 : MAIN
    Network type            : Infrastructure
    Authentication          : WPA2-Personal
    Encryption              : CCMP
    BSSID 1                 : 70:4f:57:aa:bb:10
         Signal             : 82%
         Radio type         : 802.11ax
         Channel            : 6
    BSSID 2                 : 70:4f:57:aa:bb:11
         Signal             : 64%
         Radio type         : 802.11ax
         Channel            : 11
SSID 2 : GUEST
    BSSID 1                 : 90:11:22:33:44:10
         Signal             : 50%
         Radio type         : 802.11n
         Channel            : 1
"""

        networks = parse_netsh_output(output)

        self.assertEqual(len(networks), 3)
        self.assertEqual(networks[0]["ssid"], "MAIN")
        self.assertEqual(networks[0]["bssid"], "70:4f:57:aa:bb:10")
        self.assertEqual(networks[0]["signal_dbm"], -59.0)
        self.assertEqual(networks[0]["auth"], "WPA2-Personal")
        self.assertEqual(networks[0]["encryption"], "CCMP")
        self.assertEqual(networks[0]["security"], "WPA2-Personal / CCMP")
        self.assertEqual(networks[1]["auth"], "WPA2-Personal")
        self.assertEqual(networks[1]["channel"], "11")
        self.assertEqual(networks[2]["ssid"], "GUEST")
        self.assertEqual(networks[2]["auth"], "")

    def test_parse_lswifi_bss_list_normalizes_width_and_radio(self):
        networks = parse_lswifi_bss_list([
            FakeLswifiBss(
                ssid="MAIN",
                bssid="70:4f:57:aa:bb:10",
                rssi="-61",
                channel_number=36,
                channel_width="80+80 MHz",
                phy_type=FakeLswifiPhy(amendment="ax"),
                channel_frequency=FakeLswifiValue("5.180"),
                security="WPA2-Personal / CCMP",
                auth=FakeLswifiValue("WPA2-Personal"),
                encryption=FakeLswifiValue("CCMP"),
                pmf="Disabled",
                country_code="IT",
                spatial_streams="2",
                stations="4",
                utilization="18%",
                modes=FakeLswifiList(["n", "ax"]),
                amendments=FakeLswifiList(["i", "k", "v"]),
                ap_name="office-ap",
                information_elements=[
                    FakeLswifiInformationElement(
                        "Manufacturer: Acme\nModel Name: AX-1"
                    )
                ],
            ),
            FakeLswifiBss(ssid="", bssid="80:11:22:33:44:10", rssi="-70", channel_number=1),
        ])

        self.assertEqual(len(networks), 1)
        self.assertEqual(networks[0]["signal_dbm"], -61.0)
        self.assertEqual(networks[0]["signal_percent"], 78)
        self.assertEqual(networks[0]["channel"], "36")
        self.assertEqual(networks[0]["channel_width_mhz"], 160)
        self.assertEqual(networks[0]["band"], "5")
        self.assertEqual(networks[0]["radio"], "802.11ax")
        self.assertEqual(networks[0]["frequency_mhz"], "5180")
        self.assertEqual(networks[0]["security"], "WPA2-Personal / CCMP")
        self.assertEqual(networks[0]["auth"], "WPA2-Personal")
        self.assertEqual(networks[0]["encryption"], "CCMP")
        self.assertEqual(networks[0]["pmf"], "Disabled")
        self.assertEqual(networks[0]["country_code"], "IT")
        self.assertEqual(networks[0]["spatial_streams"], "2")
        self.assertEqual(networks[0]["stations"], "4")
        self.assertEqual(networks[0]["channel_utilization"], "18%")
        self.assertEqual(networks[0]["wifi_modes"], "ax/n")
        self.assertEqual(networks[0]["amendments"], "i/k/v")
        self.assertEqual(networks[0]["vendor"], "Acme")
        self.assertEqual(networks[0]["model"], "AX-1")
        self.assertEqual(networks[0]["ap_name"], "office-ap")

    def test_parse_lswifi_bss_list_reads_frequency_based_6ghz_band(self):
        networks = parse_lswifi_bss_list([
            FakeLswifiBss(
                ssid="MAIN",
                bssid="70:4f:57:aa:bb:10",
                rssi="-61",
                channel_number=5,
                channel_frequency=FakeLswifiValue("5.975"),
            ),
        ])

        self.assertEqual(len(networks), 1)
        self.assertEqual(networks[0]["channel"], "5")
        self.assertEqual(networks[0]["band"], "6")
        self.assertEqual(networks[0]["frequency_mhz"], "5975")

    def test_parse_lswifi_bss_list_marks_connected_bssid(self):
        networks = parse_lswifi_bss_list(
            [
                FakeLswifiBss(ssid="MAIN", bssid="70:4F:57:AA:BB:10", rssi="-61", channel_number=36),
                FakeLswifiBss(ssid="GUEST", bssid="70:4f:57:aa:bb:11", rssi="-70", channel_number=36),
            ],
            connected_bssids={"70-4f-57-aa-bb-10"},
        )

        self.assertTrue(networks[0]["is_connected"])
        self.assertFalse(networks[1]["is_connected"])

    def test_mark_connected_networks_uses_normalized_bssid(self):
        networks = [
            {"ssid": "MAIN", "bssid": "70:4F:57:AA:BB:10"},
            {"ssid": "MAIN", "bssid": "70:4f:57:aa:bb:11"},
        ]

        scanner_module.mark_connected_networks(networks, {"bssid": "70-4f-57-aa-bb-10"})

        self.assertTrue(networks[0]["is_connected"])
        self.assertFalse(networks[1]["is_connected"])

    def test_scan_wifi_netsh_marks_connected_bssid_from_interface_state(self):
        calls = []
        networks_output = """
SSID 1 : MAIN
    BSSID 1                 : 70:4f:57:aa:bb:10
         Signal             : 82%
         Radio type         : 802.11ax
         Channel            : 40
    BSSID 2                 : 70:4f:57:aa:bb:11
         Signal             : 70%
         Radio type         : 802.11ax
         Channel            : 40
"""
        interfaces_output = """
Name                   : Wi-Fi
State                  : connected
SSID                   : MAIN
AP BSSID               : 70:4f:57:aa:bb:10
"""

        class Result:
            def __init__(self, stdout):
                self.stdout = stdout

        def fake_run(args, *_positional, **_kwargs):
            calls.append(args)
            if args == ["netsh", "wlan", "show", "interfaces"]:
                return Result(interfaces_output)
            return Result(networks_output)

        with (
            patch.object(scanner_module, "WIFI_SCAN_ATTEMPTS", 1),
            patch.object(scanner_module.subprocess, "run", side_effect=fake_run),
        ):
            networks = scanner_module.scan_wifi_netsh(show_errors=False)

        self.assertEqual(len(networks), 2)
        self.assertTrue(networks[0]["is_connected"])
        self.assertFalse(networks[1]["is_connected"])
        self.assertIn(["netsh", "wlan", "show", "interfaces"], calls)

    def test_frequency_band_inference_accepts_mhz_khz_hz_and_ghz_values(self):
        self.assertEqual(infer_band_from_frequency_mhz(5975), "6")
        self.assertEqual(infer_band_from_frequency_mhz(5975000), "6")
        self.assertEqual(infer_band_from_frequency_mhz(5975000000), "6")
        self.assertEqual(infer_band_from_frequency_mhz(5.975), "6")
        self.assertEqual(normalize_frequency_mhz("5.975 GHz"), 5975)

    def test_merge_wifi_scans_aggregates_samples_and_confidence(self):
        samples = [
            {
                "ssid": "MAIN",
                "bssid": "70:4f:57:aa:bb:10",
                "signal_dbm": -52,
                "channel": "6",
                "channel_width_mhz": "20",
                "radio": "802.11ax",
                "frequency_mhz": "2437",
                "security": "WPA2-Personal / CCMP",
                "auth": "WPA2-Personal",
                "encryption": "CCMP",
                "pmf": "Disabled",
                "country_code": "IT",
                "spatial_streams": "2",
                "stations": "4",
                "channel_utilization": "18%",
                "wifi_modes": "ax/n",
                "amendments": "i/k/v",
                "vendor": "Acme",
                "model": "AX-1",
                "ap_name": "office-ap",
            },
            {
                "ssid": "MAIN",
                "bssid": "70:4f:57:aa:bb:10",
                "signal_dbm": -48,
                "channel": "6",
                "channel_width_mhz": "20",
                "radio": "802.11ax",
                "frequency_mhz": "2437",
                "security": "WPA2-Personal / CCMP",
                "auth": "WPA2-Personal",
                "encryption": "CCMP",
                "pmf": "Disabled",
                "country_code": "IT",
                "spatial_streams": "2",
                "stations": "4",
                "channel_utilization": "18%",
                "wifi_modes": "ax/n",
                "amendments": "i/k/v",
                "vendor": "Acme",
                "model": "AX-1",
                "ap_name": "office-ap",
            },
            {"ssid": "MAIN", "bssid": "70:4f:57:aa:bb:10", "signal_dbm": -55, "channel": "6", "channel_width_mhz": "40", "radio": "802.11ax"},
        ]

        networks = merge_wifi_scans(samples, samples_total=5)

        self.assertEqual(len(networks), 1)
        self.assertEqual(networks[0]["signal_dbm"], -52.0)
        self.assertEqual(networks[0]["signal_median_dbm"], -52.0)
        self.assertEqual(networks[0]["signal_max_dbm"], -48)
        self.assertEqual(networks[0]["signal_min_dbm"], -55)
        self.assertEqual(networks[0]["signal_samples_dbm"], "-52;-48;-55")
        self.assertEqual(networks[0]["samples_seen"], 3)
        self.assertEqual(networks[0]["samples_total"], 5)
        self.assertEqual(networks[0]["scan_confidence"], 0.6)
        self.assertEqual(networks[0]["channel_width_mhz"], "20")
        self.assertEqual(networks[0]["band"], "2.4")
        self.assertEqual(networks[0]["frequency_mhz"], "2437")
        self.assertEqual(networks[0]["pmf"], "Disabled")
        self.assertEqual(networks[0]["channel_utilization"], "18%")
        self.assertEqual(networks[0]["wifi_modes"], "ax/n")
        self.assertEqual(networks[0]["vendor"], "Acme")
        self.assertEqual(networks[0]["model"], "AX-1")
        self.assertEqual(networks[0]["ap_name"], "office-ap")
        self.assertFalse(networks[0]["is_connected"])
        self.assertIs(networks[0]["raw_samples"][0], samples[0])

    def test_merge_wifi_scans_keeps_same_channel_different_bands_separate(self):
        samples = [
            {"ssid": "MAIN", "bssid": "70:4f:57:aa:bb:10", "signal_dbm": -52, "channel": "5", "band": "2.4"},
            {"ssid": "MAIN", "bssid": "70:4f:57:aa:bb:10", "signal_dbm": -48, "channel": "5", "band": "6"},
        ]

        networks = merge_wifi_scans(samples, samples_total=1)

        self.assertEqual(len(networks), 2)
        self.assertEqual({network["band"] for network in networks}, {"2.4", "6"})

    def test_merge_wifi_scans_uses_frequency_when_band_is_missing(self):
        samples = [
            {"ssid": "MAIN", "bssid": "70:4f:57:aa:bb:10", "signal_dbm": -52, "channel": "5"},
            {"ssid": "MAIN", "bssid": "70:4f:57:aa:bb:10", "signal_dbm": -48, "channel": "5", "frequency_mhz": "5975"},
        ]

        networks = merge_wifi_scans(samples, samples_total=1)

        self.assertEqual(len(networks), 2)
        self.assertEqual({network["band"] for network in networks}, {"2.4", "6"})

    def test_merge_wifi_scans_ignores_invalid_signal_samples_but_keeps_raw_samples(self):
        samples = [
            {"ssid": "MAIN", "bssid": "70:4f:57:aa:bb:10", "signal_dbm": "", "channel": "6", "channel_width_mhz": "40"},
            {"ssid": "MAIN", "bssid": "70:4f:57:aa:bb:10", "signal_dbm": -60, "channel": "6", "channel_width_mhz": "20"},
            {"ssid": "MAIN", "bssid": "70:4f:57:aa:bb:10", "signal_dbm": "bad", "channel": "6", "channel_width_mhz": "80"},
        ]

        networks = merge_wifi_scans(samples, samples_total=3)

        self.assertEqual(len(networks), 1)
        self.assertEqual(networks[0]["signal_dbm"], -60.0)
        self.assertEqual(networks[0]["samples_seen"], 1)
        self.assertEqual(networks[0]["scan_confidence"], 0.333)
        self.assertEqual(networks[0]["raw_samples"], samples)

    def test_merge_wifi_scans_clamps_confidence_to_one(self):
        samples = [
            {"ssid": "MAIN", "bssid": "70:4f:57:aa:bb:10", "signal_dbm": -52, "channel": "6"},
            {"ssid": "MAIN", "bssid": "70:4f:57:aa:bb:10", "signal_dbm": -48, "channel": "6"},
            {"ssid": "MAIN", "bssid": "70:4f:57:aa:bb:10", "signal_dbm": -50, "channel": "6"},
        ]

        networks = merge_wifi_scans(samples, samples_total=2)

        self.assertEqual(networks[0]["samples_seen"], 3)
        self.assertEqual(networks[0]["scan_confidence"], 1.0)

    def test_merge_wifi_scans_groups_bssid_case_insensitively(self):
        networks = merge_wifi_scans(
            [
                {"ssid": "MAIN", "bssid": "70:4F:57:AA:BB:10", "signal_dbm": -60, "channel": "6"},
                {"ssid": "MAIN", "bssid": "70:4f:57:aa:bb:10", "signal_dbm": -50, "channel": "6"},
            ],
            samples_total=2,
        )

        self.assertEqual(len(networks), 1)
        self.assertEqual(networks[0]["signal_median_dbm"], -55.0)
        self.assertEqual(networks[0]["samples_seen"], 2)

    def test_annotate_raw_scan_samples_updates_samples_in_place(self):
        samples = [{"ssid": "MAIN"}, {"ssid": "GUEST"}]

        annotated = annotate_raw_scan_samples(samples, 3, "netsh")

        self.assertIs(annotated, samples)
        self.assertEqual({sample["scan_attempt"] for sample in samples}, {3})
        self.assertEqual({sample["backend"] for sample in samples}, {"netsh"})

    def test_normalize_channel_width_mhz_handles_common_text_values(self):
        self.assertEqual(normalize_channel_width_mhz("20 MHz"), 20)
        self.assertEqual(normalize_channel_width_mhz("80+80 MHz"), 160)
        self.assertEqual(normalize_channel_width_mhz("--"), "")
        self.assertEqual(normalize_channel_width_mhz("unknown"), "")


class UiScalingTests(unittest.TestCase):
    def test_ui_scale_helpers_are_predictable(self):
        self.assertEqual(normalize_ui_scale_mode("125%"), "125")
        self.assertEqual(normalize_ui_scale_mode("auto"), "auto")
        self.assertEqual(normalize_ui_scale_mode("bad"), "auto")
        self.assertEqual(scale_px(10, 1.25), 12)
        self.assertGreater(scale_font(10, 1.25), 10)

    def test_ui_auto_scale_matches_common_resolutions(self):
        self.assertEqual(scale_percent_for_resolution(1920, 1080), 100)
        self.assertEqual(scale_percent_for_resolution(2560, 1440), 125)
        self.assertEqual(scale_percent_for_resolution(2560, 1600), 125)
        self.assertEqual(scale_percent_for_resolution(3840, 2160), 150)

    def test_ui_scale_percent_is_relative_to_resolution_class(self):
        self.assertEqual(effective_scale_for_percent(125, 125), 1.0)
        self.assertEqual(effective_scale_for_percent(100, 125), 0.8)
        self.assertEqual(effective_scale_for_percent(150, 125), 1.2)

    def test_screen_resolution_uses_device_pixel_ratio(self):
        screen = FakeScreen(1280, 800, 2.0)

        self.assertEqual(detect_screen_resolution(screen), (2560, 1600))

    def test_ui_scale_diagnostics_format_is_stable(self):
        diagnostics = {
            "mode": "125",
            "auto_percent": 125,
            "effective_scale": 1.0,
            "screen": "2560x1600",
        }

        self.assertEqual(
            format_ui_scale_diagnostics(diagnostics),
            "mode=125 auto_percent=125 effective_scale=1.0 screen=2560x1600",
        )

    def test_ui_scale_diagnostics_accepts_app_like_object(self):
        app = FakeApp(FakeScreen(2560, 1600, 1.0))

        diagnostics = ui_scale_diagnostics("100", app)

        self.assertEqual(diagnostics["auto_percent"], 125)
        self.assertEqual(diagnostics["effective_scale"], 0.8)
        self.assertEqual(diagnostics["screen"], "2560x1600")


class AppRestartTests(unittest.TestCase):
    def test_restart_command_uses_python_script_in_source_mode(self):
        command = build_restart_command(
            executable="python.exe",
            argv=["main.py", "--debug"],
            frozen=False,
        )

        self.assertEqual(command, ["python.exe", "main.py", "--debug"])

    def test_restart_command_uses_executable_only_in_frozen_mode(self):
        command = build_restart_command(
            executable="wifi_heatmap.exe",
            argv=["wifi_heatmap.exe", "--debug"],
            frozen=True,
        )

        self.assertEqual(command, ["wifi_heatmap.exe", "--debug"])


class AppSettingsTests(unittest.TestCase):
    def test_measurement_unit_helpers_convert_without_changing_internal_meters(self):
        self.assertEqual(normalize_measurement_system("bad"), MEASUREMENT_SYSTEM_METRIC)
        self.assertAlmostEqual(meters_to_display_units(10, MEASUREMENT_SYSTEM_IMPERIAL), 32.8084, places=3)
        self.assertAlmostEqual(display_units_to_meters(32.8084, MEASUREMENT_SYSTEM_IMPERIAL), 10.0, places=3)
        self.assertEqual(format_distance_meters(10, MEASUREMENT_SYSTEM_METRIC), "10 m")
        self.assertEqual(format_distance_meters(10, MEASUREMENT_SYSTEM_IMPERIAL), "32.8 ft")

    def test_measurement_system_preference_is_saved(self):
        previous = os.environ.get("WIFI_HEATMAP_SETTINGS_FILE")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.environ["WIFI_HEATMAP_SETTINGS_FILE"] = os.path.join(temp_dir, "settings.json")

                self.assertEqual(get_saved_measurement_system(), MEASUREMENT_SYSTEM_METRIC)
                self.assertTrue(save_measurement_system(MEASUREMENT_SYSTEM_IMPERIAL))

                self.assertEqual(get_saved_measurement_system(), MEASUREMENT_SYSTEM_IMPERIAL)
                self.assertEqual(
                    get_saved_measurement_system(valid_modes=(MEASUREMENT_SYSTEM_METRIC,)),
                    MEASUREMENT_SYSTEM_METRIC,
                )
        finally:
            if previous is None:
                os.environ.pop("WIFI_HEATMAP_SETTINGS_FILE", None)
            else:
                os.environ["WIFI_HEATMAP_SETTINGS_FILE"] = previous

    def test_last_survey_directory_uses_saved_file_parent(self):
        previous = os.environ.get("WIFI_HEATMAP_SETTINGS_FILE")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                settings_file = os.path.join(temp_dir, "settings.json")
                survey_file = os.path.join(temp_dir, "surveys", "test.csv")
                os.makedirs(os.path.dirname(survey_file), exist_ok=True)
                os.environ["WIFI_HEATMAP_SETTINGS_FILE"] = settings_file

                self.assertTrue(save_last_survey_path(survey_file))

                self.assertEqual(get_last_survey_directory(), os.path.dirname(survey_file))
        finally:
            if previous is None:
                os.environ.pop("WIFI_HEATMAP_SETTINGS_FILE", None)
            else:
                os.environ["WIFI_HEATMAP_SETTINGS_FILE"] = previous


class LoggingTests(unittest.TestCase):
    def test_info_console_filter_excludes_warnings_and_errors(self):
        log_filter = MaxLogLevelFilter(logging.INFO)

        self.assertTrue(log_filter.filter(logging.LogRecord(
            "test",
            logging.INFO,
            __file__,
            1,
            "info",
            (),
            None,
        )))
        self.assertFalse(log_filter.filter(logging.LogRecord(
            "test",
            logging.WARNING,
            __file__,
            1,
            "warning",
            (),
            None,
        )))


class QtWindowingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_dim_push_ignores_dialog_that_is_already_hidden(self):
        parent = QWidget()
        parent.show()
        dialog = QDialog(parent)
        dialog.show()
        dialog.hide()

        push_modal_dim(dialog)

        self.assertIsNone(getattr(parent.window(), "_wifi_heatmap_dim_overlay", None))
        dialog.deleteLater()
        parent.deleteLater()

    def test_dim_pop_clears_overlay_and_active_token(self):
        parent = QWidget()
        parent.resize(300, 200)
        parent.show()
        dialog = QDialog(parent)
        dialog.show()

        push_modal_dim(dialog)
        self.assertIsNotNone(getattr(parent.window(), "_wifi_heatmap_dim_overlay", None))

        pop_modal_dim(dialog)

        self.assertEqual(getattr(parent.window(), "_wifi_heatmap_dim_count", 0), 0)
        self.assertEqual(getattr(parent.window(), "_wifi_heatmap_dim_tokens", set()), set())
        self.assertIsNone(getattr(parent.window(), "_wifi_heatmap_dim_overlay", None))
        dialog.deleteLater()
        parent.deleteLater()



