import rp2
from time import sleep
from machine import I2C, Pin

from config_loader import get_config_value, load_config
from core.data_connector import DataConnector
from core.time_service import TimeService
from devices import scd40_thread
from devices.ap import AccessPoint
from storage.filemanager import CsvWriter, FileHandler
from web.web_server import WebServer

APP_NAME = "PTL-LOGGER"
CONFIG_FILE = "config.json"
MAIN_LOOP_INTERVAL_SECONDS = 0.05

# @brief LED 초기화 및 꺼짐 상태 유지
# @return LED 상태
def create_status_led():
    status_led = Pin("LED", Pin.OUT)
    status_led.off()
    return status_led

# @brief CSV파일 관리 객체 생성 및 반환
# @param config 설정
# @param connector 커넥터
# @return CSVWriter 객체
def create_storage(config, connector):
    csv_path     = get_config_value(config, "logfile", "filename")
    field_names  = get_config_value(config, "logfile", "field_names")
    file_handler = FileHandler(csv_path)
    return CsvWriter(
        connector,
        file_handler,
        ", ".join(field_names),
    )

# @brief SCD40 센서 기록 스레드 생성 및 반환
# @param connector 커넥터
# @param time_service 시간 동기화 객체
# @return cd40_thread.SCD40Thread
def create_sensor(connector, time_service):
    i2c = I2C(
        scd40_thread.I2C_BUS_ID,
        scl  = Pin(scd40_thread.SCD40_SCL_PIN),
        sda  = Pin(scd40_thread.SCD40_SDA_PIN),
        freq = scd40_thread.I2C_FREQUENCY,
    )
    print("i2c_0 scan result:", i2c.scan())

    return scd40_thread.SCD40Thread(
        i2c,
        connector,
        time_service,
    )

# @brief 애플리케이션 생성 및 반환
# @param config 설정
# @param status_led LED 상태
# @return ap, web_server, sensor, csv_writer
def create_application(config, status_led):
    #1.데이터 커넥터 생성(센서스레드 - 웹 서버 간 데이터 consume/produce)
    connector = DataConnector()
    #2.시간 동기화 생성
    time_service = TimeService()
    #3. csv writer 생성 및 커넥터 추가
    csv_writer = create_storage(config, connector)
    #4. AP 생성
    ap = AccessPoint(
        get_config_value(config, "wifi", "ssid"),
        get_config_value(config, "wifi", "password"),
    )
    #5. 웹 서버 생성
    web_server = WebServer(
        connector=connector,
        time_service=time_service,
        csv_writer=csv_writer,
        led=status_led,
    )
    #6. scd40 센서 수집기 생성
    sensor = create_sensor(connector, time_service)

    return ap, web_server, sensor, csv_writer

# @brief 애플리케이션 시작
# @param ap AP
# @param web_server 웹서버
# @param sensor SDC40 센서
# @param status_led LED 상태
def start_application(ap, web_server, sensor, status_led):
    #1. AP 구동
    ap.start(status_led)
    #2. 웹서버 구동
    web_server.start()
    #3. 센서 수집기 구동
    sensor.start()

# @brief 애플리케이션 중지
# @param ap AP
# @param web_server 웹서버
# @param sensor SDC40 센서
# @param status_led LED 상태
def stop_application(ap, web_server, sensor, csv_writer, status_led):
    web_server.stop()
    sensor.stop()

    while sensor.is_running():
        sleep(MAIN_LOOP_INTERVAL_SECONDS)

    csv_writer.flush()
    ap.stop(status_led)


if __name__ == "__main__":
    print("[ALERT] %s Started.")
    # 1.설정파일 로드
    config = load_config(CONFIG_FILE)
    print("[INFO] Succeed to load configurtaion."+ config)
    # 2.LED 초기화
    status_led = create_status_led()
    print("[INFO] Succeed to initailaize LED statue.")
    # 3. 애플리케이션 초기화
    (
        ap,
        web_server,
        sensor,
        csv_writer,
    ) = create_application(config, status_led)
    print("[INFO] Succeed to create application.")
    # 4. 애플리케이션 구동
    start_application(ap, web_server, sensor, status_led)
    print("[INFO] Succeed to start application.")
    # 버튼 푸시 감지 전 까지 무한 루프
    while True:
        try:
            #CSV 파일 write
            csv_writer.process_one()
        except OSError as error:
            print("[WARN] Failed to write CSV.", error)

        if rp2.bootsel_button():
            print("[ALERT] BOOTSEL button detected!", error)
            stop_application(
                ap,
                web_server,
                sensor,
                csv_writer,
                status_led,
            )
            break
        sleep(MAIN_LOOP_INTERVAL_SECONDS)

    print("[ALERT] %s Stopped.")