import unittest
import threading
from ultra_modules.event_lru_idempotency_guard_core_engine import EventLRUIdempotencyGuardCoreEngine

class UnstringifiableObj:
    def __str__(self):
        raise ValueError("Cannot convert to string")

class TestEventLRUIdempotencyGuardCoreEngine(unittest.TestCase):
    def setUp(self):
        self.guard = EventLRUIdempotencyGuardCoreEngine()
        self.guard.reset_for_testing()
        self.guard.capacity = 1000

    def test_singleton_and_invalid_capacity_healing(self):
        self.guard.reset_for_testing()
        EventLRUIdempotencyGuardCoreEngine._instance = None
        """Test singleton nature and silent self-healing for invalid capacity."""
        guard1 = EventLRUIdempotencyGuardCoreEngine(capacity=-10)
        guard2 = EventLRUIdempotencyGuardCoreEngine(capacity="invalid")
        self.assertIs(guard1, guard2)
        # Should fallback to default 1000
        self.assertEqual(guard1.capacity, 1000)

    def test_normal_flow_lru_eviction(self):
        """Test standard ID extraction, duplicate detection, and LRU eviction."""
        # Force small capacity for testing eviction
        self.guard.capacity = 3

        # 1. New event should pass
        self.assertTrue(self.guard.check_and_record({"event_id": "event_1"}))
        # 2. Same event should be blocked
        self.assertFalse(self.guard.check_and_record({"event_id": "event_1"}))

        # 3. Add more events to trigger eviction
        self.assertTrue(self.guard.check_and_record({"message_id": "msg_2"}))
        self.assertTrue(self.guard.check_and_record({"header": {"event_id": "event_3"}}))
        self.assertTrue(self.guard.check_and_record({"event": {"message_id": "msg_4"}}))

        # event_1 should be evicted now because capacity is 3 (2, 3, 4 are in)
        self.assertTrue(self.guard.check_and_record({"event_id": "event_1"}))

    def test_dirty_data_self_healing(self):
        """Test dirty IDs (whitespace, non-strings) are handled correctly."""
        self.assertTrue(self.guard.check_and_record({"event_id": "  dirty_id  "}))
        # Should block the clean version
        self.assertFalse(self.guard.check_and_record({"event_id": "dirty_id"}))

        # Int parsing
        self.assertTrue(self.guard.check_and_record({"event_id": 12345}))
        self.assertFalse(self.guard.check_and_record({"event_id": "12345"}))

    def test_missing_params_fallback(self):
        """Test missing IDs default to passing through (fail-open)."""
        # Empty dict
        self.assertTrue(self.guard.check_and_record({}))
        # List instead of dict
        self.assertTrue(self.guard.check_and_record(["not", "a", "dict"]))
        # Dict with no ID fields
        self.assertTrue(self.guard.check_and_record({"some": "data"}))
        # Unstringifiable ID should fallback to None and pass through
        self.assertTrue(self.guard.check_and_record({"event_id": UnstringifiableObj()}))

    def test_extreme_boundary_multithreading(self):
        """Test thread safety under high concurrency."""
        self.guard.capacity = 1000

        def worker(event_id, results, index):
            results[index] = self.guard.check_and_record({"event_id": event_id})

        threads = []
        results = [None] * 100

        # 100 threads trying to process the exact same event ID concurrently
        for i in range(100):
            t = threading.Thread(target=worker, args=("concurrent_event", results, i))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Only one thread should have seen it as a new event (True)
        # The other 99 should have been blocked (False)
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 99)

if __name__ == "__main__":
    unittest.main()
