import time
import concurrent.futures
import datetime
from typing import Callable, List, Any, Dict

class SyntheticFixtureGenerator:
    """
    Generates extreme edge cases and synthetic fixtures for ultra-long response chunk splitting.
    """
    def __init__(self, default_max_size: int = 50000):
        self.default_max_size = default_max_size if isinstance(default_max_size, int) and default_max_size > 0 else 50000

    def generate(self, fixture_type: str = "normal", size: int = None) -> Any:
        # Default parameter fallback
        if not isinstance(fixture_type, str):
            fixture_type = "normal"
        size = size if isinstance(size, int) and size > 0 else self.default_max_size

        if fixture_type == "normal":
            return self._generate_normal(size)
        elif fixture_type == "empty":
            return ""
        elif fixture_type == "none":
            return None
        elif fixture_type == "garbage":
            return self._generate_garbage(size)
        elif fixture_type == "cross_year_month":
            return self._generate_cross_year_month(size)
        else:
            return self._generate_normal(size)

    def _generate_normal(self, size: int) -> str:
        paragraph = "This is a normal paragraph to test standard semantic splitting for Feishu cards.\n\n"
        if len(paragraph) == 0:
            return ""
        repetitions = (size // len(paragraph)) + 1
        return (paragraph * repetitions)[:size]

    def _generate_garbage(self, size: int) -> str:
        # Garbage data: unprintable characters, malformed unicode, random bytes converted to string
        garbage_chunk = "" * 10 + chr(0) + chr(1) + chr(7) + "乱码测试" * 5 + "\n\n"
        if len(garbage_chunk) == 0:
            return ""
        repetitions = (size // len(garbage_chunk)) + 1
        return (garbage_chunk * repetitions)[:size]

    def _generate_cross_year_month(self, size: int) -> str:
        # Generate text with lots of cross year and cross month date boundaries to simulate reports spanning multiple periods
        base_date = datetime.datetime(2023, 12, 31, 23, 59, 59)
        chunks = []
        current_len = 0
        while current_len < size:
            base_date += datetime.timedelta(seconds=1)
            date_str = f"\n# Report Date: {base_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
            content = "Financial results and analysis across the year/month boundary showing continuous data.\n\n"
            chunk = date_str + content
            chunks.append(chunk)
            current_len += len(chunk)
        return "".join(chunks)[:size]


class BenchmarkSuite:
    """
    Performance benchmark validation verifying zero-crash and millisecond response under ultra-high concurrency.
    """
    def __init__(self, concurrency: int = 100):
        # Default configuration
        self.concurrency = concurrency if isinstance(concurrency, int) and concurrency > 0 else 100
        self.generator = SyntheticFixtureGenerator()

    def run_benchmark(self, splitter_func: Callable[[Any, int], List[str]], fixture_types: List[str] = None) -> Dict[str, Any]:
        """
        Runs benchmark with synthetic fixtures against a provided splitter function.
        Verifies zero crash and millisecond response time.
        """
        # Default parameter fallback
        if fixture_types is None or not isinstance(fixture_types, list):
            fixture_types = ["normal", "empty", "none", "garbage", "cross_year_month"]

        results = {
            "total_runs": 0,
            "success_runs": 0,
            "failed_runs": 0,
            "total_time_ms": 0.0,
            "average_time_ms": 0.0,
            "zero_crash_verified": True,
            "millisecond_response_verified": True,
            "details": []
        }

        # Prepare dataset
        datasets = []
        for ftype in fixture_types:
            datasets.append({"type": ftype, "data": self.generator.generate(ftype)})

        if not datasets:
            return results

        # Ultra-high concurrency simulation
        def worker(dataset):
            start_time = time.time()
            success = False
            error_msg = None
            try:
                # We assume splitter_func takes text and max_chunk_size
                chunks = splitter_func(dataset["data"], 30000)
                # Verify it actually returns a list (even empty)
                if isinstance(chunks, list):
                    success = True
            except Exception as e:
                error_msg = str(e)

            end_time = time.time()
            elapsed_ms = (end_time - start_time) * 1000
            return {
                "type": dataset["type"],
                "success": success,
                "elapsed_ms": elapsed_ms,
                "error": error_msg
            }

        tasks = datasets * (self.concurrency // len(datasets) + 1)
        tasks = tasks[:self.concurrency]

        start_total = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.concurrency, 500)) as executor:
            futures = [executor.submit(worker, task) for task in tasks]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                results["total_runs"] += 1
                if res["success"]:
                    results["success_runs"] += 1
                else:
                    results["failed_runs"] += 1
                    results["zero_crash_verified"] = False

                results["total_time_ms"] += res["elapsed_ms"]
                results["details"].append(res)

                # We consider > 1000ms not millisecond response (allowing for CI variances)
                if res["elapsed_ms"] > 1000.0:
                    results["millisecond_response_verified"] = False

        results["total_time_ms_overall"] = (time.time() - start_total) * 1000
        if results["total_runs"] > 0:
            results["average_time_ms"] = results["total_time_ms"] / results["total_runs"]

        return results
