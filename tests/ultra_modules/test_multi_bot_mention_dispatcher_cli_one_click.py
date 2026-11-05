import unittest
from ultra_modules.multi_bot_mention_dispatcher_cli_one_click import cli_main, MultiBotMentionDispatcherCliOneClick

class TestMultiBotMentionDispatcherCliOneClick(unittest.TestCase):
    def test_normal_execution(self):
        """Test normal execution with string containing bot mentions"""
        records = ["Hello @大肥鱼, please help.", "Need some data @数据"]
        result = cli_main(records=records, output_format="json")

        self.assertEqual(result["summary"]["total_records"], 2)
        self.assertEqual(result["summary"]["processed_successfully"], 2)
        self.assertEqual(result["summary"]["ignored_empty"], 0)

        mentions = result["summary"]["mention_statistics"]
        self.assertEqual(mentions.get("@大肥鱼"), 1)
        self.assertEqual(mentions.get("@数据"), 1)
        self.assertNotIn("@招聘", mentions)

        self.assertEqual(len(result["details"]), 2)
        self.assertEqual(result["details"][0]["mentions"], ["@大肥鱼"])
        self.assertEqual(result["details"][1]["mentions"], ["@数据"])

    def test_missing_parameters(self):
        """Test zero-configuration fallback: calling cli_main with no parameters"""
        result = cli_main()

        self.assertEqual(result["summary"]["total_records"], 0)
        self.assertEqual(result["summary"]["processed_successfully"], 0)
        self.assertEqual(result["summary"]["ignored_empty"], 0)
        self.assertEqual(result["summary"]["mention_statistics"], {})
        self.assertEqual(result["details"], [])

    def test_dirty_data_self_healing(self):
        """Test robust parsing and fault tolerance with None, dict, and numbers"""
        records = [
            None,
            {"text": "Is this @量化 working?"},
            {"content": "Look for @招聘"},
            {"other_key": "Random @数据 dict"}, # fallback to str(dict)
            12345
        ]

        result = cli_main(records=records)

        self.assertEqual(result["summary"]["total_records"], 5)
        self.assertEqual(result["summary"]["processed_successfully"], 4)
        self.assertEqual(result["summary"]["ignored_empty"], 1) # None should be ignored_empty

        details = result["details"]

        self.assertEqual(details[0]["status"], "ignored_empty")
        self.assertEqual(details[0]["cleaned_text"], "")

        self.assertEqual(details[1]["status"], "success")
        self.assertEqual(details[1]["cleaned_text"], "Is this @量化 working?")
        self.assertEqual(details[1]["mentions"], ["@量化"])

        self.assertEqual(details[2]["status"], "success")
        self.assertEqual(details[2]["cleaned_text"], "Look for @招聘")
        self.assertEqual(details[2]["mentions"], ["@招聘"])

        self.assertEqual(details[3]["status"], "success")
        self.assertTrue("Random @数据 dict" in details[3]["cleaned_text"])
        self.assertEqual(details[3]["mentions"], ["@数据"])

        self.assertEqual(details[4]["status"], "success")
        self.assertEqual(details[4]["cleaned_text"], "12345")
        self.assertEqual(details[4]["mentions"], [])

    def test_json_and_excel_output_mode(self):
        """Verify multiple output formats"""
        record = "Hello @大肥鱼"

        # Default is JSON
        res_default = cli_main(record)
        self.assertIn("details", res_default)

        # Explicit JSON
        res_json = cli_main(record, output_format="json")
        self.assertIn("details", res_json)

        # Explicit Excel
        res_excel = cli_main(record, output_format="excel")
        self.assertNotIn("details", res_excel)
        self.assertIn("excel_csv_simulation", res_excel)
        self.assertIn("@大肥鱼", res_excel["excel_csv_simulation"])
        self.assertIn("Hello @大肥鱼", res_excel["excel_csv_simulation"])

        # Invalid format falls back to JSON
        res_invalid = cli_main(record, output_format="xml")
        self.assertIn("details", res_invalid)

    def test_extreme_boundary_cases(self):
        """Test with malformed inputs, single item instead of list, extreme strings"""
        # Single item
        res_single = cli_main("This is just a single string @数据")
        self.assertEqual(res_single["summary"]["total_records"], 1)
        self.assertEqual(res_single["details"][0]["mentions"], ["@数据"])

        # Very large list of empty strings
        large_records = [""] * 1000
        res_large = cli_main(large_records)
        self.assertEqual(res_large["summary"]["total_records"], 1000)
        self.assertEqual(res_large["summary"]["ignored_empty"], 1000)

        # Mentions across boundaries (multiple bots in one message)
        res_multi = cli_main("@大肥鱼 and @招聘 and @量化 and @数据")
        mentions = res_multi["details"][0]["mentions"]
        self.assertEqual(len(mentions), 4)
        self.assertIn("@大肥鱼", mentions)
        self.assertIn("@招聘", mentions)
        self.assertIn("@量化", mentions)
        self.assertIn("@数据", mentions)

if __name__ == '__main__':
    unittest.main()
