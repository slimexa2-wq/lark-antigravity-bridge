import unittest
import json
from ultra_modules.mobile_table_digest_formatter_cli_one_click import MobileTableDigestFormatterCliOneClick

class TestMobileTableDigestFormatterCliOneClick(unittest.TestCase):
    def setUp(self):
        self.formatter = MobileTableDigestFormatterCliOneClick()

    def test_normal_standard_json(self):
        input_data = {
            "summary": "Sales data Q3",
            "anomalies": ["Missing revenue for Sept", "Duplicate entry ID 104"],
            "file_url": "https://example.com/sales_q3.xlsx",
            "file_name": "sales_q3.xlsx",
            "total_rows": 1000,
            "processed_rows": 998
        }
        json_str = json.dumps(input_data)
        result = self.formatter.run_cli(json_str)
        result_dict = json.loads(result)

        # Check header
        self.assertEqual(result_dict["header"]["template"], "red")

        # Check digest content
        markdown_content = result_dict["elements"][0]["content"]
        self.assertIn("**Summary:** Sales data Q3", markdown_content)
        self.assertIn("**Stats:** Processed 998/1000 rows.", markdown_content)
        self.assertIn("**<font color='red'>Anomalies Detected:</font>**", markdown_content)
        self.assertIn("Missing revenue for Sept", markdown_content)

        # Check button
        button = result_dict["elements"][1]["actions"][0]
        self.assertEqual(button["url"], "https://example.com/sales_q3.xlsx")
        self.assertEqual(button["text"]["content"], "Download sales_q3.xlsx")

    def test_default_zero_parameter(self):
        result = self.formatter.run_cli()
        result_dict = json.loads(result)

        # Default should have no anomalies, blue template
        self.assertEqual(result_dict["header"]["template"], "blue")

        markdown_content = result_dict["elements"][0]["content"]
        self.assertIn("**Summary:** Demo table summary: everything is OK.", markdown_content)
        self.assertIn("**Stats:** Processed 100/100 rows.", markdown_content)
        self.assertIn("**Anomalies:** None detected.", markdown_content)

        button = result_dict["elements"][1]["actions"][0]
        self.assertEqual(button["url"], "https://example.com/demo.xlsx")

    def test_dirty_data_self_healing(self):
        # Invalid JSON string
        result = self.formatter.run_cli("this is {not} valid json")
        result_dict = json.loads(result)

        # Should fall back to default
        self.assertEqual(result_dict["header"]["template"], "blue")
        markdown_content = result_dict["elements"][0]["content"]
        self.assertIn("**Summary:** Demo table summary: everything is OK.", markdown_content)

        # Valid JSON, but not a dict (e.g., a list)
        result2 = self.formatter.run_cli("[\"not\", \"a\", \"dict\"]")
        result_dict2 = json.loads(result2)
        self.assertEqual(result_dict2["header"]["template"], "blue")
        self.assertIn("**Summary:** Demo table summary: everything is OK.", result_dict2["elements"][0]["content"])

    def test_excel_path_mock_parsing(self):
        result = self.formatter.run_cli("my_report_2023.xlsx")
        result_dict = json.loads(result)

        markdown_content = result_dict["elements"][0]["content"]
        self.assertIn("**Summary:** Data parsed from my_report_2023.xlsx", markdown_content)
        self.assertIn("**Stats:** Processed 50/50 rows.", markdown_content)
        self.assertIn("**Anomalies:** None detected.", markdown_content)

        button = result_dict["elements"][1]["actions"][0]
        self.assertEqual(button["url"], "https://example.com/my_report_2023.xlsx")
        self.assertEqual(button["text"]["content"], "Download my_report_2023.xlsx")

    def test_extreme_boundary_cases(self):
        # Empty dictionary
        result = self.formatter.run_cli("{}")
        result_dict = json.loads(result)

        # Should merge with default gracefully
        markdown_content = result_dict["elements"][0]["content"]
        self.assertIn("**Summary:** Demo table summary: everything is OK.", markdown_content)
        self.assertEqual(result_dict["header"]["template"], "blue")

        # Missing keys in dictionary
        partial_data = {
            "summary": "Partial data summary",
            # missing total_rows, processed_rows, etc.
        }
        result2 = self.formatter.run_cli(json.dumps(partial_data))
        result_dict2 = json.loads(result2)
        markdown_content2 = result_dict2["elements"][0]["content"]
        self.assertIn("**Summary:** Partial data summary", markdown_content2)
        self.assertIn("**Stats:** Processed 100/100 rows.", markdown_content2) # Filled from default
        self.assertEqual(result_dict2["header"]["template"], "blue")

        # Empty string
        result3 = self.formatter.run_cli("   ")
        result_dict3 = json.loads(result3)
        self.assertEqual(result_dict3["header"]["template"], "blue")
        self.assertIn("**Summary:** Demo table summary: everything is OK.", result_dict3["elements"][0]["content"])

if __name__ == "__main__":
    unittest.main()
