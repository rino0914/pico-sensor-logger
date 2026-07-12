import unittest

from config_loader import AppConfig


def create_config(wifi):
    return {
        "wifi": wifi,
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
        self.assertIsNone(config.wifi_connect_timeout_seconds)

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
