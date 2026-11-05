import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def process_approval_callback(payload: Optional[Any] = None) -> Dict[str, Any]:
    """
    Process one-tap approval/rejection callback from Feishu cards.

    This function is a pure algorithm that parses the callback payload, cleans dirty data,
    auto-fallbacks missing parameters, and generates a zero-redirect response for Feishu cards.
    """
    # 1. Extreme boundary: None payload
    if payload is None:
        payload = {}

    # 2. Parse stringified JSON if it comes as a string
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            # Fallback for invalid JSON string
            payload = {}

    # If payload is not a dict after parsing, force it to an empty dict
    if not isinstance(payload, dict):
        payload = {}

    # 3. Extract and clean data
    action_data = payload.get("action", {})
    if not isinstance(action_data, dict):
        action_data = {}

    action_value = action_data.get("value", {})
    if not isinstance(action_value, dict):
        action_value = {}

    # 4. Handle default parameters and missing data
    action_type = action_value.get("action_type", "unknown")
    approval_id = action_value.get("approval_id", "default_approval_id")

    # 5. Build response based on action type
    # If action_type is missing or unexpected, default to error state
    if action_type not in ["approve", "reject"]:
        toast_message = "Invalid or missing action type"
        toast_type = "error"
    else:
        status_text = "Approved" if action_type == "approve" else "Rejected"
        toast_message = f"Successfully {status_text.lower()} {approval_id}"
        toast_type = "success"

    # Zero-redirect response format for Feishu cards
    return {
        "toast": {
            "type": toast_type,
            "content": toast_message,
        }
    }
