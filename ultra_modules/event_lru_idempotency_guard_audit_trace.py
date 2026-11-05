import collections
import time
import logging
import json
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

class AuditLogger:
    """Silently tracks all operations for tracing and auditing."""

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def log(self, action: str, details: Dict[str, Any]) -> None:
        """Records an audit trace entry."""
        entry = {
            "timestamp": time.time(),
            "action": action,
            "details": details
        }
        self.logs.append(entry)
        logger.debug(f"Audit Trace [{action}]: {json.dumps(details)}")

    def get_logs(self) -> List[Dict[str, Any]]:
        """Retrieves the full audit log."""
        return self.logs

    def clear(self) -> None:
        """Clears the audit log."""
        self.logs.clear()


class DifferenceComparator:
    """Compares dictionaries to find structural differences."""

    @staticmethod
    def compare(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Returns fields that differ between old_data and new_data."""
        if not isinstance(old_data, dict) or not isinstance(new_data, dict):
            return {"old": old_data, "new": new_data} if old_data != new_data else {}

        differences = {}
        all_keys = set(old_data.keys()).union(set(new_data.keys()))

        for key in all_keys:
            if key not in old_data:
                differences[key] = {"type": "added", "value": new_data[key]}
            elif key not in new_data:
                differences[key] = {"type": "removed", "value": old_data[key]}
            elif old_data[key] != new_data[key]:
                if isinstance(old_data[key], dict) and isinstance(new_data[key], dict):
                    nested_diff = DifferenceComparator.compare(old_data[key], new_data[key])
                    differences[key] = {"type": "modified", "diff": nested_diff}
                else:
                    differences[key] = {"type": "modified", "old": old_data[key], "new": new_data[key]}

        return differences

class EventIdempotencyGuard:
    """LRU Idempotency Guard for Feishu webhook events."""

    def __init__(self, capacity: int = 1000):
        # Fallback to sensible defaults
        if not isinstance(capacity, int) or capacity <= 0:
            capacity = 1000

        self.capacity = capacity
        self.cache: collections.OrderedDict = collections.OrderedDict()
        self.audit_logger = AuditLogger()

    def _extract_id(self, event_data: Any) -> Optional[str]:
        """Extract event_id or message_id silently healing dirty data."""
        if not isinstance(event_data, dict):
            self.audit_logger.log("extract_id_failed", {"reason": "Not a dictionary", "type": type(event_data).__name__})
            return None

        # Prioritize event_id, then message_id, also check under 'header' and 'event'
        possible_ids = [
            event_data.get("event_id"),
            event_data.get("message_id"),
            event_data.get("header", {}).get("event_id") if isinstance(event_data.get("header"), dict) else None,
            event_data.get("event", {}).get("message", {}).get("message_id") if isinstance(event_data.get("event"), dict) and isinstance(event_data.get("event").get("message"), dict) else None
        ]

        for candidate in possible_ids:
            if candidate and isinstance(candidate, str):
                return candidate

        self.audit_logger.log("extract_id_failed", {"reason": "No valid ID found in payload"})
        return None

    def check(self, event_data: Any) -> bool:
        """
        Checks if the event is a duplicate.
        Returns True if it's a new event (or uncacheable), False if it's a duplicate.
        """
        if event_data is None:
            self.audit_logger.log("check_skipped", {"reason": "Null event_data"})
            return True # Let null data pass through, typically handled by downstream validation

        event_id = self._extract_id(event_data)

        if not event_id:
            self.audit_logger.log("check_skipped", {"reason": "No extractable ID"})
            return True # Can't deduplicate without an ID, let it pass

        if event_id in self.cache:
            # It's a duplicate
            old_data = self.cache[event_id]
            diff = DifferenceComparator.compare(old_data, event_data if isinstance(event_data, dict) else {})

            self.audit_logger.log("duplicate_detected", {
                "event_id": event_id,
                "diff": diff
            })

            # Move to end to mark as recently used
            self.cache.move_to_end(event_id)
            return False

        # It's new
        self.cache[event_id] = event_data if isinstance(event_data, dict) else {}
        self.audit_logger.log("event_cached", {"event_id": event_id})

        # Evict if over capacity
        if len(self.cache) > self.capacity:
            evicted_key, _ = self.cache.popitem(last=False)
            self.audit_logger.log("cache_eviction", {"evicted_id": evicted_key})

        return True

    def get_audit_logs(self) -> List[Dict[str, Any]]:
        return self.audit_logger.get_logs()


# Global single instance for zero-configuration use
_DEFAULT_GUARD = EventIdempotencyGuard()

def check_event(event_data: Any) -> bool:
    """
    Extremely simple frontend/calling method.
    One-click access, zero-configuration fault tolerance.
    Returns True if the event should be processed (new or uncacheable).
    Returns False if it is a duplicate and should be ignored.
    """
    try:
        return _DEFAULT_GUARD.check(event_data)
    except Exception as e:
        # Fallback for catastrophic failure: let the event pass so we don't break the webhook
        logger.error(f"Catastrophic failure in idempotency guard: {e}")
        return True
