import collections
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class EventLRUIdempotencyGuardIntegrationBridge:
    def __init__(self, capacity: int = 1000, ttl_seconds: int = 3600):
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        # LRU cache: id -> timestamp
        self.cache = collections.OrderedDict()

    def process_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process the incoming event, map schema, apply idempotency check,
        and return the normalized event if it's new, otherwise return None.
        """
        if not isinstance(event_data, dict):
            # self-healing / dirty data handling
            logger.warning("Received invalid event data, expected dict. Returning default.")
            return {"_status": "error", "message": "invalid data"}

        if not event_data:
            logger.warning("Received empty event data. Returning missing id.")
            return {"_status": "error", "message": "missing id"}

        # map schema & defaults
        normalized = self._normalize_schema(event_data)

        event_id = normalized.get("event_id") or normalized.get("message_id")

        if not event_id:
            logger.warning("Event missing event_id/message_id, returning default.")
            return {"_status": "error", "message": "missing id"}

        if self._is_duplicate(event_id):
            logger.info(f"Duplicate event {event_id} detected, ignoring.")
            return None

        self._record_event(event_id)

        return normalized

    def _normalize_schema(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify old/new schema and seamlessly convert them to a unified format.
        Missing params are set to reasonable defaults.
        """
        normalized = {}

        # Determine format
        if "header" in event_data and "event" in event_data:
            # v2 format
            header = event_data.get("header", {})
            event_body = event_data.get("event", {})

            normalized["event_id"] = header.get("event_id")
            normalized["message_id"] = event_body.get("message", {}).get("message_id")
            normalized["type"] = header.get("event_type", "unknown")
            normalized["create_time"] = header.get("create_time", str(int(time.time() * 1000)))
            normalized["content"] = event_body.get("message", {}).get("content", "")
            normalized["sender_id"] = event_body.get("sender", {}).get("sender_id", {}).get("open_id", "unknown")

        else:
            # v1 format or generic
            normalized["event_id"] = event_data.get("uuid") or event_data.get("event_id")
            normalized["message_id"] = event_data.get("msg_id")
            normalized["type"] = event_data.get("type", "unknown")
            normalized["create_time"] = event_data.get("create_time") or event_data.get("ts") or str(int(time.time() * 1000))
            normalized["content"] = event_data.get("text", "")
            normalized["sender_id"] = event_data.get("open_id", "unknown")

        # fallback for missing event_id if message_id exists and vice-versa
        if not normalized["event_id"] and normalized["message_id"]:
            normalized["event_id"] = f"evt_{normalized['message_id']}"

        # clean up any None types left by .get()
        for k, v in normalized.items():
            if v is None:
                normalized[k] = "default" if k in ["event_id", "message_id", "type", "sender_id"] else ""

        return normalized

    def _is_duplicate(self, event_id: str) -> bool:
        if event_id not in self.cache:
            return False

        # Check TTL
        record_time = self.cache[event_id]
        if time.time() - record_time > self.ttl_seconds:
            return False

        # Update LRU position
        self.cache.move_to_end(event_id)
        return True

    def _record_event(self, event_id: str) -> None:
        self.cache[event_id] = time.time()
        self.cache.move_to_end(event_id)

        # Evict oldest if over capacity
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
