import unittest
import math
from ultra_modules.slash_command_quick_menu_export_formatter import (
    sanitize_export_data,
    generate_report_text,
    format_quick_menu_export
)

class TestSlashCommandQuickMenuExportFormatter(unittest.TestCase):
    def test_normal_export_weekly_report(self):
        data = {"user": "Alice", "tasks_completed": 5}
        result = format_quick_menu_export("/周报", data)
        self.assertEqual(result["command"], "/周报")
        self.assertEqual(result["sanitized_data"]["comments"], 0)
        self.assertEqual(result["sanitized_data"]["user"], "Alice")

        lines = result["report_text"].split("\n")
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], "【本周工作汇报】")
        self.assertIn("user:Alice", lines[1])
        self.assertIn("tasks_completed:5", lines[1])
        self.assertEqual(lines[2], "已处理批注数量：0，随时可复制流转。")

    def test_dirty_data_nan_none_fallback(self):
        dirty_data = {
            "value1": None,
            "value2": float('nan'),
            "nested_list": [None, float('nan'), "valid"],
            "nested_dict": {"inner": None},
            "comments": float('nan')
        }
        result = format_quick_menu_export("/提成", dirty_data)
        safe = result["sanitized_data"]

        self.assertEqual(safe["value1"], "")
        self.assertEqual(safe["value2"], 0)
        self.assertEqual(safe["nested_list"], ["", 0, "valid"])
        self.assertEqual(safe["nested_dict"], {"inner": "", "comments": 0})
        self.assertEqual(safe["comments"], 0)

        lines = result["report_text"].split("\n")
        self.assertEqual(lines[0], "【提成核算简报】")

    def test_missing_parameter_default_values(self):
        # Missing data parameter
        result = format_quick_menu_export("/漫剧")
        self.assertEqual(result["sanitized_data"], {"comments": 0})

        lines = result["report_text"].split("\n")
        self.assertEqual(lines[0], "【漫剧项目进度】")
        self.assertEqual(lines[1], "数据概览：暂无详细数据")

        # Completely missing parameters
        result2 = format_quick_menu_export()
        self.assertEqual(result2["command"], "")
        self.assertEqual(result2["sanitized_data"], {"comments": 0})
        lines2 = result2["report_text"].split("\n")
        self.assertEqual(lines2[0], "【快捷导出简报】")

        # Test command as None
        result3 = format_quick_menu_export(None)
        self.assertEqual(result3["command"], "")
        lines3 = result3["report_text"].split("\n")
        self.assertEqual(lines3[0], "【快捷导出简报】")

        # Test command not string
        result4 = format_quick_menu_export(123)
        self.assertEqual(result4["command"], "")

    def test_extreme_boundary_unrecognized_command(self):
        data = {"field1": "test"}
        # Test unrecognized command
        result = format_quick_menu_export("/未知指令", data)
        lines = result["report_text"].split("\n")
        self.assertEqual(lines[0], "【快捷导出简报】")

        # Test other known commands
        commands = {
            "/标书": "【标书制作状态】",
            "/状态": "【当前状态同步】"
        }
        for cmd, title in commands.items():
            res = format_quick_menu_export(cmd, {})
            self.assertEqual(res["report_text"].split("\n")[0], title)

    def test_extreme_boundary_malformed_data(self):
        # Feeding a list instead of a dict
        result1 = format_quick_menu_export("/状态", ["should", "be", "dict"])
        self.assertEqual(result1["sanitized_data"], {"comments": 0})

        # Feeding a string
        result2 = format_quick_menu_export("/状态", "invalid_string_data")
        self.assertEqual(result2["sanitized_data"], {"comments": 0})

        # Test sanitizing standalone values not inside dict
        self.assertEqual(sanitize_export_data(None), "")
        self.assertEqual(sanitize_export_data(float('nan')), 0)
        self.assertEqual(sanitize_export_data("normal"), "normal")

        # Test dict with missing comments, and None comments
        self.assertEqual(sanitize_export_data({"a": 1})["comments"], 0)
        self.assertEqual(sanitize_export_data({"comments": None})["comments"], 0)

if __name__ == '__main__':
    unittest.main() # pragma: no cover
