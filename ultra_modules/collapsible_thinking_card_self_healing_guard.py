import time
import uuid
from typing import Any, Dict, Optional, Tuple

def clean_string(val: Any) -> str:
    """Safely cast to string and clean."""
    if val is None:
        return ""
    try:
        if isinstance(val, (list, dict)):
            val = str(val)
        return str(val).strip()
    except Exception:
        return ""

class CollapsibleThinkingCardSelfHealingGuard:
    """
    Feishu Card builder for thinking process with conclusion top,
    thinking process collapsed by default, and a 5-second undo (snapshot) mechanism.
    Zero-config fault tolerance: dirty data auto-heals, missing params default.
    """

    def __init__(self) -> None:
        self._snapshots: Dict[str, Tuple[Dict[str, Any], float]] = {}

    def build_card(
        self,
        conclusion: Optional[Any] = None,
        thinking_process: Optional[Any] = None,
        title: Optional[Any] = None,
        card_link: Optional[Any] = None,
        show_undo: bool = True
    ) -> Dict[str, Any]:
        """
        Builds the collapsible thinking card.
        Self-heals dirty data, ensures missing parameters have defaults.
        Injects an undo snapshot if `show_undo` is True.
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

        # 2. Build Elements
        elements = []

        # Conclusion section
        elements.append({
            "tag": "markdown",
            "content": f"**结论：**\n{safe_conclusion}"
        })

        # Thinking process section (collapsible)
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

        # Base Card Structure
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

        # 3. Snapshot & Undo Injection
        if show_undo:
            snapshot_id = str(uuid.uuid4())
            # Save snapshot with current timestamp
            # Make sure we store a deep enough copy or recreate it if we were modifying in place.
            # Here we just store the dict representing the card without undo button for pure restore.
            card_snapshot = dict(card)
            card_snapshot["elements"] = list(elements)
            self._snapshots[snapshot_id] = (card_snapshot, time.time())

            # Append the Undo button
            card["elements"].append({
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
                            "action": "undo",
                            "snapshot_id": snapshot_id
                        }
                    }
                ]
            })

        return card

    def undo(self, snapshot_id: str, current_time: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Attempts to undo a card generation within a 5-second window.
        Returns the snapshot dictionary if successful, or None if expired or invalid.
        """
        if snapshot_id not in self._snapshots:
            return None

        snapshot, timestamp = self._snapshots[snapshot_id]

        if current_time is None:
            current_time = time.time()

        if current_time - timestamp > 5.0:
            # Clean up expired snapshot
            del self._snapshots[snapshot_id]
            return None

        # Optional: remove from snapshots after successful undo
        del self._snapshots[snapshot_id]
        return snapshot
