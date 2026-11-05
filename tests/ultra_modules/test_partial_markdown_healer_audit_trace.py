import unittest
from ultra_modules.partial_markdown_healer_audit_trace import heal_content_with_audit

class TestPartialMarkdownHealerAuditTrace(unittest.TestCase):

    def test_normal_markdown_no_healing_needed(self):
        # Normal content doesn't need healing
        content = "Here is some text.\n\n```python\nprint('hello')\n```\n\n**Bold Text**"
        healed, trace = heal_content_with_audit(content, format="auto")
        self.assertEqual(healed, content)

        # Verify trace
        self.assertTrue(any(t["step"] == "format_determined" and t["details"]["determined_format"] == "markdown" for t in trace))
        end_trace = next(t for t in trace if t["step"] == "markdown_heal_end")
        self.assertFalse(end_trace["details"]["is_modified"])
        self.assertEqual(len(end_trace["details"]["healed_parts"]), 0)

    def test_dirty_data_json_unclosed_string_and_object(self):
        # Truncated JSON
        content = '{"name": "John", "age": 30, "address": {"city": "New York", "street": "Broadway'
        healed, trace = heal_content_with_audit(content, format="json")

        self.assertTrue(healed.endswith('"}}'))
        self.assertTrue(healed.startswith('{'))
        self.assertTrue(healed.endswith('Broadway"}}'))
        self.assertEqual(healed, '{"name": "John", "age": 30, "address": {"city": "New York", "street": "Broadway"}}')

        # Verify trace
        self.assertTrue(any(t["step"] == "format_determined" and t["details"]["determined_format"] == "json" for t in trace))
        end_trace = next(t for t in trace if t["step"] == "json_heal_end")
        self.assertTrue(end_trace["details"]["is_modified"])
        self.assertIn("closed_string", end_trace["details"]["healed_parts"])
        self.assertIn("closed_object", end_trace["details"]["healed_parts"])

    def test_missing_params_fallback(self):
        # Missing or invalid input fallback
        healed, trace = heal_content_with_audit(None)
        self.assertEqual(healed, "")

        normalized_trace = next(t for t in trace if t["step"] == "input_normalized")
        self.assertTrue(normalized_trace["details"]["is_empty"])

        # Another invalid input
        healed, trace = heal_content_with_audit(12345)
        self.assertEqual(healed, "12345")

        format_trace = next(t for t in trace if t["step"] == "format_determined")
        self.assertEqual(format_trace["details"]["determined_format"], "markdown")

    def test_extreme_boundary_multiple_markdown_errors(self):
        # Extreme boundaries with multiple markdown issues
        content = "Here is an issue:\n```python\ndef test(): pass\n\nAlso some **bold text"
        healed, trace = heal_content_with_audit(content)

        self.assertTrue(healed.endswith('\n```**'))

        end_trace = next(t for t in trace if t["step"] == "markdown_heal_end")
        self.assertTrue(end_trace["details"]["is_modified"])
        self.assertIn("closed_code_block", end_trace["details"]["healed_parts"])
        self.assertIn("closed_bold", end_trace["details"]["healed_parts"])

    def test_table_handling(self):
        # Handling unclosed table
        content = "| Name | Age |\n|---|---|\n| Alice | 25 |\n| Bob | 30 "
        healed, trace = heal_content_with_audit(content)

        self.assertTrue(healed.endswith('|'))

        end_trace = next(t for t in trace if t["step"] == "markdown_heal_end")
        self.assertTrue(end_trace["details"]["is_modified"])
        self.assertIn("closed_table", end_trace["details"]["healed_parts"])

if __name__ == "__main__":
    unittest.main()
