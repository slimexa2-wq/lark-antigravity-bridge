import re
import json
from typing import Dict, Any, Optional

class SlashCommandQuickMenuRouter:
    """
    A simple, zero-configuration router for quick menu slash commands.
    Automatically detects and maps old/new schema versions seamlessly.
    """

    SUPPORTED_COMMANDS = {
        "/周报": "weekly_report",
        "/提成": "commission",
        "/漫剧": "comic_drama",
        "/标书": "bidding_document",
        "/状态": "status"
    }

    @classmethod
    def process_request(cls, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the incoming request. Performs silent data cleaning, auto-fallback,
        and schema version bridging.
        """
        # Ensure input is a dictionary
        if not isinstance(request_data, dict):
            request_data = {}

        # 1. Clean data and extract base command
        raw_cmd = str(request_data.get("command", "")).strip()

        # Auto-fallback for empty or invalid commands
        if not raw_cmd:
            raw_cmd = "/状态"

        # Ensure slash prefix
        if not raw_cmd.startswith("/"):
            raw_cmd = f"/{raw_cmd}"

        # 2. Extract arguments
        parts = raw_cmd.split(maxsplit=1)
        base_cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        # Unknown command fallback
        if base_cmd not in cls.SUPPORTED_COMMANDS:
            base_cmd = "/状态"

        action = cls.SUPPORTED_COMMANDS[base_cmd]

        # 3. Handle schema differences
        # Try to extract data from both old ('payload') and new ('data') schema
        payload = request_data.get("payload")
        data = request_data.get("data")

        extracted_data = {}
        if isinstance(data, dict):
            extracted_data = data
        elif isinstance(payload, dict):
            extracted_data = payload
        elif isinstance(payload, str):
            try:
                extracted_data = json.loads(payload)
            except Exception:
                extracted_data = {}

        # Combine args into data
        if args and not extracted_data.get("args"):
            extracted_data["args"] = args

        # 4. Standardize output schema (latest version)
        return {
            "status": "success",
            "action": action,
            "data": extracted_data,
            "original_command": base_cmd
        }
