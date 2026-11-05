import unittest
from ultra_modules.voice_message_intent_parser_batch_pipeline import parse_voice_message_intents, IntentExtractor

class BadObject:
    def __str__(self):
        raise ValueError("Cannot convert to string")

class TestVoiceMessageIntentParserBatchPipeline(unittest.TestCase):

    def test_normal_batch_processing(self):
        """Test normal batch processing with multiple intents."""
        records = [
            "把这月提成表核一下",
            "明天有个重要的会议日程",
            "我想请假",
            "随便聊聊天" # no intent
        ]
        results = parse_voice_message_intents(records)
        self.assertEqual(len(results), 4)

        # Test first record
        self.assertEqual(results[0]['intent_result']['intent'], 'audit')
        self.assertTrue(any(e['value'] == '这月' for e in results[0]['intent_result']['entities']))

        # Test second record
        self.assertEqual(results[1]['intent_result']['intent'], 'schedule')

        # Test third record
        self.assertEqual(results[2]['intent_result']['intent'], 'leave')

        # Test fourth record
        self.assertEqual(results[3]['intent_result']['intent'], 'unknown')

    def test_dirty_data_self_healing(self):
        """Test dirty data self-healing (dicts, tuples, etc.)."""
        records = [
            {"text": "核对一下工资单"},
            ("帮我查一下日程",),
            None,
            12345,
            {"some_key": "some_value"} # Will fallback to dict stringification, likely unknown intent
        ]
        results = parse_voice_message_intents(records)
        self.assertEqual(len(results), 5)

        self.assertIn(results[0]['intent_result']['intent'], ['audit', 'salary']) # Might match both, priority is based on order

        self.assertIn(results[1]['intent_result']['intent'], ['audit', 'schedule'])

        self.assertEqual(results[2]['intent_result']['intent'], 'unknown')
        self.assertEqual(results[2]['status'], 'empty_or_failed')

        self.assertEqual(results[3]['intent_result']['intent'], 'unknown')

        self.assertEqual(results[4]['intent_result']['intent'], 'unknown')

    def test_zero_config_defaults(self):
        """Test missing parameters / default arguments."""
        # Empty call
        results = parse_voice_message_intents()
        self.assertEqual(results, [])

        # Single item instead of list
        results = parse_voice_message_intents("同意这份报告")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['intent_result']['intent'], 'approval')

    def test_extreme_boundaries(self):
        """Test processing 1000 items concurrently."""
        records = ["把这月提成表核一下"] * 1000
        results = parse_voice_message_intents(records, max_workers=50) # High max_workers
        self.assertEqual(len(results), 1000)
        # Verify first and last
        self.assertEqual(results[0]['intent_result']['intent'], 'audit')
        self.assertEqual(results[999]['intent_result']['intent'], 'audit')

    def test_bad_objects_handling(self):
        """Test handling of objects that raise exceptions upon string conversion."""
        records = [
            BadObject(),
            "正常消息打卡",
            BadObject()
        ]
        results = parse_voice_message_intents(records)
        self.assertEqual(len(results), 3)

        self.assertEqual(results[0]['status'], 'empty_or_failed')
        self.assertEqual(results[0]['intent_result']['intent'], 'unknown')

        self.assertEqual(results[1]['intent_result']['intent'], 'attendance')

        self.assertEqual(results[2]['status'], 'empty_or_failed')
        self.assertEqual(results[2]['intent_result']['intent'], 'unknown')

    def test_intent_extractor_direct(self):
        extractor = IntentExtractor()
        res = extractor.extract(None)
        self.assertEqual(res['intent'], 'unknown')

        res = extractor.extract("上月总结")
        self.assertEqual(res['intent'], 'report')
        self.assertEqual(res['entities'][0]['value'], '上月')

if __name__ == '__main__':
    unittest.main()
