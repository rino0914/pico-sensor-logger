try:
    from time import sleep_ms
except ImportError:
    from time import sleep

    def sleep_ms(milliseconds):
        sleep(milliseconds / 1_000)

import const


class SCD40:
    def __init__(self, i2c, address=const.SCD40_ADDRESS):
        self.i2c = i2c
        self.address = address
        self.command_buffer = bytearray(
            const.SCD40_COMMAND_BUFFER_SIZE
        )
        self.status_buffer = bytearray(
            const.SCD40_STATUS_BUFFER_SIZE
        )
        self.measurement_buffer = bytearray(
            const.SCD40_MEASUREMENT_BUFFER_SIZE
        )

    def restart_periodic_measurement(self):
        self.stop_periodic_measurement()
        sleep_ms(const.SCD40_STOP_DELAY_MS)
        self.start_periodic_measurement()

    def start_periodic_measurement(self):
        self._send_command(
            const.SCD40_START_PERIODIC_MEASUREMENT
        )

    def stop_periodic_measurement(self):
        self._send_command(
            const.SCD40_STOP_PERIODIC_MEASUREMENT
        )

    def is_data_ready(self):
        self._send_command(const.SCD40_DATA_READY)
        sleep_ms(const.SCD40_COMMAND_DELAY_MS)
        self._read_response(self.status_buffer)

        status = (
            self.status_buffer[0] << 8
        ) | self.status_buffer[1]
        return status & 0x07FF != 0

    def read_measurement(self):
        self._send_command(const.SCD40_READ_MEASUREMENT)
        sleep_ms(const.SCD40_COMMAND_DELAY_MS)
        self._read_response(self.measurement_buffer)

        co2 = self._word_at(self.measurement_buffer, 0)
        raw_temperature = self._word_at(
            self.measurement_buffer,
            3,
        )
        raw_humidity = self._word_at(
            self.measurement_buffer,
            6,
        )

        temperature = -45 + 175 * raw_temperature / 65_536
        humidity = 100 * raw_humidity / 65_536
        return co2, temperature, humidity

    def read_if_ready(self):
        if not self.is_data_ready():
            return None
        return self.read_measurement()

    def _send_command(self, command):
        self.command_buffer[0] = command >> 8
        self.command_buffer[1] = command & 0xFF
        self.i2c.writeto(self.address, self.command_buffer)

    def _read_response(self, buffer):
        self.i2c.readfrom_into(self.address, buffer)
        self._validate_crc(buffer)

    @classmethod
    def _validate_crc(cls, buffer):
        for offset in range(0, len(buffer), 3):
            expected_crc = buffer[offset + 2]
            actual_crc = cls._crc8(
                buffer[offset],
                buffer[offset + 1],
            )
            if actual_crc != expected_crc:
                raise RuntimeError("SCD40 CRC check failed")

    @staticmethod
    def _crc8(first_byte, second_byte):
        crc = 0xFF

        for byte in (first_byte, second_byte):
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc <<= 1
                crc &= 0xFF

        return crc

    @staticmethod
    def _word_at(buffer, offset):
        return (buffer[offset] << 8) | buffer[offset + 1]
