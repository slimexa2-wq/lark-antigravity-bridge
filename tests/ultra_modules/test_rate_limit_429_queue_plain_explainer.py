import unittest
from ultra_modules.rate_limit_429_queue_plain_explainer import RateLimitExplainer

class TestRateLimitExplainer(unittest.TestCase):
    def test_normal_operation(self):
        result = RateLimitExplainer.explain(total_requests=100, success=100, queued=0, dropped=0, rate_limited_429=0)
        self.assertEqual(result["json"]["state"], "Normal")
        self.assertIn("All systems operational", result["plain_text"])
        self.assertIn("Successfully processed 100", result["plain_text"])
        self.assertEqual(result["json"]["metrics"]["success"], 100)

    def test_dirty_data_self_healing(self):
        result = RateLimitExplainer.explain(total_requests=-10, success=-5, queued=-2, dropped=-1, rate_limited_429=-100)
        self.assertEqual(result["json"]["state"], "Normal")
        self.assertEqual(result["json"]["metrics"]["total_requests"], 0)
        self.assertEqual(result["json"]["metrics"]["success"], 0)
        self.assertEqual(result["json"]["metrics"]["queued"], 0)
        self.assertEqual(result["json"]["metrics"]["dropped"], 0)
        self.assertEqual(result["json"]["metrics"]["rate_limited_429"], 0)

    def test_missing_parameters_defaults(self):
        result = RateLimitExplainer.explain(total_requests=None, success=None, queued=None, dropped=None, rate_limited_429=None)
        self.assertEqual(result["json"]["state"], "Normal")
        self.assertEqual(result["json"]["metrics"]["total_requests"], 0)
        self.assertEqual(result["json"]["metrics"]["success"], 0)

    def test_extreme_edge_cases_dropped(self):
        result = RateLimitExplainer.explain(total_requests=1000, success=0, queued=0, dropped=1000, rate_limited_429=1000)
        self.assertEqual(result["json"]["state"], "Critical - Dropping Messages")
        self.assertIn("CRITICAL: 1000 messages had to be dropped", result["plain_text"])
        self.assertIn("Encountered 1000 rate limit", result["plain_text"])

    def test_warning_queued(self):
        result = RateLimitExplainer.explain(total_requests=500, success=400, queued=100, dropped=0, rate_limited_429=50)
        self.assertEqual(result["json"]["state"], "Warning - Queuing Messages")
        self.assertIn("Encountered 50 rate limit", result["plain_text"])
        self.assertIn("100 messages are currently queued", result["plain_text"])
        self.assertIn("400 messages were successfully delivered", result["plain_text"])

if __name__ == '__main__':
    unittest.main()
