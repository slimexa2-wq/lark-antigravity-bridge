import collections
import math
from typing import Any, Dict, Optional, Tuple, Union

class LRUIdempotencyGuard:
    """
    A thousands-level LRU (Least Recently Used) cache for idempotency checking.
    """
    def __init__(self, capacity: int = 1000):
        # Default capacity is 1000, fallback to 1000 if invalid capacity is provided
        if not isinstance(capacity, int) or capacity <= 0:
            capacity = 1000
        self.capacity = capacity
        self.cache: collections.OrderedDict = collections.OrderedDict()

    def check_and_add(self, event_id: str) -> bool:
        """
        Check if an event_id exists. If it exists, return False (duplicate).
        If not, add it to the cache and return True (first time seen).
        """
        if not event_id:
            # If no event_id, treat as new/pass-through, but don't cache
            return True

        if event_id in self.cache:
            # Move to end to mark as recently used
            self.cache.move_to_end(event_id)
            return False

        # Add new event_id
        self.cache[event_id] = True

        # Evict oldest if capacity exceeded
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

        return True


def clean_data(data: Any) -> Any:
    """
    Recursively clean dirty data. Ensure `comments=0` instead of removing it,
    replace NaN/None with 0 for numerical fields (or general fields),
    and traverse nested lists and dicts.
    """
    if data is None:
        return 0

    if isinstance(data, float) and math.isnan(data):
        return 0

    if isinstance(data, dict):
        cleaned_dict = {}
        for key, value in data.items():
            if key == "comments":
                cleaned_dict[key] = 0
            else:
                cleaned_dict[key] = clean_data(value)
        return cleaned_dict

    if isinstance(data, list):
        return [clean_data(item) for item in data]

    return data


# Global idempotency guard instance for easy one-click access
_global_guard = LRUIdempotencyGuard()

def process_and_export(
    event_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    guard: Optional[LRUIdempotencyGuard] = None
) -> Tuple[bool, Dict[str, Any], str]:
    """
    One-click process and export.
    Returns:
        is_new_event (bool): True if event is processed for the first time.
        cleaned_data (dict): Cleaned and formatted data.
        report (str): 3-line minimalist report text for WeChat/Lark.
    """
    if data is None:
        data = {}

    active_guard = guard if guard is not None else _global_guard
    is_new = active_guard.check_and_add(event_id) if event_id else True

    cleaned = clean_data(data)

    # Ensure it's a dict after cleaning (fallback just in case)
    if not isinstance(cleaned, dict):
        cleaned = {"data": cleaned}

    # 3-line report
    status_text = "New Event" if is_new else "Duplicate Event"
    report_lines = [
        f"Event ID: {event_id or 'N/A'} ({status_text})",
        f"Data Keys: {len(cleaned)} fields processed",
        "Export Status: Success, Cleaned"
    ]
    report = "\n".join(report_lines)

    return is_new, cleaned, report
