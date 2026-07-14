try:
    import ujson as json
except ImportError:
    import json

from devices.grove import DEFAULT_GROVE_PORT, normalize_i2c_grove_port
from devices.device_id import DEFAULT_SUFFIX_LENGTH

EXPECTED_CSV_FIELD_NAMES = ["timestamp", "CO2(ppm)", "temperature(°C)", "humidity(%)"]

WIFI_MODE_AP = "ap"
WIFI_MODE_STATION = "station"
WIFI_MODES = (WIFI_MODE_AP, WIFI_MODE_STATION)
MAX_WIFI_SSID_LENGTH = 32
MIN_WIFI_PASSWORD_LENGTH = 8
MAX_WIFI_PASSWORD_LENGTH = 64
DEFAULT_WIFI_CONNECT_TIMEOUT_SECONDS = 15
MAX_WIFI_CONNECT_TIMEOUT_SECONDS = 120
DEFAULT_WIFI_AP_CHANNEL = 1
MIN_WIFI_AP_CHANNEL = 1
MAX_WIFI_AP_CHANNEL = 11

class AppConfig:
    def __init__(
        self,
        wifi_mode,
        wifi_ssid,
        wifi_password,
        wifi_ifconfig,
        wifi_channel,
        wifi_trace_enabled,
        wifi_connect_timeout_seconds,
        sensor_grove_port,
        logfile_filename,
        logfile_field_names,
    ):
        self.wifi_mode = wifi_mode
        self.wifi_ssid = wifi_ssid
        self.wifi_password = wifi_password
        self.wifi_ifconfig = wifi_ifconfig
        self.wifi_channel = wifi_channel
        self.wifi_trace_enabled = wifi_trace_enabled
        self.wifi_connect_timeout_seconds = wifi_connect_timeout_seconds
        self.sensor_grove_port = sensor_grove_port
        self.logfile_filename = logfile_filename
        self.logfile_field_names = logfile_field_names
        
    @property
    def logfile_header(self):
        return ",".join(self.logfile_field_names)
    
    @classmethod
    def from_dict(cls, config):
        values = cls._require_mapping(config,"config")
        wifi_values = cls._require_mapping(values.get("wifi"), "wifi")
        logfile_values = cls._require_mapping(values.get("logfile"), "logfile")
        sensor_values = cls._require_mapping(
            values.get("sensor", {}),
            "sensor",
        )
        diagnostics_values = cls._require_mapping(
            values.get("diagnostics", {}),
            "diagnostics",
        )
        wifi_trace_enabled = cls._normalize_boolean(
            diagnostics_values.get("wifi_trace", False),
            "diagnostics.wifi_trace",
        )
        wifi_mode = cls._normalize_wifi_mode(wifi_values.get("mode"))
        wifi_profile_path = "wifi.%s" % wifi_mode
        wifi_profile = cls._require_mapping(
            wifi_values.get(wifi_mode),
            wifi_profile_path,
        )
        wifi_ssid = cls._normalize_ssid(
            wifi_profile.get("ssid", ""),
            "%s.ssid" % wifi_profile_path,
        )

        if wifi_mode == WIFI_MODE_AP:
            if len(wifi_ssid) + DEFAULT_SUFFIX_LENGTH > MAX_WIFI_SSID_LENGTH:
                raise ValueError(
                    "%s.ssid must not exceed %d characters because a %d-character "
                    "device suffix is appended"
                    % (
                        wifi_profile_path,
                        MAX_WIFI_SSID_LENGTH - DEFAULT_SUFFIX_LENGTH,
                        DEFAULT_SUFFIX_LENGTH,
                    )
                )
            wifi_password = None
            wifi_channel = cls._normalize_wifi_channel(
                wifi_profile.get("channel", DEFAULT_WIFI_AP_CHANNEL),
                "%s.channel" % wifi_profile_path,
            )
            wifi_ifconfig = cls._normalize_network_ifconfig(
                wifi_profile.get("network"),
                "%s.network" % wifi_profile_path,
            )
            wifi_connect_timeout_seconds = None
        else:
            wifi_password = cls._normalize_wifi_password(
                wifi_profile.get("password"),
                "%s.password" % wifi_profile_path,
            )
            wifi_ifconfig = None
            wifi_channel = None
            wifi_connect_timeout_seconds = cls._normalize_connect_timeout(
                wifi_profile.get(
                    "connect_timeout_seconds",
                    DEFAULT_WIFI_CONNECT_TIMEOUT_SECONDS,
                ),
                "%s.connect_timeout_seconds" % wifi_profile_path,
            )

        return cls(
            wifi_mode=wifi_mode,
            wifi_ssid=wifi_ssid,
            wifi_password=wifi_password,
            wifi_ifconfig=wifi_ifconfig,
            wifi_channel=wifi_channel,
            wifi_trace_enabled=wifi_trace_enabled,
            wifi_connect_timeout_seconds=wifi_connect_timeout_seconds,
            sensor_grove_port=normalize_i2c_grove_port(
                sensor_values.get("grove_port", DEFAULT_GROVE_PORT),
                "sensor.grove_port",
            ),
            logfile_filename=cls._require_string(logfile_values.get("filename"), "logfile.filename"),
            logfile_field_names=cls._normalize_field_names(
                logfile_values.get("field_names"),
                "logfile.field_names",
            ),
        )
    @classmethod
    def load(cls, path="config.json"):
        try:
            with open(path, "r") as f:
                config = json.load(f)
            return cls.from_dict(config)
        except OSError as e:
            print("[ERROR] Failed to open configuration file:", e)
            raise
        except ValueError as e:
            print("[ERROR] Invalid configuration data:", e)
            raise
        except Exception as e:
            print("[ERROR] Failed to load configuration:", e)
            raise
        
        
    @staticmethod
    def _require_mapping(value, name):
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be a mapping (dict)")
        return value

    @staticmethod
    def _require_string(value, name):
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string")
        return value

    @staticmethod
    def _require_list(value, name, expected_items):
        if not isinstance(value, list):
            raise ValueError(f"{name} must be a list")
        if not all(item in expected_items for item in value):
            raise ValueError(f"{name} must only contain the following items: {expected_items}")
        return value
    
    @classmethod
    def _normalize_network_ifconfig(cls, network_config, path):
        values = cls._require_mapping(network_config, path)
        return (
            cls._normalize_ip_address(values.get("ip"), f"{path}.ip"),
            cls._normalize_netmask(values.get("netmask"), f"{path}.netmask"),
            cls._normalize_ip_address(values.get("gateway"), f"{path}.gateway"),
            cls._normalize_ip_address(values.get("dns"), f"{path}.dns")
        )
    @classmethod
    def _normalize_field_names(cls, field_names, path):
        if not isinstance(field_names, list):
            raise ValueError(f"{path} must be a list")
        for index, field_name in enumerate(field_names):
            cls._require_string(field_name, f"{path}[{index}]")
        if field_names != EXPECTED_CSV_FIELD_NAMES:
            raise ValueError(
                f"{path} must contain the following items in order: "
                f"{EXPECTED_CSV_FIELD_NAMES}"
            )
        return tuple(field_names)

    @classmethod
    def _normalize_ip_address(cls, value, path):
        cls._require_string(value, path)
        parts = value.split(".")
        if len(parts) != 4 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            raise ValueError(f"{path} must be a valid IPv4 address")
        return value
    
    @classmethod
    def _normalize_netmask(cls, value, path):
        cls._require_string(value, path)
        parts = value.split(".")
        if len(parts) != 4 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            raise ValueError(f"{path} must be a valid IPv4 netmask")
        return value

    @classmethod
    def _normalize_ssid(cls, value, path):
        cls._require_string(value, path)
        if not value:
            raise ValueError("%s must not be empty" % path)
        if len(value) > MAX_WIFI_SSID_LENGTH:
            raise ValueError(
                "%s must not exceed %d characters"
                % (path, MAX_WIFI_SSID_LENGTH)
            )
        return value

    @classmethod
    def _normalize_wifi_mode(cls, value):
        cls._require_string(value, "wifi.mode")
        if value not in WIFI_MODES:
            raise ValueError(f"wifi.mode must be one of: {WIFI_MODES}")
        return value

    @classmethod
    def _normalize_wifi_password(cls, value, path):
        cls._require_string(value, path)
        if not MIN_WIFI_PASSWORD_LENGTH <= len(value) <= MAX_WIFI_PASSWORD_LENGTH:
            raise ValueError(
                "%s must be between %d and %d characters"
                % (path, MIN_WIFI_PASSWORD_LENGTH, MAX_WIFI_PASSWORD_LENGTH)
            )
        return value

    @classmethod
    def _normalize_connect_timeout(cls, value, path):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a number" % path)
        if not 0 < value <= MAX_WIFI_CONNECT_TIMEOUT_SECONDS:
            raise ValueError(
                "%s must be greater than 0 and at most %d"
                % (path, MAX_WIFI_CONNECT_TIMEOUT_SECONDS)
            )
        return value

    @classmethod
    def _normalize_wifi_channel(cls, value, path):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("%s must be an integer" % path)
        if not MIN_WIFI_AP_CHANNEL <= value <= MAX_WIFI_AP_CHANNEL:
            raise ValueError(
                "%s must be between %d and %d"
                % (path, MIN_WIFI_AP_CHANNEL, MAX_WIFI_AP_CHANNEL)
            )
        return value

    @classmethod
    def _normalize_boolean(cls, value, path):
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean" % path)
        return value
