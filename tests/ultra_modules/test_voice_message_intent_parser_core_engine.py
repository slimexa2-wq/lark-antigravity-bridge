import unittest
from ultra_modules.voice_message_intent_parser_core_engine import parse_voice_intent

class TestVoiceMessageIntentParser(unittest.TestCase):

    def test_normal_case(self):
        """Test a normal, clean voice message text."""
        result = parse_voice_intent("把这月提成表核一下")
        self.assertEqual(result["intent"], "VERIFY_DOCUMENT")
        self.assertEqual(result["entities"].get("document_type"), "提成表")
        self.assertEqual(result["entities"].get("time"), "这月")
        self.assertGreater(result["confidence"], 0.5)

    def test_dirty_data(self):
        """Test text with filler words and punctuations."""
        result = parse_voice_intent("呃，那个，就是把这月提成表核一下吧。")
        self.assertEqual(result["intent"], "VERIFY_DOCUMENT")
        self.assertEqual(result["entities"].get("document_type"), "提成表")
        self.assertEqual(result["entities"].get("time"), "这月")
        self.assertGreater(result["confidence"], 0.5)

    def test_default_parameter_fallback(self):
        """Test that missing parameter returns default intent."""
        # Test default parameter usage and empty string behavior
        result = parse_voice_intent("", default_intent="CUSTOM_DEFAULT")
        self.assertEqual(result["intent"], "CUSTOM_DEFAULT")
        self.assertEqual(result["entities"], {})
        self.assertEqual(result["confidence"], 0.0)

    def test_edge_cases_and_types(self):
        """Test edge cases: None, non-string, string reducing to empty after cleaning."""
        result_none = parse_voice_intent(None)
        self.assertEqual(result_none["intent"], "UNKNOWN")

        # An object that can be casted to string but results in no matching intent
        result_int = parse_voice_intent(12345)
        self.assertEqual(result_int["intent"], "UNKNOWN")

        # String containing only filler words and punctuation
        result_only_fillers = parse_voice_intent("呃那个，啊。")
        self.assertEqual(result_only_fillers["intent"], "UNKNOWN")
        self.assertEqual(result_only_fillers["entities"], {})

        # Test class object that fails string conversion or results in no intent
        class Unstringable:
            def __str__(self):
                raise ValueError("Cannot stringify")

        result_fail = parse_voice_intent(Unstringable())
        self.assertEqual(result_fail["intent"], "UNKNOWN")

    def test_multiple_intents(self):
        """Test scheduling meeting and leave requests."""
        # Meeting request
        result_meeting = parse_voice_intent("明天下午我们拉个会讨论一下")
        self.assertEqual(result_meeting["intent"], "SCHEDULE_MEETING")
        self.assertEqual(result_meeting["entities"].get("time"), "明天")

        # Leave request
        result_leave = parse_voice_intent("老板我下周一想请个年假")
        self.assertEqual(result_leave["intent"], "LEAVE_REQUEST")
        self.assertEqual(result_leave["entities"].get("leave_type"), "年假")
        self.assertEqual(result_leave["entities"].get("time"), "下周")

if __name__ == '__main__':
    unittest.main()
