import unittest
from ultra_modules.approval_one_tap_callback_audit_trace import (
    AuditLogger,
    generate_diff,
    _clean_dirty_data,
    process_approval_callback
)

class TestApprovalOneTapCallbackAuditTrace(unittest.TestCase):

    def test_normal_approval_flow(self):
        """Test normal approval flow without missing parameters."""
        old_state = {"status": "pending", "count": 1}
        new_state = {"status": "approved", "count": 1}

        result = process_approval_callback(
            action="approve",
            target_id="req-123",
            context={"user_id": "u-456"},
            old_state=old_state,
            new_state=new_state,
            reason="All good"
        )

        self.assertEqual(result["action_taken"], "approve")
        self.assertEqual(result["target_id"], "req-123")
        self.assertEqual(result["reason"], "All good")
        self.assertIn("status", result["diff_highlight"])
        self.assertEqual(result["diff_highlight"]["status"]["old"], "pending")
        self.assertEqual(result["diff_highlight"]["status"]["new"], "approved")
        self.assertNotIn("count", result["diff_highlight"])

    def test_missing_parameters_fallback(self):
        """Test missing parameters using sensible defaults."""
        result = process_approval_callback(
            action="approve",
            target_id="req-456"
        )

        self.assertEqual(result["action_taken"], "approve")
        self.assertEqual(result["target_id"], "req-456")
        self.assertEqual(result["reason"], "No reason provided")
        self.assertEqual(result["diff_highlight"], {})

    def test_dirty_data_self_healing(self):
        """Test dirty data being self-healed."""
        result = process_approval_callback(
            action="  APPROVE  ",
            target_id=" req-789 \n",
            context={"user_id": " u-999 \t", "roles": [" admin ", " user "]},
            reason=" \n Needs trimming "
        )

        self.assertEqual(result["action_taken"], "approve")
        self.assertEqual(result["target_id"], "req-789")
        self.assertEqual(result["reason"], "Needs trimming")
        self.assertEqual(result["frontend_display"], "Successfully approved target req-789.")

    def test_boundary_condition_handling(self):
        """Test extreme boundary condition handling like unknown actions."""
        # Unrecognized action should fallback to 'reject'
        result = process_approval_callback(
            action="unknown_action",
            target_id="req-invalid"
        )
        self.assertEqual(result["action_taken"], "reject")
        self.assertEqual(result["target_id"], "req-invalid")
        self.assertEqual(result["frontend_display"], "Successfully rejected target req-invalid.")

    def test_reject_flow_and_diff(self):
        """Test rejecting flow and diff highlighting."""
        old_state = {"price": 100, "description": "Original"}
        new_state = {"price": 200, "description": "Original"}

        result = process_approval_callback(
            action="reject",
            target_id="req-diff",
            old_state=old_state,
            new_state=new_state,
            reason="Price too high"
        )

        self.assertEqual(result["action_taken"], "reject")
        self.assertEqual(result["target_id"], "req-diff")
        self.assertEqual(result["reason"], "Price too high")
        self.assertIn("price", result["diff_highlight"])
        self.assertEqual(result["diff_highlight"]["price"]["old"], 100)
        self.assertEqual(result["diff_highlight"]["price"]["new"], 200)
        self.assertNotIn("description", result["diff_highlight"])

    def test_audit_logger_and_cleaner(self):
        """Additional test for 100% coverage on helper functions and classes."""
        logger = AuditLogger()
        logger.log("TEST", {"key": "val"})
        logs = logger.get_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["action"], "TEST")
        self.assertEqual(logs[0]["details"], {"key": "val"})

        # Cover different types in dirty data cleaner
        dirty = _clean_dirty_data(123)
        self.assertEqual(dirty, 123)

        dirty_dict = _clean_dirty_data({"key": " val "})
        self.assertEqual(dirty_dict, {"key": "val"})

        dirty_list = _clean_dirty_data([" v1 ", " v2 "])
        self.assertEqual(dirty_list, ["v1", "v2"])

if __name__ == "__main__":
    unittest.main()
