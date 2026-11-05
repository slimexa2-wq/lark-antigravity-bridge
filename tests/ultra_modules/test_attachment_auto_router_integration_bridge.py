import unittest
from ultra_modules.attachment_auto_router_integration_bridge import AttachmentAutoRouter

class TestAttachmentAutoRouterIntegrationBridge(unittest.TestCase):
    def setUp(self):
        self.router = AttachmentAutoRouter()

    def test_normal_routing_and_engine_identification(self):
        # Weekly report by filename
        res = self.router.route_attachment("2023年10月第一周周报.xlsx")
        self.assertEqual(res["engine_key"], "weekly_report")
        self.assertEqual(res["routed_engine"], "周报引擎")

        # Commission by content
        res = self.router.route_attachment("data.csv", content="提成点为5%")
        self.assertEqual(res["engine_key"], "commission")

        # Bidding by filename
        res = self.router.route_attachment("项目A标书.docx")
        self.assertEqual(res["engine_key"], "bidding")

        # Comic by filename
        res = self.router.route_attachment("新漫剧剧本.txt")
        self.assertEqual(res["engine_key"], "comic")

    def test_dirty_data_self_healing(self):
        # None inputs
        res = self.router.route_attachment(None, None, "not_a_dict")
        self.assertEqual(res["engine_key"], "unknown")
        self.assertEqual(res["filename"], "")
        self.assertEqual(res["migrated_metadata"], {"version": "1.0"})

        # Leading/trailing spaces
        res = self.router.route_attachment("  招标书.pdf  ", "  资质要求  ", {"author_name": "  Alice  "})
        self.assertEqual(res["engine_key"], "bidding")
        self.assertEqual(res["filename"], "招标书.pdf")
        self.assertEqual(res["migrated_metadata"]["author"], "  Alice  ")

    def test_missing_parameters_fallback(self):
        # Only filename provided
        res = self.router.route_attachment("周报.txt")
        self.assertEqual(res["engine_key"], "weekly_report")
        self.assertEqual(res["migrated_metadata"], {"version": "2.0"})

        # Unrecognized content
        res = self.router.route_attachment("file.bin")
        self.assertEqual(res["engine_key"], "unknown")
        self.assertEqual(res["routed_engine"], "未匹配")

    def test_extreme_boundary_conditions(self):
        # Empty everything
        res = self.router.route_attachment("", "", {})
        self.assertEqual(res["engine_key"], "unknown")

        # Super long filename
        long_name = "a" * 1000 + "提成.xlsx"
        res = self.router.route_attachment(long_name)
        self.assertEqual(res["engine_key"], "commission")
        self.assertEqual(res["filename"], long_name)

        # Weird extensions
        res = self.router.route_attachment("漫剧.xyz999")
        self.assertEqual(res["engine_key"], "comic")

    def test_schema_version_forward_compatibility(self):
        # Weekly report legacy schema
        res = self.router.route_attachment("周报.doc", metadata={
            "version": "1.0",
            "last_week_done": "Finished feature X",
            "next_week_todo": "Start feature Y",
            "author_name": "Bob"
        })
        self.assertEqual(res["migrated_metadata"]["version"], "2.0")
        self.assertEqual(res["migrated_metadata"]["accomplishments"], "Finished feature X")
        self.assertEqual(res["migrated_metadata"]["plan"], "Start feature Y")
        self.assertEqual(res["migrated_metadata"]["author"], "Bob")
        self.assertNotIn("last_week_done", res["migrated_metadata"])
        self.assertNotIn("next_week_todo", res["migrated_metadata"])
        self.assertNotIn("author_name", res["migrated_metadata"])

        # Commission legacy schema
        res = self.router.route_attachment("销售提成.xls", metadata={
            "sales_volume": 10000,
            "rate": 0.05
        })
        self.assertEqual(res["migrated_metadata"]["total_sales"], 10000)
        self.assertEqual(res["migrated_metadata"]["commission_rate"], 0.05)

if __name__ == "__main__":
    unittest.main()
