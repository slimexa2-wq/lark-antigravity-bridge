import unittest
from ultra_modules.partial_markdown_healer_integration_bridge import PartialMarkdownHealerIntegrationBridge

class TestPartialMarkdownHealerIntegrationBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = PartialMarkdownHealerIntegrationBridge()

    def test_normal_payload(self):
        # 测试正常的数据结构
        payload = {
            "message": "Hello world",
            "version": "1.0",
            "timestamp": "1234567890",
            "status": "success"
        }
        result = self.bridge.process_payload(payload)
        self.assertEqual(result["message"], "Hello world")
        self.assertEqual(result["version"], "1.0")
        self.assertEqual(result["timestamp"], "1234567890")
        self.assertEqual(result["status"], "success")

    def test_dirty_data_self_healing(self):
        # 脏数据自愈：半截代码块、半截JSON、半截粗体
        payload = {
            "content": "Here is some code:\n```python\nprint('hello')",
            "data": '{"key": "value", "arr": [1, 2,',
            "note": "This is **bold text"
        }
        result = self.bridge.process_payload(payload)

        self.assertTrue("```" in result["content"] and result["content"].endswith("```"))
        self.assertEqual(result["data"], '{"key": "value", "arr": [1, 2]}')
        self.assertTrue(result["note"].endswith("**"))

    def test_missing_param_fallback(self):
        # 缺参默认兜底测试
        result_none = self.bridge.process_payload(None)
        self.assertEqual(result_none, {"version": "2.0", "status": "default", "message": ""})

        result_empty_dict = self.bridge.process_payload({})
        self.assertEqual(result_empty_dict["version"], "2.0")

        result_invalid_type = self.bridge.process_payload("not a dict")
        self.assertEqual(result_invalid_type, {"version": "2.0", "status": "default", "message": ""})

    def test_extreme_boundary_cases(self):
        # 极端边界：空字符串、不匹配表格等
        payload = {
            "content": "",
            "table_data": "| col1 | col2 |\n|---|---|\n| val1 | val2"
        }
        result = self.bridge.process_payload(payload)
        self.assertEqual(result["content"], "")
        self.assertTrue(result["table_data"].endswith("|"))

    def test_field_auto_mapping(self):
        # 字段名映射测试
        payload = {
            "msg": "test message",
            "text": "test content",
            "uid": "user_123",
            "stat": "active",
            "tmstmp": "1000", # 应该能模糊匹配到 timestamp
            "ver": "3.0"
        }
        result = self.bridge.process_payload(payload)
        self.assertEqual(result["message"], "test message")
        self.assertEqual(result["content"], "test content")
        self.assertEqual(result["sender_id"], "user_123")
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["timestamp"], "1000")
        self.assertEqual(result["version"], "3.0")

    def test_full_coverage(self):
        # Nested payload to cover lists, dicts, etc.
        payload = {
            "nested_dict": {
                "key": "value",
                "bad_code": "```\ndef f():\n  pass"
            },
            "nested_list": [
                {"inner": "```js\nconsole.log('test')"},
                "just a str",
                123
            ],
            "num": 456,
            "json_array": '[1, 2, 3',
            "json_string_escape": '{"a": "b\\\\c',
            "json_invalid_fallback": '{"a": "b',
            "table_empty": "",
            "unmatched_key": "val"
        }
        result = self.bridge.process_payload(payload)
        self.assertTrue(result["nested_dict"]["key"] == "value")
        self.assertTrue(result["nested_dict"]["bad_code"].endswith("```"))
        self.assertTrue(result["nested_list"][0]["inner"].endswith("```"))
        self.assertEqual(result["nested_list"][1], "just a str")
        self.assertEqual(result["nested_list"][2], 123)
        self.assertEqual(result["num"], 456)
        self.assertEqual(result["json_array"], '[1, 2, 3]')
        self.assertEqual(result["json_string_escape"], '{"a": "b\\\\c"}')
        self.assertEqual(result["json_invalid_fallback"], '{"a": "b"}')
        self.assertEqual(result["table_empty"], "")
        self.assertEqual(result["unmatched_key"], "val")

        # More JSON edge cases
        self.assertEqual(self.bridge.heal_content('{"a": "b"}'), '{"a": "b"}') # Already valid
        self.assertEqual(self.bridge.heal_content('[{"a": "b"}]'), '[{"a": "b"}]') # Already valid
        self.assertEqual(self.bridge.heal_content('{"a": {"b": "c"'), '{"a": {"b": "c"}}')

        # Test diff match edge
        self.assertEqual(self.bridge._auto_map_field("zzz"), "zzz")

        # Nested object test with unmapped key
        payload2 = {"data": {"nested": "value"}}
        res2 = self.bridge.process_payload(payload2)
        self.assertEqual(res2["data"]["nested"], "value")

    def test_more_coverage(self):
        # _heal_truncated_json cover missing lines
        # '}' pop
        json_str1 = '{"a": 1, "b": {"c": 2}'
        self.assertEqual(self.bridge.heal_content(json_str1), '{"a": 1, "b": {"c": 2}}')

        json_str2 = '{"a": [1, 2, 3]'
        self.assertEqual(self.bridge.heal_content(json_str2), '{"a": [1, 2, 3]}')

        # _heal_code_blocks missing count % 2
        res_code2 = self.bridge.heal_content('```code\n`')
        self.assertEqual(res_code2, '```code\n`\n```')

        # Test type fallback on list
        res_list = self.bridge.process_payload({"a": [{"b": 1}]})
        self.assertEqual(res_list["a"][0]["b"], 1)

    def test_json_healer_edge(self):
        # Edge case that throws JSONDecodeError on fix attempt
        # Just to cover the pass in exception
        self.assertEqual(self.bridge.heal_content('{"a": }'), '{"a": }')
        # Missing bracket match fallback coverage is not fully needed since we already hit it but lets double check
        self.assertEqual(self.bridge.heal_content('{"a": "b\\\\c'), '{"a": "b\\\\c"}')
