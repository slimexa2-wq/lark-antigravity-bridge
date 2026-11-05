import collections
import json
import csv
import sys
import io

class EventLRUIdempotencyGuard:
    """
    LRU Idempotency Guard to prevent Feishu Webhook events from being processed twice.
    Strictly robust, boundary fallback, silent dirty data cleaning.
    """
    def __init__(self, capacity: int = 1000):
        if not isinstance(capacity, int) or capacity <= 0:
            capacity = 1000
        self.capacity = capacity
        self.cache = collections.OrderedDict()

    def check_and_add(self, event_data: dict) -> bool:
        """
        Check if event is already processed. If not, add it to the LRU cache.
        Returns True if the event is NEW and should be processed.
        Returns False if the event is a DUPLICATE or invalid.
        """
        # Silent dirty data cleaning & boundary fallback
        if not isinstance(event_data, dict):
            return False

        # Extract event_id or message_id with fallback
        event_id = event_data.get('event_id') or event_data.get('message_id')

        # If it's nested under 'event' block (common in Feishu v2)
        if not event_id and isinstance(event_data.get('event'), dict):
            event_id = event_data['event'].get('event_id') or event_data['event'].get('message_id')

        # Ensure event_id is a valid string
        if not event_id or not isinstance(event_id, str) or not event_id.strip():
            return False

        event_id = event_id.strip()

        # Idempotency check
        if event_id in self.cache:
            # Mark as recently used
            self.cache.move_to_end(event_id)
            return False

        # Add to cache
        self.cache[event_id] = True

        # Maintain capacity
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

        return True


def run_cli(events=None, output_format="json"):
    """
    Zero-parameter one-click CLI entry point.
    Defaults to processing a sample list of events.
    """
    if not isinstance(events, list):
        events = [
            {"event_id": "evt_001", "data": "msg1"},
            {"event_id": "evt_001", "data": "duplicate"},
            {"message_id": "msg_002", "data": "msg2"},
            "dirty_string_data",
            {"event": {"event_id": "evt_003"}},
            {"event": {"message_id": "evt_003"}}, # duplicate logically if id is same
            {} # empty
        ]

    if not isinstance(output_format, str) or output_format.lower() not in ["json", "excel"]:
        output_format = "json"

    guard = EventLRUIdempotencyGuard(capacity=1000)

    results = []
    for evt in events:
        is_new = guard.check_and_add(evt)
        # We record the status for export
        evt_str = str(evt) if not isinstance(evt, dict) else json.dumps(evt, ensure_ascii=False)
        results.append({
            "event_raw": evt_str,
            "is_new": is_new,
            "status": "PROCESSED" if is_new else "DUPLICATE_OR_INVALID"
        })

    if output_format.lower() == "json":
        return json.dumps(results, indent=2, ensure_ascii=False)
    else:
        # Excel mode (CSV actually, for simplicity and no external dependencies)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["event_raw", "is_new", "status"])
        for r in results:
            writer.writerow([r["event_raw"], r["is_new"], r["status"]])
        return output.getvalue()


if __name__ == "__main__": # pragma: no cover
    # Extremely simple one-click invocation
    args = sys.argv[1:]
    fmt = args[0] if len(args) > 0 else "json"
    print(run_cli(output_format=fmt))
