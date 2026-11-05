import unittest
import math

from ultra_modules.adaptive_stream_throttler_export_formatter import (
    AdaptiveStreamThrottlerExportFormatter,
    format_export,
    _global_formatter
)

class TestAdaptiveStreamThrottlerExportFormatter(unittest.TestCase):
    def setUp(self):
        # Reset the global sequence state before each test
        _global_formatter._last_sequence = 0

    def test_normal_conditions(self):
        """Test valid dictionary data, valid window and valid sequence."""
        data = {"count": 10, "label": "test"}
        result = format_export(data=data, window=200, sequence=5)

        self.assertEqual(result["sequence"], 5)
        self.assertEqual(result["window"], 200)
        self.assertEqual(result["data"]["count"], 10)
        self.assertEqual(result["data"]["label"], "test")
        self.assertEqual(result["data"]["comments"], 0)

        expected_report = (
            "🚀 [Stream Export] Sequence: 5\n"
            "⏱️ Adaptive Window: 200ms\n"
            "✅ Data Cleaned & Ready"
        )
        self.assertEqual(result["report"], expected_report)

    def test_dirty_data_self_healing(self):
        """Test NaN and None cleaning, non-dict auto-wrap."""
        # 1. Non-dict input
        res1 = format_export(data="just a string")
        self.assertEqual(res1["data"]["value"], "just a string")
        self.assertEqual(res1["data"]["comments"], 0)

        # 2. Nested dirty data
        dirty_data = {
            "a": float("nan"),
            "b": None,
            "c": [1, None, float("nan")],
            "d": {"e": None, "f": float("nan")}
        }
        res2 = format_export(data=dirty_data)
        cleaned = res2["data"]
        self.assertEqual(cleaned["a"], 0)
        self.assertEqual(cleaned["b"], 0)
        self.assertEqual(cleaned["c"], [1, 0, 0])
        self.assertEqual(cleaned["d"]["e"], 0)
        self.assertEqual(cleaned["d"]["f"], 0)
        self.assertEqual(cleaned["comments"], 0)

    def test_missing_parameter_defaults(self):
        """Test behavior with missing/no arguments."""
        result = format_export()
        self.assertEqual(result["window"], 300)
        self.assertEqual(result["sequence"], 1) # Because default seq 0 <= _last_seq 0
        self.assertEqual(result["data"]["comments"], 0)

    def test_extreme_boundary_conditions(self):
        """Test with negative window, extremely large window, invalid data types."""
        # Negative window -> clamped to 150
        res1 = format_export(window=-50)
        self.assertEqual(res1["window"], 150)

        # Large window -> clamped to 500
        res2 = format_export(window=9999)
        self.assertEqual(res2["window"], 500)

        # Invalid window type
        res3 = format_export(window="not a number")
        self.assertEqual(res3["window"], 300)

        # NaN window
        res4 = format_export(window=float("nan"))
        self.assertEqual(res4["window"], 300)

        # Invalid sequence type
        res5 = format_export(sequence="invalid")
        self.assertTrue(res5["sequence"] > _global_formatter._last_sequence - 1)

    def test_sequence_lock_monotonicity(self):
        """Test the monotonic increasing sequence logic."""
        res1 = format_export(sequence=10)
        self.assertEqual(res1["sequence"], 10)

        # Trying to use a smaller sequence
        res2 = format_export(sequence=5)
        # Should be strictly greater than 10, so 10 + 1 = 11
        self.assertEqual(res2["sequence"], 11)

        # Trying to use the exact same sequence
        res3 = format_export(sequence=11)
        self.assertEqual(res3["sequence"], 12)

        # Increment automatically without sequence param
        res4 = format_export()
        self.assertEqual(res4["sequence"], 13)

if __name__ == '__main__':
    unittest.main() # pragma: no cover
