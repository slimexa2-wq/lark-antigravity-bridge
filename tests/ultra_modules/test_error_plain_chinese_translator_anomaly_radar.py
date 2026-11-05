import unittest
from ultra_modules.error_plain_chinese_translator_anomaly_radar import ErrorAnomalyRadar

class TestErrorAnomalyRadar(unittest.TestCase):
    def setUp(self):
        self.radar = ErrorAnomalyRadar()

    def test_01_normal_condition_distribution(self):
        # Create 100 items with severity 1 to 100
        errors = [{"error_msg": f"Error {i}", "severity": float(i)} for i in range(1, 101)]

        result = self.radar.scan_and_translate(errors)

        # Sort result by severity descending to check colors
        sorted_res = sorted(result, key=lambda x: x["severity"], reverse=True)

        # Top 3 (98, 99, 100) should be red
        for i in range(3):
            self.assertEqual(sorted_res[i]["color"], "red")
            self.assertIn("plain_chinese_reason", sorted_res[i])
            self.assertIn("self_healing_suggestion", sorted_res[i])

        # Next 7 (91 to 97) should be yellow
        for i in range(3, 10):
            self.assertEqual(sorted_res[i]["color"], "yellow")
            self.assertNotIn("plain_chinese_reason", sorted_res[i])

        # Remaining 90 (1 to 90) should be green
        for i in range(10, 100):
            self.assertEqual(sorted_res[i]["color"], "green")
            self.assertNotIn("plain_chinese_reason", sorted_res[i])

    def test_02_dirty_data_self_healing(self):
        errors = [
            "Not a dict",
            {"error_msg": "Missing severity"},
            {"error_msg": "Null severity", "severity": None},
            {"error_msg": "String severity", "severity": "4.5"},
            {"error_msg": "Invalid string severity", "severity": "invalid"},
            {"severity": 5.0} # Missing error_msg
        ]

        result = self.radar.scan_and_translate(errors)

        self.assertEqual(len(result), 6)

        # 1. Not a dict
        self.assertEqual(result[0]["error_msg"], "Not a dict")
        self.assertEqual(result[0]["severity"], 0.0)

        # 2. Missing severity
        self.assertEqual(result[1]["error_msg"], "Missing severity")
        self.assertEqual(result[1]["severity"], 0.0)

        # 3. Null severity
        self.assertEqual(result[2]["error_msg"], "Null severity")
        self.assertEqual(result[2]["severity"], 0.0)

        # 4. String severity
        self.assertEqual(result[3]["error_msg"], "String severity")
        self.assertEqual(result[3]["severity"], 4.5)

        # 5. Invalid string severity
        self.assertEqual(result[4]["error_msg"], "Invalid string severity")
        self.assertEqual(result[4]["severity"], 0.0)

        # 6. Missing error_msg
        self.assertEqual(result[5]["error_msg"], "Unknown error")
        self.assertEqual(result[5]["severity"], 5.0)

    def test_03_missing_parameter_fallback(self):
        # No arguments
        self.assertEqual(self.radar.scan_and_translate(), [])

        # None argument
        self.assertEqual(self.radar.scan_and_translate(None), [])

        # Wrong type (e.g. dict instead of list)
        self.assertEqual(self.radar.scan_and_translate({"error_msg": "err"}), [])

    def test_04_extreme_boundary_conditions(self):
        # Empty list
        self.assertEqual(self.radar.scan_and_translate([]), [])

        # Single element list
        single_res = self.radar.scan_and_translate([{"error_msg": "Single error", "severity": 10.0}])
        self.assertEqual(len(single_res), 1)
        self.assertEqual(single_res[0]["color"], "green")

        # List where all elements have the exact same score
        same_score_errors = [{"error_msg": f"Err {i}", "severity": 5.0} for i in range(100)]
        same_res = self.radar.scan_and_translate(same_score_errors)

        # In this boundary, top 3 should still be marked red by arbitrary ranking to prevent all getting marked red
        red_count = sum(1 for r in same_res if r["color"] == "red")
        yellow_count = sum(1 for r in same_res if r["color"] == "yellow")
        green_count = sum(1 for r in same_res if r["color"] == "green")

        self.assertEqual(red_count, 3)
        self.assertEqual(yellow_count, 7)
        self.assertEqual(green_count, 90)

    def test_05_common_error_translations(self):
        # We need a list long enough to trigger top 3% for the translations to apply (i.e. to be marked red)
        # We'll create 34 items to get exactly 1 red (34 * 0.03 = 1.02 -> 1)
        errors_npe = [{"error_msg": "java.lang.NullPointerException at some place", "severity": 100.0}]
        errors_npe.extend([{"error_msg": f"Err {i}", "severity": float(i)} for i in range(33)])

        res_npe = self.radar.scan_and_translate(errors_npe)
        top_npe = sorted(res_npe, key=lambda x: x["severity"], reverse=True)[0]

        self.assertEqual(top_npe["color"], "red")
        self.assertEqual(top_npe["plain_chinese_reason"], "遇到了空指针异常，通常是因为代码试图访问一个不存在的对象。")
        self.assertEqual(top_npe["self_healing_suggestion"], "请检查相关变量是否已被正确初始化。")

        # Test TimeoutError
        errors_timeout = [{"error_msg": "Connection TimeoutError...", "severity": 100.0}]
        errors_timeout.extend([{"error_msg": f"Err {i}", "severity": float(i)} for i in range(33)])

        res_timeout = self.radar.scan_and_translate(errors_timeout)
        top_timeout = sorted(res_timeout, key=lambda x: x["severity"], reverse=True)[0]

        self.assertEqual(top_timeout["color"], "red")
        self.assertEqual(top_timeout["plain_chinese_reason"], "请求超时，可能是网络延迟或服务器响应过慢导致。")
        self.assertEqual(top_timeout["self_healing_suggestion"], "建议增加超时时间或检查网络连通性。")

        # Test Unknown error
        errors_unknown = [{"error_msg": "Some Random Weird Exception", "severity": 100.0}]
        errors_unknown.extend([{"error_msg": f"Err {i}", "severity": float(i)} for i in range(33)])

        res_unknown = self.radar.scan_and_translate(errors_unknown)
        top_unknown = sorted(res_unknown, key=lambda x: x["severity"], reverse=True)[0]

        self.assertEqual(top_unknown["color"], "red")
        self.assertEqual(top_unknown["plain_chinese_reason"], "发生了未知错误。")
        self.assertEqual(top_unknown["self_healing_suggestion"], "请查看详细的后台日志以获取更多线索。")

if __name__ == "__main__":
    unittest.main() # pragma: no cover
