from devices.ap import AccessPoint
from devices.device_id import board_suffix
from devices.station import Station


def create_wifi(config):
    if config.wifi_mode == "ap":
        ssid = config.wifi_ssid + board_suffix()
        return AccessPoint(
            ssid,
            config.wifi_ifconfig,
            channel=config.wifi_channel,
            trace_enabled=config.wifi_trace_enabled,
        )

    if config.wifi_mode == "station":
        return Station(
            config.wifi_ssid,
            config.wifi_password,
            config.wifi_connect_timeout_seconds,
        )

    raise ValueError("Unsupported Wi-Fi mode: %s" % config.wifi_mode)
