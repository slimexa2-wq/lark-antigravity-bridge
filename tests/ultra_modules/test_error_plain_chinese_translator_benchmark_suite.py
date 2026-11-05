import unittest
import sys
import os

# 将父目录加入 PYTHONPATH，以确保可以正常引入模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from ultra_modules.error_plain_chinese_translator_benchmark_suite import generate_synthetic_fixtures, run_benchmark


class TestErrorPlainChineseTranslatorBenchmarkSuite(unittest.TestCase):

    def test_generate_synthetic_fixtures_default_params(self):
        """测试缺参（或负数）时的默认兜底行为"""
        fixtures_default = generate_synthetic_fixtures()
        self.assertEqual(len(fixtures_default), 10000)

        fixtures_none = generate_synthetic_fixtures(None)
        self.assertEqual(len(fixtures_none), 10000)

        fixtures_negative = generate_synthetic_fixtures(-5)
        self.assertEqual(len(fixtures_negative), 10000)

    def test_generate_synthetic_fixtures_normal_size(self):
        """测试正常参数传入"""
        fixtures = generate_synthetic_fixtures(50)
        self.assertEqual(len(fixtures), 50)

    def test_run_benchmark_default_params(self):
        """测试运行 benchmark 缺参兜底"""
        # 测试缺省 concurrency_size 参数
        res = run_benchmark(concurrency_size=None, fixtures=[None, "", 404, "java.lang.NullPointerException"])
        self.assertEqual(res["total_requests"], 4)
        self.assertTrue(res["total_time_ms"] >= 0)

        # 测试完全缺参
        res_default = run_benchmark(100)
        self.assertEqual(res_default["total_requests"], 100)
        self.assertTrue(res_default["total_time_ms"] >= 0)

    def test_run_benchmark_zero_crashes_and_performance(self):
        """
        测试 10000 次调用保证零崩溃，并且平均延迟处于毫秒级
        覆盖脏数据自愈、正常数据、极端边界情况。
        """
        size = 10000
        res = run_benchmark(concurrency_size=size)
        self.assertEqual(res["total_requests"], size)

        # 平均延迟应该非常低，毫秒级响应 (比如平均每个请求 < 1 ms)
        self.assertTrue(res["avg_latency_ms"] < 5.0)

    def test_extreme_empty_fixtures(self):
        """测试极端边界：传入空的 fixtures 数组"""
        res = run_benchmark(fixtures=[])
        self.assertEqual(res["total_requests"], 0)
        self.assertTrue(res["total_time_ms"] >= 0)
        self.assertEqual(res["avg_latency_ms"], 0)

    def test_benchmark_exception_handling(self):
        """测试 benchmark 中的异常捕获分支，确保会抛出 RuntimeError"""
        from unittest.mock import patch

        with patch('ultra_modules.error_plain_chinese_translator_benchmark_suite.translate_error_to_plain_chinese', side_effect=Exception("Mocked crash")):
            with self.assertRaises(RuntimeError) as context:
                run_benchmark(fixtures=["test_fixture"])

            self.assertIn("Mocked crash", str(context.exception))
            self.assertIn("test_fixture", str(context.exception))


if __name__ == '__main__':
    unittest.main()
