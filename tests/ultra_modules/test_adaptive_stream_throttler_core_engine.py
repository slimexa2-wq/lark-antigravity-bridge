import unittest
from ultra_modules.adaptive_stream_throttler_core_engine import process_stream_event

class TestAdaptiveStreamThrottler(unittest.TestCase):
    def test_1_normal_flow_and_monotonic_seq(self):
        # 1st event, should emit
        state, should_emit, evt = process_stream_event({}, {'seq': 1, 'data': 'A'}, 1000)
        self.assertTrue(should_emit)
        self.assertEqual(evt['seq'], 1)
        self.assertEqual(state['last_seq'], 1)

        # 2nd event with same seq, should NOT emit (discarded)
        state2, should_emit2, evt2 = process_stream_event(state, {'seq': 1, 'data': 'B'}, 1200)
        self.assertFalse(should_emit2)
        self.assertIsNone(evt2)

        # 3rd event with smaller seq, should NOT emit (discarded)
        state3, should_emit3, evt3 = process_stream_event(state, {'seq': 0, 'data': 'C'}, 1300)
        self.assertFalse(should_emit3)
        self.assertIsNone(evt3)

        # 4th event with larger seq, should emit
        state4, should_emit4, evt4 = process_stream_event(state, {'seq': 2, 'data': 'D'}, 1400)
        self.assertTrue(should_emit4)
        self.assertEqual(evt4['seq'], 2)

    def test_2_adaptive_window_throttling(self):
        # Initial state
        state = {'last_emit_time': 1000, 'last_seq': 1, 'window_size': 150}

        # Too fast, throttled (time diff 100 < 150)
        state, should_emit, evt = process_stream_event(state, {'seq': 2}, 1100)
        self.assertFalse(should_emit)
        self.assertEqual(state['window_size'], 150) # doesn't change window when throttled
        self.assertEqual(state['last_seq'], 2) # sequence advances even when throttled

        # Enough time elapsed, should emit and window should adapt
        # Fast emission (time diff 200 is close to 150*1.5=225) -> increases window
        state, should_emit, evt = process_stream_event(state, {'seq': 3}, 1200)
        self.assertTrue(should_emit)
        self.assertEqual(state['window_size'], 200) # 150 + 50

        # Later, very slow emission -> shrinks window
        state, should_emit, evt = process_stream_event(state, {'seq': 4}, 2000)
        self.assertTrue(should_emit)
        self.assertEqual(state['window_size'], 150) # 200 - 50 -> 150

    def test_3_bad_data_self_healing(self):
        # State with bad data
        bad_state = {
            'last_emit_time': 'invalid',
            'last_seq': None,
            'window_size': 9999 # way over 500
        }

        # Should self heal state and initialize correctly
        state, should_emit, evt = process_stream_event(bad_state, {'seq': '10'}, 1000)

        self.assertTrue(should_emit)
        self.assertEqual(state['window_size'], 150) # default because 9999 was clamped/rejected
        self.assertEqual(state['last_seq'], 10)
        self.assertEqual(state['last_emit_time'], 1000)
        self.assertEqual(evt['seq'], 10) # string '10' was parsed to int

        # Bad event (not a dict)
        state2, should_emit2, evt2 = process_stream_event(state, "not a dict", 1200)
        self.assertFalse(should_emit2)
        self.assertIsNone(evt2)
        self.assertEqual(state2['last_seq'], 10) # unaffected

        # Event with unparseable seq
        state3, should_emit3, evt3 = process_stream_event(state, {'seq': 'invalid_seq'}, 1300)
        self.assertFalse(should_emit3)
        self.assertIsNone(evt3)
        self.assertEqual(state3['last_seq'], 10)

    def test_4_default_fallback_zero_config(self):
        # Empty inputs should be handled gracefully
        state, should_emit, evt = process_stream_event(None, {'seq': 1})
        self.assertTrue(should_emit)
        self.assertEqual(state['window_size'], 150)
        self.assertEqual(state['last_seq'], 1)
        self.assertTrue(state['last_emit_time'] > 0) # Uses current system time
        self.assertEqual(evt['seq'], 1)

    def test_5_edge_cases_time_rewind(self):
        # System clock rewinds backward (e.g. NTP sync)
        state = {'last_emit_time': 5000, 'last_seq': 5, 'window_size': 150}

        # current time is 1000, which is BEFORE last_emit_time
        state2, should_emit, evt = process_stream_event(state, {'seq': 6}, 1000)

        # Since time rewind makes last_emit_time > current_time_ms,
        # the engine should heal last_emit_time to 0, which means it emits immediately.
        self.assertTrue(should_emit)
        self.assertEqual(state2['last_emit_time'], 1000)
        self.assertEqual(state2['last_seq'], 6)

if __name__ == '__main__':
    unittest.main()
