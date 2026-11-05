import unittest
from ultra_modules.daily_ops_digest_pusher_batch_pipeline import DailyOpsDigestPusherBatchPipeline

class TestDailyOpsDigestPusherBatchPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = DailyOpsDigestPusherBatchPipeline(max_workers=5)

    def test_normal_flow(self):
        """测试正常流程：处理10条正常记录"""
        records = [
            {"title": f"Jules舰队节点{i}", "progress": 80, "health_score": 95, "status": "running"}
            for i in range(10)
        ]
        snapshot = self.pipeline.process_batch(records)

        self.assertEqual(snapshot["total"], 10)
        self.assertEqual(snapshot["processed"], 10)
        self.assertEqual(snapshot["success_count"], 10)
        self.assertEqual(snapshot["failed_count"], 0)
        self.assertEqual(len(snapshot["results"]), 10)

        # 验证结果内容
        for res in snapshot["results"]:
            self.assertTrue(res["success"])
            self.assertIsNotNone(res["data"])
            self.assertEqual(res["data"]["progress"], 80)
            self.assertEqual(res["data"]["health_score"], 95)

    def test_dirty_data_self_healing(self):
        """测试脏数据自愈：处理越界、类型错误数据"""
        records = [
            {"title": "节点1", "progress": 150, "health_score": -10},  # 越界
            {"title": "节点2", "progress": "not_a_number", "health_score": None}, # 类型错误
            "完全不是字典的字符串" # 非字典结构
        ]

        snapshot = self.pipeline.process_batch(records)

        self.assertEqual(snapshot["total"], 3)
        self.assertEqual(snapshot["success_count"], 3)

        # 找各个结果验证
        results_data = [res["data"] for res in snapshot["results"]]

        # 找越界的自愈结果
        node1 = next((r for r in results_data if r["title"] == "节点1"), None)
        self.assertIsNotNone(node1)
        self.assertEqual(node1["progress"], 100) # 150被修正为100
        self.assertEqual(node1["health_score"], 0) # -10被修正为0

        # 找类型错误的自愈结果
        node2 = next((r for r in results_data if r["title"] == "节点2"), None)
        self.assertIsNotNone(node2)
        self.assertEqual(node2["progress"], 0) # 修正为0
        self.assertEqual(node2["health_score"], 100) # 修正为100

        # 找非字典的自愈结果
        non_dict = next((r for r in results_data if r["title"] == "无标题"), None)
        self.assertIsNotNone(non_dict)
        self.assertEqual(non_dict["progress"], 0)
        self.assertEqual(non_dict["health_score"], 100)

    def test_missing_parameter_fallback(self):
        """测试缺参默认兜底：传入None或缺少关键字段"""
        # 测试 process_batch 参数为 None
        snapshot = self.pipeline.process_batch(None)
        self.assertEqual(snapshot["total"], 0)

        # 测试字典缺少关键字段
        records = [{}]
        snapshot2 = self.pipeline.process_batch(records)
        self.assertEqual(snapshot2["total"], 1)
        self.assertEqual(snapshot2["success_count"], 1)

        data = snapshot2["results"][0]["data"]
        self.assertEqual(data["title"], "无标题")
        self.assertEqual(data["progress"], 0)
        self.assertEqual(data["health_score"], 100)
        self.assertEqual(data["status"], "unknown")
        self.assertEqual(data["content"], "暂无内容")

    def test_extreme_boundary_empty(self):
        """测试极端边界：空批次"""
        snapshot = self.pipeline.process_batch([])
        self.assertEqual(snapshot["total"], 0)
        self.assertEqual(snapshot["processed"], 0)
        self.assertEqual(snapshot["success_count"], 0)
        self.assertEqual(snapshot["failed_count"], 0)
        self.assertEqual(len(snapshot["results"]), 0)

    def test_extreme_boundary_large_input(self):
        """测试极端边界：1000条记录批量处理"""
        # 为了测试快点执行完，虽然支持1000，但保证不超时
        num_records = 1000
        records = [
            {"title": f"大规模节点{i}", "progress": 50, "health_score": 100}
            for i in range(num_records)
        ]

        snapshot = self.pipeline.process_batch(records)
        self.assertEqual(snapshot["total"], num_records)
        self.assertEqual(snapshot["processed"], num_records)
        self.assertEqual(snapshot["success_count"], num_records)
        self.assertEqual(snapshot["failed_count"], 0)
        self.assertEqual(len(snapshot["results"]), num_records)

if __name__ == '__main__':
    unittest.main()
