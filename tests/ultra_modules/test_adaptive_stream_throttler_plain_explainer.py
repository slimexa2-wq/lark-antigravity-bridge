import unittest
import json
from ultra_modules.adaptive_stream_throttler_plain_explainer import AdaptiveStreamThrottlerPlainExplainer

class TestAdaptiveStreamThrottlerPlainExplainer(unittest.TestCase):
    def setUp(self):
        self.explainer = AdaptiveStreamThrottlerPlainExplainer()

    def test_normal_conditions(self):
        # Test normal mid-range window
        metrics = {
            'current_window_ms': 300,
            'sequence_number': 42,
            'dropped_messages': 5
        }
        result = self.explainer.explain(metrics, format_type='markdown')
        self.assertIn("**当前状态:** 正常 (Normal)", result)
        self.assertIn("300.0毫秒", result)
        self.assertIn("**最新序号:** 42", result)
        self.assertIn("**拦截冗余:** 5条", result)

        # Test HTML output
        html_result = self.explainer.explain(metrics, format_type='html')
        self.assertIn("<div class=\"throttler-card\">", html_result)
        self.assertIn("300.0毫秒", html_result)

        # Test JSON output
        json_result = self.explainer.explain(metrics, format_type='JSON ')
        parsed_json = json.loads(json_result)
        self.assertEqual(parsed_json['window_ms'], "300.0毫秒")
        self.assertEqual(parsed_json['status'], "正常 (Normal)")
        self.assertEqual(parsed_json['sequence'], "42")
        self.assertEqual(parsed_json['dropped'], "5")

    def test_dirty_data_self_healing(self):
        # Test with string values instead of ints/floats
        metrics_str = {
            'current_window_ms': "250.5",
            'sequence_number': "10",
            'dropped_messages': "2"
        }
        result_str = self.explainer.explain(metrics_str, format_type='markdown')
        self.assertIn("250.5毫秒", result_str)
        self.assertIn("**最新序号:** 10", result_str)

        # Test with unparseable data
        metrics_bad = {
            'current_window_ms': "bad_window",
            'sequence_number': [1,2,3],
            'dropped_messages': None
        }
        result_bad = self.explainer.explain(metrics_bad)
        self.assertIn("300.0毫秒", result_bad) # default window
        self.assertIn("**最新序号:** 0", result_bad) # default seq
        self.assertIn("**拦截冗余:** 0条", result_bad) # default dropped

        # Test with completely wrong object type
        class BadObject:
            pass

        result_obj = self.explainer.explain(BadObject())
        self.assertIn("300.0毫秒", result_obj)

        result_list = self.explainer.explain(["invalid", "data"])
        self.assertIn("300.0毫秒", result_list)

    def test_missing_parameters_fallback(self):
        # Test with None input (Zero configuration API)
        result_none = self.explainer.explain(None)
        self.assertIn("300.0毫秒", result_none)
        self.assertIn("正常 (Normal)", result_none)
        self.assertIn("**最新序号:** 0", result_none)
        self.assertIn("**拦截冗余:** 0条", result_none)

        # Test with empty dict
        result_empty = self.explainer.explain({})
        self.assertIn("300.0毫秒", result_empty)

        # Test missing format type
        result_default_format = self.explainer.explain({'current_window_ms': 200})
        self.assertTrue(result_default_format.startswith("# 飞书流式卡片推送状态摘要"))

    def test_extreme_boundary_conditions(self):
        # Below lower bound (should clamp to 150ms)
        metrics_low = {'current_window_ms': -50, 'dropped_messages': -10}
        result_low = self.explainer.explain(metrics_low)
        self.assertIn("150.0毫秒", result_low)
        self.assertIn("畅通 (Smooth) - 极速推送中", result_low)
        self.assertIn("**拦截冗余:** 0条", result_low) # Negative drops clamp to 0

        # Above upper bound (should clamp to 500ms)
        metrics_high = {'current_window_ms': 9999999}
        result_high = self.explainer.explain(metrics_high)
        self.assertIn("500.0毫秒", result_high)
        self.assertIn("拥堵 (Congested) - 推送降速中", result_high)

    def test_object_input_attributes(self):
        # Test handling object that acts like a dict using __dict__
        class MockMetrics:
            def __init__(self):
                self.current_window_ms = 460
                self.sequence_number = 99
                self.dropped_messages = 1

        metrics_obj = MockMetrics()
        result = self.explainer.explain(metrics_obj)
        self.assertIn("460.0毫秒", result)
        self.assertIn("拥堵 (Congested)", result)
        self.assertIn("**最新序号:** 99", result)

if __name__ == '__main__':
    unittest.main()
