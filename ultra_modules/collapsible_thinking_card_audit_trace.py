import json
import difflib
import time
from typing import Any, Dict, List, Optional, Tuple

class CollapsibleThinkingCardAuditTrace:
    """
    Builder for a collapsible thinking Feishu card with an audit trace.
    Features:
    1. conclusion pinned to the top.
    2. thinking process collapsible (default collapsed).
    3. undo button (optional).
    4. audit log tracking data changes (dirty data self-healing and missing parameters).
    """

    def __init__(self):
        self.audit_log: List[Dict[str, Any]] = []

    def _generate_diff(self, original: str, cleaned: str) -> str:
        """Generates a diff between original and cleaned text."""
        diff = difflib.ndiff(original.splitlines(), cleaned.splitlines())
        return "\n".join(diff)

    def _record_audit(self, field: str, original: Any, cleaned: str, reason: str) -> None:
        """Records an audit log entry for data transformations."""
        original_str = ""
        try:
            original_str = str(original)
        except Exception:
            original_str = "<unstringable>"

        self.audit_log.append({
            "timestamp": time.time(),
            "field": field,
            "reason": reason,
            "diff": self._generate_diff(original_str, cleaned)
        })

    def _clean_string(self, val: Any, field_name: str, default_val: str) -> str:
        """Safely cast to string, clean it, and provide default if missing."""
        if val is None:
            self._record_audit(field_name, val, default_val, "missing parameter")
            return default_val

        try:
            val_str = str(val)
        except Exception:
            self._record_audit(field_name, "<unstringable>", default_val, "unstringable object")
            return default_val

        cleaned_str = val_str.strip()

        if not cleaned_str:
            self._record_audit(field_name, val_str, default_val, "empty string")
            return default_val

        if cleaned_str != val_str:
            self._record_audit(field_name, val_str, cleaned_str, "dirty data cleaned")

        return cleaned_str

    def build_card(
        self,
        conclusion: Optional[Any] = None,
        thinking_process: Optional[Any] = None,
        title: Optional[Any] = None,
        card_link: Optional[Any] = None,
        show_undo: bool = True
    ) -> Dict[str, Any]:
        """Builds a collapsible thinking Feishu card and logs audit trace."""
        self.audit_log.clear()

        safe_conclusion = self._clean_string(conclusion, "conclusion", "暂无结论")
        safe_thinking = self._clean_string(thinking_process, "thinking_process", "暂无推理过程")
        safe_title = self._clean_string(title, "title", "智能推理结果")
        safe_link = self._clean_string(card_link, "card_link", "")

        elements = []

        elements.append({
            "tag": "markdown",
            "content": f"**结论：**\n{safe_conclusion}"
        })

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

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Returns the audit log of transformations during the last build."""
        return self.audit_log
