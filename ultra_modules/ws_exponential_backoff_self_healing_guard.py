import time
import math
import random

class WsExponentialBackoffSelfHealingGuard:
    def __init__(self, base_delay=1000, max_delay=60000, jitter_ratio=0.5):
        # Initial configurations self-healing
        self.base_delay = self._clean_numeric(base_delay, 1000, min_val=0.1)
        self.max_delay = self._clean_numeric(max_delay, 60000, min_val=self.base_delay)
        if self.max_delay < self.base_delay:
            self.max_delay = self.base_delay

        self.jitter_ratio = self._clean_numeric(jitter_ratio, 0.5, min_val=0.0, max_val=1.0)

        # State
        self.state = "DISCONNECTED" # CONNECTED, DISCONNECTED, RECONNECTING
        self.attempt = 0

        # Snapshot mechanism
        self._snapshots = {}

    def _clean_numeric(self, value, default, min_val=None, max_val=None):
        try:
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return default
            val = float(value)
            if min_val is not None and val < min_val:
                val = min_val
            if max_val is not None and val > max_val:
                val = max_val
            return val
        except (TypeError, ValueError):
            return default

    def _create_snapshot(self):
        snapshot_id = str(time.time()) + str(random.random())
        state_copy = {
            "state": self.state,
            "attempt": self.attempt,
            "timestamp": time.time()
        }
        self._snapshots[snapshot_id] = state_copy
        return snapshot_id

    def connect(self):
        snapshot_id = self._create_snapshot()
        self.state = "CONNECTED"
        self.attempt = 0
        return snapshot_id

    def disconnect(self):
        snapshot_id = self._create_snapshot()
        self.state = "DISCONNECTED"
        return snapshot_id

    def mark_failure(self):
        snapshot_id = self._create_snapshot()
        self.state = "RECONNECTING"
        self.attempt += 1
        return snapshot_id

    def calculate_next_delay(self):
        if self.state == "CONNECTED":
            return 0.0

        try:
            safe_attempt = min(self.attempt, 1000)
            exponential_delay = self.base_delay * (2 ** safe_attempt)
        except OverflowError:
            exponential_delay = float('inf')

        delay = min(exponential_delay, self.max_delay)

        if self.jitter_ratio > 0:
            jitter_amount = delay * self.jitter_ratio
            delay = delay - random.uniform(0, jitter_amount)

        return delay

    def undo(self, snapshot_id):
        if snapshot_id not in self._snapshots:
            return False

        snapshot = self._snapshots[snapshot_id]
        if time.time() - snapshot["timestamp"] > 5.0:
            return False

        self.state = snapshot["state"]
        self.attempt = snapshot["attempt"]

        # Clean up used and old snapshots
        current_time = time.time()
        self._snapshots = {k: v for k, v in self._snapshots.items() if current_time - v["timestamp"] <= 5.0}

        return True
