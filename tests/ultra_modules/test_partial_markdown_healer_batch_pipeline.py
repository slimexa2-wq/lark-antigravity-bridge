import unittest
from ultra_modules.partial_markdown_healer_batch_pipeline import PartialMarkdownHealerBatchPipeline

class TestPartialMarkdownHealerBatchPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = PartialMarkdownHealerBatchPipeline(max_workers=5)

    def test_normal_use_case(self):
        """Test with valid data that does not need healing."""
        items = ["**bold**", "```python\nprint(1)\n```", "| a | b |\n|---|---|\n| c | d |", '{"a": 1}']
        results = self.pipeline.process_batch(items)
        self.assertEqual(results, items)

    def test_dirty_data_self_healing(self):
        """Test healing of unclosed tags."""
        cases = [
            ("**bold", "**bold**"),
            ("```python\nprint(1)", "```python\nprint(1)\n```"),
            ("| a | b |\n|---|---|\n| c | d ", "| a | b |\n|---|---|\n| c | d |"),
            ('{"a": 1', '{"a": 1}'),
            ('[1, 2, 3', '[1, 2, 3]')
        ]

        items = [c[0] for c in cases]
        expected = [c[1] for c in cases]

        results = self.pipeline.process_batch(items)
        self.assertEqual(results, expected)

    def test_default_fallback_null(self):
        """Test fallback when input is None."""
        self.assertEqual(self.pipeline.heal_single(None), "")
        self.assertEqual(self.pipeline.process_batch([None, "**abc"]), ["", "**abc**"])

    def test_high_throughput_batch(self):
        """Test batch processing with 1000 items."""
        pipeline = PartialMarkdownHealerBatchPipeline(max_workers=50)
        items = ["**batch" + str(i) for i in range(1000)]
        expected = ["**batch" + str(i) + "**" for i in range(1000)]
        results = pipeline.process_batch(items)
        self.assertEqual(results, expected)

    def test_streaming_progress(self):
        """Test streaming process to ensure it yields correct progress snapshots."""
        items = ["**str1", "```bash\nls", "| A |\n|---|", '{"key": "val"']
        expected_finals = [
            "**str1**",
            "```bash\nls\n```",
            "| A |\n|---|",
            '{"key": "val"}'
        ]

        snapshots = list(self.pipeline.stream_process(items))
        self.assertEqual(len(snapshots), len(items))

        last_snapshot = snapshots[-1]
        self.assertEqual(last_snapshot["progress"], 1.0)
        self.assertEqual(last_snapshot["completed"], 4)
        self.assertEqual(last_snapshot["total"], 4)

        # In stream_process the order of results completing can vary,
        # but the array indexes are mapped correctly, so by the end,
        # the results array should be fully populated and in order.
        self.assertEqual(last_snapshot["results"], expected_finals)

    def test_extreme_edge_cases(self):
        """Test weird strings and ensure no crash."""
        items = ["", "   ", "\n\n", "****", "``````"]
        # Healing these might result in specific outputs, mainly we want to ensure no crash
        results = self.pipeline.process_batch(items)
        self.assertEqual(len(results), 5)
        # Empty stays empty
        self.assertEqual(results[0], "")
        # Whitespace stays whitespace
        self.assertEqual(results[1], "   ")

if __name__ == '__main__':
    unittest.main()
