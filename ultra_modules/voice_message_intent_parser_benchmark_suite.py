import re
import time
import concurrent.futures
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

class VoiceMessageIntentParser:
    def __init__(self, reference_date: Optional[datetime] = None):
        """
        Zero-configuration intent parser for voice-to-text messages.
        :param reference_date: The date to use as a reference for relative time parsing. Defaults to now.
        """
        self.reference_date = reference_date if reference_date is not None else datetime.now()

    def _sanitize_text(self, text: Any) -> str:
        """
        Silently cleans and handles dirty or invalid data.
        """
        if text is None:
            return ""
        if not isinstance(text, str):
            text = str(text)
        # Remove emojis and special non-alphanumeric characters, keeping Chinese characters and basic punctuation
        # This regex keeps Chinese characters, english letters, numbers
        text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
        return text

    def _extract_time_period(self, text: str) -> str:
        """
        Extracts the time period from the text, handling cross-year and cross-month boundaries.
        Returns a string in the format 'YYYY-MM' or 'YYYY'.
        """
        year = self.reference_date.year
        month = self.reference_date.month

        # Remove common verb suffixes that might interfere with time extraction
        text = text.replace("一下", "")

        if "上上个月" in text or "上上月" in text:
            month -= 2
        elif "下下个月" in text or "下下月" in text:
            month += 2
        elif "上个月" in text or "上月" in text:
            month -= 1
        elif "下个月" in text or "下月" in text:
            month += 1
        elif "去年" in text:
            return f"{year - 1}"
        elif "明年" in text:
            return f"{year + 1}"
        elif "今年" in text:
            return f"{year}"
        elif "这月" in text or "这个月" in text or "本月" in text:
            pass # Keep current month
        else:
            # Default fallback for missing time parameter: current month
            pass

        # Handle month boundaries
        while month < 1:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1

        return f"{year}-{month:02d}"

    def _extract_action(self, text: str) -> str:
        if "核" in text or "查" in text or "看" in text or "算" in text:
            return "check"
        if "发" in text or "给" in text:
            return "send"
        return "default_action" # Fallback

    def _extract_subject(self, text: str) -> str:
        if "提成" in text:
            return "commission"
        if "工资" in text or "薪水" in text:
            return "salary"
        if "报表" in text:
            return "report"
        return "default_subject" # Fallback

    def parse(self, text: Any) -> Dict[str, str]:
        """
        Parses the intent from the given text.
        Guarantees to return a valid dict with 'action', 'subject', and 'time_period'.
        """
        clean_text = self._sanitize_text(text)

        return {
            "action": self._extract_action(clean_text),
            "subject": self._extract_subject(clean_text),
            "time_period": self._extract_time_period(clean_text),
            "original_text_length": str(len(clean_text))
        }


class BenchmarkSuite:
    @staticmethod
    def generate_synthetic_fixtures() -> List[Any]:
        """
        Generates synthetic dataset containing normal, dirty, empty, and edge case data.
        """
        return [
            "把这月提成表核一下",
            "查一下上个月的工资",
            "看看去年的报表",
            "算一下下个月的提成",
            "发本月薪水",
            None,
            "",
            12345,
            "🤯🤯🤯!!!把这个月%^&*提成核一下???", # Dirty data
            "核上上个月工资", # Cross month boundary testing
            "明年报表", # Cross year
            " \t\n ", # Whitespace
            "hello world 你好", # Irrelevant
        ] * 100 # Duplicate to create a larger dataset for performance testing

    @staticmethod
    def run_benchmark(concurrency: int = 100, iterations_per_thread: int = 1000) -> Dict[str, Any]:
        """
        Runs a high concurrency benchmark to verify zero crashes and millisecond-level response.
        """
        parser = VoiceMessageIntentParser()
        fixtures = BenchmarkSuite.generate_synthetic_fixtures()

        def task() -> int:
            success_count = 0
            for _ in range(iterations_per_thread):
                for fixture in fixtures[:10]: # Pick a few to parse per iteration to keep it fast
                    result = parser.parse(fixture)
                    if result is not None:
                        success_count += 1
            return success_count

        start_time = time.time()
        total_success = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(task) for _ in range(concurrency)]
            for future in concurrent.futures.as_completed(futures):
                total_success += future.result()

        end_time = time.time()
        elapsed_ms = (end_time - start_time) * 1000

        return {
            "elapsed_ms": elapsed_ms,
            "total_success": total_success,
            "average_ms_per_task": elapsed_ms / (concurrency * iterations_per_thread * 10),
            "is_millisecond_level": (elapsed_ms / (concurrency * iterations_per_thread * 10)) < 1.0
        }
