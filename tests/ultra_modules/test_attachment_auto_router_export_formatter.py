import unittest
import math
from ultra_modules.attachment_auto_router_export_formatter import AttachmentAutoRouter

class TestAttachmentAutoRouterExportFormatter(unittest.TestCase):

    def test_normal_data_and_standard_input(self):
        """Test 1: Normal data with standard input."""
        router = AttachmentAutoRouter(filename="report.xlsx", file_type="excel", business_type="周报")
        data = [{"id": 1, "name": "Alice", "amount": 100}, {"id": 2, "name": "Bob", "amount": 200}]

        result = router.process(data)

        self.assertEqual(result["engine"], "周报")
        self.assertEqual(len(result["cleaned_data"]), 2)
        self.assertEqual(result["comments"], 0)

        lines = result["summary"].split("\n")
        self.assertEqual(len(lines), 3)
        self.assertIn("【周报】", lines[0])
        self.assertIn("2", lines[1])
        self.assertIn("comments=0", lines[2])

    def test_dirty_data_self_healing(self):
        """Test 2: Dirty data self-healing (replacing None/NaN with 0 for numerics)."""
        router = AttachmentAutoRouter(filename="commission.csv", business_type="提成")
        data = [
            {"name": "Alice", "提成": None, "id": float('nan')},
            {"name": None, "金额": float('nan')}
        ]

        result = router.process(data)
        cleaned = result["cleaned_data"]

        # Self-healing tests
        self.assertEqual(cleaned[0]["提成"], 0)
        self.assertEqual(cleaned[0]["id"], 0)
        self.assertEqual(cleaned[1]["name"], "") # non-numeric null should be empty string
        self.assertEqual(cleaned[1]["金额"], 0)

    def test_missing_parameter_fallbacks(self):
        """Test 3: Missing parameter fallbacks (providing default types when business type missing)."""
        # Falls back to 漫剧引擎 based on filename
        router = AttachmentAutoRouter(filename="12月漫剧引擎汇总.docx")
        self.assertEqual(router.file_type, "word")
        self.assertEqual(router.business_type, "漫剧引擎")

        # Completely unknown filename falls back to txt and 周报
        router2 = AttachmentAutoRouter(filename="unknown_file")
        self.assertEqual(router2.file_type, "txt")
        self.assertEqual(router2.business_type, "周报")

        # Empty filename
        router3 = AttachmentAutoRouter(filename="")
        self.assertEqual(router3.file_type, "txt")
        self.assertEqual(router3.business_type, "周报")

    def test_extreme_boundary(self):
        """Test 4: Extreme boundary (empty file, invalid list input, extremely large data simulation)."""
        router = AttachmentAutoRouter(filename="empty.txt")

        # Invalid type fallback
        result1 = router.process(None) # type: ignore
        self.assertEqual(len(result1["cleaned_data"]), 0)

        result2 = router.process("not a list") # type: ignore
        self.assertEqual(len(result2["cleaned_data"]), 0)

        # Test large structure (simulation)
        large_data = [{"id": i, "value": i} for i in range(1000)]
        result3 = router.process(large_data)
        self.assertEqual(len(result3["cleaned_data"]), 1000)
        lines = result3["summary"].split("\n")
        self.assertIn("1000", lines[1])

    def test_output_format_check(self):
        """Test 5: Output format check (ensuring 3 lines in the generated summary and comments=0)."""
        router = AttachmentAutoRouter(filename="标书_final.pdf", business_type="标书")
        result = router.process([{"A": 1}])

        self.assertEqual(result["comments"], 0)

        summary = result["summary"]
        lines = summary.split("\n")
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], "【标书】解析完毕 (文件: 标书_final.pdf)")
        self.assertEqual(lines[1], "共处理 1 条数据 (零批注纯净导出)")
        self.assertEqual(lines[2], "导出状态: 正常 | comments=0")

if __name__ == '__main__':
    unittest.main()
