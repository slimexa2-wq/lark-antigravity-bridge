import unittest
import os
import json
import csv
from unittest.mock import patch, MagicMock
from ultra_modules.rate_limit_429_queue_cli_one_click import DualModeOutputAdapter, one_click_cli_entry

class TestRateLimit429QueueCLIOneClick(unittest.TestCase):
    def setUp(self):
        self.output_json = "test_output.json"
        self.output_csv = "test_output.csv"
        # Cleanup before tests
        if os.path.exists(self.output_json):
            os.remove(self.output_json)
        if os.path.exists(self.output_csv):
            os.remove(self.output_csv)

    def tearDown(self):
        # Cleanup after tests
        if os.path.exists(self.output_json):
            os.remove(self.output_json)
        if os.path.exists(self.output_csv):
            os.remove(self.output_csv)

    def test_normal_json_export(self):
        """Test case 1: Normal JSON export."""
        adapter = DualModeOutputAdapter(mode="json", output_path="test_output")
        data = [{"id": 1, "status": "ok"}]
        success = adapter.export(data)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.output_json))
        with open(self.output_json, "r") as f:
            loaded_data = json.load(f)
            self.assertEqual(loaded_data, data)

    def test_normal_csv_export(self):
        """Test case 2: Normal CSV export."""
        adapter = DualModeOutputAdapter(mode="csv", output_path="test_output")
        data = [{"id": 1, "status": "ok"}, {"id": 2, "status": "queued"}]
        success = adapter.export(data)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.output_csv))
        with open(self.output_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["id"], "1")
            self.assertEqual(rows[0]["status"], "ok")

    def test_dirty_data_self_healing(self):
        """Test case 3: Dirty data self-healing."""
        adapter = DualModeOutputAdapter(mode="json", output_path="test_output")
        # Mixing dicts, strings, None
        dirty_data = [{"id": 1}, "string_data", None, 123]
        success = adapter.export(dirty_data)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.output_json))
        with open(self.output_json, "r") as f:
            loaded_data = json.load(f)
            self.assertEqual(len(loaded_data), 3) # None should be skipped
            self.assertEqual(loaded_data[0], {"id": 1})
            self.assertEqual(loaded_data[1], {"data": "string_data"})
            self.assertEqual(loaded_data[2], {"data": "123"})

    def test_missing_parameter_default_fallbacks(self):
        """Test case 4: Missing parameter defaults fallback (zero config)."""
        # Testing one_click_cli_entry with completely empty parameters
        with patch('ultra_modules.rate_limit_429_queue_cli_one_click.DualModeOutputAdapter.export') as mock_export:
            mock_export.return_value = True
            success = one_click_cli_entry()
            self.assertTrue(success)
            mock_export.assert_called_once()
            args, _ = mock_export.call_args
            # Should have processed the default requests: {"id": 1, "req": "default_1"}, {"id": 2, "req": "default_2"}
            data = args[0]
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["status"], "processed")
            self.assertEqual(data[1]["status"], "processed_from_queue")

    def test_empty_boundary_conditions(self):
        """Test case 5: Empty arrays and extreme boundary condition silent handling."""
        # Empty array
        adapter = DualModeOutputAdapter(mode="csv", output_path="test_output")
        success = adapter.export([])
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.output_csv))
        with open(self.output_csv, "r") as f:
            content = f.read()
            self.assertEqual(content, "")

        # Unwritable output path fallback (simulate by providing an invalid path like a directory)
        adapter = DualModeOutputAdapter(mode="json", output_path="/invalid_dir_that_does_not_exist/test_output")
        # Should gracefully fail to write, print, and return True if fallback_mode is True
        with patch('builtins.print') as mock_print:
            success = adapter.export([{"data": 1}])
            self.assertTrue(success)
            mock_print.assert_called()

        # Should fail and return False if fallback_mode is False
        success = adapter.export([{"data": 1}], fallback_mode=False)
        self.assertFalse(success)

if __name__ == '__main__':
    unittest.main()
