import unittest
import time
from typing import List

from ultra_modules.multi_bot_mention_dispatcher_benchmark_suite import (
    MultiBotMentionDispatcher,
    SyntheticFixtureGenerator,
    BenchmarkSuite
)

class TestMultiBotMentionDispatcher(unittest.TestCase):
    def setUp(self):
        self.dispatcher = MultiBotMentionDispatcher()

    def test_normal_case(self):
        dataset = SyntheticFixtureGenerator.generate_normal()
        for item in dataset:
            mentions = self.dispatcher.parse_mentions(item)
            results = self.dispatcher.dispatch(mentions)
            card = self.dispatcher.build_feishu_card(results)

            self.assertIn("config", card)
            self.assertIn("header", card)
            self.assertIn("elements", card)

            # Should have up to 3 lines summary
            summary = card["elements"][0]["text"]["content"]
            lines = summary.split("\n")
            self.assertLessEqual(len(lines), 3)

    def test_dirty_data_and_self_healing(self):
        dataset = SyntheticFixtureGenerator.generate_dirty()
        for item in dataset:
            # We expect zero crashes
            try:
                mentions = self.dispatcher.parse_mentions(item)
                results = self.dispatcher.dispatch(mentions)
                card = self.dispatcher.build_feishu_card(results)
            except Exception as e:
                self.fail(f"Dispatcher failed on dirty data '{item}': {e}")

            # If item was None or empty, it should use the empty card logic
            if not item or (isinstance(item, str) and not item.strip()):
                self.assertEqual(card["header"]["template"], "grey")
                self.assertEqual(card["elements"][0]["text"]["content"], "暂无有效的Bot提及或解析失败，未执行任何任务。")

    def test_missing_params_fallback(self):
        # When bot name is not strictly in KNOWN_BOTS, it should fallback
        mentions = self.dispatcher.parse_mentions("@未知 @飞书")
        self.assertEqual(len(mentions), 2)
        for m in mentions:
            self.assertEqual(m.bot_name, "默认助手")

        results = self.dispatcher.dispatch(mentions)
        card = self.dispatcher.build_feishu_card(results)

        # Checking collapsible detailed card is there
        self.assertEqual(len(card["elements"]), 2) # 1 summary + 1 detail note for "默认助手"

    def test_extreme_boundary_conditions(self):
        dataset = SyntheticFixtureGenerator.generate_extreme_boundary()
        for item in dataset:
            # Should not crash on huge strings or extreme boundaries
            try:
                mentions = self.dispatcher.parse_mentions(item)
                # Some are cross-year single sentences (len >= 1), some are big synthetic items (len >= 500)
                self.assertGreaterEqual(len(mentions), 1)
            except Exception as e:
                self.fail(f"Dispatcher failed on extreme boundary: {e}")

    def test_ultra_high_concurrency_benchmark(self):
        # The requirement asks for verifying millisecond-level response for high concurrency
        # We will use 10,000 requests.
        dataset = SyntheticFixtureGenerator.generate_high_concurrency(count=10000)
        suite = BenchmarkSuite(self.dispatcher)

        metrics = suite.run_benchmark(dataset)

        # Zero crashes
        self.assertEqual(metrics["failure_count"], 0)
        self.assertEqual(metrics["success_count"], 10000)

        # Check avg time per item is below a reasonable threshold, e.g. < 5ms per item
        # (Usually it's way faster, like 0.05ms)
        self.assertLess(metrics["avg_ms_per_item"], 5.0,
                        "Average processing time per request exceeded 5ms threshold")

if __name__ == "__main__":
    unittest.main()
