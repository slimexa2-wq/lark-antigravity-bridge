import unittest
from ultra_modules.approval_one_tap_callback_batch_pipeline import ApprovalOneTapCallbackBatchPipeline

class TestApprovalOneTapCallbackBatchPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = ApprovalOneTapCallbackBatchPipeline(max_workers=5)

    def test_normal_usage(self):
        records = [
            {"card_id": "card_1", "action": "approve"},
            {"card_id": "card_2", "action": "reject"}
        ]
        result = self.pipeline.process_batch(records)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["summary"]["total"], 2)
        self.assertEqual(result["summary"]["success"], 2)
        self.assertEqual(result["summary"]["error"], 0)
        self.assertEqual(len(result["results"]), 2)

        card_ids = [r["card_id"] for r in result["results"]]
        self.assertIn("card_1", card_ids)
        self.assertIn("card_2", card_ids)

    def test_dirty_data_self_healing(self):
        records = [
            {"card_id": "card_3", "action": "approve", "extra_field": "ignore_me"},
            "this_is_not_a_dict",
            {"card_id": "card_4", "action": "invalid_action"}
        ]
        result = self.pipeline.process_batch(records)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["summary"]["total"], 3)
        self.assertEqual(result["summary"]["success"], 1)
        self.assertEqual(result["summary"]["error"], 2)

        success_results = [r for r in result["results"] if r.get("status") == "success"]
        error_results = [r for r in result["results"] if r.get("status") == "error"]

        self.assertEqual(len(success_results), 1)
        self.assertEqual(success_results[0]["card_id"], "card_3")
        self.assertEqual(len(error_results), 2)

    def test_missing_param_defaults(self):
        records = [
            {"action": "approve"},
            {"card_id": "card_6"}
        ]
        result = self.pipeline.process_batch(records)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["summary"]["total"], 2)
        self.assertEqual(result["summary"]["success"], 1)
        self.assertEqual(result["summary"]["error"], 1)

        success_results = [r for r in result["results"] if r.get("status") == "success"]
        self.assertEqual(success_results[0]["card_id"], "default_missing_id")

    def test_extreme_boundary_and_invalid_input(self):
        result_empty = self.pipeline.process_batch([])
        self.assertEqual(result_empty["status"], "success")
        self.assertEqual(result_empty["summary"]["total"], 0)

        result_none = self.pipeline.process_batch(None)
        self.assertEqual(result_none["status"], "error")

        pipeline_invalid_config = ApprovalOneTapCallbackBatchPipeline(max_workers=-1)
        self.assertEqual(pipeline_invalid_config.max_workers, 10)

    def test_high_throughput_execution(self):
        records = [{"card_id": f"card_{i}", "action": "approve"} for i in range(1000)]
        result = self.pipeline.process_batch(records)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["summary"]["total"], 1000)
        self.assertEqual(result["summary"]["success"], 1000)
        self.assertEqual(result["summary"]["error"], 0)
        self.assertEqual(len(result["results"]), 1000)

if __name__ == '__main__':
    unittest.main()
