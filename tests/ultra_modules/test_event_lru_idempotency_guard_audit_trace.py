import unittest
from unittest.mock import patch
import collections
from ultra_modules.event_lru_idempotency_guard_audit_trace import EventIdempotencyGuard, DifferenceComparator, check_event, _DEFAULT_GUARD

class TestEventLRUIdempotencyGuard(unittest.TestCase):

    def setUp(self):
        # Clear the global instance before each test
        _DEFAULT_GUARD.cache.clear()
        _DEFAULT_GUARD.audit_logger.clear()

    def test_difference_comparator_normal(self):
        """Test the structural difference comparator with normal dictionary data."""
        old_data = {"key1": "val1", "nested": {"a": 1, "b": 2}, "list": [1, 2]}
        new_data = {"key1": "val2", "nested": {"a": 1, "c": 3}, "new_key": "val3"}

        diff = DifferenceComparator.compare(old_data, new_data)

        self.assertIn("key1", diff)
        self.assertEqual(diff["key1"]["type"], "modified")
        self.assertEqual(diff["key1"]["old"], "val1")
        self.assertEqual(diff["key1"]["new"], "val2")

        self.assertIn("nested", diff)
        self.assertEqual(diff["nested"]["type"], "modified")
        self.assertIn("b", diff["nested"]["diff"])
        self.assertEqual(diff["nested"]["diff"]["b"]["type"], "removed")
        self.assertIn("c", diff["nested"]["diff"])
        self.assertEqual(diff["nested"]["diff"]["c"]["type"], "added")

        self.assertIn("new_key", diff)
        self.assertEqual(diff["new_key"]["type"], "added")

        self.assertIn("list", diff)
        self.assertEqual(diff["list"]["type"], "removed")

    def test_difference_comparator_dirty_data(self):
        """Test the structural difference comparator with invalid/dirty data."""
        self.assertEqual(DifferenceComparator.compare("string", "string"), {})

        diff = DifferenceComparator.compare("string1", "string2")
        self.assertEqual(diff, {"old": "string1", "new": "string2"})

        diff2 = DifferenceComparator.compare({"a": 1}, None)
        self.assertEqual(diff2, {"old": {"a": 1}, "new": None})

    def test_guard_normal_flow_and_deduplication(self):
        """Test normal idempotency checking and deduplication."""
        guard = EventIdempotencyGuard(capacity=10)

        event1 = {"event_id": "evt_123", "data": "first"}
        # First time should pass
        self.assertTrue(guard.check(event1))
        self.assertIn("evt_123", guard.cache)

        # Exact duplicate should be blocked
        self.assertFalse(guard.check(event1))

        # Duplicate with different data should be blocked, but diff tracked
        event1_mod = {"event_id": "evt_123", "data": "modified"}
        self.assertFalse(guard.check(event1_mod))

        logs = guard.get_audit_logs()
        duplicate_logs = [log for log in logs if log["action"] == "duplicate_detected"]
        self.assertEqual(len(duplicate_logs), 2)

        # Verify the diff was captured
        last_diff = duplicate_logs[-1]["details"]["diff"]
        self.assertIn("data", last_diff)
        self.assertEqual(last_diff["data"]["type"], "modified")
        self.assertEqual(last_diff["data"]["old"], "first")
        self.assertEqual(last_diff["data"]["new"], "modified")

    def test_guard_dirty_data_self_healing(self):
        """Test guard's handling of malformed or unexpected data structures."""
        guard = EventIdempotencyGuard()

        # 1. Null data
        self.assertTrue(guard.check(None))
        logs = guard.get_audit_logs()
        self.assertEqual(logs[-1]["action"], "check_skipped")
        self.assertEqual(logs[-1]["details"]["reason"], "Null event_data")

        # 2. String instead of dict
        self.assertTrue(guard.check("not_a_dict"))
        logs = guard.get_audit_logs()
        extract_fail = [log for log in logs if log["action"] == "extract_id_failed"][-1]
        self.assertEqual(extract_fail["details"]["reason"], "Not a dictionary")
        self.assertEqual(extract_fail["details"]["type"], "str")

        # 3. Dict with no identifiable ID
        self.assertTrue(guard.check({"random": "data"}))
        logs = guard.get_audit_logs()
        extract_fail = [log for log in logs if log["action"] == "extract_id_failed"][-1]
        self.assertEqual(extract_fail["details"]["reason"], "No valid ID found in payload")

        # 4. Deeply nested dirty data for ID extraction
        # e.g., 'header' is a string not a dict
        event = {"header": "invalid_string", "message_id": "msg_001"}
        self.assertTrue(guard.check(event))
        self.assertFalse(guard.check(event)) # Second time blocks

        # 'event' and 'message' are strings
        event2 = {"event": "invalid", "message_id": "msg_002"}
        self.assertTrue(guard.check(event2))

        # List instead of string for ID
        event3 = {"event_id": ["list", "not", "string"], "message_id": "fallback_msg_id"}
        self.assertTrue(guard.check(event3))
        self.assertIn("fallback_msg_id", guard.cache)

    def test_guard_missing_param_fallback_extreme_boundary(self):
        """Test missing params defaulting and extreme boundary behaviors like eviction."""
        # Extreme boundary: zero or negative capacity should fallback to default (1000)
        guard1 = EventIdempotencyGuard(capacity=0)
        self.assertEqual(guard1.capacity, 1000)

        guard2 = EventIdempotencyGuard(capacity=-50)
        self.assertEqual(guard2.capacity, 1000)

        guard3 = EventIdempotencyGuard(capacity="invalid_str")
        self.assertEqual(guard3.capacity, 1000)

        # Test LRU eviction policy at small capacity
        guard = EventIdempotencyGuard(capacity=3)

        # Fill cache
        guard.check({"event_id": "evt_1"})
        guard.check({"event_id": "evt_2"})
        guard.check({"event_id": "evt_3"})

        self.assertEqual(list(guard.cache.keys()), ["evt_1", "evt_2", "evt_3"])

        # Access evt_1 to make it recently used
        self.assertFalse(guard.check({"event_id": "evt_1"}))
        self.assertEqual(list(guard.cache.keys()), ["evt_2", "evt_3", "evt_1"])

        # Add new event to trigger eviction
        guard.check({"event_id": "evt_4"})

        # evt_2 should be evicted because evt_1 was recently accessed
        self.assertNotIn("evt_2", guard.cache)
        self.assertEqual(list(guard.cache.keys()), ["evt_3", "evt_1", "evt_4"])

        logs = guard.get_audit_logs()
        eviction_log = [log for log in logs if log["action"] == "cache_eviction"][-1]
        self.assertEqual(eviction_log["details"]["evicted_id"], "evt_2")

    def test_global_helper_and_catastrophic_failure(self):
        """Test one-click access helper and its fault tolerance."""
        # Normal usage of check_event
        self.assertTrue(check_event({"event_id": "global_1"}))
        self.assertFalse(check_event({"event_id": "global_1"}))

        # Simulate a catastrophic failure inside the guard to test the global fallback
        with patch.object(_DEFAULT_GUARD, 'check', side_effect=Exception("Catastrophic error")):
            # It should gracefully log error and return True (allow through)
            self.assertTrue(check_event({"event_id": "global_fail"}))
