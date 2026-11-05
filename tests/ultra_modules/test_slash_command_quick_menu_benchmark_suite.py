import unittest
import threading
import time
from ultra_modules.slash_command_quick_menu_benchmark_suite import SlashCommandRouter

class TestSlashCommandQuickMenuBenchmarkSuite(unittest.TestCase):

    def setUp(self):
        self.router = SlashCommandRouter()

    def test_normal_commands(self):
        """Test 1: Normal commands (perfect inputs)."""
        res_zb = self.router.process("/周报", {"user_id": "alice", "year": 2023, "month": 11})
        self.assertEqual(res_zb["matched_command"], "/周报")
        self.assertEqual(res_zb["data"]["period"], "2023-11")

        res_tc = self.router.process("提成", {"user_id": "bob"})
        self.assertEqual(res_tc["matched_command"], "/提成")
        self.assertEqual(res_tc["data"]["amount"], 0.00)

        res_mj = self.router.process("/漫剧 extra args")
        self.assertEqual(res_mj["matched_command"], "/漫剧")
        self.assertEqual(res_mj["data"]["url"], "https://default.app.url/comic")

        res_bs = self.router.process("  /标书  ")
        self.assertEqual(res_bs["matched_command"], "/标书")
        self.assertEqual(res_bs["data"]["template_id"], "TPL-001")

        res_zt = self.router.process("/状态")
        self.assertEqual(res_zt["matched_command"], "/状态")
        self.assertEqual(res_zt["data"]["health"], "OK")

    def test_dirty_data_self_healing(self):
        """Test 2: Dirty data self-healing (None, integers, byte arrays, objects)."""
        # None
        res_none = self.router.process(None)
        self.assertEqual(res_none["matched_command"], "/状态")

        # Integers
        res_int = self.router.process(12345)
        self.assertEqual(res_int["matched_command"], "/状态")

        # Bytes
        res_bytes = self.router.process(b"\xe5\x91\xa8\xe6\x8a\xa5") # "/周报" without slash in utf-8 is 周报
        self.assertEqual(res_bytes["matched_command"], "/周报")

        # Random bytes (invalid utf-8)
        res_bad_bytes = self.router.process(b"\xff\xfe\x00")
        self.assertEqual(res_bad_bytes["matched_command"], "/状态")

        # Custom Object without proper string representation
        class BadObject:
            def __str__(self):
                raise ValueError("Bad string representation")

        res_obj = self.router.process(BadObject())
        self.assertEqual(res_obj["matched_command"], "/状态")

    def test_missing_parameters_fallback(self):
        """Test 3: Missing parameters fallback (empty contexts, cross-year/month boundaries)."""
        # Empty context
        res_empty_ctx = self.router.process("/周报", {})
        self.assertEqual(res_empty_ctx["matched_command"], "/周报")
        self.assertEqual(res_empty_ctx["data"]["period"], "2024-01") # Default year/month
        self.assertEqual(res_empty_ctx["context"]["user_id"], "unknown_user")

        # Invalid year/month
        res_invalid_date = self.router.process("/周报", {"year": "invalid", "month": 13})
        self.assertEqual(res_invalid_date["data"]["period"], "2024-01") # Falls back to 2024-01

        # None as context
        res_none_ctx = self.router.process("/提成", None)
        self.assertEqual(res_none_ctx["context"]["user_id"], "unknown_user")

        # Invalid context type
        res_bad_ctx = self.router.process("/状态", "not a dictionary")
        self.assertEqual(res_bad_ctx["context"]["user_id"], "unknown_user")

    def test_extreme_boundaries(self):
        """Test 4: Extreme boundaries (huge strings, invisible characters)."""
        huge_string = "a" * 10000 + "/周报" + "b" * 10000
        res_huge = self.router.process(huge_string)
        # Should be truncated and likely fall back to /状态 unless it catches the command
        # Based on implementation, max 1000 chars, so it will be just 'a's, resulting in /状态
        self.assertEqual(res_huge["matched_command"], "/状态")
        self.assertTrue(len(res_huge["original_command_cleaned"]) <= 1000)

        invisible_chars = "\x00\x01\x02\x03\x04\x05\x06\x07\x08/周报\x0b\x0c\x0e\x0f"
        res_invisible = self.router.process(invisible_chars)
        self.assertEqual(res_invisible["matched_command"], "/周报")

    def test_high_concurrency_benchmark(self):
        """Test 5: High concurrency benchmark (100 threads sending requests simultaneously)."""
        num_threads = 100
        results = []
        errors = []

        def worker():
            try:
                # A mix of normal and dirty data
                res = self.router.process("/提成", {"user_id": threading.current_thread().name})
                results.append(res)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, name=f"Thread-{i}") for i in range(num_threads)]

        start_time = time.time()
        for t in threads:
            t.start()

        for t in threads:
            t.join()
        end_time = time.time()

        self.assertEqual(len(errors), 0, "No exceptions should occur during concurrent execution")
        self.assertEqual(len(results), num_threads, "All threads should return a result")

        # Check processing time constraint (should be fast, though Python GIL makes threading somewhat sequential,
        # the individual processing_time_ms should be very small)
        for res in results:
            self.assertTrue(res["processing_time_ms"] < 100, f"Processing time too high: {res['processing_time_ms']} ms")

if __name__ == '__main__':
    unittest.main()
