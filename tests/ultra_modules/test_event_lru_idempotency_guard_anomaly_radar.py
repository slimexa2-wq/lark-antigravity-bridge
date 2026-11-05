import unittest
from ultra_modules.event_lru_idempotency_guard_anomaly_radar import EventLRUIdempotencyGuardAnomalyRadar

class TestEventLRUIdempotencyGuardAnomalyRadar(unittest.TestCase):
    def setUp(self):
        self.radar = EventLRUIdempotencyGuardAnomalyRadar(max_lru_size=1000)

    def test_normal_condition(self):
        # Test normal event
        res = self.radar.process_event({'event_id': 'evt_001', 'metric_value': 1.0})
        self.assertEqual(res['status'], 'processed')
        self.assertEqual(res['color'], 'green')
        self.assertEqual(res['event_id'], 'evt_001')

    def test_idempotency_duplicate_rejection(self):
        # First event
        self.radar.process_event({'event_id': 'evt_002', 'metric_value': 1.0})
        # Duplicate event
        res = self.radar.process_event({'event_id': 'evt_002', 'metric_value': 2.0})
        self.assertEqual(res['status'], 'ignored')
        self.assertEqual(res['color'], 'yellow')
        self.assertEqual(res['event_id'], 'evt_002')

    def test_dirty_data_self_healing(self):
        # Missing event_id but has message_id
        res = self.radar.process_event({'message_id': 'msg_001'})
        self.assertEqual(res['status'], 'processed')
        self.assertEqual(res['color'], 'green')
        self.assertEqual(res['event_id'], 'msg_001')

        # Invalid metric_value
        res = self.radar.process_event({'event_id': 'evt_003', 'metric_value': 'invalid'})
        self.assertEqual(res['status'], 'processed')
        self.assertEqual(res['color'], 'green')

        # None event
        res = self.radar.process_event(None)
        self.assertEqual(res['status'], 'processed')
        self.assertTrue(res['event_id'].startswith('auto-healed-'))

        # List instead of dict
        res = self.radar.process_event(['not', 'a', 'dict'])
        self.assertEqual(res['status'], 'processed')
        self.assertTrue(res['event_id'].startswith('auto-healed-'))

    def test_missing_parameter_fallbacks(self):
        # Nested header event_id
        res = self.radar.process_event({'header': {'event_id': 'hdr_001'}})
        self.assertEqual(res['status'], 'processed')
        self.assertEqual(res['event_id'], 'hdr_001')

    def test_extreme_boundary_conditions_and_anomaly(self):
        radar = EventLRUIdempotencyGuardAnomalyRadar(max_lru_size=20)

        # Add 96 normal items
        for i in range(100):
            radar.process_event({'event_id': f'norm_{i}', 'metric_value': 10 + (i % 5)})

        # Add anomaly
        res = radar.process_event({'event_id': 'anom_1', 'metric_value': 100000.0})
        self.assertEqual(res['status'], 'flagged')
        self.assertEqual(res['color'], 'red')

        # Test LRU eviction
        # max size is 20, we added over 100 items. norm_0 should be evicted.
        res_norm_0 = radar.process_event({'event_id': 'norm_0', 'metric_value': 10})
        self.assertEqual(res_norm_0['status'], 'processed') # Not ignored because it was evicted

        # LRU max_size condition testing
        self.assertEqual(len(radar.lru_cache), 20)
        self.assertEqual(len(radar.history_metrics), 20)

if __name__ == '__main__':
    unittest.main() # pragma: no cover
