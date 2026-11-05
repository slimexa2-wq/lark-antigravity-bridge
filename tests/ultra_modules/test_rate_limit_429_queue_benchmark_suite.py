import unittest
from unittest.mock import patch
from ultra_modules.rate_limit_429_queue_benchmark_suite import (
    generate_synthetic_fixtures,
    run_benchmark_suite,
    evaluate_benchmark_results
)

class TestRateLimit429QueueBenchmarkSuite(unittest.TestCase):

    def test_normal_benchmark_execution(self):
        """Test 1: Normal benchmark execution with valid fixtures."""
        fixtures = generate_synthetic_fixtures(num_requests=100)
        self.assertEqual(len(fixtures), 100)

        results = run_benchmark_suite(fixtures=fixtures, capacity=10, refill_rate=5.0)

        self.assertIn("total_requests", results)
        self.assertEqual(results["total_requests"], 100)
        self.assertTrue(results["is_zero_crash"])

        evaluation = evaluate_benchmark_results(results)
        self.assertTrue(evaluation)

    def test_dirty_data_self_healing(self):
        """Test 2: Dirty data self-healing (None, negative ints, strings)."""
        # Test generate_synthetic_fixtures self healing
        fixtures_str = generate_synthetic_fixtures("invalid")
        self.assertEqual(len(fixtures_str), 1000)

        fixtures_none = generate_synthetic_fixtures(None)
        self.assertEqual(len(fixtures_none), 1000)

        fixtures_neg = generate_synthetic_fixtures(-500)
        self.assertEqual(len(fixtures_neg), 1000)

        # Test evaluate_benchmark_results self healing
        eval_none = evaluate_benchmark_results(None)
        self.assertFalse(eval_none)

        eval_str = evaluate_benchmark_results("not a dict")
        self.assertFalse(eval_str)

        # Run benchmark with dirty capacity/refill_rate
        fixtures = generate_synthetic_fixtures(num_requests=50)
        results = run_benchmark_suite(fixtures=fixtures, capacity="dirty", refill_rate=None)
        self.assertTrue(results["is_zero_crash"])
        self.assertTrue(evaluate_benchmark_results(results))

    def test_missing_parameter_defaults(self):
        """Test 3: Missing parameter defaults."""
        # Calling functions without args
        fixtures = generate_synthetic_fixtures()
        self.assertEqual(len(fixtures), 1000)

        results = run_benchmark_suite()
        self.assertTrue(results["is_zero_crash"])
        self.assertTrue(results["is_millisecond_response"])
        self.assertTrue(evaluate_benchmark_results(results))

    def test_extreme_boundaries(self):
        """Test 4: Extreme boundaries (large concurrency)."""
        fixtures = generate_synthetic_fixtures(num_requests=50000)
        self.assertEqual(len(fixtures), 50000)

        # Test benchmark with extremely high throughput simulation
        results = run_benchmark_suite(fixtures=fixtures, capacity=1000, refill_rate=500.0)
        self.assertEqual(results["total_requests"], 50000)
        self.assertTrue(results["is_zero_crash"])
        self.assertTrue(evaluate_benchmark_results(results))

    def test_synthetic_fixture_content_check(self):
        """Test 5: Synthetic fixture content check (cross-year, nulls, gibberish)."""
        fixtures = generate_synthetic_fixtures(num_requests=20)

        has_none = False
        has_gibberish = False
        has_cross_year = False
        has_cross_month = False
        has_empty_dict = False
        has_normal = False

        for f in fixtures:
            if f is None:
                has_none = True
            elif isinstance(f, str) and f == "gibberish!@#":
                has_gibberish = True
            elif isinstance(f, dict):
                if not f:
                    has_empty_dict = True
                elif f.get("created_at") == 1704067199:
                    has_cross_year = True
                elif f.get("created_at") == 1706745599:
                    has_cross_month = True
                elif f.get("type") == "normal":
                    has_normal = True

        self.assertTrue(has_none)
        self.assertTrue(has_gibberish)
        self.assertTrue(has_cross_year)
        self.assertTrue(has_cross_month)
        self.assertTrue(has_empty_dict)
        self.assertTrue(has_normal)

    @patch("ultra_modules.rate_limit_429_queue_benchmark_suite.process_request")
    def test_exception_handling_in_benchmark(self, mock_process_request):
        """Test exception handling in benchmark suite."""
        mock_process_request.side_effect = Exception("Simulated error")
        fixtures = generate_synthetic_fixtures(num_requests=5)
        results = run_benchmark_suite(fixtures=fixtures)
        self.assertEqual(results["exceptions_caught"], 1)
        self.assertFalse(results["is_zero_crash"])
        self.assertFalse(evaluate_benchmark_results(results))

    @patch("ultra_modules.rate_limit_429_queue_benchmark_suite.process_queue")
    def test_infinite_loop_prevention(self, mock_process_queue):
        """Test infinite loop prevention in fast forward phase."""
        # Setup so process_request queues items
        with patch("ultra_modules.rate_limit_429_queue_benchmark_suite.process_request") as mock_pr:
            # Simulate state with queue
            def mock_pr_side_effect(state, req, current_time):
                state["queue"].append(req)
                return state, False

            mock_pr.side_effect = mock_pr_side_effect

            # Make process_queue return empty processed list to trigger break
            def mock_pq_side_effect(state, current_time):
                return state, []
            mock_process_queue.side_effect = mock_pq_side_effect

            fixtures = generate_synthetic_fixtures(num_requests=5)
            results = run_benchmark_suite(fixtures=fixtures, capacity=1, refill_rate=1.0)

            self.assertEqual(results["queued_remaining"], 5)

if __name__ == "__main__":
    unittest.main()
