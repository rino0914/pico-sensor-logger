STATUS_INITIALIZED = "initialized"
STATUS_TIME_SYNC = "time_sync"
STATUS_DELETE_BLOCKED = "delete_blocked"
STATUS_CSV_RESET = "csv_reset"
STATUS_TIME_SYNC_REQUIRED = "time_sync_required"
STATUS_SENSING = "sensing"
STATUS_STOPPED = "stopped"
STATUS_CSV_DOWNLOAD = "csv_download"
STATUS_MEASUREMENT_COMPLETE = "measurement_complete"
STATUS_MEASUREMENT_LIMIT_REACHED = "measurement_limit_reached"


STATUS_TEXT_BY_CODE = {
    STATUS_INITIALIZED: "초기화 완료",
    STATUS_TIME_SYNC: "시간 동기화 완료",
    STATUS_DELETE_BLOCKED: "측정 중에는 파일을 삭제할 수 없습니다.",
    STATUS_CSV_RESET: "데이터 파일 초기화 완료",
    STATUS_TIME_SYNC_REQUIRED: "시간 동기화 후 측정을 시작하세요.",
    STATUS_SENSING: "측정 중",
    STATUS_STOPPED: "측정 중지",
    STATUS_CSV_DOWNLOAD: "CSV 다운로드 준비 완료",
    STATUS_MEASUREMENT_COMPLETE: "측정 완료",
    STATUS_MEASUREMENT_LIMIT_REACHED: "측정 데이터가 가득 찼습니다. CSV 저장 후 데이터를 초기화하세요.",
}


class WebControlService:
    """웹 요청을 애플리케이션 동작과 대시보드 데이터로 연결한다."""

    def __init__(
        self,
        connector,
        time_service,
        csv_writer,
        max_duration_seconds=20 * 60,
    ):
        self.connector = connector
        self.time_service = time_service
        self.csv_writer = csv_writer
        self.csv_file_name = csv_writer.file_name
        self.max_duration_seconds = max_duration_seconds
        self._status_code = STATUS_INITIALIZED
        self._measurement_completed = False
        self._completion_status_code = None

    @property
    def status_text(self):
        if self._status_code == STATUS_MEASUREMENT_COMPLETE:
            return "%d분 측정 완료" % (self.max_duration_seconds // 60)
        return STATUS_TEXT_BY_CODE[self._status_code]

    def dashboard_payload(self):
        time_synchronized = self.time_service.is_synchronized()
        return {
            "data_snapshot": self.connector.snapshot(),
            "status_text": self.status_text,
            "csv_file_name": self.csv_file_name,
            "pending_count": self.csv_writer.pending_count(),
            "time_synchronized": time_synchronized,
            "current_time": (
                self.time_service.now()
                if time_synchronized
                else None
            ),
        }

    def measurements_payload(self):
        snapshot = self.connector.snapshot()
        time_synchronized = self.time_service.is_synchronized()
        return {
            "time_offsets": list(snapshot.time_offsets),
            "co2": list(snapshot.series[0]),
            "temperature": list(snapshot.series[1]),
            "humidity": list(snapshot.series[2]),
            "latest_timestamp": (
                list(snapshot.latest_timestamp)
                if snapshot.latest_timestamp is not None
                else None
            ),
            "age_ms": snapshot.age_ms,
            "is_stale": snapshot.is_stale,
            "sensing_enabled": snapshot.sensing_enabled,
            "runtime_seconds": snapshot.runtime_seconds,
            "status_text": self.status_text,
            "pending_count": snapshot.pending_count,
            "dropped_count": snapshot.dropped_count,
            "time_synchronized": time_synchronized,
            "current_time": (
                list(self.time_service.now())
                if time_synchronized
                else None
            ),
        }

    def _set_status(self, status_code):
        self._status_code = status_code

    def synchronize_time(self, query):
        self.time_service.synchronize(*self._parse_time_values(query))
        print("[CONTROL] Time synchronized:", self.time_service.now())
        if not self.connector.is_enabled() and not self._measurement_completed:
            self._set_status(STATUS_TIME_SYNC)

    def delete_csv(self):
        if self.connector.is_enabled():
            self._set_status(STATUS_DELETE_BLOCKED)
            return False
        self.csv_writer.reset()
        self._measurement_completed = False
        self._completion_status_code = None
        self._set_status(STATUS_CSV_RESET)
        return True

    def start_sensing(self):
        if self.connector.is_enabled():
            return True
        if not self.time_service.is_synchronized():
            self._set_status(STATUS_TIME_SYNC_REQUIRED)
            print("[CONTROL] Sensing start rejected: time is not synchronized.")
            return False
        duration_reached = (
            self.connector.snapshot().runtime_seconds
            >= self.max_duration_seconds
        )
        if self._measurement_completed or duration_reached or self.csv_writer.is_full():
            self._measurement_completed = self._measurement_completed or duration_reached
            self._set_status(
                self._completion_status_code
                or (
                    STATUS_MEASUREMENT_COMPLETE
                    if duration_reached
                    else STATUS_MEASUREMENT_LIMIT_REACHED
                )
            )
            print("[CONTROL] Sensing start rejected: measurement limit reached.")
            return False
        self.connector.start_sensing()
        self._set_status(STATUS_SENSING)
        print("[CONTROL] Sensing enabled.")
        return True

    def stop_sensing(self):
        self.connector.stop_sensing()
        self._set_status(STATUS_STOPPED)

    def process_pending(self):
        if not self.connector.is_enabled():
            return False

        snapshot = self.connector.snapshot()
        duration_reached = snapshot.runtime_seconds >= self.max_duration_seconds
        record_limit_reached = self.csv_writer.is_full()
        if not duration_reached and not record_limit_reached:
            return False

        self.connector.complete_sensing()
        self._measurement_completed = True
        self._completion_status_code = (
            STATUS_MEASUREMENT_COMPLETE
            if duration_reached
            else STATUS_MEASUREMENT_LIMIT_REACHED
        )
        self._set_status(self._completion_status_code)
        try:
            self.csv_writer.flush()
        except OSError as error:
            print("[WARN] Failed to flush CSV after measurement completion:", error)
        print(
            "[CONTROL] Measurement completed: runtime=%ss, records=%s"
            % (snapshot.runtime_seconds, self.csv_writer.record_count())
        )
        return True

    def prepare_csv_download(self):
        self._set_status(STATUS_CSV_DOWNLOAD)
        self.csv_writer.flush()
        return self.csv_file_name

    def send_csv(self, client_socket):
        self.csv_writer.send_to(client_socket)

    def iter_csv_chunks(self, chunk_size=512):
        return self.csv_writer.iter_chunks(chunk_size)

    @staticmethod
    def _parse_time_values(query):
        required = (
            "year", "month", "day", "weekday",
            "hour", "minute", "second",
        )
        try:
            return tuple(int(query[key]) for key in required)
        except (KeyError, TypeError, ValueError):
            raise ValueError("Invalid time sync request.")
