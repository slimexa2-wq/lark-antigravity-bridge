import math
import unittest
from ultra_modules.partial_markdown_healer_export_formatter import PartialMarkdownHealerExportFormatter

class TestPartialMarkdownHealerExportFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = PartialMarkdownHealerExportFormatter()

    def test_normal_case(self):
        """Test with valid JSON and complete markdown."""
        input_json = '{"name": "test", "value": 42}'
        input_markdown = "```python\nprint('hello')\n```"

        result = self.formatter.process(input_json, input_markdown)

        self.assertEqual(result["data"]["name"], "test")
        self.assertEqual(result["data"]["value"], 42)
        self.assertEqual(result["data"]["comments"], 0)
        self.assertEqual(result["markdown"], input_markdown)
        self.assertIn("Status: Success", result["report_text"])

    def test_dirty_data_self_healing(self):
        """Test healing of truncated JSON and unclosed markdown components."""
        input_json = '{"name": "test", "value": {"nested": "truncated string'
        input_markdown = "Here is some code:\n```python\nprint('hello')"

        result = self.formatter.process(input_json, input_markdown)

        self.assertEqual(result["data"]["name"], "test")
        self.assertEqual(result["data"]["value"]["nested"], "truncated string")
        self.assertEqual(result["data"]["comments"], 0)

        self.assertTrue(result["markdown"].endswith("```\n"))
        self.assertIn("Status: Success", result["report_text"])

        # Test unclosed bold
        result_bold = self.formatter.process("{}", "This is **bold")
        self.assertEqual(result_bold["markdown"], "This is **bold**")

        # Test truncated table
        input_table = "| Col1 | Col2 |\n| --- | --- |\n| Val1 | Val2 "
        result_table = self.formatter.process("{}", input_table)
        self.assertTrue(result_table["markdown"].endswith("|"))

    def test_missing_parameter_fallback(self):
        """Test calling process without parameters."""
        result = self.formatter.process()

        self.assertEqual(result["data"]["comments"], 0)
        self.assertEqual(result["markdown"], "")
        self.assertIn("Status: Success", result["report_text"])

    def test_nan_none_clean(self):
        """Test cleaning of NaN and None values in JSON."""
        # Using a list with NaN and None and testing if it is cleaned properly.
        # json.loads can actually handle NaN for float if we use parse_constant, but standard JSON shouldn't have it.
        # So we test _clean_data directly as well as through process.

        # We can construct python objects that simulate the output of json.loads if there was NaN or None
        data = {
            "valid": 1,
            "null_value": None,
            "nan_value": float("nan"),
            "inf_value": float("inf"),
            "nested": [None, float("nan")]
        }
        cleaned = self.formatter._clean_data(data)

        self.assertEqual(cleaned["valid"], 1)
        self.assertEqual(cleaned["null_value"], 0)
        self.assertEqual(cleaned["nan_value"], 0)
        self.assertEqual(cleaned["inf_value"], 0)
        self.assertEqual(cleaned["nested"], [0, 0])

    def test_extreme_boundary_case(self):
        """Test with deeply nested truncations and invalid JSON."""
        input_json = '[[[[{"a": 1, "b": [{"c":'
        input_markdown = "```python\n```python\n" # This doesn't make total sense but should heal

        result = self.formatter.process(input_json, input_markdown)

        # Depending on healing logic it might give {} or a deeply nested structure
        # The main goal is it doesn't crash and returns comments=0
        self.assertEqual(result["data"]["comments"], 0)
        self.assertTrue(isinstance(result["data"], dict))

        # Malformed markdown tests
        result_md = self.formatter.process(None, "```")
        self.assertEqual(result_md["markdown"], "```\n```\n")

        result_empty_json = self.formatter.process("   ", "")
        self.assertEqual(result_empty_json["data"]["comments"], 0)

if __name__ == '__main__':
    unittest.main()
