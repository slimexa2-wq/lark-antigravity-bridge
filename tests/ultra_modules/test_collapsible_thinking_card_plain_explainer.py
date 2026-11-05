import unittest
import json
from ultra_modules.collapsible_thinking_card_plain_explainer import build_explainer_card, PlainExplainerCardBuilder

class TestCollapsibleThinkingCardPlainExplainer(unittest.TestCase):

    def test_normal_input_json(self):
        """Test case 1: Normal valid inputs with JSON format."""
        data = {
            "conclusion": "业务已确认通过。",
            "thinking_process": "步骤1: 核对信息。步骤2: 通过检查。",
            "undo_action_id": "undo_12345",
            "status": "success"
        }
        result = build_explainer_card(data, "json")
        card = json.loads(result)

        self.assertEqual(card["header"]["template"], "blue")
        # Conclusion is in elements[0]
        self.assertIn("业务已确认通过", card["elements"][0]["text"]["content"])
        # Thinking process is in elements[2]
        self.assertIn("步骤1: 核对信息", card["elements"][2]["elements"][0]["content"])
        # Undo button is in elements[3]
        self.assertEqual(card["elements"][3]["actions"][0]["value"]["undo_id"], "undo_12345")

    def test_missing_parameters_fallback(self):
        """Test case 2: Empty or missing parameters, checking auto-healing default fallback."""
        data = {}
        result = build_explainer_card(data, "markdown")

        self.assertIn("系统已完成处理，一切正常。", result)
        self.assertIn("后台自动推导与处理过程已隐藏。", result)
        self.assertIn("default_undo_id", result)

    def test_dirty_data_auto_healing(self):
        """Test case 3: Dirty data (e.g., passing invalid JSON string or None)."""
        # Testing with None
        result_none = build_explainer_card(None, "html")
        self.assertIn("系统已完成处理，一切正常。", result_none)

        # Testing with invalid JSON string
        result_invalid_json = build_explainer_card("{invalid json string", "json")
        card = json.loads(result_invalid_json)
        self.assertIn("系统已完成处理", card["elements"][0]["text"]["content"])

        # Testing with valid JSON string (it should load correctly)
        valid_json_str = '{"conclusion": "Valid JSON String"}'
        result_valid_json = build_explainer_card(valid_json_str, "md")
        self.assertIn("Valid JSON String", result_valid_json)

        # Testing with incorrect types for values
        data_wrong_types = {
            "conclusion": 12345,
            "thinking_process": ["list", "of", "steps"],
            "undo_action_id": {"id": "1"}
        }
        result_wrong_types = build_explainer_card(data_wrong_types, "md")
        self.assertIn("12345", result_wrong_types)
        self.assertIn("['list', 'of', 'steps']", result_wrong_types)

    def test_extreme_boundary_cases(self):
        """Test case 4: Extreme string length boundary cases."""
        huge_string = "A" * 20000
        data = {
            "conclusion": huge_string,
            "thinking_process": huge_string,
        }

        builder = PlainExplainerCardBuilder(data)
        # Ensure it got truncated
        self.assertEqual(len(builder.data["conclusion"]), 5000)
        self.assertEqual(len(builder.data["thinking_process"]), 10000)

    def test_fallback_for_format_parameter(self):
        """Test case 5: Fallback testing for format parameter (e.g., None, integer, unknown)."""
        data = {"conclusion": "Format test"}

        # Unknown format defaults to json
        result_unknown = build_explainer_card(data, "unknown_format")
        # Should be a parseable JSON
        json.loads(result_unknown)

        # Non-string format defaults to json
        result_int = build_explainer_card(data, 123)
        json.loads(result_int)

        result_none = build_explainer_card(data, None)
        json.loads(result_none)

if __name__ == '__main__':
    unittest.main()
