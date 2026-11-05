import time
import copy

class AdaptiveStreamThrottlerSelfHealingGuard:
    def __init__(self, undo_window: float = 5.0):
        self.undo_window = undo_window
        self.current_seq = 0
        self.current_data = {}
        self.snapshots = []
        self.last_push_time = 0.0

    def _calculate_throttle_ms(self, data_length: int) -> float:
        """Dynamic throttle window: 150ms ~ 500ms based on length"""
        base_ms = 150.0
        max_ms = 500.0
        # Scale length up to 500 chars to reach max throttle
        ratio = min(data_length / 500.0, 1.0)
        return base_ms + ratio * (max_ms - base_ms)

    def _heal_data(self, data):
        """Silently cleans dirty data into a valid dict"""
        if data is None:
            return {}
        if isinstance(data, str):
            return {"content": data}
        if isinstance(data, dict):
            return copy.deepcopy(data)
        return {"value": data}

    def _heal_seq(self, seq):
        """Monotonically increasing sequence lock with silent self-healing"""
        if not isinstance(seq, int) or seq <= self.current_seq:
            self.current_seq += 1
        else:
            self.current_seq = seq
        return self.current_seq

    def push(self, seq=None, data=None):
        data = self._heal_data(data)
        seq = self._heal_seq(seq)

        data_str_len = len(str(data))
        throttle_ms = self._calculate_throttle_ms(data_str_len)
        throttle_s = throttle_ms / 1000.0

        now = time.time()
        elapsed = now - self.last_push_time
        sleep_time = 0.0

        # Only sleep if we have pushed before and the elapsed time is less than throttle window
        if self.last_push_time > 0 and elapsed < throttle_s:
            sleep_time = throttle_s - elapsed
            time.sleep(sleep_time)
            now = time.time()

        self.last_push_time = now

        # Maintain snapshot queue
        self._cleanup_snapshots(now)
        self.snapshots.append((now, copy.deepcopy(self.current_data)))

        self.current_data = data
        return {
            "seq": self.current_seq,
            "data": self.current_data,
            "sleep_time": sleep_time
        }

    def _cleanup_snapshots(self, now: float):
        """Removes snapshots older than the undo_window (5 seconds)"""
        self.snapshots = [s for s in self.snapshots if now - s[0] <= self.undo_window]

    def undo(self):
        """One-tap 5-second undo snapshot mechanism"""
        now = time.time()
        self._cleanup_snapshots(now)

        if not self.snapshots:
            # Self-heal when no undo is possible: simply increment sequence and retain state
            self.current_seq += 1
            return {
                "status": "failed",
                "reason": "snapshot_expired_or_empty",
                "seq": self.current_seq,
                "data": self.current_data
            }

        # Pop the latest valid snapshot
        _, previous_data = self.snapshots.pop()

        # Sequence strictly monotonic
        self.current_seq += 1
        self.current_data = previous_data
        self.last_push_time = time.time()

        return {
            "status": "success",
            "seq": self.current_seq,
            "data": self.current_data
        }

    def get_current_state(self):
        return {
            "seq": self.current_seq,
            "data": self.current_data
        }
