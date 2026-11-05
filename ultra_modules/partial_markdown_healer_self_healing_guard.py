import time
import json
import re

class Snapshot:
    def __init__(self, original_content, healed_content, timestamp):
        self.original_content = original_content
        self.healed_content = healed_content
        self.timestamp = timestamp

class PartialMarkdownHealerSelfHealingGuard:
    def __init__(self):
        self.snapshots = {}
        self.UNDO_WINDOW_SECONDS = 5.0

    def _heal_json(self, text: str) -> str:
        text = text.strip()
        if not text:
            return "{}"

        stack = []
        in_string = False
        escape = False
        for char in text:
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
                if char == '{':
                    stack.append('}')
                elif char == '[':
                    stack.append(']')
                elif char in '}]':
                    if stack and stack[-1] == char:
                        stack.pop()

        healed_text = text
        if in_string:
            healed_text += '"'

        healed_text = healed_text.rstrip()
        if healed_text.endswith(','):
            healed_text = healed_text[:-1]

        while stack:
            healed_text += stack.pop()

        return healed_text

    def _heal_bold(self, text: str) -> str:
        if text.count('**') % 2 != 0:
            text += '**'
        return text

    def _heal_table(self, text: str) -> str:
        lines = text.split('\n')
        if not lines:
            return text
        last_line = lines[-1].strip()
        if last_line.startswith('|') and not last_line.endswith('|'):
            lines[-1] = lines[-1] + ' |'
        return '\n'.join(lines)

    def _heal_code_blocks(self, text: str) -> str:
        if text.count('```') % 2 != 0:
            last_idx = text.rfind('```')
            first_line_end = text.find('\n', last_idx)
            if first_line_end != -1:
                lang = text[last_idx+3:first_line_end].strip()
                if lang.lower() == 'json':
                    json_content = text[first_line_end+1:]
                    healed_json = self._heal_json(json_content)
                    text = text[:first_line_end+1] + healed_json

            if not text.endswith('\n'):
                text += '\n'
            text += '```'
        return text

    def heal(self, content: str = "", user_id: str = "default_user") -> str:
        if content is None:
            content = ""

        healed = content

        # Handle pure JSON
        if healed.strip().startswith('{') or healed.strip().startswith('['):
            try:
                json.loads(healed)
            except json.JSONDecodeError:
                healed = self._heal_json(healed)
        else:
            # Handle markdown components
            healed = self._heal_bold(healed)
            healed = self._heal_table(healed)
            healed = self._heal_code_blocks(healed)

        self.snapshots[user_id] = Snapshot(
            original_content=content,
            healed_content=healed,
            timestamp=time.time()
        )

        return healed

    def undo(self, user_id: str = "default_user") -> str:
        """
        Revert to original content if within 5 seconds window,
        otherwise return the healed content (or empty if no snapshot).
        """
        snapshot = self.snapshots.get(user_id)
        if not snapshot:
            return ""

        if time.time() - snapshot.timestamp <= self.UNDO_WINDOW_SECONDS:
            del self.snapshots[user_id]
            return snapshot.original_content

        return snapshot.healed_content
