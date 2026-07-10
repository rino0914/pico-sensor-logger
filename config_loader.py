try:
    import ujson as json
except ImportError:
    import json

EXPECTED_CSV_FIELD_NAMES = ["timestamp", "CO2(ppm)", "temperature(°C)", "humidity(%)"]

MAX_WIFI_SSID_LENGTH = 32
MAX_WIFI_PASSWORD_LENGTH = 64
MIN_WIFI_PASSWORD_LENGTH = 8

class AppConfig:
    def __init__(self, wifi_ssid, wifi_password, logfile_filename, logfile_field_names):
        self.wifi_ssid = wifi_ssid
        self.wifi_password = wifi_password
        self.logfile_filename = logfile_filename
        self.logfile_field_names = logfile_field_names
        
    @property
    def logfile_header(self):
        return ".".join(self.logfile_field_names)
    
    @classmethod
    def from_dict(cls, config):
        values = cls._require_mapping(config,"config")
        wifi_values = cls._require_mapping(values.get("wifi"), "wifi")
        logfile_values = cls._require_mapping(values.get("logfile"), "logfile")
        wifi_network = wifi_values.get("network", "")
        return cls(
            wifi_ssid=cls._normalize_ssid(wifi_values.get("ssid", "")),
            wifi_password=cls._normalize_password(wifi_values.get("password", "")),
            wifi_ifconfig=(cls._get_wifi_ifconfig(wifi_network)),
            logfile_filename=cls._require_string(logfile_values.get("filename"), "logfile.filename"),
            logfile_field_names=cls._require_list(logfile_values.get("field_names"), "logfile.field_names", EXPECTED_CSV_FIELD_NAMES)
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
        except json.JSONDecodeError as e:
            print("[ERROR] Failed to parse JSON configuration:", e)
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
    
    @staticmethod
    def _normalize_network_ifconfig(cls, network_config, path):
        values = cls._require_mapping(network_config, path)
        return (
            cls._normalize_ip_address(values.get("ip"), f"{path}.ip"),
            cls._normalize_netmask(values.get("netmask"), f"{path}.netmask"),
            cls._normalize_ip_address(values.get("gateway"), f"{path}.gateway"),
            cls._normalize_ip_address(values.get("dns"), f"{path}.dns")
        )
    def _normalize_field_names(cls,fiedl_names, path):
        if not isinstance(fiedl_names, list):
            raise ValueError(f"{path} must be a list")
        normalized_field_names = []
        for index, field_name in enumerate(fiedl_names):
            cls._require_string(field_name, f"{path}[{index}]")
            
            normalized = tuple(normalized)
            if normalized != EXPECTED_CSV_FIELD_NAMES:
                raise ValueError(f"{path} must contain the following items in order: {EXPECTED_CSV_FIELD_NAMES}")
            return normalized

    @classmethod
    def _normalize_ip_address(cls, value, path):
        cls._require_string(value, path)
        parts = value.split(".")
        if len(parts) != 4 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            raise ValueError(f"{path} must be a valid IPv4 address")
        return value
    
    def _normalize_netmask(cls, value, path):
        cls._require_string(value, path)
        parts = value.split(".")
        if len(parts) != 4 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            raise ValueError(f"{path} must be a valid IPv4 netmask")
        return value

    @classmethod
    def _normalize_ssid(cls, value):
        cls._require_string(value, "wifi.ssid")
        if len(value) > MAX_WIFI_SSID_LENGTH:
            raise ValueError(f"wifi.ssid must not exceed {MAX_WIFI_SSID_LENGTH} characters")
        return value

    @classmethod
    def _normalize_wifi_password(cls, value):
        cls._require_string(value, "wifi.password")
        if len(value) < MIN_WIFI_PASSWORD_LENGTH or len(value) > MAX_WIFI_PASSWORD_LENGTH:
            raise ValueError(f"wifi.password must be between {MIN_WIFI_PASSWORD_LENGTH} and {MAX_WIFI_PASSWORD_LENGTH} characters")
        return value