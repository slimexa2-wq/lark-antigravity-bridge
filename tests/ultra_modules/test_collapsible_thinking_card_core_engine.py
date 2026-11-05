import unittest
from ultra_modules.collapsible_thinking_card_core_engine import build_collapsible_thinking_card, clean_string

class FaultyObject:
    def __str__(self):
        raise ValueError("Cannot stringify this object")

class TestCollapsibleThinkingCardCoreEngine(unittest.TestCase):
    def test_normal_usage(self):
        """Test normal usage with all parameters provided correctly."""
        card = build_collapsible_thinking_card(
            conclusion="The answer is 42.",
            thinking_process="We multiply 6 by 7.",
            title="Math Result",
            card_link="https://example.com/math",
            show_undo=True
        )

        self.assertEqual(card["header"]["title"]["content"], "Math Result")
        self.assertIn("**结论：**\nThe answer is 42.", card["elements"][0]["content"])
        self.assertEqual(card["elements"][1]["elements"][0]["content"], "We multiply 6 by 7.")
        self.assertEqual(card["elements"][1]["default_expanded"], False)
        self.assertEqual(card["elements"][2]["tag"], "action")
        self.assertEqual(card["card_link"]["url"], "https://example.com/math")

    def test_missing_parameters_defaults(self):
        """Test with missing parameters to check for defaults."""
        card = build_collapsible_thinking_card()

        self.assertEqual(card["header"]["title"]["content"], "智能推理结果")
        self.assertIn("**结论：**\n暂无结论", card["elements"][0]["content"])
        self.assertEqual(card["elements"][1]["elements"][0]["content"], "暂无推理过程")
        self.assertEqual(card["elements"][1]["default_expanded"], False)
        self.assertEqual(card["elements"][2]["tag"], "action")
        self.assertNotIn("card_link", card)

    def test_dirty_data_self_healing(self):
        """Test with dirty data like integers, None, and empty strings."""
        card = build_collapsible_thinking_card(
            conclusion=12345,
            thinking_process=None,
            title="   ",
            card_link="  https://example.com  "
        )

        self.assertEqual(card["header"]["title"]["content"], "智能推理结果") # "   " is stripped to empty, falling back to default
        self.assertIn("**结论：**\n12345", card["elements"][0]["content"]) # Integer is stringified
        self.assertEqual(card["elements"][1]["elements"][0]["content"], "暂无推理过程") # None falls back to default
        self.assertEqual(card["card_link"]["url"], "https://example.com") # Link is stripped

    def test_extreme_edge_cases(self):
        """Test with an object that fails to stringify."""
        faulty = FaultyObject()
        card = build_collapsible_thinking_card(
            conclusion=faulty,
            thinking_process=faulty,
            title=faulty
        )

        self.assertEqual(card["header"]["title"]["content"], "智能推理结果")
        self.assertIn("**结论：**\n暂无结论", card["elements"][0]["content"])
        self.assertEqual(card["elements"][1]["elements"][0]["content"], "暂无推理过程")

    def test_collapsible_and_undo_behavior(self):
        """Test the disable of undo and the collapsible panel flag."""
        card = build_collapsible_thinking_card(
            show_undo=False
        )

        self.assertEqual(card["elements"][1]["tag"], "collapsible_panel")
        self.assertEqual(card["elements"][1]["default_expanded"], False)

        # Verify no undo button (action)
        for element in card["elements"]:
            self.assertNotEqual(element["tag"], "action")

    def test_clean_string(self):
        """Test the clean_string helper directly"""
        self.assertEqual(clean_string("  hello  "), "hello")
        self.assertEqual(clean_string(None), "")
        self.assertEqual(clean_string(123), "123")
        self.assertEqual(clean_string(FaultyObject()), "")

if __name__ == '__main__':
    unittest.main()
