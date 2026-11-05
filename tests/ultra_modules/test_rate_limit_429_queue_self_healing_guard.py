import unittest
import time
from typing import Dict, Any

from ultra_modules.rate_limit_429_queue_self_healing_guard import init_state, process_message, undo_last_message

class TestRateLimit429QueueSelfHealingGuard(unittest.TestCase):

    def test_normal_behavior_token_bucket(self):
        """Test normal token bucket and queue behavior."""
        state = init_state(capacity=5, refill_rate=10.0)
        self.assertEqual(state["capacity"], 5)
        self.assertEqual(state["tokens"], 5.0)

        # Process a message, should consume 1 token
        msg1 = {"id": 1}
        state, result = process_message(state, msg1, message_cost=1)
        self.assertEqual(result, msg1)
        self.assertTrue(state["tokens"] <= 4.0)
        self.assertEqual(len(state["queue"]), 0)

        # Process an expensive message that exceeds current tokens
        msg2 = {"id": 2}
        state, result = process_message(state, msg2, message_cost=10)
        self.assertIsNone(result) # Should be queued, not processed
        self.assertEqual(len(state["queue"]), 1)
        self.assertEqual(state["queue"][0]["message"], msg2)

    def test_dirty_data_self_healing(self):
        """Test that abnormal inputs are silently self-healed."""
        # Invalid init parameters
        state = init_state(capacity="invalid", refill_rate=-5.0)
        self.assertEqual(state["capacity"], 100)
        self.assertEqual(state["refill_rate"], 10.0)

        # Invalid message and cost
        invalid_msg = "just a string"
        state, result = process_message(state, invalid_msg, message_cost="too much")

        self.assertIsNotNone(result)
        self.assertEqual(result["content"], "just a string") # Healed to dict

        # Cost should be healed to 1, token should decrease by 1
        self.assertTrue(state["tokens"] <= 99.0)

    def test_missing_parameters_fallback(self):
        """Test fallback when parameters are completely missing."""
        state = init_state() # Missing both
        self.assertEqual(state["capacity"], 100)
        self.assertEqual(state["refill_rate"], 10.0)

        # Process None message
        state, result = process_message(state, None)
        self.assertIsNotNone(result)
        self.assertEqual(result["content"], "")

    def test_extreme_edge_cases(self):
        """Test extreme edge cases like zero or negative costs."""
        state = init_state(capacity=1)

        # Negative cost (heals to 1)
        state, result = process_message(state, {"id": 1}, message_cost=-100)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 1)

        # Zero tokens left now.
        # Send another with zero cost (heals to 1), should be queued
        state, result2 = process_message(state, {"id": 2}, message_cost=0)

        # It might actually get processed if refill happens, so let's check
        # the mechanics directly: if it's too fast, tokens won't refill enough
        if result2 is None:
            self.assertEqual(len(state["queue"]), 1)
            self.assertEqual(state["queue"][0]["cost"], 1) # Healed to 1
        else:
            self.assertEqual(result2["id"], 2)

    def test_undo_snapshot_mechanism(self):
        """Test the 5-second one-tap Undo snapshot mechanism."""
        state = init_state(capacity=5)
        initial_tokens = state["tokens"]

        # Process a message
        state, result = process_message(state, {"id": 1})
        self.assertTrue(state["tokens"] < initial_tokens)

        # Undo the message
        state, success = undo_last_message(state, undo_window=5.0)
        self.assertTrue(success)
        self.assertEqual(state["tokens"], initial_tokens)

        # Try to undo again (should fail since no snapshots left)
        state, success2 = undo_last_message(state)
        self.assertFalse(success2)

        # Test expiration
        state, _ = process_message(state, {"id": 2})

        # Simulate time passing (modify snapshot timestamp directly for test)
        old_time = time.time() - 6.0
        state["history_snapshots"][0] = (old_time, state["history_snapshots"][0][1])

        state, success3 = undo_last_message(state, undo_window=5.0)
        self.assertFalse(success3) # Expired

if __name__ == '__main__':
    unittest.main()
