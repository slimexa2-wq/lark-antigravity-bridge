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

def build_collapsible_thinking_card(
    conclusion: Optional[Any] = None,
    thinking_process: Optional[Any] = None,
    title: Optional[Any] = None,
    card_link: Optional[Any] = None,
    show_undo: bool = True
) -> Dict[str, Any]:
    """
    Builds a collapsible thinking Feishu card.
    1. conclusion pinned to the top.
    2. thinking process collapsible (default collapsed).
    3. undo button (optional).
    """

    # 1. Dirty data self-healing and missing parameter defaults
    safe_conclusion = clean_string(conclusion)
    if not safe_conclusion:
        safe_conclusion = "暂无结论"

    safe_thinking = clean_string(thinking_process)
    if not safe_thinking:
        safe_thinking = "暂无推理过程"

    safe_title = clean_string(title)
    if not safe_title:
        safe_title = "智能推理结果"

    safe_link = clean_string(card_link)

    # 2. Build Card
    elements = []

    # Conclusion section
    elements.append({
        "tag": "markdown",
        "content": f"**结论：**\n{safe_conclusion}"
    })

    # Thinking process section (collapsible)
    # Using 'column_set' or similar structure if we were doing true Feishu collapsible panels.
    # Feishu 2.0 card schema supports 'collapsible_panel'
    # Reference for Feishu collapsible panel:
    # {
    #   "tag": "collapsible_panel",
    #   "title": "推理过程",
    #   "elements": [...],
    #   "default_expanded": False
    # }
    # However, sometimes standard markdown is enough if collapsible is not strictly tag based.
    # Let's use the standard Feishu collapsible panel syntax:
    elements.append({
        "tag": "collapsible_panel",
        "vertical_spacing": "default",
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "展开查看推理过程"
            }
        },
        "elements": [
            {
                "tag": "markdown",
                "content": safe_thinking
            }
        ],
        "default_expanded": False
    })

    # Action section (Undo button)
    if show_undo:
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "撤回 (Undo)"
                    },
                    "type": "default",
                    "value": {
                        "action": "undo"
                    }
                }
            ]
        })

    # Card Header
    header = {
        "title": {
            "tag": "plain_text",
            "content": safe_title
        },
        "template": "blue"
    }

    card = {
        "config": {
            "wide_screen_mode": True
        },
        "header": header,
        "elements": elements
    }

    if safe_link:
        card["card_link"] = {
            "url": safe_link,
            "pc_url": safe_link,
            "ios_url": safe_link,
            "android_url": safe_link
        }

    return card
