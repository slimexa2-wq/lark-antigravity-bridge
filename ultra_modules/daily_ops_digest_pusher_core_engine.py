import json
import logging

def generate_daily_digest(data: dict) -> dict:
    """
    Generates a Daily Ops Digest for Jules Fleet.
    Implements pure function algorithm, zero-configuration auto-fault tolerance,
    missing parameter fallback, and silent dirty data self-healing.
    """
    if not isinstance(data, dict):
        data = {}

    # Dirty data silent cleaning & defaults extraction
    def extract_dict(key):
        val = data.get(key)
        return val if isinstance(val, dict) else {}

    progress_data = extract_dict("progress")
    recruitment_data = extract_dict("recruitment")
    health_data = extract_dict("health")

    # 1. Process Progress
    progress_status = str(progress_data.get("status", "Unknown"))
    if not progress_status.strip():
        progress_status = "Unknown"

    progress_details = str(progress_data.get("details", "No details provided."))
    # Boundary: extremely long string truncation for details
    if len(progress_details) > 1000:
        progress_details = progress_details[:997] + "..."

    # 2. Process Recruitment
    def parse_int(val, default=0):
        try:
            parsed = int(val)
            return parsed if parsed >= 0 else default
        except (ValueError, TypeError):
            return default

    hired = parse_int(recruitment_data.get("hired"), 0)
    target = parse_int(recruitment_data.get("target"), 0)
    # Target should at least be what's hired to avoid weird negative ratios if something is wrong
    if target < hired:
        target = hired

    recruitment_details = str(recruitment_data.get("details", "No details provided."))
    if len(recruitment_details) > 1000:
        recruitment_details = recruitment_details[:997] + "..."

    # 3. Process System Health
    def parse_float(val, default=100.0):
        try:
            parsed = float(val)
            # Health score bounds check
            if parsed < 0.0 or parsed > 100.0:
                return default
            return parsed
        except (ValueError, TypeError):
            return default

    health_score = parse_float(health_data.get("score"), 100.0)
    health_details = str(health_data.get("details", "System running normally."))
    if len(health_details) > 1000:
        health_details = health_details[:997] + "..."

    # Core Summary (Strictly <= 3 lines to prevent mobile screen flooding)
    line1 = f"🚀 Jules Fleet Progress: {progress_status}"
    line2 = f"👥 Recruitment: {hired}/{target} target achieved"
    line3 = f"❤️ System Health: {health_score:.1f}%"
    core_summary = f"{line1}\n{line2}\n{line3}"

    # Ensure it's exactly 3 lines max by just safety splitting (though we built it as 3 lines)
    core_summary_lines = core_summary.split("\n")[:3]
    final_core_summary = "\n".join(core_summary_lines)

    # Feishu Card Structure with Collapsible Panel for details
    card = {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "Jules Fleet Daily Ops Digest"
            },
            "template": "blue"
        },
        "elements": [
            {
                "tag": "markdown",
                "content": final_core_summary
            },
            {
                "tag": "collapsible_panel",
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "View Detailed Data"
                    }
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": f"**Progress Details**\n{progress_details}\n\n**Recruitment Details**\n{recruitment_details}\n\n**Health Details**\n{health_details}"
                    }
                ]
            }
        ]
    }

    return card
