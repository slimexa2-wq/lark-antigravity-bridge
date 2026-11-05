import unittest
import json
from ultra_modules.voice_message_intent_parser_plain_explainer import VoiceMessageIntentParserPlainExplainer


class TestVoiceMessageIntentParserPlainExplainer(unittest.TestCase):

    def setUp(self):
        self.parser = VoiceMessageIntentParserPlainExplainer()

    def test_normal_intent(self):
        """Test with normal valid data for json export."""
        data = {
            "intent": "核对提成表",
            "confidence": 0.95,
            "entities": {"月份": "本月", "目标人": "销售部"}
        }
        result = self.parser.parse_to_card(data, export_format="json")
        res_json = json.loads(result)

        self.assertEqual(res_json["intent"], "核对提成表")
        self.assertEqual(res_json["confidence_score"], "95%")
        self.assertEqual(res_json["entities"]["月份"], "本月")
        self.assertIn("核对提成表", res_json["summary"])
        self.assertIn("【月份】设为 本月", res_json["summary"])

    def test_dirty_data_recovery(self):
        """Test with dirty/invalid data, e.g., bad json string, None values."""
        # 1. Bad JSON String
        result1 = self.parser.parse_to_card("not a valid json", export_format="markdown")
        self.assertIn("未知操作", result1)
        self.assertIn("0%", result1)

        # 2. None data
        result2 = self.parser.parse_to_card(None, export_format="markdown")
        self.assertIn("未知操作", result2)

        # 3. Invalid types in dictionary
        data_invalid = {
            "intent": 12345,  # should be string
            "confidence": "not a float", # should be float
            "entities": "not a dict" # should be dict
        }
        result3 = self.parser.parse_to_card(data_invalid, export_format="json")
        res_json = json.loads(result3)
        self.assertEqual(res_json["intent"], "未知操作")
        self.assertEqual(res_json["confidence_score"], "0%")
        self.assertEqual(res_json["entities"], {})

    def test_missing_parameters_fallback(self):
        """Test when parameters are completely missing from dict."""
        data = {}
        result = self.parser.parse_to_card(data, export_format="html")
        self.assertIn("未知操作", result)
        self.assertIn("0%", result)
        self.assertIn("无附加参数", result)

        # Test low confidence summary
        data_low_conf = {"confidence": 0.2, "intent": "测试"}
        result_low_conf = self.parser.parse_to_card(data_low_conf, export_format="markdown")
        self.assertIn("无法确定您的需求，请尝试重新发送语音或换个说法", result_low_conf)

        # Missing entities shouldn't crash
        data_no_entities = {"confidence": 0.8, "intent": "查考勤"}
        result_no_entities = self.parser.parse_to_card(data_no_entities, export_format="json")
        res = json.loads(result_no_entities)
        self.assertIn("暂未发现相关的补充细节", res["summary"])

    def test_extreme_confidence_boundaries(self):
        """Test confidence out of bounds."""
        data_high = {"intent": "A", "confidence": 1.5}
        res_high = self.parser.parse_to_card(data_high, export_format="json")
        self.assertEqual(json.loads(res_high)["confidence_score"], "100%")

        data_low = {"intent": "A", "confidence": -0.5}
        res_low = self.parser.parse_to_card(data_low, export_format="json")
        self.assertEqual(json.loads(res_low)["confidence_score"], "0%")

    def test_empty_string_values_in_entities(self):
        """Test entities with empty strings or None."""
        data = {
            "intent": "测试",
            "confidence": 0.9,
            "entities": {"A": "", "B": None, "C": "有效"}
        }
        res = self.parser.parse_to_card(data, export_format="json")
        parsed = json.loads(res)
        self.assertNotIn("【A】设为", parsed["summary"])
        self.assertNotIn("【B】设为", parsed["summary"])
        self.assertIn("【C】设为 有效", parsed["summary"])

    def test_all_export_formats(self):
        """Test that json, markdown, html and default formats all work."""
        data = {"intent": "格式测试", "confidence": 0.9, "entities": {"P": "V"}}

        # HTML
        res_html = self.parser.parse_to_card(data, export_format="html")
        self.assertIn("<div class=\"intent-card\"", res_html)
        self.assertIn("<li><strong>P:</strong> V</li>", res_html)

        # Markdown (Explicit)
        res_md = self.parser.parse_to_card(data, export_format="markdown")
        self.assertIn("### 🎙️ 语音指令解析结果", res_md)
        self.assertIn("**P**: V", res_md)

        # Default (Unrecognized format defaults to markdown)
        res_default = self.parser.parse_to_card(data, export_format=123) # type: ignore
        self.assertIn("### 🎙️ 语音指令解析结果", res_default)

if __name__ == '__main__':
    unittest.main()
