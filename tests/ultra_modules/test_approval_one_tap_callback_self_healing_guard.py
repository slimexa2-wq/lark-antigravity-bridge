import unittest
import time
import json
from ultra_modules.approval_one_tap_callback_self_healing_guard import ApprovalGuard

class TestApprovalGuard(unittest.TestCase):
    def setUp(self):
        self.guard = ApprovalGuard()

    def test_normal_approve_and_reject(self):
        # Normal approve
        payload = {"card_id": "card_1", "user_id": "user_1", "action": "approve"}
        res = self.guard.process_callback(payload)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["current_state"], "approved")
        self.assertEqual(self.guard.get_card_state("card_1"), "approved")

        # Normal reject on a different card
        payload_reject = {"card_id": "card_2", "user_id": "user_2", "action": "reject"}
        res_reject = self.guard.process_callback(payload_reject)
        self.assertEqual(res_reject["status"], "success")
        self.assertEqual(res_reject["current_state"], "rejected")
        self.assertEqual(self.guard.get_card_state("card_2"), "rejected")

    def test_dirty_data_self_healing(self):
        # String payload that is a valid JSON
        payload_str = json.dumps({"card_id": "card_3", "user_id": "user_3", "action": " APPROVE "})
        res = self.guard.process_callback(payload_str)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["current_state"], "approved")
        self.assertEqual(res["action_applied"], "approve")

        # String payload that is invalid JSON
        payload_invalid_str = "not a valid json {}"
        res_invalid = self.guard.process_callback(payload_invalid_str)
        self.assertEqual(res_invalid["status"], "success")
        self.assertEqual(res_invalid["card_id"], "default_card_id")
        self.assertEqual(res_invalid["user_id"], "unknown_user")
        self.assertEqual(res_invalid["action_applied"], "approve") # default fallback

        # Invalid type entirely (e.g. integer)
        res_int = self.guard.process_callback(12345)
        self.assertEqual(res_int["status"], "success")
        self.assertEqual(res_int["card_id"], "default_card_id")

    def test_missing_parameter_fallback(self):
        # Empty dict
        res = self.guard.process_callback({})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["card_id"], "default_card_id")
        self.assertEqual(res["user_id"], "unknown_user")
        self.assertEqual(res["action_applied"], "approve")
        self.assertEqual(res["current_state"], "approved")

        # Partial missing
        res_partial = self.guard.process_callback({"card_id": "card_4"})
        self.assertEqual(res_partial["status"], "success")
        self.assertEqual(res_partial["card_id"], "card_4")
        self.assertEqual(res_partial["user_id"], "unknown_user")
        self.assertEqual(res_partial["action_applied"], "approve")

    def test_undo_mechanism_success(self):
        # Change state to approve
        payload = {"card_id": "card_undo_1", "action": "reject"}
        self.guard.process_callback(payload)
        self.assertEqual(self.guard.get_card_state("card_undo_1"), "rejected")

        # Immediately undo
        undo_res = self.guard.undo_action({"card_id": "card_undo_1"})
        self.assertEqual(undo_res["status"], "success")
        self.assertEqual(undo_res["current_state"], "pending")
        self.assertEqual(self.guard.get_card_state("card_undo_1"), "pending")

        # Another sequence: pending -> approved -> rejected -> undo (should be approved)
        self.guard.process_callback({"card_id": "card_undo_2", "action": "approve"})
        self.assertEqual(self.guard.get_card_state("card_undo_2"), "approved")

        self.guard.process_callback({"card_id": "card_undo_2", "action": "reject"})
        self.assertEqual(self.guard.get_card_state("card_undo_2"), "rejected")

        undo_res_2 = self.guard.undo_action({"card_id": "card_undo_2"})
        self.assertEqual(undo_res_2["status"], "success")
        self.assertEqual(undo_res_2["current_state"], "approved")

    def test_undo_mechanism_expiration_and_edge_cases(self):
        # Override the undo window for fast testing
        self.guard.undo_window_seconds = 0.1

        self.guard.process_callback({"card_id": "card_exp_1", "action": "approve"})

        # Wait for expiration
        time.sleep(0.2)

        undo_res = self.guard.undo_action({"card_id": "card_exp_1"})
        self.assertEqual(undo_res["status"], "error")
        self.assertEqual(undo_res["message"], "Undo window expired.")
        self.assertEqual(undo_res["current_state"], "approved")

        # Try undo on non-existent card
        undo_nonexistent = self.guard.undo_action({"card_id": "no_such_card"})
        self.assertEqual(undo_nonexistent["status"], "error")
        self.assertEqual(undo_nonexistent["message"], "No snapshot available for undo.")

        # Dirty data in undo payload - it should fall back to default card ID
        # Wait, undo on fast window is 0.1s, let's wait 0.2s so it fails with "error".
        self.guard.process_callback({"card_id": "default_card_id"})
        time.sleep(0.2)
        undo_dirty = self.guard.undo_action("invalid json")
        self.assertEqual(undo_dirty["status"], "error")
        self.assertEqual(undo_dirty["message"], "Undo window expired.")

    def test_undo_mechanism_dirty_data(self):
        self.guard.undo_window_seconds = 5.0
        self.guard.process_callback({"card_id": "default_card_id"})

        # Invalid string payload should fallback to empty dict, which defaults card_id to 'default_card_id'
        undo_dirty = self.guard.undo_action("invalid json")
        self.assertEqual(undo_dirty["status"], "success")
        self.assertEqual(undo_dirty["current_state"], "pending")

if __name__ == '__main__':
    unittest.main()
