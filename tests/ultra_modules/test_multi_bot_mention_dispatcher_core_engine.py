import unittest
import json
from ultra_modules.multi_bot_mention_dispatcher_core_engine import (
    clean_string,
    parse_mentions,
    generate_aggregated_card
)

class TestMultiBotMentionDispatcherCoreEngine(unittest.TestCase):

    def test_clean_string(self):
        # Normal string
        self.assertEqual(clean_string(" hello  "), "hello")

        # Missing parameter fallback (None)
        self.assertEqual(clean_string(None, "default"), "default")

        # Missing parameter fallback (without custom default)
        self.assertEqual(clean_string(None), "")

        # Dirty data self-healing: integers
        self.assertEqual(clean_string(123), "123")

        # Dirty data self-healing: complex objects (dicts and lists)
        self.assertEqual(clean_string({"key": "value"}), '{"key": "value"}')
        self.assertEqual(clean_string([1, 2, 3]), '[1, 2, 3]')

        # Edge case: object that cannot be easily stringified in standard json will just fallback to str()
        class Dummy:
            def __str__(self):
                return "dummy"
        self.assertEqual(clean_string(Dummy()), "dummy")

    def test_parse_mentions_normal(self):
        msg = "@大肥鱼 请分析市场 @招聘 查一下HC @数据 导出报表"
        expected = {
            "大肥鱼": "请分析市场",
            "招聘": "查一下HC",
            "数据": "导出报表"
        }
        self.assertEqual(parse_mentions(msg), expected)

    def test_parse_mentions_dirty_and_missing(self):
        # Empty string
        self.assertEqual(parse_mentions(""), {})

        # None
        self.assertEqual(parse_mentions(None), {})

        # No bots mentioned
        self.assertEqual(parse_mentions("这是一段没有提及机器人的话"), {})

        # Only one bot with no command
        self.assertEqual(parse_mentions("@大肥鱼"), {"大肥鱼": ""})

        # Dirty data: integer as message
        self.assertEqual(parse_mentions(123), {})

        # Edge case: multiple spaces
        self.assertEqual(parse_mentions("   @bot1   cmd1   @bot2   cmd2   "), {"bot1": "cmd1", "bot2": "cmd2"})

    def test_generate_aggregated_card_normal(self):
        bot_results = {
            "大肥鱼": "市场分析完成，结果向好。",
            "招聘": {"summary": "HC有空缺", "details": "目前还有3个前端岗位和2个后端岗位"}
        }
        card = generate_aggregated_card(bot_results)

        self.assertEqual(card["header"]["title"]["content"], "多Bot协同执行结果汇总")
        # bot1 summary + hr + bot2 summary + bot2 details note
        self.assertEqual(len(card["elements"]), 4)
        self.assertEqual(card["elements"][0]["content"], "**@大肥鱼** 响应:\n市场分析完成，结果向好。")
        self.assertEqual(card["elements"][1]["tag"], "hr")
        self.assertEqual(card["elements"][2]["content"], "**@招聘** 响应:\nHC有空缺")
        self.assertEqual(card["elements"][3]["tag"], "note")
        self.assertEqual(card["elements"][3]["elements"][1]["content"], "目前还有3个前端岗位和2个后端岗位")

    def test_generate_aggregated_card_truncation(self):
        # More than 3 lines summary
        summary_text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        bot_results = {
            "数据": summary_text
        }
        card = generate_aggregated_card(bot_results)

        # 1 markdown, 1 note (details)
        self.assertEqual(len(card["elements"]), 2)
        self.assertEqual(card["elements"][0]["content"], "**@数据** 响应:\nLine 1\nLine 2\nLine 3")
        self.assertEqual(card["elements"][1]["tag"], "note")
        self.assertEqual(card["elements"][1]["elements"][1]["content"], "Line 4\nLine 5")

    def test_generate_aggregated_card_truncation_with_existing_details(self):
        # More than 3 lines summary and existing details
        summary_text = "Line 1\nLine 2\nLine 3\nLine 4"
        details_text = "Extra details"
        bot_results = {
            "Bot1": {"summary": summary_text, "details": details_text}
        }
        card = generate_aggregated_card(bot_results)

        self.assertEqual(card["elements"][0]["content"], "**@Bot1** 响应:\nLine 1\nLine 2\nLine 3")
        expected_details = "Line 4\n---\nExtra details"
        self.assertEqual(card["elements"][1]["elements"][1]["content"], expected_details)

    def test_generate_aggregated_card_dirty_data(self):
        # Invalid bot_results type
        card = generate_aggregated_card(None)
        self.assertEqual(len(card["elements"]), 1)
        self.assertEqual(card["elements"][0]["content"], "未识别到任何有效指令。 / No valid commands recognized.")

        # Missing summary or empty results
        bot_results = {
            "BotEmpty": {},
            "BotNone": None
        }
        card2 = generate_aggregated_card(bot_results)
        self.assertEqual(len(card2["elements"]), 3) # BotEmpty + hr + BotNone
        self.assertEqual(card2["elements"][0]["content"], "**@BotEmpty** 响应:\n无结果 / No result")
        self.assertEqual(card2["elements"][2]["content"], "**@BotNone** 响应:\n无结果 / No result")

if __name__ == "__main__":
    unittest.main()
