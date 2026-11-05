import unittest
import time
import sys
import os

# Add project root to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ultra_modules.long_response_chunk_splitter_self_healing_guard import LongResponseChunkSplitter

class TestLongResponseChunkSplitter(unittest.TestCase):
    def setUp(self):
        self.splitter = LongResponseChunkSplitter(default_max_length=50)

    def test_normal_case_semantic_boundaries(self):
        # A text that should be split around paragraphs or newlines
        text = "This is a paragraph.\n\nThis is another paragraph."
        # Length of text is 46, which is less than 50. Wait, let me make it longer.
        text = "This is the first paragraph that is long enough.\n\nAnd this is the second paragraph which is also quite long."
        # Expected to be split at \n\n because max length is 50.
        chunks = self.splitter.split_and_snapshot(text, max_length=60)
        self.assertEqual(len(chunks), 2)
        self.assertIn("This is the first paragraph that is long enough.", chunks[0])
        self.assertIn("And this is the second paragraph", chunks[1])

    def test_dirty_data_self_healing(self):
        # Passing None
        chunks_none = self.splitter.split_and_snapshot(None)
        self.assertEqual(chunks_none, [])

        # Passing an integer
        chunks_int = self.splitter.split_and_snapshot(12345)
        self.assertEqual(chunks_int, ["12345"])

        # Passing an object without proper str conversion or something complex
        class DirtyObj:
            def __str__(self):
                raise ValueError("Bad string conversion")

        chunks_dirty = self.splitter.split_and_snapshot(DirtyObj())
        self.assertEqual(chunks_dirty, [])

    def test_default_fallbacks(self):
        # Calling with no arguments
        chunks = self.splitter.split_and_snapshot()
        self.assertEqual(chunks, [])

        # Negative max length
        text = "short text"
        chunks_neg = self.splitter.split_and_snapshot(text, max_length=-10)
        self.assertEqual(chunks_neg, ["short text"])
        snapshot = self.splitter.undo_snapshot()
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["max_length"], self.splitter.default_max_length)

    def test_extreme_boundary_no_newlines(self):
        # Very long string with no newlines
        text = "a" * 150
        chunks = self.splitter.split_and_snapshot(text, max_length=50)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], "a" * 50)
        self.assertEqual(chunks[1], "a" * 50)
        self.assertEqual(chunks[2], "a" * 50)

    def test_undo_mechanism(self):
        text = "Undo this"
        self.splitter.split_and_snapshot(text, max_length=50)

        # Undo within 5 seconds
        snapshot = self.splitter.undo_snapshot()
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["original_text"], text)

        # Undo again should return None because it was popped
        snapshot_again = self.splitter.undo_snapshot()
        self.assertIsNone(snapshot_again)

    def test_undo_timeout(self):
        text = "Time out this"
        # Mock time.time to simulate passage of time
        original_time = time.time
        try:
            current_time = original_time()
            time.time = lambda: current_time
            self.splitter.split_and_snapshot(text, max_length=50)

            # Fast forward 6 seconds
            time.time = lambda: current_time + 6.0
            snapshot = self.splitter.undo_snapshot()
            self.assertIsNone(snapshot)
        finally:
            time.time = original_time

if __name__ == '__main__':
    unittest.main()
