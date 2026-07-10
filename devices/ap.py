import network

WIFI_POWER_SAVE_DISABLED = 0xA11140

class AccessPoint:
    def __init__(self, ssid, password, network_ifconfig=None):
        self.ssid = ssid
        self.password = password
        self.network_ifconfig = network_ifconfig
        self.ap = network.WLAN(network.AP_IF)
        self.ap.config(
            ssid     = self.ssid,
            password = self.password,
            pm       = WIFI_POWER_SAVE_DISABLED,
        )

    def start(self, led=None):
        self.ap.active(True)

        if not self.ap.active():
            raise RuntimeError("Failed to start access point")

        if self.network_ifconfig is not None:
            self.ap.ifconfig(self.network_ifconfig)

        if led:
            led.on()

        print("IP address:", self.ap.ifconfig()[0])
        print("AP Mode Is Active, You can Now Connect")
        print("WiFi Name:", self.ssid)
        print("Access point started")

    def stop(self, led=None):
        self.ap.active(False)

        if led:
            led.off()

        print("Access point stopped")
