import time
import json
import csv
import io
import threading
import sys
from typing import Optional, List, Dict, Any

class DualModeAdapter:
    @staticmethod
    def format_output(data: Any, mode: str = "json") -> str:
        # Fallback to json if mode is invalid or missing
        if mode not in ("json", "excel"):
            mode = "json"

        # Dirty data self-healing: ensure data is a list of dicts
        if not isinstance(data, list):
            data = [data] if data else []

        healed_data = []
        for item in data:
            if isinstance(item, dict):
                healed_data.append(item)
            else:
                healed_data.append({"payload": str(item)})

        if mode == "json":
            return json.dumps(healed_data, ensure_ascii=False)
        elif mode == "excel":
            if not healed_data:
                return ""
            output = io.StringIO()
            # Extract all unique keys
            keys = []
            for item in healed_data:
                for k in item.keys():
                    if k not in keys:
                        keys.append(k)
            if not keys:
                return ""
            writer = csv.DictWriter(output, fieldnames=keys)
            writer.writeheader()
            for item in healed_data:
                writer.writerow(item)
            return output.getvalue()
        return ""

class AdaptiveStreamThrottler:
    def __init__(self, min_window_ms: int = 150, max_window_ms: int = 500):
        self.min_window = min_window_ms / 1000.0
        self.max_window = max_window_ms / 1000.0

        self.lock = threading.Lock()
        self.sequence = 0
        self.buffer = []
        self.flush_history = []

        self.last_flush_time = time.time()
        self.flush_timer = None

    def _next_sequence(self):
        self.sequence += 1
        return self.sequence

    def push(self, data: Any):
        with self.lock:
            seq = self._next_sequence()
            item = {
                "sequence": seq,
                "data": data,
                "timestamp": time.time()
            }
            self.buffer.append(item)

            now = time.time()
            time_since_last_flush = now - self.last_flush_time

            if time_since_last_flush >= self.max_window:
                self._flush_locked()
            elif len(self.buffer) == 1:
                # First item in window, schedule a flush at max_window
                self._schedule_flush(self.max_window - time_since_last_flush)
            else:
                # More items coming, maybe dynamically flush earlier if buffer is getting big
                # We use min_window to debounce
                self._schedule_flush(self.min_window)

    def _schedule_flush(self, delay: float):
        if self.flush_timer:
            self.flush_timer.cancel()
        self.flush_timer = threading.Timer(delay, self._flush_timer_cb)
        self.flush_timer.start()

    def _flush_timer_cb(self):
        with self.lock:
            self._flush_locked()

    def _flush_locked(self):
        if self.flush_timer:
            self.flush_timer.cancel()
            self.flush_timer = None

        if not self.buffer:
            self.last_flush_time = time.time()
            return

        to_flush = self.buffer
        self.buffer = []
        self.last_flush_time = time.time()
        self._on_flush(to_flush)

    def _on_flush(self, items: List[Dict[str, Any]]):
        self.flush_history.append(items)

    def get_flushed_batches(self):
        with self.lock:
            return list(self.flush_history)

    def force_flush(self):
        with self.lock:
            self._flush_locked()

    def stop(self):
        with self.lock:
            if self.flush_timer:
                self.flush_timer.cancel()
                self.flush_timer = None

def run_one_click_cli(mode: str = "json", data_to_push: Optional[List[Any]] = None) -> str:
    # Zero parameter defaults
    if data_to_push is None:
        data_to_push = [{"msg": "hello"}, {"msg": "world"}]

    throttler = AdaptiveStreamThrottler()
    for item in data_to_push:
        throttler.push(item)

    # Wait for dynamic window
    time.sleep(0.6)
    throttler.force_flush()
    throttler.stop()

    batches = throttler.get_flushed_batches()
    flat_items = []
    for b in batches:
        flat_items.extend(b)

    return DualModeAdapter.format_output(flat_items, mode)

if __name__ == "__main__":
    mode_arg = "json"
    if len(sys.argv) > 1:
        mode_arg = sys.argv[1]

    print(run_one_click_cli(mode=mode_arg))
