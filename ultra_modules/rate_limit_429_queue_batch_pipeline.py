import asyncio
import time
import logging
from typing import List, Callable, Any, Dict, Optional, Awaitable
from dataclasses import dataclass
import threading

logger = logging.getLogger(__name__)

class RateLimit429Exception(Exception):
    """Exception raised when HTTP 429 Too Many Requests is encountered."""
    pass

@dataclass
class ProgressSnapshot:
    total: int
    success: int
    failed: int
    pending: int
    retries: int

class RateLimit429QueueBatchPipeline:
    """
    飞书OpenAPI频控(HTTP 429)后台令牌桶平滑排队与零丢信重试队列
    高吞吐批量流水线与并发加速封装
    """
    def __init__(self,
                 process_func: Callable[[Any], Awaitable[Any]],
                 max_concurrency: int = 10,
                 tokens_per_second: float = 10.0,
                 max_retries: int = 3):
        # 缺参自动设合理默认值
        self.process_func = process_func
        self.max_concurrency = max_concurrency if max_concurrency is not None and max_concurrency > 0 else 10
        self.tokens_per_second = tokens_per_second if tokens_per_second is not None and tokens_per_second > 0 else 10.0
        self.max_retries = max_retries if max_retries is not None and max_retries >= 0 else 3

        self.tokens = self.tokens_per_second
        self.last_token_update = time.monotonic()

        self.results = []
        self.errors = []
        self.total = 0
        self.success_count = 0
        self.failed_count = 0
        self.retry_count = 0
        self._lock = None

    async def _consume_token(self):
        """后台令牌桶平滑排队"""
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_token_update
                self.tokens += elapsed * self.tokens_per_second
                if self.tokens > self.tokens_per_second:
                    self.tokens = self.tokens_per_second
                self.last_token_update = now

                if self.tokens >= 1:
                    self.tokens -= 1
                    return
            await asyncio.sleep(0.01)

    async def _worker(self, queue: asyncio.Queue):
        while True:
            try:
                item, retries = queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            await self._consume_token()
            try:
                # 脏数据自愈：如果在进入流程时发现是明显无效数据（如 None），提供一定自愈（抛异常跳过而不崩溃）
                if item is None:
                    raise ValueError("Dirty data self-healing: Skipped None item")

                result = await self.process_func(item)
                async with self._lock:
                    self.results.append(result)
                    self.success_count += 1
            except RateLimit429Exception as e:
                # 零丢信重试队列
                async with self._lock:
                    self.retry_count += 1

                if retries < self.max_retries:
                    # Exponential backoff retry (0.1s, 0.2s, 0.4s ...) for quick recovery without overwhelming
                    await asyncio.sleep(0.1 * (2 ** retries))
                    await queue.put((item, retries + 1))
                else:
                    async with self._lock:
                        self.errors.append((item, e))
                        self.failed_count += 1
            except Exception as e:
                # 其他异常，直接记录，不阻塞主流程，实现零阻塞结果汇总
                async with self._lock:
                    self.errors.append((item, e))
                    self.failed_count += 1
            finally:
                queue.task_done()

    async def process_batch_async(self, items: List[Any]) -> Dict[str, Any]:
        self._lock = asyncio.Lock()

        if not items:
            return {"results": [], "errors": [], "snapshot": self.get_snapshot()}

        self.total = len(items)
        queue = asyncio.Queue()
        for item in items:
            queue.put_nowait((item, 0))

        # 并发加速封装
        workers = [asyncio.create_task(self._worker(queue)) for _ in range(self.max_concurrency)]

        await queue.join()

        for w in workers:
            if not w.done():
                w.cancel()

        return {
            "results": self.results,
            "errors": self.errors,
            "snapshot": self.get_snapshot()
        }

    def get_snapshot(self) -> ProgressSnapshot:
        """进度快照"""
        return ProgressSnapshot(
            total=self.total,
            success=self.success_count,
            failed=self.failed_count,
            pending=self.total - (self.success_count + self.failed_count),
            retries=self.retry_count
        )

def run_batch_pipeline(items: List[Any], process_func: Callable = None, **kwargs) -> Dict[str, Any]:
    """
    一键直达、零确认弹窗、零配置容错的极简调用入口
    """
    # 缺参自动设合理默认值
    if items is None:
        items = []

    if process_func is None:
        # 如果未提供处理函数，默认返回自身作为回退容错
        async def default_func(x):
            return x
        process_func = default_func

    # 兼容传入同步函数
    if not asyncio.iscoroutinefunction(process_func):
        sync_func = process_func
        async def async_wrapper(x):
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, sync_func, x)
        real_func = async_wrapper
    else:
        real_func = process_func

    pipeline = RateLimit429QueueBatchPipeline(
        process_func=real_func,
        max_concurrency=kwargs.get('max_concurrency', 10),
        tokens_per_second=kwargs.get('tokens_per_second', 50.0),
        max_retries=kwargs.get('max_retries', 3)
    )

    def run_sync():
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            result_container = {}
            def thread_target():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                result_container['res'] = new_loop.run_until_complete(pipeline.process_batch_async(items))
                new_loop.close()
            t = threading.Thread(target=thread_target)
            t.start()
            t.join()
            return result_container['res']
        else:
            return asyncio.run(pipeline.process_batch_async(items))

    return run_sync()
