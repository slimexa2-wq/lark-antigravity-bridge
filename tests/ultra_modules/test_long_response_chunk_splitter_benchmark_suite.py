import unittest
from ultra_modules.long_response_chunk_splitter_benchmark_suite import SyntheticFixtureGenerator, BenchmarkSuite
from ultra_modules.long_response_chunk_splitter_core_engine import split_long_response

class TestLongResponseChunkSplitterBenchmarkSuite(unittest.TestCase):

    def setUp(self):
        self.generator = SyntheticFixtureGenerator(default_max_size=1000)
        self.benchmark = BenchmarkSuite(concurrency=10) # Lower concurrency for quick unit tests

    def test_normal_operation_fixtures(self):
        """Test generation of normal and empty fixtures."""
        normal_data = self.generator.generate("normal", size=500)
        self.assertTrue(isinstance(normal_data, str))
        self.assertTrue(len(normal_data) > 0)
        self.assertTrue(len(normal_data) <= 500)

        empty_data = self.generator.generate("empty")
        self.assertEqual(empty_data, "")

    def test_dirty_data_self_healing(self):
        """Test generation and handling of garbage data and None values."""
        none_data = self.generator.generate("none")
        self.assertIsNone(none_data)

        garbage_data = self.generator.generate("garbage", size=100)
        self.assertTrue(isinstance(garbage_data, str))
        self.assertIn("乱码测试", garbage_data)

        # Ensure benchmark does not crash with dirty data
        results = self.benchmark.run_benchmark(
            splitter_func=split_long_response,
            fixture_types=["garbage", "none"]
        )
        self.assertTrue(results["zero_crash_verified"])
        self.assertEqual(results["failed_runs"], 0)

    def test_default_parameters_fallback(self):
        """Test that default values kick in when bad parameters are passed."""
        # Generator fallbacks
        bad_generator = SyntheticFixtureGenerator(default_max_size="invalid")
        self.assertEqual(bad_generator.default_max_size, 50000)

        # Generator parameter fallbacks
        res = bad_generator.generate(fixture_type=None, size="invalid")
        self.assertTrue(isinstance(res, str))
        self.assertTrue(len(res) > 0)

        # Benchmark fallbacks
        bad_benchmark = BenchmarkSuite(concurrency=-50)
        self.assertEqual(bad_benchmark.concurrency, 100)

        # Benchmark parameter fallbacks
        res_bench = bad_benchmark.run_benchmark(splitter_func=split_long_response, fixture_types="not a list")
        self.assertEqual(res_bench["total_runs"], 100) # Defaults to 100 concurrency with 5 default fixtures

    def test_extreme_boundary_conditions(self):
        """Test extreme boundaries like cross year/month generation and ultra huge datasets."""
        # Cross year/month
        cross_data = self.generator.generate("cross_year_month", size=2000)
        self.assertTrue(isinstance(cross_data, str))
        self.assertIn("2024-01-01 00:00:00", cross_data)

        # Ensure splitter can handle it
        chunks = split_long_response(cross_data, max_chunk_size=500)
        self.assertTrue(len(chunks) > 1)

        # Check extremely large concurrency (scaled down slightly for unit test limits but proves concept)
        heavy_benchmark = BenchmarkSuite(concurrency=200)
        results = heavy_benchmark.run_benchmark(
            splitter_func=split_long_response,
            fixture_types=["cross_year_month"]
        )
        self.assertTrue(results["zero_crash_verified"])
        self.assertEqual(results["total_runs"], 200)

    def test_millisecond_response_and_zero_crash(self):
        """Test the benchmark suite properly tracks performance metrics and zero-crash capability."""
        # Run a small benchmark suite
        results = self.benchmark.run_benchmark(
            splitter_func=split_long_response,
            fixture_types=["normal", "empty", "garbage", "none", "cross_year_month"]
        )

        self.assertTrue(results["zero_crash_verified"])
        self.assertEqual(results["failed_runs"], 0)
        self.assertTrue(results["total_time_ms"] > 0)
        self.assertTrue(results["millisecond_response_verified"])
        self.assertEqual(results["total_runs"], 10)
        self.assertEqual(len(results["details"]), 10)
        for detail in results["details"]:
            self.assertTrue(detail["success"])
            self.assertIsNone(detail["error"])

if __name__ == '__main__':
    unittest.main()
