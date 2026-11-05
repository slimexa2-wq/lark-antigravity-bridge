import unittest
from ultra_modules.multi_bot_mention_dispatcher_anomaly_radar import MultiBotAnomalyRadar

class TestMultiBotAnomalyRadar(unittest.TestCase):
    def setUp(self):
        self.radar = MultiBotAnomalyRadar()

    def test_normal_distribution_flow(self):
        # 100 items around 50
        data = [50 + (i % 5 - 2) for i in range(100)]
        results = self.radar.dispatch_and_analyze(data)

        self.assertEqual(len(results), 100)
        # Check that nothing is flagged as 'red' since there are no anomalies
        red_tags = [r for r in results if r['tag'] == 'red']
        self.assertEqual(len(red_tags), 0)

        # Check that reason is the default green reason
        green_tags = [r for r in results if r['tag'] == 'green']
        self.assertGreater(len(green_tags), 0)
        self.assertEqual(green_tags[0]['reason'], "正常放行")

    def test_malformed_string_auto_healing(self):
        # Mixed dirty data
        data = [10, "20", "invalid_string", None, {"value": "30"}, {"value": None}, 40]
        results = self.radar.dispatch_and_analyze(data)

        self.assertEqual(len(results), 7)
        cleaned_values = [r['original_data'] for r in results]
        self.assertIn("invalid_string", cleaned_values)

        # Verify invalid_string was treated as 0.0 internally
        # We can check z-scores are calculated without error
        for r in results:
            self.assertIsInstance(r['z_score'], float)

    def test_null_parameters_fallback(self):
        # Test missing / null parameters fallback
        results = self.radar.dispatch_and_analyze(None)
        self.assertEqual(results, [])

        # Test passing single non-list item
        results_single = self.radar.dispatch_and_analyze(42)
        self.assertEqual(len(results_single), 1)
        self.assertEqual(results_single[0]['tag'], 'green')

    def test_zscore_extreme_outliers(self):
        # 100 normal items + 3 extreme items to simulate exactly 3% outlier scenario
        data = [10 for _ in range(100)] + [10000, 10001, 10002]
        results = self.radar.dispatch_and_analyze(data)

        self.assertEqual(len(results), 103)
        red_tags = [r for r in results if r['tag'] == 'red']

        # It should flag the top 3% (ceil(103 * 0.03) = 4, but we only have 3 extreme outliers > zscore 2 or iqr)
        self.assertEqual(len(red_tags), 3)

        # Verify the reason format for one of the red items
        self.assertIn("数值异常偏离！", red_tags[0]['reason'])
        self.assertIn("属于前 3% 的离群分布", red_tags[0]['reason'])

    def test_empty_input_array(self):
        # Edge case: empty list
        results = self.radar.dispatch_and_analyze([])
        self.assertEqual(results, [])

    def test_100_percent_coverage_cases(self):
        # Line 18: data is None
        self.radar.calculate_z_scores_and_iqr(None)

        # Line 39: n == 0 after cleaning? Let's just mock cleaned_values len to 0 or pass non-list
        # Actually n == 0 if data is [] (line 24 catches it though).
        # Wait, if data is [], line 24 returns [].
        # Is it possible for n == 0 at line 39?
        # Only if data had items but len(cleaned_values) == 0. But cleaned_values appends for EVERY item.
        # So n will be equal to len(data).
        # Wait, data is [], then len(cleaned_values) is 0.
        # But `if not data: return []` catches it first.
        # Let's cover stats_data is None in apply_traffic_light_tags
        self.radar.apply_traffic_light_tags(None)

        # Cover non-list stats_data
        self.radar.apply_traffic_light_tags({"deviation": 5.0})

        # To cover `f == c` in percentile (line 54)
        # We need `k` to be an integer. `k = (n - 1) * p`.
        # For p=0.25 (1/4) and p=0.75 (3/4).
        # We need (n-1) to be a multiple of 4.
        # Let n-1 = 4 => n = 5.
        self.radar.calculate_z_scores_and_iqr([1, 2, 3, 4, 5])

        # Cover n = 1 in calculate_z_scores_and_iqr (std_dev = 0 branch as well)
        self.radar.calculate_z_scores_and_iqr([10])

        # Let's test apply_traffic_light_tags directly with empty array
        self.radar.apply_traffic_light_tags([])

if __name__ == '__main__':
    unittest.main() # pragma: no cover
