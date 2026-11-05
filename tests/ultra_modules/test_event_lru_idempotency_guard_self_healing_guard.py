import unittest
import time
from unittest.mock import patch
from ultra_modules.event_lru_idempotency_guard_self_healing_guard import EventIdempotencyGuard

class TestEventIdempotencyGuard(unittest.TestCase):
    def test_normal_operation(self):
        """Test normal insertion and replay rejection."""
        guard = EventIdempotencyGuard(capacity=10)

        # First time should pass
        self.assertTrue(guard.check_and_record(event_id="evt_123", event_data={"text": "hello"}))
        # Replay should be rejected
        self.assertFalse(guard.check_and_record(event_id="evt_123", event_data={"text": "hello"}))

        # Another distinct event should pass
        self.assertTrue(guard.check_and_record(event_id="evt_456"))

    def test_dirty_data_self_healing(self):
        """Test self-healing mechanisms for dirty inputs like whitespace, non-strings, or None."""
        guard = EventIdempotencyGuard()

        # With whitespace
        self.assertTrue(guard.check_and_record(event_id=" evt_789 ", event_data={"text": "clean"}))
        # Replay should hit despite whitespace mismatch in input
        self.assertFalse(guard.check_and_record(event_id="evt_789", event_data={"text": "clean"}))

        # With non-string (int) ID
        self.assertTrue(guard.check_and_record(event_id=101112))
        self.assertFalse(guard.check_and_record(event_id="101112"))

        # With weird event_data types (int, list, etc.) - should fallback to a string wrapper if not dict
        self.assertTrue(guard.check_and_record(event_id="weird_data", event_data=123))
        self.assertIsNotNone(guard.get_snapshot(event_id="weird_data")["snapshot"])

    def test_missing_parameter_fallback(self):
        """Test fallback when event_id and message_id are missing."""
        guard = EventIdempotencyGuard()

        # Missing event_id, has message_id
        self.assertTrue(guard.check_and_record(message_id="msg_111", event_data={"k": "v"}))
        self.assertFalse(guard.check_and_record(message_id="msg_111"))

        # Missing both, fallback to hashing event_data
        event_data1 = {"action": "push", "val": 1}
        self.assertTrue(guard.check_and_record(event_data=event_data1))
        # Second time with same data should be rejected
        self.assertFalse(guard.check_and_record(event_data=event_data1))

        # Test completely missing all parameters (timestamp fallback)
        with patch('time.time', return_value=12345.0):
            self.assertTrue(guard.check_and_record())
            # Replay with same patched time
            self.assertFalse(guard.check_and_record())

    def test_snapshot_undo(self):
        """Test snapshot retrieval and undo logic within the 5-second window."""
        guard = EventIdempotencyGuard(undo_window_seconds=5)

        # Record an event
        guard.check_and_record(event_id="undo_evt", event_data={"important": "data"})

        # Snapshot exists
        snapshot = guard.get_snapshot(event_id="undo_evt")
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot['snapshot'], {"important": "data"})

        # Undo within window (mock time to be within 5 seconds)
        with patch('time.time', return_value=snapshot['timestamp'] + 2):
            self.assertTrue(guard.undo(event_id="undo_evt"))

        # Snapshot should be gone
        self.assertIsNone(guard.get_snapshot(event_id="undo_evt"))

        # Can record again since it was undone
        self.assertTrue(guard.check_and_record(event_id="undo_evt", event_data={"important": "data"}))
        snapshot2 = guard.get_snapshot(event_id="undo_evt")

        # Try undoing after window expired
        with patch('time.time', return_value=snapshot2['timestamp'] + 6):
            self.assertFalse(guard.undo(event_id="undo_evt"))

        # Snapshot should still be there
        self.assertIsNotNone(guard.get_snapshot(event_id="undo_evt"))

    def test_lru_eviction(self):
        """Test LRU eviction when capacity is reached."""
        guard = EventIdempotencyGuard(capacity=3)

        # Add 3 events (cache full)
        guard.check_and_record(event_id="e1")
        guard.check_and_record(event_id="e2")
        guard.check_and_record(event_id="e3")

        # Add 4th event, evicting the least recently used ('e1')
        guard.check_and_record(event_id="e4")

        # e1 should be gone (treated as new event)
        self.assertTrue(guard.check_and_record(event_id="e1"))

        # e2 was now evicted by e1
        self.assertTrue(guard.check_and_record(event_id="e2"))

if __name__ == '__main__':
    unittest.main()
