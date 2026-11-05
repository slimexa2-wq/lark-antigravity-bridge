import unittest
import time
from unittest.mock import patch
from ultra_modules.multi_bot_mention_dispatcher_self_healing_guard import MultiBotDispatcherGuard

class TestMultiBotDispatcherGuard(unittest.TestCase):
    def setUp(self):
        self.guard = MultiBotDispatcherGuard(snapshot_ttl=5.0)

    def test_normal_flow_dispatch(self):
        """Test normal dispatch flow resulting in a card with an undo button."""
        msg = "@大肥鱼 请分析市场 @招聘 查一下HC"
        bot_results = {
            "大肥鱼": "市场分析完成。",
            "招聘": {"summary": "HC有空缺", "details": "还有3个岗位"}
        }
        card = self.guard.dispatch(msg, bot_results)

        self.assertEqual(card["header"]["title"]["content"], "多Bot协同执行结果汇总")
        # Check elements count: bot1 + hr + bot2 + note + hr + undo action
        self.assertTrue(len(card["elements"]) >= 2)

        # Verify undo button exists and snapshot_id is valid
        last_element = card["elements"][-1]
        self.assertEqual(last_element["tag"], "action")
        self.assertEqual(last_element["actions"][0]["value"]["action"], "undo")
        self.assertIn("snapshot_id", last_element["actions"][0]["value"])

    def test_dirty_data_handling(self):
        """Test that invalid types for message and bot_results are handled silently."""
        msg = {"dirty": "dict"} # Invalid type for message
        bot_results = 12345 # Invalid type for results

        card = self.guard.dispatch(msg, bot_results)

        self.assertEqual(card["header"]["title"]["content"], "多Bot协同执行结果汇总")
        self.assertEqual(card["elements"][0]["content"], "未识别到任何有效指令。 / No valid commands recognized.")

        last_element = card["elements"][-1]
        self.assertEqual(last_element["tag"], "action")
        self.assertEqual(last_element["actions"][0]["value"]["action"], "undo")

        snapshot_id = last_element["actions"][0]["value"]["snapshot_id"]
        result = self.guard.handle_undo(snapshot_id)
        self.assertEqual(result["status"], "success")

    def test_missing_parameter_fallbacks(self):
        """Test missing parameters such as None for message or results."""
        card = self.guard.dispatch(None, None)

        self.assertEqual(card["header"]["title"]["content"], "多Bot协同执行结果汇总")
        self.assertEqual(card["elements"][0]["content"], "未识别到任何有效指令。 / No valid commands recognized.")

        last_element = card["elements"][-1]
        snapshot_id = last_element["actions"][0]["value"]["snapshot_id"]

        # Ensure undo works even when the snapshot contained None
        result = self.guard.handle_undo(snapshot_id)
        self.assertEqual(result["status"], "success")

    def test_successful_undo_within_5_seconds(self):
        """Test that undoing a snapshot within the 5 second TTL is successful."""
        msg = "@数据 导出报表"
        bot_results = {"数据": "已导出"}

        card = self.guard.dispatch(msg, bot_results)
        snapshot_id = card["elements"][-1]["actions"][0]["value"]["snapshot_id"]

        result = self.guard.handle_undo(snapshot_id)
        self.assertEqual(result["status"], "success")
        self.assertIsNotNone(result["recovered_data"])

        # A second undo on the same id should fail gracefully
        result2 = self.guard.handle_undo(snapshot_id)
        self.assertEqual(result2["status"], "failed")

    @patch('time.time')
    def test_undo_failure_after_5_seconds(self, mock_time):
        """Test that undoing a snapshot after the 5 second TTL expires fails gracefully."""
        # Initial time for snapshot creation
        mock_time.return_value = 100.0

        msg = "@量化 跑一下模型"
        bot_results = {"量化": "模型运行中"}

        card = self.guard.dispatch(msg, bot_results)
        snapshot_id = card["elements"][-1]["actions"][0]["value"]["snapshot_id"]

        # Fast-forward 6 seconds (TTL is 5.0)
        mock_time.return_value = 106.0

        result = self.guard.handle_undo(snapshot_id)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["recovered_data"], None)

if __name__ == '__main__':
    unittest.main()
