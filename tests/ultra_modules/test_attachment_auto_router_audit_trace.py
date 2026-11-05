import unittest
from ultra_modules.attachment_auto_router_audit_trace import AttachmentAutoRouterAuditTrace, DifferenceHighlighter

class TestAttachmentAutoRouterAuditTrace(unittest.TestCase):
    def setUp(self):
        self.router = AttachmentAutoRouterAuditTrace()

    def test_normal_routing_cases(self):
        """Test normal routing cases (e.g., Excel for Commission, Word for Bid Document)."""
        # Excel -> commission_engine by default, or weekly_report if keyword matches
        res1 = self.router.route(filename="2024_提成.xlsx")
        self.assertEqual(res1["status"], "success")
        self.assertEqual(res1["engine"], "commission_engine")

        res2 = self.router.route(filename="team_weekly_report.xlsx")
        self.assertEqual(res2["status"], "success")
        self.assertEqual(res2["engine"], "weekly_report_engine")

        # Word -> bid_document_engine
        res3 = self.router.route(filename="project_bid_document.docx")
        self.assertEqual(res3["status"], "success")
        self.assertEqual(res3["engine"], "bid_document_engine")

        # TXT -> comic_drama_engine
        res4 = self.router.route(filename="漫剧_script.txt")
        self.assertEqual(res4["status"], "success")
        self.assertEqual(res4["engine"], "comic_drama_engine")

    def test_missing_parameter_fallback(self):
        """Test missing parameter fallback (e.g., filename=None)."""
        res = self.router.route(filename=None)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["filename"], "default_attachment.txt")
        self.assertEqual(res["engine"], "comic_drama_engine")  # .txt defaults to comic_drama

        # Verify log is silent in return but recorded in backend
        logs = self.router.audit_logger.get_logs()
        self.assertTrue(any(log["action"] == "missing_parameter_fallback" for log in logs))

    def test_dirty_data_self_healing(self):
        """Test dirty data self-healing (verifying the filename gets cleaned and diff is logged)."""
        dirty_filename = "bad @# name $% \n with \t chars.xlsx"
        res = self.router.route(filename=dirty_filename)

        self.assertEqual(res["status"], "success")
        expected_repaired = "bad name with chars.xlsx"
        self.assertEqual(res["filename"], expected_repaired)

        logs = self.router.audit_logger.get_logs()
        sanitize_logs = [log for log in logs if log["action"] == "sanitize"]
        self.assertTrue(len(sanitize_logs) > 0)

        last_sanitize_log = sanitize_logs[-1]
        self.assertEqual(last_sanitize_log["details"]["original"], dirty_filename)
        self.assertEqual(last_sanitize_log["details"]["repaired"], expected_repaired)

        expected_diff = DifferenceHighlighter.highlight(dirty_filename, expected_repaired)
        self.assertEqual(last_sanitize_log["details"]["diff"], expected_diff)

    def test_empty_data_boundary_cases(self):
        """Test empty data boundary cases."""
        # A filename that consists entirely of invalid characters
        res = self.router.route(filename="@#$%^&*()")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["filename"], "unnamed_file.txt")
        self.assertEqual(res["engine"], "comic_drama_engine") # defaults to txt logic

        logs = self.router.audit_logger.get_logs()
        self.assertTrue(any(log["action"] == "empty_data_boundary" for log in logs))

    def test_fallback_routing_logic(self):
        """Test fallback routing logic for unknown file types."""
        res = self.router.route(filename="image_file.png")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["filename"], "image_file.png")
        self.assertEqual(res["engine"], "unknown")

    def test_deduplication(self):
        """Test file deduplication."""
        res1 = self.router.route(filename="duplicate.txt", file_content=b"123")
        self.assertEqual(res1["status"], "success")

        res2 = self.router.route(filename="duplicate.txt", file_content=b"123")
        self.assertEqual(res2["status"], "ignored")
        self.assertEqual(res2["reason"], "duplicate")

if __name__ == '__main__':
    unittest.main()
