import unittest
import datetime
from ultra_modules.attachment_auto_router_benchmark_suite import AttachmentAutoRouter, BenchmarkSuite

class TestAttachmentAutoRouter(unittest.TestCase):
    def setUp(self):
        self.router = AttachmentAutoRouter()
        self.benchmark = BenchmarkSuite(self.router)

    def test_normal_routing(self):
        """Test normal routing based on filename and content preview."""
        # 1. Weekly report
        res = self.router.route(filename="2023-10-15_周报.xlsx", content_preview="This is a weekly update.")
        self.assertEqual(res["engine"], "weekly_report")
        self.assertEqual(res["date_context"], "2023-10-15")

        # 2. Commission
        res = self.router.route(filename="commission_data.csv", content_preview="提成详情")
        self.assertEqual(res["engine"], "commission")

        # 3. Tender
        res = self.router.route(filename="bidding_document.docx", content_preview="标书内容")
        self.assertEqual(res["engine"], "tender")

        # 4. Comic/Drama
        res = self.router.route(filename="comic_script.txt", content_preview="漫剧第一集")
        self.assertEqual(res["engine"], "comic_drama")

        # 5. Unknown
        res = self.router.route(filename="random_notes.txt", content_preview="Hello world")
        self.assertEqual(res["engine"], "unknown")

    def test_dirty_data_self_healing(self):
        """Test routing with dirty data (control chars, None types, etc)."""
        res = self.router.route(
            filename="\x00\x08dirty_周报_file\x1F.txt",
            content_preview=None,
            file_size=-500 # Negative size
        )
        self.assertEqual(res["engine"], "weekly_report")
        self.assertEqual(res["filename"], "dirty_周报_file.txt")
        self.assertEqual(res["processed_size"], 0)
        self.assertEqual(res["status"], "success")

    def test_missing_parameter_fallbacks(self):
        """Test routing with completely missing parameters."""
        res = self.router.route()
        self.assertEqual(res["engine"], "unknown")
        self.assertEqual(res["filename"], "unnamed_file.txt")
        self.assertEqual(res["processed_size"], 0)
        self.assertEqual(res["date_context"], datetime.date.today().isoformat())
        self.assertEqual(res["status"], "success")

    def test_extreme_cross_year_month_boundaries(self):
        """Test date extraction on extreme cross-year/month boundaries and invalid dates."""
        # Valid leap year
        res = self.router.route(filename="leap_year_2024-02-29.xlsx")
        self.assertEqual(res["date_context"], "2024-02-29")

        # Invalid date (2023-13-45) falls back to today
        res = self.router.route(filename="invalid_date_2023-13-45.xlsx")
        self.assertEqual(res["date_context"], datetime.date.today().isoformat())

        # Cross year boundary
        res = self.router.route(filename="cross_year_2023-12-31.xlsx")
        self.assertEqual(res["date_context"], "2023-12-31")
        res = self.router.route(filename="cross_year_2024-01-01.xlsx")
        self.assertEqual(res["date_context"], "2024-01-01")

    def test_high_concurrency_benchmark(self):
        """Test the benchmark suite ensuring zero crash and millisecond response."""
        res = self.benchmark.run_benchmark(concurrency=500)

        self.assertEqual(res["total_requests"], 500)
        self.assertTrue(res["zero_crash"], f"Crashes occurred! Error count: {res['error_count']}")
        self.assertTrue(res["millisecond_response"], f"Response too slow! Avg time: {res['avg_routing_time_ms']}ms")
        self.assertEqual(res["success_count"], 500)

if __name__ == '__main__':
    unittest.main()
