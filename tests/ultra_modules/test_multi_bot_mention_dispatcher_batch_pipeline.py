import unittest
from ultra_modules.multi_bot_mention_dispatcher_batch_pipeline import MultiBotMentionDispatcher

class TestMultiBotMentionDispatcherBatchPipeline(unittest.TestCase):
    def setUp(self):
        self.dispatcher = MultiBotMentionDispatcher(max_workers=5)

    def test_normal_standard_batch_processing(self):
        records = [
            "Hello @大肥鱼, please check this out.",
            "Can @招聘 and @数据 help me?",
            "Nothing here.",
            {"text": "Is this @量化 suitable?"}
        ]
        result = self.dispatcher.dispatch_batch(records)

        summary = result["batch_summary"]
        self.assertEqual(summary["total_records"], 4)
        self.assertEqual(summary["processed_successfully"], 4)

        stats = result["mention_statistics"]
        self.assertEqual(stats.get("@大肥鱼"), 1)
        self.assertEqual(stats.get("@招聘"), 1)
        self.assertEqual(stats.get("@数据"), 1)
        self.assertEqual(stats.get("@量化"), 1)

    def test_dirty_data_self_healing(self):
        records = [
            None,
            12345,
            {"invalid_key": "where is the text?"},
            "",
            ["list", "of", "strings"]
        ]
        result = self.dispatcher.dispatch_batch(records)

        summary = result["batch_summary"]
        self.assertEqual(summary["total_records"], 5)
        self.assertEqual(summary["ignored_empty"], 2) # None and ""
        self.assertEqual(summary["processed_successfully"], 3) # 12345, dict without text/content, list

        # dict without text fallback to str(dict)
        results_snap = result["results_snapshot"]
        dict_res = [r for r in results_snap if r["original_record_type"] == "dict"][0]
        self.assertEqual(dict_res["cleaned_text"], "{'invalid_key': 'where is the text?'}")

    def test_missing_parameter_default_fallback(self):
        # Calling without arguments
        result = self.dispatcher.dispatch_batch()
        self.assertEqual(result["batch_summary"]["total_records"], 0)
        self.assertEqual(result["batch_summary"]["processed_successfully"], 0)

        # Calling with single non-list item
        result2 = self.dispatcher.dispatch_batch("Just a single string with @大肥鱼")
        self.assertEqual(result2["batch_summary"]["total_records"], 1)
        self.assertEqual(result2["batch_summary"]["processed_successfully"], 1)
        self.assertEqual(result2["mention_statistics"].get("@大肥鱼"), 1)

    def test_extreme_boundary_cases(self):
        # Empty list
        result_empty = self.dispatcher.dispatch_batch([])
        self.assertEqual(result_empty["batch_summary"]["total_records"], 0)

        # Large batch of 1000 items
        large_batch = ["@量化 message " + str(i) for i in range(1000)]
        result_large = self.dispatcher.dispatch_batch(large_batch)
        self.assertEqual(result_large["batch_summary"]["total_records"], 1000)
        self.assertEqual(result_large["batch_summary"]["processed_successfully"], 1000)
        self.assertEqual(result_large["mention_statistics"]["@量化"], 1000)

    def test_mention_extraction_verification(self):
        # Multiple bots in same text, exact matches
        text = "@大肥鱼, you and @大肥鱼 together with @招聘, and some random @未定义"
        result = self.dispatcher.dispatch_batch([text])
        stats = result["mention_statistics"]

        # Extractor currently works with "in" string matching per bot,
        # so it just knows "@大肥鱼" is present, count will be 1 for the whole text record.
        self.assertEqual(stats.get("@大肥鱼"), 1)
        self.assertEqual(stats.get("@招聘"), 1)
        self.assertNotIn("@未定义", stats)

if __name__ == "__main__":
    unittest.main()
