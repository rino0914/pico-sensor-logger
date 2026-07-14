import socket
import time


CLIENT_IDLE_TIMEOUT_MS = 10000
EMPTY_POLL_LOG_INTERVAL = 200
MAX_IO_OPERATIONS_PER_POLL = 4
RECV_CHUNK_SIZE = 512

try:
    import errno
except ImportError:
    import uerrno as errno


def _ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def _ticks_diff(newer, older):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(newer, older)
    return newer - older


def _is_would_block(error):
    code = error.args[0] if error.args else None
    return code in (
        getattr(errno, "EAGAIN", 11),
        getattr(errno, "EWOULDBLOCK", 11),
    )


class TcpServer:
    """한 연결을 여러 메인 루프에 나눠 처리하는 논블로킹 TCP 서버."""

    def __init__(
        self,
        request_handler,
        host="0.0.0.0",
        port=80,
        backlog=5,
        idle_timeout_ms=CLIENT_IDLE_TIMEOUT_MS,
        time_ms_provider=None,
    ):
        # request_handler는 요청이 아직 덜 왔으면 None, 완성됐으면
        # 응답 bytes iterable을 반환한다.
        self.request_handler = request_handler
        self.host = host
        self.port = port
        self.backlog = backlog
        self.idle_timeout_ms = idle_timeout_ms
        self._time_ms = time_ms_provider or _ticks_ms
        self.socket = None
        self._client_socket = None
        self._client_address = None
        self._request = bytearray()
        self._response = None
        self._send_buffer = b""
        self._send_offset = 0
        self._last_activity_ms = 0
        self._empty_poll_count = 0

    def start(self):
        if self.socket is not None:
            return

        address = socket.getaddrinfo(self.host, self.port)[0][-1]
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(address)
            server_socket.listen(self.backlog)
            server_socket.setblocking(False)
        except Exception:
            server_socket.close()
            raise

        self.socket = server_socket
        self._empty_poll_count = 0
        print("TCP server listening on %s:%d" % (self.host, self.port))

    def stop(self):
        self._close_client()
        if self.socket is None:
            return
        self.socket.close()
        self.socket = None

    def process_pending(self):
        if self.socket is None:
            return False

        if self._client_socket is None:
            return self._accept_client()

        now = self._time_ms()
        if _ticks_diff(now, self._last_activity_ms) >= self.idle_timeout_ms:
            print("TCP client timed out:", self._client_address)
            self._close_client()
            return False

        try:
            if self._response is None:
                return self._receive_request()
            return self._send_response()
        except Exception as error:
            print("TCP client handling failed:", error)
            self._close_client()
            return False

    def _accept_client(self):
        try:
            client_socket, client_address = self.socket.accept()
        except OSError as error:
            if not _is_would_block(error):
                print("TCP accept failed:", error)
                return False
            self._empty_poll_count += 1
            if self._empty_poll_count >= EMPTY_POLL_LOG_INTERVAL:
                print("[DEBUG] TCP server polling; no pending client connection.")
                self._empty_poll_count = 0
            return False

        self._empty_poll_count = 0
        try:
            client_socket.setblocking(False)
        except Exception as error:
            client_socket.close()
            print("TCP client setup failed:", error)
            return False
        self._client_socket = client_socket
        self._client_address = client_address
        self._request = bytearray()
        self._response = None
        self._send_buffer = b""
        self._send_offset = 0
        self._last_activity_ms = self._time_ms()
        print("TCP client connected:", client_address)
        return True

    def _receive_request(self):
        progressed = False
        for _ in range(MAX_IO_OPERATIONS_PER_POLL):
            try:
                chunk = self._client_socket.recv(RECV_CHUNK_SIZE)
            except OSError as error:
                if _is_would_block(error):
                    break
                raise

            if not chunk:
                self._close_client()
                return progressed

            progressed = True
            self._last_activity_ms = self._time_ms()
            self._request.extend(chunk)
            # bytearray를 그대로 넘겨 미완성 요청마다 전체 복사하지 않는다.
            response = self.request_handler(self._request)
            if response is not None:
                self._response = iter(response)
                # 같은 poll에서 첫 응답 조각까지 전송해 지연을 줄인다.
                return self._send_response() or progressed
        return progressed

    def _send_response(self):
        progressed = False
        for _ in range(MAX_IO_OPERATIONS_PER_POLL):
            if self._send_offset >= len(self._send_buffer):
                try:
                    self._send_buffer = next(self._response)
                except StopIteration:
                    self._close_client()
                    return True
                self._send_offset = 0
                if isinstance(self._send_buffer, str):
                    self._send_buffer = self._send_buffer.encode("utf-8")
                if not self._send_buffer:
                    continue

            try:
                sent = self._client_socket.send(
                    self._send_buffer[self._send_offset:]
                )
            except OSError as error:
                if _is_would_block(error):
                    break
                raise

            if sent is None:
                # 일부 MicroPython 포트는 성공 시 None을 반환할 수 있다.
                sent = len(self._send_buffer) - self._send_offset
            if sent <= 0:
                raise OSError("TCP socket send returned no progress")
            self._send_offset += sent
            self._last_activity_ms = self._time_ms()
            progressed = True
        return progressed

    def _close_client(self):
        if self._client_socket is not None:
            try:
                self._client_socket.close()
            except Exception:
                pass
        self._client_socket = None
        self._client_address = None
        self._request = bytearray()
        self._response = None
        self._send_buffer = b""
        self._send_offset = 0
