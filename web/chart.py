CHART_WIDTH = 520.0
CHART_HEIGHT = 370.0
PLOT_LEFT = 76.0
PLOT_RIGHT = 500.0
PLOT_TOP = 16.0
PLOT_BOTTOM = 300.0
PLOT_WIDTH = PLOT_RIGHT - PLOT_LEFT
PLOT_HEIGHT = PLOT_BOTTOM - PLOT_TOP
Y_AXIS_DIVISIONS = 5
X_AXIS_DIVISIONS = 4


class ChartScale:
    def __init__(self):
        self.min_value = 0.0
        self.max_value = 0.0
        self.value_range = 0.0
        self.scale_factor = 0.0


class SensorChartRenderer:
    """센서값과 측정 경과 시간을 정확한 SVG 좌표로 변환한다."""

    @staticmethod
    def calculate_chart_scale(values, minimum_range):
        chart_scale = ChartScale()
        if not values:
            return chart_scale

        min_value = min(values)
        max_value = max(values)
        value_range = max_value - min_value

        if value_range < minimum_range:
            center = (min_value + max_value) / 2
            half_range = minimum_range / 2
            min_value = center - half_range
            max_value = center + half_range
            value_range = minimum_range
        else:
            padding = value_range * 0.05
            min_value -= padding
            max_value += padding
            value_range = max_value - min_value

        chart_scale.min_value = min_value
        chart_scale.max_value = max_value
        chart_scale.value_range = value_range
        chart_scale.scale_factor = PLOT_HEIGHT / value_range
        return chart_scale

    @classmethod
    def build_svg_path(cls, values, chart_scale, time_offsets=None):
        if not values:
            return ""

        x_positions = cls.calculate_x_positions(len(values), time_offsets)
        commands = [None] * len(values)
        for offset, value in enumerate(values):
            y = PLOT_BOTTOM - (
                value - chart_scale.min_value
            ) * chart_scale.scale_factor
            command = "M" if offset == 0 else "L"
            commands[offset] = "%s %.1f %.1f" % (
                command,
                x_positions[offset],
                y,
            )
        return " ".join(commands)

    @staticmethod
    def calculate_x_positions(value_count, time_offsets=None):
        if value_count <= 0:
            return ()
        if value_count == 1:
            return (PLOT_RIGHT,)

        if time_offsets and len(time_offsets) == value_count:
            first = time_offsets[0]
            duration = time_offsets[-1] - first
            if duration > 0:
                return tuple(
                    PLOT_LEFT + (value - first) * PLOT_WIDTH / duration
                    for value in time_offsets
                )

        interval = PLOT_WIDTH / (value_count - 1)
        return tuple(
            PLOT_LEFT + offset * interval
            for offset in range(value_count)
        )

    @staticmethod
    def y_ticks(chart_scale):
        if chart_scale.value_range <= 0:
            return ()
        ticks = []
        for index in range(Y_AXIS_DIVISIONS + 1):
            ratio = index / Y_AXIS_DIVISIONS
            value = chart_scale.max_value - chart_scale.value_range * ratio
            y = PLOT_TOP + PLOT_HEIGHT * ratio
            ticks.append((y, value))
        return tuple(ticks)

    @staticmethod
    def x_ticks(time_offsets):
        if not time_offsets:
            return ((PLOT_LEFT, "첫 측정"), (PLOT_RIGHT, "최신"))
        if len(time_offsets) == 1:
            return ((PLOT_RIGHT, "최신"),)

        duration = max(0.0, time_offsets[-1] - time_offsets[0])
        if duration <= 0:
            return ((PLOT_LEFT, "첫 측정"), (PLOT_RIGHT, "최신"))
        ticks = []
        for index in range(X_AXIS_DIVISIONS + 1):
            ratio = index / X_AXIS_DIVISIONS
            x = PLOT_LEFT + PLOT_WIDTH * ratio
            remaining = duration * (1.0 - ratio)
            ticks.append((x, SensorChartRenderer._relative_time_label(remaining)))
        return tuple(ticks)

    @staticmethod
    def relative_changes(values):
        if not values:
            return ()
        baseline = values[0]
        if baseline == 0:
            return tuple(value - baseline for value in values)
        denominator = abs(baseline)
        return tuple(
            (value - baseline) * 100.0 / denominator
            for value in values
        )

    @staticmethod
    def _relative_time_label(seconds):
        rounded = int(seconds + 0.5)
        if rounded <= 0:
            return "최신"
        minutes, remaining_seconds = divmod(rounded, 60)
        if minutes:
            return "-%d:%02d" % (minutes, remaining_seconds)
        return "-%d초" % remaining_seconds
