from web.chart_client import CHART_CLIENT_SCRIPT


class DashboardPageRenderer:
    """센서 상태와 차트를 독립 실행형 HTML 대시보드로 렌더링한다."""

    CHARTS = (
        (0, "CO₂", "이산화탄소 농도", "ppm", 200.0, "#38bdf8"),
        (1, "온도", "공기 온도", "°C", 4.0, "#fb923c"),
        (2, "습도", "상대습도", "%", 10.0, "#34d399"),
    )

    def render(self, payload):
        snapshot = payload["data_snapshot"]
        latest_cards = [self._render_latest_card(chart) for chart in self.CHARTS]
        comparison_chart = self._render_comparison_shell()

        sensing = snapshot.sensing_enabled
        status_class = "running" if sensing else "stopped"
        freshness = self._freshness_text(snapshot)
        time_state = "완료" if payload["time_synchronized"] else "필요"
        runtime_text = self._format_runtime(snapshot.runtime_seconds)
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
        chart_bootstrap_script = payload.get("chart_bootstrap_script", "")

        template = """<!doctype html>
<html lang=\"ko\"><head><meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">
<title>PTL 환경 탐구 대시보드</title><style>
.metric-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:25px}.metric-card{position:relative;overflow:hidden;padding:16px}.metric-card:after{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(110deg,transparent 30%%,rgba(255,255,255,.018),transparent 70%%)}
:root{color-scheme:dark;--bg:#050a0c;--surface:#0b1417;--card:#0d191c;--line:rgba(148,190,196,.14);--muted:#82979b;--text:#eef8f7;--cyan:#22d3c5;--cyan-soft:rgba(34,211,197,.12);--red:#fb7185}
*{box-sizing:border-box}html{background:var(--bg)}body{min-height:100vh;margin:0;background:radial-gradient(circle at 50%% -10%%,rgba(25,151,145,.18),transparent 38%%),linear-gradient(180deg,#061013 0,#050a0c 55%%);color:var(--text);font:15px ui-sans-serif,system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
body:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.32;background-image:linear-gradient(rgba(74,222,202,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(74,222,202,.025) 1px,transparent 1px);background-size:32px 32px;mask-image:linear-gradient(to bottom,black,transparent 72%%)}
main{position:relative;display:flex;flex-direction:column;max-width:1160px;margin:auto;padding:34px 24px calc(34px + env(safe-area-inset-bottom))}.topbar{order:-2;display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:22px}.lab-mark{display:inline-flex;align-items:center;gap:7px;margin:0 0 7px;color:#65e5d8;font-size:10px;font-weight:850;letter-spacing:.18em}.lab-mark:before{content:"";width:18px;height:2px;background:var(--cyan);box-shadow:0 0 10px var(--cyan)}h1{margin:0;font-size:clamp(25px,5vw,36px);letter-spacing:-.045em}.subtitle{margin:7px 0 0;color:var(--muted);font-size:13px}.header-side{display:flex;flex:none;flex-direction:column;align-items:flex-end;gap:9px;text-align:right}.device-clock span{display:block;color:#6f8d90;font-size:9px;font-weight:800;letter-spacing:.13em}.device-clock strong{display:block;margin-top:4px;color:#d9e7e7;font-size:13px;font-variant-numeric:tabular-nums;white-space:nowrap}.badge{display:flex;align-items:center;gap:8px;flex:none;padding:9px 13px;border:1px solid var(--line);border-radius:999px;background:rgba(8,18,21,.82);color:#b9c9ca;font-size:12px;font-weight:750}.badge:before{content:"";width:8px;height:8px;border-radius:50%%;background:#748589}.badge.running:before{background:#2dd4a8;box-shadow:0 0 13px #2dd4a8}.badge.stopped:before{background:var(--red)}
.status-panel{display:grid;grid-template-columns:1.25fr 1fr;gap:12px;margin-bottom:25px}.experiment-state,.quick-stats{border:1px solid var(--line);border-radius:17px;background:linear-gradient(135deg,rgba(13,31,34,.94),rgba(8,19,22,.86));box-shadow:0 18px 50px rgba(0,0,0,.18),inset 0 1px rgba(255,255,255,.035)}.experiment-state{position:relative;overflow:hidden;padding:17px 18px}.experiment-state:after{content:"";position:absolute;right:-25px;top:-45px;width:125px;height:125px;border-radius:50%%;background:rgba(34,211,197,.08);filter:blur(5px)}.overline{display:block;color:#6f8d90;font-size:10px;font-weight:800;letter-spacing:.13em}.experiment-state strong{display:block;margin-top:6px;font-size:17px;letter-spacing:-.02em}.quick-stats{display:grid;grid-template-columns:repeat(4,1fr);padding:8px}.quick-item{min-width:0;padding:8px 10px;border-right:1px solid var(--line)}.quick-item:last-child{border:0}.quick-item span{display:block;overflow:hidden;color:var(--muted);font-size:10px;white-space:nowrap;text-overflow:ellipsis}.quick-item strong{display:block;margin-top:5px;font-size:13px;white-space:nowrap}
.network-panel{display:flex;align-items:center;justify-content:space-between;gap:18px;margin:-13px 0 25px;padding:14px 18px}.network-title{flex:none}.network-title strong{display:block;margin-top:5px;font-size:14px}.network-items{display:grid;grid-template-columns:repeat(3,minmax(90px,1fr));width:min(100%%,570px)}.network-item{min-width:0;padding:2px 14px;border-left:1px solid var(--line)}.network-item span{display:block;color:var(--muted);font-size:10px}.network-item strong{display:block;overflow:hidden;margin-top:5px;font-size:12px;white-space:nowrap;text-overflow:ellipsis}
.section-head{display:flex;align-items:end;justify-content:space-between;gap:12px;margin:0 2px 12px}.section-head h2{margin:4px 0 0;font-size:19px;letter-spacing:-.03em}.section-head p{margin:0;color:var(--muted);font-size:11px}.chart-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.card{border:1px solid var(--line);border-radius:19px;background:linear-gradient(180deg,rgba(13,26,29,.96),rgba(8,17,19,.96));box-shadow:0 22px 55px rgba(0,0,0,.22),inset 0 1px rgba(255,255,255,.035)}.chart-card{position:relative;overflow:hidden;padding:17px}.chart-card:after{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(110deg,transparent 30%%,rgba(255,255,255,.018),transparent 70%%)}.comparison-card{margin-bottom:25px;padding:18px}.comparison-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}.comparison-head h3{margin:4px 0 0;font-size:17px}.comparison-head p{margin:5px 0 0;color:var(--muted);font-size:10px}.comparison-legend{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px 13px}.legend-item{display:flex;align-items:center;gap:6px;color:#aebfc0;font-size:10px}.legend-dot{width:8px;height:8px;border-radius:50%%;background:var(--legend-color);box-shadow:0 0 9px var(--legend-color)}.chart-title{display:flex;align-items:center;justify-content:space-between;gap:10px}.metric-name{display:flex;align-items:center;gap:8px}.metric-dot{width:7px;height:7px;border-radius:50%%;background:var(--accent);box-shadow:0 0 11px var(--accent)}.metric-name h3{margin:0;font-size:14px}.metric-subtitle{margin:4px 0 0 15px;color:var(--muted);font-size:10px}.trend{padding:5px 8px;border:1px solid var(--line);border-radius:8px;color:#9fb0b2;background:rgba(255,255,255,.025);font-size:10px;font-weight:700}.trend.up{color:#7dd3fc}.trend.down{color:#6ee7b7}.metric-value{margin:12px 0 0;font-size:35px;font-weight:780;letter-spacing:-.05em}.unit{margin-left:3px;color:var(--muted);font-size:12px;font-weight:650;letter-spacing:0}svg{display:block;width:100%%;height:auto;margin-top:2px}.axis{stroke:#365054;stroke-width:1}.grid-line{stroke:#183034;stroke-width:1;stroke-dasharray:3 7}.label{fill:#789093;font-size:9px}.axis-title{fill:#91a7aa;font-size:10px;font-weight:650}.trace{fill:none;stroke:var(--accent);stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}.comparison-trace{stroke-width:2.2}.chart-foot{display:flex;justify-content:space-between;gap:8px;padding-top:10px;border-top:1px solid var(--line);color:var(--muted);font-size:10px}.chart-foot strong{color:#b8c8c9;font-weight:650}
.chart-plot{position:relative}.pointer-area{fill:transparent;cursor:crosshair;touch-action:none}.cursor-line{stroke:#d2e2e2;stroke-width:1;stroke-dasharray:3 3;pointer-events:none}.cursor-dot{fill:var(--accent);stroke:#071012;stroke-width:2;pointer-events:none}.chart-tooltip{position:absolute;z-index:3;min-width:118px;padding:9px 10px;border:1px solid rgba(148,190,196,.28);border-radius:9px;background:rgba(5,12,14,.94);box-shadow:0 8px 22px rgba(0,0,0,.35);color:#e8f2f2;font-size:10px;pointer-events:none}.chart-tooltip strong,.chart-tooltip span{display:block}.chart-tooltip strong{margin-bottom:5px;color:#fff}.chart-tooltip span+span{margin-top:3px}.chart-tooltip i{display:inline-block;width:7px;height:7px;margin-right:6px;border-radius:50%%;background:var(--accent)}
.controls{order:-1;margin:0 0 22px;padding:16px}.controls-head{display:flex;justify-content:space-between;gap:12px;margin-bottom:13px}.controls-head h2{margin:3px 0 0;font-size:16px}.controls-head p{margin:3px 0 0;color:var(--muted);font-size:10px}.actions{display:grid;grid-template-columns:repeat(5,1fr);gap:9px}.actions form{display:flex;margin:0}.actions button,.button{display:flex;align-items:center;justify-content:center;gap:7px;width:100%%;min-height:43px;padding:10px 12px;border:1px solid transparent;border-radius:11px;background:linear-gradient(135deg,#0eaa9e,#087f79);box-shadow:0 8px 22px rgba(14,170,158,.16);color:#f3fffd;font:inherit;font-size:12px;font-weight:750;text-align:center;text-decoration:none;cursor:pointer}.step-number{display:inline-flex;align-items:center;justify-content:center;flex:none;width:20px;height:20px;border:1px solid rgba(255,255,255,.22);border-radius:50%%;background:rgba(255,255,255,.09);font-size:10px;font-weight:850}.actions .secondary{border-color:var(--line);background:#122326;box-shadow:none;color:#c1d0d1}.actions .danger{border-color:rgba(251,113,133,.2);background:rgba(122,37,52,.44);box-shadow:none;color:#fecdd3}.meta{display:flex;flex-wrap:wrap;gap:8px 16px;margin:13px 2px 0;color:#6f8588;font-size:10px}.meta span:before{content:"•";margin-right:6px;color:#2a7772}
@media(max-width:820px){.chart-grid{grid-template-columns:1fr}.chart-card{padding:18px 18px 14px}.actions{grid-template-columns:repeat(2,1fr)}.actions form:first-child{grid-column:span 2}.actions form:last-child{grid-column:span 2}}
@media(max-width:560px){main{padding:22px 14px calc(24px + env(safe-area-inset-bottom))}.topbar{margin-bottom:18px}.subtitle{max-width:210px}.header-side{gap:7px}.device-clock strong{font-size:11px}.badge{padding:8px 10px}.status-panel{grid-template-columns:1fr;gap:9px;margin-bottom:22px}.experiment-state{padding:15px 16px}.quick-stats{padding:6px}.quick-item{padding:7px 8px}.network-panel{display:block;margin-top:-10px;padding:14px}.network-items{margin-top:12px}.network-item{padding:2px 9px}.network-item:first-child{border-left:0;padding-left:0}.section-head{align-items:center}.chart-grid{gap:11px}.card{border-radius:16px}.metric-value{font-size:38px}.controls{padding:13px}.controls-head{display:block}.actions{gap:8px}.actions button,.button{min-height:46px}.meta{padding:0 2px}}
@media(max-width:560px){.metric-grid{gap:7px}.metric-card{padding:10px}.metric-card .metric-subtitle{display:none}.metric-card .metric-value{font-size:24px}}
</style></head><body><main>
<header class=\"topbar\"><div><p class=\"lab-mark\">PTL SCIENCE LAB</p><h1>무선센서 측정 실험</h1><p class=\"subtitle\">CO₂와 온·습도의 변화를 실시간으로 관찰합니다.</p></div><div class=\"header-side\"><div class=\"device-clock\"><span>DEVICE TIME</span><strong id=\"device-time\">%s</strong></div><span id=\"sensing-badge\" class=\"badge %s\">%s</span></div></header>
<section class=\"status-panel\"><div class=\"experiment-state\"><span class=\"overline\">EXPERIMENT STATUS</span><strong id=\"experiment-status\">%s</strong></div><div class=\"quick-stats\"><div class=\"quick-item\"><span>표본</span><strong id=\"sample-count\">%d회</strong></div><div class=\"quick-item\"><span>데이터</span><strong id=\"data-freshness\">%s</strong></div><div class=\"quick-item\"><span>시각 동기화</span><strong id=\"time-state\">%s</strong></div><div class=\"quick-item\"><span>측정시간</span><strong id=\"runtime\">%s</strong></div></div></section>
<section class=\"card network-panel\"><div class=\"network-title\"><span class=\"overline\">NETWORK STATUS</span><strong>%s</strong></div><div class=\"network-items\"><div class=\"network-item\"><span>SSID</span><strong>%s</strong></div><div class=\"network-item\"><span>IP 주소</span><strong>%s</strong></div><div class=\"network-item\"><span>상태</span><strong>%s</strong></div></div></section>
<div class=\"section-head\"><div><span class=\"overline\">LATEST MEASUREMENTS</span><h2>현재 측정값</h2></div><p>가장 최근의 CO₂, 온도, 습도입니다.</p></div><section class=\"metric-grid\">%s</section>
<div class=\"section-head\"><div><span class=\"overline\">RELATIVE TREND</span><h2>측정값 변화율 비교</h2></div><p>최근 10분 동안 최초 측정값 대비 변화율을 비교합니다.</p></div>%s
<section class=\"card controls\"><div class=\"controls-head\"><div><span class=\"overline\">EXPERIMENT CONTROL</span><h2>실험 제어</h2></div><p>시간 동기화부터 데이터 초기화까지 순서대로 진행하세요.</p></div><div class=\"actions\">
<button type=\"button\" class=\"secondary\" onclick=\"syncTime()\"><span class=\"step-number\">1</span><span>시간 동기화</span></button>
<form method=\"post\" action=\"/sensing_on\"><button><span class=\"step-number\">2</span><span>측정 시작</span></button></form>
<form method=\"post\" action=\"/sensing_off\"><button class=\"secondary\"><span class=\"step-number\">3</span><span>측정 중지</span></button></form>
<a class=\"button secondary\" href=\"/%s\"><span class=\"step-number\">4</span><span>CSV 받기</span></a>
<form method=\"post\" action=\"/delete_csv\" onsubmit=\"return confirm('저장된 데이터를 삭제할까요?')\"><button class=\"danger\"><span class=\"step-number\">5</span><span>데이터 초기화</span></button></form>
</div></section><div class=\"meta\"><span>데이터 <b id=\"meta-freshness\">%s</b></span><span>시각 동기화 <b id=\"meta-time-state\">%s</b></span><span>저장 대기 <b id=\"pending-count\">%d</b>건</span><span>누락 <b id=\"dropped-count\">%d</b>건</span></div>
</main><script>
function syncTime(){var d=new Date(),q=['year='+d.getFullYear(),'month='+(d.getMonth()+1),'day='+d.getDate(),'weekday='+d.getDay(),'hour='+d.getHours(),'minute='+d.getMinutes(),'second='+d.getSeconds()].join('&');fetch('/set_time?'+q,{method:'POST'}).then(function(r){if(!r.ok)throw Error();location.reload()}).catch(function(){alert('시간 동기화에 실패했습니다.')})}
%s
%s
</script></body></html>"""
        values = (
            current_time, status_class, "측정 중" if sensing else "측정 중지",
            self._escape(payload["status_text"]), sample_count, freshness,
            time_state, runtime_text, network_mode, network_ssid, network_ip, network_status,
            "".join(latest_cards), comparison_chart, csv_name, freshness, time_state,
            payload["pending_count"], snapshot.dropped_count,
            chart_bootstrap_script,
            CHART_CLIENT_SCRIPT,
        )
        return self._iter_format(template, values)

    @staticmethod
    def _iter_format(template, values, chunk_size=512):
        """큰 HTML 결과 문자열을 만들지 않고 %-template을 조각별로 치환한다."""
        value_index = 0
        literal_start = 0
        cursor = 0

        while cursor < len(template):
            marker = template.find("%", cursor)
            if marker < 0:
                for offset in range(literal_start, len(template), chunk_size):
                    yield template[offset:offset + chunk_size]
                break

            specifier = template[marker + 1:marker + 2]
            if specifier not in ("%", "s", "d"):
                cursor = marker + 1
                continue

            for offset in range(literal_start, marker, chunk_size):
                yield template[offset:min(offset + chunk_size, marker)]

            if specifier == "%":
                yield "%"
            else:
                value = values[value_index]
                value_index += 1
                text = str(value)
                for offset in range(0, len(text), chunk_size):
                    yield text[offset:offset + chunk_size]

            cursor = marker + 2
            literal_start = cursor

        if value_index != len(values):
            raise ValueError("Dashboard template value count mismatch")

    @staticmethod
    def _render_latest_card(chart):
        index, title, subtitle, unit, _, color = chart
        key = ("co2", "temperature", "humidity")[index]
        return """<article class=\"card metric-card\" style=\"--accent:%s\"><div class=\"metric-name\"><span class=\"metric-dot\"></span><h3>%s</h3></div><p class=\"metric-subtitle\">%s</p><div class=\"metric-value\"><span data-latest=\"%s\">--</span> <span class=\"unit\">%s</span></div></article>""" % (
            color,
            title,
            subtitle,
            key,
            unit,
        )

    @staticmethod
    def _render_comparison_shell():
        return """<article class=\"card comparison-card\"><div class=\"comparison-head\"><div><span class=\"overline\">NORMALIZED SERIES</span><h3>CO₂ · 온도 · 습도</h3><p>첫 측정값 대비 증감률을 동일한 Y축에서 비교합니다.</p></div><div class=\"comparison-legend\"><span class=\"legend-item\" style=\"--legend-color:#38bdf8\"><span class=\"legend-dot\"></span>CO₂</span><span class=\"legend-item\" style=\"--legend-color:#fb923c\"><span class=\"legend-dot\"></span>온도</span><span class=\"legend-item\" style=\"--legend-color:#34d399\"><span class=\"legend-dot\"></span>습도</span></div></div><div class=\"chart-plot\"><svg data-chart=\"comparison\" viewBox=\"0 0 520 370\" role=\"img\" aria-label=\"센서 상대 변화 대화형 그래프\"></svg><div class=\"chart-tooltip\" hidden></div></div></article>"""

    @staticmethod
    def _format_datetime(value):
        if value is None:
            return "--"
        return "%04d-%02d-%02d %02d:%02d:%02d" % (
            value[0],
            value[1],
            value[2],
            value[4],
            value[5],
            value[6],
        )

    @staticmethod
    def _format_runtime(total_seconds):
        total_seconds = max(0, int(total_seconds))
        return "%02d:%02d" % (total_seconds // 60, total_seconds % 60)

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
