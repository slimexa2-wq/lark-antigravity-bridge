import json
import math
import re
from typing import Any, Dict, List, Optional, Union

class PartialMarkdownHealerExportFormatter:
    """
    A standalone module that heals truncated JSON and partial markdown components (code blocks, tables, bold text).
    Replaces NaN and None with default values (like 0), ensures exported data has `comments=0`,
    and generates a 3-line simple report text for one-click copy.
    """

    def __init__(self, default_value: Union[int, float] = 0):
        """
        Initialize the formatter with a default value for missing or invalid numeric fields.
        """
        self.default_value = default_value

    def _heal_json(self, raw_json: str) -> dict:
        """
        Heals truncated JSON strings by completing unclosed strings, balancing arrays and objects.
        """
        if not raw_json or not raw_json.strip():
            return {}

        text = raw_json.strip()

        # Fast path
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to heal by analyzing characters
        in_string = False
        escape = False

        stack = []

        for i, char in enumerate(text):
            if escape:
                escape = False
                continue

            if char == '\\':
                escape = True
                continue

            if char == '"':
                in_string = not in_string
                continue

            if not in_string:
                if char in '{[':
                    stack.append(char)
                elif char in '}]':
                    if stack:
                        expected = '{' if char == '}' else '['
                        if stack[-1] == expected:
                            stack.pop()

        # Heal string
        healed_text = text
        if in_string:
            healed_text += '"'

        # Remove trailing comma if any
        healed_text = re.sub(r',\s*$', '', healed_text)

        # Close open brackets/braces
        while stack:
            open_char = stack.pop()
            close_char = '}' if open_char == '{' else ']'
            healed_text += close_char

        try:
            return json.loads(healed_text)
        except json.JSONDecodeError:
            # Last resort fallback if still malformed
            return {}

    def _heal_markdown(self, markdown_text: str) -> str:
        """
        Heals partial markdown components like unclosed code blocks, unclosed bold text, and truncated tables.
        """
        if not markdown_text:
            return ""

        text = markdown_text

        # Heal code blocks
        code_block_count = len(re.findall(r'^```', text, re.MULTILINE))
        if code_block_count % 2 != 0:
            if not text.endswith('\n'):
                text += '\n'
            text += '```\n'

        # Heal bold text (**text)
        bold_count = text.count('**')
        if bold_count % 2 != 0:
            text += '**'

        # Heal tables
        # If there's a table header and separator but truncated rows, we ensure it looks ok
        # A simple check: if the last line has '|' but doesn't end with '|', and it's part of a table
        lines = text.split('\n')
        if lines:
            last_line = lines[-1]
            if '|' in last_line and not last_line.strip().endswith('|'):
                # Check if it looks like a table row
                if re.match(r'^\|?.*\|.*', last_line):
                    lines[-1] = last_line + '|'
                    text = '\n'.join(lines)

        return text

    def _clean_data(self, data: Any) -> Any:
        """
        Recursively replaces NaN and None with self.default_value.
        """
        if data is None:
            return self.default_value

        if isinstance(data, float):
            if math.isnan(data) or math.isinf(data):
                return self.default_value
            return data

        if isinstance(data, dict):
            return {k: self._clean_data(v) for k, v in data.items()}

        if isinstance(data, list):
            return [self._clean_data(v) for v in data]

        return data

    def process(self, input_json: Optional[str] = None, input_markdown: Optional[str] = None) -> Dict[str, Any]:
        """
        Main entry point.
        Processes input JSON and Markdown, cleans data, ensures comments=0, and generates report text.
        """
        raw_json = input_json if input_json is not None else "{}"
        raw_markdown = input_markdown if input_markdown is not None else ""

        parsed_data = self._heal_json(raw_json)
        cleaned_data = self._clean_data(parsed_data)

        # Ensure it's a dict to append to
        if not isinstance(cleaned_data, dict):
            cleaned_data = {"data": cleaned_data}

        # Force comments=0
        cleaned_data["comments"] = 0

        healed_markdown = self._heal_markdown(raw_markdown)

        # Generate 3-line simple report text
        # Line 1: Status
        # Line 2: Processed Items
        # Line 3: Markdown Snippet (truncated)
        items_count = len(cleaned_data) - 1 # excluding the comments key
        preview = healed_markdown.replace('\n', ' ')[:30] + ('...' if len(healed_markdown) > 30 else '')

        report_text = f"Status: Success\nProcessed Data Items: {items_count}\nPreview: {preview if preview else 'None'}"

        return {
            "data": cleaned_data,
            "markdown": healed_markdown,
            "report_text": report_text
        }
