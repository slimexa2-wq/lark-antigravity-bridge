import unittest
from ultra_modules.mobile_table_digest_formatter_integration_bridge import MobileTableDigestFormatter

class TestMobileTableDigestFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = MobileTableDigestFormatter()

    def test_normal_v2_data(self):
        """Test behavior with properly formatted V2 data."""
        data = [
            {"id": "v2_1", "name": "Item A", "total_amount": 1500.0, "status": "completed", "date": "2023-01-01"},
            {"id": "v2_2", "name": "Item B", "total_amount": 500.0, "status": "pending", "date": "2023-01-02"}
        ]
        result = self.formatter.format_mobile_table_digest(data, include_date=False)
        self.assertEqual(result["metrics"]["total_items"], 2)
        self.assertEqual(result["metrics"]["total_sum"], 2000.0)
        self.assertEqual(result["metrics"]["anomaly_count"], 0)
        self.assertIn("Total Value: 2,000.00", result["digest_text"])
        self.assertIn("✅ All items appear normal.", result["digest_text"])

    def test_auto_map_v1_data(self):
        """Test mapping functionality from V1 schemas to V2."""
        data = [
            {"v1_id": 1, "v1_name": "Old Item X", "v1_amount": 100, "v1_status": "Success", "v1_date": "2022-01-01"},
            {"item_id": 2, "title": "Old Item Y", "amount": 250.5, "state": "Failed"}
        ]
        result = self.formatter.format_mobile_table_digest(data)
        self.assertEqual(result["metrics"]["total_items"], 2)
        self.assertEqual(result["metrics"]["total_sum"], 350.5)

        # Second item should be detected as anomaly due to 'failed' status
        self.assertEqual(result["metrics"]["anomaly_count"], 1)
        self.assertEqual(result["card_metadata"]["anomalies_highlight"][0]["id"], "2")
        self.assertIn("Abnormal status: failed", result["card_metadata"]["anomalies_highlight"][0]["reasons"])

    def test_dirty_data_self_healing(self):
        """Test parsing logic for dirty/invalid string and None values."""
        data = [
            {"id": "d1", "amount": "$1,000.50 ", "status": None},  # Clean string amount, null status
            {"id": None, "amount": "invalid_num", "status": "ERROR"},  # Bad amount, error status
            "invalid_type_not_dict",  # Should be skipped
            {"id": "d3", "amount": None, "name": None, "date": None} # None values
        ]
        result = self.formatter.format_mobile_table_digest(data, default_status="pending", default_amount=10.0)
        self.assertEqual(result["metrics"]["total_items"], 3)  # One item skipped
        self.assertEqual(result["metrics"]["total_sum"], 1020.5) # 1000.50 + 10.0 + 10.0

        anomalies = result["card_metadata"]["anomalies_highlight"]
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["id"], "unknown_id") # Second item
        self.assertIn("Abnormal status: error", anomalies[0]["reasons"])

    def test_missing_parameters_fallback(self):
        """Test the function handles missing kwargs and empty inputs gracefully with defaults."""
        result_empty_list = self.formatter.format_mobile_table_digest(None)
        self.assertEqual(result_empty_list["metrics"]["total_items"], 0)

        # Fallback dictionary to list handling
        result_dict = self.formatter.format_mobile_table_digest({"id": "1", "amount": 100})
        self.assertEqual(result_dict["metrics"]["total_items"], 1)

        # Invalid data type recovery test
        result_invalid = self.formatter.format_mobile_table_digest(123)
        self.assertEqual(result_invalid["metrics"]["total_items"], 0)

        result = self.formatter.format_mobile_table_digest([{}], include_date=True, report_date="2099-12-31")
        self.assertEqual(result["metrics"]["total_items"], 1)
        self.assertEqual(result["metrics"]["total_sum"], 0.0)
        self.assertIn("2099-12-31", result["digest_text"])

    def test_clean_and_map_exception(self):
        """Test exception handling during data mapping."""
        class BadItem:
            def __getitem__(self, key):
                raise Exception("Forced error")

            def get(self, key, default=None):
                raise Exception("Forced error")

        # This will trigger the exception block in format_mobile_table_digest
        class DictSubclassRaisingException(dict):
            def get(self, key, default=None):
                raise Exception("Forced error in get")

        result = self.formatter.format_mobile_table_digest([DictSubclassRaisingException()])
        self.assertEqual(result["metrics"]["total_items"], 0)

    def test_mapped_date_exception(self):
        """Test exception handling during date mapping."""
        class BadDateItem(dict):
            def get(self, key, default=None):
                if key == 'date':
                    # Return an object that raises an exception when str() is called
                    class BadStr:
                        def __str__(self):
                            raise Exception("Forced str error")
                    return BadStr()
                return super().get(key, default)

        result = self.formatter.format_mobile_table_digest([BadDateItem()])
        self.assertEqual(result["metrics"]["total_items"], 1)

    def test_extreme_boundary_and_anomalies(self):
        """Test with extreme boundary values to ensure anomaly highlighting."""
        data = [
            {"id": "ex1", "amount": 1000000.0, "status": "completed"}, # High amount
            {"id": "ex2", "amount": -50.0, "status": "pending"},       # Negative amount
            {"id": "ex3", "amount": 9999.0, "status": "completed"}     # Normal
        ]
        result = self.formatter.format_mobile_table_digest(data, anomaly_high_threshold=10000.0)
        self.assertEqual(result["metrics"]["total_sum"], 1009949.0)

        anomalies = result["card_metadata"]["anomalies_highlight"]
        self.assertEqual(result["metrics"]["anomaly_count"], 2)

        self.assertEqual(anomalies[0]["id"], "ex1")
        self.assertIn("Amount exceeds 10000.0", anomalies[0]["reasons"])

        self.assertEqual(anomalies[1]["id"], "ex2")
        self.assertIn("Negative amount", anomalies[1]["reasons"])

if __name__ == '__main__':
    unittest.main()
