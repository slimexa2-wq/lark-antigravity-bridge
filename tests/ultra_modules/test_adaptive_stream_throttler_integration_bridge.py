import unittest
from ultra_modules.adaptive_stream_throttler_integration_bridge import AdaptiveStreamThrottlerBridge

class TestAdaptiveStreamThrottlerBridge(unittest.TestCase):
    def test_normal_and_monotonic(self):
        # 1. Normal emit
        state, should_emit, evt = AdaptiveStreamThrottlerBridge.process(
            event={'seq': 1, 'content': 'A'},
            state={},
            current_time_ms=1000
        )
        self.assertTrue(should_emit)
        self.assertEqual(evt['seq'], 1)
        self.assertEqual(state['last_seq'], 1)

        # 2. Duplicate seq (monotonic lock drop)
        state2, emit2, evt2 = AdaptiveStreamThrottlerBridge.process(
            event={'seq': 1, 'content': 'B'},
            state=state,
            current_time_ms=1200
        )
        self.assertFalse(emit2)
        self.assertIsNone(evt2)

        # 3. Smaller seq (monotonic lock drop)
        state3, emit3, evt3 = AdaptiveStreamThrottlerBridge.process(
            event={'seq': 0},
            state=state,
            current_time_ms=1300
        )
        self.assertFalse(emit3)
        self.assertIsNone(evt3)

        # 4. Next seq emits
        state4, emit4, evt4 = AdaptiveStreamThrottlerBridge.process(
            event={'seq': 2},
            state=state,
            current_time_ms=1400
        )
        self.assertTrue(emit4)
        self.assertEqual(state4['last_seq'], 2)

    def test_dirty_data_self_healing(self):
        # Invalid state
        bad_state = {
            'last_emit_time': 'invalid',
            'last_seq': 'invalid',
            'window_size': 9999
        }
        state, emit, evt = AdaptiveStreamThrottlerBridge.process(
            event={'seq': '10'}, # parseable int
            state=bad_state,
            current_time_ms=1000
        )
        self.assertTrue(emit)
        self.assertEqual(state['window_size'], 150)
        self.assertEqual(state['last_seq'], 10)

        # Invalid event entirely
        state2, emit2, evt2 = AdaptiveStreamThrottlerBridge.process(
            event="not a dict",
            state=state,
            current_time_ms=1200
        )
        self.assertFalse(emit2)
        self.assertIsNone(evt2)

        # Unparseable seq
        state3, emit3, evt3 = AdaptiveStreamThrottlerBridge.process(
            event={'seq': 'abc'},
            state=state,
            current_time_ms=1300
        )
        self.assertFalse(emit3)
        self.assertIsNone(evt3)

        # State totally not dict
        state4, emit4, evt4 = AdaptiveStreamThrottlerBridge.process(
            event={'seq': 11},
            state="broken state",
            current_time_ms=1000
        )
        self.assertTrue(emit4)
        self.assertEqual(evt4['seq'], 11)

    def test_missing_parameter_fallback(self):
        # Zero config, completely empty params
        state, emit, evt = AdaptiveStreamThrottlerBridge.process(
            event={'sequence_id': 1} # using fallback seq field
        )
        self.assertTrue(emit)
        self.assertTrue(state['last_emit_time'] > 0)
        self.assertEqual(state['last_seq'], 1)
        self.assertEqual(evt['seq'], 1)

    def test_extreme_boundary_and_adaptive_window(self):
        state = {'last_emit_time': 1000, 'last_seq': 1, 'window_size': 150}

        # Too fast, throttled
        state2, emit2, evt2 = AdaptiveStreamThrottlerBridge.process(
            event={'seq': 2}, state=state, current_time_ms=1100
        )
        self.assertFalse(emit2)
        self.assertEqual(state2['last_seq'], 2)
        self.assertEqual(state2['window_size'], 150)

        # High frequency, adapt window UP (+50 -> 200)
        state3, emit3, evt3 = AdaptiveStreamThrottlerBridge.process(
            event={'seq': 3}, state=state2, current_time_ms=1200
        )
        self.assertTrue(emit3)
        self.assertEqual(state3['window_size'], 200)

        # Force window to 500 (max)
        state3['window_size'] = 500
        state4, emit4, evt4 = AdaptiveStreamThrottlerBridge.process(
            event={'seq': 4}, state=state3, current_time_ms=1750 # time diff 550, less than 500*1.5 (750)
        )
        self.assertTrue(emit4)
        self.assertEqual(state4['window_size'], 500) # Capped at 500

        # Low frequency, adapt window DOWN (-50)
        state5, emit5, evt5 = AdaptiveStreamThrottlerBridge.process(
            event={'seq': 5}, state=state4, current_time_ms=3000 # time diff 1250, > 500*1.5
        )
        self.assertTrue(emit5)
        self.assertEqual(state5['window_size'], 450)

        # Force window to 150 (min), then adapt down again
        state5['window_size'] = 150
        state6, emit6, evt6 = AdaptiveStreamThrottlerBridge.process(
            event={'seq': 6}, state=state5, current_time_ms=5000
        )
        self.assertTrue(emit6)
        self.assertEqual(state6['window_size'], 150) # Capped at 150

    def test_schema_forward_compatibility(self):
        old_schema_event = {
            'seq_id': '100',
            'msg_id': 'm_123',
            'text': 'hello world'
        }
        state, emit, evt = AdaptiveStreamThrottlerBridge.process(old_schema_event, {}, 1000)
        self.assertTrue(emit)
        self.assertEqual(evt['seq'], 100)
        self.assertEqual(evt['message_id'], 'm_123')
        self.assertEqual(evt['content'], 'hello world')

    def test_clock_rewind(self):
        # Test clock rewinds backward
        state = {'last_emit_time': 5000, 'last_seq': 5, 'window_size': 150}

        # time is 1000, which is BEFORE last_emit_time
        state2, emit, evt = AdaptiveStreamThrottlerBridge.process(
            event={'seq': 6}, state=state, current_time_ms=1000
        )
        self.assertTrue(emit)
        self.assertEqual(state2['last_emit_time'], 1000)

if __name__ == '__main__':
    unittest.main() # pragma: no cover
