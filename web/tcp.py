import socket


_SOCKET_CALLBACK_OPTION = 20


class TcpServer:
    def __init__(
        self,
        request_handler,
        host="0.0.0.0",
        port=80,
        backlog=5,
    ):
        self.request_handler = request_handler
        self.host = host
        self.port = port
        self.backlog = backlog
        self.socket = None

    def start(self):
        if self.socket is not None:
            return

        address = socket.getaddrinfo(self.host, self.port)[0][-1]
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            server_socket.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR,
                1,
            )
            server_socket.bind(address)
            server_socket.listen(self.backlog)
            server_socket.setblocking(False)
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
            client_socket, client_address = server_socket.accept()
            client_socket.setblocking(False)
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
