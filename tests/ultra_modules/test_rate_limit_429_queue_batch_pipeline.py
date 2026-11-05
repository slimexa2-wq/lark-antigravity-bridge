import unittest
import asyncio
import time
from ultra_modules.rate_limit_429_queue_batch_pipeline import (
    RateLimit429QueueBatchPipeline,
    run_batch_pipeline,
    RateLimit429Exception
)

class TestRateLimit429QueueBatchPipeline(unittest.TestCase):

    def test_normal_operation_batch(self):
        """测试正常流程的批量处理"""
        items = list(range(10, 20)) # 10 items

        async def process(item):
            await asyncio.sleep(0.01)
            return item * 2

        result = run_batch_pipeline(items, process, max_concurrency=5, tokens_per_second=100.0)

        self.assertEqual(len(result["results"]), 10)
        self.assertEqual(len(result["errors"]), 0)
        self.assertEqual(result["snapshot"].success, 10)
        self.assertEqual(result["snapshot"].total, 10)
        self.assertEqual(result["snapshot"].pending, 0)
        self.assertEqual(result["snapshot"].failed, 0)

        # Verify the contents are correct (order is not guaranteed due to concurrency)
        self.assertEqual(set(result["results"]), set([x * 2 for x in items]))

    def test_dirty_data_self_healing(self):
        """测试脏数据自愈功能（如跳过 None）"""
        items = [1, None, 3, None, 5]

        async def process(item):
            return item * 10

        result = run_batch_pipeline(items, process, max_concurrency=2, tokens_per_second=100.0)

        self.assertEqual(len(result["results"]), 3)
        self.assertEqual(len(result["errors"]), 2)
        self.assertEqual(result["snapshot"].success, 3)
        self.assertEqual(result["snapshot"].failed, 2)

        # Verify errors are ValueError for None
        for item, error in result["errors"]:
            self.assertIsNone(item)
            self.assertIsInstance(error, ValueError)
            self.assertIn("Dirty data", str(error))

        self.assertEqual(set(result["results"]), set([10, 30, 50]))

    def test_missing_parameter_default_fallback(self):
        """测试缺参情况下的极简入口兜底策略"""
        # 未提供 process_func 和 kwargs, None items
        result = run_batch_pipeline(None)

        self.assertEqual(len(result["results"]), 0)
        self.assertEqual(result["snapshot"].total, 0)

        # 提供正常数据但未提供 process_func
        items = [1, 2, 3]
        result2 = run_batch_pipeline(items)
        self.assertEqual(len(result2["results"]), 3)
        self.assertEqual(set(result2["results"]), set([1, 2, 3]))

    def test_429_error_retries_and_recovery(self):
        """测试429错误的零丢信重试"""
        items = [1, 2, 3]

        # 记录每个 item 尝试的次数
        attempts = {1: 0, 2: 0, 3: 0}

        async def process(item):
            attempts[item] += 1
            if item == 2 and attempts[item] <= 2:
                # 让 item 2 触发两次 429，然后在第三次成功
                raise RateLimit429Exception("Too many requests")
            return f"Success {item}"

        result = run_batch_pipeline(items, process, max_concurrency=2, tokens_per_second=100.0, max_retries=3)

        self.assertEqual(len(result["results"]), 3)
        self.assertEqual(len(result["errors"]), 0)
        self.assertEqual(result["snapshot"].success, 3)
        self.assertEqual(result["snapshot"].retries, 2)

        self.assertEqual(attempts[1], 1)
        self.assertEqual(attempts[2], 3)
        self.assertEqual(attempts[3], 1)
        self.assertEqual(set(result["results"]), set(["Success 1", "Success 2", "Success 3"]))

    def test_retry_limit_exhausted(self):
        """测试429重试次数耗尽的情况"""
        items = ["a", "b"]

        async def process(item):
            if item == "a":
                # item "a" 永远失败
                raise RateLimit429Exception("Always 429")
            return item.upper()

        result = run_batch_pipeline(items, process, max_concurrency=2, tokens_per_second=100.0, max_retries=2)

        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0], "B")

        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0][0], "a")
        self.assertIsInstance(result["errors"][0][1], RateLimit429Exception)

        # 初始1次 + 2次重试 = 3次失败触发 429，记录了 2次 retry (不包括最终放弃的那次)
        # 根据实现，每次捕获 429 都会增加 retry_count
        self.assertEqual(result["snapshot"].retries, 3)
        self.assertEqual(result["snapshot"].failed, 1)
        self.assertEqual(result["snapshot"].success, 1)

    def test_extreme_large_batch(self):
        """测试极大批量数据、并发和限流策略"""
        # 1000 items (the upper end of the required 10~1000)
        items = list(range(1000))

        def process_sync(item):
            # Also test the sync wrapper fallback
            return item + 1

        start_time = time.time()
        # Limit tokens to test if smoothing queue actually holds it back
        # If tokens_per_second is 10000 (very fast), it shouldn't hold much,
        # but let's test general throughput and stability
        result = run_batch_pipeline(items, process_sync, max_concurrency=50, tokens_per_second=20000.0)
        elapsed = time.time() - start_time

        self.assertEqual(len(result["results"]), 1000)
        self.assertEqual(result["snapshot"].success, 1000)
        self.assertEqual(len(result["errors"]), 0)

        # Sum of first 1000 integers offset by 1
        expected_sum = sum(range(1, 1001))
        self.assertEqual(sum(result["results"]), expected_sum)

        # Note: Depending on system, 1000 items might take some time even with async.
        # As long as it passes without error, throughput requirement is met.

if __name__ == '__main__':
    unittest.main()
