import rp2
from machine import I2C, Pin, SoftI2C
from time import sleep

from config_loader import AppConfig
from core.data_connector import DataConnector
from core.ntp_client import NtpClient
from core.time_service import TimeService
from devices import grove, scd40, scd40_thread
from devices.wifi import create_wifi
from storage.filemanager import CsvWriter, FileHandler
from web.web_server import WebServer

APP_NAME = "PTL-LOGGER"
CONFIG_FILE = "config.json"
MAIN_LOOP_INTERVAL_SECONDS = 0.05
SENSOR_STOP_WAIT_INTERVAL_SECONDS = 0.05
SENSOR_STOP_TIMEOUT_SECONDS = 3.0

def create_status_led():
    status_led = Pin("LED", Pin.OUT)
    status_led.off()
    return status_led

def create_csv_writer(config, connector):
    file_handler = FileHandler(config.logfile_filename)
    return CsvWriter(connector, file_handler, config.logfile_header)

def create_i2c(scl_pin, sda_pin):
    if scd40.I2C_USE_SOFT:
        return SoftI2C(
            scl=Pin(scl_pin),
            sda=Pin(sda_pin),
            freq=scd40.I2C_FREQUENCY,
        )
    return I2C(
        scd40.I2C_BUS_ID,
        scl=Pin(scl_pin),
        sda=Pin(sda_pin),
        freq=scd40.I2C_FREQUENCY,
    )


def scan_i2c(i2c, scl_pin, sda_pin):
    scan_result = i2c.scan()
    print(
        "i2c scan result (scl=GP%s, sda=GP%s):" % (scl_pin, sda_pin),
        scan_result,
    )
    return scan_result


def create_sensor(config, connector, time_service):
    port_number = config.sensor_grove_port
    candidates = grove.grove_port_i2c_candidates(port_number)
    i2c = None

    for index, pins in enumerate(candidates):
        if index > 0 and not scd40.I2C_AUTO_SWAP_PINS:
            break
        scl_pin, sda_pin = pins
        candidate_i2c = create_i2c(scl_pin, sda_pin)
        scan_result = scan_i2c(candidate_i2c, scl_pin, sda_pin)
        if i2c is None:
            i2c = candidate_i2c
        if scan_result:
            i2c = candidate_i2c
            print(
                "[INFO] Using Grove port %s for SCD40: scl=GP%s, sda=GP%s"
                % (port_number, scl_pin, sda_pin)
            )
            break

    return scd40_thread.SCD40Thread(
        scd40.SCD40Device(i2c),
        connector,
        time_service
    )


class PicoSenscorLoggerApp:
    def __init__(self, config_path=CONFIG_FILE):
        self.config_path = config_path
        self.config = AppConfig.load(config_path)
        self.status_led = create_status_led()
        
        self.connector = DataConnector()
        self.time_service = TimeService()
        self.ntp_client = NtpClient()
        self.csv_writer = create_csv_writer(self.config, self.connector)
        self.wifi = create_wifi(self.config)
        self.web_server = WebServer(
            connector=self.connector,
            time_service=self.time_service,
            csv_writer=self.csv_writer,
            led=self.status_led,
            network_info_provider=self.wifi,
        )
        self.sensor = create_sensor(self.config, self.connector, self.time_service)
    
    def start(self):
        self.wifi.start(self.status_led)
        self._synchronize_station_time()
        self.web_server.start()
        self.sensor.start()

    def _synchronize_station_time(self):
        if self.config.wifi_mode != "station":
            return

        try:
            values = self.ntp_client.request_local_datetime()
            self.time_service.synchronize(*values)
            print("[INFO] Time synchronized from NTP:", self.ntp_client.server)
        except Exception as error:
            print("[WARN] Failed to synchronize time from NTP:", error)
        
    def stop(self):
        err = None
        err = self._run_stop_step("web_server", self.web_server.stop, err)
        err = self._run_stop_step("sensor thread", self.sensor.stop, err)
        err = self._run_stop_step("sensor shutdown await", self._await_sensor_stop, err)
        err = self._run_stop_step("sensing state", self.connector.stop_sensing, err)
        err = self._run_stop_step("csv writer flush", self.csv_writer.flush, err)
        err = self._run_stop_step("wifi", lambda: self.wifi.stop(self.status_led), err)
        if err:
            print("[ERROR] Failed to stop some components:", err)

    def _await_sensor_stop(self):
        max_checks = int(
            SENSOR_STOP_TIMEOUT_SECONDS
            / SENSOR_STOP_WAIT_INTERVAL_SECONDS
        )
        for _ in range(max_checks):
            if not self.sensor.is_running():
                return
            sleep(SENSOR_STOP_WAIT_INTERVAL_SECONDS)
        if self.sensor.is_running():
            raise RuntimeError("Timed out waiting for sensor thread to stop")
    
    def _run_stop_step(self, step_name, callback, prev_err):
        try:
            callback()
        except Exception as e:
            print(f"[ERROR] Failed to stop {step_name}:", e,
                  f" (previous error: {prev_err})" if prev_err is not None else "")
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
                    self.web_server.process_pending()
                    self.sensor.process_pending()
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
            self._stop_preserving_run_error(run_error=error)
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
