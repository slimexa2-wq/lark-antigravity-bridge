import unittest
from ultra_modules.error_plain_chinese_translator_audit_trace import ErrorTranslator

class TestErrorTranslator(unittest.TestCase):
    def setUp(self):
        self.translator = ErrorTranslator()

    def test_normal_situation(self):
        # Test Case 1: Normal Situation
        error_msg = "Connection refused by the server."
        result = self.translator.process_error(raw_error=error_msg, context="API Call")

        self.assertIn("trace_id", result)
        self.assertEqual(result["plain_chinese_message"], "网络连接失败，请检查您的网络设置后重试。")
        self.assertIn("检查网络连接并重试", result["healing_suggestions"])
        self.assertIn("- [Raw Error] Connection refused", result["diff_highlight"])

        logs = self.translator.get_audit_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["trace_id"], result["trace_id"])
        self.assertEqual(logs[0]["context_info"], "API Call")

    def test_missing_parameters_default_fallback(self):
        # Test Case 2: Missing/faulty parameters (defaults)
        result = self.translator.process_error()

        self.assertEqual(result["plain_chinese_message"], "系统遇到未知错误，请稍后再试或联系技术支持。")
        self.assertEqual(result["healing_suggestions"], ["一键重试", "联系客服"])
        self.assertEqual(result["diff_highlight"], "+ 系统遇到未知错误，请稍后再试或联系技术支持。")

        logs = self.translator.get_audit_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["context_info"], "No Context Provided")

    def test_dirty_data_self_healing(self):
        # Test Case 3: Dirty data / Self-healing (unstringifiable objects)
        class Unstringifiable:
            def __str__(self):
                raise Exception("Cannot convert to string")

        dirty_data = Unstringifiable()
        result = self.translator.process_error(raw_error=dirty_data, context={"key": "value"})

        self.assertEqual(result["plain_chinese_message"], "系统遇到未知错误，请稍后再试或联系技术支持。")

        logs = self.translator.get_audit_logs()
        self.assertEqual(len(logs), 1)
        self.assertIn("Unparseable Data", logs[0]["original_error_snippet"])
        self.assertEqual(logs[0]["context_info"], "{'key': 'value'}")

    def test_extreme_boundary_massive_string(self):
        # Test Case 4: Extreme boundaries (massive string)
        massive_string = "A" * 20000
        massive_context = "B" * 10000

        result = self.translator.process_error(raw_error=massive_string, context=massive_context)

        self.assertEqual(result["plain_chinese_message"], "系统遇到未知错误，请稍后再试或联系技术支持。")
        self.assertTrue(result["diff_highlight"].startswith("- [Raw Error] AAAAA"))

        logs = self.translator.get_audit_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["original_error_length"], 10000 + len("...(truncated due to length)"))
        self.assertTrue(logs[0]["context_info"].endswith("...(truncated)"))

    def test_exception_object_parsing(self):
        # Test Case 5: Exception object parsing
        try:
            1 / 0
        except Exception as e:
            result = self.translator.process_error(raw_error=e)

            self.assertEqual(result["plain_chinese_message"], "系统遇到未知错误，请稍后再试或联系技术支持。")
            self.assertTrue("ZeroDivisionError" in result["diff_highlight"], f"Expected 'ZeroDivisionError' in {result['diff_highlight']}")

            logs = self.translator.get_audit_logs()
            self.assertEqual(len(logs), 1)
            self.assertIn("ZeroDivisionError", logs[0]["original_error_snippet"])

    def test_various_known_errors(self):
        # Test Case 6: Additional coverage for translation branches
        errors = [
            ("NullPointer Exception occurred", "程序处理到空数据，导致无法继续运行。"),
            ("Permission denied for resource", "您当前没有权限执行此操作，请联系管理员分配权限。"),
            ("Out of memory error", "系统内存不足，请尝试关闭一些程序后重试。"),
            ("Index out of range", "尝试访问的数据超出了正常范围。"),
            ("Syntax error in query", "代码或输入存在语法错误，无法解析。"),
            ("User not found 404", "您要寻找的资源或数据未找到，请确认后重试。"),
            ("Duplicate entry for key", "提交的数据已经存在，请不要重复提交。")
        ]

        for error, expected_translation in errors:
            result = self.translator.process_error(raw_error=error)
            self.assertEqual(result["plain_chinese_message"], expected_translation)

    def test_clear_audit_logs(self):
        # Test Case 7: Clear audit logs coverage
        self.translator.process_error(raw_error="test")
        self.assertEqual(len(self.translator.get_audit_logs()), 1)
        self.translator.clear_audit_logs()
        self.assertEqual(len(self.translator.get_audit_logs()), 0)

    def test_exception_format_failure(self):
        # Test Case 8: Coverage for exception formatting failure
        class UnformattableException(Exception):
            @property
            def __traceback__(self):
                raise Exception("Cannot get traceback")

        result = self.translator.process_error(raw_error=UnformattableException("test"))
        logs = self.translator.get_audit_logs()
        self.assertEqual(len(logs), 1)
        self.assertIn("Failed to format exception", logs[0]["original_error_snippet"])

if __name__ == '__main__':
    unittest.main()
