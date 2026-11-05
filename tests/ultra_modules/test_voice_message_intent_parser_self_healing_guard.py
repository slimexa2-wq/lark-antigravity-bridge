import unittest
import time
from ultra_modules.voice_message_intent_parser_self_healing_guard import VoiceIntentSelfHealingGuard

class TestVoiceIntentSelfHealingGuard(unittest.TestCase):
    def setUp(self):
        self.guard = VoiceIntentSelfHealingGuard()

    def test_normal_operation(self):
        """Test normal condition: intent extraction with valid keywords."""
        result = self.guard.extract_intent("把这月提成表核一下")

        self.assertIn("task_id", result)
        self.assertEqual(result["intent"], "VERIFY_DOCUMENT")
        self.assertEqual(result["entities"].get("document_type"), "提成表")
        self.assertIn(result["task_id"], self.guard.snapshots)

    def test_dirty_data_self_healing(self):
        """Test dirty data self-healing: remove filler words and punctuations."""
        dirty_input = "呃...那个...把这月提成表核一下吧！！！"
        result = self.guard.extract_intent(dirty_input)

        self.assertEqual(result["intent"], "VERIFY_DOCUMENT")
        self.assertEqual(result["entities"].get("document_type"), "提成表")

    def test_missing_param_fallback(self):
        """Test missing parameter fallback: handles None or invalid types silently."""
        # Test None input
        result1 = self.guard.extract_intent(None)
        self.assertEqual(result1["intent"], "UNKNOWN")
        self.assertEqual(result1["entities"], {})

        # Test integer input (invalid type)
        result2 = self.guard.extract_intent(12345, default_intent="DEFAULT_INTENT")
        self.assertEqual(result2["intent"], "DEFAULT_INTENT")
        self.assertEqual(result2["entities"], {})

        class Unstringable:
            def __str__(self):
                raise Exception("Cannot convert to string")

        result3 = self.guard.extract_intent(Unstringable(), default_intent="FALLBACK")
        self.assertEqual(result3["intent"], "FALLBACK")
        self.assertEqual(result3["entities"], {})

    def test_extreme_boundary_conditions(self):
        """Test extreme boundary conditions: very long strings, empty strings, only fillers."""
        # Empty string
        result_empty = self.guard.extract_intent("    ")
        self.assertEqual(result_empty["intent"], "UNKNOWN")

        # Only filler words
        result_filler = self.guard.extract_intent("那个就是啊嗯")
        self.assertEqual(result_filler["intent"], "UNKNOWN")

        # Very long string without intent
        long_string = "字" * 10000
        result_long = self.guard.extract_intent(long_string)
        self.assertEqual(result_long["intent"], "UNKNOWN")

    def test_undo_mechanism(self):
        """Test one-tap undo mechanism: snapshot active, expiration, and invalid task IDs."""
        # Create a task
        result = self.guard.extract_intent("核对文件")
        task_id = result["task_id"]

        # Undo within window
        undo_result = self.guard.undo_task(task_id)
        self.assertEqual(undo_result["status"], "success")
        self.assertEqual(self.guard.snapshots[task_id]["status"], "cancelled")

        # Test invalid task ID (None)
        invalid_undo_1 = self.guard.undo_task(None)
        self.assertEqual(invalid_undo_1["status"], "failed")
        self.assertEqual(invalid_undo_1["reason"], "invalid_task_id")

        # Test invalid task ID (Not found)
        invalid_undo_2 = self.guard.undo_task("nonexistent-uuid")
        self.assertEqual(invalid_undo_2["status"], "failed")
        self.assertEqual(invalid_undo_2["reason"], "not_found")

        # Test expiration
        result_expire = self.guard.extract_intent("核查")
        task_id_expire = result_expire["task_id"]

        # Simulate time passage
        self.guard.snapshots[task_id_expire]["timestamp"] = time.time() - 6.0
        expire_undo = self.guard.undo_task(task_id_expire)

        self.assertEqual(expire_undo["status"], "failed")
        self.assertEqual(expire_undo["reason"], "expired")
        self.assertEqual(self.guard.snapshots[task_id_expire]["status"], "expired")

if __name__ == '__main__':
    unittest.main()
