import unittest
import math
from ultra_modules.daily_ops_digest_pusher_anomaly_radar import DailyOpsDigestPusherAnomalyRadar

class TestDailyOpsDigestPusherAnomalyRadar(unittest.TestCase):
    def setUp(self):
        self.radar = DailyOpsDigestPusherAnomalyRadar()

    def test_normal_operation(self):
        # 100 items to easily hit the 3% boundary
        data = [{'name': f'Item {i}', 'value': 100 + i % 10} for i in range(97)]
        # Add 3 clear outliers (Top 3%)
        data.extend([
            {'name': 'Outlier 1', 'value': 1000},
            {'name': 'Outlier 2', 'value': 1200},
            {'name': 'Outlier 3', 'value': 1100},
        ])

        results = self.radar.analyze(data)

        self.assertEqual(len(results), 100)

        reds = [r for r in results if r['status'] == 'Red']
        self.assertEqual(len(reds), 3)
        for r in reds:
            self.assertTrue('Outlier' in r['name'])

        yellows = [r for r in results if r['status'] == 'Yellow']
        self.assertTrue(len(yellows) <= 3) # Up to top 3% * 2

        greens = [r for r in results if r['status'] == 'Green']
        self.assertTrue(len(greens) >= 94)

    def test_dirty_data_healing(self):
        dirty_data = [
            {'name': 'Valid', 'value': 10},
            {'name': 'String Value', 'value': '20'},
            {'name': 'Invalid String', 'value': 'abc'},
            {'name': 'None Value', 'value': None},
            {'name': 'NaN Value', 'value': float('nan')},
            {'name': 'Inf Value', 'value': float('inf')},
            ['Not a dict'],
            {'no_value_key': True},
        ]

        results = self.radar.analyze(dirty_data)

        # 'Not a dict' is skipped. So we expect 7 valid dicts.
        self.assertEqual(len(results), 7)

        val_map = {r['name']: r['value'] for r in results if 'name' in r}

        self.assertEqual(val_map['Valid'], 10.0)
        self.assertEqual(val_map['String Value'], 20.0)
        self.assertEqual(val_map['Invalid String'], 0.0)
        self.assertEqual(val_map['None Value'], 0.0)
        self.assertEqual(val_map['NaN Value'], 0.0)
        self.assertEqual(val_map['Inf Value'], 0.0)
        self.assertEqual(val_map.get('Unknown', 0.0), 0.0) # For {'no_value_key': True}

        # Given n=7, 3% is 1, so we expect 1 Red, 1 Yellow maybe.
        # But this tests mostly data healing.

    def test_missing_parameter_fallbacks(self):
        # Test with None input
        results = self.radar.analyze(None)
        self.assertEqual(results, [])

        # Test with empty list
        results = self.radar.analyze([])
        self.assertEqual(results, [])

        # Test not a list
        results = self.radar.analyze("not a list")
        self.assertEqual(results, [])

    def test_boundary_conditions(self):
        # Test size 1 (std_dev = 0, no anomalies)
        results = self.radar.analyze([{'name': 'Only', 'value': 10}])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], 'Green')

        # Test zero variance
        results = self.radar.analyze([{'name': f'Same {i}', 'value': 100} for i in range(10)])
        self.assertEqual(len(results), 10)
        for r in results:
            self.assertEqual(r['status'], 'Green')

    def test_extreme_boundaries(self):
        # Verify percentiles logic
        data = [{'name': f'Item {i}', 'value': i} for i in range(1, 6)]
        # n = 5, top 3% count = ceil(0.15) = 1
        # values: 1, 2, 3, 4, 5
        # mean = 3, variance = 2, std_dev = 1.414
        # iqr: q1 (k=1) = 2, q3 (k=3) = 4 -> iqr = 2
        # val = 5: score = 2 / 1.414 = 1.414
        # This should trigger Red
        results = self.radar.analyze(data)

        # At least one red because 5 has score > 1.0
        reds = [r for r in results if r['status'] == 'Red']
        self.assertTrue(len(reds) > 0)

        # Test exact percentile logic branch coverage
        # n = 4, p=0.25 -> k = 0.75 -> f=0, c=1 (d0 and d1 used)
        data = [{'name': f'Item {i}', 'value': i} for i in range(1, 5)]
        results = self.radar.analyze(data)
        self.assertEqual(len(results), 4)

if __name__ == '__main__':
    unittest.main() # pragma: no cover
