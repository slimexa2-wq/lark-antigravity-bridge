import unittest
import datetime
from unittest.mock import patch
from ultra_modules.voice_message_intent_parser_audit_trace import VoiceIntentParser

class UncastableMock:
    def __str__(self):
        raise ValueError("Cannot cast to string")

class TestVoiceMessageIntentParserAuditTrace(unittest.TestCase):
    def setUp(self):
        self.parser = VoiceIntentParser()

    @patch('ultra_modules.voice_message_intent_parser_audit_trace.datetime')
    def test_normal_input_with_denoise(self, mock_datetime):
        mock_datetime.datetime.now.return_value = datetime.datetime(2023, 10, 15)

        # Test 1: Normal with denoise (stop words and punctuation)
        raw_text = "那个，把这月提成表核算一下！！！"
        result = self.parser.parse(raw_text, user_context={"user_id": "u123"})

        frontend = result.to_frontend()
        backend = result.to_backend_audit()

        # Check frontend simplicity
        self.assertEqual(frontend["intent"], "review_commission")
        self.assertEqual(frontend["entities"]["year"], 2023)
        self.assertEqual(frontend["entities"]["month"], 10)
        self.assertEqual(frontend["entities"]["target"], "u123")

        # Check backend audit trail
        self.assertEqual(backend["raw_input"], raw_text)
        self.assertEqual(backend["normalized_input"], "，把这月提成表核算一下！")
        self.assertTrue(any(log["step"] == "denoise" for log in backend["audit_logs"]))
        self.assertTrue(any(log["step"] == "normalization" for log in backend["audit_logs"]))

    def test_dirty_data_null_and_uncastable(self):
        # Test 2: Dirty Data / Null Handling

        # Case 2a: None input
        result1 = self.parser.parse(None)
        self.assertEqual(result1.intent, "noop")
        backend1 = result1.to_backend_audit()
        self.assertTrue(any(log["step"] == "input_repair" and log["before"] == "None" for log in backend1["audit_logs"]))

        # Case 2b: Integer input (castable)
        result2 = self.parser.parse(12345)
        self.assertEqual(result2.intent, "unknown")
        backend2 = result2.to_backend_audit()
        self.assertTrue(any(log["step"] == "input_repair" and log["before"] == "int" for log in backend2["audit_logs"]))

        # Case 2c: Uncastable object
        result3 = self.parser.parse(UncastableMock())
        self.assertEqual(result3.intent, "noop")
        backend3 = result3.to_backend_audit()
        self.assertTrue(any(log["step"] == "input_repair" and log["before"] == "Uncastable" for log in backend3["audit_logs"]))

    def test_missing_params_fallback(self):
        # Test 3: Missing Params / Default Fallback

        # Case 3a: Missing user_context for schedule_meeting
        result = self.parser.parse("咱们明天开个会议")
        frontend = result.to_frontend()
        self.assertEqual(frontend["intent"], "schedule_meeting")
        self.assertEqual(frontend["entities"]["duration_minutes"], 30)
        self.assertEqual(frontend["entities"]["participants"], ["current_user"])

        # Case 3b: Submit report defaulting
        result_report = self.parser.parse("写个总结")
        frontend_report = result_report.to_frontend()
        self.assertEqual(frontend_report["intent"], "submit_report")
        self.assertEqual(frontend_report["entities"]["report_type"], "weekly") # Default

        result_daily = self.parser.parse("写个日报")
        self.assertEqual(result_daily.to_frontend()["entities"]["report_type"], "daily")

        result_monthly = self.parser.parse("写个月报")
        self.assertEqual(result_monthly.to_frontend()["entities"]["report_type"], "monthly")

    @patch('ultra_modules.voice_message_intent_parser_audit_trace.datetime')
    def test_extreme_boundary_cross_year(self, mock_datetime):
        # Test 4: Extreme boundary cases (e.g. cross-year handling for review_commission)
        # Mock current time to January 15, 2024
        mock_datetime.datetime.now.return_value = datetime.datetime(2024, 1, 15)

        result = self.parser.parse("看一下上个月的提成")
        frontend = result.to_frontend()
        backend = result.to_backend_audit()

        self.assertEqual(frontend["intent"], "review_commission")
        self.assertEqual(frontend["entities"]["year"], 2023)
        self.assertEqual(frontend["entities"]["month"], 12)

        self.assertTrue(any(log["step"] == "boundary_handling" for log in backend["audit_logs"]))

        result2 = self.parser.parse("看一下去年的提成")
        frontend2 = result2.to_frontend()
        self.assertEqual(frontend2["entities"]["year"], 2023)
        self.assertEqual(frontend2["entities"]["month"], 1)

    def test_extreme_boundary_long_text(self):
        # Test 5: Extremely long text (truncation check)
        long_text = "开会" * 3000 # 6000 chars
        result = self.parser.parse(long_text)

        frontend = result.to_frontend()
        backend = result.to_backend_audit()

        # Should be truncated to 5000 and still parse intent
        self.assertEqual(frontend["intent"], "schedule_meeting")
        self.assertEqual(len(backend["normalized_input"]), 5000)
        self.assertTrue(any(log["step"] == "boundary_truncation" for log in backend["audit_logs"]))

if __name__ == '__main__':
    unittest.main()
