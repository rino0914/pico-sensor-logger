import unittest

from config_loader import AppConfig


def create_config(wifi):
    return {
        "wifi": wifi,
        "sensor": {
            "grove_port": 2,
        },
        "logfile": {
            "filename": "measurements.csv",
            "field_names": [
                "timestamp",
                "CO2(ppm)",
                "temperature(°C)",
                "humidity(%)",
            ],
        },
    }


class AppConfigTest(unittest.TestCase):
    def test_loads_access_point_mode(self):
        config = AppConfig.from_dict(create_config({
            "mode": "ap",
            "ap": {
                "ssid": "Pico_Science_01",
                "channel": 6,
                "network": {
                    "ip": "192.168.4.1",
                    "netmask": "255.255.255.0",
                    "gateway": "192.168.4.1",
                    "dns": "8.8.8.8",
                },
            },
            "station": {
                "ssid": "",
                "password": "",
            },
        }))

        self.assertEqual("ap", config.wifi_mode)
        self.assertIsNone(config.wifi_password)
        self.assertEqual("192.168.4.1", config.wifi_ifconfig[0])
        self.assertEqual(6, config.wifi_channel)
        self.assertFalse(config.wifi_trace_enabled)
        self.assertIsNone(config.wifi_connect_timeout_seconds)
        self.assertEqual(2, config.sensor_grove_port)

    def test_uses_default_access_point_channel_when_missing(self):
        config = AppConfig.from_dict(create_config({
            "mode": "ap",
            "ap": {
                "ssid": "Pico_Science_01",
                "network": {
                    "ip": "192.168.4.1",
                    "netmask": "255.255.255.0",
                    "gateway": "192.168.4.1",
                    "dns": "8.8.8.8",
                },
            },
        }))

        self.assertEqual(1, config.wifi_channel)

    def test_rejects_invalid_access_point_channel(self):
        values = create_config({
            "mode": "ap",
            "ap": {
                "ssid": "Pico_Science_01",
                "channel": 12,
                "network": {
                    "ip": "192.168.4.1",
                    "netmask": "255.255.255.0",
                    "gateway": "192.168.4.1",
                    "dns": "8.8.8.8",
                },
            },
        })

        with self.assertRaisesRegex(ValueError, "wifi.ap.channel"):
            AppConfig.from_dict(values)

    def test_loads_wifi_trace_diagnostic_flag(self):
        values = create_config({
            "mode": "ap",
            "ap": {
                "ssid": "Pico_Science_01",
                "network": {
                    "ip": "192.168.4.1",
                    "netmask": "255.255.255.0",
                    "gateway": "192.168.4.1",
                    "dns": "8.8.8.8",
                },
            },
        })
        values["diagnostics"] = {"wifi_trace": True}

        config = AppConfig.from_dict(values)

        self.assertTrue(config.wifi_trace_enabled)

    def test_rejects_non_boolean_wifi_trace_flag(self):
        values = create_config({
            "mode": "ap",
            "ap": {
                "ssid": "Pico_Science_01",
                "network": {
                    "ip": "192.168.4.1",
                    "netmask": "255.255.255.0",
                    "gateway": "192.168.4.1",
                    "dns": "8.8.8.8",
                },
            },
        })
        values["diagnostics"] = {"wifi_trace": 1}

        with self.assertRaisesRegex(ValueError, "diagnostics.wifi_trace"):
            AppConfig.from_dict(values)

    def test_uses_default_grove_port_when_sensor_setting_is_missing(self):
        values = create_config({
            "mode": "ap",
            "ap": {
                "ssid": "Pico_Science_01",
                "channel": 6,
                "network": {
                    "ip": "192.168.4.1",
                    "netmask": "255.255.255.0",
                    "gateway": "192.168.4.1",
                    "dns": "8.8.8.8",
                },
            },
        })
        del values["sensor"]

        config = AppConfig.from_dict(values)

        self.assertEqual(2, config.sensor_grove_port)

    def test_rejects_unknown_grove_port(self):
        values = create_config({
            "mode": "ap",
            "ap": {
                "ssid": "Pico_Science_01",
                "network": {
                    "ip": "192.168.4.1",
                    "netmask": "255.255.255.0",
                    "gateway": "192.168.4.1",
                    "dns": "8.8.8.8",
                },
            },
        })
        values["sensor"]["grove_port"] = 99

        with self.assertRaisesRegex(ValueError, "sensor.grove_port"):
            AppConfig.from_dict(values)

    def test_accepts_another_defined_grove_port(self):
        values = create_config({
            "mode": "ap",
            "ap": {
                "ssid": "Pico_Science_01",
                "network": {
                    "ip": "192.168.4.1",
                    "netmask": "255.255.255.0",
                    "gateway": "192.168.4.1",
                    "dns": "8.8.8.8",
                },
            },
        })
        values["sensor"]["grove_port"] = 1

        config = AppConfig.from_dict(values)

        self.assertEqual(1, config.sensor_grove_port)

    def test_rejects_grove_port_without_i2c_pair(self):
        values = create_config({
            "mode": "ap",
            "ap": {
                "ssid": "Pico_Science_01",
                "network": {
                    "ip": "192.168.4.1",
                    "netmask": "255.255.255.0",
                    "gateway": "192.168.4.1",
                    "dns": "8.8.8.8",
                },
            },
        })
        values["sensor"]["grove_port"] = 7

        with self.assertRaisesRegex(ValueError, "must support I2C"):
            AppConfig.from_dict(values)

    def test_loads_station_mode(self):
        config = AppConfig.from_dict(create_config({
            "mode": "station",
            "ap": {
                "ssid": "",
            },
            "station": {
                "ssid": "CLASSROOM_WIFI",
                "password": "wifi-password",
                "connect_timeout_seconds": 20,
            },
        }))

        self.assertEqual("station", config.wifi_mode)
        self.assertEqual("CLASSROOM_WIFI", config.wifi_ssid)
        self.assertEqual("wifi-password", config.wifi_password)
        self.assertEqual(20, config.wifi_connect_timeout_seconds)
        self.assertIsNone(config.wifi_ifconfig)
        self.assertIsNone(config.wifi_channel)

    def test_station_mode_requires_password(self):
        with self.assertRaisesRegex(ValueError, "wifi.station.password"):
            AppConfig.from_dict(create_config({
                "mode": "station",
                "station": {
                    "ssid": "CLASSROOM_WIFI",
                },
            }))

    def test_rejects_unknown_wifi_mode(self):
        with self.assertRaisesRegex(ValueError, "wifi.mode"):
            AppConfig.from_dict(create_config({
                "mode": "unknown",
            }))

    def test_rejects_ap_ssid_prefix_that_has_no_room_for_suffix(self):
        values = create_config({
            "mode": "ap",
            "ap": {
                "ssid": "x" * 31,
                "network": {
                    "ip": "192.168.4.1",
                    "netmask": "255.255.255.0",
                    "gateway": "192.168.4.1",
                    "dns": "8.8.8.8",
                },
            },
        })

        with self.assertRaisesRegex(ValueError, "device suffix"):
            AppConfig.from_dict(values)

    def test_does_not_validate_inactive_station_profile(self):
        config = AppConfig.from_dict(create_config({
            "mode": "ap",
            "ap": {
                "ssid": "Pico_Science_01",
                "network": {
                    "ip": "192.168.4.1",
                    "netmask": "255.255.255.0",
                    "gateway": "192.168.4.1",
                    "dns": "8.8.8.8",
                },
            },
            "station": {
                "ssid": "",
                "password": "",
            },
        }))

        self.assertEqual("ap", config.wifi_mode)


if __name__ == "__main__":
    unittest.main()
