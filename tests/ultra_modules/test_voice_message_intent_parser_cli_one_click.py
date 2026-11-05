import sys
import unittest
import json
from unittest.mock import patch
from io import StringIO
from ultra_modules.voice_message_intent_parser_cli_one_click import parse_voice_command, export_result, cli_main

class TestVoiceMessageIntentParserCLI(unittest.TestCase):

    def test_normal_path(self):
        # Normal path
        text = "把这月提成表核一下"
        intent = parse_voice_command(text)
        self.assertEqual(intent["action"], "核对")
        self.assertEqual(intent["target"], "提成表")
        self.assertEqual(intent["time"], "本月")
        self.assertEqual(intent["raw"], text)

        # JSON export
        json_out = export_result(intent, "json")
        self.assertIn('"action": "核对"', json_out)
        self.assertIn('"target": "提成表"', json_out)

        # CSV/Excel export
        csv_out = export_result(intent, "csv")
        self.assertIn("action,target,time,raw", csv_out)
        self.assertIn("核对,提成表,本月,把这月提成表核一下", csv_out)

    def test_dirty_data_self_healing(self):
        # Dirty data: Non-string input
        class BadObject:
            def __str__(self):
                raise ValueError("cannot convert to string")

        intent1 = parse_voice_command(123.45)
        self.assertEqual(intent1["raw"], "123.45")

        intent2 = parse_voice_command(BadObject())
        self.assertEqual(intent2["raw"], "")
        self.assertEqual(intent2["action"], "unknown")

        # Dirty data: Unprintable characters
        text_with_unprintable = "发\x00送\x08报\x07告"
        intent3 = parse_voice_command(text_with_unprintable)
        self.assertEqual(intent3["raw"], "发送报告")
        self.assertEqual(intent3["action"], "发送")
        self.assertEqual(intent3["target"], "报告")

        # Dirty data in export
        dirty_intent = {"action": 123, "target": None, "raw": ["not", "string"]}
        export_out = export_result(dirty_intent, "json")
        data = json.loads(export_out)
        self.assertEqual(data["action"], "123")
        self.assertEqual(data["target"], "None")
        self.assertEqual(data["time"], "unknown")

    def test_missing_parameters_fallback(self):
        # Missing text
        intent = parse_voice_command(None)
        self.assertEqual(intent["raw"], "")
        self.assertEqual(intent["action"], "unknown")

        # Missing export parameters
        out1 = export_result(None, None)
        data1 = json.loads(out1)
        self.assertEqual(data1["action"], "unknown")

        out2 = export_result(fmt="")
        data2 = json.loads(out2)
        self.assertEqual(data2["action"], "unknown")

        # Test CLI default parameters
        with patch('sys.stdout', new_callable=StringIO):
            result = cli_main([])
            self.assertIn('"action": "核对"', result)

    def test_extreme_boundary_conditions(self):
        # Empty string
        intent = parse_voice_command("")
        self.assertEqual(intent["raw"], "")
        self.assertEqual(intent["action"], "unknown")

        # Whitespace string
        intent = parse_voice_command("   \n   \t  ")
        self.assertEqual(intent["raw"], "")
        self.assertEqual(intent["action"], "unknown")

        # No recognizable entities
        intent = parse_voice_command("天气不错")
        self.assertEqual(intent["raw"], "天气不错")
        self.assertEqual(intent["action"], "unknown")
        self.assertEqual(intent["target"], "unknown")

        # Another action and target
        intent = parse_voice_command("做一份上月总结")
        self.assertEqual(intent["action"], "创建")
        self.assertEqual(intent["target"], "报告")
        self.assertEqual(intent["time"], "上月")

    def test_cli_entry_point(self):
        # Test CLI with json format
        with patch('sys.stdout', new_callable=StringIO):
            res_json = cli_main(["--text", "查上月工资", "--format", "json"])
            data = json.loads(res_json)
            self.assertEqual(data["action"], "核对")
            self.assertEqual(data["target"], "工资单")
            self.assertEqual(data["time"], "上月")

        # Test CLI with csv format
        with patch('sys.stdout', new_callable=StringIO):
            res_csv = cli_main(["--text", "今天发报告", "--format", "csv"])
            self.assertIn("发送,报告,今天,今天发报告", res_csv)

        # Test CLI with excel format (same as csv internally)
        with patch('sys.stdout', new_callable=StringIO):
            res_excel = cli_main(["--text", "今天发报告", "--format", "excel"])
            self.assertIn("发送,报告,今天,今天发报告", res_excel)

    @patch.object(sys, 'argv', ['prog'])
    def test_cli_main_args_none(self):
        with patch('sys.stdout', new_callable=StringIO):
            result = cli_main(None)
            self.assertIn('"action": "核对"', result)

    def test_main_execution(self):
        with patch('sys.stdout', new_callable=StringIO):
            import ultra_modules.voice_message_intent_parser_cli_one_click
            ultra_modules.voice_message_intent_parser_cli_one_click.cli_main([])

if __name__ == "__main__":
    unittest.main()
