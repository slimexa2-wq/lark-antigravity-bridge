import unittest
from ultra_modules.voice_message_intent_parser_anomaly_radar import extract_anomalies

class TestVoiceMessageIntentParserAnomalyRadar(unittest.TestCase):
    def test_normal_execution_no_anomalies(self):
        # 1. Normal execution: No anomalies (all within ~1.88 Z-score)
        data = [
            {'id': 'item1', 'value': 100},
            {'id': 'item2', 'value': 105},
            {'id': 'item3', 'value': 95},
            {'id': 'item4', 'value': 102},
            {'id': 'item5', 'value': 98}
        ]
        result = extract_anomalies(data)

        self.assertEqual(len(result['anomalies']), 0)
        self.assertEqual(len(result['normal']), 5)
        self.assertEqual(result['stats']['count'], 5)
        for item in result['normal']:
            self.assertEqual(item['color'], 'green')
            self.assertIn("正常范围", item['reason'])

    def test_anomaly_detection(self):
        # 2. Normal execution: Detect top anomalies (Z > 1.88)
        data = [
            {'id': f'item{i}', 'value': 100} for i in range(20)
        ]
        # Inject an anomaly that is way larger than the rest
        data.append({'id': 'anomaly1', 'value': 1000})

        result = extract_anomalies(data)

        self.assertTrue(len(result['anomalies']) > 0)

        anomaly_item = next((item for item in result['anomalies'] if item['id'] == 'anomaly1'), None)
        self.assertIsNotNone(anomaly_item)
        self.assertEqual(anomaly_item['color'], 'red')
        self.assertIn("严重偏高", anomaly_item['reason'])

    def test_dirty_data_self_healing(self):
        # 3. Dirty data self-healing
        data = [
            {'id': 'item1', 'value': "100"}, # String number
            {'id': 'item2', 'value': "abc"}, # Invalid string
            {'id': 'item3', 'value': None},  # None value
            "totally invalid item",          # Not a dict
            {'id': 'item5', 'value': 100}    # Normal
        ]
        result = extract_anomalies(data, default_value=50.0)

        self.assertEqual(result['stats']['count'], 5)

        # Verify the self-healing extracted or defaulted properly
        values = [item['value'] for item in result['normal'] + result['anomalies']]

        # item1: "100" -> 100.0
        # item2: "abc" -> 50.0 (default)
        # item3: None -> 50.0 (default)
        # invalid: string -> 50.0 (default)
        # item5: 100 -> 100.0

        self.assertCountEqual(values, [100.0, 50.0, 50.0, 50.0, 100.0])

    def test_missing_parameters_defaults(self):
        # 4. Missing parameters default handling
        # Using a different target_key
        data = [
            {'id': '1', 'score': 10},
            {'id': '2'}, # missing 'score' key
            {'id': '3', 'score': 20}
        ]
        result = extract_anomalies(data, target_key='score', default_value=15.0)

        self.assertEqual(result['stats']['count'], 3)
        values = {item['id']: item['score'] for item in result['normal'] + result['anomalies']}
        self.assertEqual(values['1'], 10.0)
        self.assertEqual(values['2'], 15.0) # Used default
        self.assertEqual(values['3'], 20.0)

    def test_extreme_edge_cases(self):
        # 5. Extreme boundary conditions: Empty list, Single element, Zero variance

        # Empty list
        result_empty = extract_anomalies([])
        self.assertEqual(result_empty['stats']['count'], 0)
        self.assertEqual(len(result_empty['normal']), 0)
        self.assertEqual(len(result_empty['anomalies']), 0)

        # Single element
        result_single = extract_anomalies([{'id': '1', 'value': 42}])
        self.assertEqual(result_single['stats']['count'], 1)
        self.assertEqual(len(result_single['normal']), 1)
        self.assertEqual(result_single['normal'][0]['color'], 'green')
        self.assertEqual(result_single['stats']['mean'], 42.0)
        self.assertEqual(result_single['stats']['stdev'], 0.0)

        # Zero variance (all elements same value)
        result_zero_var = extract_anomalies([
            {'id': '1', 'value': 10},
            {'id': '2', 'value': 10},
            {'id': '3', 'value': 10}
        ])
        self.assertEqual(result_zero_var['stats']['count'], 3)
        self.assertEqual(result_zero_var['stats']['stdev'], 0.0)
        self.assertEqual(len(result_zero_var['anomalies']), 0)
        self.assertEqual(len(result_zero_var['normal']), 3)

if __name__ == '__main__':
    unittest.main()
