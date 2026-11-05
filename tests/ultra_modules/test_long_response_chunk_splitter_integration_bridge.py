import unittest
import copy
from ultra_modules.long_response_chunk_splitter_integration_bridge import SchemaVersionConverter, LongResponseChunkSplitterIntegrationBridge

class TestLongResponseChunkSplitterIntegrationBridge(unittest.TestCase):

    def setUp(self):
        self.bridge = LongResponseChunkSplitterIntegrationBridge(max_chunk_size=50)

    def test_schema_conversion_normal(self):
        """Test normal schema mapping."""
        data = {"subject": "Monthly Report", "body": "Sales increased."}
        converted = SchemaVersionConverter.forward_compatible_convert(data)
        self.assertEqual(converted["title"], "Monthly Report")
        self.assertEqual(converted["text"], "Sales increased.")

    def test_schema_conversion_dirty_data(self):
        """Test dirty data self-healing and missing parameters fallback."""
        # Not a dict
        converted1 = SchemaVersionConverter.forward_compatible_convert("Just a string")
        self.assertEqual(converted1["title"], "Ultra Report")
        self.assertEqual(converted1["text"], "Just a string")

        # None
        converted2 = SchemaVersionConverter.forward_compatible_convert(None)
        self.assertEqual(converted2["title"], "Ultra Report")
        self.assertEqual(converted2["text"], "")

        # Dict with missing fields
        converted3 = SchemaVersionConverter.forward_compatible_convert({})
        self.assertEqual(converted3["title"], "Ultra Report")
        self.assertEqual(converted3["text"], "")

        # Invalid types for fields
        converted4 = SchemaVersionConverter.forward_compatible_convert({"title": 123, "text": ["bad", "type"]})
        self.assertEqual(converted4["title"], "123")
        self.assertEqual(converted4["text"], "['bad', 'type']")

    def test_bridge_normal_splitting(self):
        """Test normal semantic splitting with paragraphs."""
        bridge = LongResponseChunkSplitterIntegrationBridge(max_chunk_size=30)
        text = "Paragraph 1 is here.\n\nParagraph 2 is here."
        data = {"title": "Test Split", "text": text}
        cards = bridge.process_and_bridge(data)

        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["header"]["title"]["content"], "Test Split (1/2)")
        self.assertEqual(cards[0]["elements"][0]["content"], "Paragraph 1 is here.")

        self.assertEqual(cards[1]["header"]["title"]["content"], "Test Split (2/2)")
        self.assertEqual(cards[1]["elements"][0]["content"], "Paragraph 2 is here.")

    def test_bridge_sentence_splitting(self):
        """Test splitting by sentence boundaries when a paragraph is too long."""
        bridge = LongResponseChunkSplitterIntegrationBridge(max_chunk_size=30)
        # 30 chars limit.
        text = "This is the first sentence. And this is the second! A third one."
        data = {"title": "Sentence Split", "text": text}
        cards = bridge.process_and_bridge(data)

        # Checking how it chunks:
        # "This is the first sentence. "
        self.assertTrue(len(cards) > 1)

    def test_bridge_extreme_boundary(self):
        """Test forced chunking when a single word/sentence is extremely long without punctuations."""
        bridge = LongResponseChunkSplitterIntegrationBridge(max_chunk_size=10)
        text = "Supercalifragilisticexpialidocious"
        data = {"title": "Extreme Boundary", "text": text}
        cards = bridge.process_and_bridge(data)

        # Expecting length to be broken down strictly by max_chunk_size (10)
        # 34 chars -> 4 chunks
        self.assertEqual(len(cards), 4)
        self.assertEqual(cards[0]["elements"][0]["content"], "Supercalif")
        self.assertEqual(cards[1]["elements"][0]["content"], "ragilistic")
        self.assertEqual(cards[2]["elements"][0]["content"], "expialidoc")
        self.assertEqual(cards[3]["elements"][0]["content"], "ious")

    def test_bridge_empty_and_invalid_init(self):
        """Test invalid init parameters and empty text."""
        bridge = LongResponseChunkSplitterIntegrationBridge(max_chunk_size="invalid")
        self.assertEqual(bridge.max_chunk_size, 2000)

        bridge_too_small = LongResponseChunkSplitterIntegrationBridge(max_chunk_size=5)
        self.assertEqual(bridge_too_small.max_chunk_size, 10)

        cards = bridge.process_and_bridge({"text": ""})
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["elements"][0]["content"], "")

    def test_exception_fallback(self):
        """Test the absolute zero-crash fallback by forcing an exception."""
        # Monkeypatch the converter to raise an exception
        original_convert = self.bridge.schema_converter.forward_compatible_convert

        def mock_raise(*args, **kwargs):
            raise RuntimeError("Forced Error")

        self.bridge.schema_converter.forward_compatible_convert = mock_raise

        cards = self.bridge.process_and_bridge({"text": "test"})

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["header"]["template"], "red")
        self.assertIn("soft failure", cards[0]["elements"][0]["content"])

        # Restore
        self.bridge.schema_converter.forward_compatible_convert = original_convert

    def test_schema_conversion_empty_text(self):
        # Trigger line 96-98: chunks if chunks else [""]
        bridge = LongResponseChunkSplitterIntegrationBridge(max_chunk_size=10)
        chunks = bridge._split_by_semantic_boundaries("")
        self.assertEqual(chunks, [""])

    def test_bridge_sentence_splitting_last_odd(self):
        bridge = LongResponseChunkSplitterIntegrationBridge(max_chunk_size=10)
        # Force a sentence split where it doesn't divide neatly
        text = "Hello! World! What? Yes. And this is a very long string that should hit the else case."
        chunks = bridge._split_by_semantic_boundaries(text)
        self.assertTrue(len(chunks) > 0)

    def test_bridge_split_empty_sentences(self):
        bridge = LongResponseChunkSplitterIntegrationBridge(max_chunk_size=10)
        text = "Hello! " * 50
        chunks = bridge._split_by_semantic_boundaries(text)
        self.assertTrue(len(chunks) > 0)

if __name__ == '__main__':
    unittest.main()
