# PTL Sensor Logger

Raspberry Pi Pico W와 SCD40 센서를 이용해 교실의 CO₂, 온도, 습도를 측정하고 CSV로 저장하는 탐구·실험용 데이터 로거입니다.

Pico W가 자체 Wi-Fi 액세스 포인트와 웹 서버를 실행합니다. 학생은 스마트폰으로 Pico W에 접속해 실시간 측정값과 그래프를 확인하고, 측정을 제어하거나 CSV 파일을 내려받을 수 있습니다.

## 주요 기능

- SCD40의 CO₂·온도·습도 측정
- 최근 200개 측정값의 통계 및 SVG 그래프 표시
- 모바일 중심의 반응형 다크 테마 대시보드
- 브라우저 시간을 이용한 Pico RTC 동기화
- 측정 시작·중지 및 데이터 초기화
- 측정값 CSV 저장 및 다운로드
- 저장 큐 초과 시 오래된 미저장 데이터 제거와 누락 횟수 표시
- BOOTSEL 버튼을 이용한 안전한 애플리케이션 종료

## 사용 흐름

1. Pico W와 SCD40을 연결하고 `main.py`를 실행합니다.
2. 스마트폰에서 `config.json`에 설정한 Wi-Fi SSID에 연결합니다.
3. 브라우저에서 `http://192.168.4.1`을 엽니다.
4. `시간 동기화`를 먼저 누릅니다.
5. `측정 시작`을 눌러 실험을 시작합니다.
6. 그래프를 관찰하거나 `CSV 받기`로 결과를 내려받습니다.
7. 실험이 끝나면 `측정 중지`를 누릅니다.

시간을 동기화하지 않으면 측정을 시작할 수 없습니다. Pico가 재부팅되면 시간을 다시 동기화해야 합니다.

## 하드웨어 구성

| 항목 | 설정 |
|---|---|
| 보드 | Raspberry Pi Pico W |
| 센서 | Sensirion SCD40 |
| I²C 버스 | I²C 0 |
| SDA | GPIO 8 |
| SCL | GPIO 9 |
| I²C 주파수 | 100 kHz |
| 센서 상태 LED | GPIO 1 |
| 시스템 상태 LED | Pico W 내장 LED |

SCD40의 기본 I²C 주소는 `0x62`입니다.

## 설정

실행 설정은 `config.json`에서 관리합니다.

```json
{
  "wifi": {
    "ssid": "Pico_Science_01",
    "password": "12345678",
    "network": {
      "ip": "192.168.4.1",
      "netmask": "255.255.255.0",
      "gateway": "192.168.4.1",
      "dns": "8.8.8.8"
    }
  },
  "logfile": {
    "filename": "data-SCD40-1.csv",
    "field_names": [
      "timestamp",
      "CO2(ppm)",
      "temperature(°C)",
      "humidity(%)"
    ]
  }
}
```

Wi-Fi 비밀번호는 8자 이상 64자 이하여야 합니다. CSV 필드 이름과 순서는 위 예시와 동일해야 합니다.

## CSV 형식

측정값은 다음 형식으로 저장됩니다.

```csv
timestamp,CO2(ppm),temperature(°C),humidity(%)
2026-07-11 14:30:09,512,24.5,51.2
```

저장 대기 큐는 기본 32개입니다. 큐가 가득 차면 가장 오래된 미저장 레코드를 버리고 대시보드의 `누락` 횟수를 증가시킵니다.

## 웹 요청

| 경로 | 메서드 | 기능 |
|---|---|---|
| `/` | GET | 대시보드 표시 |
| `/value_send` | GET | 대시보드 갱신용 페이지 표시 |
| `/set_time` | POST | query string으로 RTC 동기화 |
| `/sensing_on` | POST | 측정 시작 |
| `/sensing_off` | POST | 측정 중지 |
| `/delete_csv` | POST | 측정 중이 아닐 때 CSV 초기화 |
| `/<CSV 파일명>` | GET | CSV 다운로드 |

HTTP 서버는 분할 수신을 지원하며 헤더와 본문을 각각 최대 4KB까지 받습니다. `Content-Length` 본문은 지원하지만 `Transfer-Encoding: chunked`는 지원하지 않습니다.

## 프로젝트 구조

```text
main.py                         애플리케이션 진입점과 생명주기 관리
config.json                     Wi-Fi, 네트워크, CSV 설정
config_loader.py                설정 로딩 및 검증
generate_dashboard_preview.py   로컬 대시보드 미리보기 생성

core/
  data_connector.py             센서 데이터, 저장 큐, 런타임 상태 연결
  sensor_data.py                최근 측정값 원형 버퍼와 통계
  time_service.py               RTC 동기화와 현재 시각 제공

devices/
  ap.py                         Pico W 액세스 포인트
  scd40.py                      SCD40 I²C 드라이버와 CRC 검증
  scd40_thread.py               센서 측정 스레드

storage/
  filemanager.py                파일 접근과 CSV 저장

web/
  tcp.py                        non-blocking TCP accept 폴링
  web_server.py                 HTTP 파싱, 라우팅, 응답
  controller.py                 웹 요청과 애플리케이션 상태 연결
  page_renderer.py              모바일 대시보드 HTML 렌더링
  chart.py                      SVG 그래프 좌표와 경로 생성

tests/
  test_web.py                   HTTP 및 대시보드 테스트
```

각 패키지의 `__init__.py`는 패키지 구분과 설명만 담당합니다. 클래스와 함수는 실제 모듈에서 직접 import합니다.

## 로컬 대시보드 미리보기

Pico 없이 샘플 센서 데이터로 화면을 확인할 수 있습니다.

```bash
python3 generate_dashboard_preview.py
```

생성된 `dashboard_preview.html`을 브라우저에서 열면 됩니다. 이 파일은 미리보기 결과이며 실제 Pico에서는 `web/page_renderer.py`가 현재 측정값으로 페이지를 생성합니다.

## 테스트

프로젝트 루트에서 전체 테스트를 실행합니다.

```bash
python3 -m unittest discover -s tests -v
```

macOS에서 Python 캐시 권한 오류가 발생하면 임시 캐시 경로를 지정할 수 있습니다.

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ptl-pyc \
python3 -m unittest discover -s tests -v
```

현재 테스트는 HTTP 분할 수신, `Content-Length`, 요청 크기 제한, 지원하지 않는 chunked 요청, 라우팅, 시간 동기화, 측정 제어, CSV 다운로드와 대시보드 렌더링을 검사합니다.

## Pico W 배포

다음 파일과 디렉터리를 Pico W의 MicroPython 파일시스템에 복사합니다.

```text
main.py
config.json
config_loader.py
core/
devices/
storage/
web/
```

`tests/`, `generate_dashboard_preview.py`, `dashboard_preview.html`은 장치 실행에 필요하지 않습니다.

## 구현 제한사항

- HTTP/1.1의 기본 요청만 처리하며 keep-alive와 chunked body는 지원하지 않습니다.
- 한 번에 하나의 HTTP 클라이언트를 처리합니다.
- 클라이언트 요청 제한 시간은 1초입니다.
- 웹 페이지는 10초마다 자동 갱신됩니다.
- 실제 Pico W 펌웨어에서 Wi-Fi, 소켓 timeout, SCD40 배선과 센서 응답을 최종 확인해야 합니다.
