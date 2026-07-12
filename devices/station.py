import network
from time import sleep, ticks_diff, ticks_ms


WIFI_POWER_SAVE_DISABLED = 0xA11140


class Station:
    def __init__(self, ssid, password, connect_timeout_seconds):
        self.ssid = ssid
        self.password = password
        self.connect_timeout_ms = int(connect_timeout_seconds * 1000)
        self.station = network.WLAN(network.STA_IF)

    def start(self, led=None):
        self.station.active(True)
        self.station.config(pm=WIFI_POWER_SAVE_DISABLED)

        try:
            if not self.station.isconnected():
                print("Connecting to Wi-Fi:", self.ssid)
                self.station.connect(self.ssid, self.password)
                self._wait_until_connected()
        except Exception:
            self.stop(led)
            raise

        if led:
            led.on()

        ip_address = self.station.ifconfig()[0]
        print("Station mode connected")
        print("WiFi Name:", self.ssid)
        print("IP address:", ip_address)
        return ip_address

    def _wait_until_connected(self):
        started_at = ticks_ms()

        while not self.station.isconnected():
            status = self.station.status()
            if status < 0:
                raise RuntimeError(
                    "Failed to connect to Wi-Fi: status=%s" % status
                )

            if ticks_diff(ticks_ms(), started_at) >= self.connect_timeout_ms:
                raise RuntimeError("Timed out while connecting to Wi-Fi")

            sleep(0.2)

    def stop(self, led=None):
        if self.station.active():
            if self.station.isconnected():
                self.station.disconnect()
            self.station.active(False)

        if led:
            led.off()

        print("Station mode stopped")

    def get_network_info(self):
        return {
            "mode": "station",
            "ssid": self.ssid,
            "ip_address": self.station.ifconfig()[0],
            "connected": self.station.isconnected(),
        }
