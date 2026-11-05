import unittest
import json
import math
from ultra_modules.ws_exponential_backoff_plain_explainer import explain_reconnect_status

class TestWsExponentialBackoffPlainExplainer(unittest.TestCase):
    def test_normal_usage(self):
        # Normal usage with valid integers and 'markdown' format
        result = explain_reconnect_status(attempt=3, delay_ms=1500, format_type='markdown')
        self.assertIn("断线重连中", result)
        self.assertIn("当前重试次数:** 3", result)
        self.assertIn("预计等待时间:** 1.50 秒", result)
        self.assertIn("这是第 3 次尝试重连", result)

    def test_missing_parameters_default_fallback(self):
        # Missing parameters fallback to defaults
        result = explain_reconnect_status()
        self.assertIn("初次连接准备", result)
        self.assertIn("当前重试次数:** 0", result)
        self.assertIn("预计等待时间:** 0.00 秒", result)
        self.assertIn("系统即将发起初次连接，目前没有退避延迟", result)

    def test_dirty_data_self_healing(self):
        # Dirty data (strings, None, NaN) should heal
        result = explain_reconnect_status(attempt="invalid", delay_ms=None, format_type=None)
        # Should fallback to attempt=0, delay=0, format='markdown'
        self.assertIn("初次连接准备", result)
        self.assertIn("当前重试次数:** 0", result)

        # Another dirty data case
        result2 = explain_reconnect_status(attempt=math.nan, delay_ms="3000", format_type=123)
        self.assertIn("初次连接准备", result2) # attempt is 0 due to NaN
        self.assertIn("预计等待时间:** 3.00 秒", result2)

    def test_invalid_format_fallback(self):
        # Invalid format string should fallback to markdown
        result_invalid_str = explain_reconnect_status(attempt=2, delay_ms=1000, format_type='invalid_format')
        self.assertTrue(result_invalid_str.startswith("### 🔌 状态:"))

        # Valid format 'json' should return JSON string
        result_json = explain_reconnect_status(attempt=5, delay_ms=10000, format_type='json')
        parsed_json = json.loads(result_json)
        self.assertEqual(parsed_json["status"], "断线重连中")
        self.assertEqual(parsed_json["attempt"], 5)
        self.assertEqual(parsed_json["delay_ms"], 10000.0)
        self.assertEqual(parsed_json["delay_sec_approx"], 10.0)

        # Valid format 'html' should return HTML string
        result_html = explain_reconnect_status(attempt=1, delay_ms=500, format_type='html')
        self.assertIn("<div class=\"reconnect-card\"", result_html)
        self.assertIn("<strong>当前重试次数:</strong> 1", result_html)

    def test_extreme_boundaries(self):
        # Negative attempts and delays should be zeroed/handled safely
        result_negative = explain_reconnect_status(attempt=-5, delay_ms=-1000)
        self.assertIn("当前重试次数:** 0", result_negative)
        self.assertIn("预计等待时间:** 0.00 秒", result_negative)

        # Extremely large delays
        result_large = explain_reconnect_status(attempt=1000, delay_ms=9999999999)
        self.assertIn("当前重试次数:** 1000", result_large)
        self.assertIn("这是第 1000 次尝试重连", result_large)

if __name__ == '__main__':
    unittest.main()
