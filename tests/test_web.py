import unittest
import json

from core.data_connector import DataConnector
from web.web_server import WebServer


class FakeTimeService:
    def __init__(self):
        self.synchronized = False
        self.current_time = (2026, 7, 12, 6, 9, 30, 45, 0)

    def synchronize(self, *values):
        self.values = values
        self.synchronized = True

    def is_synchronized(self):
        return self.synchronized

    def now(self):
        return self.current_time


class FakeCsvWriter:
    file_name = "measurements.csv"

    def __init__(self):
        self.reset_called = False

    def pending_count(self):
        return 0

    def flush(self):
        pass

    def reset(self):
        self.reset_called = True

    def send_to(self, client_socket):
        client_socket.sendall(b"timestamp,co2\n")

    def iter_chunks(self, chunk_size=512):
        return iter((b"timestamp,co2\n",))


class FakeLed:
    def on(self):
        self.enabled = True

    def off(self):
        self.enabled = False


class FakeNetworkInfoProvider:
    def get_network_info(self):
        return {
            "mode": "station",
            "ssid": "CLASSROOM_WIFI",
            "ip_address": "192.168.0.37",
            "connected": True,
        }


class FakeSocket:
    def __init__(self, request, chunk_size=None):
        self.request = request.encode("ascii")
        self.chunk_size = chunk_size
        self.response = bytearray()
        self.closed = False

    def recv(self, size):
        if not self.request:
            return b""
        if self.chunk_size is not None:
            size = min(size, self.chunk_size)
        chunk = self.request[:size]
        self.request = self.request[size:]
        return chunk

    def setblocking(self, value):
        pass

    def settimeout(self, value):
        pass

    def sendall(self, data):
        self.response.extend(data)

    def close(self):
        self.closed = True


class WebServerTest(unittest.TestCase):
    def setUp(self):
        self.connector = DataConnector()
        self.time = FakeTimeService()
        self.csv = FakeCsvWriter()
        self.server = WebServer(
            self.connector,
            self.time,
            self.csv,
            FakeLed(),
            port=8080,
            network_info_provider=FakeNetworkInfoProvider(),
        )

    def request(self, method, target):
        client = FakeSocket("%s %s HTTP/1.1\r\nHost: logger\r\n\r\n" % (method, target))
        self.server.handle_request(client)
        return bytes(client.response)

    def test_dashboard_contains_controls_and_charts(self):
        self.time.synchronized = True
        response = self.request("GET", "/")
        self.assertIn(b"HTTP/1.1 200 OK", response)
        self.assertIn("CO₂".encode("utf-8"), response)
        self.assertIn(b"/sensing_on", response)
        self.assertIn(b"measurements.csv", response)
        self.assertIn(b"CLASSROOM_WIFI", response)
        self.assertIn(b"192.168.0.37", response)
        self.assertIn(b"Station", response)
        self.assertIn(b"2026-07-12 09:30:45", response)
        self.assertIn("초기값 대비 변화율 (%)".encode("utf-8"), response)
        self.assertIn("측정 시간 (분:초, 최신값 기준)".encode("utf-8"), response)
        self.assertIn("이산화탄소 농도 (ppm)".encode("utf-8"), response)
        self.assertIn(b'data-chart="comparison"', response)
        self.assertIn(b'class="chart-tooltip"', response)
        self.assertIn(b"fetch(CHART_API", response)
        self.assertNotIn(b'http-equiv="refresh"', response)

    def test_dashboard_shows_time_sync_required_before_synchronization(self):
        response = self.request("GET", "/")

        self.assertIn("시각 동기화".encode("utf-8"), response)
        self.assertIn(">필요<".encode("utf-8"), response)

    def test_time_sync_accepts_declared_query(self):
        response = self.request(
            "POST",
            "/set_time?year=2026&month=7&day=11&weekday=6&hour=12&minute=30&second=0",
        )
        self.assertIn(b"HTTP/1.1 204 No Content", response)
        self.assertTrue(self.time.synchronized)

    def test_accepts_request_split_across_tcp_reads(self):
        client = FakeSocket(
            "GET / HTTP/1.1\r\nHost: logger\r\n\r\n",
            chunk_size=3,
        )
        self.server.handle_request(client)
        self.assertIn(b"HTTP/1.1 200 OK", client.response)

    def test_response_builder_waits_for_complete_headers(self):
        self.assertIsNone(self.server.build_response(b"GET / HTTP/1.1\r\n"))
        response = self.server.build_response(
            b"GET / HTTP/1.1\r\nHost: logger\r\n\r\n"
        )
        self.assertIn(b"HTTP/1.1 200 OK", b"".join(response))

    def test_reads_declared_body_length(self):
        client = FakeSocket(
            "POST /sensing_off HTTP/1.1\r\n"
            "Host: logger\r\nContent-Length: 4\r\n\r\ntest",
            chunk_size=2,
        )
        self.server.handle_request(client)
        self.assertIn(b"HTTP/1.1 303 See Other", client.response)

    def test_rejects_oversized_headers(self):
        client = FakeSocket(
            "GET / HTTP/1.1\r\nX-Large: " + "x" * 4096 + "\r\n\r\n",
        )
        self.server.handle_request(client)
        self.assertIn(b"HTTP/1.1 413 Payload Too Large", client.response)

    def test_rejects_chunked_request_body(self):
        client = FakeSocket(
            "POST /sensing_off HTTP/1.1\r\n"
            "Transfer-Encoding: chunked\r\n\r\n0\r\n\r\n",
        )
        self.server.handle_request(client)
        self.assertIn(b"HTTP/1.1 501 Not Implemented", client.response)

    def test_post_action_redirects_and_updates_state(self):
        self.time.synchronized = True
        response = self.request("POST", "/sensing_on")
        self.assertIn(b"HTTP/1.1 303 See Other", response)
        self.assertTrue(self.connector.is_enabled())

    def test_rejects_wrong_method(self):
        response = self.request("GET", "/delete_csv")
        self.assertIn(b"HTTP/1.1 405 Method Not Allowed", response)
        self.assertIn(b"Allow: POST", response)

    def test_csv_download(self):
        response = self.request("GET", "/measurements.csv")
        self.assertIn(b"Content-Type: text/csv", response)
        self.assertTrue(response.endswith(b"timestamp,co2\n"))

    def test_measurements_api_returns_chart_data_as_json(self):
        self.time.synchronized = True
        self.connector.start_sensing()
        self.connector.publish(
            (2026, 7, 12, 6, 9, 30, 45, 0),
            512,
            48.5,
            24.3,
        )

        response = self.request("GET", "/api/measurements")
        headers, body = response.split(b"\r\n\r\n", 1)
        payload = json.loads(body.decode("utf-8"))

        self.assertIn(b"Content-Type: application/json", headers)
        self.assertIn(b"Cache-Control: no-store", headers)
        self.assertEqual([512.0], payload["co2"])
        self.assertAlmostEqual(24.3, payload["temperature"][0], places=4)
        self.assertAlmostEqual(48.5, payload["humidity"][0], places=4)
        self.assertEqual([0.0], payload["time_offsets"])
        self.assertEqual(
            [2026, 7, 12, 6, 9, 30, 45, 0],
            payload["latest_timestamp"],
        )
        self.assertTrue(payload["sensing_enabled"])
        self.assertIn("runtime_seconds", payload)
        self.assertGreaterEqual(payload["runtime_seconds"], 0)
        self.assertEqual(
            [2026, 7, 12, 6, 9, 30, 45, 0],
            payload["current_time"],
        )


if __name__ == "__main__":
    unittest.main()
