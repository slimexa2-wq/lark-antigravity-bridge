import time
import uuid
import re

class VoiceIntentSelfHealingGuard:
    """
    Zero-config intent extractor for voice messages with self-healing and one-tap undo.
    Features:
    - Silent cleaning of dirty data (filler words, punctuation).
    - Sensible defaults for missing parameters.
    - 5-second lightweight snapshot mechanism for one-tap undo.
    """

    def __init__(self):
        self.snapshots = {}
        self.UNDO_WINDOW = 5.0 # 5 seconds

    def _clean_text(self, text):
        if text is None:
            return ""
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                return ""

        # Silently clean dirty data (filler words, punctuations)
        filler_words = r'(呃|那个|这个|然后|就是|啊|呢|吧|嗯|哦|哈|啦|哎)'
        cleaned_text = re.sub(filler_words, '', text)
        cleaned_text = re.sub(r'[^\w\s]', '', cleaned_text).strip()
        return cleaned_text

    def extract_intent(self, text, default_intent="UNKNOWN"):
        """
        Extracts intent with fallback defaults. Records a snapshot.
        """
        cleaned = self._clean_text(text)

        intent = default_intent
        entities = {}

        if cleaned:
            # Rule-based intent extraction
            verify_keywords = ["核对", "核", "提成表", "报表", "文件", "审核", "核一下", "对一下", "核算"]

            for kw in verify_keywords:
                if kw in cleaned:
                    intent = "VERIFY_DOCUMENT"

            for kw in ["提成表", "报表", "文件"]:
                if kw in cleaned:
                    entities["document_type"] = kw
                    break

        # Generate task ID for snapshot
        task_id = str(uuid.uuid4())

        # Save snapshot
        self.snapshots[task_id] = {
            "timestamp": time.time(),
            "original_text": text,
            "intent": intent,
            "entities": entities,
            "status": "active"
        }

        return {
            "task_id": task_id,
            "intent": intent,
            "entities": entities
        }

    def undo_task(self, task_id):
        """
        One-tap undo mechanism. Silently handles invalid task IDs or expiration.
        """
        if not task_id or not isinstance(task_id, str):
            return {"status": "failed", "reason": "invalid_task_id"}

        snapshot = self.snapshots.get(task_id)

        if not snapshot:
            return {"status": "failed", "reason": "not_found"}

        # Check expiration
        if time.time() - snapshot["timestamp"] > self.UNDO_WINDOW:
            snapshot["status"] = "expired"
            return {"status": "failed", "reason": "expired"}

        # Undo logic (e.g., mark as cancelled)
        snapshot["status"] = "cancelled"

        return {"status": "success", "task_id": task_id}
