import unittest
import json
from ultra_modules.mobile_table_digest_formatter_anomaly_radar import MobileTableDigestFormatterAnomalyRadar

class TestMobileTableDigestFormatterAnomalyRadar(unittest.TestCase):
    def setUp(self):
        self.radar = MobileTableDigestFormatterAnomalyRadar()

    def test_normal_execution(self):
        data = [
            {"name": "A", "value": 10},
            {"name": "B", "value": 11},
            {"name": "C", "value": 10.5},
            {"name": "D", "value": 9},
            {"name": "E", "value": 10},
            {"name": "F", "value": 10},
            {"name": "G", "value": 10},
            {"name": "H", "value": 10},
            {"name": "I", "value": 10},
            {"name": "J", "value": 10},
        ]
        result_json = self.radar.format_table(data, "test_token")
        result = json.loads(result_json)

        self.assertEqual(result["type"], "template")
        self.assertEqual(result["elements"][0]["tag"], "markdown")
        self.assertIn("Total items: 10", result["elements"][0]["content"])
        self.assertIn("Anomalies: ", result["elements"][0]["content"])

        self.assertEqual(result["elements"][1]["tag"], "collapsible_panel")
        self.assertIn("View Anomalies", result["elements"][1]["header"]["title"]["content"])

    def test_dirty_data_healing(self):
        data = [
            {"name": "A", "value": "10"}, # String value
            {"name": "B", "value": 10},
            {"name": "C", "value": None}, # Missing value
            {"name": "D"}, # No value key
            {"name": "E", "value": "invalid"}, # Invalid string
            "Not a dict",
            {"value": 10} # Missing name
        ]

        result_json = self.radar.format_table(data, "test_token")
        result = json.loads(result_json)

        self.assertIn("Total items: 3", result["elements"][0]["content"])

    def test_missing_parameters(self):
        result_json = self.radar.format_table()
        result = json.loads(result_json)

        self.assertIn("Total items: 0", result["elements"][0]["content"])
        self.assertIn("Anomalies: 0", result["elements"][0]["content"])
        self.assertEqual(result["elements"][2]["actions"][0]["value"]["file_token"], "default_token")

    def test_empty_data_boundaries(self):
        data = []
        result_json = self.radar.format_table(data, "test_token")
        result = json.loads(result_json)

        self.assertIn("Total items: 0", result["elements"][0]["content"])

        data2 = [{"name": "A", "value": 10}, {"name": "B", "value": 10}]
        result_json2 = self.radar.format_table(data2, "test_token")
        result2 = json.loads(result_json2)

        self.assertIn("Total items: 2", result2["elements"][0]["content"])
        self.assertIn("Anomalies: 0", result2["elements"][0]["content"])

    def test_high_volume_anomaly_detection(self):
        data = [{"name": f"Item{i}", "value": 10} for i in range(100)]
        data.append({"name": "Anomaly1", "value": 100})

        result_json = self.radar.format_table(data, "test_token")
        result = json.loads(result_json)

        self.assertIn("Total items: 101", result["elements"][0]["content"])
        self.assertIn("Anomalies: 1", result["elements"][0]["content"])
        self.assertEqual(result["elements"][1]["header"]["title"]["content"], "View Anomalies (1)")

        anomaly_text = result["elements"][1]["elements"][0]["content"]
        self.assertIn("**Anomaly1**", anomaly_text)
        self.assertIn("100", anomaly_text)
        self.assertIn("is significantly higher than average", anomaly_text)

if __name__ == '__main__':
    unittest.main()
