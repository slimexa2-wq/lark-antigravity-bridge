import unittest
import math
from ultra_modules.rate_limit_429_queue_anomaly_radar import RateLimit429AnomalyRadar

class TestRateLimit429AnomalyRadar(unittest.TestCase):
    def setUp(self):
        self.radar = RateLimit429AnomalyRadar()

    def test_normal_data(self):
        # Generate 100 normal items
        items = [{"id": i, "queue_time_ms": 100 + (i % 10)} for i in range(100)]
        result = self.radar.analyze_queues(items)
        self.assertEqual(result["status"], "green")
        self.assertEqual(result["normal_items_count"], 100)
        self.assertEqual(len(result["top_anomalies"]), 0)

    def test_self_healing_dirty_data(self):
        # Mix of valid and invalid data
        items = [
            {"id": 1, "queue_time_ms": "150"},  # string instead of int
            {"id": 2, "queue_time_ms": -50},    # negative
            {"id": 3, "queue_time_ms": "abc"},  # non-numeric string
            {"id": 4, "queue_time_ms": float('inf')}, # inf
            {"id": 5, "queue_time_ms": float('nan')}, # nan
            {"id": 6, "queue_time_ms": None},   # None
            "completely invalid item" # Not even a dict
        ]

        # In `_clean_and_heal_data`:
        # "150" -> 150.0
        # -50 -> 0.0
        # "abc" -> 0.0
        # inf -> 0.0
        # nan -> 0.0
        # None -> 0.0
        # string -> 0.0

        result = self.radar.analyze_queues(items)

        # One anomaly expected because 150 is the only high value,
        # others are 0. The top 3% of 7 items is 1 item.
        # Mean = 150 / 7 = 21.4. Z-score for 150 is positive.
        self.assertEqual(len(result["top_anomalies"]), 1)
        self.assertEqual(result["top_anomalies"][0]["queue_time_ms"], 150.0)
        self.assertEqual(result["top_anomalies"][0]["reason"], "排队时间过长，可能需要人工关注")
        self.assertEqual(result["normal_items_count"], 6)

    def test_missing_parameter_fallback(self):
        # Missing `queue_time_ms` key
        items = [{"id": i} for i in range(5)]
        result = self.radar.analyze_queues(items)
        self.assertEqual(result["status"], "green")
        self.assertEqual(result["normal_items_count"], 5)
        self.assertEqual(len(result["top_anomalies"]), 0)

    def test_extreme_boundaries(self):
        # Empty list
        result1 = self.radar.analyze_queues([])
        self.assertEqual(result1["status"], "green")
        self.assertEqual(result1["normal_items_count"], 0)
        self.assertEqual(len(result1["top_anomalies"]), 0)

        # Invalid type for list
        result2 = self.radar.analyze_queues(None)
        self.assertEqual(result2["status"], "green")

        # Single item
        result3 = self.radar.analyze_queues([{"id": 1, "queue_time_ms": 500}])
        self.assertEqual(result3["status"], "green")
        self.assertEqual(result3["normal_items_count"], 1)
        self.assertEqual(len(result3["top_anomalies"]), 0)

        # All items same queue time
        items_same = [{"id": i, "queue_time_ms": 200} for i in range(50)]
        result4 = self.radar.analyze_queues(items_same)
        self.assertEqual(result4["status"], "green")
        self.assertEqual(result4["normal_items_count"], 50)
        self.assertEqual(len(result4["top_anomalies"]), 0)

        # Test 100% coverage missing line 48 in `_calculate_z_scores`
        # We need to trigger `_calculate_z_scores([])` which happens if `items` is not empty but `cleaned_items` is empty?
        # No, `_clean_and_heal_data` will return a list of same length.
        # But `_calculate_z_scores` might be called with `[]` if `analyze_queues` doesn't guard against it.
        # However, `analyze_queues` has:
        # if not items or not isinstance(items, list): return ...
        # Therefore, `_calculate_z_scores([])` is currently unreachable from `analyze_queues`.
        # To get 100% coverage, we can call it directly.
        self.assertEqual(RateLimit429AnomalyRadar._calculate_z_scores([]), [])

    def test_top_3_percent_detection(self):
        # 100 items: 97 normal, 3 huge anomalies
        items = [{"id": i, "queue_time_ms": 100} for i in range(97)]
        items.append({"id": 97, "queue_time_ms": 5000})
        items.append({"id": 98, "queue_time_ms": 5200})
        items.append({"id": 99, "queue_time_ms": 5500})

        result = self.radar.analyze_queues(items)

        self.assertEqual(len(result["top_anomalies"]), 3)
        self.assertEqual(result["normal_items_count"], 97)
        # 3 out of 100 hits the cap, so it should be red
        self.assertEqual(result["status"], "red")

        # Verify reasons and ordering (descending by score, so 5500 is first)
        self.assertEqual(result["top_anomalies"][0]["queue_time_ms"], 5500)
        self.assertEqual(result["top_anomalies"][0]["reason"], "排队时间过长，可能需要人工关注")
        self.assertEqual(result["top_anomalies"][1]["queue_time_ms"], 5200)
        self.assertEqual(result["top_anomalies"][2]["queue_time_ms"], 5000)

    def test_status_red_condition(self):
        # Create a situation where anomalies > 10%
        # Actually our algorithm says top 3% count is max(1, ceil(total * 0.03))
        # Wait, if we only select top 3% as anomalies, len(anomalies) can never be >= total_items * 0.1
        # Let's adjust the logic in the main code or just realize it's impossible with current logic
        # if max top is 3%.
        # Let's check the code: top_3_percent_count = int(math.ceil(total_items * 0.03))
        # If total_items = 5, ceil(0.15) = 1.
        # anomalies can be 1. total_items * 0.1 = 0.5.
        # So len(anomalies) = 1 > 0.5. It will be "red".

        items = [{"id": i, "queue_time_ms": 100} for i in range(4)]
        items.append({"id": 4, "queue_time_ms": 5000}) # 1 anomaly out of 5

        result = self.radar.analyze_queues(items)

        # 1 anomaly out of 5 items. 1 >= 5 * 0.1 (0.5), so status should be red.
        self.assertEqual(result["status"], "red")
        self.assertEqual(len(result["top_anomalies"]), 1)

if __name__ == '__main__':
    unittest.main()
