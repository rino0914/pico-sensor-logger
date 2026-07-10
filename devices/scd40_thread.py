import _thread
from time import sleep_ms
from machine import Pin
from devices.scd40 import SCD40Error

SCD40_POLL_INTERVAL_MS = 500
SENSOR_STATUS_LED_PIN = 1

class SCD40Thread:
    # @brief SCD40 드라이버와 송수신 버퍼 초기화
    # @param i2c machine.I2C 호환 객체
    # @return 없음
    def __init__(self, sensor, connector, time_service, status_led=None):
        self.sensor = sensor
        self.connector = connector # 수신 데이터를 저장관리하는 데이터 커넥터
        self.time_service = time_service # 시간 동기화 스레드
        self.status_led = status_led or Pin(SENSOR_STATUS_LED_PIN, Pin.OUT)
        self._started = False
        self._running = False
        
    # @brief 센서 측정 루프를 새 스레드에서 시작
    # @return 생성된 스레드 식별자
    def start(self):
        if self._started:
            raise RuntimeError("SCD40 thread is already running")

        self._started = True
        self._running = True
        try:
            return _thread.start_new_thread(self.run, ())
        except Exception:
            self._started = False
            self._running = False
            raise

    # @brief 센서 측정 스레드에 종료 요청
    def stop(self):
        self._running = False

    def is_running(self):
        return self._started

    # @brief 준비된 측정값 한 건을 읽어 DataConnector에 전달
    # @return publish한 (CO2, 온도, 습도) 튜플, 미준비 시 None
    def poll_once(self):
        measurement = self.read_if_ready()
        if measurement is None:
            return None
        self._publish_measurement(measurement)
        return measurement

    def _publish_measurement(self, measurement):
        co2, humidity, temperature = measurement
        timestamp = self.time_service.now()
        self.connector.publish(timestamp, co2, humidity, temperature)
    def _wait_until_ready(self, interval_ms):
        while self._running:
            if (
                self.time_service.is_synchronized()
                and self.connector.is_enabled()
            ):
                self._running = True
            sleep_ms(interval_ms)
            
    # @brief 주기 측정을 시작하고 측정값을 계속 DataConnector에 전달
    # @param interval_ms 데이터 준비 상태를 확인하는 간격(ms)
    # @return 없음: stop() 요청 전까지 반복
    def run(self, interval_ms=SCD40_POLL_INTERVAL_MS):
        measurement_started = False
        try:
            if not self._wait_until_ready(interval_ms):
                return

            self.sensor.restart_periodic_measurement()
            measurement_started = True
            self.status_led.on()

            while self._running:
                if self.connector.is_enabled():
                    try:
                        self.poll_once()
                    except (OSError, RuntimeError, SCD40Error) as error:
                        print("SCD40 measurement failed:", error)

                sleep_ms(interval_ms)
        finally:
            if measurement_started:
                try:
                    self.stop_periodic_measurement()
                except OSError as error:
                    print("SCD40 stop failed:", error)
            self.status_led.off()
            self._running = False
            self._started = False

