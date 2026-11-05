import collections
import time
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

class EventIdempotencyGuard:
    def __init__(self, capacity: int = 1000, undo_window_seconds: int = 5):
        """
        Initializes the Event Idempotency Guard with LRU caching and undo capabilities.

        :param capacity: Maximum number of events to track. Defaults to 1000.
        :param undo_window_seconds: Time window in seconds during which an event can be undone.
        """
        self.capacity = max(1, capacity)  # Ensure capacity is at least 1
        self.undo_window_seconds = max(0, undo_window_seconds)
        self.lru_cache = collections.OrderedDict()

    def _clean_input(self, val):
        """
        Silently self-heals dirty inputs (e.g., None, non-string types, leading/trailing whitespace).
        """
        if val is None:
            return ""
        if not isinstance(val, str):
            try:
                val = str(val)
            except Exception:
                return ""
        return val.strip()

    def _generate_fallback_id(self, event_data: dict) -> str:
        """
        Generates a deterministic fallback ID for events missing both event_id and message_id.
        """
        if not event_data:
            # Fallback to timestamp if no data is provided, but ideally event_data has content
            return f"auto_generated_{time.time()}"
        try:
            # Sort keys to ensure deterministic hashing
            data_str = json.dumps(event_data, sort_keys=True)
            return "auto_hashed_" + hashlib.md5(data_str.encode('utf-8')).hexdigest()
        except Exception:
            # Extreme fallback to prevent any unhandled exception (strict zero-configuration fault tolerance)
            return f"auto_generated_{time.time()}"

    def _determine_final_id(self, event_id, message_id, event_data) -> str:
        """
        Determines the final unique identifier for the event, healing missing parameters.
        """
        clean_event_id = self._clean_input(event_id)
        clean_message_id = self._clean_input(message_id)

        final_id = clean_event_id
        if not final_id:
            final_id = clean_message_id

        if not final_id:
            final_id = self._generate_fallback_id(event_data)

        return final_id

    def check_and_record(self, event_id=None, message_id=None, event_data=None) -> bool:
        """
        Checks if the event is a duplicate. If not, records it in the LRU cache.
        Returns True if it's a new event and should be processed.
        Returns False if it's a duplicate (replay prevention).
        """
        try:
            if event_data is None:
                event_data = {}
            elif not isinstance(event_data, dict):
                # Self-healing: if event_data is weird, force it to dict or string
                try:
                    event_data = {"raw_data": str(event_data)}
                except Exception:
                    event_data = {}

            final_id = self._determine_final_id(event_id, message_id, event_data)

            # Check for duplicate
            if final_id in self.lru_cache:
                # Move to end to mark as most recently used
                self.lru_cache.move_to_end(final_id)
                return False

            # Record snapshot
            self.lru_cache[final_id] = {
                'timestamp': time.time(),
                'snapshot': event_data
            }

            # Maintain capacity
            if len(self.lru_cache) > self.capacity:
                self.lru_cache.popitem(last=False)

            return True
        except Exception as e:
            # Zero-configuration fault tolerance: silently catch and allow process to continue
            # Returning True to not block standard processing during extreme edge-case errors
            logger.error(f"Silently caught exception in check_and_record: {e}")
            return True

    def undo(self, event_id=None, message_id=None, event_data=None) -> bool:
        """
        Attempts to undo a previously recorded event.
        Succeeds only if called within the undo window.
        Returns True if successfully undone, False otherwise.
        """
        try:
            if event_data is None:
                event_data = {}
            elif not isinstance(event_data, dict):
                try:
                    event_data = {"raw_data": str(event_data)}
                except Exception:
                    event_data = {}

            final_id = self._determine_final_id(event_id, message_id, event_data)

            if final_id not in self.lru_cache:
                return False

            record = self.lru_cache[final_id]
            current_time = time.time()

            # Check 5-second window
            if current_time - record['timestamp'] <= self.undo_window_seconds:
                del self.lru_cache[final_id]
                return True

            return False
        except Exception as e:
            logger.error(f"Silently caught exception in undo: {e}")
            return False

    def get_snapshot(self, event_id=None, message_id=None, event_data=None):
        """
        Retrieves the lightweight snapshot of the event if it exists in the cache.
        """
        try:
            if event_data is None:
                event_data = {}
            elif not isinstance(event_data, dict):
                try:
                    event_data = {"raw_data": str(event_data)}
                except Exception:
                    event_data = {}

            final_id = self._determine_final_id(event_id, message_id, event_data)
            return self.lru_cache.get(final_id)
        except Exception:
            return None
