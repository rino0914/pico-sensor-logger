import network
import const

try:
    import ujson as json
except ImportError:
    import json


def start_access_point(ssid, password, led=None):
    ap = network.WLAN(network.AP_IF)
    ap.config(ssid=ssid, password=password, pm=const.WIFI_POWER_SAVE_DISABLED)
    ap.active(True)

    if not ap.active():
        raise RuntimeError("Failed to start access point")

    if led:
        led.on()

    print("Access point started")
    print("IP address:", ap.ifconfig()[0])
    print('AP Mode Is Active, You can Now Connect')
    print('WiFi Name: ', ssid)

    return ap


def load_config(path="config.json"):
    try:
        with open(path, "r") as config_file:
            config = json.load(config_file)
    except OSError:
        raise RuntimeError("Cannot read config file: %s" % path)
    except ValueError:
        raise RuntimeError("Invalid JSON in config file: %s" % path)

    if not isinstance(config, dict):
        raise RuntimeError("Config root must be a JSON object")

    return config


def get_required(config, *keys):
    value = config

    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise RuntimeError(
                "Missing config value: %s" % ".".join(keys)
            )
        value = value[key]

    return value
