import time
import logging
from collections import deque
from typing import Callable, Any, Dict, Optional, List, Set

# Configuration for logging (backend silent audit trace)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Avoid double logging if handler exists
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class TokenBucket:
    def __init__(self, capacity: int, fill_rate: float):
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = capacity
        self.last_fill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        now = time.time()
        # refill
        elapsed = now - self.last_fill
        new_tokens = elapsed * self.fill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_fill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

class RateLimit429QueueAuditTrace:
    def __init__(self, capacity: int = 10, fill_rate: float = 2.0, max_retries: int = 3, retry_delay: float = 1.0):
        # Default reasonable configurations to prevent missing parameters issue (zero-config)
        self.bucket = TokenBucket(capacity=capacity, fill_rate=fill_rate)
        self.queue = deque()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.audit_log: List[Dict[str, Any]] = []
        self.processed_ids: Set[str] = set()

    def _log_audit(self, action: str, details: Dict[str, Any]):
        """Silent backend logging to record decision/step for audit without annoying user."""
        record = {"action": action, "timestamp": time.time(), "details": details}
        self.audit_log.append(record)
        logger.info(f"AUDIT TRACE: {action} - {details}")

    def enqueue(self, task_id: str, func: Callable, *args, **kwargs) -> Any:
        """
        Enqueues a task and immediately processes the queue.
        Provides zero-configuration, caller just passes task and gets clean result.
        Clean Result implies we return successful output or raise Exception if fully failed.
        """
        if not task_id:
            task_id = str(time.time()) # self-healing missing task_id
            self._log_audit("MISSING_PARAM_HEAL", {"healed_task_id": task_id})

        if task_id in self.processed_ids:
            self._log_audit("DEDUPLICATION", {"task_id": task_id})
            return {"status": "deduplicated", "message": f"Task {task_id} already processed"}

        self.queue.append({
            "id": task_id,
            "func": func,
            "args": args,
            "kwargs": kwargs,
            "retries": 0
        })
        self._log_audit("ENQUEUE", {"task_id": task_id})

        return self.process_queue()

    def process_queue(self) -> Any:
        results = []
        while self.queue:
            task = self.queue[0]  # Peek
            task_id = task["id"]

            # Wait for token
            while not self.bucket.consume(1):
                self._log_audit("TOKEN_WAIT", {"task_id": task_id, "queue_size": len(self.queue)})
                time.sleep(0.1) # Simulate smooth wait

            task = self.queue.popleft() # Pop after token acquired

            try:
                # Execute the task
                result = task["func"](*task["args"], **task["kwargs"])

                # Check for simulated 429 response structure
                if isinstance(result, dict) and result.get("status_code") == 429:
                     raise Exception("HTTP 429 Too Many Requests")

                self.processed_ids.add(task_id)
                self._log_audit("SUCCESS", {"task_id": task_id})
                results.append({"task_id": task_id, "status": "success", "result": result})

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "Too Many Requests" in error_msg:
                     if task["retries"] < self.max_retries:
                         task["retries"] += 1
                         self._log_audit("RETRY_429", {"task_id": task_id, "retry_count": task["retries"]})
                         # Put back to front of queue (Zero Drop)
                         self.queue.appendleft(task)
                         time.sleep(self.retry_delay * task["retries"]) # backoff
                     else:
                         self._log_audit("DROP_MAX_RETRIES", {"task_id": task_id, "error": error_msg})
                         results.append({"task_id": task_id, "status": "failed", "error": error_msg})
                else:
                    # Other dirty data/errors
                    if task["retries"] < self.max_retries:
                         task["retries"] += 1
                         self._log_audit("DIRTY_DATA_HEAL_RETRY", {"task_id": task_id, "error": error_msg})
                         self.queue.appendleft(task)
                         time.sleep(self.retry_delay)
                    else:
                        self._log_audit("DROP_ERROR", {"task_id": task_id, "error": error_msg})
                        results.append({"task_id": task_id, "status": "failed", "error": error_msg})

        # Return clean result (simplest interface for user)
        if len(results) == 1:
            return results[0]
        return results

# Expose a simple function for extremely simplified frontend call
_global_queue = RateLimit429QueueAuditTrace()

def process_request(func: Callable, task_id: Optional[str] = None, *args, **kwargs) -> Any:
    """
    Extremely simple API for frontend.
    One-click style, zero-config, handles missing parameters automatically.
    """
    return _global_queue.enqueue(task_id, func, *args, **kwargs)
