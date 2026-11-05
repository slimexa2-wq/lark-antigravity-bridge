import time
import threading
import concurrent.futures
from ultra_modules.event_lru_idempotency_guard_core_engine import EventLRUIdempotencyGuardCoreEngine

class SyntheticFixtureGenerator:
    @staticmethod
    def generate_normal_data():
        return [
            {"event_id": f"evt_{i}"} for i in range(1000)
        ]

    @staticmethod
    def generate_dirty_data():
        return [
            None,
            123,
            "string instead of dict",
            {},
            {"event_id": None},
            {"message_id": ""},
            {"header": None},
            {"header": "invalid"},
            {"event": None},
            {"event": []},
            # Garbled data
            {"event_id": "\x00\x01\x02"},
            {"message_id": "\x00garbled"},
            # Nesting test
            {"header": {"event_id": "nested_evt_1"}},
            {"event": {"message_id": "nested_msg_1"}}
        ]

    @staticmethod
    def generate_boundary_data():
        # cross year, cross month simulated IDs
        return [
            {"event_id": "evt_20231231_235959"},
            {"event_id": "evt_20240101_000000"},
            {"message_id": "msg_20240229_120000"},
            {"message_id": "msg_20240301_000000"}
        ]

class EventLRUIdempotencyGuardBenchmarkSuite:
    def __init__(self, capacity=1000, workers=50):
        self.engine = EventLRUIdempotencyGuardCoreEngine(capacity=capacity)
        self.workers = workers

    def run_benchmark(self, dataset):
        """
        Runs the idempotency guard check on the dataset concurrently.
        Returns the duration of the entire operation and the average latency.
        """
        latencies = []

        def task(item):
            start = time.perf_counter()
            self.engine.check_and_record(item)
            end = time.perf_counter()
            return (end - start) * 1000  # in ms

        start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = [executor.submit(task, item) for item in dataset]
            for future in concurrent.futures.as_completed(futures):
                latencies.append(future.result())

        end_time = time.perf_counter()

        total_duration = (end_time - start_time) * 1000 # in ms
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        return {
            "total_duration_ms": total_duration,
            "avg_latency_ms": avg_latency,
            "max_latency_ms": max(latencies) if latencies else 0,
            "total_requests": len(dataset),
            "errors": 0  # if we reached here, 0 errors
        }
