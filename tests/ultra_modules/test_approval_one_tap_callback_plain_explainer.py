import unittest
import json
from ultra_modules.approval_one_tap_callback_plain_explainer import ApprovalOneTapCallbackPlainExplainer

class TestApprovalOneTapCallbackPlainExplainer(unittest.TestCase):

    def test_generate_card_normal(self):
        """测试正常参数下的卡片生成"""
        result = ApprovalOneTapCallbackPlainExplainer.generate_card(
            action_name="删除核心数据库",
            risk_level="HIGH",
            backend_result={"db_name": "user_db", "tables_affected": 50},
            operator="AdminUser"
        )
        self.assertIn("删除核心数据库", result["markdown"])
        self.assertIn("HIGH", result["markdown"])
        self.assertIn("AdminUser", result["markdown"])
        self.assertIn("user_db", result["markdown"])
        self.assertEqual(result["lark_card_json"]["header"]["template"], "red")

        self.assertIn("<b>⚠️</b>", result["html"])
        self.assertIn("<br>", result["html"])

    def test_generate_card_missing_params(self):
        """测试缺参下的默认兜底"""
        result = ApprovalOneTapCallbackPlainExplainer.generate_card()
        self.assertIn("未知高危操作", result["markdown"])
        self.assertIn("CRITICAL", result["markdown"])
        self.assertIn("未知系统/人员", result["markdown"])
        self.assertIn("（无附加信息）", result["markdown"])
        self.assertEqual(result["lark_card_json"]["header"]["template"], "red")

    def test_generate_card_dirty_data(self):
        """测试脏数据自愈（无效的JSON字符串、异常类型等）"""
        # 测试非法 JSON
        result1 = ApprovalOneTapCallbackPlainExplainer.generate_card(
            action_name="   ",
            risk_level="invalid_risk",
            backend_result="{invalid_json:",
            operator="  "
        )

        # 测试非字典的合法 JSON
        result_array = ApprovalOneTapCallbackPlainExplainer.generate_card(
            backend_result="[1, 2, 3]"
        )
        self.assertIn("raw_parsed: [1, 2, 3]", result_array["markdown"])
        self.assertIn("未知高危操作", result1["markdown"])
        self.assertIn("CRITICAL", result1["markdown"])  # 不在列表中的风险转 CRITICAL
        self.assertIn("未知系统/人员", result1["markdown"])
        self.assertIn("raw_error: {invalid_json:", result1["markdown"])

        # 测试普通类型
        result2 = ApprovalOneTapCallbackPlainExplainer.generate_card(
            backend_result=12345
        )
        self.assertIn("raw: 12345", result2["markdown"])

        # 测试合法 JSON 字符串
        result3 = ApprovalOneTapCallbackPlainExplainer.generate_card(
            backend_result='{"key": "value"}'
        )
        self.assertIn("value", result3["markdown"])

        # 测试 raw None
        result4 = ApprovalOneTapCallbackPlainExplainer.generate_card(
            backend_result=None
        )
        self.assertIn("（无附加信息）", result4["markdown"])

        result5 = ApprovalOneTapCallbackPlainExplainer.generate_card(
            backend_result={}
        )
        self.assertIn("（无附加信息）", result5["markdown"])

    def test_sync_callback_status_normal(self):
        """测试正常回调状态解析"""
        # 批准
        res_approve1 = ApprovalOneTapCallbackPlainExplainer.sync_callback_status({"action": "approve"})
        self.assertEqual(res_approve1["status"], "success")
        self.assertEqual(res_approve1["action"], "approve")

        res_approve2 = ApprovalOneTapCallbackPlainExplainer.sync_callback_status('{"value": {"action": "yes"}}')
        self.assertEqual(res_approve2["status"], "success")
        self.assertEqual(res_approve2["action"], "approve")

        # 驳回
        res_reject1 = ApprovalOneTapCallbackPlainExplainer.sync_callback_status({"action": "reject"})
        self.assertEqual(res_reject1["status"], "success")
        self.assertEqual(res_reject1["action"], "reject")

        res_reject2 = ApprovalOneTapCallbackPlainExplainer.sync_callback_status('{"value": {"action": "false"}}')
        self.assertEqual(res_reject2["status"], "success")
        self.assertEqual(res_reject2["action"], "reject")

    def test_sync_callback_status_edge_cases(self):
        """测试回调状态的极端边界条件与错误处理"""
        # 为空
        res_empty = ApprovalOneTapCallbackPlainExplainer.sync_callback_status(None)
        self.assertEqual(res_empty["status"], "error")
        self.assertEqual(res_empty["action"], "unknown")

        # 字符串类型无效 JSON
        res_invalid_json = ApprovalOneTapCallbackPlainExplainer.sync_callback_status("{bad_json}")
        self.assertEqual(res_invalid_json["status"], "error")
        self.assertEqual(res_invalid_json["action"], "unknown")

        # 非字典数据
        res_not_dict = ApprovalOneTapCallbackPlainExplainer.sync_callback_status("[]")
        self.assertEqual(res_not_dict["status"], "error")
        self.assertEqual(res_not_dict["action"], "unknown")

        res_num = ApprovalOneTapCallbackPlainExplainer.sync_callback_status(123)
        self.assertEqual(res_num["status"], "error")
        self.assertEqual(res_num["action"], "unknown")

        # 字典中无有效 action
        res_no_action = ApprovalOneTapCallbackPlainExplainer.sync_callback_status({"foo": "bar"})
        self.assertEqual(res_no_action["status"], "error")
        self.assertIn("未知的操作指令", res_no_action["message"])
        self.assertEqual(res_no_action["action"], "unknown")

        # 字典中只有 value，但不是 dict
        res_bad_value = ApprovalOneTapCallbackPlainExplainer.sync_callback_status({"value": "approve"})
        self.assertEqual(res_bad_value["status"], "error")
        self.assertEqual(res_bad_value["action"], "unknown")

        # action 指令不认识
        res_unknown_action = ApprovalOneTapCallbackPlainExplainer.sync_callback_status({"action": "maybe"})
        self.assertEqual(res_unknown_action["status"], "error")
        self.assertEqual(res_unknown_action["action"], "maybe")

if __name__ == '__main__':
    unittest.main()
