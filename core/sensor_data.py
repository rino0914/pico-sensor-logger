from array import array

MAX_ARRAY_SIZE = 200


# @brief CO2, 습도, 온도 측정값을 고정 크기 원형 버퍼에 저장하고 통계 계산
# @note 오래된 데이터부터 새 데이터 순서로 접근하기 위해 논리 인덱스를 사용
class SensorStatsBuffer:
    # 측정값 종류를 선택할 때 사용하는 필드 이름
    FIELD_CO2 = "co2"
    FIELD_HUMIDITY = "humidity"
    FIELD_TEMPERATURE = "temperature"

    # @brief 측정값 저장용 원형 버퍼를 초기화
    def __init__(self, size=MAX_ARRAY_SIZE):
        self.size  = size
        self.head  = 0
        self.count = 0

        # 각 센서 항목을 32비트 실수 배열로 따로 보관.
        self.co2        = array("f", [0.0] * self.size)
        self.temperature = array("f", [0.0] * self.size)
        self.humidity   = array("f", [0.0] * self.size)
        self.sample_ticks = array("I", [0] * self.size)

    # @brief 현재 버퍼에 저장된 유효한 측정값 개수를 반환
    # @return 0부터 버퍼 최대 크기 사이의 데이터 개수
    def __len__(self):
        return self.count

    # @brief 저장된 데이터를 논리적으로 모두 비우고 통계값을 초기화
    # @return 없음
    # @note 배열 메모리는 다시 할당하거나 0으로 채우지 않고 head와 count만 초기화
    def clear(self):
        self.head = 0
        self.count = 0
        
    # @brief CO2, 습도, 온도 측정값 한 세트를 원형 버퍼에 추가
    # @param co2 CO2 농도(ppm)
    # @param hum 상대습도(%)
    # @param temperature 온도(°C)
    # @return 없음
    # @note 버퍼가 가득 차면 가장 오래된 값을 새 값으로 overwrite
    def append(self, co2, humidity, temperature, sample_ticks=0):
        index = self.head

        self.co2[index]        = co2
        self.humidity[index]   = humidity
        self.temperature[index] = temperature
        self.sample_ticks[index] = sample_ticks

        self.head = (self.head + 1) % self.size
        if self.count < self.size:
            self.count +=1

    # @brief 오래된 값 기준의 논리 인덱스를 실제 배열 인덱스 변환
    # @param logical_index 0이 가장 오래된 값을 가리키는 논리 인덱스
    # @return 원형 배열에서 사용할 실제 인덱스
    # @raise IndexError 논리 인덱스가 저장된 데이터 범위를 벗어난 경우
    def _physical_index(self, logical_index):
        if logical_index < 0 or logical_index >= self.count:
            raise IndexError("index out of range")
        start = (self.head - self.count) % self.size
        return (start + logical_index) % self.size

    # @brief 논리 인덱스 위치의 CO2, 습도, 온도 측정값 반환
    # @param logical_index 0이 가장 오래된 값을 가리키는 논리 인덱스
    # @return (CO2, 습도, 온도) 튜플
    # @raise IndexError 논리 인덱스가 저장된 데이터 범위를 벗어난 경우
    def get(self, logical_index):
        i = self._physical_index(logical_index)
        return (
            self.measurement_at(i)
        )
    def measurement_at(self, physical_index):
        return (
            self.co2[physical_index],
            self.humidity[physical_index],
            self.temperature[physical_index],
        )   

    # @brief 현재 저장된 데이터 중 가장 오래된 값의 실제 배열 인덱스 계산
    # @return 원형 배열의 시작 인덱스
    def _start_index(self):
        return (self.head - self.count) % self.size

    def _series_for(self, field_name):
        if field_name == self.FIELD_CO2:
            return self.co2
        elif field_name == self.FIELD_HUMIDITY:
            return self.humidity
        elif field_name == self.FIELD_TEMPERATURE:
            return self.temperature
        else:
            raise ValueError("invalid field_name")
    
    def _copy_series(self, field_name):
        source = self._series_for(field_name)
        start = self._start_index()
        copied = array("f", [0.0] * self.count)
        for offset in range(self.count):
            index = (start + offset) % self.size
            copied[offset] = source[index]
        return copied
    
  
    def _calculate_statistics(self):
        if self.count == 0:
            return None
        start = self._start_index()
        latest_index = (self.head - 1) % self.size
        min_co2 = self.co2[start]
        min_humidity = self.humidity[start]
        min_temperature = self.temperature[start]

        max_co2 = self.co2[start]
        max_humidity = self.humidity[start]
        max_temperature = self.temperature[start]

        sum_co2 = 0.0
        sum_humidity = 0.0
        sum_temperature = 0.0
        
        for offset in range(self.count):
            i = (start + offset) % self.size
            co2 = self.co2[i]
            humidity = self.humidity[i]
            temperature = self.temperature[i]

            sum_co2 += co2
            sum_humidity += humidity
            sum_temperature += temperature
            
            if co2 < min_co2:
                min_co2 = co2
            if humidity < min_humidity:
                min_humidity = humidity
            if temperature < min_temperature:
                min_temperature = temperature
            
            if co2 > max_co2:
                max_co2 = co2
            if humidity > max_humidity:
                max_humidity = humidity
            if temperature > max_temperature:
                max_temperature = temperature

        return (
            self.measurement_at(latest_index),
            (min_co2, min_humidity, min_temperature),
            (max_co2, max_humidity, max_temperature),
            (sum_co2 / self.count, sum_humidity / self.count, sum_temperature / self.count)
        )
        
    # @brief 지정한 센서 항목의 내부 배열을 반환
    # @param field_name FIELD_CO2, FIELD_HUMIDITY 또는 FIELD_TEMPERATURE
    # @return 선택한 센서 항목의 array 객체
    # @raise ValueError 지원하지 않는 필드 이름인 경우
    def get_values(self, field_name):
        return self._copy_series(field_name)
    
    # @brief 현재 유효한 차트 데이터를 오래된 순서대로 복사
    # @return (CO2 배열, 온도 배열, 습도 배열)
    def chart_snapshot(self):
        return (
            (
                self._copy_series(self.FIELD_CO2),
                self._copy_series(self.FIELD_TEMPERATURE),
                self._copy_series(self.FIELD_HUMIDITY),
            ),
            self._copy_sample_ticks(),
        )

    def _copy_sample_ticks(self):
        start = self._start_index()
        copied = array("I", [0] * self.count)
        for offset in range(self.count):
            index = (start + offset) % self.size
            copied[offset] = self.sample_ticks[index]
        return copied

    # @brief 가장 최근에 추가된 측정값 반환
    # @return (CO2, 습도, 온도) 튜플, 데이터가 없으면 None
    def latest(self):
        if self.count == 0:
            return None
        latest_index = (self.head - 1) % self.size
        return self.measurement_at(latest_index)

    # @brief 저장된 측정값의 항목별 최솟값을 계산
    # @return (최소 CO2, 최소 습도, 최소 온도) 튜플, 데이터가 없으면 None
    def minimums(self):
        stats = self._calculate_statistics()
        if stats is None:
            return None
        return stats[1]  # 최소값 튜플 반환
    
    # @brief 저장된 측정값의 항목별 최댓값을 계산
    # @return (최대 CO2, 최대 습도, 최대 온도) 튜플, 데이터가 없으면 None
    def maximums(self):
        stats = self._calculate_statistics()
        if stats is None:
            return None
        return stats[2]  # 최대값 튜플 반환

    # @brief 저장된 측정값의 항목별 평균값 계산
    # @return (평균 CO2, 평균 습도, 평균 온도) 튜플, 데이터가 없으면 None
    def averages(self):
        stats = self._calculate_statistics()
        if stats is None:
            return None

        return stats[3]  # 평균값 튜플 반환

    # @brief 최신값과 최솟값, 최댓값, 평균값을 반환
    # @return (최신값, 최솟값, 최댓값, 평균값) 튜플, 데이터가 없으면 None
    def stats(self):
        return self._calculate_statistics()
