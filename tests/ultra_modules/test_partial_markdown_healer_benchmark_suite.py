import unittest
from ultra_modules.partial_markdown_healer_benchmark_suite import (
    generate_synthetic_fixtures,
    run_single_case,
    run_benchmark,
    BenchmarkResult
)

class TestPartialMarkdownHealerBenchmarkSuite(unittest.TestCase):

    def test_generate_synthetic_fixtures(self):
        """测试正常生成数据集"""
        fixtures = generate_synthetic_fixtures(num_cases=50)
        self.assertEqual(len(fixtures), 50)
        self.assertTrue(all("content" in f and "format" in f for f in fixtures))

    def test_extreme_boundaries(self):
        """测试极端边界：超大并发与大数据集"""
        # 为了测试速度不设置太大，但也需要验证逻辑是否通顺
        result = run_benchmark(num_cases=1000, concurrency=10)
        self.assertIsInstance(result, BenchmarkResult)
        self.assertEqual(result.total_cases, 1000)
        self.assertEqual(result.success_cases, 1000)
        self.assertGreaterEqual(result.total_time_ms, 0)
        self.assertGreaterEqual(result.max_time_ms, result.avg_time_ms)

    def test_self_healing_dirty_data(self):
        """测试脏数据自愈：空值、乱码"""
        res1 = run_single_case(None, "auto")
        self.assertTrue(res1["success"])
        self.assertEqual(res1["result"], "")

        res2 = run_single_case("\x00\x1f❤️", "auto")
        self.assertTrue(res2["success"])
        self.assertEqual(res2["result"], "\x00\x1f❤️")

        res3 = run_single_case('{"key": "value", "arr": [1, 2, 3', "json")
        self.assertTrue(res3["success"])
        self.assertEqual(res3["result"], '{"key": "value", "arr": [1, 2, 3]}')

    def test_default_fallback(self):
        """测试缺参默认兜底"""
        res = run_single_case("```python\nprint('hi')", None)
        self.assertTrue(res["success"])
        self.assertEqual(res["result"], "```python\nprint('hi')\n```")

    def test_benchmark_result_format(self):
        """验证跑分结果的结构"""
        result = run_benchmark(num_cases=10, concurrency=1)
        self.assertTrue(hasattr(result, 'total_cases'))
        self.assertTrue(hasattr(result, 'success_cases'))
        self.assertTrue(hasattr(result, 'total_time_ms'))
        self.assertTrue(hasattr(result, 'avg_time_ms'))
        self.assertTrue(hasattr(result, 'max_time_ms'))
        self.assertEqual(result.total_cases, 10)
        # 基准测试所有合成用例都应能100%成功（不崩溃）
        self.assertEqual(result.success_cases, 10)

if __name__ == "__main__":
    unittest.main()
