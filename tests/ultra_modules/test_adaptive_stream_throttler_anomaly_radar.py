import unittest
import time
from unittest.mock import patch
from ultra_modules.adaptive_stream_throttler_anomaly_radar import AdaptiveStreamThrottler, AnomalyRadar

class TestAdaptiveStreamThrottlerAnomalyRadar(unittest.TestCase):

    @patch('time.time')
    def test_normal_operation_green(self, mock_time):
        """Test throttling with normal intervals and missing param fallback."""
        throttler = AdaptiveStreamThrottler()

        # Initial call should emit
        mock_time.return_value = 1000.0
        res1 = throttler.should_emit(None) # Missing stream_id fallback
        self.assertTrue(res1["emit"])
        self.assertEqual(res1["status"], "green")
        self.assertEqual(res1["window_ms"], 150.0)

        # Immediate call should be throttled
        mock_time.return_value = 1000.05 # 50ms later
        res2 = throttler.should_emit("stream1")
        self.assertFalse(res2["emit"])
        self.assertEqual(res2["reason"], "Throttled")

        # Call after window should emit
        mock_time.return_value = 1000.25 # 250ms later (total 250ms since last emit)
        res3 = throttler.should_emit("stream1")
        self.assertTrue(res3["emit"])
        self.assertEqual(res3["status"], "green")

        # Test missing sequence lock param falls back gracefully
        res4 = throttler.should_emit("stream1", seq=None)
        self.assertIn("emit", res4)

    @patch('time.time')
    def test_anomaly_detection_top_3_percent_red(self, mock_time):
        """Test IQR/Z-score detecting top 3% anomalies."""
        throttler = AdaptiveStreamThrottler()

        # Feed normal data
        mock_time.return_value = 1000.0
        throttler.should_emit("stream1")

        current_time = 1000.2
        for _ in range(100):
            mock_time.return_value = current_time
            throttler.should_emit("stream1")
            current_time += 0.2 # 200ms intervals

        # Feed an anomaly that is a top 3% anomaly
        current_time += 5.0 # 5000ms delay
        mock_time.return_value = current_time
        res = throttler.should_emit("stream1")

        self.assertTrue(res["emit"])
        self.assertEqual(res["status"], "red")
        self.assertIn("severe anomalies", res["analysis_reason"])

    @patch('time.time')
    def test_yellow_anomaly_detection(self, mock_time):
        """Test IQR yellow status"""
        radar = AnomalyRadar()
        # To get a yellow status, we need an anomaly that is not a top anomaly.
        for _ in range(100):
            radar.add_data_point(10.0) # upper_bound = 10.0

        # Feed an anomaly that is between upper_bound and top_3_threshold (15.0)
        radar.add_data_point(12.0)

        res = radar.analyze()
        self.assertEqual(res["status"], "yellow")
        self.assertIn("minor anomalies", res["reason"])

    @patch('time.time')
    def test_dirty_data_self_healing(self, mock_time):
        """Test handling corrupted timestamps or string intervals."""
        # Test dirty default window
        throttler = AdaptiveStreamThrottler(default_window_ms="dirty")
        self.assertEqual(throttler.current_window_ms, 150.0)

        radar = AnomalyRadar()
        # Feed dirty data
        radar.add_data_point("NaN")
        radar.add_data_point("Inf")
        radar.add_data_point("invalid")
        radar.add_data_point(None)

        # Verify it handled it gracefully as 0.0s
        self.assertEqual(radar.history, [0.0, 0.0, 0.0, 0.0])

        res = radar.analyze()
        self.assertEqual(res["status"], "green")
        self.assertEqual(len(res["top_anomalies"]), 0)

    @patch('time.time')
    def test_monotonic_sequence_lock(self, mock_time):
        """Test that sequence locks reject older/out-of-order sequence numbers."""
        throttler = AdaptiveStreamThrottler()
        mock_time.return_value = 1000.0

        res1 = throttler.should_emit("stream1", seq=10)
        self.assertTrue(res1["emit"])

        mock_time.return_value = 1001.0
        # Send older sequence
        res2 = throttler.should_emit("stream1", seq=5)
        self.assertFalse(res2["emit"])
        self.assertEqual(res2["status"], "yellow")
        self.assertIn("Sequence out of order", res2["reason"])

        # Send same sequence
        res3 = throttler.should_emit("stream1", seq=10)
        self.assertFalse(res3["emit"])
        self.assertEqual(res3["status"], "yellow")

        # Send newer sequence
        res4 = throttler.should_emit("stream1", seq=11)
        self.assertTrue(res4["emit"])

        # Send dirty sequence
        res5 = throttler.should_emit("stream1", seq="dirty")
        # Should fallback to 0, which is <= 11, so it fails lock
        self.assertFalse(res5["emit"])

    @patch('time.time')
    def test_extreme_boundaries_dynamic_window(self, mock_time):
        """Test window dynamically adjusting between 150ms and 500ms under boundary conditions."""
        throttler = AdaptiveStreamThrottler()
        self.assertEqual(throttler.current_window_ms, 150.0)

        mock_time.return_value = 1000.0
        throttler.should_emit("s")

        current_time = 1000.2
        # Induce red state multiple times to push to max window
        for _ in range(50):
            # Normal data
            for _ in range(40):
                mock_time.return_value = current_time
                throttler.should_emit("s")
                current_time += 0.2
            # Extreme anomaly
            current_time += 10.0
            mock_time.return_value = current_time
            throttler.should_emit("s")

        self.assertEqual(throttler.current_window_ms, 500.0) # Should be capped at 500.0

        # Now induce green state multiple times to push back to min window
        # Create a new radar to reset history quickly for the test
        throttler.radar = AnomalyRadar()
        # Reset last emit time to avoid the 10.0 jump registering in the new radar
        throttler.last_emit_time = 0.0

        current_time += 10.0
        mock_time.return_value = current_time
        throttler.should_emit("s")

        for _ in range(100):
            current_time += 0.5 # 500ms intervals which is normal now
            mock_time.return_value = current_time
            throttler.should_emit("s")

        self.assertEqual(throttler.current_window_ms, 150.0) # Should be bottomed at 150.0

if __name__ == '__main__':
    unittest.main()
