import network

try:
    from time import sleep_ms
except ImportError:
    from time import sleep

    def sleep_ms(milliseconds):
        sleep(milliseconds / 1000.0)

WIFI_POWER_SAVE_DISABLED = 0xA11140
OPEN_SECURITY = 0
AP_RESET_DELAY_MS = 100
AP_DHCP_READY_DELAY_MS = 250


class AccessPoint:
    def __init__(self, ssid, network_ifconfig=None):
        self.ssid = ssid
        self.network_ifconfig = network_ifconfig
        self.ap = network.WLAN(network.AP_IF)
        self._configure()

    def _configure(self):
        self.ap.config(
            ssid=self.ssid,
            security=OPEN_SECURITY,
            pm=WIFI_POWER_SAVE_DISABLED,
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

        if self.network_ifconfig is not None:
            self.ap.ifconfig(self.network_ifconfig)

        # Give the CYW43 interface and lwIP DHCP server time to settle before
        # the application starts accepting HTTP traffic.
        sleep_ms(AP_DHCP_READY_DELAY_MS)

        if led:
            led.on()

        print("AP ifconfig:", self.ap.ifconfig())
        print("IP address:", self.ap.ifconfig()[0])
        print("AP Mode Is Active, You can Now Connect")
        print("WiFi Name:", self.ssid)
        print("Security: open")
        print("Access point started")

    def stop(self, led=None):
        self.ap.active(False)

        if led:
            led.off()

        print("Access point stopped")

    def get_network_info(self):
        return {
            "mode": "ap",
            "ssid": self.ssid,
            "ip_address": self.ap.ifconfig()[0],
            "connected": self.ap.active(),
        }
