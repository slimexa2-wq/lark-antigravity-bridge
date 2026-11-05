import unittest
import time
from ultra_modules.slash_command_quick_menu_self_healing_guard import SlashCommandQuickMenuSelfHealingGuard

class TestSlashCommandQuickMenuSelfHealingGuard(unittest.TestCase):
    def setUp(self):
        self.guard = SlashCommandQuickMenuSelfHealingGuard()

    def test_normal_condition(self):
        """Test case 1: Normal condition for commands"""
        result = self.guard.route_command(session_id="user_123", command="周报", week="next", format="detailed")
        self.assertTrue(result["success"])
        self.assertEqual(result["session_id"], "user_123")
        self.assertEqual(result["command"], "/周报")
        self.assertEqual(result["params"]["week"], "next")
        self.assertEqual(result["params"]["format"], "detailed")

        result2 = self.guard.route_command(session_id="user_123", command="提成", month="last", currency="USD")
        self.assertEqual(result2["command"], "/提成")
        self.assertEqual(result2["params"]["month"], "last")
        self.assertEqual(result2["params"]["currency"], "USD")

    def test_dirty_data_self_healing(self):
        """Test case 2: Dirty data self-healing"""
        # Bad session id
        result = self.guard.route_command(session_id=None, command="  / 周 报!! ")
        self.assertEqual(result["session_id"], "default_session")
        self.assertEqual(result["command"], "/周报")

        # Int session id and dirty alias
        result2 = self.guard.route_command(session_id=123, command="Ticheng!!!@@  ")
        self.assertEqual(result2["session_id"], "123")
        self.assertEqual(result2["command"], "/提成")

        # Random garbage string
        result3 = self.guard.route_command(session_id="", command="!@#$!@#")
        self.assertEqual(result3["command"], "/状态") # Fallback to 状态

        # None command
        result4 = self.guard.route_command(session_id=None, command=None)
        self.assertEqual(result4["command"], "/状态")

    def test_missing_parameter_fallback(self):
        """Test case 3: Missing parameter fallback"""
        result = self.guard.route_command(session_id="u1", command="漫剧")
        self.assertEqual(result["command"], "/漫剧")
        self.assertEqual(result["params"]["episode"], "latest")

        result2 = self.guard.route_command(session_id="u2", command="标书")
        self.assertEqual(result2["command"], "/标书")
        self.assertEqual(result2["params"]["type"], "standard")
        self.assertEqual(result2["params"]["status"], "draft")

        result3 = self.guard.route_command(session_id="u3", command="状态")
        self.assertEqual(result3["command"], "/状态")
        self.assertEqual(result3["params"]["user"], "self")
        self.assertEqual(result3["params"]["visibility"], "public")

        result4 = self.guard.route_command(session_id="u4", command="周报")
        self.assertEqual(result4["command"], "/周报")
        self.assertEqual(result4["params"]["week"], "current")
        self.assertEqual(result4["params"]["format"], "summary")

        result5 = self.guard.route_command(session_id="u5", command="提成")
        self.assertEqual(result5["command"], "/提成")
        self.assertEqual(result5["params"]["month"], "current")
        self.assertEqual(result5["params"]["currency"], "CNY")

    def test_extreme_boundary_conditions(self):
        """Test case 4: Extreme boundary conditions"""
        # Complex param dictionary healing
        # Passing kwargs with None keys (not directly possible via kwargs, but simulates bad input if passed indirectly)
        # We will directly call _heal_params to test dict keys
        bad_params = {
            123: "value",
            None: "value2",
            "  ": "spaces",
            "valid_key": "data"
        }
        healed_params = self.guard._heal_params("标书", bad_params)
        self.assertIn("valid_key", healed_params)
        self.assertNotIn(123, healed_params)
        self.assertNotIn(None, healed_params)
        self.assertNotIn("  ", healed_params)
        self.assertEqual(healed_params["type"], "standard")
        self.assertEqual(healed_params["status"], "draft")

        # If params is not a dict
        healed_params2 = self.guard._heal_params("漫剧", "not a dict")
        self.assertEqual(healed_params2, {"episode": "latest"})

        # Another command healing branch coverage
        healed_params3 = self.guard._heal_params("some_other_cmd", {})
        self.assertEqual(healed_params3, {})

        # Undo when there's no snapshot
        undo_res = self.guard.undo(session_id="new_user")
        self.assertTrue(undo_res["success"])
        self.assertEqual(undo_res["action"], "undo_skipped")
        self.assertEqual(undo_res["reason"], "no_snapshot")
        self.assertIsNone(undo_res["command"])

    def test_snapshot_expiration_and_undo(self):
        """Test case 5: Snapshot expiration and undo functionality"""
        sid = "undo_user"
        # Initial command
        self.guard.route_command(session_id=sid, command="周报")

        # Second command
        self.guard.route_command(session_id=sid, command="提成")
        self.assertEqual(self.guard._state[sid]["command"], "提成")

        # Undo immediately
        undo_res = self.guard.undo(session_id=sid)
        self.assertEqual(undo_res["action"], "undone")
        self.assertEqual(undo_res["command"], "/周报")
        self.assertEqual(self.guard._state[sid]["command"], "周报")

        # Try undo again (should be skipped because snapshot was consumed)
        undo_res2 = self.guard.undo(session_id=sid)
        self.assertEqual(undo_res2["action"], "undo_skipped")
        self.assertEqual(undo_res2["reason"], "no_snapshot")
        self.assertEqual(undo_res2["command"], "/周报")

        # Test expiration
        self.guard.undo_window_seconds = 0.1 # Shrink window for test
        self.guard.route_command(session_id=sid, command="漫剧")
        time.sleep(0.2)
        undo_res3 = self.guard.undo(session_id=sid)
        self.assertEqual(undo_res3["action"], "undo_skipped")
        self.assertEqual(undo_res3["reason"], "expired")
        self.assertEqual(undo_res3["command"], "/漫剧") # Still at 漫剧

if __name__ == '__main__':
    unittest.main()
