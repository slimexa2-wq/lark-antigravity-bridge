import unittest
from typing import Dict, Any
from ultra_modules.voice_message_intent_parser_integration_bridge import VoiceMessageIntentParserBridge

class TestVoiceMessageIntentParserIntegrationBridge(unittest.TestCase):
    def setUp(self):
        self.parser = VoiceMessageIntentParserBridge()

    def test_normal_execution_intent_extraction(self):
        """Test normal execution for expected keywords."""
        result = self.parser.parse_intent("把这月提成表核一下")
        self.assertEqual(result.get("intent_code"), "finance_commission_query")
        self.assertEqual(result.get("action"), "finance_commission_query")

        entities = result.get("extracted_entities", {})
        self.assertEqual(entities.get("target_module"), "finance")
        self.assertEqual(entities.get("subject"), "commission")
        self.assertEqual(entities.get("period"), "current_month")

        self.assertGreater(result.get("parse_confidence", 0), 0.8)

    def test_dirty_data_self_healing(self):
        """Test with dirty data like dictionaries, bytes, None, numbers."""
        # Dictionary with 'text' field
        res1 = self.parser.parse_intent({"text": "我要请假"})
        self.assertEqual(res1.get("intent_code"), "hr_leave_request")

        # Bytes input
        res2 = self.parser.parse_intent(b'\xe6\x88\x91\xe8\xa6\x81\xe8\xaf\xb7\xe5\x81\x87') # "我要请假"
        self.assertEqual(res2.get("intent_code"), "hr_leave_request")

        # None input
        res3 = self.parser.parse_intent(None)
        self.assertEqual(res3.get("intent_code"), "unknown_intent")
        self.assertEqual(res3.get("parse_confidence"), 0.0)

        # Number input
        res4 = self.parser.parse_intent(12345)
        self.assertEqual(res4.get("intent_code"), "unknown_intent")
        self.assertEqual(res4.get("raw_text"), "12345")

    def test_default_fallbacks_missing_params(self):
        """Test default fallbacks for missing parameters with old schema mapping."""
        old_schema_template: Dict[str, Any] = {
            "action": "default_action",
            "score": 0.0,
            "target": {},
            "text": "",
            "version": "v1.0",
            "unknown_field": "default_unknown"
        }

        result = self.parser.parse_intent("安排下个月开会", target_schema_template=old_schema_template, schema_version="v2.0")

        # Exact/heuristic mapped fields
        self.assertEqual(result.get("action"), "calendar_meeting_schedule")
        self.assertGreater(result.get("score", 0.0), 0.8)
        self.assertEqual(result.get("text"), "安排下个月开会")
        self.assertEqual(result.get("version"), "v2.0")

        # Nested field mapping check
        target = result.get("target", {})
        self.assertEqual(target.get("target_module"), "calendar")
        self.assertEqual(target.get("period"), "next_month")

        # Missing param fallback
        self.assertEqual(result.get("unknown_field"), "default_unknown")

    def test_extreme_boundary_conditions(self):
        """Test extreme boundary conditions like very long strings, empty strings, and deep nested invalid objects."""
        # Very long string
        long_str = "a" * 10000 + "请假"
        res_long = self.parser.parse_intent(long_str)
        self.assertEqual(res_long.get("intent_code"), "hr_leave_request")

        # Empty string
        res_empty = self.parser.parse_intent("   \n \t  ")
        self.assertEqual(res_empty.get("intent_code"), "unknown_intent")
        self.assertEqual(res_empty.get("parse_confidence"), 0.0)

        # Deep nested invalid object fallback to json string parsing
        complex_obj = {"level1": {"level2": {"msg": "not here", "other": b"invalid"}}}
        # Since 'msg' is deep, it won't be caught by shallow dict check,
        # it will fallback to str(raw_input) and won't match intent keywords.
        res_complex = self.parser.parse_intent(complex_obj)
        self.assertEqual(res_complex.get("intent_code"), "unknown_intent")

    def test_schema_forward_compatibility(self):
        """Test that mapping correctly forwards old versions without config."""
        new_schema_template = {
            "intent_code": "unknown",
            "parse_confidence": 0.0,
            "extracted_entities": {},
            "raw_text": "",
            "schema_version": "v3.0"
        }

        result = self.parser.parse_intent("下个月算一下工资", target_schema_template=new_schema_template)

        self.assertEqual(result.get("intent_code"), "finance_commission_query")
        self.assertEqual(result.get("schema_version"), "v_latest")
        self.assertEqual(result.get("extracted_entities").get("target_module"), "finance")
        self.assertEqual(result.get("extracted_entities").get("period"), "next_month")

if __name__ == '__main__':
    unittest.main()
