from web.chart import SensorChartRenderer


class DashboardPageRenderer:
    """센서 상태와 차트를 독립 실행형 HTML 대시보드로 렌더링한다."""

    CHARTS = (
        (0, "CO₂", "ppm", 200.0, "#4f7cff"),
        (1, "온도", "°C", 4.0, "#ff795c"),
        (2, "습도", "%", 10.0, "#20b486"),
    )

    def __init__(self, chart_renderer=None):
        self.chart_renderer = chart_renderer or SensorChartRenderer()

    def render(self, payload):
        snapshot = payload["data_snapshot"]
        charts = []
        for index, title, unit, minimum_range, color in self.CHARTS:
            values = snapshot.series[index]
            charts.append(self._render_chart(
                title, unit, values, minimum_range, color,
            ))

        sensing = snapshot.sensing_enabled
        status_class = "running" if sensing else "stopped"
        freshness = self._freshness_text(snapshot)
        time_state = "동기화됨" if payload["time_synchronized"] else "동기화 필요"
        csv_name = self._escape(payload["csv_file_name"])

        return """<!doctype html>
<html lang=\"ko\"><head><meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<meta http-equiv=\"refresh\" content=\"10\">
<title>PTL Logger</title><style>
:root{color-scheme:dark;--bg:#0b1020;--card:#151d32;--line:#29344e;--muted:#94a3bd;--text:#edf2ff;--blue:#4f7cff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px system-ui,sans-serif}
main{max-width:1100px;margin:auto;padding:24px}header,.actions,.meta{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
header{justify-content:space-between;margin-bottom:18px}h1{font-size:24px;margin:0}.badge{padding:7px 11px;border-radius:99px;background:#39435b}
.badge.running{background:#126349}.badge.stopped{background:#5a3340}.notice{padding:13px 16px;background:#1d2944;border-left:4px solid var(--blue);border-radius:8px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px;margin:16px 0}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;overflow:hidden}
.card h2{font-size:16px;margin:0}.value{font-size:29px;font-weight:700;margin:5px 0}.unit{font-size:14px;color:var(--muted)}svg{width:100%%;height:auto}.axis{stroke:#3b4763;stroke-width:1}.label{fill:#94a3bd;font-size:11px}.trace{fill:none;stroke-width:3;stroke-linejoin:round;stroke-linecap:round}
button,.button{border:0;border-radius:8px;padding:10px 13px;background:var(--blue);color:white;font-weight:650;text-decoration:none;cursor:pointer}.secondary{background:#34405b}.danger{background:#a63d4a}
.meta{color:var(--muted);margin-top:14px;font-size:13px}.meta span{margin-right:10px}@media(max-width:500px){main{padding:15px}.actions>*{flex:1;text-align:center}}
</style></head><body><main>
<header><h1>PTL Sensor Logger</h1><span class=\"badge %s\">%s</span></header>
<div class=\"notice\">%s</div><section class=\"grid\">%s</section>
<section class=\"card actions\">
<form method=\"post\" action=\"/sensing_on\"><button>측정 시작</button></form>
<form method=\"post\" action=\"/sensing_off\"><button class=\"secondary\">측정 중지</button></form>
<button class=\"secondary\" onclick=\"syncTime()\">기기 시간 동기화</button>
<a class=\"button secondary\" href=\"/%s\">CSV 다운로드</a>
<form method=\"post\" action=\"/delete_csv\" onsubmit=\"return confirm('저장된 데이터를 삭제할까요?')\"><button class=\"danger\">CSV 초기화</button></form>
</section><div class=\"meta\"><span>데이터: %s</span><span>시간: %s</span><span>저장 대기: %d</span><span>누락: %d</span></div>
</main><script>
function syncTime(){var d=new Date(),q=['year='+d.getFullYear(),'month='+(d.getMonth()+1),'day='+d.getDate(),'weekday='+d.getDay(),'hour='+d.getHours(),'minute='+d.getMinutes(),'second='+d.getSeconds()].join('&');fetch('/set_time?'+q,{method:'POST'}).then(function(r){if(!r.ok)throw Error();location.reload()}).catch(function(){alert('시간 동기화에 실패했습니다.')})}
</script></body></html>""" % (
            status_class, "측정 중" if sensing else "측정 중지",
            self._escape(payload["status_text"]), "".join(charts), csv_name,
            freshness, time_state, payload["pending_count"],
            snapshot.dropped_count,
        )

    def _render_chart(self, title, unit, values, minimum_range, color):
        scale = self.chart_renderer.calculate_chart_scale(values, minimum_range)
        path = self.chart_renderer.build_svg_path(values, scale)
        latest = values[-1] if values else None
        value_text = "--" if latest is None else self._format_value(latest)
        if values:
            top = self._format_value(scale.max_value)
            middle = self._format_value((scale.min_value + scale.max_value) / 2)
            bottom = self._format_value(scale.min_value)
        else:
            top = middle = bottom = "--"
        return """<article class=\"card\"><h2>%s</h2><div class=\"value\">%s <span class=\"unit\">%s</span></div>
<svg viewBox=\"0 0 460 310\" role=\"img\" aria-label=\"%s 그래프\">
<line class=\"axis\" x1=\"70\" y1=\"10\" x2=\"70\" y2=\"290\"/><line class=\"axis\" x1=\"70\" y1=\"290\" x2=\"450\" y2=\"290\"/>
<text class=\"label\" x=\"4\" y=\"18\">%s</text><text class=\"label\" x=\"4\" y=\"153\">%s</text><text class=\"label\" x=\"4\" y=\"290\">%s</text>
<path class=\"trace\" stroke=\"%s\" d=\"%s\"/></svg></article>""" % (
            title, value_text, unit, title, top, middle, bottom, color, path,
        )

    @staticmethod
    def _format_value(value):
        return "%.1f" % value

    @staticmethod
    def _freshness_text(snapshot):
        if snapshot.latest_timestamp is None:
            return "측정값 없음"
        if snapshot.is_stale:
            return "오래된 측정값"
        if snapshot.age_ms is None:
            return "측정값 없음"
        return "%d초 전 갱신" % (snapshot.age_ms // 1000)

    @staticmethod
    def _escape(value):
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(
            ">", "&gt;"
        ).replace('"', "&quot;").replace("'", "&#39;")
