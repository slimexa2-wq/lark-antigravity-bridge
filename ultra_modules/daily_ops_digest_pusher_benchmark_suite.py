import time
import random
import string
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Tuple
from ultra_modules.daily_ops_digest_pusher_core_engine import generate_daily_digest

class SyntheticFixturesBuilder:
    """
    Builder for generating various extreme and normal cases of data for testing.
    """

    @staticmethod
    def _random_string(length: int) -> str:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def _garbage_string(length: int) -> str:
        # Invalid UTF-8, zero width characters, mojibake
        garbage_chars = [chr(0xFFFD), '\u200b', '', '𠜎', 'こんにちは', '안녕하세요']
        return ''.join(random.choices(garbage_chars, k=length))

    @classmethod
    def normal(cls) -> Dict[str, Any]:
        return {
            "progress": {
                "status": "On Track",
                "details": "All modules are progressing as planned."
            },
            "recruitment": {
                "hired": 5,
                "target": 10,
                "details": "Hired 5 engineers this week."
            },
            "health": {
                "score": 98.5,
                "details": "Minor latency spikes handled."
            },
            "date": "2023-10-15"
        }

    @classmethod
    def dirty_data(cls) -> Dict[str, Any]:
        return {
            "progress": "This should be a dict",
            "recruitment": {
                "hired": cls._garbage_string(10),  # Should be int, use mojibake
                "target": None,
                "details": cls._garbage_string(50)
            },
            "health": {
                "score": "not a float",
                "details": None
            },
            "date": cls._garbage_string(20) # Garbage data for date
        }

    @classmethod
    def default_fallback_missing_params(cls) -> Dict[str, Any]:
        return {}

    @classmethod
    def extreme_boundary(cls) -> Dict[str, Any]:
        return {
            "progress": {
                "status": cls._random_string(100),
                "details": cls._random_string(5000)  # Should trigger truncation
            },
            "recruitment": {
                "hired": -50,
                "target": -100,  # Target should cap at hired
                "details": cls._random_string(5000)
            },
            "health": {
                "score": 150.0,  # Out of bounds, should fallback to 100.0
                "details": cls._random_string(5000)
            },
            "date": "2023-12-31T23:59:59.999Z" # Cross year boundary simulation
        }

    @classmethod
    def cross_year_boundary(cls) -> Dict[str, Any]:
        return {
            "progress": {
                "status": "Year End Transition",
                "details": "Checking system stability during NYE."
            },
            "recruitment": {
                "hired": 100,
                "target": 150,
                "details": "Cross-year recruitment finalized."
            },
            "health": {
                "score": 99.9,
                "details": "System stable across boundaries."
            },
            "date": "2024-01-01T00:00:00.000Z"
        }

    @classmethod
    def null_data(cls) -> Any:
        return None


class BenchmarkSuite:
    """
    Runs performance and stress testing on generate_daily_digest.
    """

    def __init__(self, iterations: int = 1000, concurrency: int = 100):
        self.iterations = iterations
        self.concurrency = concurrency
        self.fixtures = [
            SyntheticFixturesBuilder.normal(),
            SyntheticFixturesBuilder.dirty_data(),
            SyntheticFixturesBuilder.default_fallback_missing_params(),
            SyntheticFixturesBuilder.extreme_boundary(),
            SyntheticFixturesBuilder.cross_year_boundary(),
            SyntheticFixturesBuilder.null_data()
        ]

    def _task(self, index: int) -> bool:
        data = self.fixtures[index % len(self.fixtures)]
        try:
            generate_daily_digest(data)
            return True
        except Exception:
            return False

    def run_benchmark(self) -> Tuple[int, float, float]:
        """
        Runs the benchmark with high concurrency.
        Returns: (successful_calls, total_time, average_time_per_call)
        """
        if self.iterations <= 0:
            return 0, 0.0, 0.0

        success_count = 0
        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            results = executor.map(self._task, range(self.iterations))
            for res in results:
                if res:
                    success_count += 1

        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time = total_time / self.iterations if self.iterations > 0 else 0.0

        return success_count, total_time, avg_time

def run_suite(iterations: int = 1000, concurrency: int = 100) -> dict:
    suite = BenchmarkSuite(iterations, concurrency)
    success, total, avg = suite.run_benchmark()
    return {
        "iterations": iterations,
        "concurrency": concurrency,
        "success": success,
        "total_time_seconds": total,
        "avg_time_seconds": avg
    }

if __name__ == "__main__":
    result = run_suite(10000, 200)
    print(f"Benchmark Results: {result}")
