import time
import random
import uuid
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from .adaptive_stream_throttler_core_engine import process_stream_event

class SyntheticFixtureGenerator:
    """
    Generates synthetic datasets for testing the adaptive stream throttler.
    Includes normal flow, dirty data, ultra-high concurrency, and time boundaries.
    """

    @staticmethod
    def generate_normal_dataset(size: int = 100) -> List[Dict[str, Any]]:
        """Generates standard sequential events."""
        return [{'seq': i, 'data': f'normal_payload_{i}'} for i in range(1, size + 1)]

    @staticmethod
    def generate_dirty_dataset(size: int = 100) -> List[Any]:
        """Generates a mix of valid, invalid, and missing fields."""
        data = []
        for i in range(size):
            r = random.random()
            if r < 0.2:
                data.append("not a dict")
            elif r < 0.4:
                data.append({'seq': str(i), 'data': 'string_seq'}) # String sequence
            elif r < 0.6:
                data.append({'data': 'missing_seq'}) # Missing sequence
            elif r < 0.8:
                data.append({'seq': None, 'data': 'none_seq'}) # None sequence
            else:
                data.append({'seq': i, 'data': f'valid_{i}'}) # Valid
        return data

    @staticmethod
    def generate_cross_boundary_dataset() -> List[Dict[str, Any]]:
        """Generates events with edge case boundary timings (not standardly used but helpful)."""
        # Cross year/month boundaries simulate by time manipulating externally,
        # here we return a dataset to be processed at those specific simulated times.
        return [{'seq': i, 'data': f'boundary_{i}'} for i in range(1, 10)]

class AdaptiveStreamThrottlerBenchmarkSuite:
    """
    Benchmark suite to validate zero-crash and millisecond responsiveness
    under extreme datasets and edge cases.
    """

    def __init__(self, concurrency: int = 50):
        self.concurrency = concurrency

    def run_benchmark(self, dataset: List[Any], start_time_ms: int = None) -> Dict[str, Any]:
        """
        Runs the standard sequential benchmark and measures throughput and correctness.
        """
        if start_time_ms is None:
            start_time_ms = int(time.time() * 1000)

        state = {}
        processed = 0
        emitted = 0
        errors = 0

        start_exec = time.time()

        for idx, event in enumerate(dataset):
            try:
                # Advance simulated time
                simulated_time = start_time_ms + (idx * 50)  # 50ms interval between events
                state, should_emit, cleaned_event = process_stream_event(state, event, simulated_time)
                processed += 1
                if should_emit:
                    emitted += 1
            except Exception:
                errors += 1

        end_exec = time.time()
        elapsed_ms = (end_exec - start_exec) * 1000

        return {
            'processed': processed,
            'emitted': emitted,
            'errors': errors,
            'elapsed_ms': elapsed_ms,
            'avg_response_ms': elapsed_ms / processed if processed > 0 else 0
        }

    def run_stress_test(self, dataset: List[Any]) -> Dict[str, Any]:
        """
        Runs ultra-high concurrency stress test on the processing logic.
        Validates thread-safety/zero-crash even if state isn't perfectly synchronized
        in standard tests without a lock (since core engine is pure function, we
        simulate concurrent calls on shared state by updating cautiously).
        """
        state = {}
        processed = 0
        errors = 0

        start_exec = time.time()

        # Note: core engine is a pure function returning new state.
        # In real usage, a lock is needed to update the central state.
        # Here we just want to ensure `process_stream_event` doesn't crash on dirty data
        # when called concurrently.
        def worker(event):
            # Using current time
            return process_stream_event(state, event)

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = [executor.submit(worker, evt) for evt in dataset]
            for future in as_completed(futures):
                try:
                    res = future.result()
                    processed += 1
                except Exception:
                    errors += 1

        end_exec = time.time()
        elapsed_ms = (end_exec - start_exec) * 1000

        return {
            'processed': processed,
            'errors': errors,
            'elapsed_ms': elapsed_ms,
            'avg_response_ms': elapsed_ms / processed if processed > 0 else 0
        }
