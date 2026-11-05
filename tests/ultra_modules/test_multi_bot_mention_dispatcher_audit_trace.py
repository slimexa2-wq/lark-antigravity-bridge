import unittest
from unittest.mock import patch, MagicMock
from ultra_modules.multi_bot_mention_dispatcher_audit_trace import MultiBotMentionDispatcherAuditTrace

class TestMultiBotMentionDispatcherAuditTrace(unittest.TestCase):
    def setUp(self):
        self.dispatcher = MultiBotMentionDispatcherAuditTrace()

    def test_normal_execution(self):
        mentions = [
            {"bot_id": "bot_1", "bot_name": "Fish Bot", "message": "hello"},
            {"bot_id": "bot_2", "bot_name": "Data Bot", "message": "query"}
        ]
        result = self.dispatcher.process_mentions(mentions)

        self.assertEqual(len(result["valid_mentions"]), 2)
        self.assertEqual(result["summary"], "Processed 2 valid mention(s)")
        self.assertEqual(result["valid_mentions"][0]["bot_name"], "Fish Bot")

        trace = self.dispatcher.get_audit_trace()
        self.assertTrue(any(t["action"] == "mention_accepted" and t["details"]["processed_item"]["bot_id"] == "bot_1" for t in trace))

    def test_missing_parameters_fallback(self):
        # Test no args
        result = self.dispatcher.process_mentions()
        self.assertEqual(len(result["valid_mentions"]), 0)
        self.assertEqual(result["summary"], "No valid mentions found")

        trace = self.dispatcher.get_audit_trace()
        self.assertTrue(any(t["action"] == "init" and t["details"]["raw_mentions"] == [] for t in trace))

    def test_dirty_data_self_healing(self):
        # Invalid inputs (e.g. non-list, mixed list)
        result_non_list = self.dispatcher.process_mentions("invalid_string_input")
        self.assertEqual(len(result_non_list["valid_mentions"]), 0)

        result_dict = self.dispatcher.process_mentions({"bot_id": "bot_1", "message": "test"})
        self.assertEqual(len(result_dict["valid_mentions"]), 1)

        mentions = [
            "invalid_string",
            123,
            None,
            {"missing_id": "value"},
            {"bot_id": "bot_3", "message": "good_message"}
        ]

        result_mixed = self.dispatcher.process_mentions(mentions)
        self.assertEqual(len(result_mixed["valid_mentions"]), 1)
        self.assertEqual(result_mixed["valid_mentions"][0]["bot_id"], "bot_3")

        trace = self.dispatcher.get_audit_trace()
        dropped_count = sum(1 for t in trace if t["action"] == "dirty_data_dropped")
        self.assertEqual(dropped_count, 4)

    def test_deduplication(self):
        mentions = [
            {"bot_id": "bot_same", "bot_name": "Bot A", "message": "first call"},
            {"bot_id": "bot_same", "bot_name": "Bot B", "message": "second call"},
            {"bot_id": "bot_other", "bot_name": "Bot C", "message": "another"}
        ]
        result = self.dispatcher.process_mentions(mentions)

        self.assertEqual(len(result["valid_mentions"]), 2)
        self.assertEqual(result["summary"], "Processed 2 valid mention(s)")

        bot_ids = [m["bot_id"] for m in result["valid_mentions"]]
        self.assertEqual(bot_ids, ["bot_same", "bot_other"])

        trace = self.dispatcher.get_audit_trace()
        self.assertTrue(any(t["action"] == "duplicate_dropped" and t["details"]["bot_id"] == "bot_same" for t in trace))

    def test_item_processing_error_recovery(self):
        class BadItem(dict):
            def get(self, key, default=None):
                raise Exception("Simulated item access error")

        mentions = [
            BadItem({"bot_id": "b1"}),
            {"bot_id": "bot_good", "bot_name": "Good Bot", "message": "hello"}
        ]

        result = self.dispatcher.process_mentions(mentions)

        self.assertEqual(len(result["valid_mentions"]), 1)
        self.assertEqual(result["valid_mentions"][0]["bot_id"], "bot_good")

        trace = self.dispatcher.get_audit_trace()
        self.assertTrue(any(t["action"] == "item_processing_error" and "Simulated item access error" in t["details"]["error"] for t in trace))

    @patch('builtins.set')
    def test_extreme_boundary_crash_prevention(self, mock_set):
        # Simulate a crash when instantiating the set to test the outer try-except
        mock_set.side_effect = Exception("Simulated catastrophic failure")

        result = self.dispatcher.process_mentions([{"bot_id": "b1"}])

        self.assertEqual(len(result["valid_mentions"]), 0)
        self.assertEqual(result["summary"], "Internal error handled safely")

        trace = self.dispatcher.get_audit_trace()
        self.assertTrue(any(t["action"] == "extreme_failure_caught" and "Simulated catastrophic failure" in t["details"]["error"] for t in trace))

if __name__ == '__main__':
    unittest.main()
