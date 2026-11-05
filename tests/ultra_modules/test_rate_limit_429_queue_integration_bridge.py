import unittest
import time
from ultra_modules.rate_limit_429_queue_integration_bridge import RateLimit429IntegrationBridge

class TestRateLimit429IntegrationBridge(unittest.TestCase):

    def setUp(self):
        self.bridge = RateLimit429IntegrationBridge()

    def test_normal_conditions(self):
        """Test normal enqueue and dequeue operations with schema v2."""
        item_id = self.bridge.enqueue(payload={"open_id": "user_123", "content": "Hello"})
        self.assertIsNotNone(item_id)
        self.assertEqual(len(self.bridge.queue), 1)

        items = self.bridge.dequeue(batch_size=1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["payload"]["id"], item_id)
        self.assertEqual(items[0]["payload"]["open_id"], "user_123")
        self.assertEqual(items[0]["payload"]["content"], "Hello")
        self.assertIn("create_time", items[0]["payload"])

    def test_schema_forward_compatibility(self):
        """Test automatic mapping from v1 schema to v2 schema."""
        item_id = self.bridge.enqueue(
            payload={"user_id": "u456", "msg": "Test MSG", "timestamp": 1234567890}
        )
        items = self.bridge.dequeue()
        self.assertEqual(len(items), 1)

        payload = items[0]["payload"]
        self.assertEqual(payload["open_id"], "u456")
        self.assertEqual(payload["content"], "Test MSG")
        self.assertEqual(payload["create_time"], 1234567890)
        self.assertNotIn("user_id", payload)
        self.assertNotIn("msg", payload)
        self.assertNotIn("timestamp", payload)

    def test_dirty_data_self_healing(self):
        """Test silent cleaning of dirty data (None keys/values, empty string keys)."""
        # Testing with missing parameter fallback (kwargs used instead of payload dict)
        self.bridge.enqueue(
            None,
            open_id="u789",
            content="Valid",
            NoneKey="Should be removed if None key was possible but it's not in kwargs",
            empty_value=None,
            **{"": "invalid_key_empty_string", "   ": "invalid_key_spaces"}
        )
        # Testing enqueue when payload is not dict
        self.bridge.enqueue("not a dict string payload")

        items = self.bridge.dequeue(batch_size=2)
        self.assertEqual(len(items), 2)

        payload1 = items[0]["payload"]
        self.assertEqual(payload1["open_id"], "u789")
        self.assertEqual(payload1["content"], "Valid")
        self.assertNotIn("empty_value", payload1)
        self.assertNotIn("", payload1)
        self.assertNotIn("   ", payload1)

        payload2 = items[1]["payload"]
        self.assertEqual(payload2["raw_data"], "not a dict string payload")

    def test_missing_parameter_default_fallback(self):
        """Test defaults for missing parameters (missing payload, invalid batch size)."""
        # No arguments provided
        item_id = self.bridge.enqueue()
        self.assertIsNotNone(item_id)

        # Dequeue with invalid batch sizes
        batch_none = self.bridge.dequeue(batch_size=None)
        self.assertEqual(len(batch_none), 1)

        self.bridge.enqueue()
        batch_zero = self.bridge.dequeue(batch_size=0)
        self.assertEqual(len(batch_zero), 1)

        self.bridge.enqueue()
        batch_str = self.bridge.dequeue(batch_size="invalid")
        self.assertEqual(len(batch_str), 1)

    def test_extreme_boundary_conditions(self):
        """Test queue overflow boundary conditions (max_queue_size)."""
        small_bridge = RateLimit429IntegrationBridge(max_queue_size=2)

        # Test branch where ID and create_time are already in mapped payload
        small_bridge.enqueue(payload={"data": "1", "id": "predefined_id", "create_time": 99999})
        items = small_bridge.dequeue(batch_size=1)
        self.assertEqual(items[0]["payload"]["id"], "predefined_id")
        self.assertEqual(items[0]["payload"]["create_time"], 99999)

        small_bridge.enqueue(payload={"data": "1"})
        small_bridge.enqueue(payload={"data": "2"})

        # This should overwrite the oldest (data: "1")
        small_bridge.enqueue(payload={"data": "3"})

        self.assertEqual(len(small_bridge.queue), 2)
        items = small_bridge.dequeue(batch_size=3)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["payload"]["data"], "2")
        self.assertEqual(items[1]["payload"]["data"], "3")

    def test_429_re_enqueue(self):
        """Test zero-loss re-enqueue behavior for 429 retries."""
        # Initial enqueue
        self.bridge.enqueue(payload={"data": "test"})
        items = self.bridge.dequeue()
        item = items[0]

        self.assertEqual(item["retry_count"], 0)

        # Simulate a 429 and re-enqueue
        self.bridge.re_enqueue(item)

        # Verify it's back in the queue with incremented retry count
        self.assertEqual(len(self.bridge.queue), 1)
        re_items = self.bridge.dequeue()
        self.assertEqual(re_items[0]["retry_count"], 1)
        self.assertEqual(re_items[0]["payload"]["data"], "test")

        # Test invalid re_enqueue inputs (dirty data fallback)
        self.bridge.re_enqueue(None)
        self.bridge.re_enqueue("not a dict")
        self.bridge.re_enqueue({"no_payload": True})
        self.assertEqual(len(self.bridge.queue), 0)

    def test_report_429(self):
        """Test report_429 method with actual item recovery."""
        # Setup specific id tracking
        self.bridge.enqueue(payload={"id": "some_id", "data": "track_me"})
        items = self.bridge.dequeue() # Starts tracking

        self.assertTrue(self.bridge.report_429("some_id"))

        # Verify it went back to queue
        self.assertEqual(len(self.bridge.queue), 1)
        re_queued = self.bridge.queue[0]
        self.assertEqual(re_queued["payload"]["data"], "track_me")
        self.assertEqual(re_queued["retry_count"], 1)

        # Try reporting invalid or non-tracked IDs
        self.assertFalse(self.bridge.report_429(None))
        self.assertFalse(self.bridge.report_429(""))
        self.assertFalse(self.bridge.report_429("unknown_id"))

    def test_complete_processing(self):
        """Test acknowledging processing completion."""
        self.bridge.enqueue(payload={"id": "done_id", "data": "finish_me"})
        self.bridge.dequeue()

        # Tracking includes it
        self.assertIn("done_id", self.bridge.processing)

        # Complete removes it
        self.assertTrue(self.bridge.complete("done_id"))
        self.assertNotIn("done_id", self.bridge.processing)

        # Invalid complete returns False
        self.assertFalse(self.bridge.complete("unknown_id"))

    def test_token_bucket_queueing(self):
        """Test token bucket rate limit behavior."""
        bridge = RateLimit429IntegrationBridge(capacity=2.0, refill_rate=1.0)

        bridge.enqueue(payload={"id": "1"})
        bridge.enqueue(payload={"id": "2"})
        bridge.enqueue(payload={"id": "3"})

        # Dequeue with time setup. Current tokens=2.0
        # Should only get 2 items even if we ask for 3
        start_time = time.time()
        # Reset internal tokens specifically for exact math in test
        bridge.last_refill_time = start_time
        bridge.tokens = 2.0

        items = bridge.dequeue(batch_size=3, current_time=start_time)
        self.assertEqual(len(items), 2)
        self.assertEqual(bridge.tokens, 0.0)
        self.assertEqual(len(bridge.queue), 1)

        # Fast forward 1 second, generates 1 token
        items2 = bridge.dequeue(batch_size=3, current_time=start_time + 1.0)
        self.assertEqual(len(items2), 1)
        self.assertEqual(bridge.tokens, 0.0)
        self.assertEqual(len(bridge.queue), 0)

    def test_extreme_boundary_re_enqueue(self):
        """Test re_enqueue hitting max queue size limit."""
        small_bridge = RateLimit429IntegrationBridge(max_queue_size=1)

        # Add a dummy item
        small_bridge.enqueue(payload={"data": "1"})

        # Re-enqueue an item while queue is full
        item_to_re_enqueue = {"payload": {"id": "2", "data": "2"}, "retry_count": 0}
        small_bridge.re_enqueue(item_to_re_enqueue)

        self.assertEqual(len(small_bridge.queue), 1)
        items = small_bridge.dequeue()
        self.assertEqual(items[0]["payload"]["data"], "2")
        self.assertEqual(items[0]["retry_count"], 1)

if __name__ == '__main__': # pragma: no cover
    unittest.main()
