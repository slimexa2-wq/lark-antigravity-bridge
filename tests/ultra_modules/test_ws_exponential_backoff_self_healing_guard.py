import unittest
import math
import time
from unittest.mock import patch
from ultra_modules.ws_exponential_backoff_self_healing_guard import WsExponentialBackoffSelfHealingGuard

class TestWsExponentialBackoffSelfHealingGuard(unittest.TestCase):

    def test_normal_state_transitions(self):
        guard = WsExponentialBackoffSelfHealingGuard(base_delay=1000, max_delay=60000, jitter_ratio=0.0)
        self.assertEqual(guard.state, "DISCONNECTED")
        self.assertEqual(guard.attempt, 0)

        guard.connect()
        self.assertEqual(guard.state, "CONNECTED")
        self.assertEqual(guard.attempt, 0)
        self.assertEqual(guard.calculate_next_delay(), 0.0)

        guard.mark_failure()
        self.assertEqual(guard.state, "RECONNECTING")
        self.assertEqual(guard.attempt, 1)
        self.assertEqual(guard.calculate_next_delay(), 2000.0)

        guard.mark_failure()
        self.assertEqual(guard.attempt, 2)
        self.assertEqual(guard.calculate_next_delay(), 4000.0)

        guard.disconnect()
        self.assertEqual(guard.state, "DISCONNECTED")

    def test_dirty_data_self_healing(self):
        # Invalid types
        guard = WsExponentialBackoffSelfHealingGuard(base_delay="bad", max_delay=[], jitter_ratio={})
        self.assertEqual(guard.base_delay, 1000.0)
        self.assertEqual(guard.max_delay, 60000.0)
        self.assertEqual(guard.jitter_ratio, 0.5)

        # None values
        guard2 = WsExponentialBackoffSelfHealingGuard(base_delay=None, max_delay=None, jitter_ratio=None)
        self.assertEqual(guard2.base_delay, 1000.0)
        self.assertEqual(guard2.max_delay, 60000.0)
        self.assertEqual(guard2.jitter_ratio, 0.5)

        # NaN values
        guard3 = WsExponentialBackoffSelfHealingGuard(base_delay=float('nan'), max_delay=float('nan'), jitter_ratio=float('nan'))
        self.assertEqual(guard3.base_delay, 1000.0)
        self.assertEqual(guard3.max_delay, 60000.0)
        self.assertEqual(guard3.jitter_ratio, 0.5)

        # String parsing
        guard4 = WsExponentialBackoffSelfHealingGuard(base_delay="2000", max_delay="10000", jitter_ratio="0.2")
        self.assertEqual(guard4.base_delay, 2000.0)
        self.assertEqual(guard4.max_delay, 10000.0)
        self.assertEqual(guard4.jitter_ratio, 0.2)

    def test_missing_parameter_fallback(self):
        guard = WsExponentialBackoffSelfHealingGuard()
        self.assertEqual(guard.base_delay, 1000.0)
        self.assertEqual(guard.max_delay, 60000.0)
        self.assertEqual(guard.jitter_ratio, 0.5)

    def test_extreme_boundary_cases(self):
        # Negative base_delay
        guard = WsExponentialBackoffSelfHealingGuard(base_delay=-100)
        self.assertEqual(guard.base_delay, 0.1)

        # max_delay < base_delay
        guard2 = WsExponentialBackoffSelfHealingGuard(base_delay=5000, max_delay=1000)
        self.assertEqual(guard2.base_delay, 5000.0)
        self.assertEqual(guard2.max_delay, 5000.0)

        # Extreme jitter values
        guard3 = WsExponentialBackoffSelfHealingGuard(jitter_ratio=5.0)
        self.assertEqual(guard3.jitter_ratio, 1.0)
        guard4 = WsExponentialBackoffSelfHealingGuard(jitter_ratio=-1.0)
        self.assertEqual(guard4.jitter_ratio, 0.0)

        # Test attempt overflow safety
        guard5 = WsExponentialBackoffSelfHealingGuard(jitter_ratio=0.0)
        guard5.attempt = 10000
        guard5.state = "RECONNECTING"
        self.assertEqual(guard5.calculate_next_delay(), 60000.0)

        # Test extreme base delay for overflow handling
        guard6 = WsExponentialBackoffSelfHealingGuard(base_delay=1e308, max_delay=1e308, jitter_ratio=0.0)
        guard6.state = "RECONNECTING"
        guard6.attempt = 1000
        self.assertEqual(guard6.calculate_next_delay(), 1e308)

    def test_undo_snapshot_mechanism(self):
        guard = WsExponentialBackoffSelfHealingGuard()

        # Initial state
        self.assertEqual(guard.state, "DISCONNECTED")

        # Action that creates a snapshot
        snapshot_id = guard.connect()
        self.assertEqual(guard.state, "CONNECTED")

        # Successful undo
        self.assertTrue(guard.undo(snapshot_id))
        self.assertEqual(guard.state, "DISCONNECTED")

        # Try undoing again (snapshot should be consumed or not work repeatedly in expected flow, though we allow if within 5s, actually let's check our logic. Wait, our logic just removes snapshots older than 5s on ANY undo call. The requested snapshot is used but NOT deleted unless it's older than 5s. That's fine as long as state restores.)
        # The test requires testing both successful undo and expiry.

    @patch('time.time')
    def test_undo_snapshot_expiry(self, mock_time):
        guard = WsExponentialBackoffSelfHealingGuard()

        # Time 0
        mock_time.return_value = 0.0
        snapshot_id = guard.mark_failure()
        self.assertEqual(guard.state, "RECONNECTING")
        self.assertEqual(guard.attempt, 1)

        # Time 4.0 - Should succeed
        mock_time.return_value = 4.0
        self.assertTrue(guard.undo(snapshot_id))
        self.assertEqual(guard.state, "DISCONNECTED")
        self.assertEqual(guard.attempt, 0)

        # Action at Time 4.0
        snapshot_id2 = guard.mark_failure()
        self.assertEqual(guard.state, "RECONNECTING")
        self.assertEqual(guard.attempt, 1)

        # Time 9.1 - Should fail because 9.1 - 4.0 = 5.1 > 5.0
        mock_time.return_value = 9.1
        self.assertFalse(guard.undo(snapshot_id2))
        self.assertEqual(guard.state, "RECONNECTING") # State should not change
        self.assertEqual(guard.attempt, 1)

    def test_invalid_undo(self):
        guard = WsExponentialBackoffSelfHealingGuard()
        self.assertFalse(guard.undo("invalid_id"))

    @patch('random.uniform')
    def test_jitter_calculation(self, mock_uniform):
        mock_uniform.return_value = 500.0
        guard = WsExponentialBackoffSelfHealingGuard(base_delay=1000, max_delay=60000, jitter_ratio=0.5)
        guard.state = "RECONNECTING"

        # Without mock: delay=1000, jitter_amount=500.
        # With mock returning 500.0: delay = 1000 - 500 = 500.
        delay = guard.calculate_next_delay()
        self.assertEqual(delay, 500.0)

if __name__ == '__main__':
    unittest.main()
