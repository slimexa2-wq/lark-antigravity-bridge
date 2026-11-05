import concurrent.futures
import json
import re
from typing import List, Dict, Any, Generator, Optional


class PartialMarkdownHealerBatchPipeline:
    """
    A high-throughput batch pipeline for silently healing partial markdown outputs
    and truncated JSON strings. It automatically closes unclosed code blocks,
    bold formatting, tables, and attempts to parse incomplete JSON.
    """

    def __init__(self, max_workers: int = 10, default_timeout: float = 5.0):
        self.max_workers = max_workers
        self.default_timeout = default_timeout

    def _heal_bold(self, text: str) -> str:
        """Heals unclosed bold (**)."""
        count = text.count("**")
        if count % 2 != 0:
            text += "**"
        return text

    def _heal_code_blocks(self, text: str) -> str:
        """Heals unclosed code blocks (```)."""
        count = text.count("```")
        if count % 2 != 0:
            if not text.endswith("\n"):
                text += "\n"
            text += "```"
        return text

    def _heal_tables(self, text: str) -> str:
        """Heals incomplete markdown tables."""
        lines = text.split('\n')
        if not lines:
            return text

        last_line = lines[-1].strip()

        # Heuristic: if it's clearly part of a table (starts with '|') but not closed
        if last_line.startswith('|') and not last_line.endswith('|'):
            # It's an unclosed row.
            lines[-1] = lines[-1] + "|"

        return '\n'.join(lines)

    def _heal_json(self, text: str) -> str:
        """Attempts to heal truncated JSON if the text looks like JSON."""
        stripped = text.strip()
        if not (stripped.startswith("{") or stripped.startswith("[")):
            return text

        try:
            json.loads(stripped)
            return text
        except json.JSONDecodeError:
            pass

        # Heuristic state machine to balance brackets/braces/quotes
        in_string = False
        escape = False
        stack = []

        for char in stripped:
            if escape:
                escape = False
                continue
            if char == '\\' and in_string:
                escape = True
                continue

            if char == '"':
                in_string = not in_string
            elif not in_string:
                if char == '{':
                    stack.append('}')
                elif char == '[':
                    stack.append(']')
                elif char in ('}', ']'):
                    if stack and stack[-1] == char:
                        stack.pop()

        healed_text = text
        if in_string:
            healed_text += '"'

        while stack:
            healed_text += stack.pop()

        # Try to validate the healed text
        try:
            json.loads(healed_text)
            return healed_text
        except json.JSONDecodeError:
            # If our heuristic failed, return the original text
            return text

    def heal_single(self, text: Optional[str] = None) -> str:
        """
        Heals a single markdown/JSON string.
        """
        if text is None:
             return ""

        # 1. JSON healing (if it looks like pure JSON)
        text = self._heal_json(text)

        # 2. Bold healing
        text = self._heal_bold(text)

        # 3. Table healing
        text = self._heal_tables(text)

        # 4. Code block healing
        text = self._heal_code_blocks(text)

        return text

    def process_batch(self, items: List[str]) -> List[str]:
        """
        Processes a batch of items concurrently.
        """
        if not items:
            return []

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Keep order
            future_to_index = {executor.submit(self.heal_single, item): i for i, item in enumerate(items)}
            results = [""] * len(items)
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result(timeout=self.default_timeout)
                except Exception as e:
                    # Fallback to original or empty string on error to avoid blocking
                    results[index] = str(items[index]) if items[index] is not None else ""
        return results

    def stream_process(self, items: List[str]) -> Generator[Dict[str, Any], None, None]:
        """
        Processes items and yields progress snapshots.
        """
        if not items:
            yield {"progress": 1.0, "completed": 0, "total": 0, "results": []}
            return

        total = len(items)
        completed = 0
        current_results = [""] * total

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_index = {executor.submit(self.heal_single, item): i for i, item in enumerate(items)}

            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    current_results[index] = future.result(timeout=self.default_timeout)
                except Exception:
                    current_results[index] = str(items[index]) if items[index] is not None else ""

                completed += 1
                yield {
                    "progress": completed / total,
                    "completed": completed,
                    "total": total,
                    "results": current_results.copy() # snapshot
                }
