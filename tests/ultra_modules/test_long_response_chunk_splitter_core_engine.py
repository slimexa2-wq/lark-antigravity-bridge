import unittest
from ultra_modules.long_response_chunk_splitter_core_engine import split_long_response

class TestLongResponseChunkSplitter(unittest.TestCase):

    def test_normal_data_no_split(self):
        """Test with normal data that doesn't require splitting"""
        text = "This is a short response."
        result = split_long_response(text, max_chunk_size=100)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], text)

    def test_dirty_data_self_healing(self):
        """Test with dirty data like None or integer, should handle gracefully"""
        self.assertEqual(split_long_response(None), [])

        result_int = split_long_response(12345, max_chunk_size=3)
        self.assertEqual(len(result_int), 2)
        self.assertEqual(result_int[0], "123")
        self.assertEqual(result_int[1], "45")

        class BadStr:
            def __str__(self):
                raise ValueError("cannot convert")

        self.assertEqual(split_long_response(BadStr()), [])

    def test_missing_parameter_fallback(self):
        """Test with missing or invalid max_chunk_size, should fallback to default 30000"""
        long_text = "a" * 30001

        # Missing param (default used)
        result1 = split_long_response(long_text)
        self.assertEqual(len(result1), 2)
        self.assertEqual(len(result1[0]), 30000)
        self.assertEqual(result1[1], "a")

        # Invalid param types
        result2 = split_long_response(long_text, max_chunk_size=None)
        self.assertEqual(len(result2), 2)

        result3 = split_long_response(long_text, max_chunk_size=-50)
        self.assertEqual(len(result3), 2)

    def test_semantic_splitting_headings(self):
        """Test splitting at markdown headings"""
        text = "Intro text here.\n## Heading 2\nMore text here.\n# Heading 1\nFinal text."
        # Choose a size that forces a split but is large enough to contain the headings
        result = split_long_response(text, max_chunk_size=30)

        # Should split before headings
        self.assertTrue(len(result) > 1)

        # Reconstruct should equal original
        self.assertEqual("".join(result), text)

        # Check that it split around '\n## Heading 2'
        self.assertTrue('\n## ' in result[1] or '\n## ' in result[0])

    def test_semantic_splitting_paragraphs_and_sentences(self):
        """Test splitting at paragraphs and sentence boundaries"""
        text = "This is paragraph one.\n\nThis is paragraph two. It has two sentences."

        # Split on paragraph
        result_para = split_long_response(text, max_chunk_size=30)
        self.assertEqual(result_para[0], "This is paragraph one.\n\n")
        self.assertEqual(result_para[1], "This is paragraph two.")
        self.assertEqual(result_para[2], " It has two sentences.")
        self.assertEqual("".join(result_para), text)

        # Split on sentence specifically (no paragraphs)
        text_sent = "First sentence here. Second sentence follows."
        result_sent = split_long_response(text_sent, max_chunk_size=30)
        self.assertEqual(result_sent[0], "First sentence here.")
        self.assertEqual(result_sent[1], " Second sentence follows.")

    def test_extreme_boundary_conditions(self):
        """Test hard split fallback when there are no semantic boundaries"""
        text = "a" * 100
        result = split_long_response(text, max_chunk_size=30)

        self.assertEqual(len(result), 4)
        self.assertEqual(len(result[0]), 30)
        self.assertEqual(len(result[1]), 30)
        self.assertEqual(len(result[2]), 30)
        self.assertEqual(len(result[3]), 10)
        self.assertEqual("".join(result), text)

if __name__ == '__main__':
    unittest.main()
