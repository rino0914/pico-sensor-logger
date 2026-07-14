try:
    from time import ticks_diff, ticks_ms
except ImportError:
    from time import monotonic

    def ticks_ms():
        return int(monotonic() * 1000)

    def ticks_diff(current, previous):
        return current - previous

from machine import Pin
from devices.scd40 import SCD40Error


SCD40_POLL_INTERVAL_MS = 500
SENSOR_STATUS_LED_PIN = 1


class SCD40Thread:
    """Cooperative SCD40 poller retained under the old public class name.

    No RP2040 second-core thread is used. ``process_pending`` is called by the
    application main loop, which makes MicroPython soft reboot safe.
    """

    def __init__(self, sensor, connector, time_service, status_led=None):
        self.sensor = sensor
        self.connector = connector
        self.time_service = time_service
        self.status_led = status_led or Pin(SENSOR_STATUS_LED_PIN, Pin.OUT)
        self._running = False
        self._measurement_started = False
        self._last_poll_ms = None
        self._previous_wait_state = None

    def start(self):
        if self._running:
            raise RuntimeError("SCD40 poller is already running")
        self._running = True
        self._log_wait_state()

    def stop(self):
        if not self._running and not self._measurement_started:
            return

        self._running = False
        if self._measurement_started:
            try:
                self.sensor.stop_periodic_measurement()
            except (OSError, RuntimeError, SCD40Error) as error:
                print("SCD40 stop failed:", error)
        self.status_led.off()
        self._measurement_started = False
        self._last_poll_ms = None

    def is_running(self):
        return self._running

    def process_pending(self):
        if not self._running:
            return False

        time_ready = self.time_service.is_synchronized()
        sensing_enabled = self.connector.is_enabled()
        if not time_ready or not sensing_enabled:
            self._log_wait_state(time_ready, sensing_enabled)
            return False

        if not self._measurement_started:
            print("[SENSOR] Starting SCD40 periodic measurement.")
            try:
                self.sensor.restart_periodic_measurement()
            except (OSError, RuntimeError, SCD40Error) as error:
                print("SCD40 start failed:", error)
                return False
            self._measurement_started = True
            self._last_poll_ms = ticks_ms()
            self.status_led.on()
            print("[SENSOR] SCD40 periodic measurement started.")
            return True

        now = ticks_ms()
        if ticks_diff(now, self._last_poll_ms) < SCD40_POLL_INTERVAL_MS:
            return False
        self._last_poll_ms = now

        try:
            return self.poll_once() is not None
        except (OSError, RuntimeError, SCD40Error) as error:
            print("SCD40 measurement failed:", error)
            return False

    def poll_once(self):
        measurement = self.sensor.read_if_ready()
        if measurement is None:
            return None
        self._publish_measurement(measurement)
        return measurement

    def _publish_measurement(self, measurement):
        co2, temperature, humidity = measurement
        timestamp = self.time_service.now()
        self.connector.publish(timestamp, co2, humidity, temperature)
        print(
            "[SENSOR] SCD40 measurement: timestamp=%s, CO2=%s ppm, "
            "temperature=%.2f C, humidity=%.2f %%"
            % (timestamp, co2, temperature, humidity)
        )

    def _log_wait_state(self, time_ready=None, sensing_enabled=None):
        if time_ready is None:
            time_ready = self.time_service.is_synchronized()
        if sensing_enabled is None:
            sensing_enabled = self.connector.is_enabled()
        current_state = (time_ready, sensing_enabled)
        if current_state == self._previous_wait_state:
            return
        print(
            "[SENSOR] Waiting to start: time_synchronized=%s, "
            "sensing_enabled=%s"
            % current_state
        )
        self._previous_wait_state = current_state
