import unittest
from ultra_modules.partial_markdown_healer_plain_explainer import heal_markdown, heal_json, generate_explainer_card

class TestPartialMarkdownHealerPlainExplainer(unittest.TestCase):

    def test_heal_markdown_code_block(self):
        # Missing closing ```
        raw = "Here is some code:\n```python\nprint('hello')\n"
        healed = heal_markdown(raw)
        self.assertTrue(healed.endswith("```"))
        self.assertEqual(healed.count("```"), 2)

    def test_heal_markdown_bold(self):
        # Missing closing **
        raw = "This is **bold text"
        healed = heal_markdown(raw)
        self.assertTrue(healed.endswith("**"))
        self.assertEqual(healed.count("**"), 2)

    def test_heal_markdown_table(self):
        # Missing closing |
        raw = "| Header 1 | Header 2 |\n|---|---|\n| Value 1 | Value 2"
        healed = heal_markdown(raw)
        self.assertTrue(healed.endswith("|"))
        self.assertTrue(healed.splitlines()[-1].endswith("|"))

    def test_heal_json_normal(self):
        raw = '{"key": "value"}'
        healed = heal_json(raw)
        self.assertEqual(healed, {"key": "value"})

    def test_heal_json_truncated_dict(self):
        # Missing closing brace and quote
        raw = '{"key": "value'
        healed = heal_json(raw)
        self.assertEqual(healed, {"key": "value"})

    def test_heal_json_truncated_array(self):
        # Missing closing bracket
        raw = '[{"key": "value"}'
        healed = heal_json(raw)
        self.assertEqual(healed, [{"key": "value"}])

    def test_heal_json_trailing_comma(self):
        # Trailing comma before closing brace
        # But our heuristic handles trailing comma at the end of the text.
        # Let's test truncated string with trailing comma
        raw = '{"key": "value",'
        healed = heal_json(raw)
        self.assertEqual(healed, {"key": "value"})

    def test_heal_json_unrecoverable(self):
        # Completely broken
        raw = '{"key": {unquoted_value}}'
        healed = heal_json(raw)
        self.assertIn("error", healed)

    def test_generate_explainer_card_defaults(self):
        # Zero params
        result = generate_explainer_card()
        self.assertIn("markdown", result)
        self.assertIn("html", result)
        self.assertIn("json_data", result)
        self.assertEqual(result["json_data"], {})

    def test_generate_explainer_card_with_content(self):
        raw = '{"status": "ok", "message": "hello'
        result = generate_explainer_card(raw_content=raw)
        self.assertEqual(result["json_data"], {"status": "ok", "message": "hello"})
        self.assertIn("分析结论卡", result["markdown"])
        self.assertIn("explainer-card", result["html"])

if __name__ == '__main__':
    unittest.main()
