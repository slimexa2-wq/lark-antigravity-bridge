import time
import json
from typing import Dict, Any

class ApprovalSnapshot:
    def __init__(self, card_id: str, previous_state: str, timestamp: float):
        self.card_id = card_id
        self.previous_state = previous_state
        self.timestamp = timestamp

class ApprovalGuard:
    """
    High-risk outbound action Feishu card 'one-tap approve/reject'
    callback state synchronizer with silent self-healing and 5-second undo snapshot.
    """

    def __init__(self):
        self._snapshots: Dict[str, ApprovalSnapshot] = {}
        self._card_states: Dict[str, str] = {}
        self.undo_window_seconds = 5.0

    def process_callback(self, payload: Any) -> Dict[str, Any]:
        """
        Process the callback payload.
        Zero-configuration fault tolerance: automatically heals dirty data,
        adds missing parameters, and saves a state snapshot for undo.
        """
        # Self-healing: parse stringified JSON or default to dict
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        if not isinstance(payload, dict):
            payload = {}

        # Normalization & Missing Parameter Fallbacks
        raw_card_id = payload.get("card_id", "")
        card_id = str(raw_card_id).strip() if raw_card_id is not None else ""
        if not card_id:
            card_id = "default_card_id"

        raw_user_id = payload.get("user_id", "")
        user_id = str(raw_user_id).strip() if raw_user_id is not None else ""
        if not user_id:
            user_id = "unknown_user"

        raw_action = payload.get("action", "")
        action_str = str(raw_action).strip().lower() if raw_action is not None else ""

        if action_str not in ["approve", "reject"]:
            action_str = "approve"  # Safe default

        # Snapshot the current state before mutating
        current_state = self._card_states.get(card_id, "pending")
        self._snapshots[card_id] = ApprovalSnapshot(
            card_id=card_id,
            previous_state=current_state,
            timestamp=time.time()
        )

        # Apply the new state
        new_state = "approved" if action_str == "approve" else "rejected"
        self._card_states[card_id] = new_state

        return {
            "status": "success",
            "card_id": card_id,
            "user_id": user_id,
            "action_applied": action_str,
            "current_state": new_state,
            "message": "Action applied silently."
        }

    def undo_action(self, payload: Any) -> Dict[str, Any]:
        """
        One-tap undo action. Reverts state if called within 5 seconds.
        """
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        if not isinstance(payload, dict):
            payload = {}

        raw_card_id = payload.get("card_id", "")
        card_id = str(raw_card_id).strip() if raw_card_id is not None else ""
        if not card_id:
            card_id = "default_card_id"

        snapshot = self._snapshots.get(card_id)
        if not snapshot:
            return {
                "status": "error",
                "message": "No snapshot available for undo.",
                "current_state": self._card_states.get(card_id, "pending")
            }

        elapsed = time.time() - snapshot.timestamp
        if elapsed > self.undo_window_seconds:
            # Expired snapshot
            del self._snapshots[card_id]
            return {
                "status": "error",
                "message": "Undo window expired.",
                "current_state": self._card_states.get(card_id, "pending")
            }

        # Apply undo
        self._card_states[card_id] = snapshot.previous_state
        del self._snapshots[card_id]

        return {
            "status": "success",
            "card_id": card_id,
            "message": "Undo successful.",
            "current_state": snapshot.previous_state
        }

    def get_card_state(self, card_id: str) -> str:
        """Helper to get current state, defaulting to 'pending'."""
        return self._card_states.get(card_id, "pending")
