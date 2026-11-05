import unittest
from ultra_modules.multi_bot_mention_dispatcher_integration_bridge import MultiBotMentionDispatcherIntegrationBridge

class TestMultiBotMentionDispatcherIntegrationBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = MultiBotMentionDispatcherIntegrationBridge()

    def test_normal_operation_with_schema_conversion(self):
        # Test mapping of old fields to new fields
        payload_v1 = {
            "at_list": ["@大肥鱼", "@招聘"],
            "text": "Check this out"
        }
        adapted = self.bridge.adapt_schema(payload_v1)
        self.assertEqual(adapted["mentions"], ["@大肥鱼", "@招聘"])
        self.assertEqual(adapted["content"], "Check this out")

        # Test full processing
        result = self.bridge.process_webhook(payload_v1)
        # Expected: Total 2, Success 2
        lines = result.split("\n")
        self.assertEqual(len(lines), 3)
        self.assertIn("Total mentions: 2", lines[0])
        self.assertIn("Processed successfully: 2", lines[0])

    def test_dirty_data_self_healing(self):
        # None payload
        result_none = self.bridge.process_webhook(None)
        lines_none = result_none.split("\n")
        self.assertEqual(len(lines_none), 3)
        self.assertEqual(lines_none[0], "No bots mentioned.")

        # String instead of dict
        result_str = self.bridge.process_webhook("Just a string payload")
        lines_str = result_str.split("\n")
        self.assertEqual(len(lines_str), 3)
        self.assertEqual(lines_str[0], "No bots mentioned.")

        # Incorrect type for mentions
        payload_invalid_mentions = {
            "mentions": "Not a list",
            "content": "Hello"
        }
        result_invalid = self.bridge.process_webhook(payload_invalid_mentions)
        self.assertIn("No bots mentioned.", result_invalid)

    def test_missing_parameter_default_fallbacks(self):
        # Empty dict
        payload_empty = {}
        adapted = self.bridge.adapt_schema(payload_empty)
        self.assertEqual(adapted["mentions"], [])
        self.assertEqual(adapted["content"], "")

        # Dict with missing key fields
        payload_missing = {"message_id": "123"}
        adapted2 = self.bridge.adapt_schema(payload_missing)
        self.assertEqual(adapted2["mentions"], [])
        self.assertEqual(adapted2["content"], "")

    def test_extreme_boundaries(self):
        # Very large number of mentions
        large_mentions = [f"@Bot{i}" for i in range(150)]
        payload_extreme = {
            "mentions": large_mentions,
            "content": "Load test"
        }
        result = self.bridge.process_webhook(payload_extreme)

        # Should stop processing after 100 mentions, adding an error entry
        lines = result.split("\n")
        self.assertEqual(len(lines), 3)
        # The result includes up to index 100, so total is 101 records processed by dispatch
        self.assertIn("Total mentions: 102", lines[0])
        self.assertIn("Errors: 1", lines[1])

    def test_summary_card_formatting(self):
        # Ensure exactly 3 lines and no HTML
        payload = {
            "mentions": ["@大肥鱼", "@UnknownBot"],
            "content": "Test formatting"
        }
        result = self.bridge.process_webhook(payload)
        lines = result.split("\n")

        self.assertEqual(len(lines), 3)
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)

        # First line
        self.assertIn("Total mentions: 2", lines[0])
        self.assertIn("Processed successfully: 1", lines[0])

        # Second line
        self.assertIn("Errors: 0", lines[1])
        self.assertIn("Unknown bots: 1", lines[1])

        # Third line (Partial success)
        self.assertEqual(lines[2], "Partial success. Review errors/unknowns.")

if __name__ == "__main__":
    unittest.main()
