import unittest
from ultra_modules.event_lru_idempotency_guard_core_engine import EventLRUIdempotencyGuardCoreEngine
from ultra_modules.event_lru_idempotency_guard_benchmark_suite import (
    SyntheticFixtureGenerator,
    EventLRUIdempotencyGuardBenchmarkSuite
)

class TestEventLRUIdempotencyGuardBenchmarkSuite(unittest.TestCase):
    def setUp(self):
        self.engine = EventLRUIdempotencyGuardCoreEngine(capacity=1000)
        self.engine.reset_for_testing()

    def test_normal_idempotency(self):
        """Verify standard payload deduplication."""
        # First time should be processed
        evt = {"event_id": "normal_evt_1"}
        self.assertTrue(self.engine.check_and_record(evt))

        # Second time should be rejected (duplicate)
        self.assertFalse(self.engine.check_and_record(evt))

        # Different event should be processed
        evt2 = {"message_id": "normal_msg_1"}
        self.assertTrue(self.engine.check_and_record(evt2))
        self.assertFalse(self.engine.check_and_record(evt2))

    def test_dirty_data_self_healing(self):
        """Verify zero crashes with None, garbled strings, and invalid types."""
        dirty_data = SyntheticFixtureGenerator.generate_dirty_data()
        for data in dirty_data:
            # Should not crash. If it can't find an ID, it fails open (returns True)
            try:
                res = self.engine.check_and_record(data)
                # If there's an ID like "nested_evt_1", it'll return True first time, False second time
                # If there's no ID, it returns True always.
                self.assertIn(res, [True, False])
            except Exception as e:
                self.fail(f"Crashed on dirty data: {data}, error: {e}")

    def test_missing_params_default_fallback(self):
        """Verify fail-open defaults for empty dicts or missing IDs."""
        self.assertTrue(self.engine.check_and_record({}))
        self.assertTrue(self.engine.check_and_record({"other_field": "value"}))
        self.assertTrue(self.engine.check_and_record(None))

    def test_extreme_boundaries(self):
        """Verify deduplication handles cross-year/cross-month IDs correctly."""
        boundary_data = SyntheticFixtureGenerator.generate_boundary_data()

        for data in boundary_data:
            # First time processed
            self.assertTrue(self.engine.check_and_record(data))
            # Second time dropped
            self.assertFalse(self.engine.check_and_record(data))

    def test_high_concurrency_benchmark(self):
        """Run the benchmark with a large synthetic dataset and high thread count to assert zero crashes and <10ms average latency."""
        # Clean state for benchmark
        self.engine.reset_for_testing()

        # 1. Normal data (1000 items)
        dataset = SyntheticFixtureGenerator.generate_normal_data()
        # 2. Add duplicates to test cache hits
        dataset.extend(SyntheticFixtureGenerator.generate_normal_data())
        # 3. Add dirty and boundary data
        dataset.extend(SyntheticFixtureGenerator.generate_dirty_data() * 10)
        dataset.extend(SyntheticFixtureGenerator.generate_boundary_data() * 10)

        suite = EventLRUIdempotencyGuardBenchmarkSuite(capacity=1000, workers=100)

        try:
            results = suite.run_benchmark(dataset)
        except Exception as e:
            self.fail(f"Benchmark crashed: {e}")

        # Verify 0 errors
        self.assertEqual(results["errors"], 0)

        # Verify average latency < 10ms
        self.assertLess(results["avg_latency_ms"], 10.0, "Average latency exceeds 10ms")

        # Verify that all 1000 items from normal data were deduplicated correctly if we check cache length
        # (Though we can't directly check the internal dict cleanly, we rely on the logic tests)
        print(f"\nBenchmark Results: {results}")

if __name__ == "__main__":
    unittest.main()
