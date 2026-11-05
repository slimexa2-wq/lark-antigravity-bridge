import math
from typing import Dict, Any, Union

def sanitize_export_data(data: Any) -> Any:
    """Recursively sanitize data to replace None, NaN and ensure comments=0."""
    if data is None:
        return ""

    if isinstance(data, float) and math.isnan(data):
        return 0

    if isinstance(data, list):
        return [sanitize_export_data(item) for item in data]

    if isinstance(data, dict):
        sanitized = {k: sanitize_export_data(v) for k, v in data.items()}
        # Enforce comments=0 if not present or invalid (note: None is already mapped to "" by sanitize_export_data)
        if "comments" not in sanitized or sanitized["comments"] == "" or (isinstance(sanitized["comments"], float) and math.isnan(sanitized["comments"])):
            sanitized["comments"] = 0
        return sanitized

    return data

def generate_report_text(command: str, data: Dict[str, Any]) -> str:
    """Generate exactly a 3-line text report suitable for copying."""
    if command is None or not isinstance(command, str):
        command = ""

    command_clean = command.strip()

    # Line 1: Header
    if command_clean == "/周报":
        title = "【本周工作汇报】"
    elif command_clean == "/提成":
        title = "【提成核算简报】"
    elif command_clean == "/漫剧":
        title = "【漫剧项目进度】"
    elif command_clean == "/标书":
        title = "【标书制作状态】"
    elif command_clean == "/状态":
        title = "【当前状态同步】"
    else:
        title = "【快捷导出简报】"

    # Line 2: Details
    details = []
    for k, v in list(data.items())[:3]: # take up to 3 items
        if k != "comments":
            details.append(f"{k}:{v}")

    details_str = " | ".join(details) if details else "暂无详细数据"

    # Line 3: Footer (always has comments=0 due to sanitize)
    comments = data.get("comments", 0)
    footer = f"已处理批注数量：{comments}，随时可复制流转。"

    return f"{title}\n数据概览：{details_str}\n{footer}"

def format_quick_menu_export(command: str = "", data: Any = None) -> Dict[str, Any]:
    """Format and generate export, auto-healing bad inputs."""
    # Self-heal malformed data
    if data is None or not isinstance(data, dict):
        data = {}

    # Sanitize data
    safe_data = sanitize_export_data(data)

    # Generate 3-line report
    report_text = generate_report_text(command, safe_data)

    return {
        "command": command if isinstance(command, str) else "",
        "sanitized_data": safe_data,
        "report_text": report_text
    }
