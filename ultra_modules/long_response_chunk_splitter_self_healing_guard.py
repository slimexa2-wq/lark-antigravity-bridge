import time
from typing import List, Optional, Any, Dict

class LongResponseChunkSplitter:
    def __init__(self, default_max_length: int = 2000):
        self.default_max_length = default_max_length
        self._snapshots: List[Dict[str, Any]] = []

    def split_and_snapshot(self, text: Any = None, max_length: Any = None) -> List[str]:
        """
        Split a long response into chunks based on semantic boundaries,
        and save a snapshot for the 5-second undo mechanism.
        Silent self-healing for invalid inputs is enforced.
        """
        # Self-healing for max_length
        if max_length is None or not isinstance(max_length, int) or max_length <= 0:
            max_length = self.default_max_length

        # Self-healing for text
        if text is None:
            text = ""
        elif not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                text = ""

        chunks = self._smart_chunk(text, max_length)

        # Snapshot for one-click undo
        self._snapshots.append({
            "timestamp": time.time(),
            "original_text": text,
            "chunks": chunks,
            "max_length": max_length
        })

        return chunks

    def _smart_chunk(self, text: str, max_length: int) -> List[str]:
        if not text:
            return []

        if len(text) <= max_length:
            return [text]

        # Semantic boundaries ordered by priority
        separators = ["\n\n", "\n# ", "\n"]
        return self._recursive_chunk(text, max_length, separators)

    def _recursive_chunk(self, text: str, max_length: int, separators: List[str]) -> List[str]:
        if len(text) <= max_length:
            return [text]

        if not separators:
            # Hard split if no semantic boundaries left
            return [text[i:i+max_length] for i in range(0, len(text), max_length)]

        sep = separators[0]
        next_separators = separators[1:]

        parts = text.split(sep)

        reconstructed_parts = []
        for i, part in enumerate(parts):
            current_part = part
            if i > 0:
                if sep == '\n# ':
                    current_part = '# ' + current_part

            if i < len(parts) - 1:
                if sep == '\n# ':
                    current_part += '\n'
                else:
                    current_part += sep

            reconstructed_parts.append(current_part)

        flattened_parts = []
        for part in reconstructed_parts:
            if len(part) > max_length:
                flattened_parts.extend(self._recursive_chunk(part, max_length, next_separators))
            else:
                flattened_parts.append(part)

        chunks = []
        current_chunk = ""
        for part in flattened_parts:
            if len(current_chunk) + len(part) <= max_length:
                current_chunk += part
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def undo_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        5秒一键撤回 (5-second one-click undo) snapshot mechanism.
        Returns the last snapshot if it was created within 5 seconds,
        otherwise silently returns None.
        """
        if not self._snapshots:
            return None

        last_snapshot = self._snapshots[-1]
        if time.time() - last_snapshot["timestamp"] <= 5.0:
            return self._snapshots.pop()

        return None
