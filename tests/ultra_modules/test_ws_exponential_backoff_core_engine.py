import unittest
import math
import random
from unittest.mock import patch
from ultra_modules.ws_exponential_backoff_core_engine import calculate_next_delay

class TestWsExponentialBackoffCoreEngine(unittest.TestCase):

    @patch('random.uniform')
    def test_normal_backoff(self, mock_uniform):
        # Disable jitter for predictable results by mocking random.uniform to return 0
        mock_uniform.return_value = 0

        # Test exponential progression
        self.assertEqual(calculate_next_delay(attempt=0, base_delay=1000, max_delay=60000, jitter_factor=0.5), 1000)
        self.assertEqual(calculate_next_delay(attempt=1, base_delay=1000, max_delay=60000, jitter_factor=0.5), 2000)
        self.assertEqual(calculate_next_delay(attempt=2, base_delay=1000, max_delay=60000, jitter_factor=0.5), 4000)
        self.assertEqual(calculate_next_delay(attempt=3, base_delay=1000, max_delay=60000, jitter_factor=0.5), 8000)

        # Test max delay capping
        self.assertEqual(calculate_next_delay(attempt=10, base_delay=1000, max_delay=60000, jitter_factor=0.5), 60000)

    @patch('random.uniform')
    def test_dirty_data_self_healing(self, mock_uniform):
        mock_uniform.return_value = 0

        # None values
        self.assertEqual(calculate_next_delay(attempt=None, base_delay=None, max_delay=None, jitter_factor=None), 1000)

        # String values (that can be parsed)
        self.assertEqual(calculate_next_delay(attempt="2", base_delay="2000", max_delay="10000", jitter_factor="0"), 8000)

        # Invalid string values
        self.assertEqual(calculate_next_delay(attempt="invalid", base_delay="bad", max_delay="data", jitter_factor="nope"), 1000)

        # List/dict (unparsable)
        self.assertEqual(calculate_next_delay(attempt=[], base_delay={}, max_delay=[], jitter_factor={}), 1000)

        # NaN values
        self.assertEqual(calculate_next_delay(attempt=float('nan'), base_delay=float('nan'), max_delay=float('nan'), jitter_factor=float('nan')), 1000)

        # Negative values
        self.assertEqual(calculate_next_delay(attempt=-5, base_delay=-1000, max_delay=-5000, jitter_factor=-1), 0.1) # base_delay gets clamped to 0.1

        # Jitter factor clamped to 1.0
        mock_uniform.return_value = 1000 # 1000 * 1.0 = 1000 jitter
        self.assertEqual(calculate_next_delay(attempt=0, base_delay=1000, max_delay=60000, jitter_factor=5.0), 0) # 1000 - 1000

    @patch('random.uniform')
    def test_default_fallback(self, mock_uniform):
        mock_uniform.return_value = 0

        # Test completely empty args
        self.assertEqual(calculate_next_delay(), 1000)

        # Defaults internally: attempt=0, base_delay=1000, max_delay=60000
        self.assertEqual(calculate_next_delay(attempt=1), 2000)

    @patch('random.uniform')
    def test_extreme_boundaries(self, mock_uniform):
        mock_uniform.return_value = 0

        # Extreme large attempt (avoids OverflowError and caps at max_delay)
        self.assertEqual(calculate_next_delay(attempt=1000000, base_delay=1000, max_delay=60000, jitter_factor=0), 60000)

        # Overflow condition specifically inside try-except (if limit didn't exist)
        # Using a huge base_delay
        self.assertEqual(calculate_next_delay(attempt=1000, base_delay=1e308, max_delay=1e308, jitter_factor=0), 1e308)

        # Max delay smaller than base delay (self-healing should fix this)
        self.assertEqual(calculate_next_delay(attempt=0, base_delay=5000, max_delay=1000, jitter_factor=0), 5000)

    def test_jitter_distribution(self):
        # We don't mock uniform here, we want real random behavior

        results = []
        for _ in range(100):
            # Base logic calculates 1000. Jitter factor 0.5 means jitter amount is 500.
            # So delay will be 1000 - uniform(0, 500), resulting in [500, 1000]
            val = calculate_next_delay(attempt=0, base_delay=1000, max_delay=60000, jitter_factor=0.5)
            self.assertTrue(500 <= val <= 1000)
            results.append(val)

        # Ensure we're actually getting random values
        unique_results = set(results)
        self.assertTrue(len(unique_results) > 10)

if __name__ == '__main__':
    unittest.main()
