import importlib
import sys
import unittest


class FakeWlan:
    def __init__(self):
        self.active_state = False
        self.config_values = {}
        self.network_config = ("192.168.4.1", "255.255.255.0", "192.168.4.1", "8.8.8.8")

    def active(self, value=None):
        if value is not None:
            self.active_state = value
        return self.active_state

    def config(self, **values):
        self.config_values.update(values)

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
        access_point = self.ap_module.AccessPoint("Pico_Science_01", network_config)

        self.assertEqual("Pico_Science_01", self.network.ap.config_values["ssid"])
        self.assertEqual(0, self.network.ap.config_values["security"])
        self.assertNotIn("password", self.network.ap.config_values)

        access_point.start()
        self.assertTrue(self.network.ap.active_state)
        self.assertEqual(network_config, self.network.ap.network_config)

        access_point.stop()
        self.assertFalse(self.network.ap.active_state)


if __name__ == "__main__":
    unittest.main()
