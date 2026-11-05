import unittest
from ultra_modules.mobile_table_digest_formatter_benchmark_suite import (
    format_mobile_table_digest,
    generate_synthetic_fixtures,
    run_performance_benchmark
)

class TestMobileTableDigestFormatterBenchmarkSuite(unittest.TestCase):

    def test_normal_conditions(self):
        """Test with valid dictionary inputs"""
        data = [
            {"title": "Revenue", "value": "50000"},
            {"name": "Expenses", "amount": "20000"},
            {"title": "Profit", "value": "30000"},
            {"title": "Ignored", "value": "1000"}
        ]
        result = format_mobile_table_digest(data)

        self.assertIn("Item: Revenue | Value: 50000", result)
        self.assertIn("Item: Expenses | Value: 20000", result)
        self.assertIn("Item: Profit | Value: 30000", result)
        self.assertNotIn("Item: Ignored | Value: 1000", result)
        self.assertIn("[Attachment Card]", result)
        self.assertIn("Complete Table Data (4 rows)", result)
        self.assertNotIn("ANOMALY", result)

    def test_dirty_data_self_healing(self):
        """Test with non-dicts, garbled values, unparseable floats"""
        # We need to make sure the "Bad" item is within the first 3 lines
        # since format_mobile_table_digest only shows 3 lines.
        data = [
            {"title": "Good", "value": "10"},
            {"title": "Bad", "value": "abc"},
            "Just a string",
            12345
        ]
        result = format_mobile_table_digest(data)

        self.assertIn("Item: Unnamed Item | Value: 0", result)
        self.assertIn("Item: Good | Value: 10", result)
        self.assertIn("⚠️ [ANOMALY] Item: Bad | Value: abc", result)
        self.assertIn("Detected 1 anomalies.", result)
        self.assertIn("Complete Table Data (4 rows)", result)

    def test_missing_parameter_fallback(self):
        """Test with None or empty inputs to ensure default fallbacks work"""
        result_none = format_mobile_table_digest(None)
        self.assertIn("- Empty Slot -", result_none)
        self.assertEqual(result_none.count("- Empty Slot -"), 3)
        self.assertIn("Complete Table Data (0 rows)", result_none)

        result_empty = format_mobile_table_digest([])
        self.assertIn("- Empty Slot -", result_empty)
        self.assertIn("Complete Table Data (0 rows)", result_empty)

        # Test with single dict instead of list
        result_dict = format_mobile_table_digest({"title": "Single", "value": "100"})
        self.assertIn("Item: Single | Value: 100", result_dict)
        self.assertIn("- Empty Slot -", result_dict)
        self.assertIn("Complete Table Data (1 rows)", result_dict)

    def test_extreme_boundaries(self):
        """Test with extreme negative, extremely large numbers to trigger anomaly highlighting"""
        data = [
            {"title": "Extreme Neg", "value": "-1000"},
            {"title": "Extreme Pos", "value": "2000000"},
            {"title": "Valid Zero", "value": "0", "extra": "field"},
            {"title": "Zero with nothing else", "value": "0"}
        ]
        result = format_mobile_table_digest(data)

        self.assertIn("⚠️ [ANOMALY] Item: Extreme Neg | Value: -1000", result)
        self.assertIn("⚠️ [ANOMALY] Item: Extreme Pos | Value: 2000000", result)
        self.assertIn("Item: Valid Zero | Value: 0", result) # Shouldn't be anomaly
        self.assertIn("Detected 2 anomalies.", result)

        # Test valid zero pass condition
        data_valid_zero = [{"title": "Only zero", "value": "0", "extra": 1}]
        res_valid_zero = format_mobile_table_digest(data_valid_zero)
        self.assertIn("Item: Only zero | Value: 0", res_valid_zero)
        self.assertNotIn("ANOMALY", res_valid_zero)

        # Test valid zero pass condition with bad float cast that still reaches 0 fallback
        data_fallback_zero = [{"title": "Only zero", "value": []}] # lists are unhashable/uncastable to float
        res_fallback_zero = format_mobile_table_digest(data_fallback_zero)
        self.assertIn("⚠️ [ANOMALY] Item: Only zero | Value: []", res_fallback_zero)

    def test_performance_benchmark(self):
        """Test that synthetic fixture processing works and performance benchmark passes without crash"""
        success, message, duration = run_performance_benchmark()
        self.assertTrue(success, f"Benchmark failed: {message}")
        self.assertGreater(duration, 0)
        self.assertLess(duration, 500) # Should be fast

    def test_performance_benchmark_failure(self):
        """Test performance benchmark error paths"""
        import unittest.mock as mock
        # Test crash branch
        with mock.patch("ultra_modules.mobile_table_digest_formatter_benchmark_suite.format_mobile_table_digest", side_effect=Exception("Test Crash")):
            success, message, duration = run_performance_benchmark()
            self.assertFalse(success)
            self.assertIn("Crash detected: Test Crash", message)

        # Test slow branch
        with mock.patch("ultra_modules.mobile_table_digest_formatter_benchmark_suite.time.time", side_effect=[0, 1.0]): # 1000ms duration
            success, message, duration = run_performance_benchmark()
            self.assertFalse(success)
            self.assertIn("Performance too slow", message)

    def test_synthetic_fixture_generation(self):
        """Test that synthetic fixtures generates correct count of items"""
        data = generate_synthetic_fixtures(100)
        # Because we append 2 items sometimes, it can be more than 100
        self.assertGreaterEqual(len(data), 100)
        self.assertLessEqual(len(data), 150)

    def test_coverage_gap_unparseable_value_is_zero(self):
        """Test unparseable but value == 0 and len > 1"""
        # This will raise ValueError/TypeError on float cast because of some reason?
        # Actually value='0' won't raise ValueError on float().
        # We need a custom object that raises ValueError on float() but str(obj) == "0"

        class MockZeroStr:
            def __str__(self): return "0"
            def __float__(self): raise ValueError("No float")

        data = [{"title": "Zero", "value": MockZeroStr(), "extra": "field"}]
        res = format_mobile_table_digest(data)
        self.assertNotIn("ANOMALY", res)

if __name__ == "__main__":
    unittest.main()
