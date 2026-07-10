import rp2
from time import sleep
from machine import I2C, Pin

from config_loader import loading
from core.data_connector import DataConnector
from core.time_service import TimeService
from devices import scd40
from devices import scd40
from device.ap import CsvWriter, FileHandler
from web.web_server import WebServer

APP_NAME = "PTL-LOGGER"
CONFIG_FILE = "config.json"
MAIN_LOOP_INTERVAL_SECONDS = 0.05

def create_status_led():
    status_led = Pin("LED", Pin.OUT)
    status_led.off()
    return status_led

def create_csv_writer(config, connector):
    file_handler = FileHandler(config.logfile_filename)
    return CsvWriter(connector, file_handler, config.logfile_header)

def create_sensor(connector, time_service):
    i2c = I2C(
        scd40.I2C_BUS_ID,
        scl  = Pin(scd40.SCD40_SCL_PIN),
        sda  = Pin(scd40.SCD40_SDA_PIN),
        freq = scd40.I2C_FREQUENCY,
    )
    print("i2c_0 scan result:", i2c.scan())

    return scd40_thread.SCD40Thread(
        scd40.SCD40Device(i2c),
        connector,
        time_service
    )


class PicoSenscorLoggerApp:
    def __init__(self, config_path=CONFIG_FILE):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.status_led = create_status_led()
        
        self.connector = DataConnector()
        self.time_service = TimeService()
        self.csv_writer = create_csv_writer(self.config, self.connector)
        self.ap = AccessPoint(
            self.config.wifi_ssid,
            self.config.wifi_password,
            self.config.wifi_ifconfig,
            )
        self.web_server = WebServer(
            connector=self.connector,
            time_service=self.time_service,
            csv_writer=self.csv_writer,
            led=self.status_led,
        )
        self.sensor = create_sensor(self.connector, self.time_service)
    
    def start(self):
        self.ap.start(self.status_led)
        self.web_server.start()
        self.sensor.start()
        
    def stop(self):
        err = None
        err = self._run_stop_step("web_server", self.web_server.stop, err)
        err = self._run_stop_step("sensor thread", self.sensor.stop, err)
        err = self._run_stop_step("sensor shutdown await", self._await_sensor_stop, err)
        err = self._run_stop_step("sensing state", self.connector.stop_sensing, err)
        err = self._run_stop_step("csv writer flush", self.csv_writer.flush, err)
        err = self._run_stop_step("access point", lambda: self.ap.stop(self.status_led), err)
        if err:
            print("[ERROR] Failed to stop some components:", err)
    
    def _run_stop_step(self, step_name, callback, prev_err):
        try:
            callback()
        except Exception as e:
            print(f"[ERROR] Failed to stop {step_name}:", e,
                  f" (previous error: {prev_err})" if prev_err is None else "")
            return e
        return prev_err
    
    def run(self):
        error = None
        print("[ALERT] %s Started." % APP_NAME)
        print("[INFO] Succeed to load configuration:", self.config_path)
        print("[INFO] Succeed to initialize LED status.")
        print("[INFO] Succeed to create application.")
        
        try:
            self.start()
            print("[INFO] Succeed to start application.")
            while True:
                try:
                    self._process_storage()

                    if rp2.bootsel_button():
                        print("[ALERT] BOOTSEL button detected!")
                        break
                    sleep(MAIN_LOOP_INTERVAL_SECONDS)
                except OSError as e:
                    print("[WARN] Failed to write CSV.", e)
                except Exception as e:
                    print("[ERROR] Unexpected error during main loop:", e)
                    error = e
                    raise
        finally:
            self.stop_preserving_run_error(run_error=error)
            print("[ALERT] %s Stopped." % APP_NAME)
            
    def _stop_preserving_run_error(self, run_error):
        try:
            self.stop()
        except Exception as stop_error:
            print("[ERROR] Failed to stop application:", stop_error,
                  f" (original run error: {run_error})" if run_error else "")
            if not run_error:
                raise stop_error
            else:
                raise run_error
    def _process_storage(self):
        try:
            self.csv_writer.process_one()
        except OSError as e:
            print("[WARN] Failed to write CSV.", e)

if __name__ == "__main__":
    app = PicoSenscorLoggerApp()
    app.run()