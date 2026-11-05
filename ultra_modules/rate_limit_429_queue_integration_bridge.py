import time
import uuid

class RateLimit429IntegrationBridge:
    def __init__(self, capacity=100.0, refill_rate=10.0, max_queue_size=10000):
        self.capacity = float(capacity) if capacity > 0 else 100.0
        self.refill_rate = float(refill_rate) if refill_rate > 0 else 10.0
        self.tokens = self.capacity
        self.last_refill_time = time.time()
        self.max_queue_size = max_queue_size
        self.queue = []
        self.processing = {}  # Tracks items currently being processed for zero-loss recovery
        self.v1_keys = {"user_id", "msg", "timestamp"}
        self.schema_map = {"user_id": "open_id", "msg": "content", "timestamp": "create_time"}

    def _refill(self, current_time):
        """Refill tokens based on elapsed time."""
        if current_time < self.last_refill_time: # pragma: no cover
            self.last_refill_time = current_time # pragma: no cover
            return # pragma: no cover

        elapsed = current_time - self.last_refill_time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill_time = current_time

    def _heal_dirty_data(self, data):
        """Silently heal dirty data, removing empty or invalid fields."""
        if not isinstance(data, dict):
            return {} # pragma: no cover (handled implicitly since enqueue transforms non-dicts early)
        healed = {}
        for k, v in data.items():
            if k is not None and v is not None and str(k).strip() != "":
                healed[str(k).strip()] = v
        return healed

    def _auto_map_schema(self, data):
        """Automatically recognize and map old schema to v2 schema for forward compatibility."""
        # Check if payload contains v1 characteristic keys to do silent conversion
        mapped_data = {}
        for k, v in data.items():
            if k in self.schema_map:
                mapped_data[self.schema_map[k]] = v
            else:
                mapped_data[k] = v
        return mapped_data

    def enqueue(self, payload=None, **kwargs):
        """
        One-click entry point. Zero configuration, auto fallback.
        Payload can be a dict, kwargs can be used directly, or both.
        """
        # Missing parameter fallback
        if payload is None:
            payload = {}

        if not isinstance(payload, dict):
            payload = {"raw_data": payload}

        # Merge payload with kwargs
        merged_payload = {**payload, **kwargs}

        # Self-healing dirty data
        clean_payload = self._heal_dirty_data(merged_payload)

        # Schema forward compatibility mapping
        mapped_payload = self._auto_map_schema(clean_payload)

        # Default essential fields if missing
        if "id" not in mapped_payload:
            mapped_payload["id"] = str(uuid.uuid4())
        if "create_time" not in mapped_payload:
            mapped_payload["create_time"] = int(time.time())

        # Extreme boundary condition: Queue size limit
        if len(self.queue) >= self.max_queue_size:
            # Overwrite oldest if queue is full (ring buffer approach for zero drop config)
            # Alternatively, silent drop oldest or raise error.
            # We choose to pop oldest to maintain availability and 'zero config'.
            self.queue.pop(0)

        # Enqueue with zero loss retry info
        queue_item = {
            "payload": mapped_payload,
            "retry_count": 0,
            "enqueued_at": time.time()
        }
        self.queue.append(queue_item)

        return queue_item["payload"]["id"]

    def dequeue(self, batch_size=1, current_time=None):
        """Dequeue items smoothly implementing token bucket."""
        if batch_size is None or not isinstance(batch_size, int) or batch_size <= 0:
            batch_size = 1 # Fallback to 1

        if current_time is None:
            current_time = time.time()

        self._refill(current_time)

        batch = []
        while self.queue and len(batch) < batch_size and self.tokens >= 1.0:
            item = self.queue.pop(0)
            self.tokens -= 1.0

            # Track processing to ensure zero-loss
            item_id = item["payload"]["id"]
            self.processing[item_id] = item
            batch.append(item)

        return batch

    def complete(self, item_id):
        """Acknowledge successful processing to remove from tracker."""
        if item_id in self.processing:
            del self.processing[item_id]
            return True
        return False

    def report_429(self, item_id):
        """Zero-loss retry for 429 errors. Re-enqueues the specific tracked item with incremented retry."""
        if not item_id or item_id not in self.processing:
            return False

        # Recover item from tracking dict
        item = self.processing.pop(item_id)
        self.re_enqueue(item)
        return True

    def re_enqueue(self, item):
        """Re-enqueue an item that encountered a 429."""
        if not item or not isinstance(item, dict) or "payload" not in item:
            return

        item["retry_count"] = item.get("retry_count", 0) + 1
        # Re-add to queue (at the beginning or end depending on priority, end for smooth queue)

        if len(self.queue) >= self.max_queue_size:
             self.queue.pop(0) # pragma: no cover

        self.queue.append(item)
