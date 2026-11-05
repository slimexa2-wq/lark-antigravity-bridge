import unittest
import json
from ultra_modules.adaptive_stream_throttler_cli_one_click import run_one_click_cli, DualModeAdapter, AdaptiveStreamThrottler

class TestAdaptiveStreamThrottlerCliOneClick(unittest.TestCase):
    def test_01_normal_flow_default_json(self):
        result = run_one_click_cli()
        data = json.loads(result)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["data"]["msg"], "hello")
        self.assertEqual(data[1]["data"]["msg"], "world")
        self.assertTrue("sequence" in data[0])
        self.assertTrue("timestamp" in data[0])

    def test_02_missing_param_fallback(self):
        # Even if weird mode is provided, falls back to JSON
        result = run_one_click_cli(mode="weird_mode", data_to_push=[{"key": "value"}])
        data = json.loads(result)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["data"]["key"], "value")

    def test_03_dirty_data_self_healing(self):
        # Dirty data like plain strings should be self-healed by DualModeAdapter
        res_json = DualModeAdapter.format_output(["dirty_string", 123])
        data = json.loads(res_json)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["payload"], "dirty_string")
        self.assertEqual(data[1]["payload"], "123")

    def test_04_extreme_boundary_throttling(self):
        # Test throttling logic
        throttler = AdaptiveStreamThrottler(min_window_ms=10, max_window_ms=50)
        throttler.push({"event": 1})
        throttler.push({"event": 2})
        throttler.force_flush()

        batches = throttler.get_flushed_batches()
        self.assertEqual(len(batches), 1)
        self.assertEqual(len(batches[0]), 2)
        self.assertEqual(batches[0][0]["sequence"], 1)
        self.assertEqual(batches[0][1]["sequence"], 2)
        throttler.stop()

    def test_05_dual_mode_excel_output(self):
        # Excel mode
        result = run_one_click_cli(mode="excel", data_to_push=[{"a": 1}, {"b": 2}])
        self.assertTrue("sequence" in result)
        self.assertTrue("data" in result)
        self.assertTrue("timestamp" in result)
        lines = [line for line in result.strip().split("\n") if line]
        self.assertTrue(len(lines) > 1)  # Header + at least 1 row

if __name__ == "__main__":
    unittest.main()
