import unittest

from web.chart import (
    PLOT_LEFT,
    PLOT_RIGHT,
    SensorChartRenderer,
)


class SensorChartRendererTest(unittest.TestCase):
    def setUp(self):
        self.renderer = SensorChartRenderer()

    def test_x_positions_follow_real_time_intervals(self):
        positions = self.renderer.calculate_x_positions(
            3,
            (0.0, 5.0, 20.0),
        )

        self.assertEqual(PLOT_LEFT, positions[0])
        self.assertAlmostEqual(
            PLOT_LEFT + (PLOT_RIGHT - PLOT_LEFT) * 0.25,
            positions[1],
        )
        self.assertEqual(PLOT_RIGHT, positions[2])

    def test_path_uses_full_plot_width_for_available_samples(self):
        values = (400.0, 500.0, 600.0)
        scale = self.renderer.calculate_chart_scale(values, 100.0)

        path = self.renderer.build_svg_path(
            values,
            scale,
            (0.0, 5.0, 10.0),
        )

        self.assertTrue(path.startswith("M 76.0"))
        self.assertIn("L 500.0", path)

    def test_y_axis_has_detailed_numeric_ticks(self):
        scale = self.renderer.calculate_chart_scale((400.0, 600.0), 100.0)
        ticks = self.renderer.y_ticks(scale)

        self.assertEqual(6, len(ticks))
        self.assertAlmostEqual(scale.max_value, ticks[0][1])
        self.assertAlmostEqual(scale.min_value, ticks[-1][1])

    def test_relative_changes_use_first_measurement_as_baseline(self):
        changes = self.renderer.relative_changes((100.0, 110.0, 90.0))

        self.assertEqual((0.0, 10.0, -10.0), changes)

    def test_single_measurement_is_placed_at_latest_position(self):
        positions = self.renderer.calculate_x_positions(1, (0.0,))
        ticks = self.renderer.x_ticks((0.0,))

        self.assertEqual((PLOT_RIGHT,), positions)
        self.assertEqual(((PLOT_RIGHT, "최신"),), ticks)


if __name__ == "__main__":
    unittest.main()
