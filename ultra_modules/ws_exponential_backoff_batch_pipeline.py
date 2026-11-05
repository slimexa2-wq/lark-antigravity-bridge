import asyncio
import random
import logging
from typing import List, Dict, Any, Callable, Awaitable, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ws_pipeline")

class ExponentialBackoffJitter:
    def __init__(self, base_ms: int = 100, max_ms: int = 10000, max_retries: int = 5):
        self.base_ms = base_ms
        self.max_ms = max_ms
        self.max_retries = max_retries
        self.retries = 0

    def get_delay_and_increment(self) -> float:
        if self.retries >= self.max_retries:
            return -1.0

        delay = min(self.max_ms, self.base_ms * (2 ** self.retries))
        jitter = random.uniform(0, delay * 0.1)  # 10% jitter
        self.retries += 1
        return (delay + jitter) / 1000.0

    def reset(self):
        self.retries = 0

class WSPipelineStateMachine:
    def __init__(
        self,
        task: Callable[[Any], Awaitable[Any]],
        max_retries: int = 5,
        base_delay_ms: int = 100
    ):
        self.task = task
        self.backoff = ExponentialBackoffJitter(base_ms=base_delay_ms, max_retries=max_retries)
        self.state = "IDLE"

    async def execute(self, payload: Any) -> Dict[str, Any]:
        self.state = "PROCESSING"
        self.backoff.reset()

        while True:
            try:
                result = await self.task(payload)
                self.state = "SUCCESS"
                return {"status": "success", "data": result, "payload": payload}
            except Exception as e:
                self.state = "RETRIABLE_ERROR"
                delay = self.backoff.get_delay_and_increment()
                if delay < 0:
                    self.state = "FAILED"
                    logger.warning(f"Task failed permanently for payload {payload}: {e}")
                    return {"status": "failed", "error": str(e), "payload": payload}

                logger.debug(f"Retrying task for payload {payload} in {delay:.2f}s due to: {e}")
                await asyncio.sleep(delay)

class WSBatchPipeline:
    def __init__(
        self,
        process_func: Callable[[Any], Awaitable[Any]],
        batch_size: int = 50,
        max_retries: int = 5,
        base_delay_ms: int = 100
    ):
        self.process_func = process_func
        # Provide reasonable defaults if initialized with weird values
        self.batch_size = batch_size if batch_size and batch_size > 0 else 50
        self.max_retries = max_retries if max_retries is not None and max_retries >= 0 else 5
        self.base_delay_ms = base_delay_ms if base_delay_ms is not None and base_delay_ms > 0 else 100

        self.completed = 0
        self.total = 0
        self.results: List[Dict[str, Any]] = []

    async def process_items(self, items: List[Any]) -> Dict[str, Any]:
        if not items:
            return {"status": "success", "processed": 0, "results": []}

        self.total = len(items)
        self.completed = 0
        self.results = []

        # Process in batches
        for i in range(0, self.total, self.batch_size):
            batch = items[i:i + self.batch_size]
            tasks = []
            for item in batch:
                sm = WSPipelineStateMachine(
                    task=self.process_func,
                    max_retries=self.max_retries,
                    base_delay_ms=self.base_delay_ms
                )
                tasks.append(sm.execute(item))

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in batch_results:
                if isinstance(res, Exception):
                    # Should be caught by StateMachine, but just in case
                    self.results.append({"status": "failed", "error": str(res)})
                else:
                    self.results.append(res)

            self.completed += len(batch)

        return {
            "status": "success",
            "processed": self.completed,
            "results": self.results
        }

    def get_progress_snapshot(self) -> Dict[str, Any]:
        return {
            "completed": self.completed,
            "total": self.total,
            "percentage": (self.completed / self.total * 100) if self.total > 0 else 100
        }
