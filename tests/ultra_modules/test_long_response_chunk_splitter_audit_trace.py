import unittest
from ultra_modules.long_response_chunk_splitter_audit_trace import LongResponseChunkSplitterAuditTrace

class TestLongResponseChunkSplitterAuditTrace(unittest.TestCase):

    def setUp(self):
        self.splitter = LongResponseChunkSplitterAuditTrace(max_chunk_size=100)

    def test_normal_paragraph_semantics_splitting(self):
        """Test normal data splitting with paragraph semantics."""
        text = "This is the first paragraph.\n\nThis is the second paragraph."
        result = self.splitter.split_and_trace(text)

        chunks = result["chunks"]
        audit_trace = result["audit_trace"]

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

        # Verify trace entry for completion
        completion_trace = audit_trace[-1]
        self.assertEqual(completion_trace["step"], "split_execution_complete")

        # Longer text testing
        text2 = "A" * 60 + "\n\n" + "B" * 60
        result2 = self.splitter.split_and_trace(text2)

        self.assertEqual(len(result2["chunks"]), 2)
        self.assertEqual(result2["chunks"][0], "A" * 60)
        self.assertEqual(result2["chunks"][1], "B" * 60)

    def test_dirty_data_self_healing(self):
        """Test handling of None, non-string types, and missing fields."""
        # Test None
        res_none = self.splitter.split_and_trace(None)
        self.assertEqual(res_none["chunks"], [])
        self.assertTrue(any(t["step"] == "data_healing" for t in res_none["audit_trace"]))

        # Test non-string type (int)
        res_int = self.splitter.split_and_trace(12345)
        self.assertEqual(res_int["chunks"], ["12345"])
        self.assertTrue(any(t["step"] == "data_healing" for t in res_int["audit_trace"]))

        # Test empty string (only spaces)
        res_empty = self.splitter.split_and_trace("   \n  \t  ")
        self.assertEqual(res_empty["chunks"], [])
        self.assertTrue(any(t["step"] == "whitespace_normalization" for t in res_empty["audit_trace"]))

    def test_parameter_defaults_fallback(self):
        """Test zero-configuration parameter fallback for extreme/invalid inputs."""
        # Invalid initialization parameter
        bad_splitter = LongResponseChunkSplitterAuditTrace(max_chunk_size=-10)
        self.assertEqual(bad_splitter.max_chunk_size, 2000)

        # Invalid custom parameter in call
        text = "Some normal text."
        res = bad_splitter.split_and_trace(text, custom_max_chunk_size="invalid")
        self.assertTrue(any(t["step"] == "param_healing" for t in res["audit_trace"]))
        self.assertEqual(len(res["chunks"]), 1)

    def test_extreme_boundaries(self):
        """Test extreme boundaries like a single word longer than max_chunk_size."""
        # A single line longer than 100 characters, no spaces or newlines
        extreme_text = "A" * 250
        result = self.splitter.split_and_trace(extreme_text)

        chunks = result["chunks"]
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 100)
        self.assertEqual(len(chunks[1]), 100)
        self.assertEqual(len(chunks[2]), 50)

        self.assertTrue(any(t["step"] == "extreme_boundary_handling" for t in result["audit_trace"]))

        # Mixed long line and short lines
        mixed_text = "Short line.\n" + ("B" * 150) + "\nAnother short line."
        res2 = self.splitter.split_and_trace(mixed_text)

        # Check that no chunk exceeds the max length of 100 and order is preserved
        chunks2 = res2["chunks"]
        for chunk in chunks2:
            self.assertTrue(len(chunk) <= 100)

        # Specific assertions to ensure order is preserved
        self.assertEqual(chunks2[0], "Short line.")
        self.assertEqual(chunks2[1], "B" * 100)
        self.assertEqual(chunks2[2], "B" * 50)
        self.assertEqual(chunks2[3], "Another short line.")

    def test_data_deduplication_and_trace_logic(self):
        """Test data deduplication (excessive blank lines) and diff highligher trace logic."""
        text = "Para 1.\n\n\n\n\nPara 2."
        result = self.splitter.split_and_trace(text)

        # Check deduplication
        self.assertEqual(result["chunks"], ["Para 1.\n\nPara 2."])

        # Check audit trace
        audit_trace = result["audit_trace"]
        trace = next(t for t in audit_trace if t["step"] == "whitespace_normalization")

        self.assertEqual(trace["original_length"], len(text))
        self.assertEqual(trace["modified_length"], len("Para 1.\n\nPara 2."))
        self.assertTrue("Changed from" in trace["diff_highlight"])

if __name__ == '__main__':
    unittest.main()
