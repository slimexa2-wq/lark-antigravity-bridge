import unittest
import time
from ultra_modules.mobile_table_digest_formatter_self_healing_guard import MobileTableDigestFormatter

class TestMobileTableDigestFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = MobileTableDigestFormatter()

    def test_normal_data(self):
        data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        result = self.formatter.format_digest(data)
        self.assertEqual(len(result["digest"]), 2)
        self.assertEqual(len(result["anomalies"]), 0)
        self.assertIsNotNone(result["snapshot_id"])

    def test_dirty_data_self_healing(self):
        data = [[1, 2], "invalid", {"a": None}]
        result = self.formatter.format_digest(data)
        self.assertEqual(len(result["digest"]), 3)
        self.assertTrue(any(a["row"] == 2 for a in result["anomalies"]))

    def test_missing_parameter_defaults(self):
        result = self.formatter.format_digest(None)
        self.assertEqual(len(result["digest"]), 0)
        self.assertEqual(result["title"], "Table Digest")

    def test_undo_success(self):
        data = [{"test": "data"}]
        result = self.formatter.format_digest(data)
        snapshot_id = result["snapshot_id"]
        restored = self.formatter.undo(snapshot_id)
        self.assertEqual(restored, data)

    def test_undo_expiration_boundary(self):
        data = [{"test": "data"}]
        result = self.formatter.format_digest(data)
        snapshot_id = result["snapshot_id"]
        # Fast forward time to test expiration
        self.formatter._snapshots[snapshot_id]["timestamp"] -= 6
        restored = self.formatter.undo(snapshot_id)
        self.assertIsNone(restored)

if __name__ == '__main__':
    unittest.main()
