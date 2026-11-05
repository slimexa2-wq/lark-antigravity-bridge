import unittest
import math
from ultra_modules.collapsible_thinking_card_export_formatter import build_card_and_report

class TestCollapsibleThinkingCardExportFormatter(unittest.TestCase):

    def test_normal_execution(self):
        result = build_card_and_report(
            conclusion="The system is stable.",
            reasoning="All tests passed successfully.",
            metrics={"cpu": 45.2, "mem": 1024}
        )
        self.assertEqual(result["comments"], 0)
        self.assertEqual(result["metrics"]["cpu"], 45.2)
        self.assertEqual(result["metrics"]["mem"], 1024)

        report_lines = result["report"].split('\n')
        self.assertEqual(len(report_lines), 3)
        self.assertTrue(report_lines[0].startswith("Conclusion: The system is stable."))
        self.assertTrue(report_lines[1].startswith("Reasoning: All tests passed successfully."))
        self.assertTrue(report_lines[2].startswith("Metrics: cpu: 45.2, mem: 1024"))

        # Verify card structure
        card = result["card"]
        self.assertEqual(card["schema"], "2.0")
        elements = card["body"]["elements"]
        self.assertEqual(elements[0]["tag"], "markdown")
        self.assertEqual(elements[2]["tag"], "collapsible_panel")
        self.assertEqual(elements[3]["tag"], "action")

    def test_dirty_data_self_healing(self):
        result = build_card_and_report(
            conclusion="Results mixed.",
            reasoning="Some values missing.",
            metrics={"valid": 10, "missing": None, "nan_val": float('nan')}
        )

        self.assertEqual(result["metrics"]["valid"], 10)
        self.assertEqual(result["metrics"]["missing"], 0)
        self.assertEqual(result["metrics"]["nan_val"], 0.0)

    def test_missing_parameter_default_fallback(self):
        result = build_card_and_report()

        self.assertEqual(result["comments"], 0)
        self.assertEqual(result["metrics"], {})

        report_lines = result["report"].split('\n')
        self.assertEqual(len(report_lines), 3)
        self.assertTrue("No conclusion provided." in report_lines[0])
        self.assertTrue("No reasoning provided." in report_lines[1])

        elements = result["card"]["body"]["elements"]
        self.assertTrue("No conclusion provided." in elements[0]["content"])
        self.assertTrue("No reasoning provided." in elements[2]["elements"][0]["content"])

    def test_extreme_boundary_conditions(self):
        long_conclusion = "A" * 1000
        long_reasoning = "B" * 2000
        large_metrics = {f"k{i}": i for i in range(100)}

        result = build_card_and_report(
            conclusion=long_conclusion,
            reasoning=long_reasoning,
            metrics=large_metrics
        )

        # Report summary should truncate
        report_lines = result["report"].split('\n')
        self.assertEqual(len(report_lines), 3)
        self.assertEqual(len(report_lines[0]), len("Conclusion: ") + 50)
        self.assertEqual(len(report_lines[1]), len("Reasoning: ") + 50)

        # Original content in card should not be truncated
        elements = result["card"]["body"]["elements"]
        self.assertTrue(long_conclusion in elements[0]["content"])
        self.assertEqual(elements[2]["elements"][0]["content"], long_reasoning)
        self.assertEqual(len(result["metrics"]), 100)

    def test_comments_always_zero_and_report_max_3_lines(self):
        # Even with multi-line conclusion/reasoning, report should remain 3 lines
        multi_line_conclusion = "Line 1\nLine 2\nLine 3"
        multi_line_reasoning = "Reason 1\nReason 2"

        result = build_card_and_report(
            conclusion=multi_line_conclusion,
            reasoning=multi_line_reasoning,
            metrics={"score": 99}
        )

        self.assertEqual(result["comments"], 0)
        report_lines = result["report"].split('\n')
        self.assertEqual(len(report_lines), 3)

        # Ensures that only the first line was included in summary to avoid breaking 3-line format
        self.assertTrue("Line 1" in report_lines[0])
        self.assertFalse("Line 2" in report_lines[0])
        self.assertTrue("Reason 1" in report_lines[1])

if __name__ == '__main__':
    unittest.main()
