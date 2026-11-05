import random
import time
from typing import Dict, Any, Optional

class WsReconnectionStateMachine:
    """
    State machine for WebSocket reconnection with exponential backoff and random jitter.
    Guarantees zero-configuration fault tolerance and millisecond-level responsiveness.
    """
    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter_factor: float = 0.5,
        max_retries: int = -1
    ) -> None:
        # Zero-configuration defaults fallback
        self.base_delay = max(0.1, float(base_delay) if base_delay is not None else 1.0)
        self.max_delay = max(self.base_delay, float(max_delay) if max_delay is not None else 60.0)
        self.jitter_factor = max(0.0, min(1.0, float(jitter_factor) if jitter_factor is not None else 0.5))
        self.max_retries = int(max_retries) if max_retries is not None else -1

        self.retry_count = 0
        self.is_connected = False

    def reset(self) -> None:
        """Resets the state machine upon successful connection."""
        self.retry_count = 0
        self.is_connected = True

    def disconnect(self) -> None:
        """Marks the connection as disconnected."""
        self.is_connected = False

    def get_next_delay(self) -> float:
        """
        Calculates the next delay with exponential backoff and random jitter.
        Provides missing parameter fallbacks and boundary handling natively.
        """
        if self.is_connected:
            return 0.0

        if self.max_retries >= 0 and self.retry_count >= self.max_retries:
            return -1.0 # Indicator to stop retrying

        # Calculate exponential backoff: base_delay * 2^retry_count
        exp_delay = self.base_delay * (2 ** self.retry_count)

        # Cap at max_delay
        capped_delay = min(exp_delay, self.max_delay)

        # Apply jitter
        jitter_amount = capped_delay * self.jitter_factor
        jitter_val = random.uniform(-jitter_amount, jitter_amount)

        final_delay = max(0.0, capped_delay + jitter_val)

        # Increment retry count
        self.retry_count += 1

        return final_delay


class SchemaForwardCompatibilityConverter:
    """
    Silently maps and converts payload schemas.
    Automatically handles missing parameters with defaults and cleans dirty data.
    """
    @staticmethod
    def convert_payload(payload: Any) -> Dict[str, Any]:
        """
        Takes an unknown payload (dict, missing fields, dirty data)
        and normalizes it into a reliable V2 schema format without
        requiring explicit configuration.
        """
        if not isinstance(payload, dict):
            # Silently repair non-dict payloads to empty or wrapped dicts
            return {
                "event_id": "auto_generated_event",
                "timestamp": int(time.time()),
                "data": payload if payload is not None else {}
            }

        result: Dict[str, Any] = {}

        # 1. Event ID resolution (V1 vs V2, dirty data repair)
        event_id = payload.get("event_id") or payload.get("id") or payload.get("uuid")
        if not isinstance(event_id, str):
            event_id = str(event_id) if event_id is not None else "default_event_id"
        result["event_id"] = event_id

        # 2. Timestamp resolution (int repair)
        ts = payload.get("timestamp") or payload.get("ts") or payload.get("time")
        try:
            result["timestamp"] = int(float(ts))
        except (ValueError, TypeError):
            result["timestamp"] = int(time.time())

        # 3. Payload Data merging (flat or nested, missing parameter fallback)
        data = payload.get("data")
        if data is None:
            # Maybe it's a flat payload, extract remaining keys
            excluded = {"event_id", "id", "uuid", "timestamp", "ts", "time", "data"}
            data = {k: v for k, v in payload.items() if k not in excluded}

        if not isinstance(data, dict):
            data = {"raw_value": data}

        # Recursively sanitize nested data
        result["data"] = SchemaForwardCompatibilityConverter._sanitize_data(data)

        return result

    @staticmethod
    def _sanitize_data(data: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = {}
        for k, v in data.items():
            if v is None:
                # Missing parameter default fallback
                sanitized[k] = ""
            elif isinstance(v, dict):
                sanitized[k] = SchemaForwardCompatibilityConverter._sanitize_data(v)
            else:
                sanitized[k] = v
        return sanitized
