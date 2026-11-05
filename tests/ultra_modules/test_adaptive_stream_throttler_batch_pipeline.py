import unittest
import time
from typing import Dict, Any
from ultra_modules.adaptive_stream_throttler_batch_pipeline import AdaptiveStreamThrottler, BatchPipeline

class TestAdaptiveStreamThrottlerBatchPipeline(unittest.TestCase):

    def test_adaptive_stream_throttler_normal_flow(self):
        """1. 测试节流器正常流与单调递增sequence"""
        throttler = AdaptiveStreamThrottler(min_window_ms=10, max_window_ms=100) # 为测试缩短时间

        throttler.push_token("Hello ")
        throttler.push_token("World")

        # 立刻读取应该拿不到数据，因为时间未到
        self.assertIsNone(throttler.try_flush())

        # 等待超过min_window_ms
        time.sleep(0.015)

        result = throttler.try_flush()
        self.assertIsNotNone(result)
        self.assertEqual(result["content"], "Hello World")
        self.assertEqual(result["sequence"], 1)

        # 强制刷新
        throttler.push_token("!")
        result2 = throttler.force_flush()
        self.assertIsNotNone(result2)
        self.assertEqual(result2["content"], "!")
        self.assertEqual(result2["sequence"], 2) # sequence单调递增

    def test_adaptive_window_logic(self):
        """2. 测试节流器自适应窗口调整逻辑 (Adaptive Window Logic)"""
        throttler = AdaptiveStreamThrottler(min_window_ms=150, max_window_ms=500)
        self.assertEqual(throttler.current_window_ms, 150)

        # 收到429
        throttler.report_429()
        self.assertEqual(throttler.current_window_ms, 300)
        throttler.report_429()
        self.assertEqual(throttler.current_window_ms, 500) # max_window_ms 封顶

        # 成功后恢复
        throttler.report_success()
        self.assertEqual(throttler.current_window_ms, 495)

    def test_batch_pipeline_dirty_data_healing(self):
        """3. 测试批量流水线：脏数据自愈与缺参默认兜底"""
        pipeline = BatchPipeline()
        dirty_records = [
            {"name": "Alice"}, # 缺id, 缺status
            "Not a dict at all", # 彻底的脏数据
            {"id": "user_123", "status": "active", "value": "100.5"}, # 正常
            {"id": "user_456", "value": "invalid_number"} # 类型错误
        ]

        pipeline.ingest(dirty_records)

        self.assertEqual(len(pipeline.records), 4)

        r0 = pipeline.records[0]
        self.assertIn("id", r0)
        self.assertEqual(r0["status"], "pending")

        r1 = pipeline.records[1]
        self.assertIn("_raw", r1)
        self.assertEqual(r1["_raw"], "Not a dict at all")
        self.assertIn("id", r1)

        r2 = pipeline.records[2]
        self.assertEqual(r2["value"], 100.5)

        r3 = pipeline.records[3]
        self.assertEqual(r3["value"], 0.0) # 无效数值应自愈为0.0

    def test_batch_pipeline_zero_blocking_results(self):
        """4. 测试批量流水线：进度快照与零阻塞结果汇总 (极端异常处理)"""
        pipeline = BatchPipeline()
        records = [
            {"id": "1", "data": "valid"},
            {"id": "2", "data": "invalid"},
            {"id": "3", "data": "valid"}
        ]
        pipeline.ingest(records)

        # 模拟处理器，遇到 "invalid" 则抛出异常
        def flaky_processor(record: Dict[str, Any]) -> Dict[str, Any]:
            if record.get("data") == "invalid":
                raise ValueError("Simulated processing error")
            res = dict(record)
            res["status"] = "processed_ok"
            return res

        summary = pipeline.process_all(processor_func=flaky_processor)

        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["success"], 2)
        self.assertEqual(summary["error"], 1)

        # 验证快照内容
        snapshot = summary["snapshot"]
        self.assertEqual(snapshot[0]["status"], "processed_ok")
        self.assertEqual(snapshot[1]["status"], "error")
        self.assertEqual(snapshot[1]["error_msg"], "Simulated processing error")
        self.assertEqual(snapshot[2]["status"], "processed_ok")

        # 验证记录被清空
        self.assertEqual(len(pipeline.records), 0)

    def test_extreme_boundary_conditions(self):
        """5. 测试极端边界条件：超量数据与空数据"""
        pipeline = BatchPipeline()

        # 空数据ingest
        pipeline.ingest([])
        self.assertEqual(len(pipeline.records), 0)

        summary_empty = pipeline.process_all()
        self.assertEqual(summary_empty["total"], 0)

        # 超量数据拖入 (模拟1000条记录)
        large_batch = [{"id": f"item_{i}"} for i in range(1000)]
        pipeline.ingest(large_batch)
        self.assertEqual(len(pipeline.records), 1000)

        summary_large = pipeline.process_all()
        self.assertEqual(summary_large["total"], 1000)
        self.assertEqual(summary_large["success"], 1000)
        self.assertEqual(len(summary_large["snapshot"]), 1000)
        self.assertEqual(summary_large["snapshot"][999]["id"], "item_999")
        self.assertEqual(summary_large["snapshot"][999]["status"], "processed")

if __name__ == '__main__':
    unittest.main()
