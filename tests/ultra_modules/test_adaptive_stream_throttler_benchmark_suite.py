import unittest
import time
from datetime import datetime, timezone
from ultra_modules.adaptive_stream_throttler_benchmark_suite import (
    SyntheticFixtureGenerator,
    AdaptiveStreamThrottlerBenchmarkSuite
)
from ultra_modules.adaptive_stream_throttler_core_engine import process_stream_event

class TestAdaptiveStreamThrottlerBenchmarkSuite(unittest.TestCase):

    def setUp(self):
        self.benchmark_suite = AdaptiveStreamThrottlerBenchmarkSuite(concurrency=50)

    def test_1_normal_data_benchmark(self):
        """Test processing of normal, sequentially ordered datasets."""
        dataset = SyntheticFixtureGenerator.generate_normal_dataset(size=200)
        result = self.benchmark_suite.run_benchmark(dataset)

        self.assertEqual(result['processed'], 200)
        self.assertEqual(result['errors'], 0)
        self.assertGreater(result['emitted'], 0)
        # Verify millisecond responsiveness
        self.assertLess(result['avg_response_ms'], 10.0)

    def test_2_dirty_data_self_healing(self):
        """Test processing of dirty data, ensuring zero crash and proper handling."""
        dataset = SyntheticFixtureGenerator.generate_dirty_dataset(size=200)
        result = self.benchmark_suite.run_benchmark(dataset)

        self.assertEqual(result['processed'], 200)
        self.assertEqual(result['errors'], 0)  # Core engine must silently drop or self-heal
        # The number of emitted events will be lower because bad events are dropped
        self.assertLess(result['avg_response_ms'], 10.0)

    def test_3_zero_config_default_fallback(self):
        """Test processing empty configurations and missing state params safely."""
        dataset = [{'seq': 1, 'data': 'A'}]
        # Process without initialized state
        state, should_emit, cleaned_event = process_stream_event(None, dataset[0])
        self.assertTrue(should_emit)
        self.assertEqual(cleaned_event['seq'], 1)
        self.assertTrue(state['last_emit_time'] > 0)
        self.assertEqual(state['window_size'], 150)

        # Test benchmark with completely empty config
        empty_suite = AdaptiveStreamThrottlerBenchmarkSuite()
        res = empty_suite.run_benchmark(dataset)
        self.assertEqual(res['processed'], 1)
        self.assertEqual(res['errors'], 0)

    def test_4_cross_year_month_boundary(self):
        """Test timestamps occurring across year/month boundaries."""
        dataset = SyntheticFixtureGenerator.generate_cross_boundary_dataset()

        # Simulate End of Year boundary (e.g., Dec 31st 23:59:59.900)
        dt = datetime(2023, 12, 31, 23, 59, 59, 900000, tzinfo=timezone.utc)
        boundary_time_ms = int(dt.timestamp() * 1000)

        result = self.benchmark_suite.run_benchmark(dataset, start_time_ms=boundary_time_ms)
        self.assertEqual(result['processed'], len(dataset))
        self.assertEqual(result['errors'], 0)
        # Should cross smoothly to 2024 and emit
        self.assertGreater(result['emitted'], 0)
        self.assertLess(result['avg_response_ms'], 10.0)

    def test_5_ultra_high_concurrency_stress(self):
        """Test zero-crash and response time under heavy concurrent stress."""
        # Use a large payload dataset
        dataset = SyntheticFixtureGenerator.generate_normal_dataset(size=1000)

        # We process this with concurrent workers accessing the pure function
        # to ensure it behaves deterministically and without crashes
        stress_suite = AdaptiveStreamThrottlerBenchmarkSuite(concurrency=100)
        result = stress_suite.run_stress_test(dataset)

        self.assertEqual(result['processed'], 1000)
        self.assertEqual(result['errors'], 0)
        self.assertLess(result['avg_response_ms'], 50.0)  # slightly looser due to threading overhead

if __name__ == '__main__':
    unittest.main()
