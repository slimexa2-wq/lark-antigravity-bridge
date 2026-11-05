import unittest
import time
from ultra_modules.event_lru_idempotency_guard_integration_bridge import EventLRUIdempotencyGuardIntegrationBridge

class TestEventLRUIdempotencyGuardIntegrationBridge(unittest.TestCase):
    def setUp(self):
        self.guard = EventLRUIdempotencyGuardIntegrationBridge(capacity=3, ttl_seconds=1)

    def test_normal_v2_schema(self):
        """Test processing of normal v2 schema data."""
        event_data = {
            "header": {
                "event_id": "ev_v2_123",
                "event_type": "im.message.receive_v1",
                "create_time": "1234567890"
            },
            "event": {
                "message": {
                    "message_id": "msg_v2_123",
                    "content": '{"text":"hello"}'
                },
                "sender": {
                    "sender_id": {
                        "open_id": "ou_123"
                    }
                }
            }
        }

        result = self.guard.process_event(event_data)
        self.assertIsNotNone(result)
        self.assertEqual(result["event_id"], "ev_v2_123")
        self.assertEqual(result["message_id"], "msg_v2_123")
        self.assertEqual(result["type"], "im.message.receive_v1")
        self.assertEqual(result["sender_id"], "ou_123")

        # Test duplicate
        result2 = self.guard.process_event(event_data)
        self.assertIsNone(result2, "Duplicate event should return None")

    def test_legacy_v1_schema_mapping(self):
        """Test old and new version field mapping with v1 schema."""
        event_data = {
            "uuid": "ev_v1_456",
            "msg_id": "msg_v1_456",
            "type": "message",
            "ts": "1234567890",
            "text": "hello v1",
            "open_id": "ou_456"
        }

        result = self.guard.process_event(event_data)
        self.assertIsNotNone(result)
        self.assertEqual(result["event_id"], "ev_v1_456")
        self.assertEqual(result["message_id"], "msg_v1_456")
        self.assertEqual(result["type"], "message")
        self.assertEqual(result["content"], "hello v1")
        self.assertEqual(result["sender_id"], "ou_456")

    def test_dirty_data_self_healing(self):
        """Test dirty data self-healing and missing parameter defaults."""
        # 1. Invalid data type
        result1 = self.guard.process_event(["not", "a", "dict"])
        self.assertEqual(result1, {"_status": "error", "message": "invalid data"})

        # 2. Empty data
        result2 = self.guard.process_event({})
        self.assertEqual(result2, {"_status": "error", "message": "missing id"})

        # 3. Missing event_id but has message_id (fallback logic)
        partial_data = {
            "msg_id": "msg_partial_789",
            "type": "message"
        }
        result3 = self.guard.process_event(partial_data)
        self.assertIsNotNone(result3)
        self.assertEqual(result3["event_id"], "evt_msg_partial_789")
        self.assertEqual(result3["message_id"], "msg_partial_789")
        self.assertEqual(result3["sender_id"], "unknown") # Default

    def test_lru_capacity_and_eviction(self):
        """Test extreme boundaries: LRU capacity and eviction."""
        guard = EventLRUIdempotencyGuardIntegrationBridge(capacity=2)

        # Add 3 events
        ev1 = {"uuid": "evt_1"}
        ev2 = {"uuid": "evt_2"}
        ev3 = {"uuid": "evt_3"}

        self.assertIsNotNone(guard.process_event(ev1))
        self.assertIsNotNone(guard.process_event(ev2))

        # Evict evt_1
        self.assertIsNotNone(guard.process_event(ev3))

        # evt_1 should now be processed as new
        self.assertIsNotNone(guard.process_event(ev1))

        # evt_2 should be evicted now, evt_3 should still be duplicate
        self.assertIsNone(guard.process_event(ev3))
        self.assertIsNotNone(guard.process_event(ev2))

    def test_ttl_expiration(self):
        """Test extreme boundaries: TTL expiration."""
        guard = EventLRUIdempotencyGuardIntegrationBridge(capacity=5, ttl_seconds=0.1)

        ev = {"uuid": "evt_ttl"}
        self.assertIsNotNone(guard.process_event(ev))

        # Immediately duplicate
        self.assertIsNone(guard.process_event(ev))

        # Wait for TTL
        time.sleep(0.15)

        # Should be processed as new
        self.assertIsNotNone(guard.process_event(ev))

if __name__ == "__main__":
    unittest.main()
