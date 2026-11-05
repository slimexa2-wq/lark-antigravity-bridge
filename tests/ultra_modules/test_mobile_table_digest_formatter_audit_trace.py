import unittest
from ultra_modules.mobile_table_digest_formatter_audit_trace import format_mobile_table_digest

class TestMobileTableDigestFormatterAuditTrace(unittest.TestCase):
    def test_normal_data(self):
        """Test with normal valid data"""
        data = [
            {"id": "1", "name": "Item A", "expected": 100, "actual": 100},
            {"id": "2", "name": "Item B", "expected": 50, "actual": 40},
            {"id": "3", "name": "Item C", "expected": 200, "actual": 210.5},
        ]
        res, traces = format_mobile_table_digest(data, "https://example.com/file")
        self.assertIn("共处理 3 条数据", res)
        self.assertIn("发现 2 项异常", res)
        self.assertIn("Item B(Δ-10.00)", res)
        self.assertIn("Item C(Δ+10.50)", res)
        self.assertIn("https://example.com/file", res)

        # Check trace
        diff_traces = [t for t in traces if t["step"] == "DIFF_HIGHLIGHT"]
        self.assertEqual(len(diff_traces), 2)

    def test_dirty_data_self_healing(self):
        """Test with dirty data like non-dicts, duplicates, missing fields, invalid numbers"""
        data = [
            {"id": "1", "name": "Item A", "expected": 100, "actual": "invalid"},
            {"id": "1", "name": "Item A Dup"},
            "not a dict",
            {"expected": "bad", "actual": "worse"},
        ]
        res, traces = format_mobile_table_digest(data, "https://example.com/file")

        self.assertIn("共处理 2 条数据", res)
        self.assertIn("发现 1 项异常", res)
        self.assertIn("Item A(Δ-100.00)", res)

        # Check logs
        self.assertTrue(any(t["step"] == "SELF_HEAL" and "actual value invalid" in str(t["details"]) for t in traces))
        self.assertTrue(any(t["step"] == "DEDUPLICATE" and "1" in str(t["details"]) for t in traces))
        self.assertTrue(any(t["step"] == "SELF_HEAL" and "not a dict" in str(t["details"]) for t in traces))
        self.assertTrue(any(t["step"] == "SELF_HEAL" and "missing ID, auto-generated" in str(t["details"]) for t in traces))

    def test_missing_parameter_fallback(self):
        """Test missing parameters (None)"""
        res, traces = format_mobile_table_digest()

        self.assertIn("共处理 0 条数据", res)
        self.assertIn("发现 0 项异常", res)
        self.assertIn("✅ 异常高亮: 无异常，系统运行平稳。", res)
        self.assertIn("https://feishu.cn/default_attachment_download", res)

        self.assertTrue(any(t["step"] == "FALLBACK" and "Missing raw_data" in str(t["details"]) for t in traces))
        self.assertTrue(any(t["step"] == "FALLBACK" and "used default fallback" in str(t["details"]) for t in traces))

    def test_extreme_boundaries(self):
        """Test extreme boundary conditions: many items, triggering truncation"""
        data = [{"id": str(i), "name": f"Item_{i}", "expected": 10, "actual": 20} for i in range(10)]
        res, traces = format_mobile_table_digest(data, "https://example.com/file")

        self.assertIn("共处理 10 条数据", res)
        self.assertIn("发现 10 项异常", res)
        self.assertIn("Item_0(Δ+10.00), Item_1(Δ+10.00), Item_2(Δ+10.00)...", res)

        self.assertEqual(len([t for t in traces if t["step"] == "DIFF_HIGHLIGHT"]), 10)

    def test_invalid_data_type(self):
        """Test passing a non-list as raw_data"""
        res_dict, traces_dict = format_mobile_table_digest({"id": "only", "name": "Lonely", "expected": 5, "actual": 1})
        self.assertIn("共处理 1 条数据", res_dict)
        self.assertIn("发现 1 项异常", res_dict)
        self.assertTrue(any(t["step"] == "SELF_HEAL" and "wrapping in list" in str(t["details"]) for t in traces_dict))

        res_int, traces_int = format_mobile_table_digest(123)
        self.assertIn("共处理 0 条数据", res_int)
        self.assertTrue(any(t["step"] == "SELF_HEAL" and "wrapping in list or defaulting" in str(t["details"]) for t in traces_int))
