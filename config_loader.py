try:
    import ujson as json
except ImportError:
    import json

# @brief Json 파일에서 설정을 로드
# @param path 설정파일이름
# @return config 설정 객체
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

# @brief 설정 객체에서 Key와 맵핑되는 설정정보 반환
# @param config 설정
# @param keys 키 값
# @return value key에서 파싱한 값
def get_config_value(config, *keys):
    value = config

    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise RuntimeError(
                "Missing config value: %s" % ".".join(keys)
            )
        value = value[key]

    return value
