#y축이 좌우 동일한 경우 
from app import (
    get_required,
    load_config,
    start_access_point,
)
from senser_data import SensorData
from web_server import WebServer
import scd40
# Set up Wifi connection details

import rp2
import sys

from time import sleep
from machine import I2C, Pin, RTC
led_pico = Pin("LED", Pin.OUT)
import const
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

data_1st = SensorData("data_1st")
data_2nd = SensorData("data_2nd")
data_3rd = SensorData("data_3rd")

data_1st.is_sensing = False
with open(csv_file_name_ext, "a"):
    pass

rtc = RTC()
rtc.datetime((2024, 6, 3, 1, 0, 0, 0, 0))


if __name__ == "__main__":
    
    config = load_config()
    ssid = get_required(config, "wifi", "ssid")
    password = get_required(config, "wifi", "password")

    ap = start_access_point(ssid, password, led_pico)
       
    web_server = WebServer(
        sensors=(data_1st, data_2nd, data_3rd),
        rtc=rtc,
        led=led_pico,
        file_lock=file_lock,
        data_lock=data_lock,
        csv_file_name=csv_file_name,
        csv_header=csv_file_head,
    )
    web_server.start()

    timestamp  = rtc.datetime()
    timestring = "%02d:%02d:%02d" % (timestamp[4:7])

    i2c_scd40 = I2C(
        const.I2C_BUS_ID,
        scl=Pin(const.SCD40_SCL_PIN),
        sda=Pin(const.SCD40_SDA_PIN),
        freq=const.I2C_FREQUENCY,
    )
    print("i2c_0 scan result:", i2c_scd40.scan())
    scd40_sensor = scd40.SCD40(i2c_scd40)
    scd40_sensor.restart_periodic_measurement()

    #센서 정보 수집 시작
    led_sensor = Pin(1, Pin.OUT)
    led_sensor.value(1)
    
    data_lock.acquire() #-------------------------
    data_1st.last_index = -1
    data_1st.value_count = 0
    data_2nd.last_index = -1
    data_2nd.value_count = 0
    data_3rd.last_index = -1
    data_3rd.value_count = 0
    data_lock.release() #-------------------------
    while True:
        led_sensor.value(0) 
        if data_1st.is_sensing:
            measurement = scd40_sensor.read_if_ready()
            if measurement is None:
                led_sensor.value(1)
                sleep(period_sensing)
                continue

            co2, temperature, humidity = measurement
            timestamp = rtc.datetime()
            timestring = "%02d:%02d:%02d" % (timestamp[4:7])

            data_lock.acquire()
            try:
                data_1st.add(co2)
                data_2nd.add(temperature)
                data_3rd.add(humidity)
            finally:
                data_lock.release()

            file_lock.acquire()
            try:
                with open(csv_file_name_ext, "a") as csv_file:
                    csv_file.write(
                        "%s,%s,%s,%s\n" % (
                            timestring,
                            co2,
                            temperature,
                            humidity,
                        )
                    )
            finally:
                file_lock.release()

        led_sensor.value(1) 
        sleep(period_sensing)
        
    print("It' the END of Core_1")
