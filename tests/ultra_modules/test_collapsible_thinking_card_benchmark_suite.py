import unittest
import uuid
import datetime

from ultra_modules.collapsible_thinking_card_benchmark_suite import (
    CollapsibleThinkingCardBuilder,
    SyntheticFixtures,
    BenchmarkSuite
)

class TestCollapsibleThinkingCardBenchmarkSuite(unittest.TestCase):
    def test_normal_input(self):
        """Test with standard string inputs."""
        card = CollapsibleThinkingCardBuilder.build(
            conclusion="Tests passed",
            reasoning_process="Analyzed the logs.",
            undo_action_id="undo_123"
        )

        conclusion_content = card["elements"][0]["text"]["content"]
        self.assertIn("Tests passed", conclusion_content)

        reasoning_content = card["elements"][3]["columns"][0]["elements"][0]["content"]
        self.assertEqual(reasoning_content, "Analyzed the logs.")

        undo_action = card["elements"][4]["actions"][0]["value"]["action_id"]
        self.assertEqual(undo_action, "undo_123")

    def test_empty_values_fallback(self):
        """Test that missing parameters receive sensible defaults."""
        fixture = SyntheticFixtures.generate_empty_values()
        card = CollapsibleThinkingCardBuilder.build(**fixture)

        conclusion_content = card["elements"][0]["text"]["content"]
        self.assertIn("Success", conclusion_content)

        reasoning_content = card["elements"][3]["columns"][0]["elements"][0]["content"]
        self.assertEqual(reasoning_content, "Process completed smoothly.")

        undo_action = card["elements"][4]["actions"][0]["value"]["action_id"]
        self.assertTrue(undo_action.startswith("undo_"))

        # Test empty string specifically
        card2 = CollapsibleThinkingCardBuilder.build(
            conclusion="   ",
            reasoning_process="   ",
            undo_action_id="   "
        )
        self.assertIn("Success", card2["elements"][0]["text"]["content"])
        self.assertEqual(card2["elements"][3]["columns"][0]["elements"][0]["content"], "Process completed smoothly.")
        self.assertTrue(card2["elements"][4]["actions"][0]["value"]["action_id"].startswith("undo_"))

    def test_garbage_data_healing(self):
        """Test dirty data is silently cleaned/handled without crashing."""
        fixture = SyntheticFixtures.generate_garbage_data()
        card = CollapsibleThinkingCardBuilder.build(**fixture)

        conclusion_content = card["elements"][0]["text"]["content"]
        self.assertIn("Success", conclusion_content)

        reasoning_content = card["elements"][3]["columns"][0]["elements"][0]["content"]
        self.assertTrue("Process completed smoothly." in reasoning_content or len(reasoning_content) > 0)

        undo_action = card["elements"][4]["actions"][0]["value"]["action_id"]
        self.assertTrue(undo_action.startswith("undo_"))

    def test_list_reasoning_process(self):
        """Test reasoning process when given as a list."""
        class Unstringable:
            def __str__(self):
                raise ValueError("cannot convert to string")

        card = CollapsibleThinkingCardBuilder.build(
            reasoning_process=["Step 1", None, Unstringable(), "Step 2", "   "]
        )
        reasoning_content = card["elements"][3]["columns"][0]["elements"][0]["content"]

        # The list stringification skips None and unstringable elements.
        # It should contain "Step 1" and "Step 2". Note: empty strings won't be stripped out of list initially,
        # but the joined result will be stripped at the end.
        self.assertIn("Step 1", reasoning_content)
        self.assertIn("Step 2", reasoning_content)
        self.assertNotIn("ValueError", reasoning_content)

        # Test completely empty list or a list that yields nothing
        card_empty_list = CollapsibleThinkingCardBuilder.build(
            reasoning_process=[None, Unstringable()]
        )
        self.assertEqual(card_empty_list["elements"][3]["columns"][0]["elements"][0]["content"], "Process completed smoothly.")

    def test_extreme_boundaries(self):
        """Test massive input and cross year boundary fixtures."""
        massive_fixture = SyntheticFixtures.generate_massive_input()
        card = CollapsibleThinkingCardBuilder.build(**massive_fixture)

        conclusion_content = card["elements"][0]["text"]["content"]
        self.assertIn("A" * 100000, conclusion_content)

        cross_year_fixture = SyntheticFixtures.generate_cross_year_boundary()
        card2 = CollapsibleThinkingCardBuilder.build(**cross_year_fixture)
        self.assertIn("2024", card2["elements"][0]["text"]["content"])
        self.assertIn("2023", card2["elements"][0]["text"]["content"])

    def test_benchmark_suite(self):
        """Test zero-crash and reasonable execution times under load."""
        result = BenchmarkSuite.run_benchmark(iterations=100)
        self.assertTrue(result["success"])
        self.assertFalse(result["crashed"])
        self.assertTrue(result["elapsed_ms"] >= 0)
        # Even with massive inputs, 100 iterations should easily take under 5000ms
        self.assertLess(result["elapsed_ms"], 5000)

if __name__ == '__main__':
    unittest.main()
