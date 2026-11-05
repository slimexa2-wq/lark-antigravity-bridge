import unittest
from ultra_modules.attachment_auto_router_core_engine import route_attachment

class TestAttachmentAutoRouterCoreEngine(unittest.TestCase):

    def test_normal_routing_weekly_report(self):
        # Normal case for WEEKLY_REPORT_ENGINE
        self.assertEqual(route_attachment(file_name="张三_2023_周报.xlsx"), "WEEKLY_REPORT_ENGINE")
        self.assertEqual(route_attachment(file_name="weekly_status.docx"), "WEEKLY_REPORT_ENGINE")
        self.assertEqual(route_attachment(file_content="这是一份汇报材料"), "WEEKLY_REPORT_ENGINE")

    def test_normal_routing_commission(self):
        # Normal case for COMMISSION_ENGINE
        self.assertEqual(route_attachment(file_name="2023年10月提成表.xlsx"), "COMMISSION_ENGINE")
        self.assertEqual(route_attachment(file_name="bonus_calculation.csv"), "COMMISSION_ENGINE")

    def test_normal_routing_bidding_and_comic(self):
        # Normal cases for BIDDING_ENGINE and COMIC_ENGINE
        self.assertEqual(route_attachment(file_name="项目标书.pdf"), "BIDDING_ENGINE")
        self.assertEqual(route_attachment(file_name="bidding_document.doc"), "BIDDING_ENGINE")
        self.assertEqual(route_attachment(file_name="最新漫剧脚本.txt"), "COMIC_ENGINE")
        self.assertEqual(route_attachment(file_name="comic_draft.png"), "COMIC_ENGINE")

    def test_dirty_data_auto_healing(self):
        # Dirty data should be sanitized silently and not raise exceptions
        self.assertEqual(route_attachment(file_name=12345, file_content=["Not a string"]), "UNKNOWN_ENGINE")
        self.assertEqual(route_attachment(file_name=None, file_content=None, metadata="Not a dict"), "UNKNOWN_ENGINE")
        self.assertEqual(route_attachment(file_name="  周报  \n"), "WEEKLY_REPORT_ENGINE")

        # Metadata contains dirty string data but has valid key
        self.assertEqual(route_attachment(metadata={'title': 123}), "UNKNOWN_ENGINE")
        self.assertEqual(route_attachment(metadata={'title': '提成明细'}), "COMMISSION_ENGINE")
        self.assertEqual(route_attachment(metadata={'description': '漫画脚本'}), "COMIC_ENGINE")
        self.assertEqual(route_attachment(metadata={'description': 456}), "UNKNOWN_ENGINE")

    def test_missing_parameters_fallback(self):
        # Missing parameters gracefully fallback
        self.assertEqual(route_attachment(), "UNKNOWN_ENGINE")
        self.assertEqual(route_attachment(file_name="unknown_file.txt"), "UNKNOWN_ENGINE")

    def test_extreme_edge_cases(self):
        # Empty strings
        self.assertEqual(route_attachment(file_name="", file_content=""), "UNKNOWN_ENGINE")
        # Mixed keywords: returns the first match in code logic (WEEKLY_REPORT_ENGINE is first)
        self.assertEqual(route_attachment(file_name="周报_标书.docx"), "WEEKLY_REPORT_ENGINE")
        # Special characters
        self.assertEqual(route_attachment(file_name="!@#$%^&*()_+提成!@#"), "COMMISSION_ENGINE")

if __name__ == '__main__':
    unittest.main()
