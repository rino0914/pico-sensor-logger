try:
    import ujson as json
except ImportError:
    import json


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
