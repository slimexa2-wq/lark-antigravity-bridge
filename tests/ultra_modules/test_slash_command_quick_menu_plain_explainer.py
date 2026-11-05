import unittest
import sys
import os

# Ensure the module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from ultra_modules.slash_command_quick_menu_plain_explainer import generate_explainer_card

class TestSlashCommandQuickMenuPlainExplainer(unittest.TestCase):
    def test_normal_data(self):
        """Test with normal, expected data for a specific command."""
        data = {
            "completed_tasks": ["A", "B", "C"],
            "pending_tasks": ["D"],
            "stats": {"efficiency": "high"}
        }
        result = generate_explainer_card("/周报", data)

        self.assertEqual(result["format"], "card")
        self.assertIn("✅ 已完成: 3 项任务", result["json"]["summary"])
        self.assertIn("⏳ 待办中: 1 项任务", result["json"]["summary"])
        self.assertIn("本周工作进度正常", result["json"]["summary"][2])
        self.assertEqual(result["json"]["details"]["completed"], ["A", "B", "C"])
        self.assertIn("<details>", result["html"])
        self.assertIn("```json", result["markdown"])

    def test_dirty_data_self_healing(self):
        """Test dirty data self-healing, such as invalid types passed into parameters."""
        data = {
            "amount": "not_a_number",
            "rate": [1, 2, 3],
            "total": "5000"
        }
        result = generate_explainer_card("/提成", data)

        self.assertEqual(result["json"]["details"]["base_amount"], 0.0)
        self.assertEqual(result["json"]["details"]["rate"], 0.0)
        self.assertEqual(result["json"]["details"]["calculated_total"], 5000.0)
        self.assertIn("预计提成: ¥5000.00", result["json"]["summary"][0])

    def test_missing_parameter_fallback(self):
        """Test fallback when raw_data is not provided, is None, or not a dict."""
        result = generate_explainer_card("/标书", None)

        self.assertEqual(result["json"]["details"]["project_name"], "未命名项目")
        self.assertEqual(result["json"]["details"]["status"], "未知")
        self.assertEqual(result["json"]["details"]["deadline"], "未设定")
        self.assertIn("未命名项目", result["json"]["summary"][0])
        self.assertIn("未知", result["json"]["summary"][1])

    def test_extreme_boundaries(self):
        """Test extreme boundary cases like very large numbers or empty/whitespace commands."""
        data = {
            "title": "Super Popular",
            "views": 10**10, # Very large number
        }
        result = generate_explainer_card("/漫剧", data)

        self.assertEqual(result["json"]["details"]["views"], 10**10)
        self.assertIn("爆款潜质", result["json"]["summary"][2])

        result_unknown = generate_explainer_card("   ", {"test": "data"})
        self.assertIn("未知指令", result_unknown["json"]["summary"][0])

    def test_calculation_edge_cases(self):
        """Test edge cases for calculations or specific conditional logic."""
        # Weekly report where pending > completed
        data = {
            "completed_tasks": ["A"],
            "pending_tasks": ["B", "C", "D"]
        }
        result = generate_explainer_card("/周报", data)
        self.assertIn("需加快进度", result["json"]["summary"][2])

        # Commission where amount and rate are strings of valid floats
        data2 = {
            "amount": "100.5",
            "rate": "0.1"
        }
        result2 = generate_explainer_card("/提成", data2)
        self.assertEqual(result2["json"]["details"]["base_amount"], 100.5)
        self.assertEqual(result2["json"]["details"]["rate"], 0.1)
        self.assertEqual(result2["json"]["details"]["calculated_total"], 10.05)

if __name__ == '__main__':
    unittest.main()
