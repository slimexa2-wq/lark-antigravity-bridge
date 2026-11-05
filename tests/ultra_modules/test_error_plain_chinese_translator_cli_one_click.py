import unittest
import json
from unittest.mock import patch
from io import StringIO

from ultra_modules.error_plain_chinese_translator_cli_one_click import ErrorPlainChineseTranslator, main

class TestErrorPlainChineseTranslator(unittest.TestCase):

    def test_normal_execution(self):
        """测试正常执行 (Normal execution)"""
        translator = ErrorPlainChineseTranslator(mode="json")
        trace = "Traceback (most recent call last):\n  File \"<stdin>\", line 1, in <module>\nTypeError: unsupported operand type(s) for +: 'int' and 'str'"
        result_json = translator.process_and_output(trace)
        result = json.loads(result_json)

        # Verify the Lark card structure
        self.assertIn("elements", result)
        text_content = result["elements"][0]["text"]["content"]
        self.assertIn("数据类型不匹配", text_content)
        self.assertIn("程序尝试对错误类型的数据执行操作", text_content)

    def test_dirty_data_healing(self):
        """测试脏数据自愈 (Dirty data self-healing)"""
        translator = ErrorPlainChineseTranslator(mode="excel")
        # Dirty data: spaces, empty lines
        dirty_trace = "   \n  \n  "
        result_csv = translator.process_and_output(dirty_trace)

        # Should fallback to unknown error
        self.assertIn("未知异常 (Unknown Error)", result_csv)
        self.assertIn("未知运行时异常", result_csv)

    def test_missing_parameters_fallback(self):
        """测试缺参默认兜底 (Missing parameter fallback)"""
        translator = ErrorPlainChineseTranslator(mode="json")
        # Empty string
        result_empty_json = translator.process_and_output("")
        result_empty = json.loads(result_empty_json)
        self.assertIn("未知运行时异常", result_empty["elements"][0]["text"]["content"])

        # None value
        result_none_json = translator.process_and_output(None)
        result_none = json.loads(result_none_json)
        self.assertIn("未知运行时异常", result_none["elements"][0]["text"]["content"])

    def test_extreme_boundary_conditions(self):
        """测试极端边界条件 (Extreme boundary conditions)"""
        # Invalid mode should fallback to json
        translator = ErrorPlainChineseTranslator(mode="invalid_mode")
        self.assertEqual(translator.mode, "json")

        # Extremely long error trace with special chars
        long_trace = "A" * 10000 + "\nSyntaxError: invalid syntax!@#$%^&*()"
        result_json = translator.process_and_output(long_trace)
        result = json.loads(result_json)

        text_content = result["elements"][0]["text"]["content"]
        self.assertIn("代码语法错误", text_content)

        # Verify it handled the large payload
        trace_in_card = result["elements"][2]["columns"][0]["elements"][0]["content"]
        self.assertIn("SyntaxError: invalid syntax", trace_in_card)
        # Verify collapsible tags are present
        self.assertIn("<details><summary>👉 点击展开查看详细堆栈数据</summary>", trace_in_card)

    @patch("sys.stdout", new_callable=StringIO)
    @patch("sys.argv", ["error_plain_chinese_translator_cli_one_click.py"])
    def test_zero_configuration_cli_execution(self, mock_stdout):
        """测试零配置 CLI 执行 (Zero-configuration CLI execution)"""
        main()
        output = mock_stdout.getvalue()

        # Parse output as JSON
        result = json.loads(output.strip())

        # Default error should be FileNotFoundError
        text_content = result["elements"][0]["text"]["content"]
        self.assertIn("找不到文件", text_content)
        self.assertIn("程序试图读取或写入的文件在指定路径下不存在", text_content)

if __name__ == '__main__':
    unittest.main()
