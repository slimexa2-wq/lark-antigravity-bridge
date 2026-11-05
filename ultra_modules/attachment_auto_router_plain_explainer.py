import json
from typing import Any, Dict, Optional

def clean_string(val: Any) -> str:
    """Safely cast to string and clean."""
    if val is None:
        return ""
    try:
        return str(val).strip()
    except Exception:
        return ""

def explain_routing_result(
    routing_result: Optional[Any] = None,
    title: Optional[Any] = None,
    show_undo: bool = True
) -> Dict[str, Any]:
    """
    Format complex routing calculation results into a simple 1-second plain-text conclusion card.
    Limit core summaries to a maximum of 3 lines and place detailed data inside single-click collapsible panels.
    """

    # 1. Dirty data self-healing & default handling
    safe_title = clean_string(title)
    if not safe_title:
        safe_title = "文件智能路由结果"

    if not isinstance(routing_result, dict):
        if isinstance(routing_result, str):
            try:
                parsed = json.loads(routing_result)
                routing_result = parsed if isinstance(parsed, dict) else {}
            except Exception:
                routing_result = {}
        else:
            routing_result = {}

    # Extract info with fallback
    filename = clean_string(routing_result.get("filename", ""))
    if not filename:
        filename = "未知文件"

    routed_to = clean_string(routing_result.get("routed_to", ""))

    # Map technical engine names to plain Chinese names
    engine_name_mapping = {
        "weekly_report": "周报引擎",
        "commission": "提成引擎",
        "tender_document": "标书引擎",
        "comic_drama": "漫剧引擎",
        "unknown": "未知类型，需人工处理"
    }

    plain_routed_to = engine_name_mapping.get(routed_to, "未知类型，需人工处理") if routed_to else "未知类型，需人工处理"

    reasoning = clean_string(routing_result.get("reasoning", ""))
    if not reasoning:
        reasoning = "系统根据文件内容与特征自动推断。"

    confidence = routing_result.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0

    confidence_str = f"{confidence * 100:.1f}%" if confidence > 0 else "未知"

    # 2. Build short summary (Max 3 lines)
    summary_lines = [
        f"📄 **接收文件**：{filename}",
        f"🎯 **已路由至**：{plain_routed_to}",
        f"💡 **置信度**：{confidence_str}"
    ]
    summary_text = "\n".join(summary_lines)

    # Detailed raw JSON / extra info
    try:
        detailed_info = json.dumps(routing_result, ensure_ascii=False, indent=2)
    except Exception:
        detailed_info = str(routing_result)

    # 3. Build elements
    elements = []

    # Summary
    elements.append({
        "tag": "markdown",
        "content": summary_text
    })

    # Collapsible Panel for details
    elements.append({
        "tag": "collapsible_panel",
        "vertical_spacing": "default",
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "展开查看路由详细特征与原始数据"
            }
        },
        "elements": [
            {
                "tag": "markdown",
                "content": f"**路由推断原因：**\n{reasoning}\n\n**后台原始特征：**\n```json\n{detailed_info}\n```"
            }
        ],
        "default_expanded": False
    })

    # Undo button
    if show_undo:
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "撤销本次路由 (Undo)"
                    },
                    "type": "default",
                    "value": {
                        "action": "undo"
                    }
                }
            ]
        })

    # 4. Construct Card
    card = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "blue",
                "title": {
                    "tag": "plain_text",
                    "content": safe_title
                }
            },
            "elements": elements
        }
    }

    return card
