import unittest
import asyncio
from unittest.mock import AsyncMock, patch

from ultra_modules.ws_exponential_backoff_batch_pipeline import (
    WSBatchPipeline,
    ExponentialBackoffJitter,
    WSPipelineStateMachine
)

class TestWSExponentialBackoffBatchPipeline(unittest.IsolatedAsyncioTestCase):

    async def test_normal_processing(self):
        """Test case 1: Normal processing of records (no failures)."""
        async def mock_process(item):
            await asyncio.sleep(0.01)
            return f"Processed {item}"

        pipeline = WSBatchPipeline(process_func=mock_process, batch_size=10)
        items = list(range(25))

        result = await pipeline.process_items(items)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["processed"], 25)
        self.assertEqual(len(result["results"]), 25)

        # Check if one result is as expected
        first_success = next(r for r in result["results"] if r["payload"] == 0)
        self.assertEqual(first_success["status"], "success")
        self.assertEqual(first_success["data"], "Processed 0")

        progress = pipeline.get_progress_snapshot()
        self.assertEqual(progress["completed"], 25)
        self.assertEqual(progress["total"], 25)
        self.assertEqual(progress["percentage"], 100.0)

    async def test_dirty_data_self_healing(self):
        """Test case 2: Dirty data/self-healing using exponential backoff retry."""
        fail_count = 0

        async def fragile_process(item):
            nonlocal fail_count
            if fail_count < 3:
                fail_count += 1
                raise ValueError("Temporary failure")
            return f"Healed {item}"

        # Setup state machine directly for this to assert retries easily
        sm = WSPipelineStateMachine(task=fragile_process, max_retries=5, base_delay_ms=10)

        result = await sm.execute("dirty_data")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], "Healed dirty_data")
        self.assertEqual(sm.state, "SUCCESS")
        self.assertEqual(fail_count, 3)

    async def test_missing_parameter_fallback(self):
        """Test case 3: Missing or bad parameter defaults."""
        async def dummy_process(item):
            return item

        # Pass None or invalid values to see if defaults kick in
        pipeline = WSBatchPipeline(
            process_func=dummy_process,
            batch_size=-10,
            max_retries=None,
            base_delay_ms=0
        )

        self.assertEqual(pipeline.batch_size, 50)
        self.assertEqual(pipeline.max_retries, 5)
        self.assertEqual(pipeline.base_delay_ms, 100)

        result = await pipeline.process_items([1, 2, 3])
        self.assertEqual(result["processed"], 3)

    async def test_extreme_boundary_1000_items(self):
        """Test case 4: Boundary testing with 1000 items concurrently."""
        async def fast_process(item):
            # No real IO, just return fast to test throughput logic
            return item * 2

        pipeline = WSBatchPipeline(process_func=fast_process, batch_size=100)
        items = list(range(1000))

        result = await pipeline.process_items(items)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["processed"], 1000)
        self.assertEqual(len(result["results"]), 1000)

        # Verify 1000 items were processed successfully
        successes = [r for r in result["results"] if r["status"] == "success"]
        self.assertEqual(len(successes), 1000)

    async def test_exponential_backoff_retry_simulation_failure(self):
        """Test case 5: Exponential backoff retry simulation (permanent failure)."""
        async def always_fail(item):
            raise RuntimeError("Permanent failure")

        # Mock asyncio.sleep so we don't actually wait
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            sm = WSPipelineStateMachine(task=always_fail, max_retries=3, base_delay_ms=10)
            result = await sm.execute("fail_data")

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error"], "Permanent failure")
            self.assertEqual(sm.state, "FAILED")

            # Should have retried 3 times (so sleep called 3 times)
            self.assertEqual(mock_sleep.call_count, 3)

if __name__ == '__main__':
    unittest.main()
