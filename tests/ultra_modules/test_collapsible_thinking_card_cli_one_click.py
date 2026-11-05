import unittest
import json
import subprocess
import sys
import os
from ultra_modules.collapsible_thinking_card_cli_one_click import adapt_input_data, generate_one_click_cli_output

class FaultyObject:
    def __str__(self):
        raise ValueError("Simulated stringification error")

class TestCollapsibleThinkingCardCliOneClick(unittest.TestCase):
    def test_normal_json_input(self):
        """Test normal usage with valid JSON string."""
        json_data = json.dumps({
            "conclusion": "42",
            "thinking_process": "Multiplied 6 by 7",
            "title": "Math Result",
            "link": "https://example.com"
        })
        card = generate_one_click_cli_output(input_data=json_data)

        self.assertEqual(card["header"]["title"]["content"], "Math Result")
        self.assertIn("**结论：**\n42", card["elements"][0]["content"])
        self.assertEqual(card["elements"][1]["elements"][0]["content"], "Multiplied 6 by 7")
        self.assertEqual(card["card_link"]["url"], "https://example.com")
        self.assertTrue(card["elements"][2]["tag"] == "action") # undo button

    def test_excel_plain_string_input(self):
        """Test Excel plain string input, defaulting to raw_value."""
        plain_text = "This is a conclusion from an Excel cell."
        card = generate_one_click_cli_output(input_data=plain_text)

        self.assertEqual(card["header"]["title"]["content"], "智能推理结果")
        self.assertIn(plain_text, card["elements"][0]["content"])
        self.assertEqual(card["elements"][1]["elements"][0]["content"], "暂无推理过程")

    def test_missing_parameters_fallback(self):
        """Test zero-parameter one-click execution."""
        card = generate_one_click_cli_output()

        self.assertEqual(card["header"]["title"]["content"], "智能推理结果")
        self.assertIn("暂无结论", card["elements"][0]["content"])
        self.assertEqual(card["elements"][1]["elements"][0]["content"], "暂无推理过程")
        self.assertNotIn("card_link", card)

    def test_dirty_data_self_healing(self):
        """Test with dirty data like lists, nested dicts, and invalid JSON strings."""
        # 1. Invalid JSON string
        card1 = generate_one_click_cli_output(input_data="[Unclosed JSON")
        self.assertIn("[Unclosed JSON", card1["elements"][0]["content"])

        # 2. Empty string or None in dict
        card2 = generate_one_click_cli_output(input_data={"conclusion": None, "title": "   "})
        self.assertIn("暂无结论", card2["elements"][0]["content"])
        self.assertEqual(card2["header"]["title"]["content"], "智能推理结果")

        # 3. List input (gets first element if dict, otherwise raw list)
        card3 = generate_one_click_cli_output(input_data=[{"conclusion": "from list dict"}])
        self.assertIn("from list dict", card3["elements"][0]["content"])

        # 4. Empty list
        card4 = generate_one_click_cli_output(input_data=[])
        self.assertIn("暂无结论", card4["elements"][0]["content"])

        # 5. List with plain text
        card5 = generate_one_click_cli_output(input_data=["plain", "list"])
        self.assertIn("['plain', 'list']", card5["elements"][0]["content"])

    def test_extreme_boundary_conditions(self):
        """Test with a faulty object that fails stringification to check adapter robustness."""
        faulty = FaultyObject()
        card = generate_one_click_cli_output(input_data=faulty)

        self.assertEqual(card["header"]["title"]["content"], "智能推理结果")
        self.assertIn("暂无结论", card["elements"][0]["content"])

        # Test string parsing as a non-dict json object
        json_array = json.dumps([1, 2, 3])
        card_array = generate_one_click_cli_output(input_data=json_array)
        self.assertIn("[1, 2, 3]", card_array["elements"][0]["content"])

    def test_title_and_link_provided(self):
        """Test with explicitly provided title and link"""
        card = generate_one_click_cli_output(
            input_data={"conclusion": "test"},
            title="Explicit Title",
            link="https://explicit.com"
        )
        self.assertEqual(card["header"]["title"]["content"], "Explicit Title")
        self.assertEqual(card["card_link"]["url"], "https://explicit.com")

    def test_cli_execution(self):
        """Test the if __name__ == '__main__' block via subprocess"""
        env = os.environ.copy()
        env["PYTHONPATH"] = "."

        result = subprocess.run(
            [sys.executable, "ultra_modules/collapsible_thinking_card_cli_one_click.py"],
            capture_output=True,
            text=True,
            env=env
        )
        self.assertEqual(result.returncode, 0)
        output_data = json.loads(result.stdout)
        self.assertEqual(output_data["header"]["title"]["content"], "智能推理结果")

if __name__ == "__main__":
    unittest.main()
