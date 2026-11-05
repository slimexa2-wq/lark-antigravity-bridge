import unittest
import json
from ultra_modules.mobile_table_digest_formatter_plain_explainer import MobileTableDigestFormatter

class TestMobileTableDigestFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = MobileTableDigestFormatter()

    def test_normal_data_markdown(self):
        """测试正常数据以及默认的Markdown输出格式"""
        data = [
            {"id": 1, "name": "Alice", "sales": 1500, "status": "ok"},
            {"id": 2, "name": "Bob", "sales": 2300, "status": "ok"}
        ]
        result = self.formatter.format(data)

        self.assertIn("## 数据摘要分析", result)
        self.assertIn("🎯 核心摘要", result)
        self.assertIn("1. 数据总览：共处理 2 条有效数据记录。", result)
        self.assertIn("3. 核心指标：[sales] 汇总值为 3800.00。", result)
        self.assertIn("📎 附件下载卡片", result)

    def test_missing_parameters_default_fallback(self):
        """测试缺省参数的默认兜底处理"""
        # data为None，其他参数也是默认
        result = self.formatter.format(data=None)

        self.assertIn("1. 数据总览：当前未接收到有效数据记录。", result)
        self.assertIn("2. 状态评估：暂无业务数据可供分析。", result)
        self.assertIn("3. 核心指标：所有数值指标均为空。", result)
        self.assertIn("未知大小", result)

    def test_dirty_data_self_healing(self):
        """测试脏数据自愈：非列表结构、包含None值"""
        dirty_data_dict = {"status": "error", "message": "fail"}
        # 传递字典，应该能自愈为包含一个元素的列表
        result_json = self.formatter.format(dirty_data_dict, format_type="json")
        parsed = json.loads(result_json)

        self.assertEqual(parsed["title"], "数据摘要分析")
        self.assertIn("1. 数据总览：共处理 1 条有效数据记录。", parsed["digest"][0])

        # 测试包含非字典元素或None元素的列表
        dirty_data_list = [{"val": 10}, None, "string_item", {"status": "ok", "val": 20}]
        result_html = self.formatter.format(dirty_data_list, format_type="html")

        # 应该只处理有效行（包含非空元素的会被转为带_raw的数据，字典会被保留）
        # None会被忽略，剩余3个有效行
        self.assertIn("共处理 3 条有效数据记录", result_html)

    def test_anomaly_detection_with_anomaly_keys(self):
        """测试异常检测逻辑与指定异常键"""
        data = [
            {"id": 1, "stock": 100},
            {"id": 2, "stock": -5},  # 负数异常
            {"id": 3, "stock": 50, "status": "超时"}, # 关键字异常
            {"id": 4, "stock": None} # 空值异常
        ]

        result = self.formatter.format(data, anomaly_keys=["stock"])

        self.assertIn("⚠️ 异常高亮", result)
        self.assertIn("第 2 行发现异常 -> stock: -5", result)
        self.assertIn("第 3 行发现异常 -> status: 超时", result)
        self.assertIn("第 4 行发现异常 -> stock: None", result)

    def test_anomaly_truncation_extreme_boundary(self):
        """测试极端边界：异常信息爆炸时的截断功能"""
        data = [{"id": i, "status": "error"} for i in range(10)]
        result = self.formatter.format(data)

        self.assertIn("第 1 行发现异常", result)
        self.assertIn("第 5 行发现异常", result)
        self.assertNotIn("第 6 行发现异常", result)
        self.assertIn("...及其他 5 项异常隐藏", result)

if __name__ == '__main__':
    unittest.main()
