import unittest
from ultra_modules.slash_command_quick_menu_audit_trace import SlashCommandQuickMenuAuditTraceRouter

class TestSlashCommandQuickMenuAuditTraceRouter(unittest.TestCase):
    def setUp(self):
        self.router = SlashCommandQuickMenuAuditTraceRouter()

    def test_normal_operation(self):
        """1. Normal operation with proper command and params."""
        result = self.router.route("/周报", kwargs_list=[("period", "last_week"), ("user", "john_doe")])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "generate_weekly_report")
        self.assertEqual(result["data"], {"period": "last_week", "user": "john_doe"})

        # Verify trace contains basic initialization and success
        actions = [entry["action"] for entry in self.router.audit_trace]
        self.assertIn("initialization", actions)
        self.assertIn("routing_success", actions)

    def test_missing_parameter_fallback(self):
        """2. Missing parameter fallback (defaults being injected)."""
        result = self.router.route("/提成")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "query_commission")
        self.assertEqual(result["data"], {"month": "current"})

        # Verify defaulting trace is captured
        defaulting_entries = [entry for entry in self.router.audit_trace if entry["action"] == "defaulting"]
        self.assertTrue(any("month missing" in entry["details"] for entry in defaulting_entries))

    def test_dirty_data_self_healing(self):
        """3. Dirty data self-healing (repairing control chars and whitespaces)."""
        result = self.router.route(" \x01/漫剧 \t\n", kwargs_list=[("\x00workspace\x0b", " project_x ")])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "open_comic_drama_workspace")
        self.assertEqual(result["data"], {"workspace": "project_x"})

        dirty_repairs = [entry for entry in self.router.audit_trace if entry["action"] == "dirty_data_repair"]
        self.assertGreater(len(dirty_repairs), 0)

    def test_extreme_boundaries(self):
        """4. Extreme boundaries (invalid types, missing input handling)."""
        result = self.router.route(None)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Unrecognized or empty command.")

        type_conversions = [entry for entry in self.router.audit_trace if entry["action"] == "type_conversion"]
        self.assertTrue(any("None converted" in entry["details"] for entry in type_conversions))

        # Test routing with unrecognized command type
        result_unrecognized = self.router.route(12345)
        self.assertEqual(result_unrecognized["status"], "error")
        self.assertEqual(result_unrecognized["message"], "Unrecognized or empty command.")

        type_conversions_2 = [entry for entry in self.router.audit_trace if entry["action"] == "type_conversion"]
        self.assertTrue(any("Non-string" in entry["details"] for entry in type_conversions_2))


    def test_deduplication_logic(self):
        """5. Deduplication logic when duplicate keys are encountered."""
        result = self.router.route("/标书", kwargs_list=[("type", "v1"), ("type", "v2"), ("type", "final_version")])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "retrieve_bidding_document")
        self.assertEqual(result["data"], {"type": "final_version"})

        dedup_entries = [entry for entry in self.router.audit_trace if entry["action"] == "deduplication"]
        # There should be 2 dedup log entries (v1 overwritten by v2, v2 overwritten by final_version)
        self.assertEqual(len(dedup_entries), 2)

        # Another test for state command
        result = self.router.route("/状态", kwargs_list=[("target", "db"), ("target", "web")])
        self.assertEqual(result["data"], {"target": "web"})

if __name__ == '__main__':
    unittest.main()
