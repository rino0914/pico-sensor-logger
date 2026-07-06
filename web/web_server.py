from web.chart import SensorChartRenderer
from web.tcp import TcpServer


HTML_HEAD = """<!DOCTYPE html>
<html>
<head>
  <title>Pico W 서버</title>
  <meta charset="utf-8">
  <meta http-equiv="Refresh" content="6;URL=/value_send">
  <meta name="viewport" content="initial-scale=1.0,user-scalable=no,maximum-scale=1,width=device-width">
  <link rel="icon" href="data:,">
"""

HTML_HEAD_END = "</head>\n"

TIME_SYNC_SCRIPT = """
  <script>
  document.addEventListener("DOMContentLoaded", function () {
    const now = new Date();
    const params = new URLSearchParams({
      year: now.getFullYear(),
      month: now.getMonth() + 1,
      day: now.getDate(),
      weekday: (now.getDay() + 6) % 7,
      hour: now.getHours(),
      minute: now.getMinutes(),
      second: now.getSeconds()
    });
    fetch("/set_time?" + params.toString(), {method: "POST"})
      .then(function (response) {
        if (response.ok) {
          window.location.replace("/");
        }
      })
      .catch(function () {});
  });
  </script>
"""

PAGE_TEMPLATE = """
<body style="font-size:1.0em"> <h1> 무선피코(SCD40) </h1>
<font size="2em" color="green">
  <div>
    <form class="form1" action="/delete_csv" method="POST">
      <input style="font-size:1.2em" type="submit" value="기존 데이터 삭제" onclick="if(!confirm('정말로 삭제하시겠습니까??')){return false;}" />
    </form>
    <br>
    <form class="form1" action="/sensing_on" method="POST">
      <input style="font-size:1.2em" type="submit" value="측정 시작" />
    </form>
    <br>
    <form class="form1" action="/value_send" method="GET">
      <input style="font-size:1.2em" type="submit" value="측정값 확인" />
    </form>
  </div>
  <br>
  <div>
    <a href="/%s" download="%s" style="font-size:1.2em">%s 파일 다운로드</a>
    <br>
    <form class="form2" action="/sensing_off" method="POST">
      <input style="font-size:1.2em" type="submit" value="측정 멈춤" onclick="if(!confirm('정말로 중지하시겠습니까??')){return false;}" />
    </form>
  </div>
  <p style="font-size:1.1em">현재 상태: %s </p>
  <p style="font-size:1.0em">마지막 측정: %s</p>
  <p style="font-size:1.0em">데이터 최신성: %s</p>
  <p style="font-size:1.0em">파일 저장 대기: %s개 / 유실: %s개</p>
  <p style="font-size:1.1em; color: red;">CO2(I2C0) = %s [ppm]</p>
  <p style="font-size:1.1em; color: blue;">온도 = %s [C]</p>
  <p style="font-size:1.1em; color: #DAA520;">습도 = %s [percent]</p>
  ※ 그래프는 가장 최근에 측정한 200개 데이터만 표시됩니다.
  <br>
"""

CHART_TEMPLATE = """<svg class="plt" width="500" height="300" viewBox="0 0 500 300">
<style>
.plt{stroke-linecap:round;stroke-linejoin:round;font-family:Roboto,sans-serif;font-size:16px;}
.plt_background{fill:#262626;}
.plt_text{fill:orangered;}
.plt_text2{fill:gold;}
.plt_grid{stroke:gray;stroke-width:0.5;}
.plt_line{stroke-dasharray:2;stroke-width:2;}
</style>
<circle r="1e5" class="plt_background" fill="white"/>
<text class="plt_text" x="10" y="225"> %3.1f </text>
<text class="plt_text" x="10" y="150"> %3.1f </text>
<text class="plt_text" x="10" y="75"> %3.1f </text>
<text class="plt_text2" x="450" y="225"> %3.1f </text>
<text class="plt_text2" x="450" y="150"> %3.1f </text>
<text class="plt_text2" x="450" y="75"> %3.1f </text>
<g id="plt_plot0" class="plt_line" fill="none" stroke="orangered"><path d="""

SECOND_PATH = """"/>
</g>
<g id="plt_plot1" class="plt_line" fill="none" stroke="deepskyblue"><path d="""

THIRD_PATH = """"/>
</g>
<g id="plt_plot2" class="plt_line" fill="none" stroke="gold"><path d="""

HTML_END = """"/>
</g>
<g class="plt_grid plt_y" stroke="red">
<line x1="70" x2="450" y1="75" y2="75"/>
<line x1="70" x2="450" y1="150" y2="150"/>
<line x1="70" x2="450" y1="225" y2="225"/>
</g>
</svg>
</font>
</body>
</html>
"""


class HttpError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message


class WebServer:
    def __init__(
        self,
        connector,
        time_service,
        csv_writer,
        led,
        host="0.0.0.0",
        port=80,
    ):
        self.connector = connector
        self.chart_renderer = SensorChartRenderer()
        self.time_service = time_service
        self.csv_writer = csv_writer
        self.led = led
        self.csv_file_name = csv_writer.file_name
        self.state = "초기화 완료"
        self.tcp_server = TcpServer(
            self.handle_request,
            host = host,
            port = port,
        )

    def start(self):
        self.tcp_server.start()

    def stop(self):
        self.tcp_server.stop()

    def handle_request(self, client_socket):
        try:
            raw_request = client_socket.read()
            if not raw_request:
                return

            # 요청 도착 감지는 non-blocking으로 하고, 응답은 끝까지 전송한다.
            client_socket.setblocking(True)

            method, request_path, query = self._parse_request(raw_request)
            print("HTTP request:", method, request_path)

            if request_path == "/set_time":
                self._require_method(method, "POST")
                self._synchronize_time(query)
                self._send_no_content(client_socket)
                return
            if request_path == "/delete_csv":
                self._require_method(method, "POST")
                self._delete_csv()
                self._send_page(client_socket)
                return
            if request_path == "/sensing_on":
                self._require_method(method, "POST")
                self._start_sensing()
                self._send_page(client_socket)
                return
            if request_path == "/sensing_off":
                self._require_method(method, "POST")
                self._stop_sensing()
                self._send_page(client_socket)
                return
            if request_path == "/" + self.csv_file_name:
                self._require_method(method, "GET")
                self._send_csv(client_socket)
                return
            if request_path in ("/", "/value_send"):
                self._require_method(method, "GET")
                self._send_page(client_socket)
                return

            self._send_error(client_socket, 404, "Not Found")
        except HttpError as error:
            print("HTTP request rejected:", error.message)
            self._try_send_error(
                client_socket,
                error.status_code,
                error.message,
            )
        except ValueError as error:
            print("HTTP request rejected:", error)
            self._try_send_error(client_socket, 400, str(error))
        except Exception as error:
            print("HTTP request failed:", error)
            self._try_send_error(client_socket, 500, "Internal Server Error")
        finally:
            client_socket.close()

    @staticmethod
    def _parse_request(raw_request):
        try:
            request_line = raw_request.split(b"\r\n", 1)[0]
            parts = request_line.split()
            if len(parts) != 3:
                raise ValueError("Invalid HTTP request line")

            method = parts[0].decode()
            target = parts[1].decode()
            if "?" not in target:
                return method, target, {}

            path, query_string = target.split("?", 1)
            query = {}
            for item in query_string.split("&"):
                if "=" in item:
                    key, value = item.split("=", 1)
                    query[key] = value
            return method, path, query
        except (IndexError, UnicodeError):
            raise ValueError("Invalid HTTP request line")

    @staticmethod
    def _require_method(actual, expected):
        if actual != expected:
            raise HttpError(405, "Method Not Allowed")

    def _synchronize_time(self, query):
        required = (
            "year",
            "month",
            "day",
            "weekday",
            "hour",
            "minute",
            "second",
        )
        try:
            values = tuple(int(query[key]) for key in required)
        except (KeyError, ValueError):
            raise ValueError("Invalid time synchronization request")

        self.time_service.synchronize(*values)
        if not self.connector.is_sensing_enabled():
            self.state = "시간 동기화 완료"

    @staticmethod
    def _send_no_content(client_socket):
        client_socket.sendall(
            "HTTP/1.1 204 No Content\r\n"
            "Connection: close\r\n\r\n"
        )

    @staticmethod
    def _send_error(client_socket, status_code, message):
        body = "%d %s" % (status_code, message)
        client_socket.sendall(
            "HTTP/1.1 %d %s\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "Content-Length: %d\r\n"
            "Connection: close\r\n\r\n%s"
            % (
                status_code,
                message,
                len(body.encode("utf-8")),
                body,
            )
        )

    def _try_send_error(self, client_socket, status_code, message):
        try:
            self._send_error(client_socket, status_code, message)
        except Exception:
            pass

    def _delete_csv(self):
        if self.connector.is_sensing_enabled():
            self.state = "측정 중에는 파일을 삭제할 수 없음"
            return

        self.csv_writer.reset()

        self.state = "기존 데이터 파일 삭제되었음"

    def _start_sensing(self):
        if self.connector.is_sensing_enabled():
            return

        if not self.time_service.is_synchronized():
            self.state = "시간 동기화 후 측정을 시작하세요"
            return

        self.connector.start_sensing()
        self.state = "측정중"

    def _stop_sensing(self):
        self.connector.stop_sensing()
        self.state = "측정 멈춤"

    def _send_csv(self, client_socket):
        self.state = "데이터파일 전송"
        # 다운로드 시작 시점까지 큐에 들어온 데이터를 먼저 파일에 반영한다.
        self.csv_writer.flush()
        client_socket.sendall(
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/csv\r\n"
            "Content-Disposition: attachment; filename=\"%s\"\r\n"
            "Cache-Control: no-store\r\n"
            "Connection: close\r\n\r\n"
            % self.csv_file_name
        )

        self.csv_writer.send_to(client_socket)

    def _send_page(self, client_socket):
        self.led.off()
        try:
            data_snapshot = self.connector.snapshot()
            series = data_snapshot.series
            minimum_ranges = (50.0, 3.0, 10.0)
            scales = tuple(
                self.chart_renderer.calculate_chart_scale(
                    values,
                    minimum_range,
                )
                for values, minimum_range in zip(
                    series,
                    minimum_ranges,
                )
            )
            paths = tuple(
                self.chart_renderer.build_svg_path(values, scale)
                for values, scale in zip(series, scales)
            )
            sensor_values = tuple(
                str(values[-1] if values else 0.0)
                for values in series
            )
            first_scale = scales[0]
            third_scale = scales[2]
            chart_values = (
                first_scale.chart_min_value + first_scale.chart_step,
                first_scale.chart_min_value + first_scale.chart_step * 2,
                first_scale.chart_min_value + first_scale.chart_step * 3,
                third_scale.chart_min_value + third_scale.chart_step,
                third_scale.chart_min_value + third_scale.chart_step * 2,
                third_scale.chart_min_value + third_scale.chart_step * 3,
            )
            if data_snapshot.latest_timestamp is None:
                latest_time = "측정값 없음"
                freshness = "측정값 없음"
            else:
                latest_time = self._format_timestamp(
                    data_snapshot.latest_timestamp
                )
                freshness = "%d초 전 (%s)" % (
                    data_snapshot.age_ms // 1000,
                    "오래됨" if data_snapshot.is_stale else "정상",
                )
        finally:
            self.led.on()

        page = PAGE_TEMPLATE % (
            self.csv_file_name,
            self.csv_file_name,
            self.csv_file_name,
            self.state,
            latest_time,
            freshness,
            self.csv_writer.pending_count(),
            data_snapshot.dropped_count,
            sensor_values[0],
            sensor_values[1],
            sensor_values[2],
        )
        chart = CHART_TEMPLATE % chart_values

        client_socket.sendall(
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            "Cache-Control: no-store\r\n"
            "Connection: close\r\n\r\n"
        )
        client_socket.sendall(HTML_HEAD)
        if not self.time_service.is_synchronized():
            client_socket.sendall(TIME_SYNC_SCRIPT)
        client_socket.sendall(HTML_HEAD_END)
        client_socket.sendall(page)
        client_socket.sendall(chart)
        client_socket.sendall(paths[0])
        client_socket.sendall(SECOND_PATH)
        client_socket.sendall(paths[1])
        client_socket.sendall(THIRD_PATH)
        client_socket.sendall(paths[2])
        client_socket.sendall(HTML_END)

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
