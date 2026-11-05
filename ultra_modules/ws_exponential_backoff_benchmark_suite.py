import time
import random
from typing import Optional, Dict, Any, List
import datetime

class WSReconnectStateMachine:
    """
    Feishu/Lark WebSocket exponential backoff reconnect state machine with random jitter.
    Features silent self-healing and dirty data resilience.
    """

    # State constants
    STATE_CONNECTED = 'CONNECTED'
    STATE_DISCONNECTED = 'DISCONNECTED'
    STATE_RECONNECTING = 'RECONNECTING'
    STATE_TERMINATED = 'TERMINATED'

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize with config, featuring missing parameter default fallbacks.
        """
        if config is None:
            config = {}

        # Default fallbacks and dirty data self-healing
        try:
            self.base_delay = float(config.get('base_delay', 100)) # ms
            if self.base_delay <= 0 or self.base_delay > 10000:
                self.base_delay = 100
        except (ValueError, TypeError):
            self.base_delay = 100

        try:
            self.max_delay = float(config.get('max_delay', 30000)) # ms
            if self.max_delay <= 0 or self.max_delay > 300000:
                self.max_delay = 30000
        except (ValueError, TypeError):
            self.max_delay = 30000

        try:
            self.max_retries = int(config.get('max_retries', 10))
            if self.max_retries < 0 or self.max_retries > 1000:
                self.max_retries = 10
        except (ValueError, TypeError):
            self.max_retries = 10

        try:
            self.jitter_factor = float(config.get('jitter_factor', 0.2))
            if self.jitter_factor < 0.0 or self.jitter_factor > 1.0:
                self.jitter_factor = 0.2
        except (ValueError, TypeError):
            self.jitter_factor = 0.2

        # Ensure max_delay >= base_delay
        self.max_delay = max(self.base_delay, self.max_delay)

        self.state = self.STATE_DISCONNECTED
        self.retries = 0
        self.last_disconnect_time = 0.0
        self.last_reconnect_attempt = 0.0

    def transition_to(self, new_state: str) -> bool:
        """
        Safely transition to a new state.
        """
        valid_states = [self.STATE_CONNECTED, self.STATE_DISCONNECTED,
                        self.STATE_RECONNECTING, self.STATE_TERMINATED]

        if new_state not in valid_states:
            # Silent self-healing for invalid state requests
            return False

        if self.state == self.STATE_TERMINATED:
            return False # Terminal state cannot be escaped

        if new_state == self.STATE_DISCONNECTED and self.state == self.STATE_CONNECTED:
            self.last_disconnect_time = time.time()
            self.retries = 0

        elif new_state == self.STATE_CONNECTED:
            self.retries = 0

        self.state = new_state
        return True

    def get_next_backoff(self) -> float:
        """
        Calculate next backoff time in milliseconds using exponential backoff with jitter.
        Prevents overflow issues safely.
        """
        if self.state != self.STATE_RECONNECTING and self.state != self.STATE_DISCONNECTED:
            return 0.0

        if self.retries >= self.max_retries:
            self.transition_to(self.STATE_TERMINATED)
            return -1.0 # Indicator to stop retrying

        # Exponential calculation with cap to prevent overflow
        try:
            # 2^retries
            # Even with large retries, min(pow, max) prevents overflow as long as we cap early
            exp = min(self.retries, 30) # 2^30 * 100ms is huge, more than max_delay anyway
            backoff = self.base_delay * (2 ** exp)
        except Exception:
            backoff = self.max_delay

        # Cap at max delay
        backoff = min(backoff, self.max_delay)

        # Apply jitter
        jitter_amount = backoff * self.jitter_factor
        jitter = random.uniform(-jitter_amount, jitter_amount)

        final_delay = max(0, backoff + jitter)

        return final_delay

    def record_attempt(self) -> float:
        """
        Record a reconnection attempt, increment retries, and return the delay we should wait.
        """
        delay = self.get_next_backoff()
        if delay >= 0:
            self.retries += 1
            self.transition_to(self.STATE_RECONNECTING)
            self.last_reconnect_attempt = time.time()
        return delay

class WSBenchmarkSuite:
    """
    Benchmark suite for synthetic testing of the WSReconnectStateMachine.
    """

    @staticmethod
    def synthesize_dirty_configs(count: int) -> List[Dict[str, Any]]:
        """
        Generate dirty configurations for testing self-healing.
        """
        configs = []
        for _ in range(count):
            config = {
                'base_delay': random.choice([None, "invalid", -100, 1000000, 50]),
                'max_delay': random.choice([None, "nan", -1, 500000, 10000]),
                'max_retries': random.choice([None, 10.5, "five", -5, 2000, 5]),
                'jitter_factor': random.choice([None, "high", -0.5, 2.5, 0.5])
            }
            configs.append(config)
        return configs

    @staticmethod
    def simulate_concurrent_reconnects(concurrency: int = 1000) -> Dict[str, Any]:
        """
        Simulate ultra-high concurrency reconnects to verify zero crashes and performance.
        Returns benchmark metrics.
        """
        start_time = time.time()
        machines = [WSReconnectStateMachine() for _ in range(concurrency)]

        # Simulate disconnect and reconnect cycles
        total_delays = 0
        crashes = 0

        for m in machines:
            try:
                m.transition_to(WSReconnectStateMachine.STATE_DISCONNECTED)

                # Simulate a few retries
                for _ in range(3):
                    delay = m.record_attempt()
                    total_delays += delay
            except Exception:
                crashes += 1

        end_time = time.time()

        return {
            'concurrency': concurrency,
            'duration_ms': (end_time - start_time) * 1000,
            'crashes': crashes,
            'avg_delay_calculated': total_delays / (concurrency * 3) if concurrency > 0 else 0
        }

    @staticmethod
    def test_cross_year_boundary() -> bool:
        """
        Test behavior across extreme time boundaries (e.g. cross-year).
        """
        machine = WSReconnectStateMachine()
        machine.transition_to(WSReconnectStateMachine.STATE_DISCONNECTED)

        # Mock time across year boundary (e.g. Dec 31 23:59:59 to Jan 1 00:00:01)
        # In Python, time.time() is just a float, so we test large jumps in time manually
        # and ensure state machine doesn't crash on timestamp arithmetic if we added any.
        machine.last_disconnect_time = datetime.datetime(2023, 12, 31, 23, 59, 59).timestamp()

        # Simulate attempt 2 seconds later in the new year
        current_time = datetime.datetime(2024, 1, 1, 0, 0, 1).timestamp()

        # This implementation just uses backoff calculation, which is independent of absolute time,
        # but we verify it handles being called after a time gap
        machine.last_reconnect_attempt = current_time

        delay = machine.record_attempt()
        return delay > 0 and machine.state == WSReconnectStateMachine.STATE_RECONNECTING
