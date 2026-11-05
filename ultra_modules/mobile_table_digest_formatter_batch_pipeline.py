import concurrent.futures
from typing import List, Dict, Any, Generator, Iterator


class MobileTableDigestFormatter:
    """
    Formatter to convert a wide table record into a mobile-friendly 3-line digest,
    highlight anomalies, and prepare an attachment download card.
    """

    def __init__(self):
        pass

    def format_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats a single record.
        - Limits to 3-line core summary.
        - Highlights anomalous items.
        - Adds full attachment download card.
        - Provides defaults for missing fields and self-heals dirty data.
        """
        if not isinstance(record, dict):
            record = {"raw_data": str(record)}

        title = str(record.get("title") or "Unnamed Report").strip()
        if not title:
            title = "Unnamed Report"

        status = str(record.get("status") or "unknown").strip().lower()

        # Self-heal metrics
        metrics = record.get("metrics")
        if not isinstance(metrics, dict):
            metrics = {}

        revenue = metrics.get("revenue")
        try:
            revenue = float(revenue) if revenue is not None else 0.0
        except (ValueError, TypeError):
            revenue = 0.0

        cost = metrics.get("cost")
        try:
            cost = float(cost) if cost is not None else 0.0
        except (ValueError, TypeError):
            cost = 0.0

        profit = revenue - cost

        # Highlight anomalies (e.g., negative profit or specific error status)
        is_anomaly = status in ["error", "failed", "exception"] or profit < 0

        # 3-line core summary
        # Line 1: Title and Status (with anomaly indicator)
        # Line 2: Revenue and Cost
        # Line 3: Profit

        status_display = f"[{status.upper()}]"
        if is_anomaly:
            status_display = f"🚨 {status_display}"

        line1 = f"{title} {status_display}"
        line2 = f"Rev: ${revenue:.2f} | Cost: ${cost:.2f}"
        line3 = f"Profit: ${profit:.2f}"
        if profit < 0:
            line3 += " ⚠️ LOSS"

        summary = f"{line1}\n{line2}\n{line3}"

        # Attachment download card
        attachment_url = str(record.get("attachment_url") or "https://fallback.example.com/default_attachment.pdf")

        formatted = {
            "original_id": record.get("id"),
            "summary": summary,
            "is_anomaly": is_anomaly,
            "attachment_card": {
                "title": f"Download Details: {title}",
                "url": attachment_url,
                "action": "click_to_download"
            },
            "mobile_ui_optimized": True
        }

        return formatted


class MobileTableDigestBatchPipeline:
    """
    High-throughput batch pipeline for processing multiple records concurrently.
    """

    def __init__(self, max_workers: int = 10):
        self.formatter = MobileTableDigestFormatter()
        self.max_workers = max_workers

    def process_batch(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of records concurrently.
        """
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Map maintains order
            processed = executor.map(self.formatter.format_record, records)
            results = list(processed)
        return results

    def process_batch_stream(self, records: List[Dict[str, Any]]) -> Generator[Dict[str, Any], None, None]:
        """
        Process records and yield results as they complete (streaming).
        Provides progress snapshots implicitly via the generator.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Using submit and as_completed for streaming out of order (faster for throughput)
            # but usually for a simple pipeline we might want order. Let's yield in order for consistency,
            # or yield as completed if order doesn't matter. The requirements say "streaming output with progress snapshots".
            # We'll yield as they complete to be truly non-blocking.
            future_to_record = {executor.submit(self.formatter.format_record, r): i for i, r in enumerate(records)}

            completed = 0
            total = len(records)

            for future in concurrent.futures.as_completed(future_to_record):
                try:
                    result = future.result()
                    completed += 1
                    # Inject progress snapshot
                    result["_pipeline_progress"] = {
                        "completed": completed,
                        "total": total,
                        "percent": round(completed / total * 100, 2) if total > 0 else 100.0
                    }
                    yield result
                except Exception as e:
                    # Self-heal pipeline failure
                    yield {
                        "summary": "🚨 Pipeline Error\nCould not process record\nFallback applied",
                        "is_anomaly": True,
                        "attachment_card": None,
                        "error": str(e),
                        "_pipeline_progress": {
                            "completed": completed + 1,
                            "total": total,
                            "percent": round((completed + 1) / total * 100, 2) if total > 0 else 100.0
                        }
                    }
                    completed += 1
