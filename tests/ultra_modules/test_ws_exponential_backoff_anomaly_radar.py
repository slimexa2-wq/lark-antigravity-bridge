import unittest
import math
from ultra_modules.ws_exponential_backoff_anomaly_radar import WSRecoveryRadar

class TestWSRecoveryRadar(unittest.TestCase):

    def test_missing_parameter_fallback(self):
        # Missing parameters fallback to default
        radar1 = WSRecoveryRadar()
        self.assertEqual(radar1.base_delay, 1.0)
        self.assertEqual(radar1.max_delay, 60.0)

        # Incorrect types and values fallback
        radar2 = WSRecoveryRadar(base_delay="abc", max_delay=None)
        self.assertEqual(radar2.base_delay, 1.0)
        self.assertEqual(radar2.max_delay, 60.0)

        # NaN and Inf handling
        radar3 = WSRecoveryRadar(base_delay=float('nan'), max_delay=float('inf'))
        self.assertEqual(radar3.base_delay, 1.0)
        self.assertEqual(radar3.max_delay, 60.0)

        # Negative values fallback
        radar4 = WSRecoveryRadar(base_delay=-5, max_delay=0)
        self.assertEqual(radar4.base_delay, 1.0)
        self.assertEqual(radar4.max_delay, 60.0)

        # Base delay greater than max delay (should swap)
        radar5 = WSRecoveryRadar(base_delay=100.0, max_delay=10.0)
        self.assertEqual(radar5.base_delay, 10.0)
        self.assertEqual(radar5.max_delay, 100.0)

    def test_normal_behavior_with_anomalies(self):
        radar = WSRecoveryRadar()
        # Normal distribution-like array with mostly 10s and one extreme value
        metrics = [10] * 97 + [11, 9, 1000]
        results = radar.analyze_metrics(metrics)

        self.assertEqual(len(results), 100)

        # The value 1000 should be marked red (anomaly)
        anomalies = [r for r in results if r['status'] == 'red']
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]['value'], 1000)
        self.assertIn("偏离正常指标极值", anomalies[0]['reason'])

        # The normal values should be green
        normals = [r for r in results if r['status'] == 'green']
        self.assertEqual(len(normals), 99)

    def test_extreme_boundary_conditions(self):
        radar = WSRecoveryRadar()

        # Empty array
        self.assertEqual(radar.analyze_metrics([]), [])

        # Non-list input
        self.assertEqual(radar.analyze_metrics("not a list"), [])
        self.assertEqual(radar.analyze_metrics(None), [])

        # Tiny array (n < 3)
        tiny = [10, 20]
        tiny_res = radar.analyze_metrics(tiny)
        self.assertEqual(len(tiny_res), 2)
        self.assertEqual(tiny_res[0]['status'], 'green')
        self.assertEqual(tiny_res[1]['status'], 'green')

        # Zero variance (all elements same)
        same_res = radar.analyze_metrics([5, 5, 5, 5, 5])
        self.assertEqual(len(same_res), 5)
        self.assertTrue(all(r['status'] == 'green' for r in same_res))

    def test_dirty_data_self_healing(self):
        radar = WSRecoveryRadar()

        # Mixed dirty data
        metrics = [
            10, 12, "15", "invalid", None, float('nan'), float('inf'), 20, 25, 30, 2000
        ]

        results = radar.analyze_metrics(metrics)
        # Should process 10, 12, 15.0, 20, 25, 30, 2000 (total 7 items)
        self.assertEqual(len(results), 7)

        values = [r['value'] for r in results]
        self.assertEqual(sorted(values), [10.0, 12.0, 15.0, 20.0, 25.0, 30.0, 2000.0])

        anomalies = [r for r in results if r['status'] == 'red']
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]['value'], 2000.0)

    def test_exponential_backoff_and_jitter(self):
        radar = WSRecoveryRadar(base_delay=1.0, max_delay=30.0)

        # Invalid retry count
        delay_invalid = radar.calculate_backoff("invalid")
        self.assertTrue(0 <= delay_invalid <= 1.0)

        delay_neg = radar.calculate_backoff(-5)
        self.assertTrue(0 <= delay_neg <= 1.0)

        # Normal exponential with jitter
        # For retry_count = 3, base = 1.0 -> exp = 8.0
        # Should be between 0 and 8.0
        delays = [radar.calculate_backoff(3) for _ in range(50)]
        for d in delays:
            self.assertTrue(0 <= d <= 8.0)

        # Capping at max_delay
        # For retry_count = 10, exp = 1024, capped at 30.0
        delays_capped = [radar.calculate_backoff(10) for _ in range(50)]
        for d in delays_capped:
            self.assertTrue(0 <= d <= 30.0)

        # Large retry_count capping at 30 logic internally
        delays_large = [radar.calculate_backoff(100) for _ in range(50)]
        for d in delays_large:
            self.assertTrue(0 <= d <= 30.0)

        # Verify it's actually jittered and not returning same number always
        self.assertTrue(len(set(delays)) > 1)

if __name__ == '__main__':
    unittest.main() # pragma: no cover
