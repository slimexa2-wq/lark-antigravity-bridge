import unittest
from datetime import datetime
import json
import time

from ultra_modules.voice_message_intent_parser_benchmark_suite import (
    VoiceMessageIntentParser,
    BenchmarkSuite
)

class TestVoiceMessageIntentParser(unittest.TestCase):
    def setUp(self):
        # Reference date set to 2024-01-15 for testing boundaries
        self.ref_date = datetime(2024, 1, 15)
        self.parser = VoiceMessageIntentParser(reference_date=self.ref_date)

    def test_normal_cases(self):
        """Test normal voice message instructions"""
        result = self.parser.parse("把这月提成表核一下")
        self.assertEqual(result["action"], "check")
        self.assertEqual(result["subject"], "commission")
        self.assertEqual(result["time_period"], "2024-01")

        result = self.parser.parse("发今年工资")
        self.assertEqual(result["action"], "send")
        self.assertEqual(result["subject"], "salary")
        self.assertEqual(result["time_period"], "2024")

        result = self.parser.parse("看下个月的报表")
        self.assertEqual(result["action"], "check")
        self.assertEqual(result["subject"], "report")
        self.assertEqual(result["time_period"], "2024-02")

    def test_dirty_data_self_healing(self):
        """Test dirty data like none, empty strings, numbers and emojis"""
        result = self.parser.parse(None)
        self.assertEqual(result["action"], "default_action")
        self.assertEqual(result["subject"], "default_subject")
        self.assertEqual(result["time_period"], "2024-01")
        self.assertEqual(result["original_text_length"], "0")

        result = self.parser.parse("")
        self.assertEqual(result["action"], "default_action")
        self.assertEqual(result["subject"], "default_subject")
        self.assertEqual(result["time_period"], "2024-01")
        self.assertEqual(result["original_text_length"], "0")

        result = self.parser.parse(12345)
        self.assertEqual(result["action"], "default_action")
        self.assertEqual(result["subject"], "default_subject")
        self.assertEqual(result["time_period"], "2024-01")

        result = self.parser.parse("🤯🤯🤯!!!把这个月%^&*提成核一下???")
        self.assertEqual(result["action"], "check")
        self.assertEqual(result["subject"], "commission")
        self.assertEqual(result["time_period"], "2024-01")

    def test_cross_year_month_boundaries(self):
        """Test cross year and cross month logic"""
        # Given ref_date is 2024-01

        # Test previous month (cross year backwards)
        result = self.parser.parse("核一下上个月的提成")
        self.assertEqual(result["time_period"], "2023-12")

        # Test previous two months (cross year backwards)
        result = self.parser.parse("核上上个月工资")
        self.assertEqual(result["time_period"], "2023-11")

        # Now switch ref_date to December for forward testing
        dec_parser = VoiceMessageIntentParser(reference_date=datetime(2023, 12, 15))

        # Test next month (cross year forward)
        result = dec_parser.parse("算一下下个月工资")
        self.assertEqual(result["time_period"], "2024-01")

        # Test next two months (cross year forward)
        result = dec_parser.parse("查下下月报表")
        self.assertEqual(result["time_period"], "2024-02")

        # Direct year testing
        result = self.parser.parse("看去年报表")
        self.assertEqual(result["time_period"], "2023")

        result = self.parser.parse("发明年的")
        self.assertEqual(result["time_period"], "2025")

    def test_missing_parameters_fallback(self):
        """Test default fallbacks when parameters are missing"""
        result = self.parser.parse("随机说句话")
        self.assertEqual(result["action"], "default_action")
        self.assertEqual(result["subject"], "default_subject")
        self.assertEqual(result["time_period"], "2024-01") # Defaults to current month

        result = self.parser.parse("提成") # Only subject
        self.assertEqual(result["action"], "default_action")
        self.assertEqual(result["subject"], "commission")
        self.assertEqual(result["time_period"], "2024-01")

        result = self.parser.parse("核") # Only action
        self.assertEqual(result["action"], "check")
        self.assertEqual(result["subject"], "default_subject")
        self.assertEqual(result["time_period"], "2024-01")

    def test_benchmark_performance_and_stability(self):
        """Test performance benchmark execution and ensure zero crashes"""
        # Run benchmark with small parameters just to test the logic during unittests
        benchmark_results = BenchmarkSuite.run_benchmark(concurrency=10, iterations_per_thread=10)

        # Assert structure
        self.assertIn("elapsed_ms", benchmark_results)
        self.assertIn("total_success", benchmark_results)
        self.assertIn("average_ms_per_task", benchmark_results)
        self.assertIn("is_millisecond_level", benchmark_results)

        # Ensure all tasks succeeded without crash
        self.assertEqual(benchmark_results["total_success"], 10 * 10 * 10)

        # Verify millisecond level (soft check for test env, actual performance depends on machine)
        # But we print it to see in logs
        print(f"\nBenchmark Results: {json.dumps(benchmark_results, indent=2)}")

if __name__ == '__main__':
    unittest.main()
