import unittest
from ultra_modules.collapsible_thinking_card_anomaly_radar import CollapsibleThinkingCardAnomalyRadar, build_radar_and_get_card

class TestCollapsibleThinkingCardAnomalyRadar(unittest.TestCase):
    def test_normal_data_silent_pass(self):
        # Normal dataset with no huge variations
        data = [10, 11, 12, 10, 11, 9, 10, 10, 11, 10]
        radar = CollapsibleThinkingCardAnomalyRadar(data)
        result = radar.analyze()

        self.assertEqual(len(result["top_anomalies"]), 0)
        self.assertEqual(len(result["normal_items"]), 10)

        card = radar.generate_feishu_card()
        self.assertEqual(card["header"]["template"], "green")
        self.assertTrue("✅ All 10 items normal" in card["elements"][0]["content"])

    def test_anomaly_detection(self):
        # Dataset with one large anomaly
        # 99 normal items around 10
        data = [10] * 99
        # 1 anomaly
        data.append(100)

        radar = CollapsibleThinkingCardAnomalyRadar(data)
        result = radar.analyze()

        self.assertEqual(len(result["top_anomalies"]), 1)
        self.assertEqual(len(result["normal_items"]), 99)
        self.assertEqual(result["top_anomalies"][0]["value"], 100)
        self.assertEqual(result["top_anomalies"][0]["tag"], "red")

        card = radar.generate_feishu_card()
        self.assertEqual(card["header"]["template"], "red")
        self.assertTrue("🚨 Detected 1 anomalies requiring attention" in card["elements"][0]["content"])

    def test_dirty_data_self_healing(self):
        # Mixed dataset: normal numbers, strings that can be parsed, and unparseable types/Nones
        # Added enough normal numbers so the anomaly stands out (Z > 2.0)
        data = [10, "11", None, "invalid", 12, "13", float('inf'), float('nan'), 10, 10, 11, 1000]

        radar = CollapsibleThinkingCardAnomalyRadar(data)

        # Valid data (length 8): 10, 11.0, 12.0, 13.0, 10, 10, 11, 1000.0 (inf and nan removed, None and "invalid" ignored)
        self.assertEqual(len(radar.clean_data), 8)
        self.assertTrue(1000.0 in radar.clean_data)

        result = radar.analyze()
        self.assertEqual(len(result["top_anomalies"]), 1)
        self.assertEqual(result["top_anomalies"][0]["value"], 1000.0)

    def test_missing_params_fallback(self):
        # Empty initialization, should fallback to empty list and safe defaults without crashing
        card = build_radar_and_get_card()

        self.assertIsNotNone(card)
        self.assertEqual(card["header"]["template"], "green")
        # clean_data falls back to [0.0] if empty
        self.assertTrue("✅ All 1 items normal" in card["elements"][0]["content"])

    def test_extreme_boundary_conditions(self):
        # Empty list
        radar = CollapsibleThinkingCardAnomalyRadar([])
        self.assertEqual(radar.clean_data, [0.0])

        # All same elements (variance = 0)
        radar_same = CollapsibleThinkingCardAnomalyRadar([5, 5, 5, 5, 5])
        res = radar_same.analyze()
        self.assertEqual(len(res["top_anomalies"]), 0)
        # Verify Z-scores are 0 and not crashing with division by zero
        for item in res["normal_items"]:
            self.assertEqual(item["z_score"], 0.0)

    def test_feishu_card_schema(self):
        # Verify the presence of conclusion, collapsible_panel and undo action
        data = [1, 2, 3, 4, 100]
        card = build_radar_and_get_card(data)

        # Verify config
        self.assertEqual(card["config"]["update_multi"], True)

        # Elements structure
        elements = card["elements"]
        self.assertEqual(len(elements), 3)

        # 1. Conclusion (Markdown)
        self.assertEqual(elements[0]["tag"], "markdown")

        # 2. Collapsible Panel
        self.assertEqual(elements[1]["tag"], "collapsible_panel")
        self.assertEqual(elements[1]["header"]["title"]["content"], "Detailed Thinking Process")
        self.assertEqual(elements[1]["elements"][0]["tag"], "markdown")

        # 3. Action button (Undo)
        self.assertEqual(elements[2]["tag"], "action")
        self.assertEqual(elements[2]["actions"][0]["tag"], "button")
        self.assertEqual(elements[2]["actions"][0]["text"]["content"], "Undo Action")
        self.assertEqual(elements[2]["actions"][0]["value"]["action"], "undo")

if __name__ == '__main__':
    unittest.main()
