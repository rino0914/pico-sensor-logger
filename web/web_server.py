try:
    from urllib.parse import unquote_plus
except ImportError:
    def unquote_plus(value):
        return value.replace("+", " ")

try:
    import ujson as json
except ImportError:
    import json

import gc

from web.controller import WebControlService
from web.page_renderer import DashboardPageRenderer
from web.tcp import TcpServer


HTTP_REASONS = {
    204: "No Content", 400: "Bad Request", 404: "Not Found",
    405: "Method Not Allowed", 413: "Payload Too Large",
    500: "Internal Server Error", 501: "Not Implemented",
}

HTTP_HEADER_END = b"\r\n\r\n"
HTTP_READ_CHUNK_SIZE = 512
MAX_HTTP_HEADER_SIZE = 4096
MAX_HTTP_BODY_SIZE = 4096
HTTP_RESPONSE_CHUNK_SIZE = 512


class HttpError(Exception):
    def __init__(self, status_code, message, headers=None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.headers = headers or {}


class WebServer:
    def __init__(
        self,
        connector,
        time_service,
        csv_writer,
        led,
        host="0.0.0.0",
        port=80,
        network_info_provider=None,
    ):
        self.controller = WebControlService(connector, time_service, csv_writer)
        self.page_renderer = DashboardPageRenderer()
        self.led = led
        self.network_info_provider = network_info_provider
        self.tcp_server = TcpServer(self.build_response, host=host, port=port)
        self._routes = self._build_routes()

    @property
    def csv_file_name(self):
        return self.controller.csv_file_name

    def start(self):
        self.tcp_server.start()

    def stop(self):
        self.tcp_server.stop()

    def process_pending(self):
        return self.tcp_server.process_pending()

    def _build_routes(self):
        return {
            "/": {"GET": self._handle_page},
            "/value_send": {"GET": self._handle_page},
            "/api/measurements": {"GET": self._handle_measurements},
            "/set_time": {"POST": self._handle_set_time},
            "/delete_csv": {"POST": self._handle_delete_csv},
            "/sensing_on": {"POST": self._handle_sensing_on},
            "/sensing_off": {"POST": self._handle_sensing_off},
        }

    def handle_request(self, client_socket):
        """블로킹 소켓 기반 호출과 기존 테스트를 위한 호환 진입점."""
        try:
            raw_request = self._read_request(client_socket)
            response = self.build_response(raw_request)
            if response is not None:
                for chunk in response:
                    client_socket.sendall(chunk)
        except HttpError as error:
            print("HTTP request rejected:", error.message)
            for chunk in self._send_response(
                error.status_code,
                error.message,
                headers=error.headers,
            ):
                client_socket.sendall(chunk)
        except ValueError as error:
            print("HTTP request rejected:", error)
            for chunk in self._send_response(400, str(error)):
                client_socket.sendall(chunk)
        except Exception as error:
            print("HTTP request failed:", error)
            try:
                for chunk in self._send_response(500, "Internal Server Error"):
                    client_socket.sendall(chunk)
            except Exception as send_error:
                print("HTTP error response failed:", send_error)
        finally:
            client_socket.close()
            gc.collect()

    def build_response(self, raw_request):
        """완성된 요청에는 응답 iterable, 미완성 요청에는 None을 반환한다."""
        try:
            raw_request = self._extract_complete_request(raw_request)
            if raw_request is None:
                return None

            method, request_path, query = self._parse_request(raw_request)
            print("HTTP request:", method, request_path)

            if request_path == "/" + self.csv_file_name:
                if method != "GET":
                    raise HttpError(405, "Method Not Allowed", {"Allow": "GET"})
                response = self._send_csv()
            else:
                methods = self._routes.get(request_path)
                if methods is None:
                    raise HttpError(404, "Not Found")
                handler = methods.get(method)
                if handler is None:
                    raise HttpError(
                        405,
                        "Method Not Allowed",
                        {"Allow": ", ".join(methods)},
                    )
                response = handler(query)
        except HttpError as error:
            print("HTTP request rejected:", error.message)
            response = self._send_response(
                error.status_code,
                error.message,
                headers=error.headers,
            )
        except ValueError as error:
            print("HTTP request rejected:", error)
            response = self._send_response(400, str(error))
        except Exception as error:
            print("HTTP request failed:", error)
            response = self._send_response(500, "Internal Server Error")
        return self._collect_after(response)

    @staticmethod
    def _collect_after(response):
        try:
            for chunk in response:
                yield chunk
        finally:
            gc.collect()

    @classmethod
    def _extract_complete_request(cls, raw_request):
        request = raw_request
        header_end = request.find(HTTP_HEADER_END)
        if header_end < 0:
            if len(request) > MAX_HTTP_HEADER_SIZE:
                raise HttpError(413, "HTTP headers too large")
            return None
        if header_end > MAX_HTTP_HEADER_SIZE:
            raise HttpError(413, "HTTP headers too large")

        content_length = cls._parse_content_length(bytes(request[:header_end]))
        if content_length > MAX_HTTP_BODY_SIZE:
            raise HttpError(413, "HTTP body too large")
        request_end = header_end + len(HTTP_HEADER_END) + content_length
        if len(request) < request_end:
            return None
        return bytes(request[:request_end])

    @classmethod
    def _read_request(cls, client_socket):
        request = bytearray()
        header_end = -1

        while header_end < 0:
            chunk = client_socket.recv(HTTP_READ_CHUNK_SIZE)
            if not chunk:
                raise HttpError(400, "Incomplete HTTP headers")
            request.extend(chunk)
            header_end = request.find(HTTP_HEADER_END)
            if header_end < 0 and len(request) > MAX_HTTP_HEADER_SIZE:
                raise HttpError(413, "HTTP headers too large")

        if header_end > MAX_HTTP_HEADER_SIZE:
            raise HttpError(413, "HTTP headers too large")

        content_length = cls._parse_content_length(bytes(request[:header_end]))
        if content_length > MAX_HTTP_BODY_SIZE:
            raise HttpError(413, "HTTP body too large")

        request_end = header_end + len(HTTP_HEADER_END) + content_length
        while len(request) < request_end:
            chunk = client_socket.recv(min(
                HTTP_READ_CHUNK_SIZE,
                request_end - len(request),
            ))
            if not chunk:
                raise HttpError(400, "Incomplete HTTP body")
            request.extend(chunk)

        return bytes(request[:request_end])

    @staticmethod
    def _parse_content_length(header_bytes):
        content_lengths = []
        transfer_encoding = None

        for raw_line in header_bytes.split(b"\r\n")[1:]:
            name, separator, value = raw_line.partition(b":")
            if not separator:
                raise HttpError(400, "Malformed HTTP header")
            name = name.strip().lower()
            value = value.strip().lower()
            if name == b"content-length":
                content_lengths.append(value)
            elif name == b"transfer-encoding":
                transfer_encoding = value

        if transfer_encoding is not None:
            raise HttpError(501, "Transfer-Encoding is not supported")
        if len(content_lengths) > 1:
            raise HttpError(400, "Duplicate Content-Length")
        if not content_lengths:
            return 0

        try:
            content_length = int(content_lengths[0])
        except ValueError:
            raise HttpError(400, "Invalid Content-Length")
        if content_length < 0:
            raise HttpError(400, "Invalid Content-Length")
        return content_length

    def _handle_page(self, query):
        return self._send_page()

    def _handle_set_time(self, query):
        self.controller.synchronize_time(query)
        return self._send_response(204, b"")

    def _handle_measurements(self, query):
        body = json.dumps(self.controller.measurements_payload())
        return self._send_response(
            200,
            body,
            "application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )

    def _handle_delete_csv(self, query):
        self.controller.delete_csv()
        return self._send_redirect("/")

    def _handle_sensing_on(self, query):
        if self.controller.start_sensing():
            self._set_led(True)
        return self._send_redirect("/")

    def _handle_sensing_off(self, query):
        self.controller.stop_sensing()
        self._set_led(False)
        return self._send_redirect("/")

    def _send_page(self):
        gc.collect()
        payload = self.controller.dashboard_payload()
        payload["network_info"] = self._get_network_info()
        page = self.page_renderer.render(payload)
        return self._send_streaming_text_response(
            200,
            page,
            "text/html; charset=utf-8",
        )

    def _send_streaming_text_response(
        self,
        status_code,
        text,
        content_type,
    ):
        # Connection-close framing avoids allocating a second full-size UTF-8
        # copy of the dashboard page on memory-constrained MicroPython boards.
        yield self._send_headers(status_code, content_type, None)
        for offset in range(0, len(text), HTTP_RESPONSE_CHUNK_SIZE):
            chunk = text[offset:offset + HTTP_RESPONSE_CHUNK_SIZE]
            yield chunk.encode("utf-8")

    def _get_network_info(self):
        if self.network_info_provider is None:
            return {
                "mode": "unknown",
                "ssid": "-",
                "ip_address": "-",
                "connected": False,
            }
        return self.network_info_provider.get_network_info()

    def _send_csv(self):
        filename = self.controller.prepare_csv_download()
        headers = {"Content-Disposition": 'attachment; filename="%s"' % filename}
        return self._stream_csv(headers)

    def _stream_csv(self, headers):
        yield self._send_headers(200, "text/csv; charset=utf-8", None, headers)
        for chunk in self.controller.iter_csv_chunks(HTTP_RESPONSE_CHUNK_SIZE):
            yield chunk

    def _send_redirect(self, location):
        return self._send_response(303, b"", headers={"Location": location})

    def _send_response(self, status_code, body, content_type="text/plain; charset=utf-8", headers=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        chunks = [self._send_headers(status_code, content_type, len(body), headers)]
        if body:
            chunks.append(body)
        return chunks

    def _send_headers(self, status_code, content_type, content_length, headers=None):
        reason = HTTP_REASONS.get(status_code, "See Other" if status_code == 303 else "OK")
        lines = ["HTTP/1.1 %d %s" % (status_code, reason), "Connection: close"]
        if content_type:
            lines.append("Content-Type: " + content_type)
        if content_length is not None:
            lines.append("Content-Length: %d" % content_length)
        for name, value in (headers or {}).items():
            lines.append("%s: %s" % (name, value))
        return ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8")

    def _set_led(self, enabled):
        if self.led is None:
            return
        if enabled:
            self.led.on()
        else:
            self.led.off()

    @classmethod
    def _parse_request(cls, raw_request):
        if isinstance(raw_request, bytes):
            raw_request = raw_request.decode("utf-8")
        first_line = raw_request.split("\r\n", 1)[0]
        parts = first_line.split()
        if len(parts) != 3 or not parts[2].startswith("HTTP/"):
            raise HttpError(400, "Malformed HTTP request")
        method, target = parts[0].upper(), parts[1]
        path, separator, query_string = target.partition("?")
        if not path.startswith("/"):
            raise HttpError(400, "Malformed request target")
        query = cls._parse_query(query_string) if separator else {}
        return method, path, query

    @staticmethod
    def _parse_query(query_string):
        query = {}
        if not query_string:
            return query
        for pair in query_string.split("&"):
            key, separator, value = pair.partition("=")
            if not separator or not key:
                raise ValueError("Invalid query string.")
            query[unquote_plus(key)] = unquote_plus(value)
        return query
