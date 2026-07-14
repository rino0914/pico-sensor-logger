"""Robo Pico Board Grove port pin definitions."""

# GPIO pairs from the ROBO-PICO datasheet, Table 1 (Grove Ports).
# Each tuple follows the GPIO order printed in the datasheet.
GROVE_PORT_1_PINS = (0, 1)
GROVE_PORT_2_PINS = (2, 3)
GROVE_PORT_3_PINS = (4, 5)
GROVE_PORT_4_PINS = (16, 17)
GROVE_PORT_5_PINS = (6, 26)
GROVE_PORT_6_PINS = (26, 27)
GROVE_PORT_7_PINS = (7, 28)

GROVE_PORTS = {
    1: {"pins": GROVE_PORT_1_PINS, "i2c": True, "i2c_bus": 0},
    2: {"pins": GROVE_PORT_2_PINS, "i2c": True, "i2c_bus": 1},
    3: {"pins": GROVE_PORT_3_PINS, "i2c": True, "i2c_bus": 0},
    4: {"pins": GROVE_PORT_4_PINS, "i2c": True, "i2c_bus": 0},
    5: {"pins": GROVE_PORT_5_PINS, "i2c": False, "i2c_bus": None},
    6: {"pins": GROVE_PORT_6_PINS, "i2c": True, "i2c_bus": 1},
    7: {"pins": GROVE_PORT_7_PINS, "i2c": False, "i2c_bus": None},
}

I2C_GROVE_PORTS = tuple(
    port_number
    for port_number in sorted(GROVE_PORTS.keys())
    if GROVE_PORTS[port_number]["i2c"]
)

# The Maker/QWIIC connector shares GP2/GP3 with Grove port 2.
DEFAULT_GROVE_PORT = 2


def normalize_grove_port(value, path="sensor.grove_port"):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer" % path)
    if value not in GROVE_PORTS:
        raise ValueError(
            "%s must be one of: %s"
            % (path, tuple(sorted(GROVE_PORTS.keys())))
        )
    return value


def normalize_i2c_grove_port(value, path="sensor.grove_port"):
    port_number = normalize_grove_port(value, path)
    if not GROVE_PORTS[port_number]["i2c"]:
        raise ValueError(
            "%s must support I2C; available ports: %s"
            % (path, I2C_GROVE_PORTS)
        )
    return port_number


def grove_port_i2c_candidates(port_number):
    """Return both possible (SCL, SDA) orders for a Grove signal pair."""
    port_number = normalize_i2c_grove_port(port_number)
    first_pin, second_pin = GROVE_PORTS[port_number]["pins"]
    return (
        (first_pin, second_pin),
        (second_pin, first_pin),
    )
