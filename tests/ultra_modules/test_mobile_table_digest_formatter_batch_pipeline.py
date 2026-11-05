import unittest
from ultra_modules.mobile_table_digest_formatter_batch_pipeline import MobileTableDigestFormatter, MobileTableDigestBatchPipeline

class TestMobileTableDigestBatchPipeline(unittest.TestCase):

    def setUp(self):
        self.formatter = MobileTableDigestFormatter()
        self.pipeline = MobileTableDigestBatchPipeline(max_workers=4)

    def test_normal_data(self):
        record = {
            "id": "r1",
            "title": "Q3 Financials",
            "status": "success",
            "metrics": {
                "revenue": 1500.50,
                "cost": 1000.00
            },
            "attachment_url": "https://example.com/q3.pdf"
        }
        result = self.formatter.format_record(record)

        self.assertEqual(result["original_id"], "r1")
        self.assertFalse(result["is_anomaly"])
        self.assertTrue(result["mobile_ui_optimized"])
        self.assertEqual(result["attachment_card"]["url"], "https://example.com/q3.pdf")

        # Check 3 lines
        lines = result["summary"].split("\n")
        self.assertEqual(len(lines), 3)
        self.assertIn("Q3 Financials", lines[0])
        self.assertIn("[SUCCESS]", lines[0])
        self.assertIn("Rev: $1500.50", lines[1])
        self.assertIn("Cost: $1000.00", lines[1])
        self.assertIn("Profit: $500.50", lines[2])

    def test_dirty_data_self_healing(self):
        # Strings instead of numbers, weird status
        record = {
            "title": "   Messy Report   ",
            "status": "FAILED",
            "metrics": {
                "revenue": "invalid_number",
                "cost": None
            }
        }
        result = self.formatter.format_record(record)

        self.assertTrue(result["is_anomaly"])
        lines = result["summary"].split("\n")
        self.assertIn("Messy Report", lines[0])
        self.assertIn("🚨 [FAILED]", lines[0])
        self.assertIn("Rev: $0.00", lines[1])
        self.assertIn("Cost: $0.00", lines[1])
        self.assertIn("Profit: $0.00", lines[2])

    def test_missing_parameters_fallback(self):
        # Completely empty record
        record = {}
        result = self.formatter.format_record(record)

        self.assertFalse(result["is_anomaly"]) # default unknown, profit 0
        self.assertEqual(result["attachment_card"]["url"], "https://fallback.example.com/default_attachment.pdf")

        lines = result["summary"].split("\n")
        self.assertIn("Unnamed Report", lines[0])
        self.assertIn("[UNKNOWN]", lines[0])
        self.assertIn("Rev: $0.00", lines[1])

        # Test completely invalid record type
        result2 = self.formatter.format_record("I am a string, not a dict")
        lines2 = result2["summary"].split("\n")
        self.assertIn("Unnamed Report", lines2[0])

    def test_extreme_boundary_1000_records(self):
        records = [{"id": f"rec_{i}", "metrics": {"revenue": i, "cost": i/2}} for i in range(1000)]
        results = self.pipeline.process_batch(records)
        self.assertEqual(len(results), 1000)

        # Verify first and last
        # Order is maintained in process_batch
        self.assertEqual(results[0]["original_id"], "rec_0")
        self.assertEqual(results[999]["original_id"], "rec_999")

        self.assertIn("Profit: $0.00", results[0]["summary"])
        self.assertIn("Profit: $499.50", results[999]["summary"])

    def test_stream_processing_and_snapshots(self):
        records = [{"id": f"rec_{i}", "title": f"Stream {i}"} for i in range(50)]
        stream = self.pipeline.process_batch_stream(records)

        results = list(stream)
        self.assertEqual(len(results), 50)

        # Verify progress snapshots
        completed_counts = [r["_pipeline_progress"]["completed"] for r in results]
        self.assertEqual(sorted(completed_counts), list(range(1, 51)))

        percents = [r["_pipeline_progress"]["percent"] for r in results]
        self.assertEqual(max(percents), 100.0)

if __name__ == '__main__':
    unittest.main()
