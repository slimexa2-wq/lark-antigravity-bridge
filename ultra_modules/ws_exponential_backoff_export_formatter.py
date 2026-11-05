import math
import random
from typing import Dict, Any, Optional

class WSExponentialBackoffExportFormatter:
    """
    Feishu persistent connection WebSocket disconnect exponential backoff + random jitter
    silent self-healing reconnection state machine & report generator.
    """

    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, jitter_factor: float = 0.5):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_factor = jitter_factor

    def _clean_numeric(self, val: Any, default: float = 0.0) -> float:
        """Self-healing for None/NaN and other dirty data."""
        if val is None:
            return default
        try:
            f_val = float(val)
            if math.isnan(f_val) or math.isinf(f_val):
                return default
            return f_val
        except (ValueError, TypeError):
            return default

    def calculate_backoff(self, attempt: Any) -> float:
        """Calculate exponential backoff with jitter."""
        clean_attempt = max(0.0, self._clean_numeric(attempt, 0.0))
        # Exponential backoff: base_delay * 2^attempt
        capped_attempt = min(clean_attempt, 20.0)
        delay = self.base_delay * (2 ** capped_attempt)

        # Apply random jitter
        jitter_range = delay * self.jitter_factor
        jitter = random.uniform(-jitter_range, jitter_range)

        final_delay = delay + jitter

        # Clamp to bounds
        return max(0.0, min(self.max_delay, final_delay))

    def generate_export_data(self, state_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate cleaned export data.
        Ensures comments=0 and no NaN/None in numericals.
        """
        if state_data is None:
            state_data = {}

        attempt = self._clean_numeric(state_data.get("attempt"), 0.0)
        connection_uptime = self._clean_numeric(state_data.get("connection_uptime"), 0.0)

        next_retry_delay = self.calculate_backoff(attempt)

        status = state_data.get("status")
        if not isinstance(status, str) or not status.strip():
            status = "disconnected"

        export_data = {
            "attempt": int(attempt),
            "connection_uptime": connection_uptime,
            "next_retry_delay": round(next_retry_delay, 2),
            "status": status.strip(),
            "comments": 0,
            "error_count": int(self._clean_numeric(state_data.get("error_count"), 0.0))
        }

        return export_data

    def generate_report(self, state_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a 3-line minimalist report text for WeChat/Feishu.
        """
        export_data = self.generate_export_data(state_data)

        line1 = f"【WS状态】{export_data['status']} | 运行时长: {export_data['connection_uptime']:.1f}s"
        line2 = f"【重连机制】第{export_data['attempt']}次退避 | 下次重试: {export_data['next_retry_delay']}s"
        line3 = f"【健康度】异常次数: {export_data['error_count']} | 诊断备注: {export_data['comments']}"

        return f"{line1}\n{line2}\n{line3}"
