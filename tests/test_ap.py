import importlib
import sys
import unittest


class FakeWlan:
    def __init__(self):
        self.active_state = False
        self.config_values = {}
        self.stations = []
        self.reported_channel = None
        self.network_config = ("192.168.4.1", "255.255.255.0", "192.168.4.1", "8.8.8.8")

    def active(self, value=None):
        if value is not None:
            self.active_state = value
        return self.active_state

    def config(self, name=None, **values):
        if name is not None:
            if name == "mac":
                return bytes((0x02, 0x00, 0x00, 0x00, 0x00, 0x01))
            if name == "channel" and self.reported_channel is not None:
                return self.reported_channel
            return self.config_values[name]
        self.config_values.update(values)

    def status(self, name=None):
        if name == "stations":
            return self.stations
        return 0

    def ifconfig(self, value=None):
        if value is not None:
            self.network_config = value
        return self.network_config


class FakeNetwork:
    AP_IF = 1

    def __init__(self):
        self.ap = FakeWlan()

    def WLAN(self, interface):
        if interface != self.AP_IF:
            raise AssertionError("Expected AP interface")
        return self.ap


class AccessPointTest(unittest.TestCase):
    def setUp(self):
        self.network = FakeNetwork()
        sys.modules["network"] = self.network
        sys.modules.pop("devices.ap", None)
        self.ap_module = importlib.import_module("devices.ap")

    def tearDown(self):
        sys.modules.pop("devices.ap", None)
        sys.modules.pop("network", None)

    def test_configures_and_starts_open_access_point(self):
        network_config = (
            "192.168.4.1",
            "255.255.255.0",
            "192.168.4.1",
            "8.8.8.8",
        )
        access_point = self.ap_module.AccessPoint(
            "Pico_Science_01",
            network_config,
            channel=6,
        )

        self.assertEqual("Pico_Science_01", self.network.ap.config_values["ssid"])
        self.assertEqual(0, self.network.ap.config_values["security"])
        self.assertEqual(6, self.network.ap.config_values["channel"])
        self.assertNotIn("password", self.network.ap.config_values)
        self.assertNotIn("pm", self.network.ap.config_values)

        access_point.start()
        self.assertTrue(self.network.ap.active_state)
        self.assertEqual(network_config, self.network.ap.network_config)
        self.network.ap.stations = [(bytes((1, 2, 3, 4, 5, 6)),)]
        self.assertTrue(access_point._log_station_changes())
        self.assertFalse(access_point._log_station_changes())
        self.assertEqual({
            "mode": "ap",
            "ssid": "Pico_Science_01",
            "channel": 6,
            "ip_address": "192.168.4.1",
            "connected": True,
        }, access_point.get_network_info())

        access_point.stop()
        self.assertFalse(self.network.ap.active_state)

    def test_health_check_rejects_channel_mismatch(self):
        access_point = self.ap_module.AccessPoint("Pico_Science_01", channel=6)
        self.network.ap.active(True)
        self.network.ap.reported_channel = 11

        with self.assertRaisesRegex(RuntimeError, "AP channel mismatch"):
            access_point._validate_health()

    def test_runtime_check_rejects_inactive_access_point(self):
        access_point = self.ap_module.AccessPoint("Pico_Science_01")

        with self.assertRaisesRegex(RuntimeError, "became inactive"):
            access_point.process_pending()

    def test_enables_low_level_trace_when_requested(self):
        access_point = self.ap_module.AccessPoint(
            "Pico_Science_01",
            trace_enabled=True,
        )

        self.assertTrue(access_point._enable_trace())
        self.assertEqual(15, self.network.ap.config_values["trace"])


if __name__ == "__main__":
    unittest.main()
