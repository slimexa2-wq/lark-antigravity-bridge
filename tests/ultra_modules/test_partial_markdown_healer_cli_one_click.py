import unittest
import json
from unittest.mock import patch, MagicMock
import sys
import io
import importlib
import builtins

from ultra_modules.partial_markdown_healer_cli_one_click import MarkdownHealerOneClick, DualModeAdapter, main
import ultra_modules.partial_markdown_healer_cli_one_click as module_to_test

class TestPartialMarkdownHealer(unittest.TestCase):
    def test_normal_execution(self):
        """Test normal healing execution on truncated code blocks and tables."""
        text = "Here is some code:\n```python\nprint('hello')\nAnd a table:\n| Header1 | Header2 |\n|---|---|\n| Data1 | Data2"
        healed = MarkdownHealerOneClick.heal(text)
        self.assertIn("```", healed)
        self.assertEqual(healed.count("```"), 2)
        self.assertTrue(healed.endswith("Data2|") or healed.endswith("```"))

        # Test CLI main function outputs valid JSON for normal execution
        test_args = ["prog", "--text", text]
        with patch.object(sys, 'argv', test_args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                main()
                output = fake_out.getvalue().strip()
                result = json.loads(output)
                self.assertEqual(result["status"], "success")

    def test_dirty_data_self_healing(self):
        """Test self-healing on dirty data (carriage returns, truncated json)."""
        dirty_text = "Some text\r\n{\"key\": \"value\", \"arr\": [1, 2"
        healed = MarkdownHealerOneClick.heal(dirty_text)
        self.assertNotIn("\r\n", healed)
        self.assertTrue(healed.endswith("]}"))
        self.assertEqual(healed.count("{"), healed.count("}"))
        self.assertEqual(healed.count("["), healed.count("]"))

        # Also test with trailing newline to code blocks to cover branch
        text_with_newline_code = "```\nsome code\n"
        healed_newline_code = MarkdownHealerOneClick.heal(text_with_newline_code)
        self.assertEqual(healed_newline_code.count("```"), 2)

    def test_missing_parameter_default(self):
        """Test that missing text parameter falls back to a sensible default."""
        healed = MarkdownHealerOneClick.heal()
        self.assertEqual(healed, "Default **fallback**")

        test_args = ["prog"]
        with patch.object(sys, 'argv', test_args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                main()
                output = fake_out.getvalue().strip()
                result = json.loads(output)
                self.assertEqual(result["status"], "success")
                self.assertEqual(result["data"], "Default **fallback**")

    def test_extreme_boundary_empty(self):
        """Test extreme boundary condition with empty string or empty lines for tables."""
        healed_empty = MarkdownHealerOneClick.heal("")
        self.assertEqual(healed_empty, "")

        healed_newlines = MarkdownHealerOneClick.heal("\n\n")
        self.assertEqual(healed_newlines, "\n\n")

        # Test missing tables block branch - text.split('\n') returns empty
        # Python's split() returns [''] for empty string, but we test it with heal("") which already hit it.
        # Let's mock _heal_tables explicitly for empty array just in case
        healed_spaces = MarkdownHealerOneClick.heal("   \n   ")

        # Test a line ending with | to cover the branch: not last_line.endswith('|')
        healed_pipe = MarkdownHealerOneClick.heal("| A | B |")
        self.assertTrue(healed_pipe.endswith("|"))

        # Test a line starting with | but NOT ending with |
        healed_unclosed_table = MarkdownHealerOneClick.heal("| A | B")
        self.assertTrue(healed_unclosed_table.endswith("|"))

    def test_json_excel_mode_adapter(self):
        """Test dual mode adapter fallbacks and excel/json modes."""
        text = "Hello **world"
        healed = MarkdownHealerOneClick.heal(text)

        # Test JSON mode
        json_out = DualModeAdapter.output(healed, "json")
        parsed = json.loads(json_out)
        self.assertEqual(parsed["data"], "Hello **world**")

        # Test Excel mode mock
        mock_pd = MagicMock()
        mock_df_instance = MagicMock()
        mock_pd.DataFrame.return_value = mock_df_instance

        with patch('ultra_modules.partial_markdown_healer_cli_one_click.PANDAS_AVAILABLE', True), \
             patch('ultra_modules.partial_markdown_healer_cli_one_click.pd', mock_pd, create=True):

            # Succeeds
            excel_out = DualModeAdapter.output(healed, "excel")
            self.assertTrue("Excel output ready" in excel_out)
            mock_df_instance.to_excel.assert_called_once()

            # Mock to raise exception to fallback to JSON
            mock_df_instance.to_excel.side_effect = Exception("Mock exception")
            fallback_out = DualModeAdapter.output(healed, "excel")
            parsed_fallback = json.loads(fallback_out)
            self.assertEqual(parsed_fallback["data"], "Hello **world**")

        # Test when pandas is not available
        with patch('ultra_modules.partial_markdown_healer_cli_one_click.PANDAS_AVAILABLE', False):
            fallback_out_no_pd = DualModeAdapter.output(healed, "excel")
            parsed_no_pd = json.loads(fallback_out_no_pd)
            self.assertEqual(parsed_no_pd["data"], "Hello **world**")

    def test_pandas_import(self):
        original_import = builtins.__import__
        def mocked_import(name, *args, **kwargs):
            if name == 'pandas':
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mocked_import):
            importlib.reload(module_to_test)
            self.assertFalse(module_to_test.PANDAS_AVAILABLE)

        # Re-reload without mock to cover PANDAS_AVAILABLE = True
        # Since pandas is NOT installed in this container, it will still raise ImportError in the reload.
        # We need to explicitly patch it so pandas is loaded successfully to hit line 10
        import sys
        sys.modules['pandas'] = MagicMock()
        importlib.reload(module_to_test)
        self.assertTrue(module_to_test.PANDAS_AVAILABLE)
        del sys.modules['pandas']
        importlib.reload(module_to_test)

    def test_main_name(self):
        # Trigger the if __name__ == "__main__" block via mocking the run or simply test run main as a script
        import subprocess
        result = subprocess.run([sys.executable, "ultra_modules/partial_markdown_healer_cli_one_click.py"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        parsed = json.loads(result.stdout)
        self.assertEqual(parsed["status"], "success")

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
