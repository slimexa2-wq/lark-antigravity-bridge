import re
import json
from typing import Any, Dict, List, Optional

def clean_string(value: Any, default_val: str = "") -> str:
    """
    Silently handles dirty data and missing parameters, converting inputs to strings
    and stripping whitespace.
    """
    if value is None:
        return default_val
    try:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value).strip()
    except Exception:
        return default_val

def parse_mentions(message: Any) -> Dict[str, str]:
    """
    Parses a message containing multiple bot mentions (e.g., '@大肥鱼', '@招聘')
    and returns a dictionary of routed commands for each bot.
    Provides default fallbacks for missing or dirty messages.
    """
    cleaned_msg = clean_string(message)
    if not cleaned_msg:
        return {}

    # Extract all mentions using regex. A mention is assumed to start with '@'
    # followed by non-whitespace characters.
    # To handle multiple mentions gracefully and assign trailing text to the preceding mention.

    # We split by '@'
    parts = cleaned_msg.split('@')

    if len(parts) <= 1:
        return {}

    result = {}

    for part in parts[1:]:
        part = part.strip()
        if not part:
            continue

        # The bot name is the first word, the rest is the command
        match = re.match(r'^(\S+)(.*)', part, re.DOTALL)
        if match:
            bot_name = match.group(1).strip()
            command = match.group(2).strip()
            # If a bot is mentioned multiple times, we append the command or just use the last one?
            # Let's concatenate commands if mentioned multiple times, or just keep the last one.
            # We'll just keep the last one for simplicity, or concatenate them with a space.
            if bot_name in result and result[bot_name]:
                if command:
                    result[bot_name] += " " + command
            else:
                result[bot_name] = command

    return result

def generate_aggregated_card(bot_results: Any) -> Dict[str, Any]:
    """
    Aggregates bot results into a Feishu message card JSON structure.
    Limits core summaries to 3 lines and represents detailed data in collapsible structures.
    """
    # Self-healing for bot_results
    if not isinstance(bot_results, dict):
        bot_results = {}

    elements = []

    for bot_name, result_data in bot_results.items():
        bot_name = clean_string(bot_name, default_val="Unknown Bot")

        # Determine summary and details
        summary_lines = []
        details = ""

        if isinstance(result_data, dict):
            summary = clean_string(result_data.get('summary', ''))
            details = clean_string(result_data.get('details', ''))
        else:
            summary = clean_string(result_data)

        if not summary:
            summary = "无结果 / No result"

        # Truncate summary to max 3 lines
        lines = summary.split('\n')
        if len(lines) > 3:
            summary_lines = lines[:3]
            # Put the rest into details if details is empty
            if not details:
                details = '\n'.join(lines[3:])
            else:
                details = '\n'.join(lines[3:]) + '\n---\n' + details
        else:
            summary_lines = lines

        truncated_summary = '\n'.join(summary_lines)

        # Add summary element
        elements.append({
            "tag": "markdown",
            "content": f"**@{bot_name}** 响应:\n{truncated_summary}"
        })

        # Add collapsible details if any
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

        # Add a divider between bots if it's not the last one (will handle in list comprehension or just add divider)
        elements.append({
            "tag": "hr"
        })

    # Remove the last divider if it exists
    if elements and elements[-1].get("tag") == "hr":
        elements.pop()

    # Fallback if no elements
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
