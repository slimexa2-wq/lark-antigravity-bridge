import json
from collections import OrderedDict
from datetime import datetime
from typing import Dict, Any, Optional

class IdempotencyExplainer:
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._pool: OrderedDict = OrderedDict()

    def process_event(self, event_id: Any, message_id: Any = "") -> Dict[str, Any]:
        """
        Process an event and return a plain language explanation of whether it was processed or skipped.
        Handles dirty data by assigning fallback IDs.
        """
        # Handle dirty data
        clean_event_id = str(event_id).strip() if event_id is not None else ""
        clean_message_id = str(message_id).strip() if message_id is not None else ""

        if not clean_event_id:
            if clean_message_id:
                clean_event_id = f"fallback_evt_{clean_message_id}"
            else:
                clean_event_id = f"unknown_evt_{datetime.now().timestamp()}"

        is_duplicate = clean_event_id in self._pool

        if not is_duplicate:
            # Add to LRU cache
            self._pool[clean_event_id] = {
                "message_id": clean_message_id,
                "timestamp": datetime.now().isoformat()
            }
            # Evict if over size
            if len(self._pool) > self.max_size:
                self._pool.popitem(last=False)

            status = "新事件"
            action = "允许处理"
            description = "这是一个新的事件，系统已经记录并准备进行后续处理。"
        else:
            # Move to end to mark as recently used
            self._pool.move_to_end(clean_event_id)

            status = "重复事件"
            action = "拦截阻断"
            description = "这个事件系统之前已经处理过了，为了防止重复执行，系统已自动将其拦截。"

        result = {
            "event_id": clean_event_id,
            "status": status,
            "action": action,
            "description": description,
            "timestamp": datetime.now().isoformat()
        }

        return result

    def generate_cards(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate HTML, Markdown, and JSON cards based on the processing result.
        """
        json_card = json.dumps(result, ensure_ascii=False, indent=2)

        md_card = f"""### 🛡️ 事件幂等处理卡片
- **事件ID**: `{result['event_id']}`
- **当前状态**: **{result['status']}**
- **系统动作**: **{result['action']}**
- **大白话解读**: {result['description']}
- **处理时间**: `{result['timestamp']}`
"""

        color = "green" if result["status"] == "新事件" else "red"
        html_card = f"""<div style="border: 1px solid #ccc; padding: 15px; border-radius: 8px; font-family: sans-serif; max-width: 400px;">
    <h3 style="margin-top: 0; color: #333;">🛡️ 事件幂等处理卡片</h3>
    <p><strong>事件ID:</strong> <code>{result['event_id']}</code></p>
    <p><strong>当前状态:</strong> <span style="color: {color}; font-weight: bold;">{result['status']}</span></p>
    <p><strong>系统动作:</strong> <strong>{result['action']}</strong></p>
    <p style="background: #f9f9f9; padding: 10px; border-left: 4px solid {color};">{result['description']}</p>
    <p style="font-size: 0.8em; color: #888;">处理时间: {result['timestamp']}</p>
</div>"""

        return {
            "json": json_card,
            "markdown": md_card,
            "html": html_card,
            "raw_result": result
        }

    def get_summary(self) -> Dict[str, Any]:
        return {
            "pool_size": len(self._pool),
            "max_size": self.max_size,
            "latest_events": list(self._pool.keys())[-5:]
        }


# Zero-config global instance and functions
_global_explainer = IdempotencyExplainer(max_size=1000)

def explain_event_idempotency(event_id: Optional[Any] = None, message_id: Optional[Any] = None) -> Dict[str, Any]:
    """
    极简调用的全局入口：处理事件并返回可直接供业务人员查看的卡片（包含 json/markdown/html 格式）。
    """
    result = _global_explainer.process_event(event_id, message_id)
    return _global_explainer.generate_cards(result)

def get_pool_summary() -> Dict[str, Any]:
    """
    获取当前全局幂等池的摘要状态。
    """
    return _global_explainer.get_summary()
