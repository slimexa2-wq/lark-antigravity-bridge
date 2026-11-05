import unittest
import json
from ultra_modules.slash_command_quick_menu_integration_bridge import SlashCommandQuickMenuRouter

class TestSlashCommandQuickMenuRouter(unittest.TestCase):

    def test_normal_execution_new_schema(self):
        """Test normal execution with new schema ('data' field)"""
        req = {
            "command": "/周报",
            "data": {"week": "42"}
        }
        res = SlashCommandQuickMenuRouter.process_request(req)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "weekly_report")
        self.assertEqual(res["data"]["week"], "42")
        self.assertEqual(res["original_command"], "/周报")

    def test_normal_execution_old_schema_dict(self):
        """Test normal execution with old schema ('payload' field as dict)"""
        req = {
            "command": "/提成",
            "payload": {"month": "10"}
        }
        res = SlashCommandQuickMenuRouter.process_request(req)
        self.assertEqual(res["action"], "commission")
        self.assertEqual(res["data"]["month"], "10")

    def test_normal_execution_old_schema_string(self):
        """Test normal execution with old schema ('payload' field as string)"""
        req = {
            "command": "漫剧", # missing slash, should auto-fix
            "payload": '{"id": "123"}'
        }
        res = SlashCommandQuickMenuRouter.process_request(req)
        self.assertEqual(res["action"], "comic_drama")
        self.assertEqual(res["data"]["id"], "123")
        self.assertEqual(res["original_command"], "/漫剧")

    def test_dirty_data_self_healing(self):
        """Test dirty data self-healing"""
        # Invalid payload string
        req1 = {
            "command": "/标书 with args",
            "payload": "invalid json{"
        }
        res1 = SlashCommandQuickMenuRouter.process_request(req1)
        self.assertEqual(res1["action"], "bidding_document")
        self.assertEqual(res1["data"]["args"], "with args")

        # Not a dict input
        res2 = SlashCommandQuickMenuRouter.process_request(None)
        self.assertEqual(res2["action"], "status")

        res3 = SlashCommandQuickMenuRouter.process_request(["list"])
        self.assertEqual(res3["action"], "status")

    def test_missing_parameter_fallback(self):
        """Test missing parameter fallback (auto default to /状态)"""
        # Empty command
        req1 = {"command": ""}
        res1 = SlashCommandQuickMenuRouter.process_request(req1)
        self.assertEqual(res1["action"], "status")

        # Missing command key
        req2 = {}
        res2 = SlashCommandQuickMenuRouter.process_request(req2)
        self.assertEqual(res2["action"], "status")

        # Unknown command
        req3 = {"command": "/未知指令"}
        res3 = SlashCommandQuickMenuRouter.process_request(req3)
        self.assertEqual(res3["action"], "status")

    def test_extreme_boundary_conditions(self):
        """Test extreme boundary conditions"""
        # extremely long command and args
        long_cmd = "/周报 " + "A" * 10000
        req = {"command": long_cmd}
        res = SlashCommandQuickMenuRouter.process_request(req)
        self.assertEqual(res["action"], "weekly_report")
        self.assertEqual(res["data"]["args"], "A" * 10000)

        # None values inside valid dict
        req2 = {"command": None, "data": None, "payload": None}
        res2 = SlashCommandQuickMenuRouter.process_request(req2)
        self.assertEqual(res2["action"], "status")

if __name__ == '__main__':
    unittest.main() # pragma: no cover
