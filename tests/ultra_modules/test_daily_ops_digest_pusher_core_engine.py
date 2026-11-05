import unittest
from ultra_modules.daily_ops_digest_pusher_core_engine import generate_daily_digest

class TestDailyOpsDigestPusherCoreEngine(unittest.TestCase):

    def test_normal_data(self):
        """Test with typical, expected data."""
        data = {
            "progress": {
                "status": "On Track",
                "details": "All modules are progressing as planned."
            },
            "recruitment": {
                "hired": 5,
                "target": 10,
                "details": "Hired 5 engineers this week."
            },
            "health": {
                "score": 98.5,
                "details": "Minor latency spikes handled."
            }
        }
        result = generate_daily_digest(data)

        # Check core summary
        markdown_content = result["elements"][0]["content"]
        self.assertIn("Jules Fleet Progress: On Track", markdown_content)
        self.assertIn("Recruitment: 5/10 target achieved", markdown_content)
        self.assertIn("System Health: 98.5%", markdown_content)

        # Check max 3 lines
        self.assertLessEqual(len(markdown_content.split('\n')), 3)

        # Check details in collapsible panel
        panel_content = result["elements"][1]["elements"][0]["content"]
        self.assertIn("All modules are progressing as planned.", panel_content)
        self.assertIn("Hired 5 engineers this week.", panel_content)
        self.assertIn("Minor latency spikes handled.", panel_content)

    def test_dirty_data_self_healing(self):
        """Test with dirty data types that should be silently healed."""
        data = {
            "progress": {
                "status": 123,  # Should become "123"
                "details": ["not", "a", "string"]  # Should become string representation
            },
            "recruitment": {
                "hired": "3",  # String instead of int
                "target": "5.5",  # Float string instead of int
                "details": None  # Should become "None" string representation or handle gracefully
            },
            "health": {
                "score": "95.5",  # String instead of float
                "details": 456
            }
        }
        result = generate_daily_digest(data)

        markdown_content = result["elements"][0]["content"]
        self.assertIn("Jules Fleet Progress: 123", markdown_content)
        # int("5.5") raises ValueError, handled by default 0, then target < hired (0 < 3) makes it 3/3
        self.assertIn("Recruitment: 3/3 target achieved", markdown_content)
        self.assertIn("System Health: 95.5%", markdown_content)

        panel_content = result["elements"][1]["elements"][0]["content"]
        self.assertIn("['not', 'a', 'string']", panel_content)
        self.assertIn("None", panel_content)
        self.assertIn("456", panel_content)

    def test_missing_parameters_fallback(self):
        """Test with missing parameters and empty input to test defaults."""
        result_empty_dict = generate_daily_digest({})
        result_none = generate_daily_digest(None)
        result_wrong_type = generate_daily_digest("not a dict")

        for result in [result_empty_dict, result_none, result_wrong_type]:
            markdown_content = result["elements"][0]["content"]
            self.assertIn("Jules Fleet Progress: Unknown", markdown_content)
            self.assertIn("Recruitment: 0/0 target achieved", markdown_content)
            self.assertIn("System Health: 100.0%", markdown_content)

            panel_content = result["elements"][1]["elements"][0]["content"]
            self.assertIn("No details provided.", panel_content)
            self.assertIn("System running normally.", panel_content)

    def test_extreme_boundary_conditions(self):
        """Test with extreme boundary conditions like long strings and out-of-bounds numbers."""
        long_string = "A" * 5000
        data = {
            "progress": {
                "status": "   ",  # Blank spaces, should fallback to Unknown
                "details": long_string
            },
            "recruitment": {
                "hired": -5,  # Negative hired, should fallback to 0
                "target": -10, # Negative target, should fallback to 0
                "details": long_string
            },
            "health": {
                "score": 150.0, # > 100, should fallback to 100
                "details": long_string
            }
        }
        result = generate_daily_digest(data)

        markdown_content = result["elements"][0]["content"]
        self.assertIn("Jules Fleet Progress: Unknown", markdown_content)
        self.assertIn("Recruitment: 0/0 target achieved", markdown_content)
        self.assertIn("System Health: 100.0%", markdown_content)

        panel_content = result["elements"][1]["elements"][0]["content"]
        # Details should be truncated to 997 chars + "..."
        expected_truncated = "A" * 997 + "..."
        self.assertEqual(panel_content.count(expected_truncated), 3)
        self.assertEqual(len(expected_truncated), 1000)

    def test_health_score_negative_boundary(self):
        """Test health score specifically for negative values."""
        data = {
            "health": {
                "score": -10.5
            }
        }
        result = generate_daily_digest(data)
        markdown_content = result["elements"][0]["content"]
        self.assertIn("System Health: 100.0%", markdown_content)

if __name__ == '__main__':
    unittest.main()
