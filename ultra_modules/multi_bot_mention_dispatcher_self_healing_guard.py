import time
import uuid
import json
import re
from typing import Any, Dict, Optional, Tuple

class SnapshotManager:
    """
    Manages in-memory snapshots with a 5-second TTL.
    Provides robust self-healing against dirty data or invalid snapshot IDs.
    """
    def __init__(self, ttl_seconds: float = 5.0):
        self.ttl_seconds = ttl_seconds
        self._snapshots: Dict[str, Dict[str, Any]] = {}

    def create_snapshot(self, data: Any) -> str:
        """
        Creates a snapshot and returns a unique ID.
        Safely serializes the incoming data.
        """
        snapshot_id = str(uuid.uuid4())

        # Self-healing: Ensure data is a dict if it can be parsed, else store as raw string
        try:
            if isinstance(data, dict):
                safe_data = data
            elif isinstance(data, str):
                try:
                    safe_data = json.loads(data)
                except ValueError:
                    safe_data = {"raw_content": data}
            else:
                safe_data = {"raw_content": str(data)}
        except Exception:
            safe_data = {}

        self._snapshots[snapshot_id] = {
            "timestamp": time.time(),
            "data": safe_data
        }
        return snapshot_id

    def pop_snapshot(self, snapshot_id: Any) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Attempts to pop a snapshot by ID if it's within the TTL.
        Returns a tuple of (success, data).
        Fails silently and gracefully for invalid/expired IDs.
        """
        if not snapshot_id or not isinstance(snapshot_id, str):
            return False, None

        snapshot = self._snapshots.pop(snapshot_id, None)
        if not snapshot:
            return False, None

        if time.time() - snapshot["timestamp"] > self.ttl_seconds:
            return False, None # Expired

        return True, snapshot["data"]

def clean_string(value: Any, default_val: str = "") -> str:
    if value is None:
        return default_val
    try:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value).strip()
    except Exception:
        return default_val

def parse_mentions(message: Any) -> Dict[str, str]:
    cleaned_msg = clean_string(message)
    if not cleaned_msg:
        return {}

    parts = cleaned_msg.split('@')

    if len(parts) <= 1:
        return {}

    result = {}

    for part in parts[1:]:
        part = part.strip()
        if not part:
            continue

        match = re.match(r'^(\S+)(.*)', part, re.DOTALL)
        if match:
            bot_name = match.group(1).strip()
            command = match.group(2).strip()
            if bot_name in result and result[bot_name]:
                if command:
                    result[bot_name] += " " + command
            else:
                result[bot_name] = command

    return result

def generate_aggregated_card(bot_results: Any) -> Dict[str, Any]:
    if not isinstance(bot_results, dict):
        bot_results = {}

    elements = []

    for bot_name, result_data in bot_results.items():
        bot_name = clean_string(bot_name, default_val="Unknown Bot")

        summary_lines = []
        details = ""

        if isinstance(result_data, dict):
            summary = clean_string(result_data.get('summary', ''))
            details = clean_string(result_data.get('details', ''))
        else:
            summary = clean_string(result_data)

        if not summary:
            summary = "无结果 / No result"

        lines = summary.split('\n')
        if len(lines) > 3:
            summary_lines = lines[:3]
            if not details:
                details = '\n'.join(lines[3:])
            else:
                details = '\n'.join(lines[3:]) + '\n---\n' + details
        else:
            summary_lines = lines

        truncated_summary = '\n'.join(summary_lines)

        elements.append({
            "tag": "markdown",
            "content": f"**@{bot_name}** 响应:\n{truncated_summary}"
        })

        if details:
            elements.append({
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "详细数据 (点击查看) / Detailed data:"
                    },
                    {
                        "tag": "plain_text",
                        "content": details
                    }
                ]
            })

        elements.append({
            "tag": "hr"
        })

    if elements and elements[-1].get("tag") == "hr":
        elements.pop()

    if not elements:
        elements.append({
            "tag": "markdown",
            "content": "未识别到任何有效指令。 / No valid commands recognized."
        })

    card = {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "多Bot协同执行结果汇总"
            },
            "template": "blue"
        },
        "elements": elements
    }

    return card

class MultiBotDispatcherGuard:
    """
    Guard class that encapsulates mention dispatching and card generation,
    injecting self-healing capabilities and a 5-second Undo snapshot.
    """
    def __init__(self, snapshot_ttl: float = 5.0):
        self.snapshot_manager = SnapshotManager(ttl_seconds=snapshot_ttl)

    def dispatch(self, message: Any, bot_results: Any) -> Dict[str, Any]:
        """
        Parses mentions, aggregates results, and generates a card with an Undo button.
        Silently handles dirty data or missing parameters.
        """
        parsed = parse_mentions(message)

        # Self-healing bot_results:
        # If bot_results is None or invalid, we fallback to an empty dict to let generate_aggregated_card handle it gracefully
        if not isinstance(bot_results, dict):
            bot_results = {}

        base_card = generate_aggregated_card(bot_results)

        # Create a snapshot for potential undo
        snapshot_data = {
            "original_message": str(message) if message else "",
            "parsed_mentions": parsed,
            "bot_results": bot_results
        }
        snapshot_id = self.snapshot_manager.create_snapshot(snapshot_data)

        # Inject the Undo button element into the card
        undo_element = {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "撤回 (Undo)"
                    },
                    "type": "danger",
                    "value": {
                        "action": "undo",
                        "snapshot_id": snapshot_id
                    }
                }
            ]
        }

        # Append an HR if there are existing elements, then add the undo button
        if base_card.get("elements"):
            base_card["elements"].append({"tag": "hr"})
        else:
            base_card["elements"] = []

        base_card["elements"].append(undo_element)

        return base_card

    def handle_undo(self, snapshot_id: Any) -> Dict[str, Any]:
        """
        Attempts to process an undo action.
        Returns a simplified response message without ever raising exceptions,
        even for dirty snapshot_id inputs or expired snapshots.
        """
        success, data = self.snapshot_manager.pop_snapshot(snapshot_id)

        if success:
            return {
                "status": "success",
                "message": "已成功撤回操作 / Action successfully undone",
                "recovered_data": data
            }
        else:
            return {
                "status": "failed",
                "message": "撤回失败或已过期 / Undo failed or expired (5s window)",
                "recovered_data": None
            }
