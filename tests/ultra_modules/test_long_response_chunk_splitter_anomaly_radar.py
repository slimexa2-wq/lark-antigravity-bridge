import unittest
from ultra_modules.long_response_chunk_splitter_anomaly_radar import ChunkSplitterAnomalyRadar

class TestChunkSplitterAnomalyRadar(unittest.TestCase):

    def test_normal_flow(self):
        """Test normal execution with a clear anomaly."""
        data = [
            {'id': '1', 'text': 'A'*50, 'value': 10},
            {'id': '2', 'text': 'B'*50, 'value': 12},
            {'id': '3', 'text': 'C'*50, 'value': 11},
            {'id': '4', 'text': 'D'*50, 'value': 100}, # Anomaly
            {'id': '5', 'text': 'E'*50, 'value': 10},
            {'id': '6', 'text': 'F'*50, 'value': 9},
            {'id': '7', 'text': 'G'*50, 'value': 11},
            {'id': '8', 'text': 'H'*50, 'value': 10},
        ]
        radar = ChunkSplitterAnomalyRadar(data, chunk_size=120)
        result = radar.process()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total_items'], 8)

        # Check chunks length (50 + 50 = 100 < 120, so 2 items per chunk)
        self.assertEqual(len(result['chunks']), 4)

        # Find item 4 and check if it's marked red
        found_anomaly = False
        for chunk in result['chunks']:
            for item in chunk:
                if item['id'] == '4':
                    self.assertEqual(item['marker'], 'red')
                    found_anomaly = True
                elif item['id'] == '1':
                    self.assertEqual(item['marker'], 'green')

        self.assertTrue(found_anomaly)

    def test_dirty_data_self_healing(self):
        """Test with missing, non-dict, and invalid values."""
        data = [
            "not a dict",
            {'id': '1', 'text': 'Valid', 'value': 10},
            {'id': '2', 'value': 'not a float'}, # missing text, invalid value
            {'text': 'Missing ID', 'value': 15}, # missing id
        ]
        radar = ChunkSplitterAnomalyRadar(data)
        result = radar.process()

        # 1 item removed, 3 cleaned
        self.assertEqual(result['total_items'], 3)
        chunks = result['chunks']
        self.assertEqual(len(chunks), 1)

        items = chunks[0]
        self.assertEqual(items[0]['id'], '1')

        self.assertEqual(items[1]['id'], '2')
        self.assertEqual(items[1]['text'], '')
        self.assertEqual(items[1]['value'], 0.0)

        self.assertEqual(items[2]['id'], 'unknown')
        self.assertEqual(items[2]['text'], 'Missing ID')

        # Check audit trail
        self.assertIn("Cleaned non-dict item: not a dict", radar._audit_trail)
        self.assertTrue(any("Cleaned non-numeric value" in log for log in radar._audit_trail))

    def test_missing_parameter_defaults(self):
        """Test with None data and missing chunk_size."""
        radar = ChunkSplitterAnomalyRadar(None)
        result = radar.process()
        self.assertEqual(result['total_items'], 0)
        self.assertEqual(result['chunks'], [])

        # Test string chunk size -> fallback
        radar2 = ChunkSplitterAnomalyRadar([], chunk_size="invalid")
        self.assertEqual(radar2.chunk_size, 500)

        # Test small chunk size -> min boundary 100
        radar3 = ChunkSplitterAnomalyRadar([], chunk_size=50)
        self.assertEqual(radar3.chunk_size, 100)

    def test_extreme_boundaries_zero_variance(self):
        """Test with all identical values (IQR = 0)."""
        data = [
            {'id': str(i), 'text': 'A', 'value': 5.0} for i in range(10)
        ]
        radar = ChunkSplitterAnomalyRadar(data)
        result = radar.process()

        self.assertEqual(result['total_items'], 10)
        for chunk in result['chunks']:
            for item in chunk:
                # With IQR 0, none should be anomalies
                self.assertEqual(item['marker'], 'green')

    def test_empty_data(self):
        """Test with empty list."""
        radar = ChunkSplitterAnomalyRadar([])
        result = radar.process()
        self.assertEqual(result['total_items'], 0)
        self.assertEqual(len(result['chunks']), 0)

        # iqr test on empty
        lower, upper = radar._calculate_iqr_thresholds([])
        self.assertEqual(lower, 0.0)
        self.assertEqual(upper, 0.0)

if __name__ == '__main__':
    unittest.main()
