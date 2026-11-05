import unittest
import json
import collections

# Import the module to be tested
from ultra_modules.event_lru_idempotency_guard_cli_one_click import EventLRUIdempotencyGuard, run_cli


class TestEventLRUIdempotencyGuardCliOneClick(unittest.TestCase):

    def test_01_normal_operations(self):
        """Test case 1: Normal conditions - valid events are added and duplicates are rejected."""
        guard = EventLRUIdempotencyGuard()
        # Add new event
        self.assertTrue(guard.check_and_add({"event_id": "evt_123"}))
        # Add duplicate
        self.assertFalse(guard.check_and_add({"event_id": "evt_123"}))
        # Add different event
        self.assertTrue(guard.check_and_add({"event_id": "evt_456"}))

        # Nested event structure
        self.assertTrue(guard.check_and_add({"event": {"message_id": "msg_789"}}))
        self.assertFalse(guard.check_and_add({"event": {"event_id": "msg_789"}}))

    def test_02_dirty_data_self_healing(self):
        """Test case 2: Dirty data self-healing - guard handles invalid inputs gracefully."""
        guard = EventLRUIdempotencyGuard()
        # Not a dict
        self.assertFalse(guard.check_and_add("just a string"))
        self.assertFalse(guard.check_and_add(123))
        self.assertFalse(guard.check_and_add(None))
        self.assertFalse(guard.check_and_add(["list"]))

        # Dicts without valid ids
        self.assertFalse(guard.check_and_add({}))
        self.assertFalse(guard.check_and_add({"other_key": "val"}))
        self.assertFalse(guard.check_and_add({"event_id": ""}))
        self.assertFalse(guard.check_and_add({"event_id": "   "}))
        self.assertFalse(guard.check_and_add({"event_id": 123}))
        self.assertFalse(guard.check_and_add({"event": {}}))
        self.assertFalse(guard.check_and_add({"event": "not_a_dict"}))

    def test_03_missing_parameters_fallback(self):
        """Test case 3: Missing parameter fallback for constructor and CLI."""
        # Constructor falls back to 1000
        guard1 = EventLRUIdempotencyGuard(capacity=0)
        self.assertEqual(guard1.capacity, 1000)

        guard2 = EventLRUIdempotencyGuard(capacity=-50)
        self.assertEqual(guard2.capacity, 1000)

        guard3 = EventLRUIdempotencyGuard(capacity="not_an_int")
        self.assertEqual(guard3.capacity, 1000)

        # CLI falls back to defaults when called with no/invalid args
        res_json = run_cli()
        self.assertIn("evt_001", res_json)
        self.assertTrue(res_json.startswith("["))

        res_excel = run_cli(output_format="excel")
        self.assertIn("event_raw,is_new,status", res_excel)

        res_invalid_fmt = run_cli(events=[{"event_id": "abc"}], output_format=123)
        self.assertTrue(res_invalid_fmt.startswith("["))

    def test_04_extreme_boundary_conditions(self):
        """Test case 4: Extreme boundary conditions like LRU eviction."""
        guard = EventLRUIdempotencyGuard(capacity=2)

        # Add two items (cache full)
        self.assertTrue(guard.check_and_add({"event_id": "A"}))
        self.assertTrue(guard.check_and_add({"event_id": "B"}))
        self.assertEqual(len(guard.cache), 2)

        # Access 'A' to make 'B' the least recently used
        self.assertFalse(guard.check_and_add({"event_id": "A"}))

        # Add 'C', should evict 'B'
        self.assertTrue(guard.check_and_add({"event_id": "C"}))
        self.assertEqual(len(guard.cache), 2)

        # 'B' should be evicted and thus treated as new if added again
        self.assertTrue(guard.check_and_add({"event_id": "B"}))

        # Now 'A' should be evicted
        self.assertTrue(guard.check_and_add({"event_id": "A"}))

    def test_05_cli_json_and_excel_exports(self):
        """Test case 5: Thorough test of CLI exporting capabilities (JSON & Excel)."""
        events = [
            {"event_id": "A"},
            {"event_id": "A"}, # dup
            {"message_id": "B"},
            "invalid_event"
        ]

        res_json = run_cli(events=events, output_format="json")
        data = json.loads(res_json)
        self.assertEqual(len(data), 4)

        self.assertTrue(data[0]["is_new"])
        self.assertEqual(data[0]["status"], "PROCESSED")

        self.assertFalse(data[1]["is_new"])
        self.assertEqual(data[1]["status"], "DUPLICATE_OR_INVALID")

        self.assertTrue(data[2]["is_new"])

        self.assertFalse(data[3]["is_new"])

        # Excel mode
        res_excel = run_cli(events=events, output_format="Excel")
        lines = res_excel.strip().split("\r\n")

        self.assertEqual(len(lines), 5) # 1 header + 4 rows
        self.assertTrue(lines[0].startswith("event_raw,is_new,status"))
        self.assertTrue("True,PROCESSED" in lines[1])
        self.assertTrue("False,DUPLICATE_OR_INVALID" in lines[2])

if __name__ == '__main__':
    unittest.main()
