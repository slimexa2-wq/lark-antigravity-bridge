import unittest
from ultra_modules.partial_markdown_healer_core_engine import heal_content

class TestPartialMarkdownHealer(unittest.TestCase):

    def test_normal_content(self):
        # Normal complete markdown
        self.assertEqual(heal_content("Hello **world**"), "Hello **world**")
        self.assertEqual(heal_content("```python\nprint(1)\n```"), "```python\nprint(1)\n```")
        self.assertEqual(heal_content('{"a": 1}'), '{"a": 1}')

    def test_missing_params_and_dirty_data(self):
        # Missing param / None
        self.assertEqual(heal_content(), "")
        self.assertEqual(heal_content(None), "")
        self.assertEqual(heal_content(format=None), "")
        # Empty string
        self.assertEqual(heal_content("   "), "   ")
        # Dirty data
        self.assertEqual(heal_content(123), "123")

        class BadObject:
            def __str__(self):
                raise ValueError("Bad")

        self.assertEqual(heal_content(BadObject()), "")

    def test_unclosed_markdown(self):
        # Unclosed code block
        self.assertEqual(heal_content("```python\nprint(1)"), "```python\nprint(1)\n```")
        self.assertEqual(heal_content("```python\n"), "```python\n```")
        self.assertEqual(heal_content("Some text\n```bash\nls -la"), "Some text\n```bash\nls -la\n```")

        # Unclosed bold
        self.assertEqual(heal_content("This is **very important"), "This is **very important**")

        # Unclosed table
        self.assertEqual(heal_content("| Name | Age |\n|---|---|\n| Alice | 25"), "| Name | Age |\n|---|---|\n| Alice | 25|")
        # Table with exact boundary
        self.assertEqual(heal_content("|"), "|")
        self.assertEqual(heal_content("Not a table|"), "Not a table|")

        # Multiple unclosed
        self.assertEqual(heal_content("Here is **bold\n```python\nprint"), "Here is **bold\n```python\nprint\n```**")

    def test_truncated_json(self):
        self.assertEqual(heal_content('{"name": "John", "age": 30, "skills": ["python", "c++'), '{"name": "John", "age": 30, "skills": ["python", "c++"]}')
        self.assertEqual(heal_content('{"key": "value'), '{"key": "value"}')
        self.assertEqual(heal_content('[{"a": 1}, {"b": 2'), '[{"a": 1}, {"b": 2}]')

    def test_json_edge_cases_for_coverage(self):
        # Coverage for stack logic and empty/mismatched brackets
        self.assertEqual(heal_content("}", format="json"), "}")
        self.assertEqual(heal_content("]", format="json"), "]")
        self.assertEqual(heal_content("{]", format="json"), "{]}")
        self.assertEqual(heal_content("[}", format="json"), "[}]")
        self.assertEqual(heal_content('{"a": "b\\"'), '{"a": "b\\""}')
        # format edge cases
        self.assertEqual(heal_content("[]", format=""), "[]")
        self.assertEqual(heal_content("[]", format=123), "[]")
        self.assertEqual(heal_content("[not really json", format="markdown"), "[not really json")

if __name__ == '__main__':
    unittest.main()
