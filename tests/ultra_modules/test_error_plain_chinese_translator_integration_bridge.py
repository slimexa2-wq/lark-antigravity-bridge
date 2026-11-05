import unittest
import time
from ultra_modules.error_plain_chinese_translator_integration_bridge import ErrorPlainChineseTranslatorIntegrationBridge

class TestErrorPlainChineseTranslatorIntegrationBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = ErrorPlainChineseTranslatorIntegrationBridge()

    def test_normal_input(self):
        payload = {
            'error_code': 'TIMEOUT_001',
            'error_message': 'Request timeout after 30s',
            'timestamp': int(time.time())
        }
        res = self.bridge.translate_error_to_card(payload)
        self.assertEqual(res['title'], '出错了')
        self.assertEqual(res['plain_chinese_reason'], '网络请求超时或后端服务响应太慢')
        self.assertEqual(res['action_button_text'], '一键诊断网络并重试')
        self.assertEqual(res['original_error_code'], 'TIMEOUT_001')
        self.assertEqual(res['auto_snapshot_enabled'], False)

    def test_old_schema_input(self):
        # Using 'code' and 'msg' instead of 'error_code' and 'error_message'
        payload = {
            'code': '403',
            'msg': 'Permission denied'
        }
        res = self.bridge.translate_error_to_card(payload)
        self.assertEqual(res['plain_chinese_reason'], '您目前没有执行此操作的权限')
        self.assertEqual(res['original_error_code'], '403')

    def test_wrapper_object_input(self):
        # Using wrapper objects like 'error' or 'data'
        payload = {
            'error': {
                'errCode': 'DB_ERR',
                'err_msg': 'Database connection failed'
            }
        }
        res = self.bridge.translate_error_to_card(payload)
        self.assertEqual(res['plain_chinese_reason'], '底层数据库出现异常')
        self.assertEqual(res['original_error_code'], 'DB_ERR')
        self.assertEqual(res['auto_snapshot_enabled'], True)

    def test_missing_parameter_fallback(self):
        # Empty payload
        res = self.bridge.translate_error_to_card(None)
        self.assertEqual(res['original_error_code'], 'UNKNOWN_ERROR')
        self.assertEqual(res['plain_chinese_reason'], '遇到了一点小状况，我们正在努力解决')

        # Invalid type payload
        res = self.bridge.translate_error_to_card("not a dict")
        self.assertEqual(res['original_error_code'], 'UNKNOWN_ERROR')
        self.assertEqual(res['plain_chinese_reason'], '遇到了一点小状况，我们正在努力解决')

    def test_dirty_data_self_healing(self):
        # Dirty timestamp data and weird types for code/msg
        payload = {
            'code': 404,  # Int instead of string
            'message': ['Not found'],  # List instead of string
            'timestamp': 'dirty_string_not_a_number'
        }
        res = self.bridge.translate_error_to_card(payload)
        self.assertEqual(res['original_error_code'], '404')
        self.assertEqual(res['plain_chinese_reason'], '找不到您请求的资源或数据')
        self.assertIsInstance(res['timestamp'], int) # Should self-heal to current time

    def test_extreme_boundary_cases(self):
        # Timestamp way in the future (ms and microseconds)
        ts_ms = int(time.time()) * 1000
        payload_ms = {'timestamp': ts_ms}
        res_ms = self.bridge.translate_error_to_card(payload_ms)
        self.assertLess(res_ms['timestamp'], 10000000000) # Should be converted to seconds

        ts_micro = int(time.time()) * 1000000
        payload_micro = {'timestamp': ts_micro}
        res_micro = self.bridge.translate_error_to_card(payload_micro)
        self.assertLess(res_micro['timestamp'], 10000000000) # Should be converted to seconds

        # Invalid timestamp types
        res_invalid_ts = self.bridge.translate_error_to_card({'timestamp': {}})
        self.assertIsInstance(res_invalid_ts['timestamp'], int)

        res_none_ts = self.bridge.translate_error_to_card({'timestamp': None})
        self.assertIsInstance(res_none_ts['timestamp'], int)

        # Out of bounds timestamp (before 1970 or after 2100)
        res_future_ts = self.bridge.translate_error_to_card({'timestamp': 5102444800})
        self.assertIsInstance(res_future_ts['timestamp'], int)
        self.assertNotEqual(res_future_ts['timestamp'], 5102444800)

    def test_other_error_types(self):
        # Memory error
        res = self.bridge.translate_error_to_card({'message': 'Out of memory'})
        self.assertEqual(res['plain_chinese_reason'], '服务器内存不足导致处理失败')

        # Type error
        res = self.bridge.translate_error_to_card({'message': 'TypeError: ...'})
        self.assertEqual(res['plain_chinese_reason'], '系统内部数据处理格式错误')
        self.assertEqual(res['auto_snapshot_enabled'], True)

        # Connection refused in stack trace
        res = self.bridge.translate_error_to_card({'stack_trace': '... connection refused ...'})
        self.assertEqual(res['plain_chinese_reason'], '无法连接到后台服务')

if __name__ == '__main__':
    unittest.main()
