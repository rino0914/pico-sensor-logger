import unittest

import core.data_connector as data_connector_module
from core.data_connector import DataConnector


class DataConnectorRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.original_ticks_ms = data_connector_module.ticks_ms
        self.now_ms = 1_000
        data_connector_module.ticks_ms = lambda: self.now_ms
        self.connector = DataConnector()

    def tearDown(self):
        data_connector_module.ticks_ms = self.original_ticks_ms

    def test_runtime_continues_while_sensing_is_stopped(self):
        self.connector.start_sensing()
        self.now_ms = 62_000
        self.connector.stop_sensing()
        self.now_ms = 121_000

        snapshot = self.connector.snapshot()

        self.assertFalse(snapshot.sensing_enabled)
        self.assertEqual(120, snapshot.runtime_seconds)

    def test_restarting_sensing_does_not_reset_runtime(self):
        self.connector.start_sensing()
        self.now_ms = 31_000
        self.connector.stop_sensing()
        self.now_ms = 61_000
        self.connector.start_sensing()

        self.assertEqual(60, self.connector.snapshot().runtime_seconds)

    def test_clear_resets_runtime(self):
        self.connector.start_sensing()
        self.now_ms = 61_000
        self.connector.stop_sensing()
        self.connector.clear()

        self.assertEqual(0, self.connector.snapshot().runtime_seconds)


if __name__ == "__main__":
    unittest.main()
