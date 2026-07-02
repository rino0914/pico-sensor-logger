import sensor_data

CHART_HEIGHT     = 300.0
PLOT_HEIGHT      = 280.0
PLOT_MARGIN      = 10.0
PLOT_LEFT        = 70.0
PLOT_RIGHT       = 450.0
PLOT_BOTTOM      = CHART_HEIGHT - PLOT_MARGIN
PLOT_WIDTH       = PLOT_RIGHT - PLOT_LEFT
PLOT_X_INTERVAL  = PLOT_WIDTH / sensor_data.MAX_ARRAY_SIZE
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
    def __init__(self, sensor_buffer):
        self.sensor_buffer = sensor_buffer

    def calculate_chart_scale(self, field_name, minimum_range):
        if self.sensor_buffer.count == 0:
            return None
        
        values = self.sensor_buffer.get_values(field_name)
        index = (self.sensor_buffer.head -1) % self.sensor_buffer.size
        min_value = values[index]
        max_value = min_value

        for _ in range(self.sensor_buffer.count - 1):
            index -=1
            if index < 0:
                index = self.sensor_buffer.size -1

            value = values[index]
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

        chart_scale = ChartScale()
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
            
    def build_svg_path(self, field_name, chart_scale):
        if self.sensor_buffer.count ==0:
            return ""
        value_count = self.sensor_buffer.count
        values = self.sensor_buffer.get_values(field_name)
        min_value = chart_scale.min_value
        scale_factor = chart_scale.scale_factor
        index = self.sensor_buffer._start_index()
        commands = [None] * value_count

        for offset in range (value_count):
            x = PLOT_LEFT + offset * PLOT_X_INTERVAL
            y = PLOT_BOTTOM - (
                values[index] - min_value
            ) * scale_factor
            command = "M" if offset ==0 else "L"
            commands[offset] = "%s %.0f %.0f" % (command, x, y)

            index += 1
            if index == self.sensor_buffer.size:
                index = 0
        return " ".join(commands)
