import unittest
import json
from unittest.mock import patch
from ultra_modules.event_lru_idempotency_guard_plain_explainer import (
    IdempotencyExplainer,
    explain_event_idempotency,
    get_pool_summary,
    _global_explainer
)

class TestEventLRUIdempotencyGuardPlainExplainer(unittest.TestCase):
    def setUp(self):
        # Reset the global explainer for tests that might use it
        _global_explainer._pool.clear()
        _global_explainer.max_size = 1000

    def test_normal_new_event_processing(self):
        """测试正常的新事件处理"""
        explainer = IdempotencyExplainer(max_size=10)
        res = explainer.process_event("evt_123", "msg_abc")
        self.assertEqual(res["event_id"], "evt_123")
        self.assertEqual(res["status"], "新事件")
        self.assertEqual(res["action"], "允许处理")

        cards = explainer.generate_cards(res)
        self.assertIn("evt_123", cards["markdown"])
        self.assertIn("新事件", cards["html"])
        self.assertIn("允许处理", cards["json"])

    def test_duplicate_event_interception(self):
        """测试重复事件拦截"""
        explainer = IdempotencyExplainer(max_size=10)
        explainer.process_event("evt_dup", "msg_dup")

        # Process again
        res = explainer.process_event("evt_dup", "msg_dup")
        self.assertEqual(res["event_id"], "evt_dup")
        self.assertEqual(res["status"], "重复事件")
        self.assertEqual(res["action"], "拦截阻断")

        cards = explainer.generate_cards(res)
        self.assertIn("拦截阻断", cards["markdown"])
        self.assertIn("重复事件", cards["html"])

    @patch('ultra_modules.event_lru_idempotency_guard_plain_explainer.datetime')
    def test_dirty_data_self_healing(self, mock_datetime):
        """测试脏数据自愈和缺参默认兜底"""
        class MockDatetime:
            @classmethod
            def now(cls):
                class NowProxy:
                    def timestamp(self):
                        return 1600000000.0
                    def isoformat(self):
                        return "2020-09-13T12:26:40"
                return NowProxy()

        mock_datetime.now = MockDatetime.now

        explainer = IdempotencyExplainer(max_size=10)

        # Test None event_id but has message_id
        res1 = explainer.process_event(None, "msg_xyz")
        self.assertEqual(res1["event_id"], "fallback_evt_msg_xyz")
        self.assertEqual(res1["status"], "新事件")

        # Test empty event_id and empty message_id
        res2 = explainer.process_event("", None)
        self.assertEqual(res2["event_id"], "unknown_evt_1600000000.0")
        self.assertEqual(res2["status"], "新事件")

        # Test spaces only
        res3 = explainer.process_event("   ", "   ")
        self.assertEqual(res3["event_id"], "unknown_evt_1600000000.0")
        self.assertEqual(res3["status"], "重复事件") # Same fallback id generated at the same timestamp

    def test_extreme_boundary_lru_capacity(self):
        """测试极端边界：LRU容量限制和淘汰机制"""
        explainer = IdempotencyExplainer(max_size=3)

        explainer.process_event("evt_1")
        explainer.process_event("evt_2")
        explainer.process_event("evt_3")

        summary = explainer.get_summary()
        self.assertEqual(summary["pool_size"], 3)
        self.assertEqual(summary["latest_events"], ["evt_1", "evt_2", "evt_3"])

        # Add 4th, should evict evt_1
        explainer.process_event("evt_4")
        summary2 = explainer.get_summary()
        self.assertEqual(summary2["pool_size"], 3)
        self.assertEqual(summary2["latest_events"], ["evt_2", "evt_3", "evt_4"])

        # evt_1 should now be processed as a new event
        res = explainer.process_event("evt_1")
        self.assertEqual(res["status"], "新事件")

    def test_zero_config_global_functions(self):
        """测试全局零配置函数入口"""
        card1 = explain_event_idempotency("global_evt_1", "global_msg_1")
        self.assertEqual(card1["raw_result"]["status"], "新事件")

        card2 = explain_event_idempotency("global_evt_1", "global_msg_1")
        self.assertEqual(card2["raw_result"]["status"], "重复事件")

        summary = get_pool_summary()
        self.assertIn("global_evt_1", summary["latest_events"])
        self.assertGreaterEqual(summary["pool_size"], 1)

if __name__ == '__main__':
    unittest.main()
