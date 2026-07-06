from core.sensor_data import MAX_ARRAY_SIZE


CHART_HEIGHT     = 300.0
PLOT_HEIGHT      = 280.0
PLOT_MARGIN      = 10.0
PLOT_LEFT        = 70.0
PLOT_RIGHT       = 450.0
PLOT_BOTTOM      = CHART_HEIGHT - PLOT_MARGIN
PLOT_WIDTH       = PLOT_RIGHT - PLOT_LEFT
PLOT_X_INTERVAL  = PLOT_WIDTH / MAX_ARRAY_SIZE
Y_AXIS_DIVISIONS = 4.0


class ChartScale:
    def __init__(self):
        self.min_value       = 0.0
        self.max_value       = 0.0
        self.value_range     = 0.0
        self.scale_factor    = 0.0
        self.chart_step      = 0.0
        self.chart_min_value = 0.0


class SensorChartRenderer:
    """DataConnector에서 받은 센서 스냅샷을 SVG 경로로 변환한다."""

    @staticmethod
    def calculate_chart_scale(values, minimum_range):
        chart_scale = ChartScale()
        if not values:
            return chart_scale

        min_value = values[0]
        max_value = values[0]

        for value in values[1:]:
            if value < min_value:
                min_value = value
            elif value > max_value:
                max_value = value

        value_range = max_value - min_value
        if value_range < minimum_range:
            center = (min_value + max_value) / 2
            half_range = minimum_range / 2
            min_value = center - half_range
            max_value = center + half_range
            value_range = minimum_range

        chart_scale.min_value = min_value
        chart_scale.max_value = max_value
        chart_scale.value_range = value_range
        chart_scale.scale_factor = PLOT_HEIGHT / value_range
        chart_scale.chart_step = (
            value_range
            * CHART_HEIGHT
            / PLOT_HEIGHT
            / Y_AXIS_DIVISIONS
        )
        chart_scale.chart_min_value = (
            min_value - value_range * PLOT_MARGIN / PLOT_HEIGHT
        )
        return chart_scale

    @staticmethod
    def build_svg_path(values, chart_scale):
        if not values:
            return ""

        commands = [None] * len(values)
        for offset, value in enumerate(values):
            x = PLOT_LEFT + offset * PLOT_X_INTERVAL
            y = PLOT_BOTTOM - (
                value - chart_scale.min_value
            ) * chart_scale.scale_factor
            command = "M" if offset == 0 else "L"
            commands[offset] = "%s %.0f %.0f" % (command, x, y)

        return " ".join(commands)
