"""샘플 센서 데이터로 대시보드 미리보기 HTML을 생성한다."""

import math
import json

from web.page_renderer import DashboardPageRenderer


OUTPUT_FILE = "dashboard_preview.html"


class PreviewSnapshot:
    def __init__(self):
        points = range(80)
        self.series = (
            [620 + 70 * math.sin(point / 8) for point in points],
            [24.5 + 1.8 * math.sin(point / 11) for point in points],
            [48 + 5 * math.cos(point / 10) for point in points],
        )
        self.time_offsets = tuple(point * 5.0 for point in points)
        self.latest_timestamp = (2026, 7, 11, 6, 14, 30, 0, 0)
        self.age_ms = 2_400
        self.is_stale = False
        self.pending_count = 3
        self.dropped_count = 0
        self.sensing_enabled = True
        self.runtime_seconds = 754


def main():
    snapshot = PreviewSnapshot()
    preview_measurements = {
        "time_offsets": snapshot.time_offsets,
        "co2": snapshot.series[0],
        "temperature": snapshot.series[1],
        "humidity": snapshot.series[2],
        "latest_timestamp": snapshot.latest_timestamp,
        "age_ms": snapshot.age_ms,
        "is_stale": snapshot.is_stale,
        "sensing_enabled": snapshot.sensing_enabled,
        "runtime_seconds": snapshot.runtime_seconds,
        "pending_count": snapshot.pending_count,
        "dropped_count": snapshot.dropped_count,
        "time_synchronized": True,
        "current_time": [2026, 7, 12, 6, 9, 30, 45, 0],
    }
    payload = {
        "data_snapshot": snapshot,
        "status_text": "측정 중 · 미리보기 데이터",
        "csv_file_name": "measurements.csv",
        "pending_count": 3,
        "time_synchronized": True,
        "current_time": (2026, 7, 12, 6, 9, 30, 45, 0),
        "network_info": {
            "mode": "station",
            "ssid": "CLASSROOM_WIFI",
            "ip_address": "192.168.0.37",
            "connected": True,
        },
        "chart_bootstrap_script": (
            "window.PREVIEW_MEASUREMENTS="
            + json.dumps(preview_measurements)
            + ";"
        ),
    }
    html = DashboardPageRenderer().render(payload)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as preview_file:
        preview_file.write(html)
    print("Generated:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
