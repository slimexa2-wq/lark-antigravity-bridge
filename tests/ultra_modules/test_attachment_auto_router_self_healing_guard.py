import unittest
import time
import uuid
from ultra_modules.attachment_auto_router_self_healing_guard import AttachmentAutoRouterSelfHealingGuard

class TestAttachmentAutoRouterSelfHealingGuard(unittest.TestCase):

    def setUp(self):
        self.guard = AttachmentAutoRouterSelfHealingGuard()

    def test_normal_execution_matching_engines(self):
        """Test that normal inputs are routed correctly to the appropriate engines."""
        # Test Weekly Report
        result_weekly = self.guard.process_and_route(file_name="周报_2023.xlsx", file_content="This is my weekly report.")
        self.assertEqual(result_weekly["engine"], "WEEKLY_REPORT_ENGINE")

        # Test Commission
        result_commission = self.guard.process_and_route(file_name="提成明细.xlsx", file_content="sales bonus data")
        self.assertEqual(result_commission["engine"], "COMMISSION_ENGINE")

        # Test Bidding
        result_bidding = self.guard.process_and_route(file_name="投标书_V1.docx", file_content="bidding details")
        self.assertEqual(result_bidding["engine"], "BIDDING_ENGINE")

        # Test Comic
        result_comic = self.guard.process_and_route(file_name="manga_script.txt", file_content="漫剧剧本大纲")
        self.assertEqual(result_comic["engine"], "COMIC_ENGINE")

        # Test Unknown
        result_unknown = self.guard.process_and_route(file_name="general_notes.txt", file_content="just some notes")
        self.assertEqual(result_unknown["engine"], "UNKNOWN_ENGINE")

    def test_dirty_data_self_healing(self):
        """Test healing of dirty data: non-strings, control characters, missing extensions."""
        # Intentionally messy data
        # Control characters like \x01, \x08 should be stripped.
        dirty_file_name = "data\x01\x08" # No extension
        dirty_content = 12345 # Not a string, should be stringified
        metadata = "Not a dict" # Should fallback to {}

        result = self.guard.process_and_route(
            file_name=dirty_file_name,
            file_content=dirty_content,
            metadata=metadata
        )

        # Missing extension self-healing adds .txt for unknown content
        self.assertEqual(result["healed_file_name"], "data.txt")
        # Content "12345" doesn't match any engine, so UNKNOWN
        self.assertEqual(result["engine"], "UNKNOWN_ENGINE")

    def test_missing_parameters_fallback(self):
        """Test that missing parameters (None) don't crash and get sane defaults."""
        result = self.guard.process_and_route(file_id=None, file_name=None, file_content=None, metadata=None)

        self.assertTrue(result["task_id"] is not None)
        self.assertEqual(result["healed_file_name"], ".txt") # Empty name + missing extension logic
        self.assertEqual(result["engine"], "UNKNOWN_ENGINE")

    def test_undo_mechanism_success_within_5_seconds(self):
        """Test that undo works successfully within the 5 second window."""
        result = self.guard.process_and_route(file_name="周报.xlsx")
        task_id = result["task_id"]

        undo_result = self.guard.undo(task_id)

        self.assertTrue(undo_result["success"])
        self.assertEqual(undo_result["message"], "Undo successful.")
        self.assertEqual(self.guard._snapshots[task_id]["status"], "undone")

    def test_undo_mechanism_failure_after_5_seconds(self):
        """Test that undo fails if attempted after the 5 second window expires."""
        result = self.guard.process_and_route(file_name="提成.xlsx")
        task_id = result["task_id"]

        # Manually alter the snapshot timestamp to simulate time passing (> 5 seconds)
        self.guard._snapshots[task_id]["timestamp"] -= 6.0

        undo_result = self.guard.undo(task_id)

        self.assertFalse(undo_result["success"])
        self.assertEqual(undo_result["message"], "Undo time window expired.")
        self.assertEqual(self.guard._snapshots[task_id]["status"], "routed")

if __name__ == '__main__':
    unittest.main()
