import unittest
import time
from ultra_modules.ws_exponential_backoff_benchmark_suite import WSReconnectStateMachine, WSBenchmarkSuite

class TestWSExponentialBackoffBenchmarkSuite(unittest.TestCase):

    def test_01_normal_backoff_progression(self):
        """Test 1: Verify normal state transitions and exponential backoff growth"""
        config = {'base_delay': 100, 'max_delay': 5000, 'jitter_factor': 0.0} # 0 jitter for exact testing
        machine = WSReconnectStateMachine(config)

        self.assertEqual(machine.state, WSReconnectStateMachine.STATE_DISCONNECTED)

        # First attempt (retries = 0) -> delay = 100 * 2^0 = 100
        delay1 = machine.record_attempt()
        self.assertEqual(delay1, 100.0)
        self.assertEqual(machine.retries, 1)
        self.assertEqual(machine.state, WSReconnectStateMachine.STATE_RECONNECTING)

        # Second attempt (retries = 1) -> delay = 100 * 2^1 = 200
        delay2 = machine.record_attempt()
        self.assertEqual(delay2, 200.0)
        self.assertEqual(machine.retries, 2)

        # Third attempt (retries = 2) -> delay = 100 * 2^2 = 400
        delay3 = machine.record_attempt()
        self.assertEqual(delay3, 400.0)

        # Test transition back to connected resets retries
        machine.transition_to(WSReconnectStateMachine.STATE_CONNECTED)
        self.assertEqual(machine.state, WSReconnectStateMachine.STATE_CONNECTED)
        self.assertEqual(machine.retries, 0)

    def test_02_dirty_data_self_healing(self):
        """Test 2: Verify zero crashes when config has invalid, negative, or crazy types (Silent self-healing)"""
        dirty_configs = WSBenchmarkSuite.synthesize_dirty_configs(10)

        for config in dirty_configs:
            # Should not crash during initialization
            machine = WSReconnectStateMachine(config)

            # Values should be forced to reasonable defaults
            self.assertTrue(0 < machine.base_delay <= 10000)
            self.assertTrue(machine.base_delay <= machine.max_delay <= 300000)
            self.assertTrue(0 <= machine.max_retries <= 1000)
            self.assertTrue(0.0 <= machine.jitter_factor <= 1.0)

            # Execution should not crash
            machine.transition_to(WSReconnectStateMachine.STATE_DISCONNECTED)
            delay = machine.record_attempt()
            self.assertGreaterEqual(delay, 0)

    def test_03_missing_param_fallbacks(self):
        """Test 3: Verify completely empty or None configs fall back to sensible defaults"""
        # None config
        machine1 = WSReconnectStateMachine(None)
        self.assertEqual(machine1.base_delay, 100.0)
        self.assertEqual(machine1.max_delay, 30000.0)
        self.assertEqual(machine1.max_retries, 10)
        self.assertEqual(machine1.jitter_factor, 0.2)

        # Empty dict config
        machine2 = WSReconnectStateMachine({})
        self.assertEqual(machine2.base_delay, 100.0)

        # Execution is safe
        delay = machine2.record_attempt()
        self.assertGreaterEqual(delay, 0)

    def test_04_extreme_boundary_conditions(self):
        """Test 4: Verify extreme bounds like max retries termination, max delay cap, and cross-year time limits"""
        machine = WSReconnectStateMachine({'base_delay': 1000, 'max_delay': 3000, 'max_retries': 3, 'jitter_factor': 0.0})

        # 1st attempt: 1000
        self.assertEqual(machine.record_attempt(), 1000.0)

        # 2nd attempt: 2000
        self.assertEqual(machine.record_attempt(), 2000.0)

        # 3rd attempt: 4000 capped to max_delay 3000
        self.assertEqual(machine.record_attempt(), 3000.0)

        # 4th attempt: exceeds max_retries of 3, should return -1 and terminate
        self.assertEqual(machine.record_attempt(), -1.0)
        self.assertEqual(machine.state, WSReconnectStateMachine.STATE_TERMINATED)

        # Cross year boundary test should not crash
        self.assertTrue(WSBenchmarkSuite.test_cross_year_boundary())

    def test_05_synthetic_benchmark_concurrency(self):
        """Test 5: Verify ultra-high concurrency synthetic benchmarking for performance and stability"""
        concurrency = 5000
        results = WSBenchmarkSuite.simulate_concurrent_reconnects(concurrency)

        self.assertEqual(results['concurrency'], concurrency)
        self.assertEqual(results['crashes'], 0)
        self.assertGreater(results['avg_delay_calculated'], 0)

        # Fast execution expected, should comfortably finish well within 1000ms
        self.assertLess(results['duration_ms'], 1000.0, "Benchmark should be highly performant (millisecond response)")

if __name__ == '__main__':
    unittest.main()
