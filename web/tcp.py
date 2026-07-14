import socket


CLIENT_TIMEOUT_SECONDS = 1.0
EMPTY_POLL_LOG_INTERVAL = 200

# @brief TCP 서버 클래스
class TcpServer:
    def __init__(
        self,
        request_handler,
        host    = "0.0.0.0",
        port    = 80,
        backlog = 5,
    ):
        self.request_handler = request_handler
        self.host = host
        self.port = port
        self.backlog = backlog
        self.socket = None
        self._empty_poll_count = 0

    # @brief TCP 서버를 초기화하고 시작
    def start(self):
        # 1. 소켓이 존재하면 중단
        if self.socket is not None:
            return
        # 2. IP/Port로 주소 생성 및 소켓 할당
        address = socket.getaddrinfo(self.host, self.port)[0][-1]
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            # 3. 소켓 옵션 설정
            server_socket.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR,
                1,
            )
            # 4. 소켓 Bind -> Listing
            server_socket.bind(address)
            server_socket.listen(self.backlog)
            # 5. Non-Blocking 모드로 동작
            server_socket.setblocking(False)
        except Exception:
            server_socket.close()
            raise

        self.socket = server_socket
        self._empty_poll_count = 0
        print("TCP server listening on %s:%d" % (self.host, self.port))

    def stop(self):
        if self.socket is None:
            return

        self.socket.close()
        self.socket = None

    def process_pending(self):
        if self.socket is None:
            return False

        client_socket = None
        try:
            client_socket, client_address = self.socket.accept()
        except OSError:
            self._empty_poll_count += 1
            if self._empty_poll_count >= EMPTY_POLL_LOG_INTERVAL:
                print("[DEBUG] TCP server polling; no pending client connection.")
                self._empty_poll_count = 0
            return False

        try:
            self._empty_poll_count = 0
            client_socket.setblocking(True)
            client_socket.settimeout(CLIENT_TIMEOUT_SECONDS)
            print("TCP client connected:", client_address)
            self.request_handler(client_socket)
            return True
        except Exception as error:
            if client_socket is not None:
                client_socket.close()
            print("TCP client handling failed:", error)
            return False
