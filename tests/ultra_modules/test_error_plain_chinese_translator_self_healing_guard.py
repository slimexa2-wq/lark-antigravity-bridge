import unittest
import time
from ultra_modules.error_plain_chinese_translator_self_healing_guard import ErrorPlainChineseTranslatorSelfHealingGuard

class TestErrorPlainChineseTranslatorSelfHealingGuard(unittest.TestCase):
    def setUp(self):
        self.guard = ErrorPlainChineseTranslatorSelfHealingGuard()

    def test_normal_processing(self):
        """测试正常错误处理（覆盖常见的各种已知和未知错误模式）"""
        # 测试 timeout
        res = self.guard.translate_and_heal("Connection timeout on 8080")
        self.assertTrue(res["is_healed"])
        self.assertIn("网络请求超时", res["plain_chinese_explanation"])
        self.assertEqual(res["healed_state"], {"action": "retry_network", "delay": 2000})

        # 测试 null pointer
        res = self.guard.translate_and_heal({"message": "Null pointer exception"})
        self.assertTrue(res["is_healed"])
        self.assertIn("空值", res["plain_chinese_explanation"])
        self.assertEqual(res["healed_state"], {"action": "fill_default_values"})

        # 测试 permission denied
        res = self.guard.translate_and_heal("Error 403: Forbidden access")
        self.assertFalse(res["is_healed"])
        self.assertIn("没有权限", res["plain_chinese_explanation"])

        # 测试 database
        res = self.guard.translate_and_heal("SQL query failed in database")
        self.assertFalse(res["is_healed"])
        self.assertIn("数据库", res["plain_chinese_explanation"])

        # 测试 format/syntax
        res = self.guard.translate_and_heal("Invalid JSON format syntax")
        self.assertTrue(res["is_healed"])
        self.assertIn("数据格式", res["plain_chinese_explanation"])

        # 测试 未知错误
        res = self.guard.translate_and_heal("Some random error that is unknown")
        self.assertFalse(res["is_healed"])
        self.assertIn("未知错误", res["plain_chinese_explanation"])

    def test_dirty_data_self_healing(self):
        """测试脏数据自愈（各种异常输入类型）"""
        # 输入 None
        res = self.guard.translate_and_heal(None)
        self.assertEqual(res["original_error"], "未提供错误信息")

        # 输入只包含空白的字符串
        res = self.guard.translate_and_heal("   \n   ")
        self.assertEqual(res["original_error"], "未提供错误信息")

        # 输入缺少关键字段的字典
        res = self.guard.translate_and_heal({"some_key": "value"})
        self.assertEqual(res["original_error"], "未提供错误信息")

        # 输入非字符串且非字典的数据，例如整数或列表
        res = self.guard.translate_and_heal(12345)
        self.assertEqual(res["original_error"], "12345")

        res = self.guard.translate_and_heal([1, 2, 3])
        self.assertEqual(res["original_error"], "[1, 2, 3]")

    def test_missing_params_fallback(self):
        """测试缺参情况下的默认兜底逻辑"""
        # 完全不传参数
        res = self.guard.translate_and_heal()
        self.assertEqual(res["original_error"], "未提供错误信息")
        self.assertFalse(res["is_healed"])
        self.assertIsNotNone(res["snapshot_id"])

        # 传错 context 类型 (比如传个整数而不是字典)
        context_mock = 999
        res = self.guard.translate_and_heal("error!", context=context_mock)
        # 应静默清理 context 并生成正常快照，而不是崩溃
        self.assertIsNotNone(res["snapshot_id"])

        # 撤回时传无效的快照 ID 类型
        undo_res = self.guard.undo_snapshot(12345)
        self.assertFalse(undo_res["success"])
        self.assertIn("无效", undo_res["message"])

        # 撤回时不传参数
        undo_res = self.guard.undo_snapshot()
        self.assertFalse(undo_res["success"])

    def test_extreme_boundary(self):
        """测试极端边界：超长错误信息的截断机制"""
        large_error = "A" * 10000
        res = self.guard.translate_and_heal(large_error)

        self.assertTrue(res["is_truncated"])
        self.assertTrue(len(res["original_error"]) < 6000)
        self.assertTrue(res["original_error"].endswith("...[截断]"))

    def test_snapshot_and_undo_mechanism(self):
        """测试 5 秒快照有效期和一键撤回功能"""
        # 测试正常的撤回
        context = {"current_state": {"step": 1, "data": "old_data"}}
        res = self.guard.translate_and_heal("test error", context=context)
        snapshot_id = res["snapshot_id"]

        undo_res = self.guard.undo_snapshot(snapshot_id)
        self.assertTrue(undo_res["success"])
        self.assertEqual(undo_res["restored_state"], {"step": 1, "data": "old_data"})

        # 快照只能撤回一次
        undo_res2 = self.guard.undo_snapshot(snapshot_id)
        self.assertFalse(undo_res2["success"])

        # 测试 5 秒超时清理机制 (使用猴子补丁或直接改 _snapshots 时间)
        res2 = self.guard.translate_and_heal("test error 2", context=context)
        snapshot_id2 = res2["snapshot_id"]

        # 手动把快照时间改老
        self.guard._snapshots[snapshot_id2]["timestamp"] = time.time() - 6.0

        # 此时撤回应失败并被静默清理
        undo_res3 = self.guard.undo_snapshot(snapshot_id2)
        self.assertFalse(undo_res3["success"])
        self.assertIn("超过5秒可撤回时间", undo_res3["message"])

if __name__ == '__main__':
    unittest.main()
