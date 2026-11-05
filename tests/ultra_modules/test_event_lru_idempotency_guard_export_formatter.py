import math
import unittest
from typing import Any, Dict

from ultra_modules.event_lru_idempotency_guard_export_formatter import (
    LRUIdempotencyGuard,
    clean_data,
    process_and_export
)

class TestEventLRUIdempotencyGuardExportFormatter(unittest.TestCase):

    def setUp(self):
        self.guard = LRUIdempotencyGuard(capacity=10)

    def test_normal_condition(self):
        event_id = "evt_12345"
        data = {"user": "alice", "score": 100, "comments": 5}

        is_new, cleaned, report = process_and_export(event_id, data, guard=self.guard)

        self.assertTrue(is_new)
        self.assertEqual(cleaned["user"], "alice")
        self.assertEqual(cleaned["score"], 100)
        self.assertEqual(cleaned["comments"], 0)

        self.assertIn("evt_12345", report)
        self.assertIn("New Event", report)

    def test_dirty_data_self_healing(self):
        data = {
            "val1": float('nan'),
            "val2": None,
            "nested": {
                "comments": "should be 0",
                "val3": float('nan')
            },
            "list_val": [None, float('nan'), {"comments": 100}]
        }

        _, cleaned, _ = process_and_export("evt_dirty", data, guard=self.guard)

        self.assertEqual(cleaned["val1"], 0)
        self.assertEqual(cleaned["val2"], 0)
        self.assertEqual(cleaned["nested"]["comments"], 0)
        self.assertEqual(cleaned["nested"]["val3"], 0)
        self.assertEqual(cleaned["list_val"], [0, 0, {"comments": 0}])

    def test_missing_parameters(self):
        # Missing event_id and data
        is_new, cleaned, report = process_and_export(guard=self.guard)

        self.assertTrue(is_new)
        self.assertEqual(cleaned, {})
        self.assertIn("N/A", report)

        # Test empty event_id directly
        is_new_empty, _, _ = process_and_export(event_id="", data={}, guard=self.guard)
        self.assertTrue(is_new_empty)

        # Test guard directly with empty
        self.assertTrue(self.guard.check_and_add(""))

        # Test clean_data with none
        self.assertEqual(clean_data(None), 0)

        # Test default LRU capacity handling
        bad_guard = LRUIdempotencyGuard(capacity=-5)
        self.assertEqual(bad_guard.capacity, 1000)

    def test_idempotency_checks(self):
        # Process first time
        is_new1, _, _ = process_and_export("evt_dup", {}, guard=self.guard)
        self.assertTrue(is_new1)

        # Process second time (should be duplicate)
        is_new2, _, report2 = process_and_export("evt_dup", {}, guard=self.guard)
        self.assertFalse(is_new2)
        self.assertIn("Duplicate Event", report2)

        # Push enough elements to evict evt_dup
        for i in range(20):
            process_and_export(f"evt_{i}", {}, guard=self.guard)

        # evt_dup should now be new again because it was evicted
        is_new3, _, _ = process_and_export("evt_dup", {}, guard=self.guard)
        self.assertTrue(is_new3)

    def test_boundary_conditions(self):
        # Very deep nested data
        deep_data = {"level1": {"level2": {"level3": {"comments": 5, "val": float('nan')}}}}
        _, cleaned, _ = process_and_export("evt_deep", deep_data, guard=self.guard)
        self.assertEqual(cleaned["level1"]["level2"]["level3"]["comments"], 0)
        self.assertEqual(cleaned["level1"]["level2"]["level3"]["val"], 0)

        # Primitive non-dict data fallback
        _, cleaned_prim, report = process_and_export("evt_prim", "just a string", guard=self.guard)
        self.assertEqual(cleaned_prim, {"data": "just a string"})

        # Using global guard implicitly
        is_new_global, _, _ = process_and_export("evt_global_123", {"a": 1})
        self.assertTrue(is_new_global)

        is_new_global2, _, _ = process_and_export("evt_global_123", {"a": 1})
        self.assertFalse(is_new_global2)

if __name__ == '__main__':
    unittest.main() # pragma: no cover
