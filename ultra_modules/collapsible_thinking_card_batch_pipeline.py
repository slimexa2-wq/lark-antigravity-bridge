import concurrent.futures
import threading
import uuid
from typing import List, Dict, Any, Optional

class ThinkingCardBuilder:
    """
    Builder for Lark/Feishu interactive cards.
    Follows rules: conclusion fixed at top (max 3 lines), reasoning inside default-collapsed panel, one-click undo button.
    """
    @staticmethod
    def build_card(conclusion: Optional[str] = None, reasoning: Optional[str] = None, record_id: Optional[str] = None) -> Dict[str, Any]:
        # Handle defaults and dirty data self-healing
        conclusion = str(conclusion) if conclusion is not None else "Default Conclusion"
        reasoning = str(reasoning) if reasoning is not None else "Default Reasoning"
        record_id = str(record_id) if record_id is not None else str(uuid.uuid4())

        # Prevent mobile screen flooding: limit core summaries to a maximum of 3 lines
        conclusion_lines = conclusion.split('\n')
        if len(conclusion_lines) > 3:
            conclusion = '\n'.join(conclusion_lines[:3]) + '...'

        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "Reasoning Result"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**Conclusion:**\n{conclusion}"
                    }
                },
                {
                    "tag": "collapsible_panel",
                    "is_collapsed": True,
                    "title": {
                        "tag": "plain_text",
                        "content": "Thinking Process"
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": reasoning
                        }
                    ]
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "Undo"
                            },
                            "type": "danger",
                            "value": {
                                "action": "undo",
                                "record_id": record_id
                            }
                        }
                    ]
                }
            ]
        }
        return card

class BatchPipeline:
    """
    High-throughput batch pipeline with concurrent processing, self-healing, and progress snapshots.
    Supports single-time drop of 10~1000 records.
    """
    def __init__(self, max_workers: int = 20):
        self.max_workers = max_workers
        self.snapshots: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def process_record(self, record: Any) -> Dict[str, Any]:
        # Dirty data self-healing: if not dict, wrap it
        if not isinstance(record, dict):
            record = {"raw_data": record}

        conclusion = record.get("conclusion")
        reasoning = record.get("reasoning")
        record_id = record.get("record_id", str(uuid.uuid4()))

        try:
            card = ThinkingCardBuilder.build_card(conclusion, reasoning, record_id)
            return {"record_id": record_id, "status": "success", "card": card}
        except Exception as e:
            # Fallback for extreme errors
            return {"record_id": record_id, "status": "error", "error": str(e)}

    def run_batch(self, batch_id: str, records: List[Any]) -> Dict[str, Any]:
        if not records:
            # Missing param default fallback / zero records boundary
            self._update_snapshot(batch_id, {"status": "completed", "progress": 100, "total": 0, "completed": 0})
            return {"batch_id": batch_id, "status": "completed", "results": []}

        # Boundary: Cap at 1000 records per requirement
        if len(records) > 1000:
            records = records[:1000]

        results = []
        completed = 0
        total = len(records)

        self._update_snapshot(batch_id, {"status": "running", "progress": 0, "total": total, "completed": 0})

        # Non-blocking result aggregation conceptually via ThreadPoolExecutor which runs concurrently.
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_record = {executor.submit(self.process_record, r): r for r in records}
            for future in concurrent.futures.as_completed(future_to_record):
                res = future.result()
                results.append(res)
                completed += 1
                self._update_snapshot(batch_id, {
                    "status": "running",
                    "progress": (completed / total) * 100,
                    "total": total,
                    "completed": completed
                })

        self._update_snapshot(batch_id, {"status": "completed", "progress": 100, "total": total, "completed": total})
        return {"batch_id": batch_id, "status": "completed", "results": results}

    def run_batch_async(self, batch_id: str, records: List[Any]) -> threading.Thread:
        """
        Runs the batch in a background thread for true non-blocking behavior.
        """
        # Ensure snapshot is initialized before returning
        self._update_snapshot(batch_id, {"status": "running", "progress": 0, "total": len(records) if records else 0, "completed": 0})
        thread = threading.Thread(target=self.run_batch, args=(batch_id, records))
        thread.start()
        return thread

    def _update_snapshot(self, batch_id: str, state: Dict[str, Any]) -> None:
        with self._lock:
            self.snapshots[batch_id] = state

    def get_snapshot(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the current progress snapshot.
        """
        with self._lock:
            return self.snapshots.get(batch_id)
