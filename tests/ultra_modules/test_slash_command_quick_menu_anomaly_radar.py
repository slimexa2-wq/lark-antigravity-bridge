import unittest
import math
from ultra_modules.slash_command_quick_menu_anomaly_radar import AnomalyRadar

class TestAnomalyRadar(unittest.TestCase):
    def test_normal_distribution(self):
        """测试正常数据分布：仅提取真正的异常点"""
        radar = AnomalyRadar()
        # 100个数据点，大部分都在100附近
        data = [{"id": f"emp_{i}", "name": f"员工{i}", "value": 100 + (i % 5)} for i in range(97)]
        # 3个极其异常的数据
        data.extend([
            {"id": "emp_97", "name": "提成王", "value": 1000},
            {"id": "emp_98", "name": "摆烂王", "value": -500},
            {"id": "emp_99", "name": "天降奇兵", "value": 800}
        ])

        result = radar.scan(data)

        self.assertEqual(result["status"], "red")
        self.assertTrue(len(result["anomalies"]) > 0)

        # 提成王绝对应该被标红
        anomalies_ids = [a["id"] for a in result["anomalies"]]
        self.assertIn("emp_97", anomalies_ids)
        self.assertIn("emp_98", anomalies_ids)

        # 测试异常分类
        red_anomalies = [a for a in result["anomalies"] if a["status"] == "red"]
        yellow_anomalies = [a for a in result["anomalies"] if a["status"] == "yellow"]

        self.assertTrue(any(a["id"] == "emp_97" for a in red_anomalies))
        self.assertTrue(any(a["id"] == "emp_98" for a in yellow_anomalies))
        self.assertTrue("超出均值水平" in red_anomalies[0]["reason"])

    def test_dirty_data_self_healing(self):
        """测试脏数据自愈：静默处理非法数据而不崩溃"""
        radar = AnomalyRadar()
        dirty_data = [
            {"id": "1", "name": "N/A数据", "value": "N/A"},
            {"id": "2", "name": "空数据"},
            {"id": "3", "name": "字符串数字", "value": "100.5"},
            {"id": "4", "name": "正常数据", "value": 200},
            {"id": "5", "name": "列表数据", "value": [1, 2, 3]},
            {"id": "6", "name": "None数据", "value": None},
            "这不是一个字典",
            None
        ]
        # 添加更多正常数据形成分布
        dirty_data.extend([{"id": f"norm_{i}", "name": f"N{i}", "value": 100} for i in range(10)])

        # 不抛异常即胜利
        result = radar.scan(dirty_data)

        # 字符串 100.5 和 200 应该被正常解析，其他的当做 0
        self.assertTrue(result["normal_count"] > 0)
        self.assertIn(result["status"], ["green", "yellow", "red"])

    def test_missing_param_fallback(self):
        """测试缺参容错：构造函数与数据缺字段"""
        radar = AnomalyRadar(anomaly_threshold="not a float", top_percentile=1.5)

        self.assertEqual(radar.anomaly_threshold, 2.0)
        self.assertEqual(radar.top_percentile, 0.03)

        # 扫描完全空的数据集
        result = radar.scan([])
        self.assertEqual(result["status"], "green")
        self.assertEqual(result["normal_count"], 0)
        self.assertEqual(len(result["anomalies"]), 0)

    def test_boundary_conditions(self):
        """测试极端边界：数据量少、全部一致、标准差为0等"""
        radar = AnomalyRadar()

        # 数据量不足3个
        result = radar.scan([{"id": "1", "value": 100}, {"id": "2", "value": 1000}])
        self.assertEqual(result["status"], "green")
        self.assertEqual(result["normal_count"], 2)

        # 数据全部一致，stdev = 0
        result = radar.scan([{"id": f"x{i}", "value": 50} for i in range(10)])
        self.assertEqual(result["status"], "green")
        self.assertEqual(len(result["anomalies"]), 0)

        # 触发 statistics.StatisticsError (通常是只传入一个或两个值时触发，但是前面已经过滤了 len < 3 的情况，
        # 为了覆盖我们直接在 scan 里面传入一些奇怪的数据，或者 Mock stdev。但是这里我们不想用复杂的 Mock，
        # 直接使用 unittest.mock 来补上这个1%的缺失分支)
        import statistics
        from unittest.mock import patch

        with patch("statistics.stdev", side_effect=statistics.StatisticsError("mocked error")):
            result = radar.scan([{"id": f"x{i}", "value": 50} for i in range(5)])
            self.assertEqual(result["status"], "green")
            self.assertEqual(len(result["anomalies"]), 0)

    def test_outlier_handling_no_top_k(self):
        """测试极端离群点但不在Top K范围内的情况"""
        # top_percentile = 0.01，只取Top 1%
        radar = AnomalyRadar(anomaly_threshold=2.0, top_percentile=0.01)

        data = [{"id": f"n{i}", "value": 100} for i in range(95)]
        # 加入多个离群点，超出Top 1%的数量
        data.extend([
            {"id": "out1", "value": 500},
            {"id": "out2", "value": -400},
            {"id": "out3", "value": 450},
            {"id": "out4", "value": 480}
        ])

        result = radar.scan(data)

        # 由于所有异常点超出了 anomaly_threshold * 1.5 的极端容忍度
        # 所以即使超出了Top K数量(4 > 100*0.01)，也应该被抓出来
        anomalies_ids = [a["id"] for a in result["anomalies"]]
        self.assertIn("out1", anomalies_ids)
        self.assertIn("out2", anomalies_ids)
        self.assertEqual(result["status"], "red")

if __name__ == '__main__':
    unittest.main()
