import errno
import unittest

from web.tcp import TcpServer


WOULD_BLOCK = getattr(errno, "EWOULDBLOCK", errno.EAGAIN)


class FakeListener:
    def __init__(self, client):
        self.client = client
        self.accepted = False
        self.closed = False

    def accept(self):
        if self.accepted:
            raise OSError(WOULD_BLOCK)
        self.accepted = True
        return self.client, ("192.168.4.17", 12345)

    def close(self):
        self.closed = True


class FakeNonBlockingClient:
    def __init__(self, receives=None, send_limit=None):
        self.receives = list(receives or [])
        self.send_limit = send_limit
        self.response = bytearray()
        self.blocking = None
        self.closed = False

    def setblocking(self, value):
        self.blocking = value

    def recv(self, size):
        if not self.receives:
            raise OSError(WOULD_BLOCK)
        value = self.receives.pop(0)
        if isinstance(value, Exception):
            raise value
        return value[:size]

    def send(self, data):
        size = len(data) if self.send_limit is None else min(self.send_limit, len(data))
        self.response.extend(data[:size])
        return size

    def close(self):
        self.closed = True


class TcpServerTest(unittest.TestCase):
    def make_server(self, client, handler, clock=None, timeout=10000):
        clock = clock or [0]
        server = TcpServer(
            handler,
            idle_timeout_ms=timeout,
            time_ms_provider=lambda: clock[0],
        )
        server.socket = FakeListener(client)
        return server, clock

    def test_fragmented_request_does_not_block_or_close_client(self):
        requests = []

        def handler(request):
            requests.append(request)
            if b"\r\n\r\n" not in request:
                return None
            return (b"HTTP/1.1 200 OK\r\n\r\n", b"ok")

        client = FakeNonBlockingClient([
            b"GET / HTTP/1.1\r\n",
            OSError(WOULD_BLOCK),
            b"Host: pico\r\n\r\n",
        ])
        server, _ = self.make_server(client, handler)

        self.assertTrue(server.process_pending())
        self.assertFalse(client.blocking)
        self.assertTrue(server.process_pending())
        self.assertFalse(client.closed)
        self.assertTrue(server.process_pending())
        while not client.closed:
            server.process_pending()

        self.assertGreaterEqual(len(requests), 2)
        self.assertEqual(b"HTTP/1.1 200 OK\r\n\r\nok", client.response)

    def test_partial_send_resumes_from_previous_offset(self):
        client = FakeNonBlockingClient(
            [b"request"],
            send_limit=2,
        )
        server, _ = self.make_server(client, lambda request: (b"abcdef", b"ghi"))

        server.process_pending()
        for _ in range(10):
            server.process_pending()
            if client.closed:
                break

        self.assertTrue(client.closed)
        self.assertEqual(b"abcdefghi", client.response)

    def test_idle_client_is_closed_after_timeout(self):
        client = FakeNonBlockingClient([OSError(WOULD_BLOCK)])
        server, clock = self.make_server(client, lambda request: None)

        server.process_pending()
        server.process_pending()
        self.assertFalse(client.closed)
        clock[0] = 10000
        server.process_pending()

        self.assertTrue(client.closed)

    def test_stop_closes_listener_and_active_client(self):
        client = FakeNonBlockingClient()
        server, _ = self.make_server(client, lambda request: None)
        listener = server.socket
        server.process_pending()

        server.stop()

        self.assertTrue(client.closed)
        self.assertTrue(listener.closed)
        self.assertIsNone(server.socket)


if __name__ == "__main__":
    unittest.main()
