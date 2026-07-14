import network

try:
    from time import sleep_ms, ticks_diff, ticks_ms
except ImportError:
    from time import monotonic, sleep

    def sleep_ms(milliseconds):
        sleep(milliseconds / 1000.0)

    def ticks_ms():
        return int(monotonic() * 1000)

    def ticks_diff(current, previous):
        return current - previous

OPEN_SECURITY = 0
AP_RESET_DELAY_MS = 1000
AP_DHCP_READY_DELAY_MS = 1000
DEFAULT_AP_CHANNEL = 1
AP_STATUS_POLL_INTERVAL_MS = 2000
CYW43_TRACE_ALL = 15


class AccessPoint:
    def __init__(
        self,
        ssid,
        network_ifconfig=None,
        channel=DEFAULT_AP_CHANNEL,
        trace_enabled=False,
    ):
        self.ssid = ssid
        self.network_ifconfig = network_ifconfig
        self.channel = channel
        self.trace_enabled = trace_enabled
        self.ap = network.WLAN(network.AP_IF)
        self._last_status_poll_ms = None
        self._last_stations = None
        self._station_status_supported = True
        self._configure()

    def _configure(self):
        # Configure AP parameters before activation. Leave power management at
        # the firmware default; runtime PM changes belong after active(True).
        self.ap.config(
            ssid=self.ssid,
            security=OPEN_SECURITY,
            channel=self.channel,
        )

    def start(self, led=None):
        # A MicroPython soft reboot may leave CYW43 AP/DHCP state active.
        # Force a full interface restart so clients can associate again.
        self.ap.active(False)
        sleep_ms(AP_RESET_DELAY_MS)
        self._configure()
        self.ap.active(True)

        if not self.ap.active():
            raise RuntimeError("Failed to start access point")

        self._enable_trace()

        if self.network_ifconfig is not None:
            self.ap.ifconfig(self.network_ifconfig)

        # Give the CYW43 interface and lwIP DHCP server time to settle before
        # the application starts accepting HTTP traffic.
        sleep_ms(AP_DHCP_READY_DELAY_MS)

        self._validate_health()

        if led:
            led.on()

        print("AP ifconfig:", self.ap.ifconfig())
        print("IP address:", self.ap.ifconfig()[0])
        print("AP Mode Is Active, You can Now Connect")
        print("WiFi Name:", self.ssid)
        print("WiFi channel (requested):", self.channel)
        print("WiFi channel (active):", self._read_config("channel"))
        print("AP MAC address:", self._format_mac(self._read_config("mac")))
        print("Security: open")
        print("[INFO] AP health check passed.")
        print("Access point started")
        self._log_station_changes(force=True)

    def _enable_trace(self):
        if not self.trace_enabled:
            return False

        try:
            self.ap.config(trace=CYW43_TRACE_ALL)
        except Exception as error:
            print("[WARN] Low-level Wi-Fi tracing is unavailable:", error)
            return False

        print("[WARN] Low-level Wi-Fi tracing is enabled.")
        print("[WARN] Trace output may be verbose and contain network data.")
        return True

    def process_pending(self):
        if not self.ap.active():
            raise RuntimeError("Access point became inactive")

        now = ticks_ms()
        if (
            self._last_status_poll_ms is not None
            and ticks_diff(now, self._last_status_poll_ms)
            < AP_STATUS_POLL_INTERVAL_MS
        ):
            return False

        self._last_status_poll_ms = now
        self._validate_health()
        if not self._station_status_supported:
            return False
        return self._log_station_changes()

    def _validate_health(self):
        if not self.ap.active():
            raise RuntimeError("Access point is inactive")

        try:
            active_channel = self.ap.config("channel")
        except Exception as error:
            raise RuntimeError("Failed to read active AP channel: %s" % error)
        if active_channel != self.channel:
            raise RuntimeError(
                "AP channel mismatch: requested=%s, active=%s"
                % (self.channel, active_channel)
            )

        actual_ifconfig = self.ap.ifconfig()
        if self.network_ifconfig is not None:
            if tuple(actual_ifconfig) != tuple(self.network_ifconfig):
                raise RuntimeError(
                    "AP network configuration mismatch: expected=%s, actual=%s"
                    % (self.network_ifconfig, actual_ifconfig)
                )
        elif not actual_ifconfig or actual_ifconfig[0] == "0.0.0.0":
            raise RuntimeError("Access point has no IPv4 address")

        try:
            mac = self.ap.config("mac")
        except Exception as error:
            raise RuntimeError("Failed to read AP MAC address: %s" % error)
        if (
            not isinstance(mac, (bytes, bytearray))
            or len(mac) != 6
            or mac == bytes(6)
            or mac == bytes((0xFF,) * 6)
        ):
            raise RuntimeError("Invalid AP MAC address: %s" % repr(mac))

        return True

    def _log_station_changes(self, force=False):
        if not self._station_status_supported:
            return False

        try:
            stations = self.ap.status("stations")
        except Exception as error:
            self._station_status_supported = False
            print("[WARN] AP station status is unavailable:", error)
            return False

        snapshot = repr(stations)
        if not force and snapshot == self._last_stations:
            return False

        self._last_stations = snapshot
        print("[DEBUG] AP connected stations (%d):" % len(stations), stations)
        return True

    def _read_config(self, name):
        try:
            return self.ap.config(name)
        except Exception as error:
            return "unavailable (%s)" % error

    @staticmethod
    def _format_mac(value):
        if not isinstance(value, (bytes, bytearray)):
            return value
        return ":".join("%02x" % byte for byte in value)

    def stop(self, led=None):
        self.ap.active(False)
        self._last_status_poll_ms = None
        self._last_stations = None

        if led:
            led.off()

        print("Access point stopped")

    def get_network_info(self):
        return {
            "mode": "ap",
            "ssid": self.ssid,
            "channel": self.channel,
            "ip_address": self.ap.ifconfig()[0],
            "connected": self.ap.active(),
        }
