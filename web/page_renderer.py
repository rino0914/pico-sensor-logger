from web.chart import SensorChartRenderer


class DashboardPageRenderer:
    """센서 상태와 차트를 독립 실행형 HTML 대시보드로 렌더링한다."""

    CHARTS = (
        (0, "CO₂", "이산화탄소 농도", "ppm", 200.0, "#38bdf8"),
        (1, "온도", "공기 온도", "°C", 4.0, "#fb923c"),
        (2, "습도", "상대습도", "%", 10.0, "#34d399"),
    )

    def __init__(self, chart_renderer=None):
        self.chart_renderer = chart_renderer or SensorChartRenderer()

    def render(self, payload):
        snapshot = payload["data_snapshot"]
        charts = []
        for index, title, subtitle, unit, minimum_range, color in self.CHARTS:
            values = snapshot.series[index]
            charts.append(self._render_chart(
                title,
                subtitle,
                unit,
                values,
                minimum_range,
                color,
                snapshot.time_offsets,
            ))
        comparison_chart = self._render_comparison_chart(
            snapshot.series,
            snapshot.time_offsets,
        )

        sensing = snapshot.sensing_enabled
        status_class = "running" if sensing else "stopped"
        freshness = self._freshness_text(snapshot)
        time_state = "동기화됨" if payload["time_synchronized"] else "동기화 필요"
        current_time = self._format_datetime(payload["current_time"])
        csv_name = self._escape(payload["csv_file_name"])
        sample_count = len(snapshot.series[0])
        network = payload["network_info"]
        network_mode = {
            "ap": "AP",
            "station": "Station",
        }.get(network["mode"], "알 수 없음")
        network_ssid = self._escape(network["ssid"])
        network_ip = self._escape(network["ip_address"])
        network_status = "활성" if network["connected"] else "비활성"

        return """<!doctype html>
<html lang=\"ko\"><head><meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">
<meta http-equiv=\"refresh\" content=\"10\">
<title>PTL 환경 탐구 대시보드</title><style>
:root{color-scheme:dark;--bg:#050a0c;--surface:#0b1417;--card:#0d191c;--line:rgba(148,190,196,.14);--muted:#82979b;--text:#eef8f7;--cyan:#22d3c5;--cyan-soft:rgba(34,211,197,.12);--red:#fb7185}
*{box-sizing:border-box}html{background:var(--bg)}body{min-height:100vh;margin:0;background:radial-gradient(circle at 50%% -10%%,rgba(25,151,145,.18),transparent 38%%),linear-gradient(180deg,#061013 0,#050a0c 55%%);color:var(--text);font:15px ui-sans-serif,system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
body:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.32;background-image:linear-gradient(rgba(74,222,202,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(74,222,202,.025) 1px,transparent 1px);background-size:32px 32px;mask-image:linear-gradient(to bottom,black,transparent 72%%)}
main{position:relative;max-width:1160px;margin:auto;padding:34px 24px calc(34px + env(safe-area-inset-bottom))}.topbar{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:22px}.lab-mark{display:inline-flex;align-items:center;gap:7px;margin:0 0 7px;color:#65e5d8;font-size:10px;font-weight:850;letter-spacing:.18em}.lab-mark:before{content:"";width:18px;height:2px;background:var(--cyan);box-shadow:0 0 10px var(--cyan)}h1{margin:0;font-size:clamp(25px,5vw,36px);letter-spacing:-.045em}.subtitle{margin:7px 0 0;color:var(--muted);font-size:13px}.header-side{display:flex;flex:none;flex-direction:column;align-items:flex-end;gap:9px;text-align:right}.device-clock span{display:block;color:#6f8d90;font-size:9px;font-weight:800;letter-spacing:.13em}.device-clock strong{display:block;margin-top:4px;color:#d9e7e7;font-size:13px;font-variant-numeric:tabular-nums;white-space:nowrap}.badge{display:flex;align-items:center;gap:8px;flex:none;padding:9px 13px;border:1px solid var(--line);border-radius:999px;background:rgba(8,18,21,.82);color:#b9c9ca;font-size:12px;font-weight:750}.badge:before{content:"";width:8px;height:8px;border-radius:50%%;background:#748589}.badge.running:before{background:#2dd4a8;box-shadow:0 0 13px #2dd4a8}.badge.stopped:before{background:var(--red)}
.status-panel{display:grid;grid-template-columns:1.25fr 1fr;gap:12px;margin-bottom:25px}.experiment-state,.quick-stats{border:1px solid var(--line);border-radius:17px;background:linear-gradient(135deg,rgba(13,31,34,.94),rgba(8,19,22,.86));box-shadow:0 18px 50px rgba(0,0,0,.18),inset 0 1px rgba(255,255,255,.035)}.experiment-state{position:relative;overflow:hidden;padding:17px 18px}.experiment-state:after{content:"";position:absolute;right:-25px;top:-45px;width:125px;height:125px;border-radius:50%%;background:rgba(34,211,197,.08);filter:blur(5px)}.overline{display:block;color:#6f8d90;font-size:10px;font-weight:800;letter-spacing:.13em}.experiment-state strong{display:block;margin-top:6px;font-size:17px;letter-spacing:-.02em}.quick-stats{display:grid;grid-template-columns:repeat(3,1fr);padding:8px}.quick-item{min-width:0;padding:8px 10px;border-right:1px solid var(--line)}.quick-item:last-child{border:0}.quick-item span{display:block;overflow:hidden;color:var(--muted);font-size:10px;white-space:nowrap;text-overflow:ellipsis}.quick-item strong{display:block;margin-top:5px;font-size:13px;white-space:nowrap}
.network-panel{display:flex;align-items:center;justify-content:space-between;gap:18px;margin:-13px 0 25px;padding:14px 18px}.network-title{flex:none}.network-title strong{display:block;margin-top:5px;font-size:14px}.network-items{display:grid;grid-template-columns:repeat(3,minmax(90px,1fr));width:min(100%%,570px)}.network-item{min-width:0;padding:2px 14px;border-left:1px solid var(--line)}.network-item span{display:block;color:var(--muted);font-size:10px}.network-item strong{display:block;overflow:hidden;margin-top:5px;font-size:12px;white-space:nowrap;text-overflow:ellipsis}
.section-head{display:flex;align-items:end;justify-content:space-between;gap:12px;margin:0 2px 12px}.section-head h2{margin:4px 0 0;font-size:19px;letter-spacing:-.03em}.section-head p{margin:0;color:var(--muted);font-size:11px}.chart-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.card{border:1px solid var(--line);border-radius:19px;background:linear-gradient(180deg,rgba(13,26,29,.96),rgba(8,17,19,.96));box-shadow:0 22px 55px rgba(0,0,0,.22),inset 0 1px rgba(255,255,255,.035)}.chart-card{position:relative;overflow:hidden;padding:17px}.chart-card:after{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(110deg,transparent 30%%,rgba(255,255,255,.018),transparent 70%%)}.comparison-card{margin-bottom:25px;padding:18px}.comparison-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}.comparison-head h3{margin:4px 0 0;font-size:17px}.comparison-head p{margin:5px 0 0;color:var(--muted);font-size:10px}.comparison-legend{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px 13px}.legend-item{display:flex;align-items:center;gap:6px;color:#aebfc0;font-size:10px}.legend-dot{width:8px;height:8px;border-radius:50%%;background:var(--legend-color);box-shadow:0 0 9px var(--legend-color)}.chart-title{display:flex;align-items:center;justify-content:space-between;gap:10px}.metric-name{display:flex;align-items:center;gap:8px}.metric-dot{width:7px;height:7px;border-radius:50%%;background:var(--accent);box-shadow:0 0 11px var(--accent)}.metric-name h3{margin:0;font-size:14px}.metric-subtitle{margin:4px 0 0 15px;color:var(--muted);font-size:10px}.trend{padding:5px 8px;border:1px solid var(--line);border-radius:8px;color:#9fb0b2;background:rgba(255,255,255,.025);font-size:10px;font-weight:700}.trend.up{color:#7dd3fc}.trend.down{color:#6ee7b7}.metric-value{margin:12px 0 0;font-size:35px;font-weight:780;letter-spacing:-.05em}.unit{margin-left:3px;color:var(--muted);font-size:12px;font-weight:650;letter-spacing:0}svg{display:block;width:100%%;height:auto;margin-top:2px}.axis{stroke:#365054;stroke-width:1}.grid-line{stroke:#183034;stroke-width:1;stroke-dasharray:3 7}.label{fill:#789093;font-size:9px}.axis-title{fill:#91a7aa;font-size:10px;font-weight:650}.trace{fill:none;stroke:var(--accent);stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}.comparison-trace{stroke-width:2.2}.chart-foot{display:flex;justify-content:space-between;gap:8px;padding-top:10px;border-top:1px solid var(--line);color:var(--muted);font-size:10px}.chart-foot strong{color:#b8c8c9;font-weight:650}
.controls{margin-top:15px;padding:16px}.controls-head{display:flex;justify-content:space-between;gap:12px;margin-bottom:13px}.controls-head h2{margin:3px 0 0;font-size:16px}.controls-head p{margin:3px 0 0;color:var(--muted);font-size:10px}.actions{display:grid;grid-template-columns:repeat(5,1fr);gap:9px}.actions form{display:flex;margin:0}.actions button,.button{display:flex;align-items:center;justify-content:center;width:100%%;min-height:43px;padding:10px 12px;border:1px solid transparent;border-radius:11px;background:linear-gradient(135deg,#0eaa9e,#087f79);box-shadow:0 8px 22px rgba(14,170,158,.16);color:#f3fffd;font:inherit;font-size:12px;font-weight:750;text-align:center;text-decoration:none;cursor:pointer}.actions .secondary{border-color:var(--line);background:#122326;box-shadow:none;color:#c1d0d1}.actions .danger{border-color:rgba(251,113,133,.2);background:rgba(122,37,52,.44);box-shadow:none;color:#fecdd3}.meta{display:flex;flex-wrap:wrap;gap:8px 16px;margin:13px 2px 0;color:#6f8588;font-size:10px}.meta span:before{content:"•";margin-right:6px;color:#2a7772}
@media(max-width:820px){.chart-grid{grid-template-columns:1fr}.chart-card{padding:18px 18px 14px}.actions{grid-template-columns:repeat(2,1fr)}.actions form:first-child{grid-column:span 2}.actions form:last-child{grid-column:span 2}}
@media(max-width:560px){main{padding:22px 14px calc(24px + env(safe-area-inset-bottom))}.topbar{margin-bottom:18px}.subtitle{max-width:210px}.header-side{gap:7px}.device-clock strong{font-size:11px}.badge{padding:8px 10px}.status-panel{grid-template-columns:1fr;gap:9px;margin-bottom:22px}.experiment-state{padding:15px 16px}.quick-stats{padding:6px}.quick-item{padding:7px 8px}.network-panel{display:block;margin-top:-10px;padding:14px}.network-items{margin-top:12px}.network-item{padding:2px 9px}.network-item:first-child{border-left:0;padding-left:0}.section-head{align-items:center}.chart-grid{gap:11px}.card{border-radius:16px}.metric-value{font-size:38px}.controls{padding:13px}.controls-head{display:block}.actions{gap:8px}.actions button,.button{min-height:46px}.meta{padding:0 2px}}
</style></head><body><main>
<header class=\"topbar\"><div><p class=\"lab-mark\">PTL SCIENCE LAB</p><h1>교실 환경 탐구</h1><p class=\"subtitle\">CO₂와 온·습도의 변화를 실시간으로 관찰합니다.</p></div><div class=\"header-side\"><div class=\"device-clock\"><span>DEVICE TIME</span><strong>%s</strong></div><span class=\"badge %s\">%s</span></div></header>
<section class=\"status-panel\"><div class=\"experiment-state\"><span class=\"overline\">EXPERIMENT STATUS</span><strong>%s</strong></div><div class=\"quick-stats\"><div class=\"quick-item\"><span>표본</span><strong>%d회</strong></div><div class=\"quick-item\"><span>데이터</span><strong>%s</strong></div><div class=\"quick-item\"><span>시간</span><strong>%s</strong></div></div></section>
<section class=\"card network-panel\"><div class=\"network-title\"><span class=\"overline\">NETWORK STATUS</span><strong>%s</strong></div><div class=\"network-items\"><div class=\"network-item\"><span>SSID</span><strong>%s</strong></div><div class=\"network-item\"><span>IP 주소</span><strong>%s</strong></div><div class=\"network-item\"><span>상태</span><strong>%s</strong></div></div></section>
<div class=\"section-head\"><div><span class=\"overline\">RELATIVE TREND</span><h2>센서 상대 변화 비교</h2></div><p>각 센서의 첫 측정값을 0%% 기준으로 비교</p></div>%s
<div class=\"section-head\"><div><span class=\"overline\">ABSOLUTE MEASUREMENTS</span><h2>센서별 정밀 그래프</h2></div><p>실제 단위와 측정 경과 시간 기준</p></div><section class=\"chart-grid\">%s</section>
<section class=\"card controls\"><div class=\"controls-head\"><div><span class=\"overline\">EXPERIMENT CONTROL</span><h2>실험 제어</h2></div><p>측정 전 기기 시간을 먼저 동기화하세요.</p></div><div class=\"actions\">
<form method=\"post\" action=\"/sensing_on\"><button>측정 시작</button></form>
<form method=\"post\" action=\"/sensing_off\"><button class=\"secondary\">측정 중지</button></form>
<button class=\"secondary\" onclick=\"syncTime()\">시간 동기화</button>
<a class=\"button secondary\" href=\"/%s\">CSV 받기</a>
<form method=\"post\" action=\"/delete_csv\" onsubmit=\"return confirm('저장된 데이터를 삭제할까요?')\"><button class=\"danger\">데이터 초기화</button></form>
</div></section><div class=\"meta\"><span>데이터 %s</span><span>시간 %s</span><span>저장 대기 %d건</span><span>누락 %d건</span></div>
</main><script>
function syncTime(){var d=new Date(),q=['year='+d.getFullYear(),'month='+(d.getMonth()+1),'day='+d.getDate(),'weekday='+d.getDay(),'hour='+d.getHours(),'minute='+d.getMinutes(),'second='+d.getSeconds()].join('&');fetch('/set_time?'+q,{method:'POST'}).then(function(r){if(!r.ok)throw Error();location.reload()}).catch(function(){alert('시간 동기화에 실패했습니다.')})}
</script></body></html>""" % (
            current_time, status_class, "측정 중" if sensing else "측정 중지",
            self._escape(payload["status_text"]), sample_count, freshness,
            time_state, network_mode, network_ssid, network_ip, network_status,
            comparison_chart, "".join(charts), csv_name, freshness, time_state,
            payload["pending_count"], snapshot.dropped_count,
        )

    def _render_chart(
        self,
        title,
        subtitle,
        unit,
        values,
        minimum_range,
        color,
        time_offsets,
    ):
        scale = self.chart_renderer.calculate_chart_scale(values, minimum_range)
        path = self.chart_renderer.build_svg_path(
            values,
            scale,
            time_offsets,
        )
        latest = values[-1] if values else None
        value_text = "--" if latest is None else self._format_value(latest)
        trend_class, trend_text = self._trend(values)
        if values:
            value_range = "%s ~ %s %s" % (
                self._format_value(scale.min_value),
                self._format_value(scale.max_value),
                unit,
            )
        else:
            value_range = "측정값 없음"
        axes = self._render_axes(scale, time_offsets, "%s (%s)" % (subtitle, unit))
        return """<article class=\"card chart-card\" style=\"--accent:%s\"><div class=\"chart-title\"><div><div class=\"metric-name\"><span class=\"metric-dot\"></span><h3>%s</h3></div><p class=\"metric-subtitle\">%s</p></div><span class=\"trend %s\">%s</span></div><div class=\"metric-value\">%s <span class=\"unit\">%s</span></div>
<svg viewBox=\"0 0 520 370\" role=\"img\" aria-label=\"%s 시간 변화 그래프\">%s<path class=\"trace\" d=\"%s\"/></svg><div class=\"chart-foot\"><span>Y축 범위 <strong>%s</strong></span><span><strong>%d</strong> samples</span></div></article>""" % (
            color, title, subtitle, trend_class, trend_text, value_text, unit,
            title, axes, path, value_range, len(values),
        )

    def _render_comparison_chart(self, series, time_offsets):
        relative_series = tuple(
            self.chart_renderer.relative_changes(values)
            for values in series
        )
        combined_values = []
        for values in relative_series:
            combined_values.extend(values)
        scale = self.chart_renderer.calculate_chart_scale(
            combined_values,
            10.0,
        )
        axes = self._render_axes(
            scale,
            time_offsets,
            "초기값 대비 변화율 (%)",
        )
        paths = []
        legend = []
        for metadata, values, relative_values in zip(
            self.CHARTS,
            series,
            relative_series,
        ):
            _, title, _, unit, _, color = metadata
            path = self.chart_renderer.build_svg_path(
                relative_values,
                scale,
                time_offsets,
            )
            paths.append(
                '<path class="trace comparison-trace" '
                'style="--accent:%s" d="%s"/>' % (color, path)
            )
            latest = "--" if not values else self._format_value(values[-1])
            legend.append(
                '<span class="legend-item" style="--legend-color:%s">'
                '<span class="legend-dot"></span>%s %s %s</span>'
                % (color, title, latest, unit)
            )

        return """<article class=\"card comparison-card\"><div class=\"comparison-head\"><div><span class=\"overline\">NORMALIZED SERIES</span><h3>CO₂ · 온도 · 습도</h3><p>첫 측정값 대비 증감률을 동일한 Y축에서 비교합니다.</p></div><div class=\"comparison-legend\">%s</div></div><svg viewBox=\"0 0 520 370\" role=\"img\" aria-label=\"센서 상대 변화 비교 그래프\">%s%s</svg></article>""" % (
            "".join(legend),
            axes,
            "".join(paths),
        )

    def _render_axes(self, scale, time_offsets, y_axis_title):
        elements = []
        for y, value in self.chart_renderer.y_ticks(scale):
            elements.append(
                '<line class="grid-line" x1="76" y1="%.1f" '
                'x2="500" y2="%.1f"/>' % (y, y)
            )
            elements.append(
                '<text class="label" x="69" y="%.1f" '
                'text-anchor="end">%s</text>'
                % (y + 3, self._format_value(value))
            )
        for x, label in self.chart_renderer.x_ticks(time_offsets):
            elements.append(
                '<line class="grid-line" x1="%.1f" y1="16" '
                'x2="%.1f" y2="300"/>' % (x, x)
            )
            elements.append(
                '<text class="label" x="%.1f" y="318" '
                'text-anchor="middle">%s</text>'
                % (x, self._escape(label))
            )
        elements.append(
            '<line class="axis" x1="76" y1="16" x2="76" y2="300"/>'
            '<line class="axis" x1="76" y1="300" x2="500" y2="300"/>'
            '<text class="axis-title" x="288" y="350" '
            'text-anchor="middle">측정 시간 (분:초, 최신값 기준)</text>'
            '<text class="axis-title" x="-158" y="14" '
            'text-anchor="middle" transform="rotate(-90)">%s</text>'
            % self._escape(y_axis_title)
        )
        return "".join(elements)

    @classmethod
    def _trend(cls, values):
        if len(values) < 2:
            return "", "변화량 --"
        difference = values[-1] - values[-2]
        if difference > 0.05:
            return "up", "▲ +%s" % cls._format_value(difference)
        if difference < -0.05:
            return "down", "▼ %s" % cls._format_value(difference)
        return "", "― 0.0"

    @staticmethod
    def _format_value(value):
        return "%.1f" % value

    @staticmethod
    def _format_datetime(value):
        if value is None:
            return "동기화 필요"
        return "%04d-%02d-%02d %02d:%02d:%02d" % (
            value[0],
            value[1],
            value[2],
            value[4],
            value[5],
            value[6],
        )

    @staticmethod
    def _freshness_text(snapshot):
        if snapshot.latest_timestamp is None:
            return "측정값 없음"
        if snapshot.is_stale:
            return "갱신 지연"
        if snapshot.age_ms is None:
            return "측정값 없음"
        return "%d초 전" % (snapshot.age_ms // 1000)

    @staticmethod
    def _escape(value):
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(
            ">", "&gt;"
        ).replace('"', "&quot;").replace("'", "&#39;")
