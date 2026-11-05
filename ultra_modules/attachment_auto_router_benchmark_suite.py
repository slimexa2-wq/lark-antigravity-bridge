import time
import re
import random
import string
import datetime
import concurrent.futures
from typing import Dict, Any, Optional

class AttachmentAutoRouter:
    """
    Routes dropped Excel/Word/TXT files in Lark group to corresponding engines.
    Engines: 'weekly_report', 'commission', 'tender', 'comic_drama', 'unknown'
    """

    def __init__(self, default_engine: str = "unknown"):
        self.default_engine = default_engine

    def _heal_filename(self, filename: Any) -> str:
        """Self-healing for dirty filenames."""
        if filename is None or not isinstance(filename, str):
            return "unnamed_file.txt"

        # Remove control characters and non-printable characters
        cleaned = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', filename).strip()
        if not cleaned:
            return "unnamed_file.txt"
        return cleaned

    def _extract_date_context(self, text: str) -> datetime.date:
        """Extracts date from text or defaults to today. Handles cross-year/month logic."""
        match = re.search(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', text)
        if match:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            try:
                # Validates leap years and cross-year/month boundaries natively
                return datetime.date(year, month, day)
            except ValueError:
                pass
        return datetime.date.today()

    def route(self, filename: Any = None, content_preview: Any = None, file_size: Any = None) -> Dict[str, Any]:
        """Routes the file and returns routing context with zero-crash guarantees."""
        start_time = time.time()

        # Fallbacks & Self-healing
        safe_filename = self._heal_filename(filename)
        safe_content = str(content_preview) if content_preview is not None else ""
        try:
            safe_size = int(file_size) if file_size is not None else 0
            if safe_size < 0:
                safe_size = 0
        except (ValueError, TypeError):
            safe_size = 0

        combined_text = (safe_filename + " " + safe_content).lower()

        # Routing evaluation
        engine = self.default_engine
        if any(kw in combined_text for kw in ["周报", "weekly", "汇报"]):
            engine = "weekly_report"
        elif any(kw in combined_text for kw in ["提成", "commission", "bonus", "工资"]):
            engine = "commission"
        elif any(kw in combined_text for kw in ["标书", "tender", "bidding", "采购"]):
            engine = "tender"
        elif any(kw in combined_text for kw in ["漫剧", "comic", "drama", "剧本"]):
            engine = "comic_drama"

        # Extract date context
        date_context = self._extract_date_context(combined_text)

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "engine": engine,
            "filename": safe_filename,
            "date_context": date_context.isoformat(),
            "processed_size": safe_size,
            "elapsed_ms": elapsed_ms,
            "status": "success"
        }

class BenchmarkSuite:
    """Benchmark suite for validating high concurrency and extreme edge cases."""

    def __init__(self, router: AttachmentAutoRouter):
        self.router = router

    def generate_synthetic_fixture(self) -> Dict[str, Any]:
        """Generates random, potentially dirty data for extreme boundary testing."""
        is_dirty = random.random() < 0.3
        is_missing = random.random() < 0.2

        keywords = ["周报", "提成", "标书", "漫剧", "unknown_text"]
        # Includes cross-year (2023-12-31 to 2024-01-01), leap year (2024-02-29), invalid dates (2023-13-45)
        dates = ["2023-12-31", "2024-01-01", "2024-02-29", "2023-13-45", ""]

        filename = random.choice(keywords) + "_" + random.choice(dates)
        if is_dirty:
            filename += "\x00\x08" + "".join(random.choices(string.punctuation, k=5))
        if is_missing:
            filename = None

        content = "".join(random.choices(string.ascii_letters + string.digits, k=100))
        if is_dirty:
            content += " 提成 " # add routing keyword in dirty content

        return {
            "filename": filename,
            "content_preview": content,
            "file_size": random.randint(-100, 10000) if is_dirty else random.randint(100, 10000)
        }

    def run_benchmark(self, concurrency: int = 1000) -> Dict[str, Any]:
        """Runs a high-concurrency benchmark with synthetic fixtures ensuring zero crashes and fast response."""
        fixtures = [self.generate_synthetic_fixture() for _ in range(concurrency)]

        start_time = time.time()
        results = []

        # High concurrency evaluation
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(concurrency, 100)) as executor:
            future_to_fixture = {
                executor.submit(self.router.route, **fix): fix for fix in fixtures
            }
            for future in concurrent.futures.as_completed(future_to_fixture):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    results.append({"status": "error", "error": str(e)})

        total_time_ms = (time.time() - start_time) * 1000
        success_count = sum(1 for r in results if r.get("status") == "success")
        error_count = len(results) - success_count
        avg_routing_time_ms = sum(r.get("elapsed_ms", 0) for r in results if r.get("status") == "success") / (success_count or 1)

        return {
            "total_requests": concurrency,
            "success_count": success_count,
            "error_count": error_count,
            "total_time_ms": total_time_ms,
            "avg_routing_time_ms": avg_routing_time_ms,
            "zero_crash": error_count == 0,
            "millisecond_response": avg_routing_time_ms < 50
        }
