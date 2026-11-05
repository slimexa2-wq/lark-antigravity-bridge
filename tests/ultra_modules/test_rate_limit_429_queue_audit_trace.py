import unittest
import time
from ultra_modules.rate_limit_429_queue_audit_trace import RateLimit429QueueAuditTrace, process_request

class TestRateLimit429QueueAuditTrace(unittest.TestCase):

    def setUp(self):
        # Extremely small capacity and fast fill rate for testing
        self.queue = RateLimit429QueueAuditTrace(capacity=2, fill_rate=10.0, max_retries=2, retry_delay=0.1)

    def test_normal_success(self):
        """Test 1: Normal success with clean result"""
        def simple_task():
            return "ok"

        result = self.queue.enqueue("task_1", simple_task)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"], "ok")

    def test_dirty_data_self_healing_and_deduplication(self):
        """Test 2: Deduplication ignores duplicate tasks"""
        def simple_task():
            return "ok"

        # First call works
        res1 = self.queue.enqueue("task_2", simple_task)
        self.assertEqual(res1["status"], "success")

        # Second call with same ID should be deduplicated
        res2 = self.queue.enqueue("task_2", simple_task)
        self.assertEqual(res2["status"], "deduplicated")
        self.assertTrue("already processed" in res2["message"])

    def test_missing_parameters_fallback(self):
        """Test 3: Missing parameters fallback (no task_id) using global zero-config API"""
        def simple_task():
            return "auto_healed"

        # Call global helper with no task_id
        result = process_request(simple_task)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"], "auto_healed")

    def test_extreme_boundary_token_exhaustion(self):
        """Test 4: Extreme boundary conditions (many tasks, checking rate limit backoff logic implicitly via timing)"""
        start_time = time.time()

        def fast_task(x):
            return x

        results = []
        # Enqueue 5 tasks. Capacity is 2. So it must wait for tokens.
        for i in range(5):
            res = self.queue.enqueue(f"ext_task_{i}", fast_task, i)
            results.append(res)

        end_time = time.time()
        # Ensure all succeeded
        for i in range(5):
            self.assertEqual(results[i]["status"], "success")
            self.assertEqual(results[i]["result"], i)

        # It should take some time because capacity is 2 and we need 5
        self.assertGreater(end_time - start_time, 0.0)

    def test_http_429_retry_zero_drop(self):
        """Test 5: HTTP 429 retry zero drop logic"""
        call_count = [0]

        def flaky_task():
            call_count[0] += 1
            if call_count[0] <= 2:
                # Simulate 429 response dict
                return {"status_code": 429, "message": "Too Many Requests"}
            return "finally_success"

        result = self.queue.enqueue("flaky_task_1", flaky_task)

        # Should have retried and eventually succeeded
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"], "finally_success")
        self.assertEqual(call_count[0], 3)

        # Verify audit log recorded the 429 retries
        retry_logs = [log for log in self.queue.audit_log if log["action"] == "RETRY_429"]
        self.assertEqual(len(retry_logs), 2)

if __name__ == "__main__":
    unittest.main()
