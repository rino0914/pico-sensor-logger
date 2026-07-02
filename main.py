#y축이 좌우 동일한 경우 
from app import (
    SensingState,
    get_required,
    load_config,
    start_access_point,
)
from sensor_data import SensorHistory
from web_server import WebServer
import scd40
# Set up Wifi connection details

import rp2
import sys

from time import sleep
from machine import I2C, Pin, RTC
led_pico = Pin("LED", Pin.OUT)
import _thread
# create a global lock
file_lock = _thread.allocate_lock()
data_lock = _thread.allocate_lock()

#정지 대기 3초
for i in range(300): #전원 투입후 3초 이내에 BOOTSEL 누르면 main.py 정지
    sleep(0.01) 
    if rp2.bootsel_button():
        sys.exit("BOOTSEL pressed!")
led_pico.off()

csv_file_name = "data-SCD40-1"         #센서에 맞게 조정 
csv_file_name_ext = str(csv_file_name + ".csv")
csv_file_head = "time,CO2(ppm),temp(C),hum(percent)" #조정

period_sensing = 3.0

co2_history = SensorHistory("co2")
temperature_history = SensorHistory("temperature")
humidity_history = SensorHistory("humidity")
histories = (
    co2_history,
    temperature_history,
    humidity_history,
)

with open(csv_file_name_ext, "a"):
    pass

rtc = RTC()
rtc.datetime((2024, 6, 3, 1, 0, 0, 0, 0))


def is_sensing_enabled(sensing_state, lock):
    lock.acquire()
    try:
        return sensing_state.enabled
    finally:
        lock.release()


def store_measurement(histories, measurement, lock):
    lock.acquire()
    try:
        for history, value in zip(histories, measurement):
            history.add(value)
    finally:
        lock.release()


def append_measurement_to_csv(
    csv_path,
    rtc,
    measurement,
    lock,
):
    timestamp = rtc.datetime()
    time_string = "%02d:%02d:%02d" % timestamp[4:7]

    lock.acquire()
    try:
        with open(csv_path, "a") as csv_file:
            csv_file.write(
                "%s,%s,%s,%s\n" % (
                    time_string,
                    measurement[0],
                    measurement[1],
                    measurement[2],
                )
            )
    finally:
        lock.release()


def run_measurement_loop(
    sensor,
    histories,
    sensing_state,
    rtc,
    status_led,
    data_lock,
    file_lock,
    csv_path,
    interval,
):
    while True:
        status_led.off()

        try:
            if is_sensing_enabled(sensing_state, data_lock):
                measurement = sensor.read_if_ready()
                if measurement is not None:
                    store_measurement(
                        histories,
                        measurement,
                        data_lock,
                    )
                    append_measurement_to_csv(
                        csv_path,
                        rtc,
                        measurement,
                        file_lock,
                    )
        except (OSError, RuntimeError) as error:
            print("Measurement failed:", error)
        finally:
            status_led.on()
            sleep(interval)


if __name__ == "__main__":
    
    config = load_config()
    ssid = get_required(config, "wifi", "ssid")
    password = get_required(config, "wifi", "password")

    ap = start_access_point(ssid, password, led_pico)
       
    sensing_state = SensingState()
    web_server = WebServer(
        histories=histories,
        sensing_state=sensing_state,
        rtc = rtc,
        led = led_pico,
        file_lock = file_lock,
        data_lock = data_lock,
        csv_file_name = csv_file_name,
        csv_header = csv_file_head,
    )
    web_server.start()

    i2c_scd40 = I2C(
        scd40.I2C_BUS_ID,
        scl=Pin(scd40.SCD40_SCL_PIN),
        sda=Pin(scd40.SCD40_SDA_PIN),
        freq=scd40.I2C_FREQUENCY,
    )
    print("i2c_0 scan result:", i2c_scd40.scan())
    scd40_sensor = scd40.SCD40(i2c_scd40)
    scd40_sensor.restart_periodic_measurement()

    #센서 정보 수집 시작
    led_sensor = Pin(scd40.SENSOR_STATUS_LED_PIN, Pin.OUT)
    led_sensor.on()

    run_measurement_loop(
        sensor=scd40_sensor,
        histories=histories,
        sensing_state=sensing_state,
        rtc=rtc,
        status_led=led_sensor,
        data_lock=data_lock,
        file_lock=file_lock,
        csv_path=csv_file_name_ext,
        interval=period_sensing,
    )
