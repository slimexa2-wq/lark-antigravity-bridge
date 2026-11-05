import unittest
import json
from unittest.mock import patch
from ultra_modules.daily_ops_digest_pusher_cli_one_click import DailyOpsDigestPusher, cli_entry, clean_data

class TestDailyOpsDigestPusherCliOneClick(unittest.TestCase):

    def test_clean_data(self):
        # Normal
        self.assertEqual(clean_data(10, 5), 10)
        # Dirty
        self.assertEqual(clean_data(None, 5), 5)
        self.assertEqual(clean_data("", "default"), "default")
        self.assertEqual(clean_data("   ", "default"), "default")
        self.assertEqual(clean_data(-5, 10), 10)

    def test_cli_entry_default_no_params(self):
        """Test the one-click zero-parameter entry point directly."""
        output = cli_entry()
        data = json.loads(output)

        self.assertIn("timestamp", data)

        # Verify defaults
        self.assertEqual(data["fleet_progress"]["completed_tasks"], 0)
        self.assertEqual(data["fleet_progress"]["ongoing_tasks"], 0)
        self.assertEqual(data["fleet_progress"]["efficiency_rate"], 0.85)

        self.assertEqual(data["recruitment_status"]["interviews_conducted"], 0)
        self.assertEqual(data["recruitment_status"]["offers_extended"], 0)

        self.assertEqual(data["system_health"]["uptime_percentage"], 99.9)
        self.assertEqual(data["system_health"]["active_incidents"], 0)

    def test_cli_entry_excel_mode(self):
        """Test tabular output."""
        output = cli_entry(mode="excel")
        self.assertTrue(output.startswith("Section,Metric,Value"))
        self.assertIn("FleetProgress,completed_tasks,0", output)
        self.assertIn("SystemHealth,uptime_percentage,99.9", output)

    def test_dirty_data_self_healing(self):
        """Test with dirty input data, expecting sensible defaults."""
        fleet_data = {"completed_tasks": -10, "ongoing_tasks": None, "efficiency_rate": ""}
        recruitment_data = {"interviews_conducted": "  ", "offers_extended": -1}
        health_data = {"uptime_percentage": 200, "active_incidents": -5} # extreme uptime

        output = cli_entry(mode="json", fleet_data=fleet_data, recruitment_data=recruitment_data, health_data=health_data)
        data = json.loads(output)

        self.assertEqual(data["fleet_progress"]["completed_tasks"], 0)
        self.assertEqual(data["fleet_progress"]["ongoing_tasks"], 0)
        self.assertEqual(data["fleet_progress"]["efficiency_rate"], 0.85)

        self.assertEqual(data["recruitment_status"]["interviews_conducted"], 0)
        self.assertEqual(data["recruitment_status"]["offers_extended"], 0)

        # Uptime is bounded between 0 and 100
        self.assertEqual(data["system_health"]["uptime_percentage"], 100.0)
        self.assertEqual(data["system_health"]["active_incidents"], 0)

    def test_extreme_boundaries(self):
        """Test with valid extreme data boundaries."""
        fleet_data = {"completed_tasks": 9999999, "ongoing_tasks": 0, "efficiency_rate": 1.0}
        health_data = {"uptime_percentage": -100, "active_incidents": 999} # negative uptime triggers clean_data to fallback to 99.9

        output = cli_entry(mode="json", fleet_data=fleet_data, health_data=health_data)
        data = json.loads(output)

        self.assertEqual(data["fleet_progress"]["completed_tasks"], 9999999)
        self.assertEqual(data["system_health"]["uptime_percentage"], 99.9)
        self.assertEqual(data["system_health"]["active_incidents"], 999)

    @patch('ultra_modules.daily_ops_digest_pusher_cli_one_click.DailyOpsDigestPusher.fetch_system_health')
    def test_exception_handling(self, mock_fetch):
        """Test graceful fallback when an internal exception occurs."""
        mock_fetch.side_effect = Exception("Simulated crash")

        output = cli_entry()
        data = json.loads(output)

        self.assertIn("error", data)
        self.assertEqual(data["error"], "Failed to generate digest")
        self.assertIn("Simulated crash", data["details"])

if __name__ == "__main__":
    unittest.main()
