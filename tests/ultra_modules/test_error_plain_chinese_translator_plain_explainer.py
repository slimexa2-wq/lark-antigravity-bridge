import unittest
import json
from ultra_modules.error_plain_chinese_translator_plain_explainer import generate_error_card

class TestErrorPlainChineseTranslatorPlainExplainer(unittest.TestCase):

    def test_normal_json(self):
        """Test normal condition generating JSON card."""
        error_msg = "Error 403: Forbidden - Permission denied"
        result = generate_error_card(error_msg, "json")
        result_dict = json.loads(result)
        self.assertEqual(result_dict["title"], "🔒 权限不足")
        self.assertIn("您当前的账号没有执行这个操作的权限", result_dict["explanation"])
        self.assertIn("一键重试 / 自愈", result_dict["action"])

    def test_normal_html(self):
        """Test normal condition generating HTML card."""
        error_msg = "Connection Refused: Failed to connect to port 8080"
        result = generate_error_card(error_msg, "html")
        self.assertIn('<div class="error-card"', result)
        self.assertIn("🔌 网络连接不通", result)
        self.assertIn("一键重试 / 自愈</button>", result)

    def test_normal_markdown(self):
        """Test normal condition generating Markdown card."""
        error_msg = "java.lang.NullPointerException at com.example.MyClass"
        result = generate_error_card(error_msg, "markdown")
        self.assertTrue(result.startswith("### 📉 数据缺失"))
        self.assertIn("**原因：** 系统在处理任务时，发现有一个必要的数据是空的", result)
        self.assertIn("[ 一键重试 / 自愈 ]", result)

    def test_out_of_memory_markdown(self):
        """Test Out Of Memory error matching."""
        error_msg = "java.lang.OutOfMemoryError: Java heap space"
        result = generate_error_card(error_msg, "markdown")
        self.assertTrue(result.startswith("### 💾 内存不足"))
        self.assertIn("**原因：** 这次处理的数据量太大了，超出了系统当前能承受的极限。", result)

    def test_dirty_data_missing_param_fallback(self):
        """Test dirty data/missing parameter fallback."""
        # Missing/invalid format type
        result1 = generate_error_card("Some error", "xml")
        self.assertTrue(result1.startswith("### ⚠️ 系统开小差了"))

        # Missing error_trace parameter (None)
        result2 = generate_error_card(None, "markdown")
        self.assertTrue(result2.startswith("### ⚠️ 系统开小差了"))

        # Dirty data (integer instead of string)
        result3 = generate_error_card(12345, "markdown")
        self.assertTrue(result3.startswith("### ⚠️ 系统开小差了"))

        # Dirty data (dict instead of string)
        result4 = generate_error_card({"error": "test"}, "markdown")
        self.assertTrue(result4.startswith("### ⚠️ 系统开小差了"))

        # Extreme dirty data (object that fails str() conversion)
        class BadStr:
            def __str__(self):
                raise ValueError("cannot convert to string")

        result5 = generate_error_card(BadStr(), "markdown")
        self.assertTrue(result5.startswith("### ⚠️ 系统开小差了"))

    def test_extreme_boundary_condition(self):
        """Test extreme boundary condition (extremely long traceback string)."""
        long_traceback = "A" * 200000 + "Connection Refused"
        result = generate_error_card(long_traceback, "markdown")
        # Should not crash and should fall back since "Connection Refused" is truncated
        self.assertTrue(result.startswith("### ⚠️ 系统开小差了"))

        # If the keyword is within the 100,000 char limit
        long_traceback_2 = "Connection Refused" + "A" * 200000
        result_2 = generate_error_card(long_traceback_2, "markdown")
        self.assertTrue(result_2.startswith("### 🔌 网络连接不通"))

if __name__ == '__main__':
    unittest.main()
