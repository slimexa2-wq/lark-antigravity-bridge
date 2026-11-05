import unittest
from ultra_modules.approval_one_tap_callback_integration_bridge import ApprovalOneTapCallbackIntegrationBridge

class TestApprovalOneTapCallbackIntegrationBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = ApprovalOneTapCallbackIntegrationBridge()

    def test_normal_case_old_schema(self):
        """Test old schema where fields are flat."""
        payload = {
            "action_name": "approve",
            "open_id": "ou_12345",
            "instance_code": "inst_789"
        }
        result = self.bridge.sync_status(payload)
        self.assertEqual(result["status"], "APPROVED")
        self.assertEqual(result["user_id"], "ou_12345")
        self.assertEqual(result["task_id"], "inst_789")

    def test_normal_case_new_schema(self):
        """Test new schema where fields are nested objects."""
        payload = {
            "action": {"value": "REJECT"},
            "user": {"id": "ou_67890"},
            "task": {"id": "inst_001"}
        }
        result = self.bridge.sync_status(payload)
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["user_id"], "ou_67890")
        self.assertEqual(result["task_id"], "inst_001")

    def test_missing_parameter_fallback(self):
        """Test when the payload is None or missing entirely."""
        result = self.bridge.sync_status(None)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["user_id"], "UNKNOWN_USER")
        self.assertEqual(result["task_id"], "UNKNOWN_TASK")

    def test_dirty_data_self_healing(self):
        """Test with invalid JSON string and other non-dict types."""
        # Invalid JSON string
        result_invalid_json = self.bridge.sync_status("this is not a valid json")
        self.assertEqual(result_invalid_json["status"], "UNKNOWN")
        self.assertEqual(result_invalid_json["raw_payload"], "this is not a valid json")

        # Valid JSON string but old schema
        valid_json = '{"action_name": "approve", "open_id": "123", "instance_code": "456"}'
        result_valid_json = self.bridge.sync_status(valid_json)
        self.assertEqual(result_valid_json["status"], "APPROVED")
        self.assertEqual(result_valid_json["user_id"], "123")
        self.assertEqual(result_valid_json["task_id"], "456")

        # Non-string, non-dict type (e.g., int)
        result_int = self.bridge.sync_status(12345)
        self.assertEqual(result_int["status"], "UNKNOWN")
        self.assertEqual(result_int["raw_payload"], 12345)

    def test_extreme_boundaries(self):
        """Test with unexpected field types and missing fields in nested structures."""
        # Partially nested schema with missing value/id
        payload = {
            "action": {},  # missing value
            "user": {"name": "test"}, # missing id
            "task": [] # wrong type
        }
        result = self.bridge.sync_status(payload)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["user_id"], "UNKNOWN_USER")
        self.assertEqual(result["task_id"], "UNKNOWN_TASK")

        # Mixed old/new schema with unconventional casing
        mixed_payload = {
            "action_name": "ReJeCtEd",
            "user": {"id": 999}, # int instead of str
            "task_id": None
        }
        result_mixed = self.bridge.sync_status(mixed_payload)
        self.assertEqual(result_mixed["status"], "REJECTED")
        self.assertEqual(result_mixed["user_id"], "999")
        self.assertEqual(result_mixed["task_id"], "None")

if __name__ == '__main__':
    unittest.main()
