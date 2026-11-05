import unittest
import time
from ultra_modules.collapsible_thinking_card_self_healing_guard import (
    CollapsibleThinkingCardSelfHealingGuard,
    clean_string
)

class TestCollapsibleThinkingCardSelfHealingGuard(unittest.TestCase):
    def setUp(self):
        self.guard = CollapsibleThinkingCardSelfHealingGuard()

    def test_clean_string(self):
        # 100% branch coverage for clean_string
        self.assertEqual(clean_string(None), "")
        self.assertEqual(clean_string("  hello  "), "hello")
        self.assertEqual(clean_string(["a", "b"]), "['a', 'b']")
        self.assertEqual(clean_string({"k": "v"}), "{'k': 'v'}")

        class Unstringable:
            def __str__(self):
                raise Exception("no string representation")

        self.assertEqual(clean_string(Unstringable()), "")

    def test_normal_build(self):
        card = self.guard.build_card(
            conclusion="Everything is fine.",
            thinking_process="I thought about it.",
            title="Results",
            card_link="https://example.com"
        )
        self.assertEqual(card["header"]["title"]["content"], "Results")
        self.assertTrue(card["elements"][0]["content"].endswith("Everything is fine."))
        self.assertEqual(card["elements"][1]["elements"][0]["content"], "I thought about it.")
        self.assertEqual(card["card_link"]["url"], "https://example.com")
        self.assertEqual(card["elements"][2]["tag"], "action")

    def test_dirty_data_healing(self):
        card = self.guard.build_card(
            conclusion=["dirty", "data"],
            thinking_process={"complex": "object"},
            title=123,
            card_link=None,
            show_undo=False
        )
        self.assertEqual(card["header"]["title"]["content"], "123")
        self.assertTrue(card["elements"][0]["content"].endswith("['dirty', 'data']"))
        self.assertEqual(card["elements"][1]["elements"][0]["content"], "{'complex': 'object'}")
        self.assertNotIn("card_link", card)
        # Ensure no undo button is appended when show_undo=False
        self.assertEqual(len(card["elements"]), 2)

    def test_missing_parameters_fallback(self):
        card = self.guard.build_card()
        self.assertEqual(card["header"]["title"]["content"], "智能推理结果")
        self.assertTrue(card["elements"][0]["content"].endswith("暂无结论"))
        self.assertEqual(card["elements"][1]["elements"][0]["content"], "暂无推理过程")
        self.assertNotIn("card_link", card)

    def test_snapshot_and_undo_success(self):
        card = self.guard.build_card(
            conclusion="Undo me",
            show_undo=True
        )
        undo_action = card["elements"][2]["actions"][0]["value"]
        self.assertEqual(undo_action["action"], "undo")
        snapshot_id = undo_action["snapshot_id"]

        # Check snapshot existence
        self.assertIn(snapshot_id, self.guard._snapshots)

        # Undo successful
        snapshot = self.guard.undo(snapshot_id)
        self.assertIsNotNone(snapshot)
        self.assertTrue(snapshot["elements"][0]["content"].endswith("Undo me"))

        # Snapshot should be removed after successful undo
        self.assertNotIn(snapshot_id, self.guard._snapshots)

    def test_undo_expired_window_and_invalid_id(self):
        card = self.guard.build_card(show_undo=True)
        snapshot_id = card["elements"][2]["actions"][0]["value"]["snapshot_id"]

        # Test invalid ID
        self.assertIsNone(self.guard.undo("invalid_id"))

        # Fast forward time to test expiration (>5 seconds)
        snapshot, timestamp = self.guard._snapshots[snapshot_id]
        future_time = timestamp + 6.0

        expired_snapshot = self.guard.undo(snapshot_id, current_time=future_time)
        self.assertIsNone(expired_snapshot)
        # Expired snapshot should be cleaned up
        self.assertNotIn(snapshot_id, self.guard._snapshots)

if __name__ == '__main__':
    unittest.main()
