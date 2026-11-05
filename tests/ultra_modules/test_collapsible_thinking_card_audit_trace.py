import unittest
from ultra_modules.collapsible_thinking_card_audit_trace import CollapsibleThinkingCardAuditTrace

class TestCollapsibleThinkingCardAuditTrace(unittest.TestCase):
    def setUp(self):
        self.builder = CollapsibleThinkingCardAuditTrace()

    def test_normal_inputs(self):
        """Test with valid normal inputs, ensuring no audit logs are generated for cleaning."""
        card = self.builder.build_card(
            conclusion="Here is the conclusion.",
            thinking_process="Step 1... Step 2...",
            title="My Results",
            card_link="https://example.com",
            show_undo=True
        )

        self.assertEqual(card["header"]["title"]["content"], "My Results")
        self.assertEqual(card["elements"][0]["content"], "**结论：**\nHere is the conclusion.")
        self.assertEqual(card["elements"][1]["elements"][0]["content"], "Step 1... Step 2...")
        self.assertEqual(card["card_link"]["url"], "https://example.com")
        self.assertTrue(any(el.get("tag") == "action" for el in card["elements"]))

        # Only empty card_link should NOT generate log. Here, all parameters are perfect strings.
        self.assertEqual(len(self.builder.get_audit_log()), 0)

    def test_missing_parameters(self):
        """Test missing parameters which should trigger default values and audit logs."""
        card = self.builder.build_card()

        self.assertEqual(card["header"]["title"]["content"], "智能推理结果")
        self.assertEqual(card["elements"][0]["content"], "**结论：**\n暂无结论")
        self.assertEqual(card["elements"][1]["elements"][0]["content"], "暂无推理过程")
        self.assertNotIn("card_link", card)

        logs = self.builder.get_audit_log()
        self.assertEqual(len(logs), 4) # conclusion, thinking_process, title, card_link
        self.assertTrue(all(log["reason"] == "missing parameter" for log in logs))

        fields = [log["field"] for log in logs]
        self.assertIn("conclusion", fields)
        self.assertIn("thinking_process", fields)
        self.assertIn("title", fields)
        self.assertIn("card_link", fields)

    def test_dirty_data_self_healing(self):
        """Test with strings containing leading/trailing whitespace which should be cleaned."""
        card = self.builder.build_card(
            conclusion="  Messy conclusion  \n",
            thinking_process="\tMessy process  ",
            title=" Messy title ",
            card_link="  " # This becomes empty after strip, thus falls back to ""
        )

        self.assertEqual(card["header"]["title"]["content"], "Messy title")
        self.assertEqual(card["elements"][0]["content"], "**结论：**\nMessy conclusion")
        self.assertEqual(card["elements"][1]["elements"][0]["content"], "Messy process")
        self.assertNotIn("card_link", card) # Link becomes empty string

        logs = self.builder.get_audit_log()
        self.assertEqual(len(logs), 4) # All 4 parameters are dirty
        reasons = [log["reason"] for log in logs]

        self.assertIn("dirty data cleaned", reasons)
        self.assertIn("empty string", reasons) # Because card_link became empty

    def test_extreme_boundaries(self):
        """Test with non-string objects and objects that raise exceptions on __str__."""
        class Unstringable:
            def __str__(self):
                raise ValueError("Cannot convert to string")

        card = self.builder.build_card(
            conclusion=Unstringable(),
            thinking_process={"complex": "dict"},
            title=12345, # Integer instead of string
            card_link=None
        )

        # Unstringable object should trigger fallback
        self.assertEqual(card["elements"][0]["content"], "**结论：**\n暂无结论")

        # Dict object should be converted to string representation
        self.assertEqual(card["elements"][1]["elements"][0]["content"], "{'complex': 'dict'}")

        # Integer should be converted to string
        self.assertEqual(card["header"]["title"]["content"], "12345")

        logs = self.builder.get_audit_log()

        # conclusion (unstringable), thinking_process (cleaned? wait, str(dict) is cleaned but maybe same), title (cleaned? str(int) same), card_link (missing)
        # Wait, str({"complex": "dict"}) == "{'complex': 'dict'}", it won't be stripped because no spaces around it normally, so no log.
        # However, if any log exists, it should not crash.

        self.assertTrue(any(log["reason"] == "unstringable object" for log in logs))
        self.assertTrue(any(log["reason"] == "missing parameter" and log["field"] == "card_link" for log in logs))

    def test_record_audit_unstringable(self):
        """Test _record_audit fallback for unstringable objects to cover lines 29-30."""
        class Unstringable:
            def __str__(self):
                raise ValueError("Bad")

        # Manually invoke _record_audit to cover the inner except block which
        # couldn't be easily triggered just from build_card since _clean_string
        # intercepts unstringable objects before they get passed to _record_audit
        # except when called with "<unstringable>" which itself IS a string.
        self.builder._record_audit("test", Unstringable(), "cleaned", "test reason")
        logs = self.builder.get_audit_log()
        self.assertEqual(logs[-1]["field"], "test")

    def test_undo_button_toggle(self):
        """Test that show_undo=False hides the undo action block."""
        card = self.builder.build_card(
            conclusion="Test",
            thinking_process="Test",
            title="Test",
            card_link="https://test.com",
            show_undo=False
        )

        action_elements = [el for el in card["elements"] if el.get("tag") == "action"]
        self.assertEqual(len(action_elements), 0)

if __name__ == '__main__':
    unittest.main()
