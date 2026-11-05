import time
import logging
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuditLogEntry:
    def __init__(self, sequence: int, timestamp: float, action: str, details: Dict[str, Any]):
        self.sequence = sequence
        self.timestamp = timestamp
        self.action = action
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "action": self.action,
            "details": self.details
        }

class DiffHighlighter:
    @staticmethod
    def compare(old_data: Any, new_data: Any) -> str:
        # Extreme simple string diff highlighting just for audit log readability
        if old_data == new_data:
            return "NO_CHANGE"
        return f"CHANGE: {old_data} -> {new_data}"

class AdaptiveStreamThrottler:
    """
    Adaptive stream throttler with 150ms~500ms dynamic window and monotonic sequence lock.
    """
    def __init__(self, min_window_ms: int = 150, max_window_ms: int = 500, burst_threshold: int = 5):
        self.min_window = min_window_ms / 1000.0
        self.max_window = max_window_ms / 1000.0
        self.burst_threshold = burst_threshold

        self.current_window = self.min_window
        self.last_flush_time = time.time()
        self.message_buffer: List[Any] = []

        # Sequence lock state
        self._sequence_counter = 0

        # Audit trace state
        self.audit_trail: List[AuditLogEntry] = []

    def _next_sequence(self) -> int:
        self._sequence_counter += 1
        return self._sequence_counter

    def _record_audit(self, action: str, details: Dict[str, Any]) -> None:
        seq = self._next_sequence()
        entry = AuditLogEntry(seq, time.time(), action, details)
        self.audit_trail.append(entry)
        logger.debug(f"[AUDIT] {action}: {details}")

    def push(self, data: Any = None) -> Optional[Dict[str, Any]]:
        """
        Pushes data to the throttler. Returns the flushed batch if the window is reached.
        """
        # Default fallback for missing parameter
        if data is None:
            self._record_audit("DEFAULT_FALLBACK", {"reason": "missing data parameter", "default": ""})
            data = ""

        # Dirty data self-healing: ensure strings
        original_data = data
        if not isinstance(data, str):
            try:
                data = str(data)
                self._record_audit("DIRTY_DATA_HEALED", {"original_type": type(original_data).__name__, "new_val": data})
            except Exception as e:
                self._record_audit("DIRTY_DATA_HEAL_FAILED", {"error": str(e)})
                data = ""

        now = time.time()

        if self.message_buffer:
            diff = DiffHighlighter.compare(self.message_buffer[-1], data)
            if diff == "NO_CHANGE":
                self._record_audit("DEDUPLICATE", {"data": data})
                # Check for flush even on deduplicated items
                time_since_last_flush = now - self.last_flush_time
                if time_since_last_flush >= self.current_window:
                    return self.flush()
                return None # deduplicated

        self.message_buffer.append(data)
        self._record_audit("PUSH_BUFFER", {"data": data, "buffer_size": len(self.message_buffer)})

        # Adaptive window adjustment based on burst rate
        if len(self.message_buffer) >= self.burst_threshold:
            self.current_window = min(self.max_window, self.current_window * 1.5)
            self._record_audit("ADAPTIVE_WINDOW_INCREASE", {"new_window": self.current_window})
        else:
            self.current_window = max(self.min_window, self.current_window * 0.9)
            self._record_audit("ADAPTIVE_WINDOW_DECREASE", {"new_window": self.current_window})

        time_since_last_flush = now - self.last_flush_time
        if time_since_last_flush >= self.current_window:
            return self.flush()

        return None

    def flush(self) -> Optional[Dict[str, Any]]:
        """
        Forces a flush of the current buffer.
        """
        if not self.message_buffer:
            return None

        batch = self.message_buffer.copy()
        self.message_buffer.clear()
        self.last_flush_time = time.time()

        self._record_audit("FLUSH", {"batch_size": len(batch), "window": self.current_window})

        # Clean frontend result format
        return {
            "result": "".join(batch),
            "events_flushed": len(batch)
        }

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        return [entry.to_dict() for entry in self.audit_trail]
