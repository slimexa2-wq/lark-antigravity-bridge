import unittest
import json
from unittest.mock import patch
from io import StringIO

from ultra_modules.attachment_auto_router_cli_one_click import AttachmentAutoRouter, main

class TestAttachmentAutoRouter(unittest.TestCase):
    def test_normal_execution_weekly(self):
        router = AttachmentAutoRouter(mode="json")
        result_json = router.process_and_output("张三_周报_2023.xlsx")
        result = json.loads(result_json)

        self.assertEqual(result["engine"], "Weekly Report Engine")
        self.assertEqual(result["category"], "周报")
        self.assertEqual(result["healed_filename"], "张三_周报_2023.xlsx")

    def test_dirty_data_healing_commission(self):
        router = AttachmentAutoRouter(mode="excel")
        # Dirty data: spaces, weird path
        dirty_filename = "   /some/weird/path/  项目A_提成明细_FINAL.xlsx   "
        result_csv = router.process_and_output(dirty_filename)

        self.assertIn("项目a_提成明细_final.xlsx", result_csv)
        self.assertIn("Commission Engine", result_csv)
        self.assertIn("提成", result_csv)

    def test_missing_parameters_fallback(self):
        # Empty filename or None
        router = AttachmentAutoRouter(mode="json")
        result_json = router.process_and_output("")
        result = json.loads(result_json)

        self.assertEqual(result["healed_filename"], "unknown_file.txt")
        self.assertEqual(result["engine"], "Fallback Engine")
        self.assertEqual(result["category"], "未知/默认")

        result_none_json = router.process_and_output(None)
        result_none = json.loads(result_none_json)
        self.assertEqual(result_none["healed_filename"], "unknown_file.txt")

    def test_extreme_boundary_conditions(self):
        router = AttachmentAutoRouter(mode="invalid_mode")
        # Should fallback to json mode if invalid mode is passed
        self.assertEqual(router.mode, "json")

        # Super long filename with special chars
        long_filename = "x" * 1000 + "_标书_!@#$%^&*().docx"
        result_json = router.process_and_output(long_filename)
        result = json.loads(result_json)

        self.assertEqual(result["engine"], "Bid Document Engine")
        self.assertEqual(result["category"], "标书")

    @patch("sys.stdout", new_callable=StringIO)
    @patch("sys.argv", ["attachment_auto_router_cli_one_click.py"])
    def test_zero_configuration_cli_execution(self, mock_stdout):
        # Running main without any arguments (zero configuration)
        main()
        output = mock_stdout.getvalue()

        # Since default file is '周报_2023.xlsx' and default mode is 'json'
        result = json.loads(output.strip())
        self.assertEqual(result["engine"], "Weekly Report Engine")
        self.assertEqual(result["category"], "周报")
        self.assertEqual(result["healed_filename"], "周报_2023.xlsx")

if __name__ == '__main__':
    unittest.main()
