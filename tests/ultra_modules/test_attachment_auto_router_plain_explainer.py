import unittest
from ultra_modules.attachment_auto_router_plain_explainer import explain_routing_result

class TestAttachmentAutoRouterPlainExplainer(unittest.TestCase):
    def test_normal_routing_result(self):
        data = {
            "filename": "Q3提成表.xlsx",
            "routed_to": "commission",
            "confidence": 0.95,
            "reasoning": "发现关键表头：提成金额、销售员"
        }
        card = explain_routing_result(routing_result=data)

        self.assertEqual(card["msg_type"], "interactive")
        self.assertEqual(card["card"]["header"]["title"]["content"], "文件智能路由结果")
        elements = card["card"]["elements"]

        # 3 elements: summary, collapsible details, undo action
        self.assertEqual(len(elements), 3)

        # Summary markdown
        self.assertEqual(elements[0]["tag"], "markdown")
        self.assertIn("接收文件", elements[0]["content"])
        self.assertIn("Q3提成表.xlsx", elements[0]["content"])
        self.assertIn("提成引擎", elements[0]["content"])
        self.assertIn("95.0%", elements[0]["content"])

        # Collapsible Panel
        self.assertEqual(elements[1]["tag"], "collapsible_panel")
        self.assertIn("展开查看路由详细特征与原始数据", elements[1]["header"]["title"]["content"])
        self.assertIn("发现关键表头：提成金额、销售员", elements[1]["elements"][0]["content"])

        # Action
        self.assertEqual(elements[2]["tag"], "action")
        self.assertEqual(elements[2]["actions"][0]["value"]["action"], "undo")

    def test_dirty_data_self_healing(self):
        # Passing weird strings instead of dict
        card_str = explain_routing_result(routing_result="this is not a dictionary")
        self.assertIn("未知文件", card_str["card"]["elements"][0]["content"])
        self.assertIn("未知类型", card_str["card"]["elements"][0]["content"])

        # Passing valid JSON string
        valid_json_str = '{"filename": "标书.docx", "routed_to": "tender_document"}'
        card_json = explain_routing_result(routing_result=valid_json_str)
        self.assertIn("标书.docx", card_json["card"]["elements"][0]["content"])
        self.assertIn("标书引擎", card_json["card"]["elements"][0]["content"])

    def test_missing_params_default_fallback(self):
        # Empty dict
        card_empty = explain_routing_result(routing_result={})
        self.assertIn("未知文件", card_empty["card"]["elements"][0]["content"])
        self.assertIn("未知类型", card_empty["card"]["elements"][0]["content"])
        self.assertIn("未知", card_empty["card"]["elements"][0]["content"]) # confidence unknown

        # None
        card_none = explain_routing_result(routing_result=None, title=None)
        self.assertEqual(card_none["card"]["header"]["title"]["content"], "文件智能路由结果")

    def test_extreme_boundary_conditions(self):
        # Confidence as string and invalid formats
        data = {
            "filename": None,
            "routed_to": "unknown",
            "confidence": "abc", # should fallback
            "reasoning": None
        }
        card = explain_routing_result(routing_result=data, show_undo=False)
        elements = card["card"]["elements"]

        # Action should be missing
        self.assertEqual(len(elements), 2)
        self.assertIn("未知文件", elements[0]["content"])
        self.assertIn("未知", elements[0]["content"]) # confidence
        self.assertIn("未知类型", elements[0]["content"])
        self.assertIn("系统根据文件内容与特征自动推断", elements[1]["elements"][0]["content"]) # fallback reasoning

    def test_all_engine_mappings(self):
        engines = [
            ("weekly_report", "周报引擎"),
            ("commission", "提成引擎"),
            ("tender_document", "标书引擎"),
            ("comic_drama", "漫剧引擎"),
            ("something_else", "未知类型，需人工处理")
        ]

        for eng, expected_name in engines:
            card = explain_routing_result(routing_result={"routed_to": eng})
            self.assertIn(expected_name, card["card"]["elements"][0]["content"])

if __name__ == '__main__':
    unittest.main()
