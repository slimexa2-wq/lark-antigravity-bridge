import unittest
import time
from ultra_modules.partial_markdown_healer_self_healing_guard import PartialMarkdownHealerSelfHealingGuard

class TestPartialMarkdownHealerSelfHealingGuard(unittest.TestCase):
    def setUp(self):
        self.guard = PartialMarkdownHealerSelfHealingGuard()

    def test_normal_content(self):
        content = "This is a **normal** text with a \n```python\nprint('hello')\n```\n and a table:\n| Header |\n| --- |\n| Data |"
        healed = self.guard.heal(content)
        self.assertEqual(healed, content)

    def test_dirty_data_self_healing(self):
        # Unclosed bold
        content = "This is a **dirty text"
        healed = self.guard.heal(content)
        self.assertEqual(healed, "This is a **dirty text**")

        # Unclosed table
        content2 = "| Header1 | Header2 |\n| --- | --- |\n| Data1 | Data2"
        healed2 = self.guard.heal(content2)
        self.assertEqual(healed2, "| Header1 | Header2 |\n| --- | --- |\n| Data1 | Data2 |")

        # Unclosed code block
        content3 = "Some text\n```python\nprint('unclosed')"
        healed3 = self.guard.heal(content3)
        self.assertEqual(healed3, "Some text\n```python\nprint('unclosed')\n```")

    def test_missing_params_fallback(self):
        healed = self.guard.heal()
        self.assertEqual(healed, "")

        healed = self.guard.heal(None)
        self.assertEqual(healed, "")

    def test_extreme_boundary_conditions(self):
        # Truncated JSON inside markdown code block
        content = "```json\n{\"key\": \"value"
        healed = self.guard.heal(content)
        self.assertEqual(healed, "```json\n{\"key\": \"value\"}\n```")

        # Deeply nested unclosed JSON
        content2 = "{\"a\": [{\"b\": {\"c\": \"test"
        healed2 = self.guard.heal(content2)
        self.assertEqual(healed2, "{\"a\": [{\"b\": {\"c\": \"test\"}}]}")

    def test_undo_mechanism(self):
        user_id = "test_user"
        content = "Unclosed **bold"
        healed = self.guard.heal(content, user_id)
        self.assertEqual(healed, "Unclosed **bold**")

        # Undo within window
        undone = self.guard.undo(user_id)
        self.assertEqual(undone, content)

        # Another test for expired window
        content2 = "Another **bold"
        healed2 = self.guard.heal(content2, user_id)
        self.assertEqual(healed2, "Another **bold**")

        # Mock time to simulate expired window
        self.guard.snapshots[user_id].timestamp = time.time() - 6.0
        undone2 = self.guard.undo(user_id)
        self.assertEqual(undone2, healed2) # Should return healed if window expired

if __name__ == '__main__':
    unittest.main()