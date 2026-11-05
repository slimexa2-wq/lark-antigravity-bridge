import unittest
import math
from typing import Dict, Any

from ultra_modules.ws_exponential_backoff_export_formatter import WSExponentialBackoffExportFormatter

class TestWSExponentialBackoffExportFormatter(unittest.TestCase):

    def setUp(self):
        self.formatter = WSExponentialBackoffExportFormatter(base_delay=1.0, max_delay=60.0, jitter_factor=0.5)

    def test_normal_operation(self):
        """Test case 1: Normal operation with valid inputs."""
        state = {
            "attempt": 2,
            "connection_uptime": 3600.5,
            "status": "reconnecting",
            "error_count": 3
        }
        export = self.formatter.generate_export_data(state)
        self.assertEqual(export["attempt"], 2)
        self.assertEqual(export["connection_uptime"], 3600.5)
        self.assertEqual(export["status"], "reconnecting")
        self.assertEqual(export["error_count"], 3)
        self.assertEqual(export["comments"], 0)

        # Base delay 1.0 * 2^2 = 4.0. Jitter up to 2.0. Expected range: [2.0, 6.0]
        self.assertTrue(2.0 <= export["next_retry_delay"] <= 6.0)

        report = self.formatter.generate_report(state)
        self.assertIn("【WS状态】reconnecting | 运行时长: 3600.5s", report)
        self.assertIn("【重连机制】第2次退避 | 下次重试: ", report)
        self.assertIn("【健康度】异常次数: 3 | 诊断备注: 0", report)

    def test_dirty_data_self_healing(self):
        """Test case 2: Dirty data self-healing (None, NaN, Inf, String for numbers)."""
        state = {
            "attempt": "invalid",
            "connection_uptime": math.nan,
            "status": "   ",
            "error_count": float('inf')
        }
        export = self.formatter.generate_export_data(state)

        # Self-healing should convert invalid numbers to default 0.0, status to default
        self.assertEqual(export["attempt"], 0)
        self.assertEqual(export["connection_uptime"], 0.0)
        self.assertEqual(export["status"], "disconnected")
        self.assertEqual(export["error_count"], 0)
        self.assertEqual(export["comments"], 0)

        report = self.formatter.generate_report(state)
        lines = report.split("\n")
        self.assertEqual(len(lines), 3)

    def test_missing_parameters_fallback(self):
        """Test case 3: Missing parameters fallback."""
        export = self.formatter.generate_export_data(None)

        self.assertEqual(export["attempt"], 0)
        self.assertEqual(export["connection_uptime"], 0.0)
        self.assertEqual(export["status"], "disconnected")
        self.assertEqual(export["error_count"], 0)
        self.assertEqual(export["comments"], 0)

        # Base delay 1.0 * 2^0 = 1.0. Jitter range [-0.5, 0.5]. Target [0.5, 1.5]
        self.assertTrue(0.5 <= export["next_retry_delay"] <= 1.5)

        report = self.formatter.generate_report({})
        self.assertIn("【WS状态】disconnected | 运行时长: 0.0s", report)

    def test_extreme_boundaries(self):
        """Test case 4: Extreme boundaries (very large attempts clamped by max_delay)."""
        state = {
            "attempt": 1000,  # Huge attempt
        }
        export = self.formatter.generate_export_data(state)

        # Max delay is 60.0, it should be clamped to 60.0
        self.assertEqual(export["next_retry_delay"], 60.0)

    def test_calculation_testing(self):
        """Test case 5: Explicit test of calculate_backoff with multiple iterations to ensure bounds."""
        for attempt in range(10):
            val = self.formatter.calculate_backoff(attempt)
            self.assertTrue(0.0 <= val <= 60.0)

        # Test negative attempt
        val = self.formatter.calculate_backoff(-5)
        # Should be treated as attempt=0. Base 1.0, Jitter [-0.5, 0.5], Range [0.5, 1.5]
        self.assertTrue(0.5 <= val <= 1.5)

if __name__ == "__main__":
    unittest.main()
