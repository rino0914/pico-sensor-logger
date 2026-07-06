import _thread

try:
    from time import ticks_diff, ticks_ms
except ImportError:
    from time import monotonic

    def ticks_ms():
        return int(monotonic() * 1000)

    def ticks_diff(current, previous):
        return current - previous

from core.sensor_data import SensorStatsBuffer


DEFAULT_QUEUE_SIZE = 32
DEFAULT_STALE_AFTER_MS = 10_000


class DataSnapshot:
    def __init__(
        self,
        series,
        latest_timestamp,
        age_ms,
        is_stale,
        pending_count,
        dropped_count,
        sensing_enabled,
    ):
        self.series = series
        self.latest_timestamp = latest_timestamp
        self.age_ms = age_ms
        self.is_stale = is_stale
        self.pending_count = pending_count
        self.dropped_count = dropped_count
        self.sensing_enabled = sensing_enabled

# @brief 센서, 파일 저장기, 웹 서버 사이에서 측정 데이터를 전달한다.
#        측정 히스토리는 SensorStatsBuffer가 담당하고, 파일 저장 대기 데이터는
#        고정 크기 원형 큐에 보관한다. 공유 상태는 이 클래스의 락으로 보호한다.
class DataConnector:
  
    def __init__(self, queue_size=DEFAULT_QUEUE_SIZE):
        if queue_size <= 0:
            raise ValueError("queue_size must be greater than zero")

        self._lock = _thread.allocate_lock()
        self._stats_buffer = SensorStatsBuffer()

        # Pico의 메모리 사용량이 계속 늘지 않도록 고정 크기 큐를 사용한다.
        self._queue         = [None] * queue_size
        self._queue_size    = queue_size
        self._queue_head    = 0
        self._queue_tail    = 0
        self._queue_count   = 0
        self._dropped_count = 0

        self._sensing_enabled    = False
        self._latest_timestamp   = None
        self._last_publish_ticks = None

    # @brief 센서 측정과 데이터 발행을 허용
    def start_sensing(self):
        self._lock.acquire()
        try:
            self._sensing_enabled = True
        finally:
            self._lock.release()

    # @brief 센서 측정과 데이터 발행 중지
    def stop_sensing(self):
        self._lock.acquire()
        try:
            self._sensing_enabled = False
        finally:
            self._lock.release()
    # @brief 현재 측정 활성 상태 반환
    def is_enabled(self):
        self._lock.acquire()
        try:
            return self._sensing_enabled
        finally:
            self._lock.release()
    # @brief 새 측정값을 통계 버퍼와 파일 저장 큐에 함께 등록
    #        반환값은 타임스탬프를 포함한 파일 저장용 튜플
    #        큐가 가득 차면 가장 오래된 미저장 데이터를 버리고 새 값을 보관
    def publish(self, timestamp, co2, humidity, temperature):
        file_record = (timestamp, co2, humidity, temperature)

        self._lock.acquire()
        try:
            if not self._sensing_enabled:
                return None

            self._stats_buffer.append(co2, humidity, temperature)
            self._latest_timestamp = timestamp
            self._last_publish_ticks = ticks_ms()

            if self._queue_count == self._queue_size:
                self._queue_head = (
                    self._queue_head + 1
                ) % self._queue_size
                self._dropped_count += 1
            else:
                self._queue_count += 1

            self._queue[self._queue_tail] = file_record
            self._queue_tail = (
                self._queue_tail + 1
            ) % self._queue_size
            return file_record
        finally:
            self._lock.release()
    # @brief 가장 오래된 파일 저장 대기 값을 반환
    #        대기 중인 데이터가 없으면 None을 반환
    def consume(self):
        self._lock.acquire()
        try:
            if self._queue_count == 0:
                return None

            measurement = self._queue[self._queue_head]
            self._queue[self._queue_head] = None
            self._queue_head = (
                self._queue_head + 1
            ) % self._queue_size
            self._queue_count -= 1
            return measurement
        finally:
            self._lock.release()
    

    def latest(self):
        """가장 최근 측정값을 반환한다."""
        self._lock.acquire()
        try:
            return self._stats_buffer.latest()
        finally:
            self._lock.release()

    def stats(self):
        """최신값, 최솟값, 최댓값, 평균값을 반환한다."""
        self._lock.acquire()
        try:
            return self._stats_buffer.stats()
        finally:
            self._lock.release()

    def get_values(self, field_name):
        """웹 차트용 센서값 배열 복사본을 반환한다."""
        self._lock.acquire()
        try:
            return self._stats_buffer.get_values(field_name)
        finally:
            self._lock.release()

    def chart_snapshot(self):
        """일관된 시점의 CO2·온도·습도 차트 데이터를 반환한다."""
        self._lock.acquire()
        try:
            return self._stats_buffer.chart_snapshot()
        finally:
            self._lock.release()

    def snapshot(self, stale_after_ms=DEFAULT_STALE_AFTER_MS):
        """웹 표시용 데이터와 최신성·파일 backlog를 한 시점에 반환한다."""
        self._lock.acquire()
        try:
            if self._last_publish_ticks is None:
                age_ms = None
                is_stale = True
            else:
                age_ms = ticks_diff(
                    ticks_ms(),
                    self._last_publish_ticks,
                )
                is_stale = age_ms > stale_after_ms

            return DataSnapshot(
                series=self._stats_buffer.chart_snapshot(),
                latest_timestamp=self._latest_timestamp,
                age_ms=age_ms,
                is_stale=is_stale,
                pending_count=self._queue_count,
                dropped_count=self._dropped_count,
                sensing_enabled=self._sensing_enabled,
            )
        finally:
            self._lock.release()

    def pending_count(self):
        """파일 저장을 기다리는 측정값 개수를 반환한다."""
        self._lock.acquire()
        try:
            return self._queue_count
        finally:
            self._lock.release()

    def dropped_count(self):
        """큐가 가득 차서 버린 측정값의 누적 개수를 반환한다."""
        self._lock.acquire()
        try:
            return self._dropped_count
        finally:
            self._lock.release()

    def clear(self):
        """통계와 파일 저장 대기 데이터를 모두 초기화한다."""
        self._lock.acquire()
        try:
            self._stats_buffer.clear()
            for index in range(self._queue_size):
                self._queue[index] = None
            self._queue_head = 0
            self._queue_tail = 0
            self._queue_count = 0
            self._dropped_count = 0
            self._latest_timestamp = None
            self._last_publish_ticks = None
        finally:
            self._lock.release()
