import concurrent.futures
from typing import List, Dict, Any, Optional

class ApprovalOneTapCallbackBatchPipeline:
    """
    Pipeline for batch processing Approval One-Tap Callback data.
    Provides robust defaults, dirty data self-healing, and high-throughput execution.
    """

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self._validate_config()

    def _validate_config(self):
        if not isinstance(self.max_workers, int) or self.max_workers <= 0:
            self.max_workers = 10

    def _heal_record(self, record: Any) -> Dict[str, Any]:
        """
        Self-heals and normalizes input records to ensure processing resilience.
        """
        if not isinstance(record, dict):
            return {"status": "error", "error_msg": "Invalid record format", "raw": record}

        healed = record.copy()

        # Default defaults and robust checks
        if "action" not in healed or healed.get("action") not in ("approve", "reject"):
            healed["action"] = "unknown"

        if "card_id" not in healed or not isinstance(healed.get("card_id"), str):
            healed["card_id"] = "default_missing_id"

        return healed

    def _process_single(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a single callback record.
        """
        healed_record = self._heal_record(record)

        if healed_record.get("status") == "error":
            return healed_record

        if healed_record["action"] == "unknown":
            return {
                "card_id": healed_record["card_id"],
                "status": "error",
                "error_msg": "Unknown or missing action"
            }

        return {
            "card_id": healed_record["card_id"],
            "status": "success",
            "action_taken": healed_record["action"]
        }

    def process_batch(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes a batch of 10~1000 records concurrently.
        """
        if not isinstance(records, list):
            return {"status": "error", "error_msg": "Input must be a list of records."}

        # Though the requirement says 10~1000, we gracefully handle any length list.
        if not records:
            return {"status": "success", "results": [], "summary": {"total": 0, "success": 0, "error": 0}}

        results = []
        success_count = 0
        error_count = 0

        # Concurrent processing for high throughput
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Using map to preserve order if needed, or submit for raw performance.
            future_to_record = {executor.submit(self._process_single, rec): rec for rec in records}

            for future in concurrent.futures.as_completed(future_to_record):
                try:
                    result = future.result()
                    results.append(result)
                    if result.get("status") == "success":
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    # Extreme edge case resilience
                    error_count += 1
                    results.append({"status": "error", "error_msg": str(e)})

        return {
            "status": "success",
            "results": results,
            "summary": {
                "total": len(records),
                "success": success_count,
                "error": error_count
            }
        }
