import datetime
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

class AuditLogger:
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def log(self, action: str, details: Dict[str, Any]) -> None:
        """Silently record every step."""
        log_entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "action": action,
            "details": details
        }
        self.logs.append(log_entry)
        logging.debug(f"Audit Log: {json.dumps(log_entry)}")

    def get_logs(self) -> List[Dict[str, Any]]:
        return self.logs

def generate_diff(old_state: Dict[str, Any], new_state: Dict[str, Any]) -> Dict[str, Any]:
    """Generates a highlighting comparison diff."""
    diff = {}
    all_keys = set(old_state.keys()).union(set(new_state.keys()))

    for key in all_keys:
        old_val = old_state.get(key)
        new_val = new_state.get(key)

        if old_val != new_val:
            diff[key] = {
                "old": old_val,
                "new": new_val
            }

    return diff

def _clean_dirty_data(value: Any) -> Any:
    """Silently cleans dirty data (e.g., stripping whitespace from strings)."""
    if isinstance(value, str):
        return value.strip()
    elif isinstance(value, dict):
        return {k: _clean_dirty_data(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_clean_dirty_data(item) for item in value]
    return value

def process_approval_callback(
    action: str,
    target_id: str,
    context: Optional[Dict[str, Any]] = None,
    old_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process one-tap approval callback with zero-configuration fault tolerance.

    Backend implementations must be rigorous and robust, favoring pure functions,
    automatic boundary fallback, silent cleaning of dirty data.
    """
    audit_logger = AuditLogger()
    audit_logger.log("START", {"target_id": target_id, "action": action})

    # Default fallback for missing parameters
    context = context or {}
    old_state = old_state or {}
    new_state = new_state or {}
    reason = reason or "No reason provided"

    # Clean dirty data
    action = _clean_dirty_data(action)
    target_id = _clean_dirty_data(target_id)
    context = _clean_dirty_data(context)
    old_state = _clean_dirty_data(old_state)
    new_state = _clean_dirty_data(new_state)
    reason = _clean_dirty_data(reason)

    # Validate action
    valid_actions = {"approve", "reject"}
    if action.lower() not in valid_actions:
        audit_logger.log("INVALID_ACTION_FALLBACK", {"original_action": action, "fallback": "reject"})
        action = "reject"
    else:
        action = action.lower()

    # Generate diff if states are provided
    diff = generate_diff(old_state, new_state)
    audit_logger.log("DIFF_GENERATED", {"diff": diff})

    result = {
        "status": "success",
        "action_taken": action,
        "target_id": target_id,
        "reason": reason,
        "diff_highlight": diff,
        # Frontend gets a clean result
        "frontend_display": f"Successfully {action}{"d" if action.endswith("e") else "ed"} target {target_id}."
    }

    audit_logger.log("END", {"result": result})

    # In a real system, audit logs would be saved to a database here.
    return result
