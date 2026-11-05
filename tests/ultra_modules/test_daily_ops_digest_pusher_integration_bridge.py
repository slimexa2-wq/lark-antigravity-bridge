import unittest
from ultra_modules.daily_ops_digest_pusher_integration_bridge import push_daily_digest

class TestDailyOpsDigestPusherIntegrationBridge(unittest.TestCase):

    def test_normal_v2_data(self):
        """Test with typical, expected v2 data format."""
        data = {
            "progress": {
                "status": "On Track"
            },
            "recruitment": {
                "hired": 5,
                "target": 10
            },
            "health": {
                "score": 98.5
            }
        }
        result = push_daily_digest(data)

        markdown_content = result["elements"][0]["content"]
        self.assertIn("Jules Fleet Progress: On Track", markdown_content)
        self.assertIn("Recruitment: 5/10 target achieved", markdown_content)
        self.assertIn("System Health: 98.5%", markdown_content)

    def test_dirty_data_self_healing(self):
        """Test with dirty data types that should be silently healed by the bridge and core engine."""
        data = {
            "progress": {
                "status": 123
            },
            "recruitment": {
                "hired": "3",
                "target": "5.5"
            },
            "health": {
                "score": "95.5"
            }
        }
        result = push_daily_digest(data)

        markdown_content = result["elements"][0]["content"]
        self.assertIn("Jules Fleet Progress: 123", markdown_content)
        self.assertIn("Recruitment: 3/3 target achieved", markdown_content)
        self.assertIn("System Health: 95.5%", markdown_content)

    def test_missing_parameters_fallback(self):
        """Test with missing parameters and empty input to test fallback defaults."""
        for data in [{}, None, "not a dict", []]:
            result = push_daily_digest(data)
            markdown_content = result["elements"][0]["content"]
            self.assertIn("Jules Fleet Progress: Unknown", markdown_content)
            self.assertIn("Recruitment: 0/0 target achieved", markdown_content)
            self.assertIn("System Health: 100.0%", markdown_content)

    def test_extreme_boundary_conditions(self):
        """Test with extreme boundary conditions like blank strings and negative out-of-bounds numbers."""
        data = {
            "progress": {
                "status": "   "
            },
            "recruitment": {
                "hired": -5,
                "target": -10
            },
            "health": {
                "score": 150.0
            }
        }
        result = push_daily_digest(data)

        markdown_content = result["elements"][0]["content"]
        self.assertIn("Jules Fleet Progress: Unknown", markdown_content)
        self.assertIn("Recruitment: 0/0 target achieved", markdown_content)
        self.assertIn("System Health: 100.0%", markdown_content)

    def test_legacy_schema_mapping(self):
        """Test that the bridge correctly maps legacy v1 schema to the new v2 schema."""
        legacy_data = {
            "old_progress": "Legacy Status",
            "old_recruitment_hired": 2,
            "old_recruitment_target": 8,
            "old_health": 85.5
        }
        result = push_daily_digest(legacy_data)

        markdown_content = result["elements"][0]["content"]
        self.assertIn("Jules Fleet Progress: Legacy Status", markdown_content)
        self.assertIn("Recruitment: 2/8 target achieved", markdown_content)
        self.assertIn("System Health: 85.5%", markdown_content)

    def test_legacy_schema_mapping_branches(self):
        """Test to cover specific branches in legacy mapping."""
        # 29->31: recruitment already exists
        data1 = {
            "old_recruitment_hired": 5,
            "recruitment": {}
        }
        push_daily_digest(data1)

        # 31->33: hired already exists in recruitment, but target doesn't
        data2 = {
            "old_recruitment_target": 5,
            "recruitment": {"hired": 5}
        }
        push_daily_digest(data2)

        # 33->37: target already exists in recruitment
        data3 = {
            "old_recruitment_target": 5,
            "recruitment": {"target": 10}
        }
        push_daily_digest(data3)

if __name__ == '__main__':
    unittest.main() # pragma: no cover
