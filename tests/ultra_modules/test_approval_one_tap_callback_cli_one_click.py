import unittest
import json
import subprocess
from ultra_modules.approval_one_tap_callback_cli_one_click import process_callback_status, run_cli

class TestApprovalOneTapCallback(unittest.TestCase):

    def test_normal_json_output(self):
        result = process_callback_status("reject", {"reason": "too expensive"}, "json")
        data = json.loads(result)
        self.assertEqual(data["final_action"], "reject")
        self.assertEqual(data["processed_payload"]["reason"], "too expensive")

    def test_normal_excel_output(self):
        result = process_callback_status("approve", {"id": 123}, "excel")
        self.assertTrue("sync_status,final_action,payload_summary" in result)
        self.assertTrue("success,approve," in result)

    def test_missing_parameters(self):
        result = process_callback_status()
        data = json.loads(result)
        self.assertEqual(data["final_action"], "approve")
        self.assertEqual(data["processed_payload"]["status"], "unknown")

    def test_dirty_data_self_healing(self):
        # weird action, non-string keys, weird output mode
        result = process_callback_status(
            action="   WeirdAction \n",
            payload={123: "number key", "": "empty key"},
            output_mode=" XML "
        )
        data = json.loads(result)
        self.assertEqual(data["final_action"], "approve") # fallback
        self.assertEqual(data["processed_payload"]["123"], "number key")
        self.assertEqual(data["processed_payload"]["unknown_key"], "empty key")

    def test_extreme_boundaries(self):
        # None for action, string for payload, None for output_mode
        result = process_callback_status(action=None, payload="not a dict", output_mode=None)
        data = json.loads(result)
        self.assertEqual(data["final_action"], "approve")
        self.assertEqual(data["processed_payload"]["status"], "unknown")

        # Test CLI entry directly
        self.assertTrue(run_cli())

    def test_additional_coverage(self):
        # Trigger line 14: action not a string but not None
        result = process_callback_status(action=123)
        self.assertTrue("approve" in result)

        # Trigger line 34: output_mode not a string but not None
        result2 = process_callback_status(output_mode=123)
        self.assertTrue("approve" in result2)

        # Output mode 'csv'
        result3 = process_callback_status(output_mode="csv")
        self.assertTrue("sync_status,final_action" in result3)

    def test_main_block(self):
        # Test the __name__ == "__main__" block
        result = subprocess.run(["python3", "ultra_modules/approval_one_tap_callback_cli_one_click.py"], capture_output=True, text=True)
        self.assertTrue("approve" in result.stdout)

if __name__ == "__main__":
    unittest.main()
