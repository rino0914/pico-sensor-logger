from array import array

MAX_ARRAY_SIZE   = 200


# @brief CO2, 습도, 온도 측정값을 고정 크기 원형 버퍼에 저장하고 통계 계산
# @note 오래된 데이터부터 새 데이터 순서로 접근하기 위해 논리 인덱스를 사용
class SensorStatsBuffer:
    # 측정값 종류를 선택할 때 사용하는 필드 이름
    FIELD_CO2 = "co2"
    FIELD_HUMIDITY = "humidity"
    FIELD_TEMPERTURE = "temperture"

    # @brief 측정값 저장용 원형 버퍼를 초기화
    def __init__(self):
        self.size  = MAX_ARRAY_SIZE
        self.head  = 0
        self.count = 0

        # 각 센서 항목을 32비트 실수 배열로 따로 보관.
        self.co2        = array("f", [0.0] * self.size)
        self.temperture = array("f", [0.0] * self.size)
        self.humidity   = array("f", [0.0] * self.size)

        self.min_co2        = 0.0
        self.min_humidity   = 0.0
        self.min_temperture = 0.0

        self.max_co2        = 0.0
        self.max_humidity   = 0.0
        self.max_temperture = 0.0

        self.avg_co2        = 0.0
        self.avg_humidity   = 0.0
        self.avg_temperture = 0.0

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
        
        self.min_co2        = 0.0
        self.min_humidity   = 0.0
        self.min_temperture = 0.0

        self.max_co2        = 0.0
        self.max_humidity   = 0.0
        self.max_temperture = 0.0

        self.avg_co2        = 0.0
        self.avg_humidity   = 0.0
        self.avg_temperture = 0.0

    # @brief CO2, 습도, 온도 측정값 한 세트를 원형 버퍼에 추가
    # @param co2 CO2 농도(ppm)
    # @param hum 상대습도(%)
    # @param temperture 온도(°C)
    # @return 없음
    # @note 버퍼가 가득 차면 가장 오래된 값을 새 값으로 overwrite
    def append(self, co2, hum, temperture):
        index = self.head

        self.co2[index]        = co2
        self.humidity[index]   = hum
        self.temperture[index] = temperture

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
            self.co2[i],
            self.humidity[i],
            self.temperture[i],
        )

    # @brief 현재 저장된 데이터 중 가장 오래된 값의 실제 배열 인덱스 계산
    # @return 원형 배열의 시작 인덱스
    def _start_index(self):
        return (self.head - self.count) % self.size

    # @brief 지정한 센서 항목의 내부 배열을 반환
    # @param field_name FIELD_CO2, FIELD_HUMIDITY 또는 FIELD_TEMPERTURE
    # @return 선택한 센서 항목의 array 객체
    # @raise ValueError 지원하지 않는 필드 이름인 경우
    def get_values(self, field_name):
        if field_name == self.FIELD_CO2:
            source = self.co2
        elif field_name == self.FIELD_HUMIDITY:
            source = self.humidity
        elif field_name == self.FIELD_TEMPERTURE:
            source = self.temperture
        else:
            raise ValueError("invalid field_name")

        # 락 해제 후에도 호출자가 안전하게 사용할 수 있도록 복사본 반환
        return array("f", source)

    # @brief 현재 유효한 차트 데이터를 오래된 순서대로 복사
    # @return (CO2 배열, 온도 배열, 습도 배열)
    def chart_snapshot(self):
        co2_values = array("f", [0.0] * self.count)
        temperature_values = array("f", [0.0] * self.count)
        humidity_values = array("f", [0.0] * self.count)
        start = self._start_index()

        for offset in range(self.count):
            index = (start + offset) % self.size
            co2_values[offset] = self.co2[index]
            temperature_values[offset] = self.temperture[index]
            humidity_values[offset] = self.humidity[index]

        return co2_values, temperature_values, humidity_values

    # @brief 가장 최근에 추가된 측정값 반환
    # @return (CO2, 습도, 온도) 튜플, 데이터가 없으면 None
    def latest(self):
        if self.count == 0:
            return None
        i = (self.head -1) % self.size
        
        return (
            self.co2[i],
            self.humidity[i],
            self.temperture[i],
        )

    # @brief 저장된 측정값의 항목별 최솟값을 계산
    # @return (최소 CO2, 최소 습도, 최소 온도) 튜플, 데이터가 없으면 None
    def minimums(self):
        if self.count == 0:
            return None
        start = (self.head - self.count) % self.size

        min_co2        = self.co2[start]
        min_humidity   = self.humidity[start]
        min_temperture = self.temperture[start]

        for offset in range(1, self.count):
            i = (start + offset) % self.size
            co2 = self.co2[i]
            humidity = self.humidity[i]
            temperture = self.temperture[i]

            if co2 < min_co2:
                min_co2 = co2
            if humidity < min_humidity:
                min_humidity = humidity
            if temperture < min_temperture:
                min_temperture = temperture
        
        return(
            min_co2,
            min_humidity,
            min_temperture
        )

    # @brief 저장된 측정값의 항목별 최댓값을 계산
    # @return (최대 CO2, 최대 습도, 최대 온도) 튜플, 데이터가 없으면 None
    def maximums(self):
        if self.count == 0:
            return None
        start = (self.head - self.count) % self.size

        max_co2        = self.co2[start]
        max_humidity   = self.humidity[start]
        max_temperture = self.temperture[start]

        for offset in range(1, self.count):
            i = (start + offset) % self.size
            co2 = self.co2[i]
            humidity = self.humidity[i]
            temperture = self.temperture[i]

            if co2 > max_co2:
                max_co2 = co2
            if humidity > max_humidity:
                max_humidity = humidity
            if temperture > max_temperture:
                max_temperture = temperture
        
        return(
            max_co2,
            max_humidity,
            max_temperture
        )

    # @brief 저장된 측정값의 항목별 평균값 계산
    # @return (평균 CO2, 평균 습도, 평균 온도) 튜플, 데이터가 없으면 None
    def averages(self):
        if self.count == 0:
            return None
        
        start = (self.head - self.count) % self.size

        sum_co2        = 0.0
        sum_humidity   = 0.0
        sum_temperture = 0.0

        for offset in range(self.count):
            i = (start + offset) % self.size
            sum_co2        += self.co2[i]
            sum_humidity   += self.humidity[i]
            sum_temperture += self.temperture[i]

            num = self.count

        return (
            sum_co2 / num,
            sum_humidity / num,
            sum_temperture / num,
        )

    # @brief 최신값과 최솟값, 최댓값, 평균값을 반환
    # @return (최신값, 최솟값, 최댓값, 평균값) 튜플, 데이터가 없으면 None
    def stats(self):
        if self.count == 0:
            return None
        
        return(
            self.latest(),
            self.minimums(),
            self.maximums(),
            self.averages(),
        )
