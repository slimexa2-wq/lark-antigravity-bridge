import threading
from collections import OrderedDict
import logging

class EventLRUIdempotencyGuardCoreEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, capacity=1000):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventLRUIdempotencyGuardCoreEngine, cls).__new__(cls)
                cls._instance._init_engine(capacity)
            return cls._instance

    def _init_engine(self, capacity):
        # 脏数据静默清洗/自动兜底
        if not isinstance(capacity, int) or capacity <= 0:
            logging.warning(f"Invalid capacity {capacity}, fallback to default 1000.")
            self.capacity = 1000
        else:
            self.capacity = capacity

        self.cache = OrderedDict()
        self._cache_lock = threading.Lock()

    def _extract_id(self, event_data):
        """
        Extrapolate event_id or message_id from the given payload safely.
        Handle various nesting cases implicitly.
        """
        if not isinstance(event_data, dict):
            return None

        # Check common Feishu fields for ID
        potential_ids = []

        # 1. Top level event_id or message_id
        if 'event_id' in event_data:
            potential_ids.append(event_data['event_id'])
        if 'message_id' in event_data:
            potential_ids.append(event_data['message_id'])

        # 2. Nested under header or event
        if 'header' in event_data and isinstance(event_data['header'], dict):
            if 'event_id' in event_data['header']:
                potential_ids.append(event_data['header']['event_id'])

        if 'event' in event_data and isinstance(event_data['event'], dict):
            if 'message_id' in event_data['event']:
                potential_ids.append(event_data['event']['message_id'])

        # Clean up the IDs and return the first valid one
        for pid in potential_ids:
            try:
                # Stringify and strip whitespace
                clean_id = str(pid).strip()
                if clean_id:
                    return clean_id
            except Exception:
                continue

        return None

    def check_and_record(self, event_data):
        """
        Check if the event is a duplicate.
        Returns False if the event is a duplicate (should be dropped).
        Returns True if the event is new (should be processed) or if there's no ID (fail-open).
        """
        extracted_id = self._extract_id(event_data)

        # 缺参自动设合理默认值: 默认放行 (fail-open)
        if not extracted_id:
            return True

        with self._cache_lock:
            if extracted_id in self.cache:
                # Refresh position in LRU
                self.cache.move_to_end(extracted_id)
                return False  # Duplicate found
            else:
                self.cache[extracted_id] = True
                if len(self.cache) > self.capacity:
                    # Pop the oldest item (FIFO)
                    self.cache.popitem(last=False)
                return True

    def reset_for_testing(self):
        """Only meant to be used for unit testing to clean up the singleton state."""
        with self._lock:
            with self._cache_lock:
                self.cache.clear()
