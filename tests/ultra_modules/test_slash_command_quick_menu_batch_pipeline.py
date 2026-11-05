import unittest
import time
import asyncio
from ultra_modules.slash_command_quick_menu_batch_pipeline import SlashCommandBatchRouter

class TestSlashCommandQuickMenuBatchPipeline(unittest.TestCase):

    def setUp(self):
        self.router = SlashCommandBatchRouter()

    def test_normal_batch_processing(self):
        """Test normal batch processing with valid records."""
        records = [
            {"command": "/周报", "payload": {"text": "week 1"}},
            {"command": "/提成", "payload": {"amount": 1000}},
            {"command": "/漫剧", "payload": {"id": 123}}
        ]

        snapshot = self.router.trigger_batch(records)

        # Non-blocking check
        self.assertFalse(snapshot.is_completed)

        # Wait for completion
        time.sleep(0.1)
        self.assertTrue(snapshot.is_completed)
        self.assertEqual(snapshot.success, 3)
        self.assertEqual(snapshot.failed, 0)
        self.assertEqual(len(snapshot.results), 3)

        # Check that results matched commands
        commands = [res["command"] for res in snapshot.results]
        self.assertIn("/周报", commands)
        self.assertIn("/提成", commands)
        self.assertIn("/漫剧", commands)

    def test_dirty_data_self_healing(self):
        """Test dirty data self-healing with invalid types and bad inputs."""
        # Mix of strings, ints, bad dicts
        records = [
            "Just a random string",
            12345,
            {"command": "not_a_slash_command", "payload": "Not a dict"},
            {"random_key": "random_value"}
        ]

        snapshot = self.router.trigger_batch(records)
        time.sleep(0.1)
        self.assertTrue(snapshot.is_completed)
        self.assertEqual(snapshot.success, 4)

        for res in snapshot.results:
            # Should have fallen back to /状态
            self.assertEqual(res["command"], "/状态")
            self.assertIsInstance(res["processed_payload"], dict)

    def test_missing_parameter_fallback(self):
        """Test missing parameter default fallback (empty lists, empty dicts)."""
        snapshot = self.router.trigger_batch([])

        time.sleep(0.1)
        self.assertTrue(snapshot.is_completed)
        self.assertEqual(snapshot.success, 1) # Falls back to 1 item

        res = snapshot.results[0]
        self.assertEqual(res["command"], "/状态")
        self.assertEqual(res["processed_payload"], {})

    def test_extreme_bounds(self):
        """Test with 1000 items to check batch limit and high throughput processing."""
        records = [{"command": "/标书", "payload": {"id": i}} for i in range(1200)]

        # Router should clip it to 1000 items
        snapshot = self.router.trigger_batch(records)
        self.assertEqual(snapshot.total, 1000)

        # Wait a bit longer for 1000 items
        time.sleep(0.5)

        self.assertTrue(snapshot.is_completed)
        self.assertEqual(snapshot.success, 1000)
        self.assertEqual(snapshot.failed, 0)

    def test_non_blocking_snapshot_check(self):
        """Test that the snapshot returns immediately and we can fetch progress."""
        records = [{"command": "/状态", "payload": {}} for _ in range(500)]
        snapshot = self.router.trigger_batch(records)

        # Immediate check
        progress = snapshot.get_progress()
        self.assertEqual(progress["total"], 500)
        # Processed should be 0 (or very low) since it's asynchronous
        self.assertFalse(progress["is_completed"])

        # Wait for completion
        time.sleep(0.3)
        progress = snapshot.get_progress()
        self.assertTrue(progress["is_completed"])
        self.assertEqual(progress["processed"], 500)
        self.assertEqual(progress["success"], 500)

if __name__ == '__main__':
    unittest.main()
