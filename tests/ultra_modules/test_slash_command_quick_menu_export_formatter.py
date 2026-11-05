import unittest
import math
from ultra_modules.slash_command_quick_menu_export_formatter import format_export, clean_value

class TestSlashCommandQuickMenuExportFormatter(unittest.TestCase):
    def test_normal_input(self):
        # 1. Normal input test case
        data = {
            'command': '/周报',
            'value': 100.5,
            'count': 5,
            'other_metric': '200'
        }
        result = format_export(data)
        self.assertEqual(result['command'], '/周报')
        self.assertEqual(result['value'], 100.5)
        self.assertEqual(result['count'], 5)
        self.assertEqual(result['other_metric'], 200.0)
        self.assertEqual(result['comments'], 0)
        expected_summary = "指令: /周报\n核心数据: 100.5\n数量: 5"
        self.assertEqual(result['summary'], expected_summary)

    def test_dirty_data_self_healing(self):
        # 2. Dirty data self-healing test case
        data = {
            'command': '/提成',
            'value': float('nan'),
            'count': None,
            'metric1': 'NaN',
            'metric2': ' None ',
            'metric3': 'invalid_string',
            'metric4': ''
        }
        result = format_export(data)
        self.assertEqual(result['value'], 0)
        self.assertEqual(result['count'], 0)
        self.assertEqual(result['metric1'], 0)
        self.assertEqual(result['metric2'], 0)
        self.assertEqual(result['metric3'], 0)
        self.assertEqual(result['metric4'], 0)
        self.assertEqual(result['comments'], 0)

    def test_missing_parameter_fallback(self):
        # 3. Missing parameter fallback
        result = format_export()
        self.assertEqual(result['command'], '')
        self.assertEqual(result['value'], 0)
        self.assertEqual(result['count'], 0)
        self.assertEqual(result['comments'], 0)
        expected_summary = "指令: 默认\n核心数据: 0\n数量: 0"
        self.assertEqual(result['summary'], expected_summary)

        # Empty dict
        result2 = format_export({})
        self.assertEqual(result2['command'], '')
        self.assertEqual(result2['value'], 0)
        self.assertEqual(result2['count'], 0)

    def test_extreme_boundary_conditions(self):
        # 4. Extreme boundary conditions (invalid data types for main structure)
        # Passing integer instead of dict
        result = format_export(123)
        self.assertEqual(result['value'], 0)
        self.assertEqual(result['comments'], 0)

        # Passing string instead of dict
        result = format_export("test")
        self.assertEqual(result['value'], 0)

        # Passing list instead of dict
        result = format_export([1, 2, 3])
        self.assertEqual(result['value'], 0)

    def test_invalid_command_type_and_unexpected_values(self):
        # 5. Invalid command type in data, and unexpected data types inside values
        data = {
            'command': 123,  # command should be a string, falls back to empty
            'value': [1, 2, 3],  # unhandled type, should be 0
            'count': {'a': 1} # unhandled type, should be 0
        }
        result = format_export(data)
        self.assertEqual(result['command'], '')
        self.assertEqual(result['value'], 0)
        self.assertEqual(result['count'], 0)

    def test_clean_value_extra(self):
        # test extra branch coverages for clean_value directly
        self.assertEqual(clean_value(float('nan')), 0)
        self.assertEqual(clean_value("NULL"), 0)

if __name__ == '__main__':
    unittest.main() # pragma: no cover
