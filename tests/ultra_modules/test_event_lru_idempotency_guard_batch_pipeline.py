import unittest
import time
from ultra_modules.event_lru_idempotency_guard_batch_pipeline import EventBatchPipeline, LRUIdempotencyGuard

class TestEventBatchPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = EventBatchPipeline(guard_capacity=10000, max_workers=5)

    def test_normal_flow_and_sync_results(self):
        """Test processing of normal batch and result collection."""
        events = [{"event_id": f"event_{i}", "data": i} for i in range(10)]

        def processor(ev):
            return ev["data"] * 2

        results = self.pipeline.process_batch(events, processor)
        self.assertEqual(results["total"], 10)
        self.assertEqual(results["processed"], 10)
        self.assertEqual(results["skipped"], 0)
        self.assertEqual(results["failed"], 0)
        self.assertEqual(sorted(results["results"]), [i * 2 for i in range(10)])

    def test_duplicate_prevention(self):
        """Test that duplicate event_ids are skipped."""
        events = [{"event_id": "duplicate_id", "val": 1}, {"event_id": "duplicate_id", "val": 2}, {"event_id": "unique_id", "val": 3}]

        def processor(ev):
            return ev["val"]

        # Due to concurrency, one will process and one will skip
        results = self.pipeline.process_batch(events, processor)
        self.assertEqual(results["total"], 3)
        self.assertEqual(results["processed"], 2)
        self.assertEqual(results["skipped"], 1)
        self.assertEqual(results["failed"], 0)
        # 1 and 3 are expected as 1 is processed first or 2 is, one of them will be skipped.
        self.assertIn(3, results["results"])

    def test_dirty_data_resilience(self):
        """Test with dirty data like missing IDs or exceptions in processor."""
        class CustomObj:
            pass

        obj = CustomObj()
        obj.message_id = "msg_123"

        events = [
            {"event_id": ""}, # Empty ID -> treated as unique
            {"random_key": "val"}, # Missing ID -> treated as unique
            "string_event", # String directly
            None, # Will cause exception in processor if not handled
            obj,
        ]

        def processor(ev):
            if ev is None:
                raise ValueError("None not allowed")
            return "ok"

        results = self.pipeline.process_batch(events, processor)
        self.assertEqual(results["total"], 5)
        self.assertEqual(results["processed"], 4)
        self.assertEqual(results["skipped"], 0)
        self.assertEqual(results["failed"], 1)
        self.assertEqual(results["results"], ["ok", "ok", "ok", "ok"])

    def test_default_params_handling(self):
        """Test default param fallbacks when none or invalid are given."""
        pipeline = EventBatchPipeline(guard_capacity=None, max_workers=-5)
        self.assertEqual(pipeline.guard.max_size, 10000)
        self.assertEqual(pipeline.max_workers, 20)

        pipeline2 = EventBatchPipeline(guard_capacity=0, max_workers=0)
        self.assertEqual(pipeline2.guard.max_size, 10000)
        self.assertEqual(pipeline2.max_workers, 20)

        # Test empty events processing
        res = pipeline.process_batch(None, lambda x: x)
        self.assertEqual(res["total"], 0)
        self.assertTrue(res["is_done"] if "is_done" in res else True)

    def test_lru_eviction(self):
        """Test extreme boundary where LRU size is small and gets evicted."""
        # Using 1 worker for deterministic execution order
        pipeline = EventBatchPipeline(guard_capacity=3, max_workers=1)

        # Process 3 events sequentially: 1, 2, 3 -> cache becomes [1, 2, 3]
        pipeline.process_batch([{"event_id": "1"}, {"event_id": "2"}, {"event_id": "3"}], lambda x: "done")

        # Process 4th event, cache becomes [2, 3, 4]
        pipeline.process_batch([{"event_id": "4"}], lambda x: "done")

        # Now process 1, 2, 3 again.
        # Check 1: not in cache. Add 1 -> cache [3, 4, 1] (evicts 2). Processed.
        # Check 2: not in cache (evicted!). Add 2 -> cache [4, 1, 2] (evicts 3). Processed.
        # Check 3: not in cache (evicted!). Add 3 -> cache [1, 2, 3] (evicts 4). Processed.
        # Wait, if they are checked sequentially, they will ALL be processed because each one evicts the next one before it can be checked as a duplicate.

        # Let's test a scenario where we only check 1 first.
        res1 = pipeline.process_batch([{"event_id": "1"}], lambda x: "done")
        self.assertEqual(res1["processed"], 1)

        # Now cache is [3, 4, 1]. So 3 and 4 are still in cache, but 2 was evicted.
        # Let's verify 3 is skipped.
        res3 = pipeline.process_batch([{"event_id": "3"}], lambda x: "done")
        self.assertEqual(res3["processed"], 0)
        self.assertEqual(res3["skipped"], 1)

    def test_async_snapshot_pipeline(self):
        """Test non-blocking snapshot behavior."""
        events = [{"event_id": f"evt_{i}"} for i in range(10)]

        def slow_processor(ev):
            time.sleep(0.1)
            return True

        run = self.pipeline.process_batch_async(events, slow_processor)

        snapshot1 = run.snapshot()
        self.assertEqual(snapshot1["total"], 10)
        self.assertFalse(snapshot1["is_done"])

        # Wait for completion
        final_res = run.wait()
        self.assertEqual(final_res["processed"], 10)

        snapshot2 = run.snapshot()
        self.assertTrue(snapshot2["is_done"])

if __name__ == '__main__':
    unittest.main()
