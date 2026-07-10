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
                title, subtitle, unit, values, minimum_range, color,
            ))

        sensing = snapshot.sensing_enabled
        status_class = "running" if sensing else "stopped"
        freshness = self._freshness_text(snapshot)
        time_state = "동기화됨" if payload["time_synchronized"] else "동기화 필요"
        csv_name = self._escape(payload["csv_file_name"])
        sample_count = len(snapshot.series[0])

        return """<!doctype html>
<html lang=\"ko\"><head><meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">
<meta http-equiv=\"refresh\" content=\"10\">
<title>PTL 환경 탐구 대시보드</title><style>
:root{color-scheme:dark;--bg:#050a0c;--surface:#0b1417;--card:#0d191c;--line:rgba(148,190,196,.14);--muted:#82979b;--text:#eef8f7;--cyan:#22d3c5;--cyan-soft:rgba(34,211,197,.12);--red:#fb7185}
*{box-sizing:border-box}html{background:var(--bg)}body{min-height:100vh;margin:0;background:radial-gradient(circle at 50%% -10%%,rgba(25,151,145,.18),transparent 38%%),linear-gradient(180deg,#061013 0,#050a0c 55%%);color:var(--text);font:15px ui-sans-serif,system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
body:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.32;background-image:linear-gradient(rgba(74,222,202,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(74,222,202,.025) 1px,transparent 1px);background-size:32px 32px;mask-image:linear-gradient(to bottom,black,transparent 72%%)}
main{position:relative;max-width:1160px;margin:auto;padding:34px 24px calc(34px + env(safe-area-inset-bottom))}.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:22px}.lab-mark{display:inline-flex;align-items:center;gap:7px;margin:0 0 7px;color:#65e5d8;font-size:10px;font-weight:850;letter-spacing:.18em}.lab-mark:before{content:"";width:18px;height:2px;background:var(--cyan);box-shadow:0 0 10px var(--cyan)}h1{margin:0;font-size:clamp(25px,5vw,36px);letter-spacing:-.045em}.subtitle{margin:7px 0 0;color:var(--muted);font-size:13px}.badge{display:flex;align-items:center;gap:8px;flex:none;padding:9px 13px;border:1px solid var(--line);border-radius:999px;background:rgba(8,18,21,.82);color:#b9c9ca;font-size:12px;font-weight:750}.badge:before{content:"";width:8px;height:8px;border-radius:50%%;background:#748589}.badge.running:before{background:#2dd4a8;box-shadow:0 0 13px #2dd4a8}.badge.stopped:before{background:var(--red)}
.status-panel{display:grid;grid-template-columns:1.25fr 1fr;gap:12px;margin-bottom:25px}.experiment-state,.quick-stats{border:1px solid var(--line);border-radius:17px;background:linear-gradient(135deg,rgba(13,31,34,.94),rgba(8,19,22,.86));box-shadow:0 18px 50px rgba(0,0,0,.18),inset 0 1px rgba(255,255,255,.035)}.experiment-state{position:relative;overflow:hidden;padding:17px 18px}.experiment-state:after{content:"";position:absolute;right:-25px;top:-45px;width:125px;height:125px;border-radius:50%%;background:rgba(34,211,197,.08);filter:blur(5px)}.overline{display:block;color:#6f8d90;font-size:10px;font-weight:800;letter-spacing:.13em}.experiment-state strong{display:block;margin-top:6px;font-size:17px;letter-spacing:-.02em}.quick-stats{display:grid;grid-template-columns:repeat(3,1fr);padding:8px}.quick-item{min-width:0;padding:8px 10px;border-right:1px solid var(--line)}.quick-item:last-child{border:0}.quick-item span{display:block;overflow:hidden;color:var(--muted);font-size:10px;white-space:nowrap;text-overflow:ellipsis}.quick-item strong{display:block;margin-top:5px;font-size:13px;white-space:nowrap}
.section-head{display:flex;align-items:end;justify-content:space-between;gap:12px;margin:0 2px 12px}.section-head h2{margin:4px 0 0;font-size:19px;letter-spacing:-.03em}.section-head p{margin:0;color:var(--muted);font-size:11px}.chart-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.card{border:1px solid var(--line);border-radius:19px;background:linear-gradient(180deg,rgba(13,26,29,.96),rgba(8,17,19,.96));box-shadow:0 22px 55px rgba(0,0,0,.22),inset 0 1px rgba(255,255,255,.035)}.chart-card{position:relative;overflow:hidden;padding:17px}.chart-card:after{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(110deg,transparent 30%%,rgba(255,255,255,.018),transparent 70%%)}.chart-title{display:flex;align-items:center;justify-content:space-between;gap:10px}.metric-name{display:flex;align-items:center;gap:8px}.metric-dot{width:7px;height:7px;border-radius:50%%;background:var(--accent);box-shadow:0 0 11px var(--accent)}.metric-name h3{margin:0;font-size:14px}.metric-subtitle{margin:4px 0 0 15px;color:var(--muted);font-size:10px}.trend{padding:5px 8px;border:1px solid var(--line);border-radius:8px;color:#9fb0b2;background:rgba(255,255,255,.025);font-size:10px;font-weight:700}.trend.up{color:#7dd3fc}.trend.down{color:#6ee7b7}.metric-value{margin:12px 0 0;font-size:35px;font-weight:780;letter-spacing:-.05em}.unit{margin-left:3px;color:var(--muted);font-size:12px;font-weight:650;letter-spacing:0}svg{display:block;width:100%%;height:auto;margin-top:2px}.axis{stroke:#274044;stroke-width:1}.grid-line{stroke:#183034;stroke-width:1;stroke-dasharray:3 7}.label{fill:#70888b;font-size:10px}.trace{fill:none;stroke:var(--accent);stroke-width:3;stroke-linecap:round;stroke-linejoin:round;filter:drop-shadow(0 0 4px var(--accent))}.chart-foot{display:flex;justify-content:space-between;gap:8px;padding-top:10px;border-top:1px solid var(--line);color:var(--muted);font-size:10px}.chart-foot strong{color:#b8c8c9;font-weight:650}
.controls{margin-top:15px;padding:16px}.controls-head{display:flex;justify-content:space-between;gap:12px;margin-bottom:13px}.controls-head h2{margin:3px 0 0;font-size:16px}.controls-head p{margin:3px 0 0;color:var(--muted);font-size:10px}.actions{display:grid;grid-template-columns:repeat(5,1fr);gap:9px}.actions form{display:flex;margin:0}.actions button,.button{display:flex;align-items:center;justify-content:center;width:100%%;min-height:43px;padding:10px 12px;border:1px solid transparent;border-radius:11px;background:linear-gradient(135deg,#0eaa9e,#087f79);box-shadow:0 8px 22px rgba(14,170,158,.16);color:#f3fffd;font:inherit;font-size:12px;font-weight:750;text-align:center;text-decoration:none;cursor:pointer}.actions .secondary{border-color:var(--line);background:#122326;box-shadow:none;color:#c1d0d1}.actions .danger{border-color:rgba(251,113,133,.2);background:rgba(122,37,52,.44);box-shadow:none;color:#fecdd3}.meta{display:flex;flex-wrap:wrap;gap:8px 16px;margin:13px 2px 0;color:#6f8588;font-size:10px}.meta span:before{content:"•";margin-right:6px;color:#2a7772}
@media(max-width:820px){.chart-grid{grid-template-columns:1fr}.chart-card{padding:18px 18px 14px}.actions{grid-template-columns:repeat(2,1fr)}.actions form:first-child{grid-column:span 2}.actions form:last-child{grid-column:span 2}}
@media(max-width:560px){main{padding:22px 14px calc(24px + env(safe-area-inset-bottom))}.topbar{align-items:flex-start;margin-bottom:18px}.subtitle{max-width:220px}.badge{padding:8px 10px}.status-panel{grid-template-columns:1fr;gap:9px;margin-bottom:22px}.experiment-state{padding:15px 16px}.quick-stats{padding:6px}.quick-item{padding:7px 8px}.section-head{align-items:center}.chart-grid{gap:11px}.card{border-radius:16px}.metric-value{font-size:38px}.controls{padding:13px}.controls-head{display:block}.actions{gap:8px}.actions button,.button{min-height:46px}.meta{padding:0 2px}}
</style></head><body><main>
<header class=\"topbar\"><div><p class=\"lab-mark\">PTL SCIENCE LAB</p><h1>교실 환경 탐구</h1><p class=\"subtitle\">CO₂와 온·습도의 변화를 실시간으로 관찰합니다.</p></div><span class=\"badge %s\">%s</span></header>
<section class=\"status-panel\"><div class=\"experiment-state\"><span class=\"overline\">EXPERIMENT STATUS</span><strong>%s</strong></div><div class=\"quick-stats\"><div class=\"quick-item\"><span>표본</span><strong>%d회</strong></div><div class=\"quick-item\"><span>데이터</span><strong>%s</strong></div><div class=\"quick-item\"><span>시간</span><strong>%s</strong></div></div></section>
<div class=\"section-head\"><div><span class=\"overline\">LIVE MEASUREMENTS</span><h2>실시간 측정 그래프</h2></div><p>최근 측정값 기준</p></div><section class=\"chart-grid\">%s</section>
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
            status_class, "측정 중" if sensing else "측정 중지",
            self._escape(payload["status_text"]), sample_count, freshness,
            time_state, "".join(charts), csv_name, freshness, time_state,
            payload["pending_count"], snapshot.dropped_count,
        )

    def _render_chart(self, title, subtitle, unit, values, minimum_range, color):
        scale = self.chart_renderer.calculate_chart_scale(values, minimum_range)
        path = self.chart_renderer.build_svg_path(values, scale)
        latest = values[-1] if values else None
        value_text = "--" if latest is None else self._format_value(latest)
        trend_class, trend_text = self._trend(values)
        if values:
            top = self._format_value(scale.max_value)
            middle = self._format_value((scale.min_value + scale.max_value) / 2)
            bottom = self._format_value(scale.min_value)
            value_range = "%s ~ %s %s" % (bottom, top, unit)
        else:
            top = middle = bottom = "--"
            value_range = "측정값 없음"
        return """<article class=\"card chart-card\" style=\"--accent:%s\"><div class=\"chart-title\"><div><div class=\"metric-name\"><span class=\"metric-dot\"></span><h3>%s</h3></div><p class=\"metric-subtitle\">%s</p></div><span class=\"trend %s\">%s</span></div><div class=\"metric-value\">%s <span class=\"unit\">%s</span></div>
<svg viewBox=\"0 0 460 310\" role=\"img\" aria-label=\"%s 변화 그래프\"><line class=\"grid-line\" x1=\"70\" y1=\"10\" x2=\"450\" y2=\"10\"/><line class=\"grid-line\" x1=\"70\" y1=\"150\" x2=\"450\" y2=\"150\"/><line class=\"grid-line\" x1=\"70\" y1=\"290\" x2=\"450\" y2=\"290\"/><line class=\"axis\" x1=\"70\" y1=\"10\" x2=\"70\" y2=\"290\"/><line class=\"axis\" x1=\"70\" y1=\"290\" x2=\"450\" y2=\"290\"/><text class=\"label\" x=\"4\" y=\"18\">%s</text><text class=\"label\" x=\"4\" y=\"153\">%s</text><text class=\"label\" x=\"4\" y=\"290\">%s</text><path class=\"trace\" d=\"%s\"/></svg><div class=\"chart-foot\"><span>관찰 범위 <strong>%s</strong></span><span><strong>%d</strong> samples</span></div></article>""" % (
            color, title, subtitle, trend_class, trend_text, value_text, unit,
            title, top, middle, bottom, path, value_range, len(values),
        )

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
