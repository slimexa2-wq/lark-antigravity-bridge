import unittest
import math
from ultra_modules.slash_command_quick_menu_export_formatter import process_slash_command, sanitize_value

class TestSlashCommandQuickMenuExportFormatter(unittest.TestCase):

    def test_normal_commands(self):
        # /周报
        result = process_slash_command("/周报", {"完成任务数": 5, "待办任务数": 2, "风险项": 0})
        self.assertEqual(result["export_data"], {"完成任务数": 5, "待办任务数": 2, "风险项": 0, "comments": 0})
        self.assertEqual(result["report_text"], "【周报汇报】\n完成任务数: 5\n待办任务数: 2")

        # /提成
        result = process_slash_command("/提成", {"销售额": 1000.5, "提成比例": 0.1, "预计发放": 100.05})
        self.assertEqual(result["export_data"], {"销售额": 1000.5, "提成比例": 0.1, "预计发放": 100.05, "comments": 0})
        self.assertEqual(result["report_text"], "【提成汇报】\n销售额: 1000.5\n提成比例: 0.1")

        # /漫剧
        result = process_slash_command("/漫剧", {"新增集数": 10, "总播放量": 100000, "完播率": 0.85})
        self.assertEqual(result["export_data"], {"新增集数": 10, "总播放量": 100000, "完播率": 0.85, "comments": 0})
        self.assertEqual(result["report_text"], "【漫剧汇报】\n新增集数: 10\n总播放量: 100000")

        # /标书
        result = process_slash_command("/标书", {"完成页数": 50, "审核进度": 0.5, "距离截标(天)": 3})
        self.assertEqual(result["export_data"], {"完成页数": 50, "审核进度": 0.5, "距离截标(天)": 3, "comments": 0})
        self.assertEqual(result["report_text"], "【标书汇报】\n完成页数: 50\n审核进度: 0.5")

        # /状态
        result = process_slash_command("/状态", {"今日工时": 8, "有效产出": 6, "疲劳度": 0.3})
        self.assertEqual(result["export_data"], {"今日工时": 8, "有效产出": 6, "疲劳度": 0.3, "comments": 0})
        self.assertEqual(result["report_text"], "【状态汇报】\n今日工时: 8\n有效产出: 6")

    def test_default_fallback_missing_command(self):
        # Missing or unknown command should fallback to "/状态"
        result = process_slash_command("/未知指令", {"今日工时": 1, "有效产出": 2, "疲劳度": 3})
        self.assertEqual(result["export_data"], {"今日工时": 1, "有效产出": 2, "疲劳度": 3, "comments": 0})
        self.assertEqual(result["report_text"], "【状态汇报】\n今日工时: 1\n有效产出: 2")

    def test_dirty_data_self_healing(self):
        # Test None, NaN, missing data, invalid strings, and lists
        # Add list test to cover `return 0` fallback at the end of `sanitize_value`
        list_data = {
            "今日工时": [],
            "有效产出": [1, 2],
            "疲劳度": {}
        }
        result_list = process_slash_command("/状态", list_data)
        self.assertEqual(result_list["export_data"], {"今日工时": 0, "有效产出": 0, "疲劳度": 0, "comments": 0})

        # Test None, NaN, missing data, and invalid strings
        dirty_data = {
            "今日工时": None,
            "有效产出": math.nan,
            "疲劳度": "invalid_string"
        }
        result = process_slash_command("/状态", dirty_data)
        self.assertEqual(result["export_data"], {"今日工时": 0, "有效产出": 0, "疲劳度": 0, "comments": 0})
        self.assertEqual(result["report_text"], "【状态汇报】\n今日工时: 0\n有效产出: 0")

        dirty_data2 = {
            "今日工时": "NaN",
            "有效产出": "None",
            "疲劳度": ""
        }
        result2 = process_slash_command("/状态", dirty_data2)
        self.assertEqual(result2["export_data"], {"今日工时": 0, "有效产出": 0, "疲劳度": 0, "comments": 0})

        dirty_data3 = {
            "今日工时": " 12.5 ",
            "有效产出": 5
        }
        result3 = process_slash_command("/状态", dirty_data3)
        self.assertEqual(result3["export_data"]["今日工时"], 12.5)

    def test_extreme_boundary_conditions(self):
        # Empty dict
        result = process_slash_command("/周报", {})
        self.assertEqual(result["export_data"], {"完成任务数": 0, "待办任务数": 0, "风险项": 0, "comments": 0})

        # None as raw_data
        result2 = process_slash_command("/提成", None)
        self.assertEqual(result2["export_data"], {"销售额": 0, "提成比例": 0, "预计发放": 0, "comments": 0})

        # Invalid type as raw_data
        result3 = process_slash_command("/漫剧", "unexpected_type")
        self.assertEqual(result3["export_data"], {"新增集数": 0, "总播放量": 0, "完播率": 0, "comments": 0})

    def test_comments_always_zero(self):
        # Even if comments is provided in raw_data, it should be 0 in export_data
        result = process_slash_command("/标书", {"完成页数": 1, "审核进度": 2, "距离截标(天)": 3, "comments": 999})
        self.assertEqual(result["export_data"]["comments"], 0)

if __name__ == '__main__':
    unittest.main() # pragma: no cover
