import unittest
import json
from ultra_modules.long_response_chunk_splitter_plain_explainer import LongResponseChunkSplitterPlainExplainer

class TestLongResponseChunkSplitterPlainExplainer(unittest.TestCase):
    def setUp(self):
        self.splitter = LongResponseChunkSplitterPlainExplainer(max_chunk_size=100, default_title="测试报告")

    def test_normal_operation_markdown(self):
        # Case 1: Normal operation with markdown header chunking
        text = "# 章节一\n这是第一章的内容。\n# 章节二\n这是第二章的内容，包含结论：测试通过。"
        result_json = self.splitter.process(text, format="json")
        cards = json.loads(result_json)

        self.assertEqual(len(cards), 3) # 1 summary + 2 chunks
        self.assertEqual(cards[0]["header"]["title"]["content"], "测试报告 - 1秒速读结论")
        self.assertIn("【核心结论】测试通过。", cards[0]["elements"][0]["content"])
        self.assertEqual(cards[1]["header"]["title"]["content"], "测试报告 - 章节一")
        self.assertEqual(cards[2]["header"]["title"]["content"], "测试报告 - 章节二")

    def test_dirty_data_self_healing(self):
        # Case 2: Dirty data (None, integers instead of strings)
        result1 = self.splitter.process(None)
        cards1 = json.loads(result1)
        self.assertEqual(cards1[0]["elements"][0]["content"], "无有效结论。")
        self.assertEqual(cards1[1]["elements"][0]["content"], "无内容")

        result2 = self.splitter.process(12345)
        cards2 = json.loads(result2)
        self.assertIn("12345", cards2[0]["elements"][0]["content"])
        self.assertIn("12345", cards2[1]["elements"][0]["content"])

    def test_missing_params_defaults(self):
        # Case 3: Missing parameters and invalid formats default properly
        text = "普通文本没有标题没有特殊格式"
        result_md = self.splitter.process(text, format="unknown_format") # Should fallback to json
        self.assertTrue(result_md.startswith("[{")) # JSON array

        # Initialize with dirty params
        dirty_splitter = LongResponseChunkSplitterPlainExplainer(max_chunk_size=-10, default_title=None)
        self.assertEqual(dirty_splitter.max_chunk_size, 1000)
        self.assertEqual(dirty_splitter.default_title, "分析报告")

    def test_extreme_boundary_long_text_split(self):
        # Case 4: Extreme boundary (very long text without headers to force length split)
        long_line = "A" * 150 # Exceeds max_chunk_size of 100
        result = self.splitter.process(long_line, format="html")

        # HTML format check
        self.assertIn("1秒速读结论", result)
        self.assertIn("引言", result)
        self.assertIn("引言 (续)", result)
        self.assertIn("<div class='feishu-card'>", result)

    def test_different_output_formats(self):
        # Case 5: Ensure markdown and html formats are correctly generated
        text = "结论：一切正常。\n内容测试"

        md_result = self.splitter.process(text, format="markdown")
        self.assertIn("# 测试报告 - 1秒速读结论", md_result)
        self.assertIn("【核心结论】一切正常。", md_result)
        self.assertIn("## 测试报告 - 引言", md_result)
        self.assertIn("内容测试", md_result)
        self.assertIn("---", md_result)

        html_result = self.splitter.process(text, format="html")
        self.assertIn("<h2>测试报告 - 1秒速读结论</h2>", html_result)
        self.assertIn("<h3>测试报告 - 引言</h3>", html_result)
        self.assertIn("<p>结论：一切正常。<br>内容测试</p>", html_result)

if __name__ == "__main__":
    unittest.main()
