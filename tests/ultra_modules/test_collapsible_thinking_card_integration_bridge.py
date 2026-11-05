import unittest
import json
from ultra_modules.collapsible_thinking_card_integration_bridge import CardIntegrationBridge

class TestCardIntegrationBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = CardIntegrationBridge()

    def test_normal_flow_with_explicit_params(self):
        """Test 1: Normal execution with explicit conclusion and reasoning provided."""
        conclusion = "The final answer is 42."
        reasoning = "1. Think\n2. Calculate\n3. Result is 42."

        card = self.bridge.build_card(conclusion=conclusion, reasoning=reasoning)

        self.assertEqual(card["header"]["title"]["content"], "Reasoning Result")
        self.assertIn("**Conclusion:**\nThe final answer is 42.", card["elements"][0]["text"]["content"])
        self.assertIn("**Reasoning (Folded):**\n1. Think\n2. Calculate\n3. Result is 42.", card["elements"][2]["text"]["content"])
        self.assertEqual(card["elements"][3]["actions"][0]["value"]["action"], "undo_snapshot")

    def test_default_fallbacks_for_missing_parameters(self):
        """Test 2: Default fallbacks when no arguments are provided."""
        card = self.bridge.build_card()

        self.assertIn(self.bridge.default_conclusion, card["elements"][0]["text"]["content"])
        self.assertIn(self.bridge.default_reasoning, card["elements"][2]["text"]["content"])

    def test_dirty_data_self_healing(self):
        """Test 3: Dirty data self-healing and schema mapping."""
        # Raw data with a nested, differently named schema (e.g., v2 mapping to v1)
        raw_data = {
            "metadata": {"version": 2},
            "payload": {
                "final_thought": " Mapped conclusion with spaces. ",
                "details": {"step1": "thinking", "step2": "done"}
            }
        }

        card = self.bridge.build_card(raw_data=raw_data)

        # Conclusion should map from final_thought and be stripped
        self.assertIn("Mapped conclusion with spaces.", card["elements"][0]["text"]["content"])

        # Reasoning should map from details and be JSON dumped since it's a dict
        reasoning_str = json.dumps({"step1": "thinking", "step2": "done"}, ensure_ascii=False)
        self.assertIn(reasoning_str, card["elements"][2]["text"]["content"])

    def test_extreme_boundary_conditions_truncation(self):
        """Test 4: Extreme boundary conditions (preventing mobile screen flooding)."""
        long_conclusion = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"

        card = self.bridge.build_card(conclusion=long_conclusion)

        conclusion_content = card["elements"][0]["text"]["content"]

        # Should be truncated to 3 lines
        self.assertIn("Line 1\nLine 2\nLine 3\n... (truncated)", conclusion_content)
        self.assertNotIn("Line 4", conclusion_content)

    def test_one_click_undo_snapshot(self):
        """Test 5: One-click undo snapshot payload generation."""
        snapshot = self.bridge.build_undo_snapshot()
        self.assertEqual(snapshot["action"], "undo_snapshot")
        self.assertEqual(snapshot["status"], "success")

        # Test disabling undo button
        card = self.bridge.build_card(enable_undo=False)
        self.assertEqual(len(card["elements"]), 3) # No undo button element

if __name__ == '__main__':
    unittest.main()
