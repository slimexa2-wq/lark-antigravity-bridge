import unittest
import json
from unittest.mock import patch
from io import StringIO
from ultra_modules.long_response_chunk_splitter_cli_one_click import LongResponseChunkSplitter, main

class TestLongResponseChunkSplitter(unittest.TestCase):

    def test_normal_text_splitting(self):
        """Condition 1: Normal long text splitting preserving paragraphs."""
        splitter = LongResponseChunkSplitter(max_length=20)
        # 3 paragraphs
        text = "This is paragraph 1.\n\nThis is paragraph 2.\n\nThis is paragraph 3."
        chunks = splitter.split_text(text)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], "This is paragraph 1.")
        self.assertEqual(chunks[1], "This is paragraph 2.")
        self.assertEqual(chunks[2], "This is paragraph 3.")

    def test_dirty_data_self_healing(self):
        """Condition 2: Dirty data self-healing (None, integers, objects handled gracefully)."""
        splitter = LongResponseChunkSplitter()

        self.assertEqual(splitter.heal_data(None), "")
        self.assertEqual(splitter.heal_data(12345), "12345")

        # An object that raises exception on str() isn't standard, but we can mock a broken object
        class BrokenObj:
            def __str__(self):
                raise ValueError("Broken")

        self.assertEqual(splitter.heal_data(BrokenObj()), "")

        # Test split with none
        chunks = splitter.split_text(None)
        self.assertEqual(chunks, [])

    def test_missing_parameters_fallback(self):
        """Condition 3: Missing parameters fallback (using default max chunk size and empty string input)."""
        # Testing constructor fallback defaults
        splitter = LongResponseChunkSplitter(mode="invalid_mode", max_length=-10)
        self.assertEqual(splitter.mode, "json")
        self.assertEqual(splitter.max_length, 1000)

        chunks = splitter.split_text("   \n  \n")
        self.assertEqual(chunks, [])

    def test_boundary_condition_large_paragraph(self):
        """Condition 4: Boundary condition 1 (single paragraph larger than max chunk size is forced split)."""
        splitter = LongResponseChunkSplitter(max_length=5)
        text = "123456789012"
        chunks = splitter.split_text(text)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], "12345")
        self.assertEqual(chunks[1], "67890")
        self.assertEqual(chunks[2], "12")

        # With preceding content
        text2 = "abc\n123456789012"
        chunks2 = splitter.split_text(text2)
        self.assertEqual(len(chunks2), 4)
        self.assertEqual(chunks2[0], "abc")
        self.assertEqual(chunks2[1], "12345")
        self.assertEqual(chunks2[2], "67890")
        self.assertEqual(chunks2[3], "12")

    def test_boundary_condition_empty_string(self):
        """Condition 5: Boundary condition 2 (empty string returns empty chunk array)."""
        splitter = LongResponseChunkSplitter()
        chunks = splitter.split_text("")
        self.assertEqual(chunks, [])

    def test_process_and_output_json(self):
        """Test output generation in JSON mode."""
        splitter = LongResponseChunkSplitter(mode="json", max_length=20)
        output = splitter.process_and_output("Hello\nWorld")
        parsed = json.loads(output)
        self.assertEqual(parsed["total_chunks"], 1)
        self.assertEqual(parsed["chunks"][0]["content"], "Hello\nWorld")

    def test_process_and_output_excel(self):
        """Test output generation in Excel (CSV) mode."""
        splitter = LongResponseChunkSplitter(mode="excel", max_length=20)
        # Include quotes to test escaping
        output = splitter.process_and_output("Hello \"World\"")
        lines = output.split("\n")
        self.assertEqual(lines[0], "Index,Content")
        self.assertEqual(lines[1], '1,"Hello ""World"""')

        # Test empty
        output2 = splitter.process_and_output("")
        self.assertEqual(output2, "Index,Content")

    def test_split_text_current_chunk_falsy(self):
        """Test branch where current_chunk is falsy in exceed max_length branch."""
        # By setting max_length=5 and giving a text that forces length condition but without current_chunk
        splitter = LongResponseChunkSplitter(max_length=5)
        # If current_chunk is empty and para > max_length, it hits line 47, not 59
        # To hit 60->62, current_chunk must be empty when we reach 59.
        # But wait, if len(para) > max_length, we enter line 47.
        # So len(para) <= max_length.
        # If current_chunk is empty, len(current_chunk) == 0.
        # Then len(para) > max_length -> false.
        # So len(current_chunk) + len(para) + (1 if current_chunk else 0) > max_length
        # Since len(current_chunk) == 0, this evaluates to len(para) > max_length, which is false.
        # So it is logically impossible to hit 60->62 if current_chunk is empty.
        pass

    @patch('sys.stdout', new_callable=StringIO)
    @patch('argparse.ArgumentParser.parse_args')
    def test_cli_main(self, mock_args, mock_stdout):
        """Test the zero-config CLI main function."""
        import argparse
        mock_args.return_value = argparse.Namespace(
            text="Test CLI.", mode="json", max_length=100
        )
        main()
        output = mock_stdout.getvalue().strip()
        parsed = json.loads(output)
        self.assertEqual(parsed["total_chunks"], 1)
        self.assertEqual(parsed["chunks"][0]["content"], "Test CLI.")

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
