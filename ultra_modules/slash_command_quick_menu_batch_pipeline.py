import asyncio
import time
from typing import List, Dict, Any, Optional

# Supported slash commands
SUPPORTED_COMMANDS = {"/周报", "/提成", "/漫剧", "/标书", "/状态"}

class ProgressSnapshot:
    """Snapshot for batch pipeline progress."""
    def __init__(self, total: int):
        self.total = total
        self.processed = 0
        self.success = 0
        self.failed = 0
        self.start_time = time.time()
        self.end_time = None
        self.results = []
        self.errors = []

    @property
    def is_completed(self) -> bool:
        return self.processed == self.total

    def get_progress(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "processed": self.processed,
            "success": self.success,
            "failed": self.failed,
            "is_completed": self.is_completed,
            "duration": (self.end_time or time.time()) - self.start_time
        }


class SlashCommandBatchRouter:
    """
    Router and pipeline for batch processing slash command payloads.
    Supports asynchronous execution, progress tracking, fallback defaults, and self-healing.
    """

    def __init__(self, batch_size_limit: int = 1000):
        self.batch_size_limit = batch_size_limit

    async def _process_single(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single record, including dirty data self-healing and missing parameter fallback.
        """
        # Missing parameter fallback & Dirty data self-healing
        if not isinstance(record, dict):
            record = {"raw_data": str(record)}

        command = record.get("command", "/状态")  # default fallback
        if command not in SUPPORTED_COMMANDS:
            command = "/状态" # fallback for invalid command

        payload = record.get("payload", {})
        if not isinstance(payload, dict):
            payload = {"content": str(payload)} # self heal payload

        # Simulate async processing time
        await asyncio.sleep(0.001)

        return {
            "status": "success",
            "command": command,
            "processed_payload": payload,
            "timestamp": time.time()
        }

    async def process_batch_async(self, records: List[Dict[str, Any]], snapshot: ProgressSnapshot) -> None:
        """
        Processes a batch of records asynchronously and updates the progress snapshot.
        """
        tasks = []
        for record in records:
            tasks.append(self._process_single(record))

        # We can run these concurrently for high throughput
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            snapshot.processed += 1
            if isinstance(res, Exception):
                snapshot.failed += 1
                snapshot.errors.append(str(res))
            else:
                snapshot.success += 1
                snapshot.results.append(res)

        snapshot.end_time = time.time()


    def trigger_batch(self, records: List[Any]) -> ProgressSnapshot:
        """
        Entry point to trigger batch processing. Returns a ProgressSnapshot immediately.
        Limits the records to batch_size_limit.
        """
        # Ensure we have a list
        if not isinstance(records, list):
            records = [records]

        # Enforce batch limits
        records = records[:self.batch_size_limit]

        # Self heal empty batch
        if not records:
            records = [{"command": "/状态", "payload": {}}]

        snapshot = ProgressSnapshot(total=len(records))

        # In a real async web framework (like FastAPI or Sanic), we'd use `asyncio.create_task`
        # and return the snapshot immediately.
        # For simplicity in this script (and unittests), we'll spin up an event loop if not running,
        # or use the existing one if running.

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.process_batch_async(records, snapshot))
        except RuntimeError:
            # No running event loop, this means we are in synchronous context.
            # To simulate non-blocking in a purely sync script, one might use a thread.
            # But asyncio.run blocks. We use a thread to keep it truly non-blocking.
            import threading
            def run_in_thread():
                asyncio.run(self.process_batch_async(records, snapshot))
            thread = threading.Thread(target=run_in_thread)
            thread.start()

        return snapshot
