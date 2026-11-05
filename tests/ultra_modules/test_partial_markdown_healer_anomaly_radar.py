import unittest
import sys
import os

# Add the root directory to PYTHONPATH so that ultra_modules can be imported properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ultra_modules.partial_markdown_healer_anomaly_radar import PartialMarkdownHealerAnomalyRadar

class TestPartialMarkdownHealerAnomalyRadar(unittest.TestCase):
    def setUp(self):
        self.radar = PartialMarkdownHealerAnomalyRadar(fallback_default={"status": "error"})

    def test_normal_data_flow(self):
        # 1. Normal Markdown
        markdown_str = "This is a **bold** text and here is a block:\n```python\nprint('hello')\n```"
        self.assertEqual(self.radar.heal_markdown(markdown_str), markdown_str)

        # 2. Normal JSON
        json_str = '{"key": "value"}'
        self.assertEqual(self.radar.heal_json(json_str), {"key": "value"})

        # 3. Normal Anomaly Data (no anomalies)
        data = [{"id": 1, "value": 10}, {"id": 2, "value": 10}, {"id": 3, "value": 10}]
        result = self.radar.scan_anomalies(data)
        for item in result:
            self.assertEqual(item['radar_status'], 'Green')

    def test_dirty_data_healing(self):
        # 1. Dirty Markdown Healing
        unclosed_bold = "This is **bold"
        self.assertEqual(self.radar.heal_markdown(unclosed_bold), "This is **bold**")

        unclosed_code = "Here is some code:\n```python\nprint('hello')"
        self.assertEqual(self.radar.heal_markdown(unclosed_code), "Here is some code:\n```python\nprint('hello')\n```")

        unclosed_table = "| Col 1 | Col 2 |\n|---|---|\n| Val 1 | Val 2"
        self.assertEqual(self.radar.heal_markdown(unclosed_table), "| Col 1 | Col 2 |\n|---|---|\n| Val 1 | Val 2 |")

        # 2. Dirty JSON Healing
        unclosed_json = '{"key": "value", "list": [1, 2, 3'
        healed_json = self.radar.heal_json(unclosed_json)
        self.assertEqual(healed_json, {"key": "value", "list": [1, 2, 3]})

        unclosed_json_string = '{"key": "value'
        healed_json_string = self.radar.heal_json(unclosed_json_string)
        self.assertEqual(healed_json_string, {"key": "value"})

        # Test case where it completely fails to heal and should return default
        garbage_json = '{"key: value" : '
        self.assertEqual(self.radar.heal_json(garbage_json), {"status": "error"})

        # Test case for JSON with escaped quotes and unmatched closing brace
        json_with_escaped = '{"key": "val\\"ue'
        self.assertEqual(self.radar.heal_json(json_with_escaped), {"key": 'val"ue'})

        json_unmatched = '{"key": "value"}' + ']' # Has unmatched brace/bracket
        self.assertEqual(self.radar.heal_json(json_unmatched), {"status": "error"})

    def test_missing_parameter_fallback(self):
        # 1. Missing parameter in heal_markdown
        self.assertEqual(self.radar.heal_markdown(None), "")
        self.assertEqual(self.radar.heal_markdown(""), "")

        # 2. Missing parameter in heal_json
        self.assertEqual(self.radar.heal_json(None), {"status": "error"})
        self.assertEqual(self.radar.heal_json(""), {"status": "error"})

        # 3. Missing parameter/data in scan_anomalies
        self.assertEqual(self.radar.scan_anomalies(None), [])
        self.assertEqual(self.radar.scan_anomalies([]), [])

        # 4. Missing value key in data
        data_missing_key = [{"id": 1}, {"id": 2}]
        result = self.radar.scan_anomalies(data_missing_key)
        for item in result:
            self.assertEqual(item['radar_status'], 'Green')
            self.assertTrue('Normal' in item['radar_reason'])

        # 5. Missing value mixed in normal data
        data_mixed = [{"id": 1, "value": 10}, {"id": 2, "value": 20}, {"id": 3, "value": 30}, {"id": 4, "value": "dirty"}]
        result = self.radar.scan_anomalies(data_mixed)
        self.assertEqual(result[3]['radar_status'], 'Green')
        self.assertTrue('non-numeric' in result[3]['radar_reason'])

    def test_extreme_boundaries(self):
        # 1. Extreme numbers in radar
        import sys
        extreme_data = [{"id": 1, "value": sys.float_info.max}, {"id": 2, "value": sys.float_info.max}]
        # Should not crash, stdev will be 0
        result = self.radar.scan_anomalies(extreme_data)
        self.assertEqual(result[0]['radar_status'], 'Green')

        # 2. Huge corrupted markdown
        huge_corrupted_md = "```" * 10000
        healed = self.radar.heal_markdown(huge_corrupted_md)
        self.assertEqual(healed.count("```") % 2, 0) # Must be even

    def test_anomaly_radar_flagging(self):
        # Generate a dataset of 1000 normal items
        # Mean around 100, stdev around 10
        import random
        random.seed(42) # For deterministic tests

        data = []
        for i in range(1000):
            # Using random.gauss to generate normal distribution
            val = random.gauss(100, 10)
            data.append({"id": i, "value": val})

        # Add 3 clear anomalies (extreme high/low)
        data.append({"id": 1001, "value": 200}) # High anomaly
        data.append({"id": 1002, "value": 250}) # High anomaly
        data.append({"id": 1003, "value": 0})   # Low anomaly

        result = self.radar.scan_anomalies(data)

        red_count = 0
        green_yellow_count = 0

        for item in result:
            if item['radar_status'] == 'Red':
                red_count += 1
                self.assertTrue('Anomaly detected' in item['radar_reason'])
            else:
                green_yellow_count += 1
                self.assertEqual(item['radar_reason'], 'Normal')

        # With normal distribution, approx 3% should be red.
        # But we added 3 specific massive outliers, and some of the 1000 normal might randomly cross the 2.17 threshold.
        # With seed 42, 1000 normal items -> standard Z-score ~2.17 flags around 1-3%.
        # Let's just assert that red_count is small (e.g., < 50, which is < 5%) and green_yellow is large (> 95%)
        # specifically verifying the 97% silent passing mechanism.

        total = len(result)
        self.assertTrue(red_count > 0, "Should detect at least some anomalies")
        self.assertTrue(red_count < total * 0.05, f"Anomalies should be rare (top ~3%), got {red_count/total*100}%")
        self.assertTrue(green_yellow_count > total * 0.95, "Most items should pass silently")

if __name__ == '__main__':
    unittest.main()
