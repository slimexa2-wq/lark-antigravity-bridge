import time
import re
import uuid
from typing import Optional, Dict, Any

class AttachmentAutoRouterSelfHealingGuard:
    """
    A robust guard class that routes attachments to specific business engines:
    - 周报 (Weekly Report)
    - 提成 (Commission)
    - 标书 (Bidding)
    - 漫剧 (Comic)

    It supports:
    1. Silent self-healing of dirty data (e.g., non-strings, missing extensions, control characters).
    2. Default fallbacks for missing parameters (None inputs).
    3. A lightweight 5-second one-tap undo (snapshot) mechanism.
    4. No interruption to users (no exceptions raised for bad inputs, only silent healing).
    """

    def __init__(self):
        # Store snapshots for undo functionality.
        # Key: file_id or generated task_id
        # Value: Dict containing routing result, original data, and timestamp.
        self._snapshots: Dict[str, Dict[str, Any]] = {}
        self.UNDO_WINDOW_SECONDS = 5.0

    def _heal_text(self, text: Any) -> str:
        """Silently heal dirty data, convert to string, remove control characters."""
        if text is None:
            return ""
        if not isinstance(text, str):
            text = str(text)
        # Remove non-printable control characters, but keep newlines/spaces
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        return text.strip()

    def process_and_route(
        self,
        file_id: Optional[str] = None,
        file_name: Optional[str] = None,
        file_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Processes the input, heals dirty data, routes to the appropriate engine,
        and saves a snapshot for possible undo.
        """
        # 1. Parameter fallback & healing
        safe_file_id = self._heal_text(file_id) if file_id else str(uuid.uuid4())
        safe_file_name = self._heal_text(file_name)
        safe_file_content = self._heal_text(file_content)

        safe_metadata = metadata if isinstance(metadata, dict) else {}

        # Self-heal missing extensions for known file types by analyzing content (mock approach for simplicity)
        if not "." in safe_file_name:
            if "excel" in safe_file_content.lower() or "xls" in safe_file_content.lower():
                safe_file_name += ".xlsx"
            elif "word" in safe_file_content.lower() or "doc" in safe_file_content.lower():
                safe_file_name += ".docx"
            else:
                safe_file_name += ".txt"

        # 2. Extract routing signals
        search_text = f"{safe_file_name} {safe_file_content}"

        title = self._heal_text(safe_metadata.get('title', ''))
        desc = self._heal_text(safe_metadata.get('description', ''))

        search_text += f" {title} {desc}"
        search_text_lower = search_text.lower()

        # 3. Routing Rules
        target_engine = "UNKNOWN_ENGINE"

        if re.search(r'周报|weekly|汇报|report', search_text_lower):
            target_engine = "WEEKLY_REPORT_ENGINE"
        elif re.search(r'提成|commission|奖金|bonus', search_text_lower):
            target_engine = "COMMISSION_ENGINE"
        elif re.search(r'标书|bidding|投标|bid', search_text_lower):
            target_engine = "BIDDING_ENGINE"
        elif re.search(r'漫剧|comic|漫画|manga|anime', search_text_lower):
            target_engine = "COMIC_ENGINE"

        # 4. Save snapshot
        timestamp = time.time()
        result = {
            "task_id": safe_file_id,
            "engine": target_engine,
            "healed_file_name": safe_file_name,
            "timestamp": timestamp,
            "status": "routed"
        }

        self._snapshots[safe_file_id] = result.copy()

        return result

    def undo(self, task_id: str) -> Dict[str, Any]:
        """
        Attempts to undo a routing task.
        Returns success status and message.
        """
        if task_id not in self._snapshots:
            return {"success": False, "message": "Task ID not found."}

        snapshot = self._snapshots[task_id]
        current_time = time.time()

        if current_time - snapshot["timestamp"] <= self.UNDO_WINDOW_SECONDS:
            # Within window, perform undo
            snapshot["status"] = "undone"
            return {"success": True, "message": "Undo successful."}
        else:
            # Past window
            return {"success": False, "message": "Undo time window expired."}
