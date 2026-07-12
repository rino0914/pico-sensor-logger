import importlib
import sys
import time as real_time
import unittest


class FakeStationInterface:
    def __init__(self):
        self.active_state = False
        self.connected = False
        self.status_value = 0
        self.config_values = {}
        self.connect_args = None

    def active(self, value=None):
        if value is not None:
            self.active_state = value
        return self.active_state

    def config(self, **values):
        self.config_values.update(values)

    def connect(self, ssid, password):
        self.connect_args = (ssid, password)

    def disconnect(self):
        self.connected = False

    def isconnected(self):
        return self.connected

    def status(self):
        return self.status_value

    def ifconfig(self):
        return ("192.168.0.37", "255.255.255.0", "192.168.0.1", "192.168.0.1")


class FakeNetwork:
    STA_IF = 0

    def __init__(self):
        self.station = FakeStationInterface()

    def WLAN(self, interface):
        if interface != self.STA_IF:
            raise AssertionError("Expected station interface")
        return self.station


class FakeTime:
    def __init__(self, station):
        self.elapsed_ms = 0
        self.station = station
        self.connect_on_sleep = False

    def ticks_ms(self):
        return self.elapsed_ms

    @staticmethod
    def ticks_diff(current, previous):
        return current - previous

    def sleep(self, seconds):
        self.elapsed_ms += int(seconds * 1000)
        if self.connect_on_sleep:
            self.station.connected = True


class StationTest(unittest.TestCase):
    def setUp(self):
        self.network = FakeNetwork()
        self.time = FakeTime(self.network.station)
        sys.modules["network"] = self.network
        sys.modules["time"] = self.time
        sys.modules.pop("devices.station", None)
        self.station_module = importlib.import_module("devices.station")
        sys.modules["time"] = real_time

    def tearDown(self):
        sys.modules.pop("devices.station", None)
        sys.modules.pop("network", None)
        sys.modules["time"] = real_time

    def test_connects_to_wifi_and_returns_dhcp_address(self):
        self.time.connect_on_sleep = True
        station = self.station_module.Station("CLASSROOM_WIFI", "wifi-password", 15)

        ip_address = station.start()

        self.assertEqual(("CLASSROOM_WIFI", "wifi-password"), self.network.station.connect_args)
        self.assertEqual("192.168.0.37", ip_address)
        self.assertTrue(self.network.station.active_state)
        self.assertEqual({
            "mode": "station",
            "ssid": "CLASSROOM_WIFI",
            "ip_address": "192.168.0.37",
            "connected": True,
        }, station.get_network_info())

        station.stop()
        self.assertFalse(self.network.station.active_state)

    def test_raises_when_connection_fails(self):
        self.network.station.status_value = -2
        station = self.station_module.Station("CLASSROOM_WIFI", "wifi-password", 15)

        with self.assertRaisesRegex(RuntimeError, "status=-2"):
            station.start()

        self.assertFalse(self.network.station.active_state)

    def test_raises_when_connection_times_out(self):
        station = self.station_module.Station("CLASSROOM_WIFI", "wifi-password", 0.4)

        with self.assertRaisesRegex(RuntimeError, "Timed out"):
            station.start()

        self.assertFalse(self.network.station.active_state)


if __name__ == "__main__":
    unittest.main()
