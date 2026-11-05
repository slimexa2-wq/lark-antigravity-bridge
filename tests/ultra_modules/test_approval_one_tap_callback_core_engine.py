import unittest
from ultra_modules.approval_one_tap_callback_core_engine import process_approval_callback

class TestApprovalOneTapCallbackCoreEngine(unittest.TestCase):
    def test_normal_approval(self):
        """Test normal 'approve' action payload."""
        payload = {
            "action": {
                "value": {
                    "action_type": "approve",
                    "approval_id": "app_12345"
                }
            }
        }
        result = process_approval_callback(payload)
        self.assertEqual(result, {
            "toast": {
                "type": "success",
                "content": "Successfully approved app_12345"
            }
        })

    def test_normal_rejection(self):
        """Test normal 'reject' action payload."""
        payload = {
            "action": {
                "value": {
                    "action_type": "reject",
                    "approval_id": "app_67890"
                }
            }
        }
        result = process_approval_callback(payload)
        self.assertEqual(result, {
            "toast": {
                "type": "success",
                "content": "Successfully rejected app_67890"
            }
        })

    def test_extreme_boundary_none(self):
        """Test extreme boundary where payload is None."""
        result = process_approval_callback(None)
        self.assertEqual(result, {
            "toast": {
                "type": "error",
                "content": "Invalid or missing action type"
            }
        })

    def test_missing_parameters_fallback(self):
        """Test missing parameter fallbacks (empty dict payload)."""
        result = process_approval_callback({})
        self.assertEqual(result, {
            "toast": {
                "type": "error",
                "content": "Invalid or missing action type"
            }
        })

    def test_stringified_json_dirty_data(self):
        """Test dirty data self-healing: stringified JSON."""
        payload_str = '{"action": {"value": {"action_type": "approve", "approval_id": "app_str"}}}'
        result = process_approval_callback(payload_str)
        self.assertEqual(result, {
            "toast": {
                "type": "success",
                "content": "Successfully approved app_str"
            }
        })

    def test_invalid_json_dirty_data(self):
        """Test dirty data self-healing: invalid JSON string."""
        payload_str = '{"action": {"value": {"action_type": "approve"'  # Malformed JSON
        result = process_approval_callback(payload_str)
        self.assertEqual(result, {
            "toast": {
                "type": "error",
                "content": "Invalid or missing action type"
            }
        })

    def test_dirty_data_wrong_types(self):
        """Test dirty data: incorrect data types for keys."""
        payload = {
            "action": "this is a string instead of dict"
        }
        result = process_approval_callback(payload)
        self.assertEqual(result, {
            "toast": {
                "type": "error",
                "content": "Invalid or missing action type"
            }
        })

        payload_value = {
            "action": {
                "value": ["list", "instead", "of", "dict"]
            }
        }
        result = process_approval_callback(payload_value)
        self.assertEqual(result, {
            "toast": {
                "type": "error",
                "content": "Invalid or missing action type"
            }
        })

    def test_dirty_data_not_a_dict(self):
        """Test dirty data: payload is an integer instead of dict or json string."""
        result = process_approval_callback(12345)
        self.assertEqual(result, {
            "toast": {
                "type": "error",
                "content": "Invalid or missing action type"
            }
        })

if __name__ == '__main__':
    unittest.main()
