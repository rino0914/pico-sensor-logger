from time import sleep

from tcp import TcpServer


HTML_HEAD = """<!DOCTYPE html>
<html>
<head>
  <title>Pico W 서버</title>
  <meta charset="utf-8">
  <meta http-equiv="Refresh" content="6;URL=./value_send">
  <meta name="viewport" content="initial-scale=1.0,user-scalable=no,maximum-scale=1,width=device-width">
  <link rel="icon" href="data:,">
</head>
"""

PAGE_TEMPLATE = """
<body style="font-size:1.0em"> <h1> 무선피코(SCD40) </h1>
<font size="2em" color="green">
  <div>
    <form class="form1" action="./delete_csv" method="POST">
      <input style="font-size:1.2em" type="submit" value="기존 데이터 삭제" onclick="if(!confirm('정말로 삭제하시겠습니까??')){return false;}" />
    </form>
    <br>
    <form class="form1" action="./sensing_on" method="POST">
      <input style="font-size:1.2em" type="submit" value="측정 시작" />
    </form>
    <br>
    <form class="form1" action="./value_send" method="POST">
      <input style="font-size:1.2em" type="submit" value="측정값 확인" />
    </form>
  </div>
  <br>
  <div>
    <form class="form2" action="./%s" method="POST">
      <a href="/%s" download="%s">
      <input style="font-size:1.2em" type="submit" value=" %s 파일 다운로드(항상 가능)" />
      </a>
      <p>※ 다운로드 후, '측정값 확인'을 눌러야 '자동 새로고침' 기능 복구됨</p>
    </form>
    <br>
    <form class="form2" action="./sensing_off" method="POST">
      <input style="font-size:1.2em" type="submit" value="측정 멈춤" onclick="if(!confirm('정말로 중지하시겠습니까??')){return false;}" />
    </form>
  </div>
  <p style="font-size:1.1em">현재 상태: %s </p>
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


class WebServer:
    def __init__(
        self,
        histories,
        sensing_state,
        rtc,
        led,
        file_lock,
        data_lock,
        csv_file_name,
        csv_header,
        host="0.0.0.0",
        port=80,
    ):
        self.histories = histories
        self.sensing_state = sensing_state
        self.rtc = rtc
        self.led = led
        self.file_lock = file_lock
        self.data_lock = data_lock
        self.csv_file_name = csv_file_name
        self.csv_path = csv_file_name + ".csv"
        self.csv_header = csv_header
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

            request_path = self._parse_request_path(raw_request)
            print("HTTP request:", request_path)

            if request_path == "/delete_csv":
                self._delete_csv()
            elif request_path == "/sensing_on":
                self._start_sensing()
            elif request_path == "/sensing_off":
                self._stop_sensing()
            elif request_path == "/value_send":
                self.state = "측정값 전송"

            if request_path == "/" + self.csv_path:
                self._send_csv(client_socket)
            else:
                self._send_page(client_socket)
        except Exception as error:
            print("HTTP request failed:", error)
        finally:
            client_socket.close()

    @staticmethod
    def _parse_request_path(raw_request):
        try:
            request_line = raw_request.split(b"\r\n", 1)[0]
            return request_line.split()[1].decode()
        except (IndexError, UnicodeError):
            raise ValueError("Invalid HTTP request line")

    def _delete_csv(self):
        if self.sensing_state.enabled:
            return

        self.file_lock.acquire()
        try:
            with open(self.csv_path, "w") as csv_file:
                csv_file.write(self.csv_header + "\n")
        finally:
            self.file_lock.release()

        self.data_lock.acquire()
        try:
            for history in self.histories:
                history.clear()
        finally:
            self.data_lock.release()

        self.state = "기존 데이터 파일 삭제되었음"

    def _start_sensing(self):
        if self.sensing_state.enabled:
            return

        self.rtc.datetime((2024, 6, 3, 1, 0, 0, 0, 0))
        self.data_lock.acquire()
        try:
            self.sensing_state.enabled = True
        finally:
            self.data_lock.release()
        self.state = "측정중"

    def _stop_sensing(self):
        self.data_lock.acquire()
        try:
            self.sensing_state.enabled = False
        finally:
            self.data_lock.release()
        self.state = "측정 멈춤"

    def _send_csv(self, client_socket):
        self.state = "데이터파일 전송"
        client_socket.send(
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/csv\r\n"
            "Connection: close\r\n\r\n"
        )

        self.file_lock.acquire()
        try:
            with open(self.csv_path, "r") as csv_file:
                for line in csv_file:
                    client_socket.send(line)
        finally:
            self.file_lock.release()

    def _send_page(self, client_socket):
        self.led.off()
        self.data_lock.acquire()
        try:
            minimum_ranges = (50.0, 3.0, 10.0)
            for history, minimum_range in zip(
                self.histories,
                minimum_ranges,
            ):
                history.calculate_chart_scale(minimum_range)

            paths = tuple(
                history.build_svg_path()
                for history in self.histories
            )
            sensor_values = tuple(
                str(history.latest_value())
                for history in self.histories
            )
            first_history = self.histories[0]
            third_history = self.histories[2]
            chart_values = (
                first_history.chart_min_value + first_history.chart_step,
                first_history.chart_min_value + first_history.chart_step * 2,
                first_history.chart_min_value + first_history.chart_step * 3,
                third_history.chart_min_value + third_history.chart_step,
                third_history.chart_min_value + third_history.chart_step * 2,
                third_history.chart_min_value + third_history.chart_step * 3,
            )
        finally:
            self.data_lock.release()
            self.led.on()

        page = PAGE_TEMPLATE % (
            self.csv_path,
            self.csv_path,
            self.csv_file_name,
            self.csv_path,
            self.state,
            sensor_values[0],
            sensor_values[1],
            sensor_values[2],
        )
        chart = CHART_TEMPLATE % chart_values

        client_socket.send(
            "HTTP/1.0 200 OK\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            "Connection: close\r\n\r\n"
        )
        client_socket.send(HTML_HEAD)
        client_socket.send(page)
        client_socket.send(chart)
        client_socket.send(paths[0])
        sleep(0.2)
        client_socket.send(SECOND_PATH)
        client_socket.send(paths[1])
        sleep(0.2)
        client_socket.send(THIRD_PATH)
        client_socket.send(paths[2])
        client_socket.sendall(HTML_END)
