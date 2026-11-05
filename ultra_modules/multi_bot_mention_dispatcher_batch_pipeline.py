import concurrent.futures
import time
from typing import List, Dict, Any, Optional

class MultiBotMentionDispatcher:
    """
    Dispatcher for processing multiple bot mentions in a batch.
    Supports high throughput via ThreadPoolExecutor.
    """

    # Supported bots for quick matching
    SUPPORTED_BOTS = {"@大肥鱼", "@招聘", "@数据", "@量化"}

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers

    def _clean_record(self, record: Any) -> str:
        """
        Auto-heal dirty data.
        Converts inputs to string safely.
        """
        if record is None:
            return ""
        if isinstance(record, dict):
            # Try to extract text if it's a dict, fallback to str(dict)
            return str(record.get('text', record.get('content', record)))
        return str(record).strip()

    def _extract_mentions(self, text: str) -> List[str]:
        """
        Extract mentions from the text.
        Looks for patterns like @大肥鱼 etc.
        """
        if not text:
            return []

        # Simple extraction looking for standard bots
        mentions = []
        for bot in self.SUPPORTED_BOTS:
            if bot in text:
                mentions.append(bot)

        return mentions

    def _process_single_record(self, record: Any) -> Dict[str, Any]:
        """
        Process a single record.
        """
        start_time = time.time()

        cleaned_text = self._clean_record(record)
        mentions = self._extract_mentions(cleaned_text)

        elapsed = time.time() - start_time

        # Determine status
        status = "success" if cleaned_text else "ignored_empty"

        return {
            "original_record_type": type(record).__name__,
            "cleaned_text": cleaned_text,
            "mentions": mentions,
            "status": status,
            "processing_time_ms": round(elapsed * 1000, 2)
        }

    def dispatch_batch(self, records: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Process a batch of records concurrently.
        Zero-blocking execution, fast turnaround, zero-config default.
        """
        if records is None:
            records = []

        if not isinstance(records, (list, tuple)):
            # Fallback for single item accidentally passed without list
            records = [records]

        start_time = time.time()
        results = []

        # Zero-blocking execution via ThreadPoolExecutor
        if records:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Map preserves order
                results = list(executor.map(self._process_single_record, records))

        total_time = time.time() - start_time

        # Summary Card (Progress snapshot & Result)
        success_count = sum(1 for r in results if r["status"] == "success")
        empty_count = sum(1 for r in results if r["status"] == "ignored_empty")

        mention_counts = {}
        for r in results:
            for m in r["mentions"]:
                mention_counts[m] = mention_counts.get(m, 0) + 1

        card_format = {
            "batch_summary": {
                "total_records": len(records),
                "processed_successfully": success_count,
                "ignored_empty": empty_count,
                "total_time_ms": round(total_time * 1000, 2),
                "throughput_rps": round(len(records) / (total_time if total_time > 0 else 0.001), 2)
            },
            "mention_statistics": mention_counts,
            "results_snapshot": results
        }

        return card_format
