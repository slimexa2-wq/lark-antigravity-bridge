import unittest
import time
from unittest.mock import patch, MagicMock

# Assuming ultra_modules is in the PYTHONPATH or can be imported directly
from ultra_modules.ws_exponential_backoff_integration_bridge import (
    WsReconnectionStateMachine,
    SchemaForwardCompatibilityConverter,
)

class TestWsExponentialBackoffIntegrationBridge(unittest.TestCase):

    def test_normal_operation_state_machine(self):
        """Test the state machine calculates delay correctly under normal conditions."""
        sm = WsReconnectionStateMachine(base_delay=1.0, max_delay=10.0, jitter_factor=0.0)

        sm.disconnect()
        self.assertFalse(sm.is_connected)

        # Retry 0: base 1.0 * 2^0 = 1.0 (no jitter)
        delay_0 = sm.get_next_delay()
        self.assertEqual(delay_0, 1.0)
        self.assertEqual(sm.retry_count, 1)

        # Retry 1: base 1.0 * 2^1 = 2.0
        delay_1 = sm.get_next_delay()
        self.assertEqual(delay_1, 2.0)
        self.assertEqual(sm.retry_count, 2)

        # Test reset
        sm.reset()
        self.assertTrue(sm.is_connected)
        self.assertEqual(sm.retry_count, 0)

        # Test when connected
        self.assertEqual(sm.get_next_delay(), 0.0)

    @patch('ultra_modules.ws_exponential_backoff_integration_bridge.random.uniform')
    def test_extreme_boundary_and_jitter(self, mock_uniform):
        """Test extreme boundary cases, capping delay, and mocking jitter for predictable results."""
        # Setup mock to return a fixed jitter (e.g. max positive jitter)
        mock_uniform.side_effect = lambda a, b: b

        sm = WsReconnectionStateMachine(base_delay=2.0, max_delay=10.0, jitter_factor=0.5, max_retries=3)
        sm.disconnect()

        # Retry 0: base 2.0 * 2^0 = 2.0. Capped at 10.0 -> 2.0. Jitter = 2.0 * 0.5 = 1.0.
        # mock_uniform returns 1.0, total = 2.0 + 1.0 = 3.0
        delay_0 = sm.get_next_delay()
        self.assertEqual(delay_0, 3.0)

        # Retry 1: base 2.0 * 2^1 = 4.0. Jitter = 2.0 -> 4.0 + 2.0 = 6.0
        delay_1 = sm.get_next_delay()
        self.assertEqual(delay_1, 6.0)

        # Retry 2: base 2.0 * 2^2 = 8.0. Jitter = 4.0 -> 8.0 + 4.0 = 12.0
        delay_2 = sm.get_next_delay()
        self.assertEqual(delay_2, 12.0)

        # Retry 3: Max retries reached (retry_count=3, max_retries=3)
        delay_3 = sm.get_next_delay()
        self.assertEqual(delay_3, -1.0)

        # Test missing parameter defaults in constructor
        sm_default = WsReconnectionStateMachine(base_delay=None, max_delay=None, jitter_factor=None, max_retries=None)
        self.assertEqual(sm_default.base_delay, 1.0)
        self.assertEqual(sm_default.max_delay, 60.0)
        self.assertEqual(sm_default.jitter_factor, 0.5)
        self.assertEqual(sm_default.max_retries, -1)

    def test_schema_converter_normal_and_missing(self):
        """Test schema converter on normal data and data with missing/dirty parameters."""
        payload_v1 = {
            "id": "evt_123",
            "ts": "1700000000.5",
            "data": {
                "field_a": "value_a",
                "field_b": None # Missing parameter fallback test
            }
        }

        converted = SchemaForwardCompatibilityConverter.convert_payload(payload_v1)

        self.assertEqual(converted["event_id"], "evt_123")
        self.assertEqual(converted["timestamp"], 1700000000)
        self.assertEqual(converted["data"]["field_a"], "value_a")
        # None should be converted to ""
        self.assertEqual(converted["data"]["field_b"], "")

    @patch('ultra_modules.ws_exponential_backoff_integration_bridge.time.time')
    def test_schema_converter_dirty_data_self_healing(self, mock_time):
        """Test converter with extremely dirty data, ensuring 0 crash."""
        mock_time.return_value = 1600000000.0

        # Test completely invalid payload type (list)
        payload_invalid = ["dirty", "data"]
        res = SchemaForwardCompatibilityConverter.convert_payload(payload_invalid)
        self.assertEqual(res["event_id"], "auto_generated_event")
        self.assertEqual(res["timestamp"], 1600000000)
        self.assertEqual(res["data"], ["dirty", "data"])

        # Test completely empty dict
        res_empty = SchemaForwardCompatibilityConverter.convert_payload({})
        self.assertEqual(res_empty["event_id"], "default_event_id")
        self.assertEqual(res_empty["timestamp"], 1600000000)
        self.assertEqual(res_empty["data"], {})

        # Test flat dict needing extraction
        payload_flat = {
            "uuid": "uuid_789",
            "time": "invalid_time_string",
            "custom_key": "custom_val",
            "nested_null": {"a": None}
        }
        res_flat = SchemaForwardCompatibilityConverter.convert_payload(payload_flat)
        self.assertEqual(res_flat["event_id"], "uuid_789")
        self.assertEqual(res_flat["timestamp"], 1600000000)
        self.assertEqual(res_flat["data"]["custom_key"], "custom_val")
        self.assertEqual(res_flat["data"]["nested_null"]["a"], "")

    def test_schema_converter_boundary_cases(self):
        """Test schema converter boundary cases like null values, integer IDs, and deeply nested structures."""
        # Integer ID fallback
        res_int_id = SchemaForwardCompatibilityConverter.convert_payload({"id": 12345})
        self.assertEqual(res_int_id["event_id"], "12345")

        # Non-dict data field
        res_str_data = SchemaForwardCompatibilityConverter.convert_payload({"data": "string_data"})
        self.assertEqual(res_str_data["data"]["raw_value"], "string_data")

        # None payload
        res_none = SchemaForwardCompatibilityConverter.convert_payload(None)
        self.assertEqual(res_none["data"], {})

        # Very nested dict
        payload_nested = {
            "data": {
                "l1": {
                    "l2": {
                        "l3": None
                    }
                }
            }
        }
        res_nested = SchemaForwardCompatibilityConverter.convert_payload(payload_nested)
        self.assertEqual(res_nested["data"]["l1"]["l2"]["l3"], "")

if __name__ == '__main__':
    unittest.main()
