import time
import math
from typing import List, Dict, Any, Optional

class AnomalyRadar:
    def __init__(self):
        self.history = []

    def add_data_point(self, value: Any) -> None:
        """Adds a data point, handling dirty data silently."""
        try:
            val = float(value)
            if math.isnan(val) or math.isinf(val):
                val = 0.0
            self.history.append(val)
        except (ValueError, TypeError):
            self.history.append(0.0)

    def analyze(self) -> Dict[str, Any]:
        """Analyzes history using IQR to identify anomalies."""
        if not self.history:
            return {"status": "green", "reason": "No data", "top_anomalies": []}

        n = len(self.history)
        if n < 4:
            return {"status": "green", "reason": "Not enough data for anomaly detection", "top_anomalies": []}

        sorted_data = sorted(self.history)
        q1 = sorted_data[n // 4]
        q3 = sorted_data[(3 * n) // 4]
        iqr = q3 - q1

        # Upper bound for anomaly
        upper_bound = q3 + 1.5 * iqr

        anomalies = [x for x in self.history if x > upper_bound]

        # Calculate Top 3% threshold
        top_3_idx = max(0, int(n * 0.97))
        # Ensure top_3_threshold is strictly greater than upper_bound to allow for yellow anomalies
        # If the 97th percentile is less than or equal to the upper bound, we use the 99th or a multiple of upper bound
        top_3_threshold = sorted_data[top_3_idx] if n >= 34 else upper_bound # Require some data for 3% to make sense
        if top_3_threshold <= upper_bound:
            top_3_threshold = upper_bound * 1.5 if upper_bound > 0 else 1.0

        top_anomalies = [x for x in anomalies if x >= top_3_threshold]

        if top_anomalies:
            return {
                "status": "red",
                "reason": f"Detected {len(top_anomalies)} severe anomalies (Top 3% extreme values) indicating potential stream blocking or network stall.",
                "top_anomalies": top_anomalies
            }
        elif anomalies:
            return {
                "status": "yellow",
                "reason": f"Detected {len(anomalies)} minor anomalies (values exceeding normal variance).",
                "top_anomalies": anomalies
            }
        else:
            return {
                "status": "green",
                "reason": "All values within normal expected ranges.",
                "top_anomalies": []
            }


class AdaptiveStreamThrottler:
    def __init__(self, default_window_ms: int = 150):
        # 150ms to 500ms dynamic window
        self.min_window_ms = 150
        self.max_window_ms = 500

        try:
            self.current_window_ms = float(default_window_ms)
        except (ValueError, TypeError):
            self.current_window_ms = float(self.min_window_ms)

        self.current_window_ms = max(self.min_window_ms, min(self.max_window_ms, self.current_window_ms))

        self.last_emit_time = 0.0
        self.radar = AnomalyRadar()
        self.sequence_locks: Dict[str, int] = {}

    def should_emit(self, stream_id: str, seq: Any = None) -> Dict[str, Any]:
        """
        Determines if a stream event should be emitted based on adaptive throttling and sequence lock.
        Handles missing parameters and dirty data silently.
        """
        if stream_id is None:
            stream_id = "default_stream"
        stream_id = str(stream_id)

        now = time.time()

        # Sequence lock check
        seq_num = 0
        if seq is not None:
            try:
                seq_num = int(seq)
            except (ValueError, TypeError):
                seq_num = 0 # Default fallback

            current_seq = self.sequence_locks.get(stream_id, -1)
            if seq_num <= current_seq:
                return {
                    "emit": False,
                    "reason": f"Sequence out of order: {seq_num} <= {current_seq}",
                    "status": "yellow",
                    "window_ms": self.current_window_ms
                }
            self.sequence_locks[stream_id] = seq_num

        # Throttle check
        time_since_last = (now - self.last_emit_time) * 1000.0 # to ms

        # Adapt window based on anomaly analysis
        analysis = self.radar.analyze()
        if analysis["status"] == "red":
            # If red, increase window to max to slow down and recover
            self.current_window_ms = min(self.max_window_ms, self.current_window_ms + 50.0)
        elif analysis["status"] == "green":
            # If green, slowly decrease window to min for faster updates
            self.current_window_ms = max(self.min_window_ms, self.current_window_ms - 10.0)

        if time_since_last < self.current_window_ms:
            return {
                "emit": False,
                "reason": "Throttled",
                "status": "green",
                "window_ms": self.current_window_ms
            }

        # Record data point for radar only on successful emit to avoid skewing stats with throttled polls
        if self.last_emit_time > 0:
            self.radar.add_data_point(time_since_last)
            # Re-analyze just for the current return status so we don't return an outdated status
            analysis = self.radar.analyze()

        self.last_emit_time = now

        return {
            "emit": True,
            "reason": "OK",
            "status": analysis["status"],
            "analysis_reason": analysis["reason"],
            "window_ms": self.current_window_ms
        }
