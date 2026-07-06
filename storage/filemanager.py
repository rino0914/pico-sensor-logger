import _thread


def _locked(method):
    def wrapper(self, *args, **kwargs):
        self._lock.acquire()
        try:
            return method(self, *args, **kwargs)
        finally:
            self._lock.release()

    return wrapper


class FileHandler:
    """하나의 파일에 대한 실제 입출력을 직렬화한다."""

    def __init__(self, path, encoding="utf-8"):
        self._lock = _thread.allocate_lock()
        self.file_path = path
        self.encoding = encoding

    @property
    def get_fname(self):
        return self.file_path.split("/")[-1]

    @property
    def get_dir(self):
        parts = self.file_path.split("/")
        if len(parts) <= 1:
            return ""
        return "/".join(parts[:-1])

    @property
    def get_ext(self):
        name = self.get_fname
        if "." in name:
            return "." + name.split(".")[-1]
        return ""

    @_locked
    def ensure_header(self, header):
        is_empty = True
        try:
            with open(self.file_path, "r") as file:
                is_empty = not bool(file.read(1))
        except OSError:
            pass

        if is_empty:
            with open(self.file_path, "w") as file:
                file.write(header + "\n")

    @_locked
    def reset(self, header):
        with open(self.file_path, "w") as file:
            file.write(header + "\n")

    @_locked
    def read(self):
        with open(self.file_path, "r") as file:
            return file.read()

    @_locked
    def write(self, content):
        with open(self.file_path, "w") as file:
            file.write(content)

    @_locked
    def write_line(self, line):
        with open(self.file_path, "a") as file:
            file.write(line + "\n")

    @_locked
    def send_to(self, client_socket):
        with open(self.file_path, "r") as file:
            for line in file:
                client_socket.sendall(line)


class CsvWriter:
    """DataConnector의 파일 큐를 소비해 CSV로 저장한다."""

    def __init__(self, connector, file_handler, header):
        self._lock = _thread.allocate_lock()
        self.connector = connector
        self.file_handler = file_handler
        self.header = header
        self._pending = None
        self.file_handler.ensure_header(header)

    @property
    def file_name(self):
        return self.file_handler.get_fname

    def process_one(self):
        """대기 중인 레코드 하나를 저장하며, 실패한 레코드는 재시도한다."""
        self._lock.acquire()
        try:
            if self._pending is None:
                self._pending = self.connector.consume()

            if self._pending is None:
                return False

            timestamp, co2, humidity, temperature = self._pending
            datetime_text = self._format_timestamp(timestamp)
            self.file_handler.write_line(
                "%s,%s,%s,%s" % (
                    datetime_text,
                    co2,
                    temperature,
                    humidity,
                )
            )
            self._pending = None
            return True
        finally:
            self._lock.release()

    def flush(self):
        while self.process_one():
            pass

    def pending_count(self):
        self._lock.acquire()
        try:
            pending_record = 1 if self._pending is not None else 0
            return self.connector.pending_count() + pending_record
        finally:
            self._lock.release()

    def reset(self):
        """미저장 데이터와 차트 히스토리를 버리고 CSV를 초기화한다."""
        self._lock.acquire()
        try:
            self._pending = None
            self.connector.clear()
            self.file_handler.reset(self.header)
        finally:
            self._lock.release()

    def send_to(self, client_socket):
        self.file_handler.send_to(client_socket)

    @staticmethod
    def _format_timestamp(timestamp):
        return "%04d-%02d-%02d %02d:%02d:%02d" % (
            timestamp[0],
            timestamp[1],
            timestamp[2],
            timestamp[4],
            timestamp[5],
            timestamp[6],
        )
