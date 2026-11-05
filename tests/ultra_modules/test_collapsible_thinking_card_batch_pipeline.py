import unittest
import time
from ultra_modules.collapsible_thinking_card_batch_pipeline import ThinkingCardBuilder, BatchPipeline

class TestCollapsibleThinkingCardBatchPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = BatchPipeline(max_workers=5)

    def test_normal_operation(self):
        """Test normal operation with valid data."""
        records = [
            {"conclusion": "Test Conclusion 1", "reasoning": "Test Reasoning 1", "record_id": "1"},
            {"conclusion": "Test Conclusion 2", "reasoning": "Test Reasoning 2", "record_id": "2"}
        ]
        result = self.pipeline.run_batch("batch_1", records)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(result["results"]), 2)

        # Check generated card structure
        card_1 = next(r["card"] for r in result["results"] if r["record_id"] == "1")
        self.assertEqual(card_1["elements"][0]["text"]["content"], "**Conclusion:**\nTest Conclusion 1")
        self.assertTrue(card_1["elements"][1]["is_collapsed"])
        self.assertEqual(card_1["elements"][1]["elements"][0]["content"], "Test Reasoning 1")
        self.assertEqual(card_1["elements"][2]["actions"][0]["value"]["record_id"], "1")

    def test_dirty_data_self_healing(self):
        """Test dirty data self-healing (e.g., malformed records)."""
        # Pass a list of non-dict items
        records = ["dirty_data_1", 123, None]
        result = self.pipeline.run_batch("batch_2", records)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(result["results"]), 3)

        for r in result["results"]:
            self.assertEqual(r["status"], "success")
            # Should have fallen back to defaults
            card = r["card"]
            self.assertEqual(card["elements"][0]["text"]["content"], "**Conclusion:**\nDefault Conclusion")
            self.assertEqual(card["elements"][1]["elements"][0]["content"], "Default Reasoning")
            self.assertIsNotNone(card["elements"][2]["actions"][0]["value"]["record_id"])

    def test_missing_parameter_default_fallbacks(self):
        """Test missing parameter default fallbacks and line limit."""
        # Long conclusion should be truncated to 3 lines
        long_conclusion = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        records = [
            {"conclusion": long_conclusion}, # missing reasoning and record_id
            {} # missing everything
        ]
        result = self.pipeline.run_batch("batch_3", records)

        card_1 = result["results"][0]["card"]
        self.assertEqual(card_1["elements"][0]["text"]["content"], "**Conclusion:**\nLine 1\nLine 2\nLine 3...")
        self.assertEqual(card_1["elements"][1]["elements"][0]["content"], "Default Reasoning")

        card_2 = result["results"][1]["card"]
        self.assertEqual(card_2["elements"][0]["text"]["content"], "**Conclusion:**\nDefault Conclusion")

    def test_extreme_boundaries(self):
        """Test boundaries (0 records, > 1000 records)."""
        # 0 records
        result_empty = self.pipeline.run_batch("batch_empty", [])
        self.assertEqual(result_empty["status"], "completed")
        self.assertEqual(len(result_empty["results"]), 0)

        # > 1000 records
        records_large = [{"record_id": str(i)} for i in range(1050)]
        result_large = self.pipeline.run_batch("batch_large", records_large)
        self.assertEqual(result_large["status"], "completed")
        # Should be capped at 1000
        self.assertEqual(len(result_large["results"]), 1000)

    def test_progress_snapshot_and_non_blocking(self):
        """Test progress snapshot and non-blocking async execution."""
        records = [{"record_id": str(i)} for i in range(50)]
        batch_id = "batch_async"

        thread = self.pipeline.run_batch_async(batch_id, records)

        # Check snapshot immediately
        snapshot = self.pipeline.get_snapshot(batch_id)
        self.assertIsNotNone(snapshot)
        self.assertIn(snapshot["status"], ["running", "completed"])

        # Wait for completion
        thread.join()

        final_snapshot = self.pipeline.get_snapshot(batch_id)
        self.assertEqual(final_snapshot["status"], "completed")
        self.assertEqual(final_snapshot["progress"], 100)
        self.assertEqual(final_snapshot["completed"], 50)
        self.assertEqual(final_snapshot["total"], 50)

if __name__ == '__main__':
    unittest.main()
