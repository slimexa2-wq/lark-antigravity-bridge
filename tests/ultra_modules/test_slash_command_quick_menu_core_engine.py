import unittest
import sys
import os

# Ensure the project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from ultra_modules.slash_command_quick_menu_core_engine import route_slash_command, clean_input

class TestSlashCommandQuickMenuCoreEngine(unittest.TestCase):

    def test_clean_input(self):
        self.assertEqual(clean_input(None), "")
        self.assertEqual(clean_input(123), "123")
        self.assertEqual(clean_input("  \x00dirty\x1fdata  "), "dirtydata")
        self.assertEqual(clean_input("clean text"), "clean text")

    def test_route_slash_command_normal(self):
        res = route_slash_command("/周报", kwargs={"period": "last_week", "user": "alice"})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "generate_weekly_report")
        self.assertEqual(res["data"]["period"], "last_week")
        self.assertEqual(res["data"]["user"], "alice")

    def test_route_slash_command_default_params(self):
        res = route_slash_command("/提成")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "query_commission")
        self.assertEqual(res["data"]["month"], "current")

    def test_route_slash_command_dirty_data_cleaning(self):
        # Command with dirty characters and whitespace
        res = route_slash_command("  \x00/漫剧\x1f  ", kwargs={"workspace": "  \x00custom_ws\x1f  "})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "open_comic_drama_workspace")
        self.assertEqual(res["data"]["workspace"], "custom_ws")

    def test_route_slash_command_invalid_param_types(self):
        # Passes integer as command and kwargs values
        res = route_slash_command("/标书", kwargs={"type": 123})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "retrieve_bidding_document")
        self.assertEqual(res["data"]["type"], "123")

    def test_route_slash_command_positional_args(self):
        res = route_slash_command("/状态", args=["ignored_arg"], kwargs={"target": "db"})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "check_status")
        self.assertEqual(res["data"]["target"], "db")

    def test_route_slash_command_unrecognized(self):
        res = route_slash_command("/未知指令")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["message"], "Unrecognized or empty command.")

    def test_route_slash_command_none_args_kwargs(self):
        res = route_slash_command("/周报", args=None, kwargs=None)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "generate_weekly_report")
        self.assertEqual(res["data"]["period"], "this_week")
        self.assertEqual(res["data"]["user"], "self")

if __name__ == '__main__':
    unittest.main()
