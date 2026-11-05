import unittest
import time
from ultra_modules.daily_ops_digest_pusher_self_healing_guard import DailyOpsDigestPusherSelfHealingGuard

class TestDailyOpsDigestPusherSelfHealingGuard(unittest.TestCase):
    def setUp(self):
        self.guard = DailyOpsDigestPusherSelfHealingGuard()

    def test_normal_execution(self):
        """Test normal data execution."""
        data = {
            "jules_fleet_progress": 85,
            "recruitment_rate": 90,
            "system_health": "All Green"
        }
        res = self.guard.push_digest(data, "push_1")
        self.assertTrue(res["success"])

        card = res["card"]
        summary = card["data"]["template_variable"]["summary_text"]
        self.assertIn("Jules舰队进度: 85%", summary)
        self.assertIn("招聘达成: 90%", summary)
        self.assertIn("系统健康度: All Green", summary)

    def test_dirty_data_self_healing(self):
        """Test dirty data self-healing and boundary fixing."""
        data = {
            "jules_fleet_progress": "  110% ", # over 100
            "recruitment_rate": -5,          # below 0
            "system_health": None
        }
        res = self.guard.push_digest(data, "push_2")
        self.assertTrue(res["success"])

        card = res["card"]
        summary = card["data"]["template_variable"]["summary_text"]
        self.assertIn("Jules舰队进度: 100%", summary)
        self.assertIn("招聘达成: 0%", summary)
        self.assertIn("系统健康度: Healthy", summary)

    def test_missing_params_default_fallback(self):
        """Test missing parameters default fallbacks."""
        res = self.guard.push_digest({}, "push_3")
        self.assertTrue(res["success"])

        card = res["card"]
        summary = card["data"]["template_variable"]["summary_text"]
        self.assertIn("Jules舰队进度: 0%", summary)
        self.assertIn("招聘达成: 0%", summary)
        self.assertIn("系统健康度: Healthy", summary)

        # Test completely wrong type (e.g. list instead of dict)
        res_list = self.guard.push_digest(["wrong type"], "push_4")
        self.assertTrue(res_list["success"])
        summary_list = res_list["card"]["data"]["template_variable"]["summary_text"]
        self.assertIn("Jules舰队进度: 0%", summary_list)

    def test_extreme_boundary_conditions(self):
        """Test extreme boundary conditions (e.g. invalid string)."""
        data = {
            "jules_fleet_progress": "invalid string",
            "recruitment_rate": "1e50", # valid float parsing but bounded
            "system_health": 12345
        }
        res = self.guard.push_digest(data, "push_5")
        self.assertTrue(res["success"])

        card = res["card"]
        summary = card["data"]["template_variable"]["summary_text"]
        self.assertIn("Jules舰队进度: 0%", summary)
        self.assertIn("招聘达成: 100%", summary)
        # 12345 is not a valid health string, so it falls back to default
        self.assertIn("系统健康度: Healthy", summary)

    def test_undo_mechanism(self):
        """Test the 5-second undo time window."""
        res = self.guard.push_digest({"system_health": "OK"}, "push_undo")
        self.assertTrue(res["success"])

        # Undo within window
        undo_res = self.guard.undo_push("push_undo")
        self.assertTrue(undo_res["success"])
        self.assertEqual(undo_res["message"], "Undo successful")

        # Undo already undone
        undo_res_2 = self.guard.undo_push("push_undo")
        self.assertTrue(undo_res_2["success"])
        self.assertEqual(undo_res_2["message"], "Already undone")

        # Test expiration by modifying the snapshot timestamp directly
        self.guard.push_digest({"system_health": "OK"}, "push_undo_expired")
        self.guard.snapshots["push_undo_expired"]["timestamp"] -= 6

        undo_res_expired = self.guard.undo_push("push_undo_expired")
        self.assertFalse(undo_res_expired["success"])
        self.assertEqual(undo_res_expired["message"], "Undo window expired")

if __name__ == '__main__':
    unittest.main()
