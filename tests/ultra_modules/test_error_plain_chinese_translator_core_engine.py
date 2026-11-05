import unittest
import sys
import os

# 将父目录加入 PYTHONPATH，以确保可以正常引入模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from ultra_modules.error_plain_chinese_translator_core_engine import translate_error_to_plain_chinese


class TestErrorPlainChineseTranslatorCoreEngine(unittest.TestCase):

    def test_missing_parameter(self):
        """测试缺参（不传参）时的默认兜底行为"""
        result = translate_error_to_plain_chinese()
        self.assertEqual(result["title"], "未知错误")
        self.assertIn("未获取到具体的错误日志", result["reason"])

    def test_dirty_data_none(self):
        """测试传入 None 时的静默清洗行为"""
        result = translate_error_to_plain_chinese(None)
        self.assertEqual(result["title"], "未知错误")
        self.assertIn("未获取到具体的错误日志", result["reason"])

    def test_dirty_data_integer(self):
        """测试传入非字符串数据（例如整数）时的行为"""
        result = translate_error_to_plain_chinese(403)
        self.assertEqual(result["title"], "无访问权限")
        self.assertIn("当前账号没有执行此操作或访问该数据的权限", result["reason"])

    def test_known_error_null_pointer(self):
        """测试已知的错误类型（NullPointerException）正常翻译"""
        error_msg = "java.lang.NullPointerException at com.example.service.UserService.getUser"
        result = translate_error_to_plain_chinese(error_msg)
        self.assertEqual(result["title"], "数据缺失异常")
        self.assertIn("发现某个关键信息是空的", result["reason"])

    def test_known_error_timeout_with_spaces(self):
        """测试已知错误类型包含多余空格时的表现"""
        error_msg = "    Connection timed out : Connection refused    "
        result = translate_error_to_plain_chinese(error_msg)
        self.assertEqual(result["title"], "网络请求失败")
        self.assertIn("超时或被拒绝", result["reason"])

    def test_extreme_edge_case_uncastable_object(self):
        """测试无法转换为字符串的极端对象"""
        class BadObject:
            def __str__(self):
                raise Exception("Cannot cast to string")

        bad_obj = BadObject()
        result = translate_error_to_plain_chinese(bad_obj)
        # 因为转换为字符串失败，应该按空字符串兜底处理
        self.assertEqual(result["title"], "未知错误")

    def test_unknown_error_snippet(self):
        """测试未匹配的未知错误，且超出 50 字符被截断摘要的功能"""
        error_msg = "This is a very long and completely unknown error message that should exceed the fifty character limit and be truncated."
        result = translate_error_to_plain_chinese(error_msg)
        self.assertEqual(result["title"], "系统运行异常")
        self.assertIn("日志摘要：This is a very long and completely unknown error m...", result["reason"])

    def test_unknown_error_short(self):
        """测试未匹配的短未知错误"""
        error_msg = "Bad gateway"
        result = translate_error_to_plain_chinese(error_msg)
        self.assertEqual(result["title"], "系统运行异常")
        self.assertIn("日志摘要：Bad gateway", result["reason"])

if __name__ == '__main__':
    unittest.main()
