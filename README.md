# PTL Sensor Logger

## 보드별 AP SSID

AP 모드의 `wifi.ap.ssid`는 완성된 이름이 아니라 공통 접두사입니다.

```json
"ssid": "pico_science_"
```

실행할 때 `machine.unique_id()` 전체를 해시한 Base36 두 자리 접미사를
자동으로 붙입니다. 같은 보드는 재부팅해도 같은 접미사를 사용합니다.

```text
pico_science_7k
pico_science_m3
```

접미사는 AP 모드에만 적용되며 Station 모드의 공유기 SSID에는 적용되지
않습니다. 접미사 두 자리를 포함한 최종 SSID는 32자를 넘을 수 없으므로
설정의 AP 접두사는 최대 30자까지 허용됩니다.

## SCD40 및 QWIIC 연결

ROBO-PICO 보드에서 QWIIC / Stemma QT 커넥터는 `Maker Port`입니다.
이 포트는 Grove 2번과 동일한 `GP2`, `GP3` 핀을 공유합니다. 따라서
SCD40을 변환 케이블 없이 QWIIC 커넥터에 직접 연결할 때는 다음과 같이
Grove 포트 2번을 설정합니다.

```json
"sensor": {
  "grove_port": 2
}
```

ROBO-PICO 데이터시트의 Grove 포트 GPIO 및 I2C 지원 여부는 다음과
같습니다.

| Grove 포트 | GPIO 핀 쌍 | 하드웨어 I2C | 참고 |
|---|---|---|---|
| 1 | GP0 / GP1 | I2C0 | Grove 단자 |
| 2 | GP2 / GP3 | I2C1 | Maker/QWIIC 포트와 공유 |
| 3 | GP4 / GP5 | I2C0 | Grove 단자 |
| 4 | GP16 / GP17 | I2C0 | Grove 단자 |
| 5 | GP6 / GP26 | 완전한 I2C 쌍이 아님 | SCD40 비권장 |
| 6 | GP26 / GP27 | I2C1 | Grove 단자 |
| 7 | GP7 / GP28 | 완전한 I2C 쌍이 아님 | SCD40 비권장 |

변환 케이블이 없다면 QWIIC 센서를 물리적으로 연결할 수 있는 포트는
Maker/QWIIC 포트 하나이며 설정값은 `2`입니다. Grove 1, 3, 4, 6번도
I2C를 지원하지만 QWIIC 센서를 연결하려면 Grove-QWIIC 변환 케이블이
필요합니다.

여러 QWIIC 센서는 센서의 보조 QWIIC 단자 또는 QWIIC 허브로 같은
버스에 연결할 수 있습니다. 이 경우 동일한 I2C 주소를 사용하는 장치끼리는
주소 충돌이 발생할 수 있습니다. SCD40의 기본 I2C 주소는 `0x62`입니다.

Raspberry Pi Pico W와 SCD40 센서를 이용해 교실의 CO₂, 온도, 습도를 측정하고 CSV로 저장하는 탐구·실험용 데이터 로거입니다.

Pico W는 비밀번호 없는 액세스 포인트를 만들거나 기존 Wi-Fi에 Station으로 접속한 뒤 웹 서버를 실행합니다. 학생은 스마트폰으로 실시간 측정값과 그래프를 확인하고, 측정을 제어하거나 CSV 파일을 내려받을 수 있습니다.

## 주요 기능

- SCD40의 CO₂·온도·습도 측정
- 최근 200개 측정값을 JSON으로 받아 브라우저에서 그리는 대화형 SVG 그래프
- 실제 측정 시간과 단위별 세부 눈금을 표시하는 센서별 정밀 그래프
- 초기값 대비 변화율로 CO₂·온도·습도 추이를 비교하는 통합 그래프
- 마우스와 터치로 특정 시점의 정확한 측정값을 확인하는 툴팁
- 모바일 중심의 반응형 다크 테마 대시보드
- Station 모드의 NTP 자동 동기화와 브라우저를 이용한 수동 RTC 동기화
- 대시보드에서 현재 Pico RTC 시각 표시
- 측정 시작·중지 및 데이터 초기화
- 측정값 CSV 저장 및 다운로드
- 대시보드에서 현재 Wi-Fi 모드, SSID, IP 주소와 연결 상태 표시
- 저장 큐 초과 시 오래된 미저장 데이터 제거와 누락 횟수 표시
- BOOTSEL 버튼을 이용한 안전한 애플리케이션 종료

## 사용 흐름

1. Pico W와 SCD40을 연결하고 `main.py`를 실행합니다.
2. AP 모드라면 스마트폰을 `config.json`의 SSID에 연결합니다. Station 모드라면 스마트폰과 Pico W를 같은 Wi-Fi에 연결합니다.
3. 브라우저에서 AP 모드는 `http://192.168.4.1`, Station 모드는 시리얼 콘솔에 출력된 IP 주소를 엽니다.
4. AP 모드에서는 `시간 동기화`를 먼저 누릅니다. Station 모드는 부팅할 때 NTP 동기화를 자동으로 시도합니다.
5. `측정 시작`을 눌러 실험을 시작합니다.
6. 그래프를 관찰하거나 `CSV 받기`로 결과를 내려받습니다.
7. 실험이 끝나면 `측정 중지`를 누릅니다.

시간을 동기화하지 않으면 측정을 시작할 수 없습니다. Station 모드에서 NTP 동기화에 실패하면 대시보드의 `시간 동기화`를 누릅니다. AP 모드는 Pico가 재부팅될 때마다 브라우저로 다시 동기화해야 합니다.

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
    "mode": "ap",
    "ap": {
      "ssid": "pico_science_",
      "network": {
        "ip": "192.168.4.1",
        "netmask": "255.255.255.0",
        "gateway": "192.168.4.1",
        "dns": "8.8.8.8"
      }
    },
    "station": {
      "ssid": "CLASSROOM_WIFI",
      "password": "wifi-password",
      "connect_timeout_seconds": 15
    }
  },
  "sensor": {
    "grove_port": 2
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

AP와 Station 설정은 각각 `wifi.ap`와 `wifi.station`에 보관합니다. 두 프로필을 한 번 설정한 후에는 `wifi.mode`만 `ap` 또는 `station`으로 변경하면 됩니다. 실행 시 선택된 프로필만 검증하므로 사용하지 않는 Station 프로필의 SSID와 비밀번호는 비워 둘 수 있습니다.

AP 모드는 비밀번호 없이 개방형으로 동작합니다. 주변 사용자는 누구나 접속하고 측정을 제어할 수 있으므로 통제된 실험 환경에서 사용해야 합니다.

Station 모드로 전환하려면 위 설정의 `mode`를 `station`으로 바꿉니다. Station 모드는 공유기의 DHCP를 사용하며, 연결되면 시리얼 콘솔에 웹 서버 접속용 IP 주소를 출력합니다.

Station 비밀번호는 8자 이상 64자 이하여야 하며 접속 제한 시간은 0초보다 크고 최대 120초입니다. 학교 Wi-Fi가 웹 로그인이나 WPA2-Enterprise 인증을 요구한다면 일반 SSID와 비밀번호만으로 접속하지 못할 수 있습니다. CSV 필드 이름과 순서는 AP와 Station 모드 모두 위 예시와 동일해야 합니다.

Station 모드는 Wi-Fi 연결 후 `pool.ntp.org`에서 시간을 받아 한국 표준시(UTC+9)로 RTC를 설정합니다. NTP 서버, UDP 포트, 요청 제한 시간과 UTC 오프셋은 `core/ntp_client.py`의 상수로 관리합니다. 네트워크에서 NTP용 UDP 123 포트를 차단하거나 인터넷 연결이 없으면 자동 동기화는 실패하며, 이때는 기존 브라우저 시간 동기화를 사용할 수 있습니다.

## 그래프 해석

센서별 정밀 그래프의 X축은 최신 측정을 기준으로 한 실제 경과 시간이며, 측정 간격이 길어진 구간은 그래프에서도 더 넓게 표시됩니다. Y축은 CO₂ `ppm`, 온도 `°C`, 상대습도 `%`의 실제 측정값을 각각 6개 눈금으로 표시합니다.

통합 그래프는 단위와 값의 크기가 서로 다른 세 센서를 한 축에서 비교하기 위해 각 센서의 첫 측정값을 `0%`로 둔 변화율을 사용합니다. 따라서 통합 그래프는 절대값 비교가 아니라 변화 방향과 상대적인 증감 폭을 해석하는 용도이며, 정확한 값은 센서별 그래프와 범례에서 확인해야 합니다.

그래프 위에서 마우스를 움직이거나 터치하면 가장 가까운 측정 시점에 세로선과 선택점이 표시됩니다. 툴팁에서 해당 시점의 경과 시간과 센서 측정값을 확인할 수 있습니다. 그래프는 페이지 전체를 새로고침하지 않고 `/api/measurements`에서 5초마다 최신 데이터를 가져와 갱신합니다.

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
| `/api/measurements` | GET | 최근 측정 시간과 CO₂·온도·습도 JSON 반환 |
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
  ntp_client.py                 Station 모드 NTP 시간 조회
  sensor_data.py                최근 측정값 원형 버퍼와 통계
  time_service.py               RTC 동기화와 현재 시각 제공

devices/
  ap.py                         Pico W 액세스 포인트
  station.py                    기존 Wi-Fi Station 접속
  wifi.py                       설정에 따른 Wi-Fi 모드 생성
  scd40.py                      SCD40 I²C 드라이버와 CRC 검증
  scd40_thread.py               센서 측정 스레드

storage/
  filemanager.py                파일 접근과 CSV 저장

web/
  tcp.py                        non-blocking TCP accept 폴링
  web_server.py                 HTTP 파싱, 라우팅, 응답
  controller.py                 웹 요청과 애플리케이션 상태 연결
  page_renderer.py              모바일 대시보드 HTML 렌더링
  chart_client.py               브라우저 SVG 그래프와 툴팁 JavaScript

tests/
  test_ap.py                    개방형 AP 시작 및 종료 테스트
  test_config_loader.py         AP/Station 설정 검증 테스트
  test_ntp_client.py            NTP 요청과 UTC+9 변환 테스트
  test_station.py               Station 접속, 실패, 시간초과 테스트
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
python3 -B run_tests.py
```

macOS에서 Python 캐시 권한 오류가 발생하면 임시 캐시 경로를 지정할 수 있습니다.

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ptl-pyc \
python3 -m unittest discover -s tests -v
```

현재 테스트는 AP/Station 네트워크 설정과 생명주기, 측정 데이터 JSON API, HTTP 분할 수신, `Content-Length`, 요청 크기 제한, 지원하지 않는 chunked 요청, 라우팅, 시간 동기화, 측정 제어, CSV 다운로드와 대시보드 렌더링을 검사합니다.

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
- 그래프 데이터는 브라우저에서 5초마다 갱신합니다.
- 실제 Pico W 펌웨어에서 Wi-Fi, 소켓 timeout, SCD40 배선과 센서 응답을 최종 확인해야 합니다.
