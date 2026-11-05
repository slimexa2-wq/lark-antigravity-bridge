import collections
import concurrent.futures
import threading
import logging
from typing import List, Callable, Any, Dict, Union

class LRUIdempotencyGuard:
    def __init__(self, max_size: int = 10000):
        # 缺参自动设合理默认值
        self.max_size = max_size if (max_size is not None and max_size > 0) else 10000
        self.cache = collections.OrderedDict()
        self.lock = threading.Lock()

    def check_and_mark(self, event_id: str) -> bool:
        """Returns True if already seen (duplicate), False if it's new."""
        if not event_id:
            return False

        with self.lock:
            if event_id in self.cache:
                self.cache.move_to_end(event_id)
                return True
            self.cache[event_id] = True
            # LRU eviction
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
            return False


class PipelineRun:
    """进度快照与零阻塞结果汇总"""
    def __init__(self, total: int):
        self.total = total
        self.processed = 0
        self.skipped = 0
        self.failed = 0
        self.results = []
        self.lock = threading.Lock()
        self._done_event = threading.Event()
        if total == 0:
            self._done_event.set()

    def update_progress(self, status: str, result: Any):
        with self.lock:
            if status == "skipped":
                self.skipped += 1
            elif status == "processed":
                self.processed += 1
                if result is not None:
                    self.results.append(result)
            elif status == "failed":
                self.failed += 1

            if self.processed + self.skipped + self.failed >= self.total:
                self._done_event.set()

    def snapshot(self) -> Dict[str, Any]:
        """Provides a non-blocking snapshot of current progress."""
        with self.lock:
            return {
                "total": self.total,
                "processed": self.processed,
                "skipped": self.skipped,
                "failed": self.failed,
                "completed": self.processed + self.skipped + self.failed,
                "is_done": self._done_event.is_set()
            }

    def wait(self, timeout: float = None) -> Dict[str, Any]:
        """Blocks until processing is complete and returns final results."""
        self._done_event.wait(timeout)
        with self.lock:
            return {
                "total": self.total,
                "processed": self.processed,
                "skipped": self.skipped,
                "failed": self.failed,
                "results": list(self.results)
            }


class EventBatchPipeline:
    """支持单次拖入10~1000条记录的批量流式处理、高吞吐批量流水线与并发加速封装"""
    def __init__(self, guard_capacity: int = 10000, max_workers: int = 20):
        # 零配置容错、缺参自动设合理默认值
        self.guard = LRUIdempotencyGuard(max_size=guard_capacity)
        self.max_workers = max_workers if (max_workers is not None and max_workers > 0) else 20
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)

    def extract_id(self, event: Any) -> str:
        """脏数据自愈，提取失败或者无 ID 的记录视作独立记录"""
        try:
            if isinstance(event, dict):
                val = event.get('event_id') or event.get('message_id')
                if val:
                    return str(val)
            elif hasattr(event, 'event_id') and event.event_id:
                return str(event.event_id)
            elif hasattr(event, 'message_id') and event.message_id:
                return str(event.message_id)
            elif isinstance(event, str):
                return event
        except Exception:
            pass
        return ""

    def process_batch_async(self, events: Union[List[Any], Any], processor_func: Callable) -> PipelineRun:
        """
        一键直达、零阻塞异步提交
        """
        if events is None:
            events = []
        elif not isinstance(events, (list, tuple)):
            events = [events]

        run = PipelineRun(total=len(events))
        if not events:
            return run

        def _worker_func(event):
            event_id = self.extract_id(event)

            # Idempotency Guard (防重放跑两遍)
            if event_id and self.guard.check_and_mark(event_id):
                run.update_progress("skipped", None)
                return

            try:
                res = processor_func(event)
                run.update_progress("processed", res)
            except Exception as e:
                logging.warning(f"Event pipeline processing failed for {event_id}: {e}")
                run.update_progress("failed", e)

        for ev in events:
            self.executor.submit(_worker_func, ev)

        return run

    def process_batch(self, events: Union[List[Any], Any], processor_func: Callable) -> Dict[str, Any]:
        """
        同步结果汇总
        """
        run = self.process_batch_async(events, processor_func)
        return run.wait()
