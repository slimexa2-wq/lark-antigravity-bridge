import unittest
import time
from ultra_modules.adaptive_stream_throttler_audit_trace import AdaptiveStreamThrottler, DiffHighlighter

class TestAdaptiveStreamThrottlerAuditTrace(unittest.TestCase):
    def setUp(self):
        # Use smaller windows for faster testing
        self.throttler = AdaptiveStreamThrottler(min_window_ms=50, max_window_ms=100, burst_threshold=3)

    def test_normal_execution_and_adaptive_window(self):
        # 1. Normal execution
        res1 = self.throttler.push("chunk1")
        self.assertIsNone(res1)  # Window not reached yet

        # Fast pushes to trigger adaptive window increase
        self.throttler.push("chunk2")
        self.throttler.push("chunk3")
        self.throttler.push("chunk4")

        # Verify burst threshold reached and window increased
        trail = self.throttler.get_audit_trail()
        increase_logs = [log for log in trail if log["action"] == "ADAPTIVE_WINDOW_INCREASE"]
        self.assertTrue(len(increase_logs) > 0)

        # Wait for max window to pass
        time.sleep(0.15)
        res = self.throttler.push("chunk5")

        self.assertIsNotNone(res)
        self.assertEqual(res["result"], "chunk1chunk2chunk3chunk4chunk5")
        self.assertEqual(res["events_flushed"], 5)

    def test_dirty_data_self_healing(self):
        # 2. Dirty data self-healing
        self.throttler.push(12345) # Should heal to "12345"
        self.throttler.push({"key": "val"}) # Should heal to string representation

        # Force a flush
        res = self.throttler.flush()
        self.assertIsNotNone(res)

        # Verify self healing in audit log
        trail = self.throttler.get_audit_trail()
        heal_logs = [log for log in trail if log["action"] == "DIRTY_DATA_HEALED"]
        self.assertEqual(len(heal_logs), 2)

        self.assertTrue("12345" in res["result"])

    def test_missing_parameter_fallback(self):
        # 3. Missing parameter default fallback
        self.throttler.push() # Calling without data

        res = self.throttler.flush()
        self.assertIsNotNone(res)
        self.assertEqual(res["result"], "")

        trail = self.throttler.get_audit_trail()
        fallback_logs = [log for log in trail if log["action"] == "DEFAULT_FALLBACK"]
        self.assertEqual(len(fallback_logs), 1)

    def test_extreme_boundary_and_deduplication(self):
        # 4. Extreme boundary and deduplication
        self.throttler.push("same_data")
        self.throttler.push("same_data") # Should be deduplicated
        self.throttler.push("same_data") # Should be deduplicated

        trail = self.throttler.get_audit_trail()
        dedup_logs = [log for log in trail if log["action"] == "DEDUPLICATE"]
        self.assertEqual(len(dedup_logs), 2)

        res = self.throttler.flush()
        self.assertEqual(res["result"], "same_data")
        self.assertEqual(res["events_flushed"], 1)

    def test_monotonic_sequence_audit(self):
        # 5. Monotonic sequence audit
        self.throttler.push("test1")
        self.throttler.push("test2")
        self.throttler.flush()

        trail = self.throttler.get_audit_trail()

        # Verify sequences are monotonically increasing
        sequences = [log["sequence"] for log in trail]
        self.assertEqual(sequences, sorted(list(set(sequences)))) # Strictly increasing
        self.assertTrue(len(sequences) > 0)

    def test_diff_highlighter(self):
        self.assertEqual(DiffHighlighter.compare("a", "a"), "NO_CHANGE")
        self.assertEqual(DiffHighlighter.compare("a", "b"), "CHANGE: a -> b")

if __name__ == '__main__':
    unittest.main()
