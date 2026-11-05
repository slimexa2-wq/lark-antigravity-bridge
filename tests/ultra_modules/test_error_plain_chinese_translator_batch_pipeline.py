import unittest
import time
from ultra_modules.error_plain_chinese_translator_batch_pipeline import ErrorPlainChineseTranslatorBatchPipeline

class TestErrorPlainChineseTranslatorBatchPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = ErrorPlainChineseTranslatorBatchPipeline(max_workers=5)

    def tearDown(self):
        self.pipeline.shutdown()

    def test_normal_processing(self):
        """测试正常的批量处理"""
        records = [
            {"raw_error": "Connection timeout on port 8080", "code": "E001"},
            {"raw_error": "Null pointer exception at line 42", "code": "E002"},
            {"raw_error": "Permission denied for user admin", "code": 403},
        ]

        batch_id = self.pipeline.process_batch(records)

        # 等待处理完成
        while True:
            progress = self.pipeline.get_progress(batch_id)
            if progress and progress['status'] == 'completed':
                break
            time.sleep(0.1)

        results = self.pipeline.get_results(batch_id)
        self.assertIsNotNone(results)
        self.assertEqual(len(results), 3)

        # 验证解析结果
        self.assertIn("网络请求超时", results[0]["plain_chinese_explanation"])
        self.assertIn("空值", results[1]["plain_chinese_explanation"])
        self.assertIn("没有权限", results[2]["plain_chinese_explanation"])

    def test_dirty_data_auto_healing(self):
        """测试脏数据自愈"""
        # 传入非字典的脏数据
        records = [
            "Just a string error",
            None,
            12345
        ]

        batch_id = self.pipeline.process_batch(records)

        while True:
            progress = self.pipeline.get_progress(batch_id)
            if progress and progress['status'] == 'completed':
                break
            time.sleep(0.1)

        results = self.pipeline.get_results(batch_id)
        self.assertEqual(len(results), 3)

        # 验证脏数据被自动包装
        self.assertEqual(results[0]["original_error"], "Just a string error")
        self.assertEqual(results[1]["original_error"], "Unknown Error")
        self.assertEqual(results[2]["original_error"], "12345")

    def test_missing_params_fallback(self):
        """测试缺参默认兜底"""
        # error_records为None或非列表
        batch_id1 = self.pipeline.process_batch(None)
        batch_id2 = self.pipeline.process_batch("not a list")

        while True:
            p1 = self.pipeline.get_progress(batch_id1)
            p2 = self.pipeline.get_progress(batch_id2)
            if (p1 and p1['status'] == 'completed') and (p2 and p2['status'] == 'completed'):
                break
            time.sleep(0.1)

        res1 = self.pipeline.get_results(batch_id1)
        res2 = self.pipeline.get_results(batch_id2)

        self.assertEqual(len(res1), 0)
        self.assertEqual(len(res2), 0)

    def test_extreme_boundary(self):
        """测试极端边界条件（如超大文本截断）"""
        large_error = "A" * 10000
        records = [{"raw_error": large_error}]

        batch_id = self.pipeline.process_batch(records)

        while True:
            progress = self.pipeline.get_progress(batch_id)
            if progress and progress['status'] == 'completed':
                break
            time.sleep(0.1)

        results = self.pipeline.get_results(batch_id)

        # 应该被截断到5000字符 + '...[截断]'
        self.assertTrue(len(results[0]["original_error"]) < 6000)
        self.assertTrue(results[0]["original_error"].endswith("...[截断]"))

    def test_progress_snapshot(self):
        """测试进度快照功能"""
        # 创建较多的任务以观察进度
        records = [{"raw_error": f"Error {i}"} for i in range(100)]
        batch_id = self.pipeline.process_batch(records)

        # 立即获取进度（可能部分完成或还在进行）
        progress = self.pipeline.get_progress(batch_id)
        self.assertIsNotNone(progress)
        self.assertEqual(progress['total'], 100)
        self.assertIn(progress['status'], ['processing', 'completed'])

        while True:
            progress = self.pipeline.get_progress(batch_id)
            if progress and progress['status'] == 'completed':
                break
            time.sleep(0.1)

        final_progress = self.pipeline.get_progress(batch_id)
        self.assertEqual(final_progress['completed'], 100)
        self.assertEqual(final_progress['failed'], 0)
        self.assertEqual(final_progress['status'], 'completed')

if __name__ == '__main__':
    unittest.main()
