import json
from typing import Dict, Any, List, Optional
from datetime import datetime

class AuditLogger:
    """Silently records audit traces for data deduplication, repairs, and sanitization."""
    def __init__(self) -> None:
        self.logs: List[Dict[str, Any]] = []

    def trace(self, action: str, details: Dict[str, Any]) -> None:
        self.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "details": details
        })

    def get_logs(self) -> List[Dict[str, Any]]:
        return self.logs


class DigestPusher:
    """
    Generates a 1-page Daily Ops Digest for Lark/Feishu.
    Ensures zero-config fault tolerance, dirty data cleanup, and missing dictionary fallbacks.
    """
    def __init__(self) -> None:
        self.audit_logger = AuditLogger()

    def _sanitize_metric(self, value: Any, default: int = 0, allow_negative: bool = False) -> int:
        original = value
        try:
            if value is None:
                parsed = default
            elif isinstance(value, str):
                parsed = int(float(value))
            elif isinstance(value, (int, float)):
                parsed = int(value)
            else:
                parsed = default
        except (ValueError, TypeError, OverflowError):
            parsed = default

        if not allow_negative and parsed < 0:
            self.audit_logger.trace("sanitize_metric_negative", {"original": original, "fixed": 0})
            return 0

        if parsed != original:
            self.audit_logger.trace("sanitize_metric_type", {"original": original, "fixed": parsed})

        return parsed

    def _sanitize_string(self, value: Any, default: str = "Unknown") -> str:
        if not value or not isinstance(value, str):
            self.audit_logger.trace("sanitize_string", {"original": value, "fixed": default})
            return default
        return value.strip()

    def _calculate_diff(self, current: int, previous: int) -> str:
        diff = current - previous
        if diff > 0:
            return f"🟢 +{diff}"
        elif diff < 0:
            return f"🔴 {diff}"
        return "⚪ 0"

    def _process_fleet_metrics(self, data: Dict[str, Any]) -> str:
        current_active = self._sanitize_metric(data.get("active_agents"), 0)
        previous_active = self._sanitize_metric(data.get("previous_active_agents"), current_active)

        tasks_completed = self._sanitize_metric(data.get("tasks_completed"), 0)

        diff_str = self._calculate_diff(current_active, previous_active)

        return f"**Jules Fleet**\n- Active Agents: {current_active} ({diff_str})\n- Tasks Completed: {tasks_completed}"

    def _process_recruitment(self, data: Dict[str, Any]) -> str:
        candidates = self._sanitize_metric(data.get("candidates_screened"), 0)
        interviews = self._sanitize_metric(data.get("interviews_scheduled"), 0)
        offers = self._sanitize_metric(data.get("offers_sent"), 0)

        if interviews > candidates:
            self.audit_logger.trace("heal_recruitment_interviews", {"interviews": interviews, "candidates": candidates})
            interviews = candidates

        if offers > interviews:
            self.audit_logger.trace("heal_recruitment_offers", {"offers": offers, "interviews": interviews})
            offers = interviews

        return f"**Recruitment**\n- Screened: {candidates}\n- Interviews: {interviews}\n- Offers: {offers}"

    def _process_system_health(self, data: Dict[str, Any]) -> str:
        status = self._sanitize_string(data.get("status"), "Healthy")
        valid_statuses = ["Healthy", "Degraded", "Down"]
        if status not in valid_statuses:
            self.audit_logger.trace("heal_system_status", {"original": status, "fixed": "Degraded"})
            status = "Degraded"

        uptime = self._sanitize_metric(data.get("uptime_hours"), 0)
        # Handle extreme boundary: uptime > 8760 (1 year)
        if uptime > 8760:
            self.audit_logger.trace("heal_system_uptime_boundary", {"original": uptime, "fixed": 8760})
            uptime = 8760

        return f"**System Health**\n- Status: {status}\n- Uptime: {uptime}h"

    def generate_digest(self, raw_data: Optional[Dict[str, Any]] = None) -> str:
        if not isinstance(raw_data, dict):
            self.audit_logger.trace("heal_raw_data_type", {"original_type": type(raw_data).__name__, "fixed": "empty_dict"})
            raw_data = {}

        fleet_data = raw_data.get("fleet", {})
        if not isinstance(fleet_data, dict):
            self.audit_logger.trace("heal_fleet_data_type", {"fixed": "empty_dict"})
            fleet_data = {}

        recruitment_data = raw_data.get("recruitment", {})
        if not isinstance(recruitment_data, dict):
            self.audit_logger.trace("heal_recruitment_data_type", {"fixed": "empty_dict"})
            recruitment_data = {}

        health_data = raw_data.get("health", {})
        if not isinstance(health_data, dict):
            self.audit_logger.trace("heal_health_data_type", {"fixed": "empty_dict"})
            health_data = {}

        fleet_section = self._process_fleet_metrics(fleet_data)
        recruitment_section = self._process_recruitment(recruitment_data)
        health_section = self._process_system_health(health_data)

        # Assemble the 1-page digest
        digest = (
            "📄 **Daily Ops Digest**\n"
            "=========================\n\n"
            f"{fleet_section}\n\n"
            f"{recruitment_section}\n\n"
            f"{health_section}\n"
            "========================="
        )

        return digest
