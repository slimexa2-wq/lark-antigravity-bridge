import unittest
from ultra_modules.daily_ops_digest_pusher_plain_explainer import explain_digest_in_plain_language

class TestDailyOpsDigestPusherPlainExplainer(unittest.TestCase):

    def test_normal_data(self):
        data = {
            "progress": {
                "status": "顺利推进",
                "details": "核心模块已完成测试并准备发布。"
            },
            "recruitment": {
                "hired": 3,
                "target": 5,
                "details": "本周新入职3名后端开发。"
            },
            "health": {
                "score": 99.9,
                "details": "系统零故障运行15天。"
            }
        }
        result = explain_digest_in_plain_language(data)

        summary = result["elements"][0]["content"]
        self.assertIn("Jules舰队当前状态：顺利推进。", summary)
        self.assertIn("当前已入职 3 人（目标 5 人）。", summary)
        self.assertIn("系统健康度评分：99.9%。", summary)
        self.assertEqual(len(summary.split("\n")), 3)

        panel = result["elements"][1]["elements"][0]["content"]
        self.assertIn("核心模块已完成测试并准备发布。", panel)
        self.assertIn("本周新入职3名后端开发。", panel)
        self.assertIn("系统零故障运行15天。", panel)

    def test_dirty_data_self_healing(self):
        data = {
            "progress": {
                "status": 404,
                "details": ["错误", "不是字符串"]
            },
            "recruitment": {
                "hired": "5.9", # should become 5
                "target": "2", # should be bumped to 5 since 5 > 2
                "details": {"key": "value"}
            },
            "health": {
                "score": "95.5",
                "details": 12345
            }
        }
        result = explain_digest_in_plain_language(data)

        summary = result["elements"][0]["content"]
        self.assertIn("Jules舰队当前状态：404。", summary)
        self.assertIn("当前已入职 5 人（目标 5 人）。", summary)
        self.assertIn("系统健康度评分：95.5%。", summary)

        panel = result["elements"][1]["elements"][0]["content"]
        self.assertIn("不是字符串", panel)
        self.assertIn("value", panel)
        self.assertIn("12345", panel)

    def test_missing_parameters_fallback(self):
        for data in [{}, None, "not_a_dict"]:
            result = explain_digest_in_plain_language(data)

            summary = result["elements"][0]["content"]
            self.assertIn("Jules舰队当前状态：未知。", summary)
            self.assertIn("当前已入职 0 人（目标 0 人）。", summary)
            self.assertIn("系统健康度评分：100.0%。", summary)

            panel = result["elements"][1]["elements"][0]["content"]
            self.assertIn("无详细进度信息。", panel)
            self.assertIn("无详细招聘信息。", panel)
            self.assertIn("系统运行平稳。", panel)

    def test_extreme_boundary_conditions(self):
        long_string = "X" * 5000
        data = {
            "progress": {
                "status": "   ",
                "details": long_string
            },
            "recruitment": {
                "hired": -10,
                "target": -5,
                "details": long_string
            },
            "health": {
                "score": 150.0,
                "details": long_string
            }
        }
        result = explain_digest_in_plain_language(data)

        summary = result["elements"][0]["content"]
        self.assertIn("Jules舰队当前状态：未知。", summary)
        self.assertIn("当前已入职 0 人（目标 0 人）。", summary)
        self.assertIn("系统健康度评分：100.0%。", summary)

        panel = result["elements"][1]["elements"][0]["content"]
        expected_truncated = "X" * 997 + "..."
        self.assertEqual(panel.count(expected_truncated), 3)

    def test_health_score_negative_boundary(self):
        data = {
            "health": {
                "score": -20.5
            }
        }
        result = explain_digest_in_plain_language(data)
        summary = result["elements"][0]["content"]
        self.assertIn("系统健康度评分：100.0%。", summary)

if __name__ == '__main__':
    unittest.main()
