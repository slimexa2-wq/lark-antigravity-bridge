import time
from typing import Any, Dict

class SlashCommandQuickMenuSelfHealingGuard:
    """
    A router and guard for quick menu slash commands in Lark.
    Features extreme zero-configuration fault tolerance, self-healing of dirty data,
    missing parameter fallbacks, and a strict 5-second one-click undo mechanism.
    """

    ALLOWED_COMMANDS = {
        "周报", "提成", "漫剧", "标书", "状态"
    }

    COMMAND_ALIASES = {
        "weekly": "周报", "zhoubao": "周报", "zb": "周报", "report": "周报",
        "commission": "提成", "ticheng": "提成", "tc": "提成", "bonus": "提成",
        "comic": "漫剧", "manju": "漫剧", "mj": "漫剧", "drama": "漫剧",
        "bid": "标书", "biaoshu": "标书", "bs": "标书", "bidding": "标书",
        "status": "状态", "zhuangtai": "状态", "zt": "状态", "state": "状态",
    }

    def __init__(self) -> None:
        # State management: session_id -> dict
        self._state: Dict[str, Dict[str, Any]] = {}
        # Snapshot for undo: session_id -> dict
        self._snapshots: Dict[str, Dict[str, Any]] = {}
        # Configuration
        self.undo_window_seconds = 5.0

    def _normalize_session_id(self, session_id: Any) -> str:
        """Silently heal session ID."""
        if not session_id or not isinstance(session_id, (str, int)):
            return "default_session"
        clean_id = str(session_id).strip()
        return clean_id if clean_id else "default_session"

    def _heal_command(self, raw_command: Any) -> str:
        """Silently heal dirty command strings, returning a valid allowed command."""
        if not isinstance(raw_command, str):
            raw_command = str(raw_command) if raw_command is not None else ""

        # Remove all whitespace, invalid chars, and slashes
        clean_cmd = "".join(c for c in raw_command if c.isalnum() or c.isalpha() or '\u4e00' <= c <= '\u9fff').lower()

        if clean_cmd in self.ALLOWED_COMMANDS:
            return clean_cmd

        if clean_cmd in self.COMMAND_ALIASES:
            return self.COMMAND_ALIASES[clean_cmd]

        # Fallback for completely unrecognizable or empty inputs
        return "状态"

    def _heal_params(self, command: str, params: Any) -> Dict[str, Any]:
        """Provide sensible default values for missing parameters based on the command."""
        if not isinstance(params, dict):
            params = {}

        healed: Dict[str, Any] = {}

        # Silent clean of keys
        for k, v in params.items():
            if isinstance(k, str) and k.strip():
                healed[k.strip()] = v

        # Apply defaults based on command
        if command == "周报":
            healed.setdefault("week", "current")
            healed.setdefault("format", "summary")
        elif command == "提成":
            healed.setdefault("month", "current")
            healed.setdefault("currency", "CNY")
        elif command == "漫剧":
            healed.setdefault("episode", "latest")
        elif command == "标书":
            healed.setdefault("type", "standard")
            healed.setdefault("status", "draft")
        elif command == "状态":
            healed.setdefault("user", "self")
            healed.setdefault("visibility", "public")

        return healed

    def route_command(self, session_id: Any = None, command: Any = None, **kwargs: Any) -> Dict[str, Any]:
        """
        One-click entry point.
        Zero confirmation pop-ups.
        Zero-configuration fault tolerance.
        """
        sid = self._normalize_session_id(session_id)
        resolved_cmd = self._heal_command(command)
        resolved_params = self._heal_params(resolved_cmd, kwargs)

        # Retrieve current state before transition
        current_state = self._state.get(sid, {"command": None, "params": {}})

        # Create snapshot for 5-second undo
        self._snapshots[sid] = {
            "state": current_state,
            "timestamp": time.time()
        }

        # Update to new state
        new_state = {
            "command": resolved_cmd,
            "params": resolved_params
        }
        self._state[sid] = new_state

        return {
            "success": True,
            "session_id": sid,
            "action": "routed",
            "command": f"/{resolved_cmd}",
            "params": resolved_params,
            "message": f"Successfully routed to /{resolved_cmd}"
        }

    def undo(self, session_id: Any = None) -> Dict[str, Any]:
        """
        One-click undo to revert to the previous state within the 5-second window.
        """
        sid = self._normalize_session_id(session_id)
        snapshot = self._snapshots.get(sid)

        if not snapshot:
            current = self._state.get(sid, {"command": None, "params": {}})
            return {
                "success": True,
                "session_id": sid,
                "action": "undo_skipped",
                "reason": "no_snapshot",
                "command": f"/{current['command']}" if current.get("command") else None,
                "params": current.get("params", {})
            }

        elapsed = time.time() - snapshot["timestamp"]
        if elapsed > self.undo_window_seconds:
            # Expired, clean up silently
            del self._snapshots[sid]
            current = self._state.get(sid, {"command": None, "params": {}})
            return {
                "success": True,
                "session_id": sid,
                "action": "undo_skipped",
                "reason": "expired",
                "command": f"/{current['command']}" if current.get("command") else None,
                "params": current.get("params", {})
            }

        # Restore snapshot
        restored_state = snapshot["state"]
        self._state[sid] = restored_state

        # Destroy snapshot after successful undo to prevent multiple undos
        del self._snapshots[sid]

        return {
            "success": True,
            "session_id": sid,
            "action": "undone",
            "command": f"/{restored_state['command']}" if restored_state.get("command") else None,
            "params": restored_state.get("params", {}),
            "message": "Successfully reverted to previous state"
        }
