import unittest
from ultra_modules.multi_bot_mention_dispatcher_plain_explainer import explain_multi_bot_results, to_int_safe

class TestMultiBotMentionDispatcherPlainExplainer(unittest.TestCase):

    def test_normal_conditions(self):
        # 1. Normal Conditions (all valid inputs)
        data = {
            "da_fei_yu": {"fish_caught": 10, "weight": 20},
            "zhao_pin": {"candidates": 50, "interviews": 5},
            "shu_ju": {"active_users": 100, "revenue": 500},
            "liang_hua": {"trades": 20, "profit": 1000}
        }
        result = explain_multi_bot_results(data)
        self.assertEqual(result["title"], "🚀 综合汇报: 业务高速增长中！")
        self.assertIn("10 条鱼", result["markdown"])
        self.assertIn("50 份简历", result["markdown"])

    def test_dirty_data_self_healing(self):
        # 2. Dirty Data Self-Healing (e.g., strings where ints are expected)
        data = {
            "da_fei_yu": {"fish_caught": "15", "weight": "25.5"}, # float string
            "zhao_pin": {"candidates": "bad_data", "interviews": None},
            "shu_ju": {"active_users": [1,2], "revenue": "100.99"},
            "liang_hua": "not_a_dict"
        }
        result = explain_multi_bot_results(data)

        self.assertEqual(result["raw_clean"]["da_fei_yu"]["fish_caught"], 15)
        self.assertEqual(result["raw_clean"]["da_fei_yu"]["weight"], 25)

        self.assertEqual(result["raw_clean"]["zhao_pin"]["candidates"], 0)
        self.assertEqual(result["raw_clean"]["zhao_pin"]["interviews"], 0)

        self.assertEqual(result["raw_clean"]["shu_ju"]["active_users"], 0)
        self.assertEqual(result["raw_clean"]["shu_ju"]["revenue"], 100)

        self.assertEqual(result["raw_clean"]["liang_hua"]["trades"], 0)

        self.assertEqual(result["title"], "📊 综合汇报: 业务平稳推进中。")

    def test_missing_parameter_fallbacks(self):
        # 3. Missing Parameter Fallbacks (empty dicts/none)
        data = {
            "da_fei_yu": None,
            # zhao_pin missing entirely
            "shu_ju": {},
            "liang_hua": {"trades": 5}
        }
        result = explain_multi_bot_results(data)
        self.assertEqual(result["raw_clean"]["da_fei_yu"]["fish_caught"], 0)
        self.assertEqual(result["raw_clean"]["zhao_pin"]["candidates"], 0)
        self.assertEqual(result["raw_clean"]["liang_hua"]["trades"], 5)
        self.assertEqual(result["raw_clean"]["liang_hua"]["profit"], 0)

    def test_extreme_boundary_conditions(self):
        # 4. Extreme Boundary Conditions (huge numbers, empty results)
        data = {
            "da_fei_yu": {"fish_caught": 999999999999, "weight": -5},
            "zhao_pin": {"candidates": 0, "interviews": 0},
            "shu_ju": {"active_users": 0, "revenue": 0},
            "liang_hua": {"trades": 0, "profit": 0}
        }
        result = explain_multi_bot_results(data)
        self.assertEqual(result["raw_clean"]["da_fei_yu"]["fish_caught"], 999999999999)
        self.assertEqual(result["raw_clean"]["da_fei_yu"]["weight"], -5)
        self.assertEqual(result["title"], "🚀 综合汇报: 业务高速增长中！")

    def test_invalid_inputs(self):
        # 5. Invalid Inputs (e.g., None passed instead of dict)
        result = explain_multi_bot_results(None)
        self.assertEqual(result["title"], "📉 综合汇报: 暂无明显进展。")
        self.assertEqual(result["raw_clean"]["da_fei_yu"]["fish_caught"], 0)

        result = explain_multi_bot_results("completely invalid string")
        self.assertEqual(result["title"], "📉 综合汇报: 暂无明显进展。")

    def test_to_int_safe_coverage(self):
        # specifically test to_int_safe branches for 100% coverage
        self.assertEqual(to_int_safe(10), 10)
        self.assertEqual(to_int_safe(10.5), 10)
        self.assertEqual(to_int_safe("10"), 10)
        self.assertEqual(to_int_safe("10.5"), 10)
        self.assertEqual(to_int_safe("abc"), 0)
        self.assertEqual(to_int_safe("abc", default=-1), -1)
        self.assertEqual(to_int_safe(None), 0)
        self.assertEqual(to_int_safe([1, 2]), 0)

if __name__ == '__main__':
    unittest.main()
