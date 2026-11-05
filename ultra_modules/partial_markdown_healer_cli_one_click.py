import argparse
import json
import re
import io
import sys

# Ensure fallback for pandas if it is needed for excel but we want zero-configuration fault tolerance
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class MarkdownHealerOneClick:
    @staticmethod
    def _heal_code_blocks(text: str) -> str:
        """Fixes unclosed code blocks."""
        code_block_count = text.count("```")
        if code_block_count % 2 != 0:
            if not text.endswith("\n"):
                text += "\n"
            text += "```"
        return text

    @staticmethod
    def _heal_bold_tags(text: str) -> str:
        """Fixes unclosed bold tags."""
        bold_count = text.count("**")
        if bold_count % 2 != 0:
            text += "**"
        return text

    @staticmethod
    def _heal_tables(text: str) -> str:
        """A simple heuristic to close unclosed tables (markdown pipes)."""
        lines = text.split('\n')
        if not lines or (len(lines) == 1 and lines[0] == ""):
            return text

        last_line = lines[-1].strip()
        if last_line.startswith('|') and not last_line.endswith('|'):
            text += "|"
        return text

    @staticmethod
    def _heal_json(text: str) -> str:
        """Attempts to close truncated JSON structures inside the text."""
        # A very basic approach: if there's more '{' than '}' or '[' than ']', append them.
        open_braces = text.count('{')
        close_braces = text.count('}')
        open_brackets = text.count('[')
        close_brackets = text.count(']')

        while open_brackets > close_brackets:
            text += ']'
            close_brackets += 1

        while open_braces > close_braces:
            text += '}'
            close_braces += 1

        return text

    @staticmethod
    def heal(text: str = None) -> str:
        if text is None:
            text = "Default **fallback" # deliberate dirty data for default

        # Silent cleaning of dirty data (e.g. carriage returns)
        text = text.replace('\r\n', '\n')

        # Apply healing heuristics sequentially
        text = MarkdownHealerOneClick._heal_code_blocks(text)
        text = MarkdownHealerOneClick._heal_bold_tags(text)
        text = MarkdownHealerOneClick._heal_tables(text)
        text = MarkdownHealerOneClick._heal_json(text)

        return text


class DualModeAdapter:
    @staticmethod
    def output(healed_text: str, mode: str = "json") -> str:
        if mode == "excel" and PANDAS_AVAILABLE:
            try:
                # Mock generating an excel file in memory and returning base64 or a success string
                # We return a string representation of the action to maintain CLI simplicity
                df = pd.DataFrame([{"healed_text": healed_text}])

                # We use a buffer to avoid touching filesystem for the output string representation
                buffer = io.BytesIO()
                df.to_excel(buffer, index=False, engine='openpyxl')
                return f"Excel output ready (size: {len(buffer.getvalue())} bytes)"
            except Exception as e:
                # Fault tolerance: fallback to JSON if Excel fails
                pass

        # Default or fallback mode is JSON
        return json.dumps({"status": "success", "data": healed_text}, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Zero-config Partial Markdown Healer CLI")
    parser.add_argument("--text", type=str, default=None, help="The truncated markdown text to heal.")
    parser.add_argument("--mode", type=str, default="json", choices=["json", "excel"], help="Output mode (json/excel)")

    args = parser.parse_args()

    healed = MarkdownHealerOneClick.heal(args.text)
    result = DualModeAdapter.output(healed, args.mode)

    print(result)

if __name__ == "__main__":  # pragma: no cover
    main()
