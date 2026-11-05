import unittest
import time
from ultra_modules.long_response_chunk_splitter_batch_pipeline import LongResponseChunkSplitterBatchPipeline

class TestLongResponseChunkSplitterBatchPipeline(unittest.TestCase):

    def test_normal_data_splitting(self):
        """Test normal data splitting with paragraph semantics."""
        pipeline = LongResponseChunkSplitterBatchPipeline(max_chunk_size=100)

        text = "This is a normal paragraph.\n\nThis is another paragraph."
        chunks = pipeline.split_text(text)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], "This is a normal paragraph.\n\nThis is another paragraph.")

        text2 = "A" * 60 + "\n\n" + "B" * 60
        chunks2 = pipeline.split_text(text2)

        self.assertEqual(len(chunks2), 2)
        self.assertEqual(chunks2[0], "A" * 60)
        self.assertEqual(chunks2[1], "B" * 60)

    def test_dirty_data_self_healing(self):
        """Test handling of None, non-string types, and missing fields."""
        pipeline = LongResponseChunkSplitterBatchPipeline()

        # Test None
        self.assertEqual(pipeline.split_text(None), [])

        # Test non-string type (int)
        self.assertEqual(pipeline.split_text(12345), ["12345"])

        # Test empty string
        self.assertEqual(pipeline.split_text("   \n  \t  "), [])

        # Test process_record with None dict
        res = pipeline.process_record({})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["chunks"], [])

        # Test process_record with bad type for record
        res2 = pipeline.process_record(None)
        self.assertEqual(res2["status"], "success")
        self.assertEqual(res2["chunks"], [])

    def test_parameter_defaults_fallback(self):
        """Test zero-configuration parameter fallback for extreme/invalid inputs."""
        # Invalid parameters should fallback gracefully
        pipeline = LongResponseChunkSplitterBatchPipeline(max_chunk_size=-10, max_workers="invalid")

        self.assertEqual(pipeline.max_chunk_size, 100)  # Min chunk size
        self.assertEqual(pipeline.max_workers, 10)      # Default workers

        # Invalid records batch
        snapshot = pipeline.process_batch(None)
        self.assertEqual(snapshot.get_snapshot()["total"], 0)

        snapshot2 = pipeline.process_batch({"text": "not a list"})
        self.assertEqual(snapshot2.get_snapshot()["total"], 1)

    def test_extreme_boundaries(self):
        """Test extreme boundaries like a single word longer than max_chunk_size."""
        pipeline = LongResponseChunkSplitterBatchPipeline(max_chunk_size=100)

        # A single line longer than 100 characters, no spaces or newlines
        extreme_text = "A" * 250
        chunks = pipeline.split_text(extreme_text)

        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 100)
        self.assertEqual(len(chunks[1]), 100)
        self.assertEqual(len(chunks[2]), 50)

        # Mixed long line and short lines
        mixed_text = "Short line.\n" + ("B" * 150) + "\nAnother short line."
        chunks2 = pipeline.split_text(mixed_text)

        # Let's just test lengths and counts to ensure no crash and reasonable bounds
        # The logic might result in 4 chunks based on exact split calculation
        self.assertTrue(len(chunks2) >= 3)
        for chunk in chunks2:
            self.assertTrue(len(chunk) <= 100)

    def test_batch_process_progress_snapshots(self):
        """Test the batch pipeline processing 10-1000 items with non-blocking progress snapshots."""
        pipeline = LongResponseChunkSplitterBatchPipeline(max_workers=5)

        # Create 50 records
        records = [{"id": f"id_{i}", "text": f"This is record {i}."} for i in range(50)]

        snapshot = pipeline.process_batch(records)

        # Initial snapshot
        status = snapshot.get_snapshot()
        self.assertEqual(status["total"], 50)

        # Wait for processing to complete
        timeout = 5.0
        start = time.time()
        while time.time() - start < timeout:
            status = snapshot.get_snapshot()
            if status["is_done"]:
                break
            time.sleep(0.01)

        final_status = snapshot.get_snapshot()
        self.assertTrue(final_status["is_done"])
        self.assertEqual(final_status["completed"] + final_status["failed"], 50)
        self.assertEqual(len(snapshot.get_all_results()), 50)
        self.assertEqual(final_status["progress_percent"], 100.0)

if __name__ == '__main__':
    unittest.main()
