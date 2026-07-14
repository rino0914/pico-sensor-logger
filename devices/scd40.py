import _thread
from time import sleep_ms
from machine import Pin
from micropython import const as _const

# 데이터 준비 상태 확인용 하위 11비트 마스크
READY_MASK = 0x07FF

# Sensirion CRC-8 설정값
CRC8_INIT = 0xFF
CRC8_POLYNOMIAL = 0x31

# 원시 온도·습도 값 변환 계수
TEMPERTURE_OFFSET_C = -45.0
TEMPERTURE_SCALE  = 175.0 / 65536.0
HUMIDITY_SCALE    = 100.0 / 65536.0

# SCD40 I2C 주소와 명령 코드
SCD40_ADDRESS                    = _const(0x62)
SCD40_DATA_READY                 = _const(0xE4B8)
SCD40_STOP_PERIODIC_MEASUREMENT  = _const(0x3F86)
SCD40_START_PERIODIC_MEASUREMENT = _const(0x21B1)
SCD40_READ_MEASUREMENT           = _const(0xEC05)    

# 명령별 송수신 버퍼 크기
SCD40_MEASUREMENT_BUFFER_SIZE = 9
SCD40_STATUS_BUFFER_SIZE      = 3
SCD40_COMMAND_BUFFER_SIZE     = 2

# Pico I2C 버스와 핀 설정
I2C_BUS_ID          = 0
I2C_FREQUENCY       = 100_000
I2C_USE_SOFT        = True
I2C_AUTO_SWAP_PINS  = True

# 명령 처리 대기시간과 상태 LED 핀
SCD40_COMMAND_DELAY_MS = 1
SCD40_STOP_DELAY_MS    = 500

# @brief SCD40 통신·응답 오류 기본 예외
class SCD40Error(Exception):
    pass

# @brief SCD40 응답 CRC 불일치 예외
class SCD40CrcError(SCD40Error):
    pass

# @brief SCD40 주기 측정, 상태 확인, 측정값 변환 API
class SCD40Device:
    # @brief SCD40 드라이버와 송수신 버퍼 초기화
    # @param i2c machine.I2C 호환 객체
    # @return 없음
    def __init__(self, i2c):
        self.i2c = i2c
        self.address = SCD40_ADDRESS

        # 센서값을 읽기위한 임시버퍼
        self._command_buffer     = bytearray(SCD40_COMMAND_BUFFER_SIZE)
        self._status_buffer      = bytearray(SCD40_STATUS_BUFFER_SIZE)
        self._measurement_buffer = bytearray(SCD40_MEASUREMENT_BUFFER_SIZE)
        
    # @brief 주기 측정 시작 명령 전송
    # @return 없음
    def start_periodic_measurement(self):
        self._write_command(SCD40_START_PERIODIC_MEASUREMENT)

    # @brief 주기 측정 중지 명령 전송
    # @return 없음
    def stop_periodic_measurement(self):
        self._write_command(SCD40_STOP_PERIODIC_MEASUREMENT)

    # @brief 주기 측정 중지 후 재시작
    # @return 없음
    def restart_periodic_measurement(self):
        self.stop_periodic_measurement()
        sleep_ms(SCD40_STOP_DELAY_MS)
        self.start_periodic_measurement()

    # @brief 새 측정값 준비 상태 확인
    # @return 준비 완료 시 True, 미완료 시 False
    def is_data_ready(self):
        status_word = self._read_word_response(SCD40_DATA_READY, self._status_buffer, SCD40_COMMAND_DELAY_MS)
        return (status_word & READY_MASK) != 0

    # @brief CO2, 온도, 습도 측정값 읽기
    # @return (CO2, 온도, 습도) 튜플
    def read_measurement(self):
        response = self._read_response(SCD40_READ_MEASUREMENT, self._measurement_buffer, SCD40_COMMAND_DELAY_MS)
        return self._parse_measurement(response)

    # @brief 준비 완료 시 측정값 읽기
    # @return (CO2, 온도, 습도) 튜플, 미준비 시 None
    def read_if_ready(self):
        if not self.is_data_ready():
            return None
        return self.read_measurement()

    # @brief 16비트 명령의 상위·하위 바이트 전송
    # @param command SCD40 16비트 명령 코드
    # @return 없음
    def _write_command(self, command):
        buffer = self._command_buffer
        buffer[0] = (command >> 8 & 0xFF)
        buffer[1] = command & 0xFF
        self.i2c.writeto(self.address, buffer)

    # @brief 명령 전송 후 응답 수신과 CRC 검증
    # @param command SCD40 16비트 명령 코드
    # @param buffer 응답 저장용 bytearray
    # @param delay_ms 명령 처리 대기시간(ms)
    # @return 수신 응답 버퍼
    def _read_response(self, command, buffer, delay_ms):
        self._write_command(command)
        sleep_ms(delay_ms)
        self.i2c.readfrom_into(self.address, buffer)
        self._validate_crc(buffer)
        return buffer

    # @brief 단일 16비트 응답 실행과 값 디코딩
    # @param command SCD40 16비트 명령 코드
    # @param buffer 3바이트 응답 저장용 bytearray
    # @param delay_ms 명령 처리 대기시간(ms)
    # @return 디코딩된 16비트 정수
    def _read_word_response(self, command, buffer, delay_ms):
        response = self._read_response(command, buffer, delay_ms)
        return self._decode_word(response, 0)

    # @brief 9바이트 측정 응답의 CO2·온도·습도 변환
    # @param buffer CRC 검증 완료 측정 응답
    # @return (CO2 ppm, 온도 °C, 상대습도 %) 튜플
    def _parse_measurement(self, buffer):
        co2 = self._decode_word(buffer, 0)
        raw_temperture = self._decode_word(buffer, 3)
        raw_humidity   = self._decode_word(buffer, 6)

        temperature = (TEMPERTURE_OFFSET_C + raw_temperture * TEMPERTURE_SCALE)
        humidity    = raw_humidity * HUMIDITY_SCALE
        return co2, temperature, humidity

    # @brief 3바이트 단위 응답의 CRC-8 검증
    # @param buffer 데이터 2바이트와 CRC 1바이트 단위 응답
    # @return 없음
    # @raise SCD40CrcError CRC 불일치
    @classmethod
    def _validate_crc(cls, buffer):
        for offset in range(0, len(buffer), 3):
            data_msb     = buffer[offset]
            data_lsb     = buffer[offset + 1]
            expected_crc = buffer[offset + 2]
            actual_crc   = cls._crc8(data_msb,data_lsb)

            if actual_crc != expected_crc:
                raise SCD40CrcError("SCD40 CRC check failed")

    # @brief 데이터 2바이트의 Sensirion CRC-8 계산
    # @param first_byte 첫 번째 데이터 바이트
    # @param second_byte 두 번째 데이터 바이트
    # @return 8비트 CRC 값
    @staticmethod
    def _crc8(first_byte, second_byte):
        crc = CRC8_INIT

        for byte in (first_byte, second_byte):
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ CRC8_POLYNOMIAL ) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF

        return crc

    # @brief 빅엔디언 16비트 값 디코딩
    # @param buffer 응답 바이트 버퍼
    # @param offset 상위 바이트 시작 위치
    # @return 디코딩된 16비트 정수
    @staticmethod
    def _decode_word(buffer, offset):
        return (buffer[offset] << 8) | buffer[offset + 1]
