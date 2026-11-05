import unittest
import time
from unittest.mock import patch
from ultra_modules.adaptive_stream_throttler_self_healing_guard import AdaptiveStreamThrottlerSelfHealingGuard

class TestAdaptiveStreamThrottlerSelfHealingGuard(unittest.TestCase):
    def setUp(self):
        self.guard = AdaptiveStreamThrottlerSelfHealingGuard(undo_window=5.0)

    def test_normal_push_and_throttle(self):
        """Test normal pushing and verify dynamic throttling timings"""
        start_time = time.time()

        # Initial push (no throttle)
        res1 = self.guard.push(seq=1, data={"msg": "A" * 100})
        self.assertEqual(res1["seq"], 1)
        self.assertAlmostEqual(res1["sleep_time"], 0.0)

        # Second push, should be throttled based on length
        res2 = self.guard.push(seq=2, data={"msg": "B" * 500})
        self.assertEqual(res2["seq"], 2)

        # Max length is reached (500 chars), so sleep time should be close to 500ms
        self.assertGreater(res2["sleep_time"], 0)
        self.assertLessEqual(res2["sleep_time"], 0.5)

    def test_dirty_data_self_healing_and_missing_params(self):
        """Test missing params, None data, string data, integer data fallback"""
        # None data
        res1 = self.guard.push(seq=1, data=None)
        self.assertEqual(res1["data"], {})

        # Missing params (should auto-increment seq)
        res2 = self.guard.push()
        self.assertEqual(res2["seq"], 2)
        self.assertEqual(res2["data"], {})

        # String data
        res3 = self.guard.push(seq=3, data="hello")
        self.assertEqual(res3["data"], {"content": "hello"})

        # Integer data (non-dict, non-string fallback)
        res4 = self.guard.push(seq=4, data=42)
        self.assertEqual(res4["data"], {"value": 42})

    def test_monotonic_sequence_correction(self):
        """Test strictly increasing sequences, even with bad inputs"""
        res1 = self.guard.push(seq=10, data="first")
        self.assertEqual(res1["seq"], 10)

        # Backward sequence (should increment from 10 to 11)
        res2 = self.guard.push(seq=5, data="second")
        self.assertEqual(res2["seq"], 11)

        # Invalid sequence type (should increment from 11 to 12)
        res3 = self.guard.push(seq="invalid", data="third")
        self.assertEqual(res3["seq"], 12)

    def test_snapshot_undo(self):
        """Test 5-second snapshot undo mechanism"""
        self.guard.push(seq=1, data="first")
        self.guard.push(seq=2, data="second")

        # Now current data is {"content": "second"}, snapshot has "first"
        self.assertEqual(self.guard.get_current_state()["data"], {"content": "second"})

        undo_res = self.guard.undo()
        self.assertEqual(undo_res["status"], "success")
        self.assertEqual(undo_res["seq"], 3) # sequence strictly monotonic
        self.assertEqual(undo_res["data"], {"content": "first"})
        self.assertEqual(self.guard.get_current_state()["data"], {"content": "first"})

    @patch('time.time')
    def test_undo_timeout_and_bounds(self, mock_time):
        """Test undo failure after 5 seconds window, and empty snapshot bounds"""
        # Start at t=0
        mock_time.return_value = 0.0
        guard = AdaptiveStreamThrottlerSelfHealingGuard(undo_window=5.0)

        # Undo on empty (should fail gracefully and just increment seq)
        res_empty = guard.undo()
        self.assertEqual(res_empty["status"], "failed")
        self.assertEqual(res_empty["reason"], "snapshot_expired_or_empty")
        self.assertEqual(res_empty["seq"], 1)

        # Push data at t=0
        guard.push(seq=2, data="first")

        # Advance time by 6 seconds (exceeding 5.0 undo_window)
        mock_time.return_value = 6.0

        # Undo should fail due to expired snapshot
        res_expired = guard.undo()
        self.assertEqual(res_expired["status"], "failed")
        self.assertEqual(res_expired["reason"], "snapshot_expired_or_empty")
        self.assertEqual(res_expired["seq"], 3) # Sequence still increases to 3

if __name__ == '__main__':
    unittest.main()
