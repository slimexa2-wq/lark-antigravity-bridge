import unittest
from ultra_modules.daily_ops_digest_pusher_audit_trace import AuditLogger, DigestPusher

class TestDailyOpsDigestPusher(unittest.TestCase):

    def setUp(self):
        self.pusher = DigestPusher()

    def test_normal_data_and_diff_highlight(self):
        """Test normal operational data, ensuring diff highlights work correctly."""
        data = {
            "fleet": {
                "active_agents": 45,
                "previous_active_agents": 40,
                "tasks_completed": 120
            },
            "recruitment": {
                "candidates_screened": 100,
                "interviews_scheduled": 20,
                "offers_sent": 5
            },
            "health": {
                "status": "Healthy",
                "uptime_hours": 240
            }
        }
        digest = self.pusher.generate_digest(data)

        self.assertIn("Active Agents: 45 (🟢 +5)", digest)
        self.assertIn("Tasks Completed: 120", digest)
        self.assertIn("Screened: 100", digest)
        self.assertIn("Interviews: 20", digest)
        self.assertIn("Offers: 5", digest)
        self.assertIn("Status: Healthy", digest)
        self.assertIn("Uptime: 240h", digest)

        logs = self.pusher.audit_logger.get_logs()
        self.assertEqual(len(logs), 0)

    def test_missing_parameters_fallback(self):
        """Test that missing parameters gracefully fallback to zero-config defaults."""
        data = {}
        digest = self.pusher.generate_digest(data)

        self.assertIn("Active Agents: 0 (⚪ 0)", digest)
        self.assertIn("Tasks Completed: 0", digest)
        self.assertIn("Screened: 0", digest)
        self.assertIn("Interviews: 0", digest)
        self.assertIn("Offers: 0", digest)
        self.assertIn("Status: Healthy", digest)
        self.assertIn("Uptime: 0h", digest)

    def test_dirty_data_self_healing(self):
        """Test dirty data sanitization (strings to int, invalid status, illogical numbers)."""
        data = {
            "fleet": {
                "active_agents": "30.5",  # Float in string
                "previous_active_agents": 35,
                "tasks_completed": None   # None type
            },
            "recruitment": {
                "candidates_screened": 10,
                "interviews_scheduled": 50, # More interviews than candidates
                "offers_sent": 60           # More offers than interviews
            },
            "health": {
                "status": "Crashed",        # Invalid status
                "uptime_hours": -50         # Negative number
            }
        }
        digest = self.pusher.generate_digest(data)

        self.assertIn("Active Agents: 30 (🔴 -5)", digest)
        self.assertIn("Tasks Completed: 0", digest)
        self.assertIn("Screened: 10", digest)
        self.assertIn("Interviews: 10", digest)
        self.assertIn("Offers: 10", digest)
        self.assertIn("Status: Degraded", digest)
        self.assertIn("Uptime: 0h", digest)

        logs = self.pusher.audit_logger.get_logs()
        actions = [log["action"] for log in logs]
        self.assertIn("sanitize_metric_type", actions)
        self.assertIn("heal_recruitment_interviews", actions)
        self.assertIn("heal_recruitment_offers", actions)
        self.assertIn("heal_system_status", actions)
        self.assertIn("sanitize_metric_negative", actions)

    def test_extreme_boundaries(self):
        """Test extreme boundary values such as massive numbers and cross-year values."""
        data = {
            "health": {
                "uptime_hours": 999999999999  # Exceeds 1 year
            }
        }
        digest = self.pusher.generate_digest(data)

        self.assertIn("Uptime: 8760h", digest) # Capped at 1 year

        logs = self.pusher.audit_logger.get_logs()
        actions = [log["action"] for log in logs]
        self.assertIn("heal_system_uptime_boundary", actions)

    def test_invalid_types_for_dicts(self):
        """Test completely wrong root structure types."""
        # This will trigger the exception block in _sanitize_metric
        # and test the `else` branch (not None, str, int, float)

        data = {
            "fleet": {
                "active_agents": {"bad": "type"},
                "previous_active_agents": "a string that cannot be cast to float",
                "tasks_completed": []
            }
        }
        self.pusher.generate_digest(data)

        digest = self.pusher.generate_digest("Not a dict")

        self.assertIn("Active Agents: 0 (⚪ 0)", digest)

        logs = self.pusher.audit_logger.get_logs()
        actions = [log["action"] for log in logs]
        self.assertIn("heal_raw_data_type", actions)

        self.pusher = DigestPusher() # Reset
        digest = self.pusher.generate_digest({
            "fleet": ["List", "instead", "of", "dict"],
            "recruitment": 123,
            "health": "bad_string"
        })

        logs = self.pusher.audit_logger.get_logs()
        actions = [log["action"] for log in logs]
        self.assertIn("heal_fleet_data_type", actions)
        self.assertIn("heal_recruitment_data_type", actions)
        self.assertIn("heal_health_data_type", actions)

if __name__ == '__main__':
    unittest.main()
