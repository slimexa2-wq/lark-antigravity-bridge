import unittest
import time
from ultra_modules.rate_limit_429_queue_core_engine import (
    init_state,
    clean_request_data,
    refill_tokens,
    process_request,
    enqueue_request,
    dequeue_requests,
    process_queue
)

class TestRateLimit429QueueCoreEngine(unittest.TestCase):

    def test_init_state_and_defaults(self):
        # Normal initialization
        state = init_state(capacity=50, refill_rate=5.0)
        self.assertEqual(state["capacity"], 50)
        self.assertEqual(state["tokens"], 50.0)
        self.assertEqual(state["refill_rate"], 5.0)
        self.assertEqual(state["queue"], [])

        # Default values and dirty data
        state = init_state(capacity=-10, refill_rate="invalid")
        self.assertEqual(state["capacity"], 100) # Fallback to 100
        self.assertEqual(state["tokens"], 100.0)
        self.assertEqual(state["refill_rate"], 10.0) # Fallback to 10.0

    def test_clean_request_data(self):
        self.assertEqual(clean_request_data({"key": "value"}), {"key": "value"})
        self.assertEqual(clean_request_data(None), {})
        self.assertEqual(clean_request_data("some string"), {"data": "some string"})
        self.assertEqual(clean_request_data(123), {"data": "123"})

    def test_process_request_and_queueing(self):
        # Start with capacity 2
        state = init_state(capacity=2, refill_rate=1.0)
        start_time = 100.0
        state["last_refill_time"] = start_time

        # Process 1st request (should succeed)
        state, success = process_request(state, {"id": 1}, current_time=start_time)
        self.assertTrue(success)
        self.assertEqual(state["tokens"], 1.0)
        self.assertEqual(len(state["queue"]), 0)

        # Process 2nd request (should succeed)
        state, success = process_request(state, {"id": 2}, current_time=start_time)
        self.assertTrue(success)
        self.assertEqual(state["tokens"], 0.0)
        self.assertEqual(len(state["queue"]), 0)

        # Process 3rd request (should fail and be queued)
        state, success = process_request(state, {"id": 3}, current_time=start_time)
        self.assertFalse(success)
        self.assertEqual(state["tokens"], 0.0)
        self.assertEqual(len(state["queue"]), 1)
        self.assertEqual(state["queue"][0], {"id": 3})

    def test_time_going_backwards(self):
        state = init_state(capacity=5, refill_rate=2.0)
        state["tokens"] = 3.0
        state["last_refill_time"] = 100.0

        # Simulate time going backwards
        state = refill_tokens(state, current_time=90.0)
        self.assertEqual(state["tokens"], 3.0) # Tokens shouldn't change
        self.assertEqual(state["last_refill_time"], 90.0)

    def test_process_queue(self):
        state = init_state(capacity=10, refill_rate=1.0)
        state["tokens"] = 0.0
        state["last_refill_time"] = 100.0
        state["queue"] = [{"id": 1}, {"id": 2}, {"id": 3}]

        # Wait 2 seconds (enough for 2 tokens)
        state, processed = process_queue(state, current_time=102.0)

        self.assertEqual(len(processed), 2)
        self.assertEqual(processed, [{"id": 1}, {"id": 2}])
        self.assertEqual(state["tokens"], 0.0) # Used the 2 newly generated tokens
        self.assertEqual(len(state["queue"]), 1)
        self.assertEqual(state["queue"], [{"id": 3}])

    def test_dequeue_requests_dirty(self):
        state = init_state()
        state["queue"] = [{"id": 1}, {"id": 2}, {"id": 3}]

        # Test dequeueing with valid parameter
        state, dequeued = dequeue_requests(state, max_items=2)
        self.assertEqual(len(dequeued), 2)
        self.assertEqual(len(state["queue"]), 1)

        # Test dequeueing with dirty parameter
        state, dequeued = dequeue_requests(state, max_items="invalid")
        self.assertEqual(len(dequeued), 1)
        self.assertEqual(len(state["queue"]), 0)

if __name__ == "__main__":
    unittest.main()
