import unittest
from ultra_modules.attachment_auto_router_anomaly_radar import AttachmentAutoRouterAnomalyRadar

class TestAttachmentAutoRouterAnomalyRadar(unittest.TestCase):
    def setUp(self):
        self.radar = AttachmentAutoRouterAnomalyRadar()

    def test_routing_logic(self):
        """Test file routing logic based on keywords."""
        self.assertEqual(self.radar.determine_route("2023年Q3周报.xlsx"), "WeeklyReportEngine")
        self.assertEqual(self.radar.determine_route("10月提成明细.csv"), "CommissionEngine")
        self.assertEqual(self.radar.determine_route("A项目标书v2.docx"), "BidDocumentEngine")
        self.assertEqual(self.radar.determine_route("热血漫剧脚本.txt"), "ComicEngine")
        self.assertEqual(self.radar.determine_route("unknown_file.pdf"), "DefaultFallbackEngine")
        self.assertEqual(self.radar.determine_route(None), "DefaultFallbackEngine")

    def test_normal_execution_and_top_3_percent_highlighting(self):
        """Test normal execution with a dataset large enough to test top 1% RED and next 2% YELLOW."""
        # Generate 100 normal data points around 100
        data_points = [100.0 + (i % 5) for i in range(97)]
        # Add 3 clear anomalies: 2 extreme (top 1% conceptually for 100 items), 1 moderate (next 2%)
        data_points.extend([1000.0, 950.0, 500.0])

        result = self.radar.process("data.csv", data_points)
        scan_results = result["anomaly_scan_results"]

        self.assertEqual(len(scan_results), 100)

        red_count = sum(1 for item in scan_results if item["status"] == "RED")
        yellow_count = sum(1 for item in scan_results if item["status"] == "YELLOW")
        green_count = sum(1 for item in scan_results if item["status"] == "GREEN")

        # With n=100: red_threshold=max(1, ceil(1))=1 (top 1). yellow_threshold=max(1, ceil(3))=3 (top 3)
        # Top 1 gets RED. Top 2 and 3 get YELLOW. Rest GREEN.
        self.assertEqual(red_count, 1)
        self.assertEqual(yellow_count, 2)
        self.assertEqual(green_count, 97)

        # Verify reasons are human readable
        red_items = [item for item in scan_results if item["status"] == "RED"]
        self.assertIn("高危异常", red_items[0]["reason"])

        green_items = [item for item in scan_results if item["status"] == "GREEN"]
        self.assertIn("系统静默放行", green_items[0]["reason"])

    def test_dirty_data_self_healing(self):
        """Test self-healing for dirty data like strings with commas, malformed dicts, and invalid types."""
        dirty_data = [
            "1,234.56",         # String with comma
            {"value": "  999 "},# Dict with string value and spaces
            "invalid_str",      # Unparseable string
            {"id": "test"},     # Dict missing 'value'
            True,               # Boolean (should be ignored, not treated as 1.0)
            None,               # None value
            42                  # Valid int
        ]

        results = self.radar.scan_anomalies(dirty_data)
        self.assertEqual(len(results), 7)

        self.assertEqual(results[0]["healed_value"], 1234.56)
        self.assertEqual(results[1]["healed_value"], 999.0)

        # Invalid data should gracefully fall back to GREEN silently
        self.assertEqual(results[2]["status"], "GREEN")
        self.assertEqual(results[3]["status"], "GREEN")
        self.assertEqual(results[4]["status"], "GREEN")
        self.assertEqual(results[5]["status"], "GREEN")

    def test_default_fallbacks_for_missing_parameters(self):
        """Test default fallbacks when input is completely missing or None."""
        result = self.radar.process()
        self.assertEqual(result["routed_engine"], "DefaultFallbackEngine")
        self.assertEqual(result["anomaly_scan_results"], [])

        result_empty_list = self.radar.process(data_points=[])
        self.assertEqual(result_empty_list["anomaly_scan_results"], [])

    def test_extreme_boundary_conditions(self):
        """Test extreme boundaries: Inf, NaN, single element, all same elements."""
        import math

        # Inf and NaN
        data = [float('inf'), float('nan'), 10, 20, 30]
        results = self.radar.scan_anomalies(data)
        self.assertEqual(len(results), 5)
        self.assertEqual(results[0]["status"], "GREEN") # Handled gracefully as invalid
        self.assertEqual(results[1]["status"], "GREEN")

        # Single element
        results_single = self.radar.scan_anomalies([42])
        self.assertEqual(len(results_single), 1)
        self.assertEqual(results_single[0]["status"], "GREEN")

        # All identical elements (std_dev = 0)
        results_identical = self.radar.scan_anomalies([10, 10, 10, 10, 10])
        self.assertEqual(len(results_identical), 5)
        for res in results_identical:
            self.assertEqual(res["status"], "GREEN")

if __name__ == '__main__':
    unittest.main()
