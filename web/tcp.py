import socket


_SOCKET_CALLBACK_OPTION = 20

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
            # 6. 소켓 옵션 생성
            server_socket.setsockopt(
                socket.SOL_SOCKET,
                _SOCKET_CALLBACK_OPTION,
                self._accept_client,
            )
        except Exception:
            server_socket.close()
            raise

        self.socket = server_socket
        print("TCP server listening on %s:%d" % (self.host, self.port))

    def stop(self):
        if self.socket is None:
            return

        self.socket.close()
        self.socket = None

    def _accept_client(self, server_socket):
        client_socket = None

        try:
            # 7. 소켓 accept wait
            client_socket, client_address = server_socket.accept()
            # 8. accept 완료시 블록킹 모드로 전환
            client_socket.setblocking(False)
            # 9. 소켓 옵션 설정
            client_socket.setsockopt(
                socket.SOL_SOCKET,
                _SOCKET_CALLBACK_OPTION,
                self.request_handler,
            )
            print("TCP client connected:", client_address)
        except Exception as error:
            if client_socket is not None:
                client_socket.close()
            print("TCP accept failed:", error)
