import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class DailyOpsDigestPusherSelfHealingGuard:
    def __init__(self):
        self.snapshots = {}
        self.UNDO_WINDOW_SECONDS = 5

    def _heal_data(self, data: Any) -> Dict[str, Any]:
        """
        Heals missing or dirty data to guarantee safe fallback defaults.
        """
        if not isinstance(data, dict):
            data = {}

        healed = {
            "jules_fleet_progress": 0,
            "recruitment_rate": 0,
            "system_health": "Healthy"
        }

        try:
            prog = data.get("jules_fleet_progress", 0)
            if isinstance(prog, str):
                prog = prog.replace('%', '').strip()
            prog = int(float(prog))
            healed["jules_fleet_progress"] = max(0, min(100, prog))
        except (ValueError, TypeError, AttributeError):
            pass

        try:
            rec = data.get("recruitment_rate", 0)
            if isinstance(rec, str):
                rec = rec.replace('%', '').strip()
            rec = int(float(rec))
            healed["recruitment_rate"] = max(0, min(100, rec))
        except (ValueError, TypeError, AttributeError):
            pass

        try:
            health = data.get("system_health")
            if isinstance(health, str) and health.strip():
                healed["system_health"] = health.strip()
        except (ValueError, TypeError, AttributeError):
            pass

        return healed

    def _generate_card(self, healed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates card data, adhering strictly to max 3 lines core summary
        and placing detailed data inside a collapsible panel.
        """
        summary = (
            f"Jules舰队进度: {healed_data['jules_fleet_progress']}%\n"
            f"招聘达成: {healed_data['recruitment_rate']}%\n"
            f"系统健康度: {healed_data['system_health']}"
        )

        return {
            "type": "template",
            "data": {
                "template_id": "daily_ops_digest",
                "template_version_name": "1.0",
                "template_variable": {
                    "summary_text": summary,
                    "collapsible_details": {
                        "click_to_expand": True,
                        "jules_fleet_progress_details": f"详细舰队资源分配及节点状态，总进度: {healed_data['jules_fleet_progress']}%",
                        "recruitment_rate_details": f"各部门详细漏斗数据，当前达成率: {healed_data['recruitment_rate']}%",
                        "system_health_details": f"微服务各项指标监控日志，健康度: {healed_data['system_health']}"
                    }
                }
            }
        }

    def push_digest(self, raw_data: Any, push_id: str) -> Dict[str, Any]:
        """
        Pushes digest silently and saves a snapshot for possible 1-tap undo.
        No popup errors will be thrown to the user.
        """
        try:
            healed_data = self._heal_data(raw_data)
            card = self._generate_card(healed_data)

            self.snapshots[push_id] = {
                "timestamp": time.time(),
                "card": card,
                "status": "pushed"
            }

            return {
                "success": True,
                "push_id": push_id,
                "card": card
            }
        except Exception as e:
            logger.error(f"Failed to push digest {push_id}: {e}")
            return {
                "success": False,
                "push_id": push_id,
                "error": "Silent failure handling"
            }

    def undo_push(self, push_id: str) -> Dict[str, Any]:
        """
        1-tap snapshot undo mechanism within a 5-second window.
        """
        if push_id not in self.snapshots:
            return {"success": False, "message": "Snapshot not found"}

        snapshot = self.snapshots[push_id]
        if snapshot["status"] == "undone":
            return {"success": True, "message": "Already undone"}

        elapsed_time = time.time() - snapshot["timestamp"]
        if elapsed_time > self.UNDO_WINDOW_SECONDS:
            return {"success": False, "message": "Undo window expired"}

        self.snapshots[push_id]["status"] = "undone"
        return {"success": True, "message": "Undo successful"}
