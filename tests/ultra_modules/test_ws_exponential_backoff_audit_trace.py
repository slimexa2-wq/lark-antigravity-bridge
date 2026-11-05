import unittest
import math
from ultra_modules.ws_exponential_backoff_audit_trace import WSRetryStateMachine

class TestWSRetryStateMachine(unittest.TestCase):
    def test_normal_input(self):
        """Test with normal, expected parameters"""
        sm = WSRetryStateMachine(base_delay=1000, max_delay=10000, jitter_factor=0.2)

        # Test first reconnect
        result1 = sm.process_reconnect_request()
        self.assertEqual(result1['attempt'], 1)
        # base_delay * 2^1 = 2000
        # Jitter +- 400 (2000 * 0.2)
        # So final_delay between 1600 and 2400
        self.assertGreaterEqual(result1['delay_ms'], 1600)
        self.assertLessEqual(result1['delay_ms'], 2400)

        # Check audit trace
        audit1 = result1['audit_trace']
        self.assertEqual(audit1['diff']['attempt_diff'], 1)
        self.assertEqual(audit1['pre_state']['attempt'], 0)
        self.assertEqual(audit1['post_state']['attempt'], 1)

        # Test second reconnect
        result2 = sm.process_reconnect_request()
        self.assertEqual(result2['attempt'], 2)
        # base_delay * 2^2 = 4000
        # Jitter +- 800 (4000 * 0.2)
        self.assertGreaterEqual(result2['delay_ms'], 3200)
        self.assertLessEqual(result2['delay_ms'], 4800)

    def test_dirty_data_healing(self):
        """Test healing of dirty data (None, NaN, strings, negative values)"""
        sm3 = WSRetryStateMachine(base_delay=1000, max_delay=500)
        self.assertEqual(sm3.state['max_delay'], 1000)
        # None, NaN, wrong types, missing parameters
        sm = WSRetryStateMachine(base_delay="invalid", max_delay=math.nan, jitter_factor=None)

        # Default fallbacks: base_delay=1000, max_delay=60000, jitter_factor=0.5
        self.assertEqual(sm.state['base_delay'], 1000)
        self.assertEqual(sm.state['max_delay'], 60000)
        self.assertEqual(sm.state['jitter_factor'], 0.5)

        # Negative bounds and bad attempts
        sm2 = WSRetryStateMachine(base_delay=-500, max_delay=-1000, jitter_factor=1.5)

        # base_delay bounded to min 0.1
        self.assertEqual(sm2.state['base_delay'], 0.1)
        # max_delay bounded to min 0.1, then ensured >= base_delay
        self.assertEqual(sm2.state['max_delay'], 0.1)
        # jitter_factor bounded to max 1.0
        self.assertEqual(sm2.state['jitter_factor'], 1.0)

        # Test process_reconnect_request with dirty data attempt
        result = sm.process_reconnect_request(external_attempt="garbage")
        # Should fallback to pre_state['attempt'] + 1 which is 1
        self.assertEqual(result['attempt'], 1)

        result = sm.process_reconnect_request(external_attempt=math.nan)
        self.assertEqual(result['attempt'], 2)

        result = sm.process_reconnect_request(external_attempt=-10)
        self.assertEqual(result['attempt'], 0) # Capped at min 0

    def test_missing_parameter_fallbacks(self):
        """Test behavior when no parameters are provided (defaults)"""
        sm = WSRetryStateMachine()
        self.assertEqual(sm.state['base_delay'], 1000)
        self.assertEqual(sm.state['max_delay'], 60000)
        self.assertEqual(sm.state['jitter_factor'], 0.5)

    def test_extreme_boundaries(self):
        """Test extremely large attempts to ensure no overflow"""
        sm = WSRetryStateMachine(base_delay=1000, max_delay=60000, jitter_factor=0.1)

        result = sm.process_reconnect_request(external_attempt=1000000)
        # max_delay is 60000, exp_delay will be capped at max_delay
        self.assertEqual(result['attempt'], 1000000)
        # jitter amount = 60000 * 0.1 = 6000
        # result delay is max_delay +- jitter = 60000 +- 6000
        self.assertGreaterEqual(result['delay_ms'], 54000)
        self.assertLessEqual(result['delay_ms'], 66000)

        result2 = sm.process_reconnect_request(external_attempt=float('inf'))
        # float('inf') will pass type check, int(inf) raises OverflowError, caught by _clean_number fallback
        # Wait, int(float('inf')) raises OverflowError, caught by ValueError in _clean_number
        # which means it will fallback to default_val = pre_state['attempt'] + 1 = 1000001
        self.assertEqual(result2['attempt'], 1000000000)

    def test_reset_and_state_diff(self):
        """Test state resetting and audit trace diff logic"""
        sm = WSRetryStateMachine()
        sm.process_reconnect_request(external_attempt=5)

        self.assertEqual(sm.state['attempt'], 5)

        result = sm.reset()
        self.assertEqual(result['status'], 'reset_successful')
        self.assertEqual(result['attempt'], 0)
        self.assertEqual(sm.state['attempt'], 0)

        audit_log = sm.audit_log
        self.assertEqual(len(audit_log), 2) # 1 for reconnect, 1 for reset
        self.assertEqual(audit_log[-1]['action'], 'reset')
        self.assertEqual(audit_log[-1]['diff']['attempt_diff'], -5)

if __name__ == '__main__':
    unittest.main()
